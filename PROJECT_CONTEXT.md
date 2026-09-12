# NEXUS — Project context and developer handoff

Updated: 12 September 2026. Read this file and README.md before changing the application. No conversation history is required. This document describes the repository, not an aspirational product specification.

## Goal and hackathon challenge — DECIDED

NEXUS is an internal academic operations platform for Islington College, with ING as the secondary ecosystem identity. The supplied Intelligent Academic Planning brief describes centralized academic, examination and resource planning. It values solving a meaningful workflow with depth and active operational improvement, rather than merely storing records.

The implemented demonstration is: detect a timetable conflict → inspect its source and constraints → ask a grounded assistant → simulate with OR-Tools → review real changes → approve → publish atomically → record audit events, affected-user notifications and email drafts. This core loop takes priority over optional LLMs, prediction, and extra dashboards.

## Product and technical decisions — DECIDED

- Work in this repository; preserve working features. The remote is `https://github.com/NormieGit/Hackathon-.git`, branch `main`. Do not force-push or rewrite history. Prior baseline commits are `2dbce80` (reference redesign) and `b5fe0b4` (MongoDB/college inventory). The final cleanup/integration commit follows those; use `git log -1` for its exact identifier.
- MongoDB is the only primary database. PyMongo, Pydantic and FastAPI provide persistence and APIs. Do not reintroduce SQLAlchemy, PostgreSQL or SQL migrations.
- Frontend: React 19, TypeScript, Vite, Tailwind CSS v4, Lucide, Recharts, Axios, React Router. Native fetch consumes the optimizer NDJSON stream. No large component library or external state manager.
- Default local storage uses MongoDB Community 8.0.32, a single-node replica set, and localhost binding. Transactions are required. Data is outside OneDrive in `%LOCALAPPDATA%\Nexus\MongoDB`. No Atlas account is created. Hosted deployments may configure Atlas.
- Exactly one initial Registrar is bootstrapped into an empty database. A Registrar can add another Registrar. Legacy `Super Admin` accounts migrate to Registrar during startup so existing local access survives. There is no public registration or extra administrator hierarchy.
- The current account-creation UI and API accept only the Registrar role. Teacher directory records do not create login accounts.
- Credentials belong only in environment/local configuration. No default bootstrap password exists in current source. The setup helper accepts hidden input and never prints passwords. Existing accounts are preserved. Test passwords are random per test process.

## Architecture and important files

| Area | Files and responsibility |
| --- | --- |
| App assembly / management | `backend/app/main.py`: lifespan, handlers, workspace, timetable mutations, CRUD/import, approve/publish, communications, exams |
| Persistence | `backend/app/db.py`: request-scoped document repository, identity cache, transaction lifecycle, generated integer IDs, references, indexes |
| Models | `backend/app/models.py`: Pydantic MongoDB document types; `schemas.py`: strict validated request contracts |
| Scheduling | `backend/app/scheduling.py`: snapshot/enrichment, independent conflicts, calculated metrics, CP-SAT |
| Conflicts | `backend/app/conflict_store.py`: revisioned conflict and count snapshots inside academic-data transactions |
| Optimizer | `optimization_service.py`: simulation and stored run; `optimizer_routes.py`: readiness and real streaming stages |
| Intelligence | `intelligence_routes.py`: role-aware search and deterministic read-only assistant |
| Audit / recipients | `services.py`: audit, revision control, affected cohorts/faculty, notifications and drafts |
| Bootstrap | `seed.py`: college inventory/admin; `reference_seed.py`: guarded reference-derived operational demo |
| Runtime data | `backend/data/college_catalog.json`, `college_operations.json` |
| Frontend shell/state | `frontend/src/App.tsx`, `context.tsx`, `components/Shell.tsx`, `components/Intelligence.tsx` |
| UI/scheduling | `screens/Overview.tsx`, `Timetable.tsx`, `SessionEditor.tsx`, `NewSession.tsx`, `Optimization.tsx` |
| Data administration | `screens/Records.tsx`, `AcademicViews.tsx`, `System.tsx`, `Examinations.tsx`, `AssessmentReferences.tsx`, `PlanningInsights.tsx` |
| Branding / style | `components/Brand.tsx`, `index.css`, `reference.css`; untouched PNG logos in `frontend/public` |
| Tests | `backend/tests`: isolated real-MongoDB functional tests; fictional fixtures are test-only |
| Setup / extraction | `scripts/configure-local.py`, setup/start/restart PowerShell scripts, college/operations extraction scripts |
| Provenance | `docs/DATA_PROVENANCE.md`: source rows, conflicts, assumptions, temporal scope |

