"""Build the clearly labelled academic demonstration overlay.

The supplied student PDF stays private and is never copied into the repository.
When it is present on the authorised local machine, the user-requested roster is
loaded into the local MongoDB database. Deployments without the private file use
synthetic profiles and must not expose the local roster.
"""
import json
import os
import re
from collections import defaultdict
from pathlib import Path

from . import models as m
from .services import audit, bump
from .student_roster import load_private_student_roster, student_email

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "college_catalog.json"
SOURCE_ROSTER_COUNT = 276
SOURCE_ACADEMIC_YEAR = "2024/25"
DEMO_REFRESH_VERSION = "2026-09-13-full-planning-coverage-v2"

_GIVEN_NAMES = (
    "Aarav", "Aaryan", "Aastha", "Aayush", "Abhaya", "Abhishek", "Aditya",
    "Aisha", "Alisha", "Aman", "Amisha", "Anish", "Anisha", "Anmol",
    "Anusha", "Arjun", "Arya", "Ashish", "Asmita", "Avinash", "Ayush",
    "Bibhuti", "Bikash", "Bina", "Binod", "Bishal", "Deepa", "Dipesh",
    "Gaurav", "Hema", "Ishaan", "Kiran", "Kriti", "Manish", "Nabin",
    "Nisha", "Prabin", "Pratiksha", "Rachana", "Rohan", "Sabin", "Sushma", "Sanjay", "Sujan", "Suman", "Sarita",
    "Anup", "Anupam", "Bibek", "Binita", "Dinesh", "Elina", "Gita", "Hari",
    "Janak", "Kamala", "Laxmi", "Madan", "Nirmal", "Puja", "Rabina", "Ramesh",
    "Reshma", "Sagar", "Sandesh", "Sita",
)
_FAMILY_NAMES = (
    "Adhikari", "Acharya", "Bajracharya", "Basnet", "Bhandari", "Bhattarai",
    "Bista", "Bohara", "Chaudhary", "Dahal", "Dangol", "Gautam", "Ghimire",
    "Gurung", "Joshi", "Kafle", "Karki", "KC", "Khanal", "Khadka", "Lama",
    "Magar", "Maharjan", "Manandhar", "Nepal", "Poudel", "Rai", "Rana",
    "Regmi", "Sah", "Shakya", "Sharma", "Sherpa", "Shrestha", "Subedi",
    "Tamang", "Thapa", "Upreti", "Yadav", "Yonjan",
)


def _cohort_name(programme_id, year):
    if programme_id == 1:
        return f"C{year}"
    if programme_id == 2:
        # AI1–AI6 are retained from the supplied Level 6 routine.
        return f"AI{year + 6}"
    if programme_id == 3:
        return f"NT{year}"
    if programme_id == 4:
        return f"MT{year}"
    if programme_id in {5, 6, 7, 8}:
        return f"B{(programme_id - 5) * 3 + year}"
    if programme_id == 9:
        return f"AF{year}"
    postgraduate_prefixes = {
        10: "MBA-IB", 11: "MBA-PM", 12: "MBA-AM", 13: "MBA-DM",
        14: "MBA-ET", 15: "MBA-CS", 16: "MSc-DA", 17: "MSc-AI",
        18: "MSc-SE", 19: "MSc-DO", 20: "MSc-CTI",
    }
    return f"{postgraduate_prefixes[programme_id]}{year}"


def _synthetic_student_name(index):
    return f"{_GIVEN_NAMES[index % len(_GIVEN_NAMES)]} {_FAMILY_NAMES[(index // len(_GIVEN_NAMES)) % len(_FAMILY_NAMES)]}"


def _slug(value):
    return re.sub(r"[^A-Z0-9]+", "", value.upper())[:28]


def _module_key(entry):
    return (entry.get("code") or "", entry["name"].strip().casefold())


