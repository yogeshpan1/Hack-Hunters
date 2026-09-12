from conftest import sign_in


def plan_body(client):
    return {'module_ids':[1,2], 'start_date':'2026-10-04', 'days':7, 'duration':2,
            'revision':client.get('/api/workspace').json()['revision'],
            'reason':'Prepare assessment planning draft'}


def test_exam_plan_preview_save_and_stale_revision(registrar):
    before=registrar.get('/api/exams').json()
    body=plan_body(registrar)
    response=registrar.post('/api/exams/plan',json=body)
    assert response.status_code==200,response.text
    assert response.json()['unscheduled']==[]
    assert len(response.json()['proposed'])==2
    assert registrar.get('/api/exams').json()==before
    saved=registrar.post('/api/exams/plan',json={**body,'confirm':True})
    assert saved.status_code==200,saved.text
    after=registrar.get('/api/exams').json()
    assert len(after)==len(before)+2
    assert all(not exam['conflicts'] for exam in after if exam['id'] not in {e['id'] for e in before})
    assert registrar.post('/api/exams/plan',json={**body,'confirm':True}).status_code==409


def test_exam_rejects_overlap_and_invalid_time(registrar):
    body=plan_body(registrar)
    proposed=registrar.post('/api/exams/plan',json=body).json()['proposed'][0]
    request={**proposed,'revision':body['revision'],'reason':body['reason']}
    assert registrar.post('/api/exams',json={**request,'start':8.25}).status_code==422
    assert registrar.post('/api/exams',json=request).status_code==200
    request['revision']=registrar.get('/api/workspace').json()['revision']
    assert registrar.post('/api/exams',json=request).status_code==409


def test_exam_plan_unknown_module_and_permissions(client):
    sign_in(client,'student')
    body={'module_ids':[999999], 'start_date':'2026-10-04','reason':'Prepare exam period','revision':1}
    assert client.post('/api/exams/plan',json=body).status_code==403
    sign_in(client,'registrar')
    body['revision']=client.get('/api/workspace').json()['revision']
    assert client.post('/api/exams/plan',json=body).status_code==422


def test_venue_preview_does_not_mutate_and_history_is_available(registrar):
    before=registrar.get('/api/exams').json()
    result=registrar.post('/api/exams/venues',json={'revision':registrar.get('/api/workspace').json()['revision'],'reason':'Review venue seat utilization'})
    assert result.status_code==200,result.text
    assert registrar.get('/api/exams').json()==before
    assert registrar.get('/api/analytics/conflict-history').status_code==200
