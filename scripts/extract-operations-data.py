"""Build a reviewable, source-attributed college operations reference dataset.

The CSV is parsed automatically. Routine and assessment rows below are manually
transcribed from the supplied images; preserving them here makes corrections
reviewable without committing the raw reference images. Nothing creates accounts.
Run from the repository root with Python 3.11+. No external dependency is required.
"""
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'College Details Assets'
DAYS = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SUN': 5}


def name_without_title(value):
    value = re.sub(r'\s*\([^)]*\)', '', value.strip())
    return re.sub(r'^(?:Mr\.?|Ms\.?|Mrs\.?|Dr\.?)\s+', '', value).strip()


def institutional_email(name):
    parts = name_without_title(name).split()
    first, last = [re.sub('[^a-z]', '', part.lower()) for part in (parts[0], parts[-1])]
    if not first or not last:
        raise ValueError('A faculty name cannot be normalized to the supplied email convention.')
    return f'{first}.{last}@islingtoncollege.edu.np'


# Day | start | duration | type | module code | module title | lecturer | groups | room
# Times are hours in Asia/Kathmandu. Half hours remain exact .5 values.
ROUTINES = [
    {
        'id': 'undated-computing-level6-c4', 'title': 'Year 3 Computing - C4',
        'programme_id': 1, 'level': 6, 'term': None,
        'source': ['Routine-1.jpeg', 'Routine-2.jpeg'],
        'notes': 'Two horizontal views of the same six-row routine. The Autumn year in the title is cropped; term/year are unconfirmed.',
        'rows': '''SUN|6.5|2|Workshop|CC6012NI|Data and Web Development|Mr. Prajwol Adhikari|C4|TR-14
TUE|6.5|2|Workshop|CU6051NI|Artificial Intelligence|Mr. Subarna Sapkota|C4|LAB-04
WED|8.5|2|Workshop|CS6004NI|Application Development|Mr. Aashish Rimal|C4|SR-06
THU|8|1.5|Lecture|CC6012NI|Data and Web Development|Mr. Abhishek Anand|C1+C2+C3+C4+C5+C6|KUMARI-HALL-1
FRI|6.5|1.5|Lecture|CU6051NI|Artificial Intelligence|Mr. Subarna Sapkota|C1+C2+C3+C4+C5+C6|KUMARI-HALL-1
FRI|9.5|1.5|Lecture|CS6004NI|Application Development|Mr. Bikram Poudel|C1+C2+C3+C4+C5+C6|KUMARI-HALL-1''',
    },
    {
        'id': 'autumn-2026-ai-level5-ai2', 'title': 'Year 2 Computing with Artificial Intelligence - AI2',
        'programme_id': 2, 'level': 5, 'term': 'Autumn 2026', 'source': ['Routine-3.png'],
        'notes': 'Term is visible in the document viewer title. Row 6 has a conflicting Databases module code; row 8 supplies only the lecturer surname.',
        'rows': '''SUN|10|2|Workshop|MA5054NI|Further Calculus|Mr. Nadil Paudel|AI2|TR-03
SUN|12|2|Workshop|CC5051NI|Databases|Mr. Kiran Chand|AI2|TR-01
MON|12.5|2|Workshop|CS5003NI|Data Structure and Specialist Programming|Mr. Sudip Dahal|AI2|LAB-07
MON|14.5|2|Workshop|CS5002NI|Software Engineering|Ms. Lenisha Ghimire|AI2|LAB-06
TUE|10.5|1.5|Lecture|CS5002NI|Software Engineering|Mr. Sanjeep Lama|AI1+AI2+AI3+AI4+AI5|KUMARI-HALL-2
TUE|13|1.5|Lecture|CS5051NI|Databases|Ms. Astha Sharma|AI1+AI2+AI3+AI4+AI5|KUMARI-HALL-1
WED|10|1.5|Lecture|MA5054NI|Further Calculus|Mr. Nadil Paudel|AI1+AI2+AI3+AI4+AI5|KUMARI-HALL-2
WED|13|1.5|Lecture|CS5003NI|Data Structure and Specialist Programming|Mr. Dahal|AI1+AI2+AI3+AI4+AI5|KUMARI-HALL-1
WED|14.5|1|Tutorial|CS5002NI|Software Engineering|Ms. Lenisha Ghimire|AI2|LT-04
THU|13|1|Tutorial|MA5054NI|Further Calculus|Mr. Nadil Paudel|AI2|TR-15
THU|14|1|Tutorial|CC5051NI|Databases|Mr. Kiran Chand|AI2|TR-14
FRI|13.5|1|Tutorial|CS5003NI|Data Structure and Specialist Programming|Mr. Sudip Dahal|AI2|TR-01''',
    },
    {
        'id': 'autumn-2026-ai-level6-ai1', 'title': 'Year 3 Artificial Intelligence - AI1',
        'programme_id': 2, 'level': 6, 'term': 'Autumn 2026', 'source': ['Routine-4.png'],
        'notes': 'Recommended single-profile demonstration baseline. The source provides no cohort sizes or enrolment roster.',
        'rows': '''SUN|8.5|2|Workshop|CU6051NI|Artificial Intelligence|Mr. Roshan Shrestha|AI1|LAB-08
TUE|6.5|2|Workshop|CT6008NI|Big Data and Data Mining|Ms. Labbi Karmacharya|AI1|LAB-09
WED|6.5|2|Workshop|CC6057NI|Applied Machine Learning|Mr. Mahotsav Bhattarai|AI1|SR-01
THU|8|1.5|Lecture|CC6057NI|Applied Machine Learning|Mr. Mahotsav Bhattarai|AI1+AI2+AI3|LT-05
THU|9.5|1.5|Lecture|CU6051NI|Artificial Intelligence|Mr. Roshan Shrestha|AI1+AI2+AI3|LT-06
FRI|6.5|1.5|Lecture|CT6008NI|Big Data and Data Mining|Ms. Labbi Karmacharya|AI1+AI2+AI3+AI4+AI5+AI6|KUMARI-HALL-2''',
    },
    {
        'id': 'spring-2026-ai-level5-ai1', 'title': 'Year 2 Computing with Artificial Intelligence - AI1',
        'programme_id': 2, 'level': 5, 'term': 'Spring 2026', 'source': ['Routine-5.png'],
        'notes': 'Historical Spring 2026 profile. Do not merge this with Autumn 2026 as one active term.',
        'rows': '''SUN|7|2|Workshop|CS5003NI|Data Structures and Specialist Programming|Mr. Akchayat Bikram Joshi|AI1|TR-08
SUN|10|2|Workshop|MA5053NI|Probability and Statistics|Mr. Indra Prasad Dhakal|AI1|SR-02
MON|9|2|Workshop|CS5002NI|Software Engineering|Mr. Dipesh Raj Adhikari|AI1|SR-05
TUE|8.5|1.5|Lecture|CC5061NI|Applied Data Science|Mr. Roshan Shrestha|AI1+AI2+AI3+AI4+AI5+AI6|KUMARI-HALL-2
TUE|11.5|1.5|Lecture|MA5053NI|Probability and Statistics|Mr. Indra Prasad Dhakal|AI1+AI2+AI3+AI4+AI5+AI6|KUMARI-HALL-2
WED|7.5|1|Tutorial|CC5061NI|Applied Data Science|Mr. Subarna Sapkota|AI1|LT-04
WED|9|1.5|Lecture|CS5002NI|Software Engineering|Mr. Rubin Thapa|AI1+AI2+AI3+AI4+AI5+AI6|KUMARI-HALL-2
WED|12|1.5|Lecture|CS5003NI|Data Structures and Specialist Programming|Mr. Akchayat Bikram Joshi|AI1+AI2+AI3+AI4+AI5+AI6|KUMARI-HALL-2
THU|11|1|Tutorial|MA5053NI|Probability and Statistics|Mr. Indra Prasad Dhakal|AI1|TR-04
THU|12|1|Tutorial|CS5003NI|Data Structures and Specialist Programming|Mr. Akchayat Bikram Joshi|AI1|TR-04
FRI|11|1|Tutorial|CS5002NI|Software Engineering|Mr. Dipesh Raj Adhikari|AI1|TR-03
FRI|13|2|Workshop|CC5061NI|Applied Data Science|Mr. Subarna Sapkota|AI1|TR-03''',
    },
    {
        'id': 'undated-computing-semester4-c5', 'title': 'Year 2 Computing - C5 (Semester 4 file)',
        'programme_id': 1, 'level': 5, 'term': None, 'source': ['Semester 4.jpg'],
        'notes': 'Semester is supplied by the filename. No academic year or term is visible in the timetable.',
        'rows': '''SUN|12|2|Workshop|CC5067NI|Smart Data Discovery|Mr. Roshan Shrestha|C5|LAB-04
SUN|14.5|2|Workshop|CS5054NI|Advanced Programming and Technologies|Mr. Rubin Thapa|C5|LAB-04
MON|14|2|Workshop|CS5002NI|Software Engineering|Mr. Ishan Singh Thakuri|C5|TR-15
TUE|8.5|1.5|Lecture|CS5002NI|Software Engineering|Mr. Rubin Thapa|C1+C2+C3+C4+C5|KUMARI-HALL-1
TUE|11.5|1.5|Lecture|CS5071NI|Professional and Ethical Issues|Ms. Astha Sharma|C1+C2+C3+C4+C5|KUMARI-HALL-1
WED|13|1.5|Lecture|CC5067NI|Smart Data Discovery|Mr. Alish KC|C1+C2+C3+C4+C5|KUMARI-HALL-1
WED|15|1.5|Lecture|CS5054NI|Advanced Programming and Technologies|Ms. Rabina Lama|C1+C2+C3+C4+C5|KUMARI-HALL-2
THU|11|1|Tutorial|CS5054NI|Advanced Programming and Technologies|Mr. Rubin Thapa|C5|SR-10
THU|12|1|Tutorial|CC5067NI|Smart Data Discovery|Mr. Roshan Shrestha|C5|SR-09
THU|14|1|Tutorial|CS5071NI|Professional and Ethical Issues|Ms. Astha Sharma|C5|SR-07
FRI|11|1|Tutorial|CS5002NI|Software Engineering|Mr. Ishan Singh Thakuri|C5|SR-07
FRI|13|2|Workshop|CS5071NI|Professional and Ethical Issues|Ms. Astha Sharma|C5|SR-10''',
    },
    {
        'id': 'undated-computing-semester5-c5', 'title': 'Year 3 Computing - C5 (Semester 5 file)',
        'programme_id': 1, 'level': 6, 'term': None, 'source': ['Semester 5.jpg'],
        'notes': 'No year is visible. Three combined lectures match the C4 routine exactly and must not be inserted twice if the profiles are combined.',
        'rows': '''SUN|6.5|2|Workshop|CS6004NI|Application Development|Mr. Aashish Rimal|C5|TR-16
MON|6.5|2|Workshop|CC6012NI|Data and Web Development|Mr. Prajwol Adhikari|C5|TR-14
WED|8.5|2|Workshop|CU6051NI|Artificial Intelligence|Mr. Subarna Sapkota|C5|LAB-04
THU|8|1.5|Lecture|CC6012NI|Data and Web Development|Mr. Abhishek Anand|C1+C2+C3+C4+C5+C6|KUMARI-HALL-1
FRI|6.5|1.5|Lecture|CU6051NI|Artificial Intelligence|Mr. Subarna Sapkota|C1+C2+C3+C4+C5+C6|KUMARI-HALL-1
FRI|9.5|1.5|Lecture|CS6004NI|Application Development|Mr. Bikram Poudel|C1+C2+C3+C4+C5+C6|KUMARI-HALL-1''',
    },
    {
        'id': 'undated-computing-semester5-bigdata01', 'title': 'Year 3 Computing - BigData01',
        'programme_id': 1, 'level': 6, 'term': None, 'source': ['Semester 5 Big Data.jpg'],
        'notes': 'No module codes or academic year are supplied. Some sessions are biweekly with June day/month anchors but no year; recurrence must be confirmed before live scheduling.',
        'rows': '''TUE|7|2|Workshop||DevOps and Cloud Deployment Bootcamp|Mr. Saurabh Adhikari|BigData01|LAB-09
TUE|10|1|Tutorial||Exploring Big Data with PySpark for Analytics and Insights|Mr. Shishir Mishra|BigData01|TR-15
WED|9|1.5|Lecture||Career Development Learning (Bi - Weekly Starting 24 June)|Mr. Bibek Baral|Flutter01+Django01+Django02+GameDev01+BigData01|KUMARI-HALL-1
WED|10.5|1.5|Lecture||Final Year Project (Bi - Weekly Starting 24 June)|Mr. Shishir Subedi|Flutter01+Django01+Django02+GameDev01+BigData01|KUMARI-HALL-1
THU|9|2|Workshop||Exploring Big Data with PySpark for Analytics and Insights|Mr. Shishir Mishra|BigData01|SR-05
FRI|7|2|Workshop||Data Structures and Algorithms (Bi - Weekly Starting 26 June)|Mr. Saroj Kumar Yadav|BigData01|SR-05''',
    },
]

