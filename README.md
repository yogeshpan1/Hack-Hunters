# NEXUS

Academic Operations Intelligence · Islington College hackathon prototype

NEXUS manages academic resources, detects timetable conflicts, and calculates alternatives with Google OR-Tools CP-SAT. Registrars review, approve, and publish changes with an audit trail. The interface follows the supplied reference screenshots and opens with a five-second introduction (skippable; shortened for reduced motion).

## Run on this Windows PC

Prerequisites: Python 3.11+, Node.js 22+, npm. From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
npm --prefix frontend ci
powershell -ExecutionPolicy Bypass -File scripts/setup-mongodb.ps1
powershell -ExecutionPolicy Bypass -File scripts/start-nexus.ps1
```

Open http://127.0.0.1:5173. API documentation: http://127.0.0.1:8000/docs.

On subsequent runs, use only `scripts/start-nexus.ps1`. It starts MongoDB and the two development servers in hidden windows. Logs are in `%LOCALAPPDATA%\Nexus\logs`. The script reuses occupied ports; check `/api/health` if another application is using port 8000 or 5173.

To start the servers manually after `scripts/start-mongodb.ps1`, run these in separate terminals:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

## Database and accounts

**MongoDB Community 8.0.32**, accessed through **PyMongo**, is the only application database. No PostgreSQL, SQLAlchemy, or SQLite fallback is used. The setup script downloads the official Windows archive, verifies its pinned SHA-256 checksum, and initializes a local single-node replica set named `nexus-rs`. Transactions make publication, revision updates, and audit records atomic.

Default connection: `mongodb://127.0.0.1:27017/?replicaSet=nexus-rs`, database `nexus`. MongoDB listens on localhost. Files persist outside OneDrive at `%LOCALAPPDATA%\Nexus\MongoDB`; the executable is in ignored `tmp/mongodb-runtime`. The existing legacy `nexus.db` is preserved but is no longer read. Old fictional records are not copied into the college workspace.

No MongoDB Atlas, college, Google, or other external account was created. This is a local database server with local application authentication. The bootstrap script creates exactly **one application administrator** when the users collection is empty:

- Email: `admin@nexus.demo`
- Initial local-development password: `NexusDemo!2026`
- Role: **Super Admin**

Sign in, open **Users & Roles**, and choose **Add administrator or user**. Select **Super Admin** to give another person administrator access. Only administrators manage users; the system prevents removing the last active administrator. All additional accounts are explicitly created by an administrator. Public registration is not enabled.

Passwords are salted PBKDF2-SHA256 hashes with 200,000 iterations, never stored as plaintext. JWT sessions expire after eight hours and use a MongoDB-specific issuer, so legacy SQLite session tokens cannot authorize access to the new database. An unconfigured signing key changes on restart. Copy `.env.example` to ignored `.env` to set `JWT_SECRET`, `MONGODB_URI`, `MONGODB_DATABASE`, and bootstrap `NEXUS_ADMIN_NAME`, `NEXUS_ADMIN_EMAIL`, `NEXUS_ADMIN_PASSWORD`. Bootstrap variables apply only before the first initialization; they do not overwrite existing accounts. Replace the development password through the administrator editor before sharing access.

## Your college sources

The first startup loads the versioned `backend/data/college_catalog.json`, derived from:

- `Class Details.csv`: **55 rooms and 2,821 seats**, preserving both the room code and descriptive name.
- `ICK UG Brochure 2026.pdf`: **9 undergraduate programme paths**.
- `ICK PG Brochure.pdf`: **11 postgraduate programme paths**.

The catalogue contains **280 curriculum entries** across 20 programme paths. These are published curricula, not invented current teaching assignments. Programme details show the module names, published codes, periods, credits, and source PDF page. The PG brochure does not supply module codes, so those remain unset. MBA final-semester routes are alternatives. Credits are transcribed as printed, including apparent brochure discrepancies, and require college confirmation before credit audits.

Your equipment instructions are applied: every room has AC and a projector; all **16 Skill Block rooms** are labs, with **510 confirmed PCs** (one per seat), including rooms with TR codes. Impact Block rooms with LAB codes are classified as labs, but their PC counts are unconfirmed and shown accordingly. The solver requires sufficient confirmed PCs when an assignment requires computers.

