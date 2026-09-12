from pydantic import BaseModel


class TimetableEntry(BaseModel):
    course_id: int
    lecturer_id: int
    room_id: int
    cohort_id: int
    day: str
    start_time: str
    end_time: str