ASSESSMENT_FILES = [f'AY 2025-26 BSc IT Assessment Schedule - Level 5 (C_251224_162117_page-000{i}.jpg' for i in (1, 2)]


def assessment_rows():
    rows = []

    def add(code, title, period, credits, courses, page, components):
        # component | type | weight (final only) | group weight | week | date/window | duration
        for index, line in enumerate(components.splitlines(), 1):
            component, kind, weight, group_weight, week, dates, duration = line.split('|')
            window = dates.split('/')
            rows.append({
                'id': f'{code}-{index}', 'academic_year': '2025-26', 'module_code': code,
                'catalogue_code': code.removesuffix('NI'), 'module_title': title, 'level': 5,
                'period': period, 'credits': credits, 'courses': courses, 'component': component,
                'type': kind, 'weight_percent': int(weight) if weight else None,
                'assessment_group_weight_percent': int(group_weight) if group_weight else None,
                'due_week': int(week), 'date': window[0] if len(window) == 1 else None,
                'window_start': window[0] if len(window) == 2 else None,
                'window_end': window[1] if len(window) == 2 else None,
                'duration': float(duration) if duration else None, 'start': None,
                'room_code': None, 'invigilator': None, 'source': ASSESSMENT_FILES[page - 1],
                'data_status': 'Historical reference',
                'notes': 'Exact examination dates are to be communicated later via MST Platform and College Email, according to the source footnote. Times, venues, invigilators and enrolment counts are not supplied.' if kind in ('Exam', 'Practical assessment') else 'Historical coursework deadline. A milestone is part of its weighted assessment group, not an additional independently weighted assessment.',
            })

    add('CC5051NI', 'Databases', 'SEM 1', 15, ['Computing', 'Artificial Intelligence'], 1, '''Coursework: MCQ and relational-environment merits (300 words+)|Coursework|40|40|7|2025-12-05|
Coursework milestone: case study design and implementation|Milestone||60|9|2025-12-19|
Coursework milestone: case study design and implementation|Milestone||60|11|2025-12-31|
Coursework: case study design and implementation (2000 words+, 20 entities/relationships/queries)|Coursework|60|60|13|2026-01-18|''')
    add('CT5052NI', 'Network Operating Systems', 'SEM 1', 15, ['Computing'], 1, '''Progress test|Exam|10|10|11|2025-12-29/2026-01-02|1
Practical test|Exam|40|40|13|2026-01-13/2026-01-19|1.5
Unseen theory exam|Exam|50|50|14|2026-01-20/2026-01-26|2''')
    rows[-3]['notes'] += ' The printed weekday range is Tuesday-Monday, but the printed dates 29 December-2 January imply Monday-Friday across 2025-26. Numeric dates are preserved and require confirmation.'
    add('CS5053NI', 'Cloud Computing and the Internet of Things', 'SEM 1', 15, ['Computing'], 1, '''Group coursework milestone|Milestone||50|11|2026-01-02|
Group coursework|Coursework|50|50|13|2026-01-16|
Written exam (60% subjective and 40% objective)|Exam|50|50|14|2026-01-20/2026-01-26|''')
    add('CS5002NI', 'Software Engineering', 'YEAR', 30, ['Computing', 'Artificial Intelligence'], 1, '''First milestone for coursework 1 (group, 1000 words + diagrams or equivalent per student)|Milestone||20|9|2025-12-22|
Second milestone for coursework 1 (group, 1000 words + diagrams or equivalent per student)|Milestone||20|11|2026-01-05|
Coursework 1 (group, 1000 words + diagrams or equivalent per student)|Coursework|20|20|13|2026-01-19|
Milestone for coursework 2 (individual, 1200 words + diagrams or equivalent per student)|Milestone||35|22|2026-04-06|
Coursework 2 (individual, 1200 words + diagrams or equivalent per student)|Coursework|35|35|26|2026-04-20|
Unseen examination (seen case study)|Exam|45|45|29|2026-05-19/2026-05-25|2''')
    add('CS5071NI', 'Professional and Ethical Issues', 'SEM 2', 15, ['Computing', 'Networking'], 2, '''Coursework milestone (written report, 2000-2500 words or equivalent)|Milestone||100|10|2026-04-27|
Coursework (written report, 2000-2500 words or equivalent)|Coursework|100|100|13|2026-05-14|''')
    add('CC5067NI', 'Smart Data Discovery', 'SEM 2', 15, ['Computing'], 2, '''First coursework milestone (individual business data analytical report)|Milestone||60|7|2026-04-02|
Second coursework milestone (individual business data analytical report)|Milestone||60|10|2026-04-23|
Coursework (individual business data analytical report, 1500 words+ with analytical output and evaluation)|Coursework|60|60|12|2026-05-11|
Practical assessment (PowerBI analytical dashboard and demonstration)|Practical assessment|40|40|14|2026-05-19/2026-05-25|''')
    add('CS5054NI', 'Advanced Programming and Technologies', 'SEM 2', 15, ['Computing'], 2, '''Group coursework milestone (1300 words + software or equivalent per student)|Milestone||50|11|2026-05-04|
Group coursework (1300 words + software or equivalent per student)|Coursework|50|50|14|2026-05-21|
Written exam (unseen exam)|Exam|50|50|15|2026-05-26/2026-06-01|''')
    return rows


