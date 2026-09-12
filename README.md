# NEXUS

**Academic Operations Intelligence · Islington College hackathon prototype**

NEXUS detects academic scheduling conflicts, computes valid alternatives with Google OR-Tools CP-SAT, and lets a registrar review, approve, and publish a timetable. Published changes create audit records, notifications, and email drafts for affected people.

All people, allocations, room capacities, student counts, credentials, and performance metrics are **fictional demo data**. Supplied Islington and ING logos are used unchanged. This project is not connected to institutional systems, SSO, or real email delivery.

## Run locally

Prerequisites: Python 3.11+, Node.js 22+ and npm. Run these commands from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm ci
cd ..
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173**. Interactive API docs: http://127.0.0.1:8000/docs.

On macOS/Linux, use `.venv/bin/python` in place of `.venv\Scripts\python.exe`.

The database initializes and seeds on first startup. Without configuration, a local SQLite `nexus.db` is created in the current working directory. Start from the repository root consistently. To reset the demo, stop the backend, back up or remove only that local database, and restart. Never reset a database containing real records.

## Demo accounts

Every account below uses the development-only password **`NexusDemo!2026`**.

| Email | Role | Primary access |
|---|---|---|
| registrar@nexus.demo | Registrar | Timetable, optimization, approvals, audit, communications |
| admin@nexus.demo | Super Admin | All supported management capabilities |
| admissions@nexus.demo | Admissions | Students, programmes, cohorts |
| hr@nexus.demo | HR Admin | Faculty and availability |
| programme@nexus.demo | Programme Admin | Programmes, modules, cohorts |
| facilities@nexus.demo | Facilities Admin | Rooms and resources |
| faculty@nexus.demo | Faculty | Own teaching schedule and workload |
| student@nexus.demo | Student | Own cohort timetable and notifications |

JWTs expire after eight hours and are stored in session storage. Passwords use salted PBKDF2-SHA256. API authorization is enforced on the server. An unconfigured server generates a random signing key per process; restarting expires sessions. Set `JWT_SECRET` in an ignored `.env` for persistence. This demo is intended for trusted local use, not a public production deployment.

## Architecture

```text
React 19 + TypeScript + Vite + Tailwind v4 + React Router
                    │ HTTP / JSON
                    ▼
                 FastAPI
       ┌────────────┼──────────────┐
       ▼            ▼              ▼
  SQLAlchemy     OR-Tools      Structured assistant
       │          CP-SAT       Database queries
       ▼
 PostgreSQL (Docker) / SQLite (local fallback)
```

The original Figma prompt is a visual reference. Its mock authentication, canned metrics, and simulated optimization are replaced with API operations. Shared UI primitives, institutional tokens, DM Sans/Inter/JetBrains Mono, the NEXUS seal, startup transition, command palette, and contextual assistant preserve its design direction.

## Project structure

```text
frontend/src/
  components/       Shell, brand, dialogs, command palette, assistant
  screens/          Operations, management, intelligence and system screens
  context.tsx       Authenticated workspace and UI state
  api.ts            Axios API boundary and human-readable errors
  types.ts          Frontend data contracts
  index.css         Design tokens, responsive layout, motion
backend/app/
  main.py           HTTP routes and permission boundaries
  models.py         Relational SQLAlchemy models
  schemas.py        Validated request contracts
  scheduling.py     Conflict detection, metrics, CP-SAT and change explanations
  services.py       Audit, revision control, recipient calculation
  auth.py           JWT, password hashing, authorization
  seed.py           Deterministic demo records
backend/tests/      Functional API and scheduling tests
```

## Working features

- Command Center with calculated health, active conflicts, room occupancy and faculty loads.
- Weekly timetable with room/cohort/faculty/module filters, conflict markers, session details, drag-to-preview, audited manual moves and locks.
- Real optimization with before/after metrics, proposed changes and explanations.
- Isolated what-if room closures; publication persists both closure and session changes.
- Review → approve → publish lifecycle, with stale-result rejection using a schedule revision.
- Database-grounded assistant for supported conflict, room, availability, workload and audit questions; no silent mutations.
- Room, faculty, programme, cohort, module, student and user management with server-side role permissions.
- Validated batch JSON import with a dry run and explicit commit.
- Audit timeline and CSV export.
- Affected-cohort notifications, individual email drafts, editable composer, demo delivery and manually processed scheduled demo outbox.
- Computed utilization charts, hard rules, weighted soft preferences, light/dark themes, reduced motion and keyboard command palette.
- Draft examination overview with computed room, invigilator and cohort clash checks.

## Scheduling logic

