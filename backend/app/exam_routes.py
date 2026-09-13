"""Audited examination planning with preview and explicit confirmation."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator
from . import models as m
from .schemas import Strict, DeleteAllocation
from .auth import current_user, require
from .db import get_db
from .scheduling import snapshot, serialize, unavailable_at, enriched
from .services import audit, bump, revision

router = APIRouter(prefix="/api/exams")


class VenueAllocation(Strict):
    room_id: int = Field(gt=0)
    invigilator_ids: list[int] = Field(min_length=1, max_length=3)


class ExamInput(Strict):
    module_id: int = Field(gt=0)
    room_id: int = Field(gt=0)
    invigilator_id: int = Field(gt=0)
    room_ids: list[int] = Field(default_factory=list,max_length=20)
    invigilator_ids: list[int] = Field(default_factory=list,max_length=60)
    cohort_ids: list[int] = Field(default_factory=list,max_length=200)
    venue_allocations: list[VenueAllocation] = Field(default_factory=list,max_length=20)
    date: date
    start: float = Field(ge=6.5,le=16.5)
    duration: float = Field(default=2,ge=.5,le=10.5)
    revision: int
    reason: str = Field(default="Exam allocation created",max_length=500)

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


def normalize_exam(item, data):
    item = dict(item)
    module = next((m for m in data['modules'] if m['id'] == item['module_id']), None)
    item['cohort_ids'] = item.get('cohort_ids') or ([module['cohort_id']] if module else [])
    allocations = item.get('venue_allocations') or []
    if not allocations:
        rooms = item.get('room_ids') or [item['room_id']]
        staff = item.get('invigilator_ids') or [item['invigilator_id']]
        allocations = [{'room_id':rid, 'invigilator_ids':staff if len(rooms)==1 else staff[i:i+1]} for i,rid in enumerate(rooms)]
    item['venue_allocations'] = allocations
    item['room_ids'] = [a['room_id'] for a in allocations]
    item['invigilator_ids'] = [fid for a in allocations for fid in a['invigilator_ids']]
    if item['room_ids']: item['room_id'] = item['room_ids'][0]
    if item['invigilator_ids']: item['invigilator_id'] = item['invigilator_ids'][0]
    return item


def issues_for(item, existing, data, capacity_check=True):
    if '_exam_index' not in data:
        data['_exam_index']=({x['id']:x for x in data['modules']},{x['id']:x for x in data['rooms']},{x['id']:x for x in data['faculty']},{x['id']:x for x in data['cohorts']},enriched(data))
    modules, rooms, staff, cohorts, teaching_sessions = data['_exam_index']
    item = normalize_exam(item, data)
    room_ids=item['room_ids']; invigilator_ids=item['invigilator_ids']; cohort_ids=item['cohort_ids']
    if item['module_id'] not in modules or not cohort_ids or any(cid not in cohorts for cid in cohort_ids) or len(set(cohort_ids))!=len(cohort_ids):
        return ['Choose an existing module and unique participating cohorts.']
    if not room_ids or len(set(room_ids))!=len(room_ids) or any(rid not in rooms for rid in room_ids):
        return ['Choose unique existing venues.']
    if any(not 1<=len(a['invigilator_ids'])<=3 for a in item['venue_allocations']) or len(set(invigilator_ids))!=len(invigilator_ids) or any(fid not in staff for fid in invigilator_ids):
        return ['Assign one to three distinct invigilators to every venue; a person cannot cover two rooms simultaneously.']
    result=[]
    if item['start']<7 or item['start']+item['duration']>17: result.append('Exams must run within 07:00–17:00.')
    if any(not rooms[rid]['active'] for rid in room_ids): result.append('Selected venue is inactive.')
    if capacity_check and sum(rooms[rid]['capacity'] for rid in room_ids)<sum(cohorts[cid]['size'] for cid in cohort_ids): result.append('Selected venues do not provide enough combined seats.')
    calendar_day=date.fromisoformat(str(item['date'])).weekday(); day=5 if calendar_day==6 else calendar_day
    if calendar_day==5: result.append('Saturday is outside the college planning week.')
    for resource in [*(rooms[rid] for rid in room_ids),*(staff[fid] for fid in invigilator_ids)]:
        if unavailable_at(resource['unavailable'],day,item['start'],item['duration']): result.append('Room or invigilator is unavailable at this time.')
    for other in existing:
        if other.get('id')==item.get('id') and item.get('id') is not None: continue
        if str(other['date'])!=str(item['date']) or item['start']>=other['start']+other['duration'] or other['start']>=item['start']+item['duration']: continue
        other=normalize_exam(other,data)
        if set(room_ids)&set(other['room_ids']): result.append('Venue clash.')
        if set(invigilator_ids)&set(other['invigilator_ids']): result.append('Invigilator clash.')
        if set(cohort_ids)&set(other['cohort_ids']): result.append('Cohort clash.')
    for teaching in teaching_sessions:
        if teaching['day']!=day or item['start']>=teaching['start']+teaching['duration'] or teaching['start']>=item['start']+item['duration']: continue
        if teaching['room_id'] in room_ids: result.append(f"Venue {teaching['room']} is occupied by a class at this time.")
        if teaching['faculty_id'] in invigilator_ids or set(cohort_ids)&set(teaching['cohort_ids']): result.append('Conflicts with a weekly teaching commitment.')
    return sorted(set(result))


def allocate_venues(item, existing, data):
    """CP-SAT minimizes room count, then empty seats, with distinct staff per room."""
    from ortools.sat.python import cp_model
    item=normalize_exam(item,data)
    demand=sum(c['size'] for c in data['cohorts'] if c['id'] in item['cohort_ids'])
    model=cp_model.CpModel(); choices=[]; staff_use={}
    preferred={a['room_id']:a['invigilator_ids'] for a in item['venue_allocations']}
    for room in sorted(data['rooms'],key=lambda r:r['id']):
        if not room['active']: continue
        candidates=[]
        for person in data['faculty']:
            trial={**item,'venue_allocations':[{'room_id':room['id'],'invigilator_ids':[person['id']]}]}
            if not issues_for(trial,existing,data,capacity_check=False): candidates.append(person['id'])
        if not candidates: continue
        use=model.NewBoolVar(f"room_{room['id']}"); assigned=[]
        count=max(1,len(preferred.get(room['id'],[])))
        for fid in candidates:
            var=model.NewBoolVar(f"room_{room['id']}_staff_{fid}")
            assigned.append((fid,var)); staff_use.setdefault(fid,[]).append(var)
        model.Add(sum(v for _,v in assigned)==count*use)
        choices.append((room,use,assigned))
    if not choices: return None
    for values in staff_use.values(): model.Add(sum(values)<=1)
    model.Add(sum(r['capacity']*v for r,v,_ in choices)>=demand)
    model.Add(sum(v for _,v,_ in choices)<=20)
    # One fewer venue wins over any possible capacity saving.
    multiplier=sum(r['capacity'] for r,_,_ in choices)+1
    model.Minimize(sum((multiplier+r['capacity'])*v for r,v,_ in choices))
    solver=cp_model.CpSolver(); solver.parameters.max_time_in_seconds=3; solver.parameters.num_search_workers=1
    status=solver.Solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return None
    result=normalize_exam({**item,'venue_allocations':[{'room_id':r['id'],'invigilator_ids':[fid for fid,v in people if solver.Value(v)]} for r,use,people in choices if solver.Value(use)]},data)
    return result if not issues_for(result,existing,data) else None


def save_exam(body, db, user, ident=None):
    require(user,['RTE']); check_revision(db,body.revision)
    item=body.model_dump(exclude={'revision','reason'}); item['date']=body.date.isoformat()
    item=normalize_exam(item,snapshot(db))
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


@router.delete('/{ident}')
def delete(ident:int,body:DeleteAllocation,db=Depends(get_db),user=Depends(current_user)):
    require(user,['RTE']); check_revision(db,body.revision)
    obj=db.get(m.ExamSession,ident)
    if not obj: raise HTTPException(404,'Exam not found.')
    previous=serialize(obj)
    db.delete(obj); db.flush(); bump(db,body.revision)
    audit(db,user,'EXAM DELETED',f'Exam {ident}',previous=previous,reason=body.reason)
    db.commit(); return {'deleted':ident}


@router.post('/plan')
def plan(body:PlanInput,db=Depends(get_db),user=Depends(current_user)):
    require(user,['RTE']); check_revision(db,body.revision)
    data=snapshot(db); existing=[serialize(x) for x in db.find(m.ExamSession)]
    modules={x['id']:x for x in data['modules']}; cohorts={x['id']:x for x in data['cohorts']}
    if len(set(body.module_ids)) != len(body.module_ids) or any(x not in modules for x in body.module_ids):
        raise HTTPException(422,'Choose unique existing modules.')
    proposed=[]; unscheduled=[]
    for mid in body.module_ids:
        found=None
        for offset in range(body.days):
            when=body.start_date+timedelta(days=offset)
            if when.weekday()==5: continue
            for start in [8.,10.,13.,15.]:
                if start+body.duration>17: continue
                if not data['rooms'] or not data['faculty']: break
                candidate=dict(module_id=mid,room_id=data['rooms'][0]['id'],invigilator_id=data['faculty'][0]['id'],date=when.isoformat(),start=start,duration=body.duration)
                found=allocate_venues(candidate,existing+proposed,data)
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
    require(user,['RTE']); check_revision(db,body.revision)
    data=snapshot(db); exams=[serialize(x) for x in db.find(m.ExamSession)]; proposed=[]; changes=[]; unresolved=[]
    # Never keep both the old and new booking for an already planned exam.
    ordered=sorted(exams,key=lambda e:(e['date'],e['start'],e['id']))
    for index,original in enumerate(ordered):
        item=allocate_venues(original,proposed+ordered[index+1:],data)
        if item is None:
            unresolved.append(original['id']); item=normalize_exam(original,data)
        before=normalize_exam(original,data)
        if item['venue_allocations']!=before['venue_allocations']:
            changes.append({'id':item['id'],'before':before['room_ids'],'after':item['room_ids'],'allocations':item['venue_allocations']})
        proposed.append(item)
    for item in proposed:
        if issues_for(item,proposed,data) and item['id'] not in unresolved: unresolved.append(item['id'])
    if body.confirm:
        if unresolved: raise HTTPException(409,'Some exams need time or invigilator changes. Edit those allocations first.')
        for item in proposed:
            exam=db.get(m.ExamSession,item['id'])
            for key in ['room_ids','room_id','invigilator_ids','invigilator_id','venue_allocations','cohort_ids']: setattr(exam,key,item[key])
        bump(db,body.revision); audit(db,user,'EXAM VENUES OPTIMIZED','Examinations',new={'changes':changes},reason=body.reason); db.commit()
    return {'changes':changes,'unresolved':unresolved,'saved':body.confirm,'details':[{'id':i['id'],'issues':issues_for(i,proposed,data)} for i in proposed if i['id'] in unresolved]}
