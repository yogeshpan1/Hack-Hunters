from conftest import sign_in
from app.student_roster import student_email


def test_routine_record_changes_without_reason_are_named_in_audit(registrar):
    body={"data":{"name":"Temporary programme","department":"Computing"}}
    response=registrar.post('/api/data/programmes',json=body)
    assert response.status_code==200,response.text
    ident=response.json()['id']
    assert registrar.put(f'/api/data/programmes/{ident}',json={"data":{**body['data'],"name":"Updated programme"}}).status_code==200
    assert registrar.request('DELETE',f'/api/data/programmes/{ident}',json={}).status_code==200
    logs=[r for r in registrar.get('/api/audit').json() if r['entity']==f'programmes/{ident}']
    assert {r['action'] for r in logs}=={'CREATE','UPDATE','DELETE'}
    assert all(r['actor'] and r['user_id'] and r['reason'] for r in logs)


def test_session_delete_checks_revision_lock_and_updates_conflicts(registrar):
    w=registrar.get('/api/workspace').json()
    locked=next(s for s in w['sessions'] if s['locked'])
    assert registrar.request('DELETE',f"/api/timetable/{locked['id']}",json={'revision':w['revision']}).status_code==409
    session=next(s for s in w['sessions'] if not s['locked'])
    url=f"/api/timetable/{session['id']}"
    assert registrar.request('DELETE',url,json={'revision':w['revision']-1}).status_code==409
    assert registrar.request('DELETE',url,json={'revision':w['revision']}).status_code==200
    after=registrar.get('/api/workspace').json()
    assert after['revision']==w['revision']+1
    assert all(s['id']!=session['id'] for s in after['sessions'])
    assert all(session['id'] not in c['session_ids'] for c in after['conflicts'])
    log=next(r for r in registrar.get('/api/audit').json() if r['action']=='SESSION DELETED')
    assert log['actor'] and log['previous']['id']==session['id']


def test_exam_create_and_delete_without_reason(registrar):
    revision=registrar.get('/api/workspace').json()['revision']
    plan=registrar.post('/api/exams/plan',json={'module_ids':[1],'start_date':'2026-10-04','days':7,'duration':2,'revision':revision,'reason':'Review examination plan'}).json()
    response=registrar.post('/api/exams',json={**plan['proposed'][0],'revision':revision})
    assert response.status_code==200,response.text
    ident=response.json()['id']
    assert registrar.request('DELETE',f'/api/exams/{ident}',json={'revision':revision}).status_code==409
    assert registrar.request('DELETE',f'/api/exams/{ident}',json={'revision':revision+1}).status_code==200
    assert all(x['id']!=ident for x in registrar.get('/api/exams').json())
    assert any(x['action']=='EXAM DELETED' and x['actor'] for x in registrar.get('/api/audit').json())


def test_allocation_deletion_requires_registrar(client):
    sign_in(client,'student')
    for url in ['/api/timetable/1','/api/exams/1']:
        assert client.request('DELETE',url,json={'revision':1}).status_code==403


def test_college_student_email_convention():
    assert student_email('Yogesh Pant')=='yogesh.pant@islingtoncollege.edu.np'
    assert student_email('Aarav Kumar Sharma')=='aarav.sharma@islingtoncollege.edu.np'
