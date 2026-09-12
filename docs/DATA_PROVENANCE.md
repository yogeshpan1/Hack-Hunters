# College data provenance

NEXUS uses source-attributed reference data from the files supplied in `College Details Assets`. These source files stay local. The application needs the small, reviewed JSON datasets in `backend/data`, not the raw PDFs, screenshots or routines. Filenames and SHA-256 hashes in `college_operations.json` identify the exact input versions used for this transcription.

Source facts, interpretations and demonstration assumptions are different types of information. A published brochure is a curriculum reference, a routine is a schedule reference for its stated or unknown term, and a derived email address is not proof that the mailbox exists. Imported faculty names do not create login accounts.

## What was extracted

| Source | Structured result | Scope and limits |
| --- | --- | --- |
| `Class Details.csv` | 55 rooms; 2,821 seats; room codes, descriptive names, blocks and capacities | The user additionally confirmed AC and projector in every room, and one PC per seat in every Skill Block room. |
| `ICK UG Brochure 2026.pdf` | 9 undergraduate programme paths and 185 curriculum entries | Published curriculum, not current module-to-lecturer allocations. Physical PDF pages 99, 101, 103, 105, 107, 109, 111, 113 and 115. |
| `ICK PG Brochure.pdf` | 11 postgraduate programme paths and 95 curriculum entries | Six MBA and five MSc specializations. Physical PDF pages 39, 40, 43, 44, 47, 48, 55, 56, 59, 60 and 63. No module codes are printed. |
| `teachers_names.csv` | 154 input rows; 153 unique normalized faculty names | One repeated name, Yaman Shakya, is deduplicated. Original names and all source row numbers are retained. |
| Routine and semester images | 7 separate profiles; 60 source timetable rows | Sunday-Friday, half-hour starts, 1/1.5/2-hour sessions, named lecturer, named groups, room, module and session type. Dates and student counts are absent. |
| Two AY 2025-26 Level 5 assessment images | 25 components for 7 modules | Historical coursework deadlines, exam windows, weights, due weeks and some durations. No exact exam start times, rooms or invigilators are supplied. |

The room inventory contains 16 Skill Block rooms with 510 confirmed PCs, including TR-14 through TR-17. The TR prefix does not override the user's statement that every Skill Block classroom is a lab. Impact Block LAB-13 through LAB-16 are typed as labs from their codes, but their PC counts remain unconfirmed (`0` is the application's unknown-count convention). No other numeric room capacities were found in the routine images, so there is no second numeric capacity source to reconcile.

## Faculty directory and email convention

Faculty names are normalized by removing honorifics and parenthesized role annotations, while preserving the original CSV value. `Aayush Pandey (GTA)` becomes `Aayush Pandey`; `Mr. Manoj Poudel` becomes `Manoj Poudel`. Middle names remain in the displayed name.

Email addresses follow the convention explicitly supplied by the user: first name, a dot, last name, then `@islingtoncollege.edu.np`. Middle names are omitted and punctuation in initials such as K.C. is removed. Every generated address has `email_verified: false`. The extraction checks for collisions and stops if different people normalize to the same address; none occurred in the supplied CSV.

`FAC001`-style values are generated application identifiers, not college-issued staff IDs. `Computing` is inferred only for faculty who appear in a Computing/AI routine. Other departments remain `Unconfirmed`. The 18-hour workload limit is a prototype policy, not a contractual or source-supplied limit. An empty unavailability list means restrictions have not been supplied; it does not certify that a teacher is available all week.

Do not treat the user-supplied name list as an independently verified employment register. There is no student roster in the assets, and no student identities or teacher login accounts are generated from it.

## Routine profiles and source issues

| Profile | Rows | Period evidence | Main caveat |
| --- | ---: | --- | --- |
| Year 3 Computing C4 (`Routine-1.jpeg` and `Routine-2.jpeg`) | 6 | Level 6/Year 3; Autumn title is cropped | Both images are horizontal views of one table. Academic year is unknown. |
| Year 2 AI2 (`Routine-3.png`) | 12 | Viewer title: Autumn 2026, Level 5 | Databases has conflicting codes; one lecturer is only `Mr. Dahal`. |
| Year 3 AI1 (`Routine-4.png`) | 6 | Viewer title: Autumn 2026, Level 6 | Recommended coherent demonstration baseline; group sizes unknown. |
| Year 2 AI1 (`Routine-5.png`) | 12 | Viewer title: Spring 2026, Level 5 | Historical term; must not be merged into Autumn 2026. |
| Year 2 Computing C5 (`Semester 4.jpg`) | 12 | Year 2 in table; semester in filename | No year or term is visible. |
| Year 3 Computing C5 (`Semester 5.jpg`) | 6 | Year 3 in table; semester in filename | Shares three identical combined lectures with the C4 source. |
| Year 3 BigData01 (`Semester 5 Big Data.jpg`) | 6 | Year 3 in table; semester in filename | Module codes absent; some sessions biweekly from June 24/26 with no year or end date. |

The original routine code and title are retained. Routine/assessment codes often end in `NI`, whereas the UG brochure uses the base code. `catalogue_code` removes only that suffix, and only links when the resulting code exists in the relevant programme curriculum. No fuzzy code correction is applied.

In `Routine-3.png`, the Databases workshop and tutorial use `CC5051NI`; lecture row 6 prints `CS5051NI`. The lecture's original code remains intact and its catalogue link is null. Row 8 lists only `Mr. Dahal`; its faculty link is null. The dataset does not silently identify that person as Sudip Dahal. These unresolved rows are reference material and are excluded from the selected demonstration profile.

