from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from .auth import ROLES

class Strict(BaseModel):
    model_config=ConfigDict(extra="forbid", str_strip_whitespace=True)

class Login(Strict):
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

class FacultyInput(Strict):
    name: str=Field(min_length=1,max_length=100)
    code: str=Field(min_length=1,max_length=40)
    department: str=Field(min_length=1,max_length=100)
    email: str=Field(default="",max_length=200)
    email_verified: bool=False
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

class ModuleInput(Strict):
    code: str=Field(min_length=1,max_length=40)
    name: str=Field(min_length=1,max_length=150)
    programme_id: int=Field(gt=0)
    faculty_id: int=Field(gt=0)
    cohort_id: int=Field(gt=0)
    credits: int=Field(default=15,ge=1,le=120)
    room_type: Literal["Classroom","Lab","Studio"]="Classroom"
    resources: list[str]=[]

class StudentInput(Strict):
    code: str=Field(min_length=1,max_length=40)
    name: str=Field(min_length=1,max_length=100)
    email: str=Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    cohort_id: int=Field(gt=0)
    status: Literal["Active","Inactive","Graduated"]="Active"

class UserInput(Strict):
    name: str=Field(min_length=1,max_length=100)
    email: str=Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    role: str
    active: bool=True
    password: str | None=Field(default=None,min_length=10)
    faculty_id: int | None=None
    cohort_id: int | None=None
    @field_validator("role")
    @classmethod
    def role_known(cls,value):
        if value not in ROLES: raise ValueError("Unknown role")
        return value

class RuleInput(Strict):
    weight: int=Field(ge=0,le=100)

class Mutation(Strict):
    data: dict
    reason: str=Field(min_length=5,max_length=500)

class RunInput(Strict):
    room_id: int | None=None
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
    room_type: Literal["Classroom","Lab","Studio"] | None = None
    resources: list[str] | None = None
    session_type: Literal["Teaching","Lecture","Workshop","Tutorial","Lab"] = "Teaching"

class SessionInput(SessionRecord,Reason):
    revision: int

class Question(Strict):
    query: str=Field(min_length=1,max_length=1000)
    context: dict={}

class EmailInput(Strict):
    subject: str=Field(min_length=1,max_length=200)
    body: str=Field(min_length=1,max_length=10000)
    action: Literal["draft","send","schedule"]="draft"
    scheduled_at: str | None=None

class ImportInput(Strict):
    entity: Literal["rooms","faculty","programmes","cohorts","modules","students","sessions"]
    rows: list[dict]=Field(min_length=1,max_length=500)
    confirm: bool=False