The remaining routes in main.py can be split further when working on their behavior; do not rewrite functioning routes solely for cosmetic reorganization. Optimization and intelligence already have separate modules.

## MongoDB data-model decisions — DECIDED

Independently queried records have their own collections: users, faculty, programmes, cohorts, students, rooms, modules, sessions, exams, rules, optimization_runs, audit_logs, approvals, notifications, emails, assessment_references, conflicts, conflict_snapshots, schedule_versions and counters.

Embedding is used for a programme's published curriculum, room/faculty availability lists, an optimization run's assignments/changes/scenario, and a historical assessment reference's detail. There is no giant institution document.

Integer IDs retain the existing frontend/API contracts. Unique indexes cover IDs and business identifiers (email, room/module/staff/student codes, programme/cohort names). Read-oriented indexes include student cohort/status, timetable day/room, conflict revision/session IDs, unique snapshot revision, audit entity/ID. Add indexes for measured queries rather than hypothetical schemas.

MongoSession stages writes and validates references before committing. It enforces an active administrator and blocks deleting referenced documents, including combined-cohort session memberships. Academic mutations persist conflict snapshots in the same transaction. Publication uses a revision compare-and-swap and revalidates proposals; stale simulations cannot publish. Duplicate/concurrent-write conflicts return 409. Database operational failures return a sanitized 503 without exposing connection values.

## Source data and demonstration state — DECIDED

Raw documents are local references in `College Details Assets` and `UI Reference images`. They are ignored and not needed to run the app. Only the exact required official logos were copied to runtime assets. Brochure PDFs and duplicate screenshots have been removed from the current tracked tree; historical commits remain intact.

`college_catalog.json` contains 55 rooms, 2,821 seats, 20 programme paths and 280 curriculum rows. Every room has AC/projector per the user's explicit instruction. All 16 Skill Block rooms are labs, including TR codes; their capacity equals confirmed PC count, totalling 510 PCs. Impact Block LAB rooms have unconfirmed PC counts and cannot satisfy computer requirements without a confirmed quantity.

`college_operations.json` contains 153 normalized faculty records; 7 separate routine profiles with 60 rows; 25 historical assessment components for 7 modules. Department remains unconfirmed unless a routine supports it. FAC identifiers and weekly target hours are prototype metadata. Generated emails follow first.last with middle names omitted, and are explicitly unverified. See DATA_PROVENANCE for ambiguity in lecturer names, module code prefixes/suffixes, source term boundaries, duplicate references and printed credit discrepancies.

The automatic demo loads only when operational faculty/cohort/module/session collections are empty and there is no prior marker. It uses one coherent Autumn 2026 Level 6 AI1 profile (Routine-4), six sessions and three modules. Each named AI group is assumed to contain 30 students; this is visibly labelled demo-derived. Combined lecture attendance sums all selected groups. The original 180-person Friday lecture is intentionally relocated from its 180-seat reference hall to LT-05 (100 seats), producing one explicit demo capacity conflict. The original source JSON is unchanged, and the altered session's notes preserve the actual source allocation. One workshop is locked for demonstration.

