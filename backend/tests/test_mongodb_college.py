from credentials import TEST_PASSWORD, SECOND_PASSWORD
import json
import pytest
from fastapi.testclient import TestClient
from pymongo.errors import OperationFailure
from app import models as m
from app.db import MongoSession, StorageConflict, get_db
from app.main import app
from app.seed import seed, CATALOG_PATH
from app.scheduling import snapshot,solve,conflicts
from conftest import sign_in

def test_college_bootstrap_is_idempotent_and_has_one_admin(empty_database):
    with MongoSession(empty_database) as db:
        seed(db);seed(db)
        assert len(db.find(m.User))==1
        assert db.first(m.User).role=='Registrar'
        rooms=db.find(m.Room)
        assert len(rooms)==55
        assert sum(r.capacity for r in rooms)==2821
        skill=[r for r in rooms if r.building=='Skill']
        assert len(skill)==16
        assert all(r.kind=='Lab' and r.pc_count==r.capacity for r in skill)
        assert all({'AC','Projector'}<=set(r.equipment) for r in rooms)
        assert len(db.find(m.Programme))==20
        assert not db.find(m.Student)
        assert not db.find(m.TimetableSession)
        assert not db.find(m.Faculty)

def test_registrar_can_create_another_registrar_but_cannot_lock_itself_out(client):
    sign_in(client,'admin')
    response=client.post('/api/data/users',json={'data':{'name':'Second Registrar','email':'SECOND@example.test','role':'Registrar','password':SECOND_PASSWORD},'reason':'Add the second Registrar'})
    assert response.status_code==200,response.text
    response=client.post('/api/auth/login',json={'email':'second@example.test','password':SECOND_PASSWORD})
    assert response.status_code==200
    client.headers['Authorization']='Bearer '+response.json()['token']
    account=response.json()['user']
    assert client.get('/api/data/users').status_code==200
    assert client.put(f'/api/data/users/{account["id"]}',json={'data':{'name':'Second Registrar','email':'SECOND@example.test','role':'Registrar','active':False},'reason':'Try disabling own account'}).status_code==409

def test_last_active_registrar_guard_in_repository(database):
    with MongoSession(database) as db:
        db.get(m.User,1).active=False
        db.get(m.User,2).active=False
        with pytest.raises(StorageConflict,match='Registrar'): db.commit()
    assert database.users.find_one({'id':2})['active'] is True

def test_transaction_rolls_back_partial_work_on_invalid_reference(database):
    with MongoSession(database) as db:
        db.add(m.Room(name='Rollback room',building='Test',capacity=30))
        db.add(m.Student(code='ROLLBACK',name='Test',email='test@example.test',cohort_id=999999))
        with pytest.raises(StorageConflict): db.commit()
    assert database.rooms.count_documents({'name':'Rollback room'})==0
    assert database.students.count_documents({'code':'ROLLBACK'})==0

def test_concurrent_revision_change_cannot_overwrite(database):
    with MongoSession(database) as a, MongoSession(database) as b:
        first=a.get(m.ScheduleVersion,1).revision
        second=b.get(m.ScheduleVersion,1).revision
        a.bump_revision(first);a.commit()
        with pytest.raises((OperationFailure,StorageConflict)):
            b.bump_revision(second);b.commit()
    assert database.schedule_versions.find_one({'id':1})['revision']==first+1

def test_skill_room_rule_is_enforced_when_admin_edits(client):
    sign_in(client,'admin')
    r=client.post('/api/data/rooms',json={'data':{'name':'SKILL-TEST','building':'Skill','capacity':42,'kind':'Classroom','pc_count':0,'equipment':[]},'reason':'Add a Skill Block classroom'})
    assert r.status_code==200,r.text
    room=r.json()
    assert room['kind']=='Lab' and room['pc_count']==42
    assert {'AC','Projector','Computers'}<=set(room['equipment'])

def test_pc_capacity_is_a_hard_constraint(db):
    room=db.get(m.Room,2);room.pc_count=1;db.commit()
    data=snapshot(db)
    assert any(c['kind']=='PC capacity' for c in conflicts(data))
    result=solve(data)
    if result['status']=='Review': assert not conflicts(data,result['assignments'])

def test_new_session_requires_valid_allocation_and_is_audited(client):
    sign_in(client,'admin')
    revision=client.get('/api/workspace').json()['revision']
    bad=client.post('/api/timetable',json={'module_id':1,'room_id':1,'day':0,'start':9,'duration':2,'revision':revision,'reason':'Capacity validation test'})
    assert bad.status_code==409
    good=client.post('/api/timetable',json={'module_id':1,'room_id':2,'day':2,'start':15,'duration':1,'revision':revision,'reason':'Schedule an additional valid class'})
    assert good.status_code==200,good.text
    assert any(r['action']=='SESSION CREATED' for r in client.get('/api/audit').json())

def test_catalogue_does_not_mix_career_examples_with_modules():
    catalog=json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    assert sum(len(p['curriculum']) for p in catalog['programmes'])==280
    for p in catalog['programmes'][15:]:
        assert len(p['curriculum'])==7
        assert p['curriculum'][-1]['name']=='MSc Project'
    # CC7008 is the one public London Met catalogue code verified for the
    # Islington MSc Cyber Threat Intelligence pathway; the remaining PG
    # brochure entries still have no published code.
    assert [c['code'] for p in catalog['programmes'][9:] for c in p['curriculum'] if c['code']] == ['CC7008']
