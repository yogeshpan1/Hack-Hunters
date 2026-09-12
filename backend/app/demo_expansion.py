"""Build the clearly labelled academic demonstration overlay.

The supplied student PDF is a private source roster. It is not copied into the
repository or the database: it contributes only its verified headcount (276).
All student records created here are synthetic, have non-identifying codes, and
are safe to use in a public hackathon demo.
"""
import json
import os
import re
from collections import defaultdict
from pathlib import Path

from . import models as m
from .services import audit, bump

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "college_catalog.json"
SOURCE_ROSTER_COUNT = 276
SOURCE_ACADEMIC_YEAR = "2024/25"


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

    # One cohort per programme/year models every supplied curriculum level. The
    # existing AI groups remain intact because their names do not use this prefix.
    cohorts_by_offering = {}
    for programme in catalog["programmes"]:
        pid = programme["id"]
        for year in sorted({entry.get("year", entry.get("semester", 1)) for entry in programme["curriculum"]}):
            name = f"P{pid}-Y{year}"
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
                        "Headcount derived from the supplied private Computing roster; names and IDs are deliberately not imported."
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

    # Generate non-identifying student records. The original roster never leaves
    # the local reference folder; even the 276-count cohort gets synthetic names.
    students_created = 0
    for (pid, year), cohort in cohorts_by_offering.items():
        count = SOURCE_ROSTER_COUNT if pid == 1 and year == 1 else 24
        prefix = f"STU-P{pid}-Y{year}"
        for number in range(1, count + 1):
            code = f"{prefix}-{number:03d}"
            db.add(m.Student(
                code=code,
                name=f"Student {number:03d}",
                email=f"student{number:03d}.p{pid}y{year}@demo.nexus.local",
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
        reason="Created source-backed curriculum coverage, one-to-one demo lecturer allocations and non-identifying planning students. Private roster names and identifiers were not imported.",
        result="Demo expansion ready",
    )
    db.commit()
    return True