Existing users and Registrar edits are not overwritten. The expansion creates no staff login accounts. The private student PDF contributes only its verified 276-person Computing headcount; the database receives non-identifying generated planning students, not source names or IDs. Setting `NEXUS_LOAD_DEMO` false disables loading on an empty workspace. Rebuilding JSON extraction does not migrate existing database records.

Historical assessment deadlines and exam windows are displayed separately from timed exam allocations. Missing exact exam time, room and invigilator remain unknown; do not convert broad windows into invented exam bookings.

## Scheduling / optimization — DECIDED

Public day indices stay Monday=0 through Friday=4; Sunday is appended as 5. The UI displays Sunday first. Do not reorder these stored numeric meanings. Times are half-hour numbers, from 06:30 to 17:00. Solver variables use integer half-hour ticks.

A module carries default faculty/cohort/room requirements. A session can override faculty, `cohort_ids`, room type and resources; this is essential because a module has lectures and workshops with different spaces and sometimes different teachers. Combined-cohort overlaps are set intersections and attendance is the sum of group planning sizes, bounded below by active roster counts. Workshop does not automatically imply Lab: the source includes a workshop in classroom SR-01.

Hard constraints: room/faculty/cohort overlap, seating and PC capacity, room type/equipment, room/faculty availability, teaching hours and locks. The independent detector checks initial schedules, solver output, manual previews and publication. Validated timetable imports may carry scheduling conflicts intentionally, but invalid field types, times and references are rejected. Generic session CRUD is blocked to preserve audited timetable actions.

Soft preferences: minimize moved sessions, avoid the first period, compact cohort teaching days, and reduce faculty hours beyond four per day. Weekly workload totals remain fixed. Room utilization is measured rather than promised to improve: moving fixed sessions alone may leave it unchanged. Solver configuration: one worker, seed 42, 12-second search limit. Feasible and optimal results are distinguished from infeasible/timeouts.

The NDJSON endpoint reports stages only as real backend work advances. Two solver streams per process are permitted; this is an in-process limit, not a distributed worker queue. No fake completion, time-based percentage or canned before/after numbers.

## UI / branding / interactions — DECIDED

Islington is primary, NEXUS is product identity, ING is secondary. Preserve official logo aspect ratios and pixels. Use the untouched crest within the NEXUS geometric seal. Institutional navy remains primary, burgundy emphasizes signature/critical/active states, with neutral surfaces and restrained semantic colours. Do not turn the product into saturated generic SaaS or cyber-security styling.

The Command Center follows the live Figma preview: a five-metric health strip, then Schedule Intelligence, ranked recommendations, and weekly operational load in three columns. The global command bar and Cmd/Ctrl+K open search/assistance; avoid a giant assistant button beside the page title.

The signature startup is four seconds before overlay removal, with Skip introduction and immediate reduced-motion completion. SVG academic nodes organize into the NEXUS seal. Dark mode has been removed; keyboard controls, visible focus and text/icon status cues remain.

Timetable Studio dynamically renders half-hour sessions and combined group names, retaining room/cohort/faculty/module views, selection inspector, drag-to-preview, lock and audited manual move. Provenance and the deliberate demo change are visible in session details. Faculty and programme details show source status and programme curriculum; unverified faculty email metadata is editable by authorized administrators.

## Assistant / audit / communication — DECIDED

Assistant behavior is deterministic database querying, not an LLM. It supports current session conflicts, capacity/availability, workload, faculty and audit questions. Selected context flows from record/session details and the global palette. A room with multiple sessions prompts for the relevant session; it never guesses class context. Room-only alternatives must pass every hard constraint for that session. Queries never write data or publish a proposal.

Audit records include actor, role, timestamp, action, entity, previous/new values, reason and result. Publishing and manual moves create affected-user, notification and email-preparation timeline events. Recipient addresses come from active students, linked faculty users and stored faculty emails. No fabricated fallback mailbox is added. Generated faculty addresses remain unverified and delivery is demo only.

