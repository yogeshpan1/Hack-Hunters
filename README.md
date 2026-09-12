# NEXUS

Academic Operations Intelligence for Islington College · ING ecosystem

NEXUS helps academic teams identify timetable conflicts, calculate valid alternatives, review the impact, approve a change, and publish it with an audit trail and communication drafts. The hackathon demonstration focuses on this complete operational loop.

## Start locally

Prerequisites: Python 3.11+, Node.js 22+, npm. Run from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
npm --prefix frontend ci
.venv\Scripts\python.exe scripts/configure-local.py
powershell -ExecutionPolicy Bypass -File scripts/setup-mongodb.ps1
powershell -ExecutionPolicy Bypass -File scripts/start-nexus.ps1
```

The configuration command asks for the initial administrator credentials using hidden password input and writes only to ignored `.env`. There is **no hard-coded default password**. Existing database accounts are preserved and are not changed by re-running setup. Existing users can change their password through the administrator's Users & Roles editor.

Open http://127.0.0.1:5173. API docs: http://127.0.0.1:8000/docs. Later launches only need `scripts/start-nexus.ps1`. After backend code changes use `scripts/restart-nexus.ps1`; it verifies the process belongs to this project's virtual environment before stopping it. Servers run in hidden windows; logs are in `%LOCALAPPDATA%\Nexus\logs`.

Manual development servers, in separate terminals after MongoDB starts:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

## MongoDB and configuration

MongoDB Community 8.0.32 with PyMongo is the only application database. The Windows installer verifies the vendor archive checksum and initializes a local replica set, `nexus-rs`, for transactions. The local connection defaults to localhost, port 27017, database `nexus`; files are in `%LOCALAPPDATA%\Nexus\MongoDB`, outside OneDrive. The downloaded runtime is ignored under `tmp`. No Atlas or external service account is created. A hosted deployment can use a replica-set MongoDB Atlas connection through environment configuration.

`.env.example` contains empty placeholders. Environment variable names:

| Variable | Purpose |
| --- | --- |
| `MONGODB_URI`, `MONGODB_DATABASE` | Database connection and name; blank values use local defaults |
| `JWT_SECRET` | Persistent session signing key; if unset a random process-local key expires sessions on restart |
| `NEXUS_ADMIN_EMAIL`, `NEXUS_ADMIN_NAME`, `NEXUS_ADMIN_PASSWORD` | Bootstrap exactly one administrator in an empty database |
| `NEXUS_LOAD_DEMO` | Set `false` to skip the reference-derived operational demo |
| `EMAIL_PROVIDER` | Shipped communication adapter is demo only |
| `EMAIL_API_KEY`, `LLM_API_KEY` | Reserved optional-adapter placeholders; no provider integration is currently implemented |

Keep actual values out of source, documentation, screenshots, and logs. Never commit `.env`. An earlier development commit contained a shared demo password; it has been removed from the current source, but historical commits are preserved. Rotate any account that still uses a previously shared development password before sharing access. The legacy local `nexus.db` is untouched and is no longer used.

## Reference data and reliable demo

The application runs from versioned structured JSON in `backend/data`; raw references remain local in **College Details Assets** and **UI Reference images**, both ignored. Official runtime logos are preserved unchanged in `frontend/public`.

- 55 rooms, 2,821 seats, 20 programme paths and 280 published curriculum entries.
- All rooms have AC/projector. The 16 Skill Block rooms have 510 confirmed PCs, one per seat. Other unconfirmed PC counts remain explicitly unknown.
- 153 faculty names, with derived institutional email addresses marked unverified. These records do not create login accounts.
- Seven separately preserved routine profiles containing 60 source rows; different terms are not silently merged.
- 25 historical assessment components. Published deadlines/windows appear separately from exam allocations; missing exact times, venues and invigilators remain unknown.

On a workspace with no operational faculty, modules, cohorts or timetable, startup loads the coherent Autumn 2026 AI1 reference profile: six sessions, six named groups, three modules. **Thirty students per group is a demonstration assumption.** One 180-person combined lecture is intentionally moved from its reference hall to the 100-seat LT-05 to create a labelled capacity disruption. A workshop is locked to demonstrate preservation of fixed allocations. This does not claim the original college routine has an error.

Seeding is transactional, audited, and idempotent. Existing operational edits prevent automatic demo loading. Set `NEXUS_LOAD_DEMO=false` before first startup for an empty planning workspace. No fake student roster or teacher login accounts are created in the live demo. Populated fictional test fixtures exist only under `backend/tests` and use generated ephemeral passwords.

See [data provenance](docs/DATA_PROVENANCE.md) for source rows, programme code differences, unresolved lecturer names, inferred emails, and assessment limitations. To regenerate extraction artifacts when the local references change:

```powershell
.venv\Scripts\python.exe -m pip install pymupdf==1.28.2
.venv\Scripts\python.exe scripts/extract-college-data.py
.venv\Scripts\python.exe scripts/extract-operations-data.py
```

Regeneration does not overwrite an already initialized database.

## Demonstrate the core workflow

1. Sign in with the administrator account configured locally.
2. Command Center shows the labelled capacity conflict. Open it in Timetable Studio.
3. Ask NEXUS why the selected session conflicts and review available alternatives.
4. Run Optimization Lab. Real streamed stages cover constraints, capacity/resources, availability, overlap constraints, CP-SAT search, and independent validation.
5. Compare actual before/after metrics and proposed moves. The live timetable remains unchanged.
6. Enter a decision reason, approve, then publish. Publication rechecks the schedule revision and all hard constraints.
7. Review the audit timeline, affected-cohort notifications, and faculty email drafts. Demo send is explicitly simulated and never contacts an email provider.
8. Use What-If Simulator to close a room for a weekday. Its closure and proposed allocations remain isolated until approved publication.

## Features and roles

The interface follows the supplied Figma hierarchy: a health KPI strip, Schedule Intelligence, ranked improvements and weekly operational load. The untouched crest appears in the NEXUS seal, login and shell. The introduction lasts four seconds, is skippable, and ends immediately for reduced motion. Keyboard command search and contextual assistance preserve selected session/record context. Dark mode is not included.

The only role available when creating an internal account is Registrar. Existing legacy `Super Admin` accounts migrate to Registrar on startup, so the original administrator remains usable. The last active Registrar cannot be removed, and a Registrar cannot disable their own account. Public registration is not implemented.

Supported management includes rooms, faculty, programmes, teaching modules, cohorts, students, and internal users. JSON import provides upload/edit, validation, structured row preview and confirmation for rooms, faculty, programmes, cohorts, modules, students and timetable sessions. Invalid fields/references do not enter the database. Imported timetable clashes are retained as visible, persisted conflicts for review. Global search covers academic records and role-authorized student, exam and audit data.

## Architecture and scheduling

React 19 + TypeScript + Vite + Tailwind v4 + Lucide + Recharts + Axios → FastAPI/Pydantic → PyMongo/MongoDB. OR-Tools CP-SAT performs real scheduling; the assistant uses deterministic database queries without an external LLM.

`backend/app/db.py` isolates the document repository, identity cache, references, indexes and transactions. Models are separate from request schemas. `scheduling.py` contains an independent conflict detector, metrics and solver. `optimization_service.py` saves proposals; `optimizer_routes.py` streams real stages and checks readiness. `intelligence_routes.py` handles search and assistant queries. `services.py` handles audit, revision and communication creation. `main.py` assembles the API and remaining management/publication routes.

Integer document IDs preserve API compatibility. Collections represent independently queried records; curriculum, availability, proposal changes and source-assessment details are embedded where read together. Session faculty, combined-cohort membership and room/resource requirements can override module defaults, so lectures and workshops can share a module without false clashes.

Days retain Monday=0 through Friday=4, with Sunday=5. The UI displays Sunday first. Public times use half-hour numeric values; CP-SAT uses integer half-hour ticks over 06:30–17:00. Hard constraints cover room/faculty/combined-cohort overlap, room/PC capacity, type/equipment, availability, teaching hours and locks. Legacy integer availability entries reserve a full hour; `.5` entries reserve half an hour.

Soft weights minimize disruption, discourage first periods, compact cohort teaching days, and reduce daily faculty overload. Weekly teaching totals do not change merely through rescheduling. Room type stays a hard requirement. The solver uses one worker, a fixed seed and a 12-second limit, distinguishing feasible/optimal, infeasible, and timeout results.

Academic mutations persist conflict records and revision snapshots in the same transaction. Publication atomically updates allocations, room closures, audit, notifications and email drafts. Compare-and-swap revision checks reject stale proposals. The assistant never mutates live data; room-only suggestions are independently checked, and ambiguous room context asks for a session rather than guessing.

## Docker alternative

Configure `.env` locally, then run `docker compose up --build`. Compose runs MongoDB with a replica set, FastAPI, and Nginx serving the production frontend. MongoDB is internal to the Compose network; data persists in its named volume. Stop local development servers first if using the same ports. The Docker configuration is validated, but the complete Docker stack has not been exercised in this implementation pass.

## Tests and current limits

```powershell
.venv\Scripts\python.exe -m pytest backend/tests -q
npm --prefix frontend run build
```

The test suite runs against isolated databases on real MongoDB. Coverage includes authentication, Registrar-only account creation, normalized email sign-in, management and import validation, transactional rollback, stale revisions, combined-cohort overlaps, half-hour sessions, PC capacity, locked sessions, infeasibility, what-if, streaming progress, source-demo bootstrap, publication, persisted conflict history, audit, notifications, demo email drafts, protected timetable actions, and sanitized database failures. The production frontend build also passes. A dependency deprecation warning remains in Starlette's test-client integration.

Known boundaries: weekly recurrence only, no full academic calendar/holiday engine; exact exam scheduling and seating/invigilator optimization are not implemented; exam allocations remain read-only. Assessment references do not substitute for confirmed schedules. Student bulk editing and CSV column-mapping are not available. Some lists use bounded result sets/client filtering rather than server pagination. Conflict history is stored but a historical trend chart is not yet exposed. No external LLM, email delivery, SSO, prediction engine, password recovery, login rate limiting or distributed solver worker is included. Production authentication and database hardening remain deployment work.

## Repository and handoff

Repository: https://github.com/NormieGit/Hackathon-.git. Keep runtime source/assets, extracted data, tests, lockfiles and documentation in Git. Reference PDFs/images, dependencies, caches, builds, archives, logs and secrets remain ignored. Existing history is not rewritten or force-pushed. Read [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) before continuing development and keep it current after architectural decisions.