def migrate_roles(db):
    """Upgrade the short-lived Registrar model without locking out local users."""
    changed = False
    for user in db.find(m.User, {"role": {"$in": ["Super Admin", "Registrar"]}}):
        user.role = "SuperAdmin"
        changed = True
    if changed:
        db.commit()


def seed_requested_accounts(db):
    """Create explicitly configured local role accounts once, without storing secrets in source."""
    accounts = [
        ("NEXUS_SUPERADMIN_EMAIL", "NEXUS_SUPERADMIN_PASSWORD", "NEXUS_SUPERADMIN_NAME", "SuperAdmin", "NEXUS SuperAdmin"),
        ("NEXUS_RTE_EMAIL", "NEXUS_RTE_PASSWORD", "NEXUS_RTE_NAME", "RTE", "RTE Administrator"),
        ("NEXUS_SSD_EMAIL", "NEXUS_SSD_PASSWORD", "NEXUS_SSD_NAME", "SSD", "SSD Timetable Viewer"),
    ]
    changed = False
    for email_key, password_key, name_key, role, default_name in accounts:
        email = os.getenv(email_key, "").strip().lower()
        password = os.getenv(password_key, "")
        if not email or len(password) < 4:
            continue
        user = db.first(m.User, {"email": email})
        if user is None:
            from .auth import password_hash
            db.add(m.User(name=os.getenv(name_key) or default_name, email=email, password_hash=password_hash(password), role=role))
            changed = True
        else:
            from .auth import password_hash, verify_password
            if user.role != role:
                user.role = role
                changed = True
            if not verify_password(password, user.password_hash):
                user.password_hash = password_hash(password)
                changed = True
    if changed:
        db.commit()


def _study_level(programme, year):
    if programme.get("level", "").casefold() == "postgraduate":
        return "Masters"
    return {1: "First Year", 2: "Second Year", 3: "Third Year"}.get(year, "Masters")


def _planning_slots(study_level):
    """Return practical lecture slots while leaving room for the stated policies."""
    if study_level == "Masters":
        return (6.5, 7.5)
    if study_level == "Third Year":
        return (6.5, 8.0, 9.5)
    return (7.0, 8.5, 10.0, 11.5, 13.0, 14.5, 15.5)


def _patterns_overlap(first, second):
    return first == "Weekly" or second == "Weekly" or first == second


def _catalogue_planning_tasks(db):
    cohorts={cohort.id: cohort for cohort in db.find(m.Cohort)}
    existing_sessions=list(db.find(m.TimetableSession))
    existing={(session.module_id, tuple(sorted(session.cohort_ids))) for session in existing_sessions}
    modules_already_scheduled={session.module_id for session in existing_sessions}
    tasks=[]
    for module in db.find(m.Module):
        # Reference-routine modules have no catalogue offerings; their actual
        # source sessions remain the authoritative demonstration allocation.
        if not module.offerings and module.id in modules_already_scheduled:
            continue
        offerings=module.offerings or [{"cohort_id": cohort_id} for cohort_id in module.cohort_ids or [module.cohort_id]]
        for offering in offerings:
            cohort_id=offering["cohort_id"]
            if (module.id, (cohort_id,)) in existing:
                continue
            cohort=cohorts[cohort_id]
            if cohort.size > 270:
                section_size=(cohort.size + 1)//2
                tasks.extend([
                    (module, cohort, section_size, "Section A"),
                    (module, cohort, cohort.size-section_size, "Section B"),
                ])
            else:
                tasks.append((module, cohort, None, ""))
    priority={"Masters":0,"Third Year":1,"First Year":2,"Second Year":3}
    return sorted(tasks,key=lambda task:(priority.get(task[1].study_level,4),task[1].id,task[0].id,task[3]))


