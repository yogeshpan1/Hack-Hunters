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
from .student_roster import load_private_student_roster

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "college_catalog.json"
SOURCE_ROSTER_COUNT = 276
SOURCE_ACADEMIC_YEAR = "2024/25"
DEMO_REFRESH_VERSION = "2026-09-12"

_GIVEN_NAMES = (
    "Aarav", "Aaryan", "Aastha", "Aayush", "Abhaya", "Abhishek", "Aditya",
    "Aisha", "Alisha", "Aman", "Amisha", "Anish", "Anisha", "Anmol",
    "Anusha", "Arjun", "Arya", "Ashish", "Asmita", "Avinash", "Ayush",
    "Bibhuti", "Bikash", "Bina", "Binod", "Bishal", "Deepa", "Dipesh",
    "Gaurav", "Hema", "Ishaan", "Kiran", "Kriti", "Manish", "Nabin",
    "Nisha", "Prabin", "Pratiksha", "Rachana", "Rohan", "Sabin", "Sushma",
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


def migrate_registrar(db):
    """Keep a pre-existing administrator usable after the Registrar-only change."""
    changed = False
    for user in db.find(m.User, {"role": "Super Admin"}):
        user.role = "Registrar"
        changed = True
    if changed:
        db.commit()


def expand_college_demo(db):
    if os.getenv("NEXUS_LOAD_DEMO", "true").lower() == "false":
        return False
    if db.first(m.AuditLog, {"action": "DEMO ACADEMIC EXPANSION INITIALIZED"}):
        return False
    administrator = db.first(m.User, {"role": "Registrar", "active": True})
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
                email=f"{code.lower()}@nexus.local",
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
                    email=f"{row['college_id'].lower()}@nexus.local",
                    cohort_id=cohort.id,
                    status="Active",
                )
                db.add(student)
            source_ids.add(student.id)
            changed |= _set_values(
                student,
                code=row["college_id"],
                name=row["name"],
                email=f"{row['college_id'].lower()}@nexus.local",
                cohort_id=cohort.id,
                status="Active",
                source="Student Details.pdf · local roster",
                data_status="Provided college roster",
                notes=(
                    f"Local roster import for London Met ID {row['london_met_id']}. "
                    "The email is a non-deliverable NEXUS placeholder."
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
        name = _synthetic_student_name(generated_index)
        generated_index += 1
        changed |= _set_values(
            student,
            name=name,
            email=f"{student.code.lower()}@nexus.local",
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
    administrator = db.first(m.User, {"role": "Registrar", "active": True})
    if not administrator:
        return False
    cohorts_changed = _rename_legacy_generated_cohorts(db)
    roster_changed, private_count = _sync_student_roster(db)
    codes_changed = _refresh_module_codes(db)
    changed = cohorts_changed or roster_changed or codes_changed
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
        },
        reason=(
            "Applied the Islington College cohort naming convention, synchronised "
            "the user-supplied local roster where available, refreshed generated "
            "student names, and verified public module-code evidence."
        ),
        result="Academic demonstration data refreshed",
    )
    db.commit()
    return True
