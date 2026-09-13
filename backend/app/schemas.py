import re
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from .auth import ROLES

class Strict(BaseModel):
    model_config=ConfigDict(extra="forbid", str_strip_whitespace=True)

class EmailRecord(Strict):
    @field_validator("email",check_fields=False)
    @classmethod
    def normalize_email(cls,value): return value.strip().lower()

class Login(EmailRecord):
    email: str
    password: str

class RoomInput(Strict):
    name: str = Field(min_length=1,max_length=100)
    building: str = Field(min_length=1,max_length=100)
    display_name: str = Field(default="",max_length=150)
    pc_count: int = Field(default=0,ge=0,le=1000)
    capacity: int = Field(ge=1,le=1000)
    kind: Literal["Classroom","Lab","Studio"]="Classroom"
    equipment: list[str]=[]
    unavailable: list[str]=[]
    active: bool=True
    @field_validator("unavailable")
    @classmethod
    def slots(cls,values):
        for value in values:
            try:
                day,hour=value.split(":"); day=int(day);hour=float(hour)
                valid=0<=day<=5 and 6.5<=hour<17 and hour*2==int(hour*2)
            except (ValueError,TypeError): valid=False
            if not valid: raise ValueError("Availability must use day:hour on half-hours, e.g. 5:6.5 (Sunday 06:30).")
        return values

class FacultyInput(EmailRecord):
    name: str=Field(min_length=1,max_length=100)
    code: str=Field(min_length=1,max_length=40)
    department: str=Field(min_length=1,max_length=100)
    email: str=Field(default="",max_length=200,pattern=r"^$|^[^\s@]+@[^\s@]+\.[^\s@]+$")
    email_verified: bool=False
    attends_masters: bool=False
    max_hours: int=Field(default=18,ge=1,le=40)
    unavailable: list[str]=[]
    slots=field_validator("unavailable")(RoomInput.slots.__func__)

class ProgrammeInput(Strict):
    name: str=Field(min_length=1,max_length=150)
    department: str=Field(min_length=1,max_length=100)

class CohortInput(Strict):
    name: str=Field(min_length=1,max_length=100)
    programme_id: int=Field(gt=0)
    size: int=Field(ge=1,le=1000)
    level: int=Field(default=5,ge=3,le=8)
    study_level: Literal["First Year","Second Year","Third Year","Masters"] = "Second Year"

class ModuleInput(Strict):
    code: str=Field(min_length=1,max_length=40)
    name: str=Field(min_length=1,max_length=150)
    programme_id: int=Field(gt=0)
    faculty_id: int=Field(gt=0)
    cohort_id: int=Field(gt=0)
    credits: int=Field(default=15,ge=1,le=120)
    room_type: Literal["Classroom","Lab","Studio"]="Classroom"
    resources: list[str]=[]

class StudentInput(EmailRecord):
    code: str=Field(min_length=1,max_length=40)
    name: str=Field(min_length=1,max_length=100)
    email: str=Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    cohort_id: int=Field(gt=0)
    status: Literal["Active","Inactive","Graduated"]="Active"

class UserInput(EmailRecord):
    name: str=Field(min_length=1,max_length=100)
    email: str=Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    role: str
    active: bool=True
    password: str | None=Field(default=None,min_length=4,max_length=256)
    @field_validator("role")
    @classmethod
    def role_known(cls,value):
        if value not in ROLES: raise ValueError("Unknown role")
        return value

class RuleInput(Strict):
    weight: int=Field(ge=0,le=100)

class Mutation(Strict):
    data: dict
    reason: str=Field(default="Record maintenance",max_length=500)

class RunInput(Strict):
    strategy: Literal['balanced','rooms','faculty']='balanced'
    scenario_kind: Literal['room','faculty']='room'
    room_id: int | None=None
    faculty_id: int | None=None
    day: int | None=Field(default=None,ge=0,le=5)

class Reason(Strict):
    reason: str=Field(min_length=5,max_length=500)

class Move(Reason):
    room_id: int=Field(gt=0)
    day: int=Field(ge=0,le=5)
    start: float=Field(ge=6.5,le=16.5,multiple_of=.5)
    revision: int
    confirm: bool=False

class Lock(Reason):
    locked: bool
    revision: int

class SessionRecord(Strict):
    module_id: int = Field(gt=0)
    room_id: int = Field(gt=0)
    day: int = Field(ge=0,le=5)
    start: float = Field(ge=6.5,le=16.5,multiple_of=.5)
    duration: float = Field(default=2,ge=.5,le=10.5,multiple_of=.5)
    faculty_id: int | None = Field(default=None,gt=0)
    cohort_ids: list[int] = []
    planned_size: int | None = Field(default=None,ge=1)
    section_label: str = Field(default="",max_length=80)
    week_pattern: Literal["Weekly","A Week","B Week"] = "Weekly"
    room_type: Literal["Classroom","Lab","Studio"] | None = None
    resources: list[str] | None = None
    session_type: Literal["Teaching","Lecture","Workshop","Tutorial","Lab"] = "Teaching"

class SessionInput(SessionRecord):
    revision: int
    reason: str=Field(default="Session created",max_length=500)

class DeleteRecord(Strict):
    reason: str=Field(default="Record deleted",max_length=500)

class DeleteAllocation(DeleteRecord):
    revision: int

class Question(Strict):
    query: str=Field(min_length=1,max_length=1000)
    context: dict={}
    history: list[str]=Field(default_factory=list,max_length=6)

    @field_validator("history")
    @classmethod
    def bounded_history(cls, values):
        if any(len(v)>1000 for v in values): raise ValueError("History question is too long")
        return values

class EmailInput(Strict):
    subject: str=Field(min_length=1,max_length=200)
    body: str=Field(min_length=1,max_length=10000)
    action: Literal["draft","send","schedule"]="draft"
    scheduled_at: str | None=None

class RecipientMessage(Strict):
    cohort_id: int | None = Field(default=None,gt=0)
    student_ids: list[int] = Field(default_factory=list,max_length=1000)
    custom_recipients: list[str] = Field(default_factory=list,max_length=1000)
    subject: str = Field(min_length=1,max_length=200)
    body: str = Field(min_length=1,max_length=10000)

    @field_validator("custom_recipients")
    @classmethod
    def custom_email_addresses(cls, values):
        normalized=[]
        for value in values:
            email=value.strip().lower()
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):
                raise ValueError("Each custom recipient must be a valid email address.")
            if email not in normalized:
                normalized.append(email)
        return normalized