ISSUES = [
    {'id': 'faculty-duplicate', 'source': ['teachers_names.csv'], 'detail': 'Yaman Shakya occurs twice; one normalized faculty directory entry is retained with both CSV row numbers.'},
    {'id': 'faculty-unverified', 'source': ['teachers_names.csv'], 'detail': 'Names are supplied by the user. Employment status, staff IDs, actual mailbox existence, departments for people absent from routines, workload limits and availability are unconfirmed. Generated codes and email convention are explicitly labelled.'},
    {'id': 'routine-module-code', 'source': ['Routine-3.png'], 'detail': 'Databases is CC5051NI in workshop/tutorial rows but CS5051NI in lecture row 6. The latter has no exact brochure match; preserve raw code and leave catalogue link unresolved.'},
    {'id': 'routine-faculty-incomplete', 'source': ['Routine-3.png'], 'detail': 'Row 8 lecturer is only Mr. Dahal. Do not silently identify this as Sudip Dahal or another Dahal.'},
    {'id': 'routine-terms', 'source': ['Routine-1.jpeg', 'Routine-2.jpeg', 'Routine-3.png', 'Routine-4.png', 'Routine-5.png', 'Semester 4.jpg', 'Semester 5.jpg', 'Semester 5 Big Data.jpg'], 'detail': 'Sources include Spring 2026, Autumn 2026 and undated profiles. They are stored separately; equivalent short group labels in different levels/terms are not the same active cohort.'},
    {'id': 'shared-lecture-duplicate', 'source': ['Routine-1.jpeg', 'Routine-2.jpeg', 'Semester 5.jpg'], 'detail': 'Three combined Year 3 Computing lectures appear in both C4 and C5 source views. They represent shared sessions, not two bookings.'},
    {'id': 'cohort-sizes', 'source': ['Routine-4.png'], 'detail': 'No source provides cohort enrolment totals. Demonstration only uses 30 students per group, labelled as a planning assumption; no named student roster is fabricated.'},
    {'id': 'capacity-evidence', 'source': ['Class Details.csv'], 'detail': 'No conflicting numeric room capacity was found in the other supplied sources; routines do not print capacities. Skill Block TR rooms are labs under the user\'s explicit correction despite their TR prefix. Impact LAB-13 through LAB-16 have unknown PC counts.'},
    {'id': 'module-code-suffix', 'source': ['ICK UG Brochure 2026.pdf'], 'detail': 'Routine and assessment codes carry NI while the UG brochure uses the base code. A suffix-only crosswalk is made only where that base code exists in the programme catalogue. Original codes and source titles are preserved.'},
    {'id': 'biweekly-year-missing', 'source': ['Semester 5 Big Data.jpg'], 'detail': 'Biweekly sessions start 24 or 26 June, but the year and end date are absent. Module codes are also absent. Keep recurrence text and leave machine recurrence dates/codes null.'},
    {'id': 'exam-windows', 'source': ASSESSMENT_FILES, 'detail': 'Academic year 2025-26 is historical. Exam date windows are not exact bookings; the source says precise examination dates will be communicated later. Start times, rooms and invigilators are absent.'},
    {'id': 'exam-weekday-conflict', 'source': [ASSESSMENT_FILES[0]], 'detail': 'Network Operating Systems progress-test window prints Tuesday-Monday but the numeric December 29-January 2 dates correspond to Monday-Friday across 2025-26. Numeric dates are retained as an interpretation and flagged for confirmation.'},
    {'id': 'assessment-milestones', 'source': ASSESSMENT_FILES, 'detail': 'Merged weight cells cover multiple milestones and a final submission. Milestones receive no independent weight; group weight is retained separately so totals are not double-counted.'},
]