The live workspace starts without fabricated faculty, cohorts, students, teaching sessions, or exams. Add faculty and cohorts, then create teaching assignments under Modules. Use **Add session** in Timetable Studio to allocate them. Every new session is validated and audited. Programme catalogue entries remain separate from these operational assignments.

To regenerate the catalogue after checking source changes:

```powershell
.venv\Scripts\python.exe -m pip install pymupdf==1.28.2
.venv\Scripts\python.exe scripts/extract-college-data.py
```

Regeneration changes the seed file, not an already initialized database. Existing administrator edits are preserved; subsequent inventory updates require an explicit reviewed import or edit.

## Architecture and features

React 19, TypeScript, Vite, and Tailwind v4 provide the interface. FastAPI handles authentication, validation, and permissions. Pydantic document models and PyMongo provide persistence. OR-Tools CP-SAT calculates timetable alternatives.

- Command Center, daily timetable, resource management, curriculum catalogue, analytics, rules, audit timeline, and examination overview.
- Timetable filters, session creation, audited manual moves, drag-to-preview, and allocation locks.
- Real optimization and isolated what-if room closures with review → approve → publish flow.
- Revision checks reject stale proposals; transactions prevent partial publication.
- Validated JSON batch import with a dry run, CSV audit export, and fixed server-enforced roles.
- Database-grounded assistant for supported scheduling questions; no external LLM is connected.
- Affected-cohort notifications and editable email drafts. Delivery remains explicitly simulated and sends no external email.
- Responsive light/dark themes, keyboard command palette, and reduced-motion support.

Scheduling covers Monday–Friday, 09:00–17:00, in hour-aligned slots. Hard constraints include room capacity, PC capacity, type, equipment, room/faculty availability, overlap, and locks. The independent conflict detector checks solver proposals and publication. Soft weights favor fewer moves, later starts, fewer teaching days per cohort, and limited daily faculty hours. The solver uses one worker, a fixed seed, and a 12-second limit, distinguishing feasible, optimal, infeasible, and timeout results.

Metrics come from stored records. An empty timetable reports zero health rather than claiming a verified schedule. Weekly workload cannot decrease merely by moving fixed teaching assignments.

## Docker alternative

Copy `.env.example` to `.env` and set a strong `JWT_SECRET` and bootstrap administrator password, then:

```powershell
docker compose up --build
```

Compose runs MongoDB 8.0.32 as a single-node replica set, FastAPI, and Nginx serving the built frontend. MongoDB is internal to the Compose network; data persists in `nexus_mongodb`. Open http://127.0.0.1:5173. Stop the local development servers first if using those same ports. The Windows setup scripts are not needed for Docker. An external MongoDB deployment must support replica-set transactions.

## Verification

Start MongoDB, then run:

```powershell
.venv\Scripts\python.exe -m pytest backend/tests -q
npm --prefix frontend run build
```

The 35 backend tests use isolated, uniquely named databases on the real local MongoDB replica set. They cover bootstrap inventory, administrator creation, last-admin protection, references and transaction rollback, concurrent revisions, authentication, permissions, CRUD, scheduling, PC constraints, optimization, publication, and communication drafts. Fictional populated scenarios live only in `backend/tests/demo_seed.py` and are never seeded into the running college workspace.

## Prototype boundaries

One weekly timetable is modeled; multi-semester recurrence and travel time are not. Examinations are a read-only draft overview. Equipment is represented by attributes and a confirmed PC count, without separate equipment reservations. Roles have fixed capability sets. JSON import is supported; spreadsheet column mapping is not. There is no real email, SSO, password recovery, login rate limiting, external LLM, background mail worker, or production migration framework. Brochure data describes published programmes, not verified current enrolment or staffing. The local MongoDB setup is intended for development on a trusted PC.

## Git workflow

Repository: https://github.com/NormieGit/Hackathon-.git. Source, source brochures, reference assets, and lockfiles belong in Git. Database files, environments, secrets, logs, runtime archives, dependency folders, and build output are ignored. Push reviewed commits without force.
