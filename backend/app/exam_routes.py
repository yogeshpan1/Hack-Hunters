"""Audited examination planning with preview and explicit confirmation."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator
from . import models as m
from .schemas import Strict
from .auth import current_user, require
from .db import get_db
from .scheduling import snapshot, serialize, unavailable_at, enriched
from .services import audit, bump, revision

router = APIRouter(prefix="/api/exams")


class ExamInput(Strict):
    module_id: int = Field(gt=0)
    room_id: int = Field(gt=0)
    invigilator_id: int = Field(gt=0)
    date: date
    start: float = Field(ge=6.5,le=16.5)
    duration: float = Field(default=2,ge=.5,le=10.5)
    revision: int
    reason: str = Field(min_length=5,max_length=500)

    @field_validator("start", "duration")
    @classmethod
    def half_hours(cls, value):
        if value * 2 != int(value * 2):
            raise ValueError("Use half-hour increments.")
        return value


class PlanInput(Strict):
    module_ids: list[int] = Field(min_length=1,max_length=200)
    start_date: date
    days: int = Field(default=10,ge=1,le=30)
    duration: float = Field(default=2,ge=.5,le=4)
    revision: int
    confirm: bool = False
    reason: str = Field(min_length=5,max_length=500)
    half_hours = field_validator("duration")(ExamInput.half_hours.__func__)


class VenueInput(Strict):
    revision: int
    confirm: bool = False
    reason: str = Field(min_length=5,max_length=500)


def check_revision(db, expected):
    if revision(db) != expected:
        raise HTTPException(409,"The workspace changed. Preview again before saving.")


def issues_for(item, existing, data):
    if '_exam_index' not in data:
        data['_exam_index']=({x['id']:x for x in data['modules']},{x['id']:x for x in data['rooms']},{x['id']:x for x in data['faculty']},{x['id']:x for x in data['cohorts']},enriched(data))
    modules, rooms, staff, cohorts, teaching_sessions = data['_exam_index']
    mod, room, person = modules.get(item['module_id']), rooms.get(item['room_id']), staff.get(item['invigilator_id'])
    if not mod or not room or not person:
        return ['Choose an existing module, room and invigilator.']
    result = []
    if item['start'] + item['duration'] > 17: result.append('Exam must finish by 17:00.')
    if not room['active'] or room['capacity'] < cohorts[mod['cohort_id']]['size']:
        result.append('Venue is unavailable or has insufficient seats.')
    calendar_day = date.fromisoformat(str(item['date'])).weekday()
    day = 5 if calendar_day == 6 else calendar_day
    if calendar_day == 5: result.append('Saturday is outside the college planning week.')
    for resource in [room,person]:
        if unavailable_at(resource['unavailable'],day,item['start'],item['duration']):
            result.append('Room or invigilator is unavailable at this time.')
    for other in existing:
        if other.get('id') == item.get('id') and item.get('id') is not None: continue
        if str(other['date']) != str(item['date']): continue
        if item['start'] >= other['start'] + other['duration'] or other['start'] >= item['start'] + item['duration']: continue
        if item['room_id'] == other['room_id']: result.append('Venue clash.')
        if item['invigilator_id'] == other['invigilator_id']: result.append('Invigilator clash.')
        if mod['cohort_id'] == modules[other['module_id']]['cohort_id']: result.append('Cohort clash.')
    for teaching in teaching_sessions:
        if teaching['day'] != day or item['start'] >= teaching['start'] + teaching['duration'] or teaching['start'] >= item['start'] + item['duration']: continue
        if item['room_id'] == teaching['room_id'] or item['invigilator_id'] == teaching['faculty_id'] or mod['cohort_id'] in teaching['cohort_ids']:
            result.append('Conflicts with a weekly teaching commitment.')
    return sorted(set(result))


def save_exam(body, db, user, ident=None):
    require(user,['Registrar']); check_revision(db,body.revision)
    item=body.model_dump(exclude={'revision','reason'}); item['date']=body.date.isoformat()
    if ident is not None: item['id']=ident
    obj=db.get(m.ExamSession,ident) if ident is not None else None
    if ident is not None and obj is None: raise HTTPException(404,'Exam not found.')
    issues=issues_for(item,[serialize(x) for x in db.find(m.ExamSession)],snapshot(db))
    if issues: raise HTTPException(409,' '.join(issues))
    previous=serialize(obj) if obj else None
    if obj:
        for key,value in item.items(): setattr(obj,key,value)
    else:
        obj=m.ExamSession(**item); db.add(obj)
    bump(db,body.revision); audit(db,user,'EXAM UPDATED' if previous else 'EXAM CREATED',f'Exam {obj.id}',previous,serialize(obj),body.reason)
    db.commit(); return serialize(obj)


@router.post('')
def create(body:ExamInput,db=Depends(get_db),user=Depends(current_user)):
    return save_exam(body,db,user)


@router.put('/{ident}')
def edit(ident:int,body:ExamInput,db=Depends(get_db),user=Depends(current_user)):
    return save_exam(body,db,user,ident)


@router.post('/plan')
def plan(body:PlanInput,db=Depends(get_db),user=Depends(current_user)):
    require(user,['Registrar']); check_revision(db,body.revision)
    data=snapshot(db); existing=[serialize(x) for x in db.find(m.ExamSession)]
    modules={x['id']:x for x in data['modules']}; cohorts={x['id']:x for x in data['cohorts']}
    if len(set(body.module_ids)) != len(body.module_ids) or any(x not in modules for x in body.module_ids):
        raise HTTPException(422,'Choose unique existing modules.')
    proposed=[]; unscheduled=[]
    for mid in body.module_ids:
        size=cohorts[modules[mid]['cohort_id']]['size']; found=None
        rooms=sorted([r for r in data['rooms'] if r['active'] and r['capacity']>=size],key=lambda r:(r['capacity'],r['id']))
        for offset in range(body.days):
            when=body.start_date+timedelta(days=offset)
            if when.weekday()==5: continue
            for start in [8.,10.,13.,15.]:
                if start+body.duration>17: continue
                for room in rooms:
                    for faculty in data['faculty']:
                        candidate=dict(module_id=mid,room_id=room['id'],invigilator_id=faculty['id'],date=when.isoformat(),start=start,duration=body.duration)
                        if not issues_for(candidate,existing+proposed,data): found=candidate; break
                    if found: break
                if found: break
            if found: break
        if found: proposed.append(found)
        else: unscheduled.append(mid)
    if body.confirm:
        if unscheduled: raise HTTPException(409,'The complete plan does not fit. Extend the date range or reduce the module selection.')
        for item in proposed: db.add(m.ExamSession(**item,source='Registrar-generated exam plan',data_status='Planning draft'))
        bump(db,body.revision); audit(db,user,'EXAM PLAN CREATED','Examinations',new={'exams':len(proposed)},reason=body.reason); db.commit()
    return {'proposed':proposed,'unscheduled':unscheduled,'saved':body.confirm}


@router.post('/venues')
def venues(body:VenueInput,db=Depends(get_db),user=Depends(current_user)):
    require(user,['Registrar']); check_revision(db,body.revision)
    data=snapshot(db); exams=db.find(m.ExamSession); candidates=[serialize(x) for x in exams]; changes=[]
    for item in candidates:
        original=item['room_id']
        for room in sorted(data['rooms'],key=lambda x:(x['capacity'],x['id'])):
            item['room_id']=room['id']
            if not issues_for(item,candidates,data): break
        else: item['room_id']=original
        if item['room_id'] != original: changes.append({'id':item['id'],'before':original,'after':item['room_id']})
    unresolved=[x['id'] for x in candidates if issues_for(x,candidates,data)]
    if body.confirm:
        if unresolved: raise HTTPException(409,'Some exams need time or invigilator changes. Edit those allocations first.')
        for change in changes: db.get(m.ExamSession,change['id']).room_id=change['after']
        bump(db,body.revision); audit(db,user,'EXAM VENUES OPTIMIZED','Examinations',new={'changes':changes},reason=body.reason); db.commit()
    return {'changes':changes,'unresolved':unresolved,'saved':body.confirm}