def add_full_planning_coverage(db):
    """Create one valid weekly lecture allocation for every catalogue offering.

    These are labelled generated planning allocations: source-derived Routine-4
    rows stay intact, while the full catalogue, faculty directory and every
    cohort become observable in planning, intelligence and What-If workflows.
    """
    tasks=_catalogue_planning_tasks(db)
    if not tasks:
        return 0
    rooms=list(db.find(m.Room))
    sessions=list(db.find(m.TimetableSession))
    modules={module.id:module for module in db.find(m.Module)}
    faculty={person.id:person for person in db.find(m.Faculty)}
    cohorts={cohort.id:cohort for cohort in db.find(m.Cohort)}
    room_busy=set(); faculty_busy=set(); cohort_busy=set(); cohort_day=defaultdict(list); faculty_hours=defaultdict(float)
    for session in sessions:
        module=modules[session.module_id]; person_id=session.faculty_id or module.faculty_id
        for tick in range(round(session.start*2),round((session.start+session.duration)*2)):
                room_busy.add((session.room_id,session.day,tick,session.week_pattern)); faculty_busy.add((person_id,session.day,tick,session.week_pattern))
                for cohort_id in session.cohort_ids or [module.cohort_id]: cohort_busy.add((cohort_id,session.day,tick,session.week_pattern))
        for cohort_id in session.cohort_ids or [module.cohort_id]: cohort_day[cohort_id,session.day,session.week_pattern].append((session.start,session.start+session.duration))
        faculty_hours[person_id,session.day,session.week_pattern]+=session.duration

    def busy(bookings, resource_id, day, ticks, pattern):
        overlapping_patterns=("Weekly", "A Week", "B Week") if pattern=="Weekly" else ("Weekly", pattern)
        return any((resource_id,day,tick,booked_pattern) in bookings for tick in ticks for booked_pattern in overlapping_patterns)

    def intervals_for(cohort_id, day, pattern):
        return [interval for booked_pattern in ("Weekly","A Week","B Week") if _patterns_overlap(booked_pattern,pattern) for interval in cohort_day[cohort_id,day,booked_pattern]]

    def fits_cohort(cohort_id, day, start, duration, level, pattern):
        intervals=sorted([*intervals_for(cohort_id,day,pattern),(start,start+duration)])
        if level=="Third Year" and len(intervals)>2:
            return False
        if level=="First Year":
            uninterrupted=1
            for previous,current in zip(intervals,intervals[1:]):
                uninterrupted=uninterrupted+1 if current[0]-previous[1]<1 else 1
                if uninterrupted>2:
                    return False
        return True

    created=0
    for module,cohort,planned_size,section_label in tasks:
        size=planned_size or cohort.size
        candidates=[]
        eligible=sorted((room for room in rooms if room.active and room.kind==module.room_type and room.capacity>=size and set(module.resources).issubset(room.equipment)),key=lambda room:(room.capacity-size,room.id))
        if not eligible:
            raise ValueError(f"No eligible room exists for {module.code} ({size} students).")
        weekly_count=sum(len(cohort_day[cohort.id,day,"Weekly"]) for day in range(6))
        faculty_weekly_count=round(sum(faculty_hours[module.faculty_id,day,"Weekly"] for day in range(6)) / 1.5)
        # A Masters cohort has only two 90-minute slots per day. Keep a small
        # shared weekly core, then alternate the rest. Apply the same limit to
        # the lecturer so a common module cannot consume every Masters slot.
        use_weekly=(cohort.study_level!="Masters" or (weekly_count<4 and faculty_weekly_count<4))
        patterns=("Weekly","A Week","B Week") if use_weekly else ("A Week","B Week")
        for pattern in patterns:
            for day in range(6):
                for start in _planning_slots(cohort.study_level):
                    duration=1.5
                    if start+duration>17 or (cohort.study_level=="Masters" and start+duration>9):
                        continue
                    ticks=range(round(start*2),round((start+duration)*2))
                    if busy(cohort_busy,cohort.id,day,ticks,pattern) or not fits_cohort(cohort.id,day,start,duration,cohort.study_level,pattern):
                        continue
                    for room in eligible:
                        if busy(room_busy,room.id,day,ticks,pattern) or busy(faculty_busy,module.faculty_id,day,ticks,pattern):
                            continue
                        score=((0 if pattern=="Weekly" else 10)+len(cohort_day[cohort.id,day,pattern])*1000+faculty_hours[module.faculty_id,day,pattern]*20+(room.capacity-size)/10+day)
                        candidates.append((score,room,day,start,pattern))
        if not candidates:
            raise ValueError(f"No valid planning slot exists for {module.code} / {cohort.name}.")
        _,room,day,start,pattern=min(candidates,key=lambda value:value[0])
        pattern_note="" if pattern=="Weekly" else f" Scheduled on the {pattern} rotation."
        session=m.TimetableSession(module_id=module.id,room_id=room.id,faculty_id=module.faculty_id,cohort_ids=[cohort.id],planned_size=planned_size,section_label=section_label,week_pattern=pattern,day=day,start=start,duration=1.5,session_type="Lecture",room_type=module.room_type,resources=module.resources,source="Full catalogue planning allocation",data_status="Generated planning allocation",notes="Generated lecture allocation for catalogue coverage. Confirm programme delivery, class sections and faculty availability before operational publication."+pattern_note)
        db.add(session); sessions.append(session); created+=1
        for tick in range(round(start*2),round((start+1.5)*2)):
            room_busy.add((room.id,day,tick,pattern)); faculty_busy.add((module.faculty_id,day,tick,pattern)); cohort_busy.add((cohort.id,day,tick,pattern))
        cohort_day[cohort.id,day,pattern].append((start,start+1.5)); faculty_hours[module.faculty_id,day,pattern]+=1.5
    return created