def main():
    csv_rows = list(csv.DictReader((SOURCES / 'teachers_names.csv').open(encoding='utf-8-sig', newline='')))
    people = {}
    for row_number, row in enumerate(csv_rows, 2):
        original = row['Teachers Name'].strip()
        name = name_without_title(original)
        key = name.casefold()
        if key in people:
            people[key]['source_rows'].append(row_number)
            continue
        people[key] = {
            'code': f'FAC{len(people) + 1:03}', 'name': name, 'email': institutional_email(name),
            'email_verified': False, 'department': 'Unconfirmed', 'max_hours': 18, 'unavailable': [],
            'source': 'teachers_names.csv', 'source_rows': [row_number], 'original_name': original,
            'data_status': 'Source name; unverified directory details',
            'notes': 'Code is an application identifier, not an official staff ID. Email is derived from the user-supplied first.last convention and is unverified. The 18-hour workload limit is a prototype policy; empty availability means no restrictions supplied, not confirmed availability.',
        }
    email_names = defaultdict(list)
    for person in people.values():
        email_names[person['email']].append(person['name'])
    collisions = {email: names for email, names in email_names.items() if len(names) > 1}
    if collisions:
        raise ValueError('Derived email collisions require manual resolution before export.')

    catalogue = json.loads((ROOT / 'backend/data/college_catalog.json').read_text(encoding='utf-8'))
    programme_codes = {p['id']: {m['code'] for m in p['curriculum'] if m['code']} for p in catalogue['programmes']}
    room_codes = {room['name'] for room in catalogue['rooms']}
    profiles = []
    for original in ROUTINES:
        profile = {key: value for key, value in original.items() if key != 'rows'}
        profile['data_status'] = 'Reference routine; enrolment and currency unconfirmed'
        profile['sessions'] = []
        for row_number, line in enumerate(original['rows'].splitlines(), 1):
            day, start, duration, kind, code, title, lecturer, groups, room = line.split('|')
            person = people.get(name_without_title(lecturer).casefold())
            notes = []
            if person:
                person['department'] = 'Computing'
            else:
                notes.append('Lecturer identity is incomplete in the source; faculty link requires confirmation.')
            base_code = code.removesuffix('NI') if code else None
            catalogue_code = base_code if base_code in programme_codes[profile['programme_id']] else None
            if code and catalogue_code is None:
                notes.append('Source module code has no exact suffix-normalized match in this programme brochure; do not silently correct it.')
            if not code:
                notes.append('No module code is supplied.')
            recurrence_text = re.search(r'\(Bi - Weekly Starting [^)]+\)', title)
            if recurrence_text:
                notes.append('Biweekly recurrence has an unknown year and end date; this is a reference pattern, not a dated recurrence.')
            if room not in room_codes:
                raise ValueError(f'Unknown source room code: {room}')
            profile['sessions'].append({
                'module_code': code or None, 'catalogue_code': catalogue_code, 'module_title': title,
                'faculty_code': person['code'] if person else None, 'faculty_raw': lecturer,
                'cohort_names': groups.split('+'), 'room_code': room, 'day': DAYS[day],
                'start': float(start), 'duration': float(duration), 'session_type': kind,
                'source': '; '.join(profile['source']), 'source_row': row_number,
                'data_status': 'Source routine; not a confirmed live allocation', 'notes': ' '.join(notes),
                'recurrence_text': recurrence_text.group(0) if recurrence_text else None,
                'recurrence_start': None, 'recurrence_end': None,
            })
        profile['cohorts'] = [{'name': name, 'size': None} for name in sorted({name for s in profile['sessions'] for name in s['cohort_names']})]
        profiles.append(profile)
    for person in people.values():
        if person['department'] == 'Computing':
            person['notes'] += ' Computing affiliation is inferred from a supplied Computing/AI teaching routine.'

    source_names = sorted({'teachers_names.csv', 'Class Details.csv', 'ICK UG Brochure 2026.pdf', 'ICK PG Brochure.pdf', *ASSESSMENT_FILES, *(source for p in profiles for source in p['source'])})
    manifest = []
    for name in source_names:
        with (SOURCES / name).open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        manifest.append({'file': name, 'sha256': digest})
    result = {
        'version': 1, 'institution': 'Islington College', 'timezone': 'Asia/Kathmandu',
        'day_index': {str(value): key for key, value in DAYS.items()},
        'faculty': list(people.values()), 'profiles': profiles,
        'recommended_demo': {
            'profile_id': 'autumn-2026-ai-level6-ai1', 'group_size': 30,
            'data_status': 'Demonstration with source routines and assumed enrolment',
            'notes': 'The six timetable rows, three named lecturers, modules, rooms and times come from Routine-4.png. Thirty students per group is a demonstration planning assumption only. No student identities are supplied or generated. Any demonstration disruption must be labelled separately from the original source schedule.',
        },
        'assessment_references': assessment_rows(), 'issues': ISSUES, 'source_manifest': manifest,
        'counts': {'teacher_csv_rows': len(csv_rows), 'faculty_unique': len(people), 'routine_profiles': len(profiles), 'routine_rows': sum(len(p['sessions']) for p in profiles), 'assessment_components': len(assessment_rows())},
    }
    output = ROOT / 'backend/data/college_operations.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
