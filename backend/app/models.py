from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def now():
    return datetime.now(timezone.utc).isoformat()

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str]
    role: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"), nullable=True)
    cohort_id: Mapped[int | None] = mapped_column(ForeignKey("cohorts.id"), nullable=True)

class Programme(Base):
    __tablename__ = "programmes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    department: Mapped[str] = mapped_column(default="Computing")

class Faculty(Base):
    __tablename__ = "faculty"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    code: Mapped[str] = mapped_column(unique=True)
    department: Mapped[str]
    max_hours: Mapped[int] = mapped_column(default=18)
    unavailable: Mapped[list] = mapped_column(JSON, default=list)

class Cohort(Base):
    __tablename__ = "cohorts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    programme_id: Mapped[int] = mapped_column(ForeignKey("programmes.id"))
    size: Mapped[int]
    level: Mapped[int] = mapped_column(default=5)

class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    email: Mapped[str]
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohorts.id"))
    status: Mapped[str] = mapped_column(default="Active")

class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    building: Mapped[str]
    capacity: Mapped[int]
    kind: Mapped[str] = mapped_column(default="Classroom")
    equipment: Mapped[list] = mapped_column(JSON, default=list)
    unavailable: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(default=True)

class Module(Base):
    __tablename__ = "modules"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    programme_id: Mapped[int] = mapped_column(ForeignKey("programmes.id"))
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"))
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohorts.id"))
    credits: Mapped[int] = mapped_column(default=15)
    room_type: Mapped[str] = mapped_column(default="Classroom")
    resources: Mapped[list] = mapped_column(JSON, default=list)

class TimetableSession(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    day: Mapped[int]
    start: Mapped[int]
    duration: Mapped[int] = mapped_column(default=2)
    locked: Mapped[bool] = mapped_column(default=False)
    state: Mapped[str] = mapped_column(default="normal")

class ExamSession(Base):
    __tablename__ = "exams"
    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    invigilator_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"))
    date: Mapped[str]
    start: Mapped[int]
    duration: Mapped[int] = mapped_column(default=2)
    status: Mapped[str] = mapped_column(default="Draft")

class Rule(Base):
    __tablename__ = "rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    kind: Mapped[str]
    weight: Mapped[int] = mapped_column(default=1)

class ScheduleVersion(Base):
    __tablename__ = "schedule_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    revision: Mapped[int] = mapped_column(default=1)

class OptimizationRun(Base):
    __tablename__ = "optimization_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[str] = mapped_column(default=now)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str]
    kind: Mapped[str] = mapped_column(default="optimization")
    revision: Mapped[int]
    before: Mapped[dict] = mapped_column(JSON)
    after: Mapped[dict] = mapped_column(JSON)
    assignments: Mapped[list] = mapped_column(JSON)
    changes: Mapped[list] = mapped_column(JSON)
    scenario: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[str] = mapped_column(default=now)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    actor: Mapped[str]
    role: Mapped[str]
    action: Mapped[str]
    entity: Mapped[str]
    previous: Mapped[dict] = mapped_column(JSON, default=dict)
    new: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str]
    result: Mapped[str] = mapped_column(default="Recorded")

class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("optimization_runs.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    timestamp: Mapped[str] = mapped_column(default=now)
    reason: Mapped[str]

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cohort_id: Mapped[int | None] = mapped_column(ForeignKey("cohorts.id"), nullable=True)
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"), nullable=True)
    title: Mapped[str]
    body: Mapped[str]
    timestamp: Mapped[str] = mapped_column(default=now)

class Email(Base):
    __tablename__ = "emails"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient: Mapped[str]
    subject: Mapped[str]
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(default="Draft")
    timestamp: Mapped[str] = mapped_column(default=now)
    scheduled_at: Mapped[str | None] = mapped_column(nullable=True)