def expand_college_demo(db):
    if os.getenv("NEXUS_LOAD_DEMO", "true").lower() == "false":
        return False
    if db.first(m.AuditLog, {"action": "DEMO ACADEMIC EXPANSION INITIALIZED"}):
        return False
    administrator = db.first(m.User, {"role": "SuperAdmin", "active": True})
    if not administrator:
        return False

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    programmes = {programme.id: programme for programme in db.find(m.Programme)}
    faculty = list(db.find(m.Faculty))
    if not programmes or not faculty:
        return False

    # One named planning cohort per programme/year models every supplied
    # curriculum level using the local group conventions (C, AI, B, NT, etc.).
    cohorts_by_offering = {}
    for programme in catalog["programmes"]:
        pid = programme["id"]
        for year in sorted({entry.get("year", entry.get("semester", 1)) for entry in programme["curriculum"]}):
            name = _cohort_name(pid, year)
            cohort = db.first(m.Cohort, {"name": name})
            if cohort is None:
                source_count = SOURCE_ROSTER_COUNT if pid == 1 and year == 1 else 24
                cohort = m.Cohort(
                    name=name,
                    programme_id=pid,
                    size=source_count,
                    level=year + 3,
                    study_level=_study_level(programme, year),
                    period=f"Year {year}",
                    intake="Autumn",
                    academic_year=SOURCE_ACADEMIC_YEAR if pid == 1 and year == 1 else "2026/27",
                    source="Student Details.pdf" if pid == 1 and year == 1 else "Generated demonstration planning cohort",
                    data_status="Generated / source count" if pid == 1 and year == 1 else "Generated demonstration data",
                    notes=(
                        "Headcount derived from the supplied private Computing roster. "
                        "A local-only refresh can synchronize the authorised roster into MongoDB."
                        if pid == 1 and year == 1 else
                        "Generated planning cohort; enrolment is not a college source fact."
                    ),
                )
                db.add(cohort)
            cohorts_by_offering[(pid, year)] = cohort

    # Combine identical catalogue entries into a single module with explicit
    # programme/cohort offerings. This avoids assigning one lecturer twice.
    grouped = defaultdict(list)
    for programme in catalog["programmes"]:
        for entry in programme["curriculum"]:
            grouped[_module_key(entry)].append((programme, entry))

    existing_by_faculty = {module.faculty_id for module in db.find(m.Module)}
    available_faculty = [person for person in faculty if person.id not in existing_by_faculty]
    existing_codes = {module.code for module in db.find(m.Module)}
    unassigned = []
    created_modules = 0
    for index, entries in enumerate(grouped.values(), 1):
        programme, entry = entries[0]
        canonical_code = entry.get("code") or f"CAT-{index:03d}-{_slug(entry['name'])[:12]}"
        code = canonical_code
        suffix = 2
        while code in existing_codes:
            code = f"{canonical_code[:34]}-{suffix}"
            suffix += 1
        existing_codes.add(code)
        primary_year = entry.get("year", entry.get("semester", 1))
        primary_cohort = cohorts_by_offering[(programme["id"], primary_year)]
        teacher = available_faculty.pop(0) if available_faculty else None
        if teacher is None:
            teacher = m.Faculty(
                name=f"Teaching allocation pending · {code}",
                code=f"TBA{index:03d}",
                department=programme["department"],
                email="",
                max_hours=18,
                source="Generated to complete module coverage",
                data_status="Generated demonstration data",
                notes="Not a member of the supplied faculty list. Replace with a confirmed lecturer.",
            )
            db.add(teacher)
            unassigned.append(code)
        offerings = []
        programme_ids, cohort_ids = [], []
        for offered_programme, offered_entry in entries:
            year = offered_entry.get("year", offered_entry.get("semester", 1))
            cohort = cohorts_by_offering[(offered_programme["id"], year)]
            if offered_programme["id"] not in programme_ids:
                programme_ids.append(offered_programme["id"])
            if cohort.id not in cohort_ids:
                cohort_ids.append(cohort.id)
            offerings.append({
                "programme_id": offered_programme["id"],
                "cohort_id": cohort.id,
                "year": year,
                "credits": offered_entry.get("credits") or 15,
                "source_code": offered_entry.get("code") or "Uncoded brochure entry",
            })
        db.add(m.Module(
            code=code,
            catalogue_code=entry.get("code") or "",
            name=entry["name"],
            programme_id=programme["id"],
            cohort_id=primary_cohort.id,
            faculty_id=teacher.id,
            programme_ids=programme_ids,
            cohort_ids=cohort_ids,
            offerings=offerings,
            credits=entry.get("credits") or 15,
            room_type="Classroom",
            resources=["AC", "Projector"],
            source="College brochure curriculum",
            data_status="Source module / generated allocation",
            notes="Module title, code and credits are brochure-derived. Lecturer assignment is a one-to-one generated demo allocation and needs confirmation.",
        ))
        created_modules += 1

    # Start with authentic-looking synthetic profiles. A separate local-only
    # refresh replaces the C1 profiles with the supplied roster when available.
    students_created = 0
    for (pid, year), cohort in cohorts_by_offering.items():
        count = SOURCE_ROSTER_COUNT if pid == 1 and year == 1 else 24
        prefix = f"STU-P{pid}-Y{year}"
        for number in range(1, count + 1):
            code = f"{prefix}-{number:03d}"
            db.add(m.Student(
                code=code,
                name=_synthetic_student_name(students_created),
                email=student_email(_synthetic_student_name(students_created)),
                cohort_id=cohort.id,
                status="Active",
                source="Student Details.pdf headcount" if pid == 1 and year == 1 else "Generated demonstration data",
                data_status="Generated / source count" if pid == 1 and year == 1 else "Generated demonstration data",
                notes="Synthetic identity for planning demonstration; not an imported student record.",
            ))
            students_created += 1

    bump(db)
    audit(
        db, administrator, "DEMO ACADEMIC EXPANSION INITIALIZED", "Curriculum, faculty allocation and student planning data",
        new={
            "source_roster_headcount": SOURCE_ROSTER_COUNT,
            "synthetic_students_created": students_created,
            "curriculum_modules_created": created_modules,
            "faculty_with_one_module": len(faculty),
            "pending_teaching_allocations": unassigned,
        },
        reason="Created source-backed curriculum coverage, one-to-one demo lecturer allocations and planning students. The subsequent local-only refresh synchronizes the authorised Computing roster when its ignored PDF is present.",
        result="Demo expansion ready",
    )
    db.commit()
    return True


