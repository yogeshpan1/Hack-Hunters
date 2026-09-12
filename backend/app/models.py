from datetime import datetime, timezone
from typing import ClassVar
from pydantic import BaseModel, ConfigDict, Field

def now():
    return datetime.now(timezone.utc).isoformat()

class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")
    collection: ClassVar[str]
    id: int | None = None


class User(Document):
    collection: ClassVar[str] = "users"
    name: str
    email: str
    password_hash: str
    role: str
    active: bool = True
    faculty_id: int | None = None
    cohort_id: int | None = None

class Programme(Document):
    collection: ClassVar[str] = "programmes"
    name: str
    department: str = "Computing"
    award: str = ""
    level: str = "Undergraduate"
    specialization: str = ""
    curriculum: list = Field(default_factory=list)
    source: str = ""

class Faculty(Document):
    collection: ClassVar[str] = "faculty"
    name: str
    code: str
    department: str
    max_hours: int = 18
    unavailable: list = Field(default_factory=list)

class Cohort(Document):
    collection: ClassVar[str] = "cohorts"
    name: str
    programme_id: int
    size: int
    level: int = 5

class Student(Document):
    collection: ClassVar[str] = "students"
    code: str
    name: str
    email: str
    cohort_id: int
    status: str = "Active"

class Room(Document):
    collection: ClassVar[str] = "rooms"
    name: str
    building: str
    display_name: str = ""
    pc_count: int = 0
    source: str = ""
    capacity: int
    kind: str = "Classroom"
    equipment: list = Field(default_factory=list)
    unavailable: list = Field(default_factory=list)
    active: bool = True

class Module(Document):
    collection: ClassVar[str] = "modules"
    code: str
    name: str
    programme_id: int
    faculty_id: int
    cohort_id: int
    credits: int = 15
    room_type: str = "Classroom"
    resources: list = Field(default_factory=list)

class TimetableSession(Document):
    collection: ClassVar[str] = "sessions"
    module_id: int
    room_id: int
    day: int
    start: int
    duration: int = 2
    locked: bool = False
    state: str = "normal"

class ExamSession(Document):
    collection: ClassVar[str] = "exams"
    module_id: int
    room_id: int
    invigilator_id: int
    date: str
    start: int
    duration: int = 2
    status: str = "Draft"

class Rule(Document):
    collection: ClassVar[str] = "rules"
    name: str
    kind: str
    weight: int = 1

class ScheduleVersion(Document):
    collection: ClassVar[str] = "schedule_versions"
    revision: int = 1

class OptimizationRun(Document):
    collection: ClassVar[str] = "optimization_runs"
    created_at: str = Field(default_factory=now)
    user_id: int
    status: str
    kind: str = "optimization"
    revision: int
    before: dict
    after: dict
    assignments: list
    changes: list
    scenario: dict = Field(default_factory=dict)
    explanation: str

class AuditLog(Document):
    collection: ClassVar[str] = "audit_logs"
    timestamp: str = Field(default_factory=now)
    user_id: int
    actor: str
    role: str
    action: str
    entity: str
    previous: dict = Field(default_factory=dict)
    new: dict = Field(default_factory=dict)
    reason: str
    result: str = "Recorded"

class Approval(Document):
    collection: ClassVar[str] = "approvals"
    run_id: int
    user_id: int
    timestamp: str = Field(default_factory=now)
    reason: str

class Notification(Document):
    collection: ClassVar[str] = "notifications"
    user_id: int | None = None
    cohort_id: int | None = None
    faculty_id: int | None = None
    title: str
    body: str
    timestamp: str = Field(default_factory=now)

class Email(Document):
    collection: ClassVar[str] = "emails"
    recipient: str
    subject: str
    body: str
    status: str = "Draft"
    timestamp: str = Field(default_factory=now)
    scheduled_at: str | None = None