Each session receives a finite set of eligible room/day/start assignments within Monday–Friday, 09:00–17:00. CP-SAT chooses exactly one assignment per session and permits at most one booking of each room, faculty member and cohort per hour.

Hard constraints enforce room capacity, room type, required equipment, room/faculty availability, and locked allocations. The same independent conflict detector checks the solver's output before it is offered and again before publication. An impossible request returns an infeasibility explanation; a time limit without a solution is reported separately. Solver status distinguishes a feasible result from proven optimality. Search is deterministic with one worker, a fixed seed, and a 12-second limit.

Soft weights prioritize minimizing moved sessions, avoiding first periods, minimizing the number of teaching days per cohort, and limiting faculty hours beyond four per day. A weight of zero disables that preference. The cohort-day measure is a compactness proxy, not an exact minimization of gaps within a day. Fixed teaching assignments mean weekly contact hours cannot decrease through rescheduling alone.

Health is the percentage of sessions without any hard conflict. Utilization counts unique occupied available room-hours divided by available room-hours. Faculty balance is the percentage within weekly target hours. Values are computed, not scripted to match Figma sample percentages. The initial dataset has **24 sessions and 11 hard conflicts**.

## Audit and communication

Important mutations record actor, role, timestamp, entity, previous/new values, reason and result. Schedule publication applies proposed assignments, availability changes, audit entries, notifications and email drafts in one database transaction. A revision compare-and-swap prevents a stale proposal from being published after input changes.

Draft email recipients are derived from active students in affected cohorts and linked faculty users. `example.test` and `nexus.demo` addresses are intentional demo addresses. **Demo delivered** records a simulated delivery; it sends nothing externally. Scheduled messages require a timezone-aware future date and are processed by the explicit **Process due demo emails** action. No background mail worker is claimed.

## Assistant

The assistant routes supported natural-language patterns to live database queries. Contextual session links supply the session identifier. It does not call an LLM or claim LLM reasoning. Room-only suggestions are checked against all hard constraints; if a faculty or cohort clash remains, the assistant directs the user to full optimization. Faculty/student data scopes are enforced. Add a validated provider adapter later if an LLM integration is needed.

## PostgreSQL and Docker

Copy `.env.example` to `.env`. Set a random `JWT_SECRET` and a URL-safe random `POSTGRES_PASSWORD` (at least 32 random bytes each recommended). Do not commit this file.

```powershell
docker compose up --build
```

Compose runs PostgreSQL 16, FastAPI, and the built frontend through Nginx. Open http://127.0.0.1:5173. Database files persist in the `nexus_postgres` volume. For an external PostgreSQL server, set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/nexus` locally. Schema creation is automatic for the prototype; versioned production migrations are not included.

## Verification

```powershell
.venv\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm run build
```

Backend tests use an in-memory database per test. Tests cover authentication, role restrictions, validation, CRUD/audit, real optimization, locks, isolated scenarios, stale proposals, publication, recipient drafts and grounded assistant answers. Browser verification follows the demo walkthrough against the local running application; no separate automated browser runner is included.

## Demo walkthrough

1. Sign in as registrar. Show computed schedule health and active conflicts.
2. Open CS302 in Timetable Studio. Inspect its capacity, room, faculty and cohort problems.
3. Ask NEXUS for the safest alternative. A room-only move cannot fix every initial clash.
4. Run Optimization Lab. Compare actual conflict counts and proposed changes.
5. Enter an approval reason, approve, then publish. Show the conflict-free timetable.
6. Open Audit Log, then Communications. Open a generated email and demonstrate a clearly labelled demo delivery.
7. Simulate Lab 2A being unavailable Thursday. Review or discard the scenario without changing live data, or approve and publish it.
8. Explore rooms, faculty commitments and programme connections.

## Boundaries

- One fictional weekly teaching period; no multi-semester recurrence engine.
- Hour-aligned sessions; no travel-time constraints or cross-campus optimization.
- Examination records are currently a read-only draft overview; no exam generation, seating charts or invigilator optimization.
- Equipment is stored as room attributes; separate inventory quantities/reservations are not modeled.
- Built-in roles have fixed capability sets; users can be assigned roles but custom permission definitions are not supported.
- JSON imports are supported; spreadsheet column mapping is not yet included.
- No real email, SSO, LLM, WebSocket updates, prediction model, or verified institutional data.
- Not production-hardened: no login rate limiting, password recovery, multi-worker key provisioning, distributed jobs or schema migrations.

## Git workflow

The configured upstream is `https://github.com/NormieGit/Hackathon-.git`. Review the diff, run the relevant tests/build, commit coherent changes and push without force. Source, lockfiles, documentation and supplied reference assets belong in Git. Databases, environments, credentials, dependency folders and build output do not.