def _set_values(record, **values):
    changed = False
    for key, value in values.items():
        if getattr(record, key) != value:
            setattr(record, key, value)
            changed = True
    return changed


def _rename_legacy_generated_cohorts(db):
    changed = False
    legacy = re.compile(r"^P(\d+)-Y(\d+)$")
    existing_names = {cohort.name for cohort in db.find(m.Cohort)}
    for cohort in db.find(m.Cohort):
        match = legacy.fullmatch(cohort.name)
        if not match:
            continue
        target = _cohort_name(int(match.group(1)), int(match.group(2)))
        if target in existing_names:
            continue
        existing_names.remove(cohort.name)
        existing_names.add(target)
        cohort.name = target
        cohort.notes = (
            f"{cohort.notes} Group label updated to the Islington College {target} convention."
        ).strip()
        changed = True
    return changed


def _sync_student_roster(db):
    cohort = db.first(m.Cohort, {"name": "C1"})
    if not cohort:
        return False, 0
    students = db.find(m.Student)
    changed = False
    source_candidates = sorted(
        (
            student for student in students
            if student.code.startswith("STU-P1-Y1-")
            or student.code.startswith("NP01CP4A")
            or student.source.startswith("Student Details.pdf")
        ),
        key=lambda student: student.id or 0,
    )
    private_roster = load_private_student_roster()
    source_ids = set()

    if private_roster:
        source_by_code = {student.code: student for student in source_candidates}
        available = iter(source_candidates)
        for row in private_roster:
            student = source_by_code.get(row["college_id"])
            if student is None:
                student = next(available, None)
            if student is None:
                student = m.Student(
                    code=row["college_id"],
                    name=row["name"],
                    email=student_email(row["name"]),
                    cohort_id=cohort.id,
                    status="Active",
                )
                db.add(student)
            source_ids.add(student.id)
            changed |= _set_values(
                student,
                code=row["college_id"],
                name=row["name"],
                email=student.email if student.data_status=="Provided college roster" and student.email and not student.email.endswith("@nexus.local") else student_email(row["name"]),
                cohort_id=cohort.id,
                status="Active",
                source="Student Details.pdf · local roster",
                data_status="Provided college roster",
                notes=(
                    f"Local roster import for London Met ID {row['london_met_id']}. "
                    "Email follows the college first.last convention supplied by the user."
                ),
            )
        changed |= _set_values(
            cohort,
            size=max(cohort.size, len(private_roster)),
            source="Student Details.pdf · local roster",
            data_status="Provided college roster",
            notes=(
                "Student roster supplied by the college user. Assigned to C1 because "
                "the PDF does not state a section label."
            ),
        )

    used_emails = {student.email for student in students if not student.data_status.startswith("Generated") and not student.source.startswith("Generated")}
    generated_index = 0
    for student in sorted(students, key=lambda value: value.id or 0):
        if student.id in source_ids or student.code.startswith("NP01CP4A"):
            continue
        generated = (
            student.data_status.startswith("Generated")
            or student.source.startswith("Generated")
            or student.name.startswith("Student ")
        )
        if not generated:
            continue
        name = student.name if not student.name.startswith("Student ") else _synthetic_student_name(generated_index)
        while student_email(name) in used_emails:
            if generated_index >= len(_GIVEN_NAMES) * len(_FAMILY_NAMES):
                raise ValueError("Generated student name pool exhausted; add more names before refreshing.")
            name = _synthetic_student_name(generated_index)
            generated_index += 1
        used_emails.add(student_email(name))
        email = student.email
        if not email or email.endswith("@nexus.local") or email == student_email(student.name):
            email = student_email(name)
        changed |= _set_values(
            student,
            name=name,
            email=email,
            data_status="Generated demonstration data",
            source="Generated Nepalese planning profile",
            notes="Synthetic planning identity; not a college student record.",
        )
    return changed, len(private_roster)