Combined lectures represent one booking attended by several cohorts. For example, `AI1+AI2+AI3` is a set of three cohort memberships, not an unrelated composite cohort. Conflict detection must compare intersecting memberships. Faculty allocation also belongs on the session: in the Year 3 Computing references, the same module has different lecturers for its lecture and workshop.

The three combined C1-C6 lectures repeated in the C4 and C5 source views must be deduplicated if those profiles are ever combined. Profiles with the same short label at different levels or terms must remain distinct. The reference dataset deliberately retains all source rows so the evidence can be reviewed without silently discarding duplicates.

The dataset uses `Asia/Kathmandu`, with Monday=0 through Friday=4 and Sunday=5. Starts and durations are hour values with exact `.5` increments. Saturday is not present in the supplied routines. The observed teaching window is 06:30-16:30; the application permits sessions ending at 17:00. Biweekly descriptions are retained as text, with machine recurrence dates left null until the missing year and end date are confirmed.

## Demonstration assumptions

The recommended baseline is the six-row Autumn 2026 Year 3 AI1 routine. Its three named lecturers, three module codes, six source room allocations, session types and times are transcribed from `Routine-4.png`.

The demonstration assumes 30 students in each of AI1 through AI6. This is a labelled planning assumption, not an extracted enrolment fact. Under that assumption:

| Source booking | Demonstration students | Inventory capacity |
| --- | ---: | ---: |
| AI1 workshop, LAB-08 or LAB-09 | 30 | 30 each |
| AI1 workshop, SR-01 | 30 | 57 |
| AI1-AI3 lecture, LT-05 | 90 | 100 |
| AI1-AI3 lecture, LT-06 | 90 | 96 |
| AI1-AI6 lecture, KUMARI-HALL-2 | 180 | 180 |

The original six-row source schedule is not asserted to contain an official college scheduling error. The application's optional demonstration loader can introduce a separately labelled capacity disruption: move the Friday 06:30 Big Data lecture for six groups from KUMARI-HALL-2 to LT-05. With the stated demonstration sizes, 180 students exceed LT-05's 100 seats, producing a real calculated conflict for the optimizer workflow. The source JSON remains unchanged, and the original allocation and deliberate disruption must be recorded in the application notes/audit.

The demo loader is intended for an empty teaching workspace and must not overwrite an administrator's existing records. `NEXUS_LOAD_DEMO=false` disables that optional demonstration population. This section describes the data contract; runtime behaviour is verified separately by application tests.

## Assessment interpretation

The two assessment sheets are explicitly AY 2025-26 Level 5 references. Coursework submission dates are transcribed as dates. Exam periods are preserved as `window_start` and `window_end`; `date`, `start`, `room_code` and `invigilator` remain null where not supplied. The final note says exact examination dates will be communicated later through the MST Platform and College Email. The reference does not justify creating confirmed exam bookings.

One source conflict needs confirmation: the Network Operating Systems progress-test line prints a Tuesday-Monday range but numeric dates of December 29-January 2, 2026. Interpreted across the academic year as 2025-12-29 to 2026-01-02, those dates are Monday-Friday. The numeric interpretation and the inconsistent weekday text are both documented; neither is silently presented as a confirmed live exam.

Weight cells span milestones and final submissions. A milestone has no independent `weight_percent`; its parent component's percentage is retained as `assessment_group_weight_percent`. Summing only non-null final/component weights gives 100% per module. This avoids incorrectly counting the same coursework weight for each milestone.

Some examination durations are supplied: Network Operating Systems progress test 1 hour, practical test 1.5 hours and theory exam 2 hours; Software Engineering unseen examination 2 hours. The other durations stay null. Venue/resource requirements cannot be inferred solely from a course title and are not fabricated.

## Curriculum caveats

MBA final-semester routes are alternatives, represented with an optional-group label, rather than simultaneous required modules. PG module codes remain null. Published credit values are retained as printed; apparent credit inconsistencies, particularly in the MBA Events and Tourism final-semester table, need programme-administrator confirmation before a credit audit. The programme catalogue should not be mistaken for a current module delivery plan.

## Rebuilding and verification

`scripts/extract-college-data.py` rebuilds `backend/data/college_catalog.json` from the local room CSV and brochure curriculum tables; it needs PyMuPDF only for rebuilding. `scripts/extract-operations-data.py` rebuilds `backend/data/college_operations.json` with Python's standard library. Its table rows are reviewed transcriptions of the images, while names are parsed from the CSV. The app does not need either extraction dependency or source folder at runtime.

Keep raw source files unchanged, review a changed hash before replacing a transcription, and review the JSON diff after rebuilding. Source fields identify filenames and row numbers, and `issues` records unresolved values. These documents and JSON contain no passwords, API keys or account tokens.

## Hackathon brief

The four-page `Intelligent Academic Planning.pdf` describes Islington College's RTE department coordinating timetables, examinations, seating, lecturers and physical resources through disconnected spreadsheets and logs. The challenge is a unified web platform that improves scheduling and resource allocation with conflict detection, constraint solving, clearer workload/resource visibility or similar active support.

It explicitly allows teams to focus on one or more problem areas. The expected submission is a working prototype with at least one meaningful end-to-end scheduling, allocation, optimization or conflict-management workflow, a demonstration of improvement, and a technical overview. Depth, effectiveness, innovation and quality of the demonstrated solution matter more than implementing every listed feature. NEXUS therefore uses an auditable conflict-to-reviewed-optimization workflow as its primary demonstration.