The email adapter creates/edit/schedules drafts and records explicitly simulated delivery statuses. It never sends external email. Scheduled demo processing is an explicit action, not an automated background mail worker. Notifications include all combined cohorts and one faculty notification.

## Verification and implementation status

COMPLETED and verified in this pass:

- Source extraction and provenance; source-backed isolated demo; local MongoDB startup and connection.
- Half-hour/Sunday/session overrides/combined-cohort scheduling and solver.
- Persisted conflicts and revision snapshots; streaming real stages and readiness.
- Existing CRUD/RBAC/authentication, source-email metadata, timetable import validation/preview.
- Approve/publish/what-if/manual override, audit, recipient drafts and notifications.
- Read-only contextual assistant and expanded role-authorized global search.
- Command Center cleanup, timetable updates, assessment reference view, reference hygiene and credential removal from current source.
- Figma Command Center alignment, Registrar-only account creation, four-second startup, no dark mode, one-to-one faculty/module assignments, and non-identifying student planning data across every programme/year.
- The final full suite passed: 43 backend tests against real MongoDB, including protected timetable actions and sanitized database failures. The production frontend build passed. Starlette's test-client integration emits one dependency deprecation warning.
- Browser observations confirmed the authenticated Command Center's actual 83.3% health/one capacity issue, selecting the Friday 06:30 combined-group session, visible source/demo notes, and assistant context. Solver-to-publication is covered by API tests; do not claim every screen was manually tested at every breakpoint.

PARTIAL / IN PROGRESS:

- This is a weekly prototype rather than an institutional production rollout.
- Remaining management/publication routes can be separated further as their scope grows.
- Lists use client-side filtering and bounded API results rather than complete pagination throughout.
- Programme details expose published curriculum and connected operational totals; a full multi-tab departmental workspace remains future work.

NOT YET IMPLEMENTED:

- Full term/holiday recurrence, travel-time constraints, prediction, or a distributed optimization worker.
- Exact examination scheduling editor, seating plans or invigilator optimization.
- CSV/spreadsheet mapping and student bulk editing.
- A historical conflict-trend chart (revision data is stored).
- Live SMTP/email provider, LLM integration, SSO, real-time subscriptions, password recovery, rate limiting and production-hardening.
- A hosted deployment. Docker Compose configuration is provided; the full stack has not been run in this pass.

## Open questions and immediate next steps

OPEN QUESTION: which source routines are current and which terms should users select? What are real group sizes, official staff IDs, faculty limits and confirmed availability? Are generated mailboxes correct? Which unresolved source lecturer/module-code entries should be corrected? What are exact exam dates/venues/invigilators? Which operational role should receive each college user's account?

Next developer: prioritize resolving source ambiguity and explicit calendar/profile selection before merging all routine profiles. Then improve department-specific administration and search pagination. Keep the demo overlay visibly distinct from source facts. Implement optional providers only with explicit configuration and real adapters; never relabel simulated delivery or deterministic querying as external AI/email.

## Setup, environment and Git hygiene

Read README for full commands. Create the Python environment, install backend requirements, run npm ci, configure local credentials through `scripts/configure-local.py`, setup/start MongoDB, then start NEXUS. The restart helper verifies process ownership. Tests use uniquely named isolated databases and drop only those test databases.

Environment variable names only: `MONGODB_URI`, `MONGODB_DATABASE`, `JWT_SECRET`, `NEXUS_ADMIN_EMAIL`, `NEXUS_ADMIN_NAME`, `NEXUS_ADMIN_PASSWORD`, `NEXUS_LOAD_DEMO`, `EMAIL_PROVIDER`, `EMAIL_API_KEY`, `LLM_API_KEY`. Never put secret values here.

The previous shared development password existed in historical commits. Current source removes it and requires local bootstrap configuration. Existing account passwords were not silently changed. Rotate previously shared credentials before exposing the app; do not rewrite repository history without explicit authorization. Raw reference files remain locally available even when removed from tracking. The unused legacy SQLite file remains local as a backup and is never read by the application.