def _has_programme(module, programme_id):
    return module.programme_id == programme_id or programme_id in module.programme_ids


def _refresh_module_codes(db):
    changed = False
    official_code = "CC7008"
    modules = db.find(m.Module)
    used_codes = {module.code for module in modules}
    for module in modules:
        if module.name == "Advanced Ethical Hacking and Security Compliance":
            if module.code != official_code and official_code not in used_codes - {module.code}:
                used_codes.remove(module.code)
                used_codes.add(official_code)
                module.code = official_code
                changed = True
            changed |= _set_values(
                module,
                catalogue_code=official_code,
                source="College brochure curriculum · London Met Module Catalogue 2026/27",
                data_status="Source module / official code verified",
                notes=(
                    "CC7008 was verified against the London Metropolitan University "
                    "Module Catalogue for 2026/27. Lecturer allocation remains a "
                    "generated planning assignment and needs confirmation."
                ),
            )
        elif _has_programme(module, 20) and not module.catalogue_code:
            note = (
                "This Islington College validated specialisation module has no "
                "publicly listed London Met module code. Keep the internal reference "
                "code for scheduling until the academic office confirms one."
            )
            if note not in module.notes:
                module.notes = f"{module.notes} {note}".strip()
                changed = True
    return changed


def refresh_academic_demo(db):
    """Upgrade existing demo data without committing private student records."""
    if os.getenv("NEXUS_LOAD_DEMO", "true").lower() == "false":
        return False
    administrator = db.first(m.User, {"role": "SuperAdmin", "active": True})
    if not administrator:
        return False
    # Run each data upgrade once so subsequent edits and deletions survive startup.
    if db.first(m.AuditLog, {"action": "ACADEMIC DEMO DATA REFRESHED", "new.refresh_version": DEMO_REFRESH_VERSION}):
        return False
    cohorts_changed = _rename_legacy_generated_cohorts(db)
    programmes = {programme.id: programme for programme in db.find(m.Programme)}
    levels_changed = False
    for cohort in db.find(m.Cohort):
        inferred = _study_level({"level": programmes[cohort.programme_id].level}, max(1, cohort.level - 3))
        if cohort.study_level != inferred:
            cohort.study_level = inferred
            levels_changed = True
    roster_changed, private_count = _sync_student_roster(db)
    codes_changed = _refresh_module_codes(db)
    allocations_created = add_full_planning_coverage(db)
    changed = cohorts_changed or levels_changed or roster_changed or codes_changed or allocations_created
    if not changed:
        return False
    bump(db)
    audit(
        db,
        administrator,
        "ACADEMIC DEMO DATA REFRESHED",
        "Cohort labels, student profiles and module codes",
        new={
            "refresh_version": DEMO_REFRESH_VERSION,
            "private_roster_records_loaded": private_count,
            "cohort_labels_updated": cohorts_changed,
            "official_module_codes_updated": codes_changed,
            "generated_planning_allocations": allocations_created,
        },
        reason=(
            "Applied the Islington College cohort naming convention, synchronised "
            "the user-supplied local roster where available, refreshed generated "
            "student names, verified public module-code evidence, and generated "
            "weekly planning allocations for all catalogue modules, faculty and cohorts."
        ),
        result="Academic demonstration data refreshed",
    )
    db.commit()
    return True
