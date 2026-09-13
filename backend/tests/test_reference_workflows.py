import json
from fastapi.testclient import TestClient
from app import models as m
from app.main import app
from app.db import MongoSession,get_db
from app.seed import seed
from app.scheduling import snapshot,enriched,conflicts,solve
from credentials import TEST_PASSWORD
from conftest import sign_in


def test_reference_demo_end_to_end(empty_database,monkeypatch):
    monkeypatch.setenv('NEXUS_LOAD_DEMO','true')
    with MongoSession(empty_database) as db:
        seed(db);seed(db)
        assert len(db.find(m.User))==1
        sourced=[person for person in db.find(m.Faculty) if person.code.startswith('FAC')]
        assert len(sourced)==153
        assignments=[module.faculty_id for module in db.find(m.Module)]
        assert len(assignments)==len(set(assignments))
        assert len(db.find(m.Student))>=276
        sessions=db.find(m.TimetableSession)
        generated=[session for session in sessions if session.source=="Full catalogue planning allocation"]
        assert generated
        assert len(sessions)>250
        assert {module.id for module in db.find(m.Module)} <= {session.module_id for session in sessions}
        assert {person.id for person in db.find(m.Faculty)} <= {session.faculty_id for session in sessions}
        assert {cohort.id for cohort in db.find(m.Cohort)} <= {cohort_id for session in sessions for cohort_id in session.cohort_ids}
        assert len(db.find(m.AssessmentReference))==25
        data=snapshot(db)
        assert len(conflicts(data))==1
        assert conflicts(data)[0]['kind']=='Capacity'
        assert any(s['day']==5 for s in enriched(data))
        assert any(s['start']==6.5 for s in enriched(data))
        assert max(s['size'] for s in enriched(data))>=180
        assert db.database.conflicts.count_documents({'revision':2})==1
    def request_db():
        with MongoSession(empty_database) as db: yield db
    app.dependency_overrides[get_db]=request_db
    try:
        client=TestClient(app)
        login=client.post('/api/auth/login',json={'email':'admin@example.test','password':TEST_PASSWORD})
        assert login.status_code==200
        client.headers['Authorization']='Bearer '+login.json()['token']
        assert client.get('/api/readiness').json()['ready']
        events=[json.loads(line) for line in client.post('/api/optimization/stream',json={}).text.splitlines()]
        assert any(e.get('stage')=='search' for e in events)
        run=events[-1]['run']
        assert run['status']=='Review' and run['after']['conflicts']==0
        assert len(client.get('/api/conflicts').json())==1
        reason={'reason':'Resolve the explicitly labelled demo capacity disruption'}
        for action in ['approve','publish']:
            response=client.post(f"/api/optimization/{run['id']}/{action}",json=reason)
            assert response.status_code==200,response.text
        assert client.get('/api/conflicts').json()==[]
        assert client.get('/api/emails').json()
        assert client.get('/api/notifications').json()
        assert all('example.test' not in e['recipient'] for e in client.get('/api/emails').json())
        with MongoSession(empty_database) as db:
            current_revision=db.first(m.ScheduleVersion).revision
            assert db.first(m.ConflictSnapshot,{'revision':current_revision}).conflict_count==0
            assert any(s.conflict_count==1 for s in db.find(m.ConflictSnapshot))
    finally: app.dependency_overrides.clear()


def test_half_hour_overlap_and_combined_cohort_detection(db):
    a=db.get(m.TimetableSession,6);b=db.get(m.TimetableSession,8)
    a.day=5;a.start=6.5;a.duration=1.5;a.cohort_ids=[5,7]
    b.day=5;b.start=7.5;b.duration=1;b.cohort_ids=[7]
    db.commit()
    assert any(c['kind']=='Cohort overlap' and set(c['session_ids'])=={6,8} for c in conflicts(snapshot(db)))


def test_assistant_accommodate_and_restricted_search(client):
    sign_in(client,'registrar')
    response=client.post('/api/assistant',json={'query':'Which room can accommodate 45 students?'}).json()
    assert any('Lab 4B' in item for item in response['items'])
    sign_in(client,'facilities')
    assert not any(r['entity']=='students' for r in client.get('/api/search?q=Demo%20student').json())


def test_empty_readiness_does_not_fake_solver_success(empty_database):
    from app.optimizer_routes import readiness
    with MongoSession(empty_database) as db:
        seed(db)
        assert not readiness(snapshot(db))['ready']


def test_generic_session_routes_preserve_scope_and_locks(client):
    sign_in(client,'student')
    assert all(1 in s['cohort_ids'] for s in client.get('/api/data/sessions').json())
    sign_in(client,'registrar')
    assert client.put('/api/data/sessions/4',json={'data':{},'reason':'Attempt to bypass locked timetable workflow'}).status_code==403


def test_database_error_response_never_exposes_connection_details(client,monkeypatch):
    from pymongo.errors import ConnectionFailure
    def failed_ping(self): raise ConnectionFailure('Sensitive connection configuration must not be returned')
    monkeypatch.setattr(MongoSession,'ping',failed_ping)
    response=client.get('/api/health')
    assert response.status_code==503
    assert 'Sensitive' not in response.text
