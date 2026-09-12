"""A reproducible reference-derived demo; never overwrite an established workspace."""
import json
import os
from pathlib import Path
from . import models as m
from .services import audit, bump

OPERATIONS_PATH=Path(__file__).resolve().parents[1]/'data'/'college_operations.json'


def load_reference_demo(db):
    if os.getenv('NEXUS_LOAD_DEMO','true').lower()=='false': return False
    if db.first(m.AuditLog,{'action':'REFERENCE DEMO INITIALIZED'}): return False
    if any(db.first(model) for model in [m.Faculty,m.Module,m.Cohort,m.TimetableSession]): return False
    admin=db.first(m.User,{'role':'Super Admin','active':True})
    if not admin: return False
    data=json.loads(OPERATIONS_PATH.read_text(encoding='utf-8'))
    profile=next(p for p in data['profiles'] if p['id']==data['recommended_demo']['profile_id'])
    programme=db.get(m.Programme,profile['programme_id'])
    if not programme: return False
    faculty={}
    for row in data['faculty']:
        record=m.Faculty(**{k:v for k,v in row.items() if k in m.Faculty.model_fields})
        db.add(record);faculty[row['code']]=record
    cohorts={}
    for name in sorted({c for s in profile['sessions'] for c in s['cohort_names']}):
        obj=m.Cohort(name=name,programme_id=programme.id,size=30,level=profile['level'],source='Routine-4.png',data_status='Demo / derived',notes='Group name from the routine; 30 students is a demo planning assumption, not verified enrolment.')
        db.add(obj);cohorts[name]=obj
    rooms={r.name:r for r in db.find(m.Room)}
    modules={}
    for row in profile['sessions']:
        if row['module_code'] in modules: continue
        entry=next((c for c in programme.curriculum if c['code']==row['catalogue_code']),None)
        obj=m.Module(code=row['module_code'],name=row['module_title'],programme_id=programme.id,faculty_id=faculty[row['faculty_code']].id,cohort_id=cohorts['AI1'].id,credits=entry['credits'] if entry else 15,room_type='Classroom',resources=['Projector'],source='Routine-4.png',data_status='Demo / derived',notes=f"Routine code preserved; catalogue crosswalk: {row['catalogue_code']}. Faculty/cohorts are overridden by each session. Credits {'from programme brochure' if entry else 'assumed 15 for demo; unconfirmed' }.")
        db.add(obj);modules[row['module_code']]=obj
    overlay=None
    for row in profile['sessions']:
        source_room=rooms[row['room_code']]
        room=rooms['LT-05'] if len(row['cohort_names'])==6 else source_room
        notes=f"{profile['term']} reference, row {row['source_row']}. Group sizes are demo assumptions."
        if room.id!=source_room.id:
            notes+=f" DEMO CONFLICT: intentionally moved from {source_room.name} to {room.name}; this is not an error claimed in the college routine."
        resources=['AC','Projector']+(['Computers'] if source_room.pc_count else [])
        obj=m.TimetableSession(module_id=modules[row['module_code']].id,room_id=room.id,faculty_id=faculty[row['faculty_code']].id,cohort_ids=[cohorts[n].id for n in row['cohort_names']],day=row['day'],start=row['start'],duration=row['duration'],session_type=row['session_type'],room_type=source_room.kind,resources=resources,source=row['source'],data_status='Demo / derived',notes=notes,locked=row['source_row']==1,state='locked' if row['source_row']==1 else 'normal')
        db.add(obj)
        if room.id!=source_room.id: overlay={'session_id':obj.id,'reference_room':source_room.name,'demo_room':room.name}
    for row in data['assessment_references']:
        db.add(m.AssessmentReference(reference_id=row['id'],data=row))
    bump(db)
    audit(db,admin,'REFERENCE DEMO INITIALIZED','Reference-derived demonstration',new={'profile':profile['id'],'faculty':len(faculty),'sessions':len(profile['sessions']),'group_size_assumption':30,'intentional_conflict':overlay},reason='Load source-backed routine with clearly labelled demo group sizes and one capacity conflict; no teacher login accounts created.',result='Demo ready')
    db.commit()
    return True
