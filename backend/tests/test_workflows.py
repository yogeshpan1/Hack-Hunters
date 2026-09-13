import pytest
from conftest import sign_in
from app import models as m
from app.main import ENTITIES
from app.scheduling import snapshot,conflicts,enriched,solve

def test_health_auth_and_invalid_password(client):
    assert client.get("/api/health").json()["database"]=="MongoDB"
    assert client.get("/api/workspace").status_code==401
    assert client.post("/api/auth/login",json={"email":"registrar@nexus.demo","password":"wrong"}).status_code==401

def test_seed_conflict_types_and_computed_metrics(registrar):
    data=registrar.get("/api/workspace").json()
    assert {"Capacity","Room clash","Faculty clash","Cohort overlap","Faculty unavailable"}.issubset({c["kind"] for c in data["conflicts"]})
    affected={i for c in data["conflicts"] for i in c["session_ids"]}
    assert data["metrics"]["health"]==round(100*(1-len(affected)/len(data["sessions"])),1)

def test_complete_optimization_approval_publish_communication_audit(registrar,db):
    before=registrar.get("/api/workspace").json(); locked=[s for s in before["sessions"] if s["locked"]]
    result=registrar.post("/api/optimization",json={})
    assert result.status_code==200,result.text
    run=result.json(); assert run["status"]=="Review",run
    assert run["after"]["conflicts"]==0
    assert registrar.get("/api/workspace").json()["sessions"]==before["sessions"]
    assert not conflicts(snapshot(db),run["assignments"])
    for original in locked:
        proposed=next(a for a in run["assignments"] if a["id"]==original["id"])
        assert all(proposed[k]==original[k] for k in ["room_id","day","start"])
    endpoint=f'/api/optimization/{run["id"]}'
    reason={"reason":"Resolve scheduling conflicts for the new teaching week"}
    assert registrar.post(endpoint+"/publish",json=reason).status_code==409
    assert registrar.post(endpoint+"/approve",json=reason).json()["status"]=="Approved"
    assert registrar.post(endpoint+"/publish",json=reason).json()["status"]=="Published"
    assert registrar.get("/api/conflicts").json()==[]
    assert registrar.get("/api/emails").json()
    assert registrar.get("/api/notifications").json()
    logs=registrar.get("/api/audit").json()
    assert any(x["action"]=="SESSION OPTIMIZED" and x["previous"] and x["new"] for x in logs)
    assert all(x["actor"] and x["timestamp"] and x["reason"] and x["result"] for x in logs)
    assert registrar.post(endpoint+"/publish",json=reason).status_code==409

def test_what_if_is_isolated_and_persists_closure_on_publish(registrar):
    before=registrar.get("/api/workspace").json()
    run=registrar.post("/api/what-if",json={"room_id":1,"day":3}).json()
    assert run["status"]=="Review",run
    assert not any(a["room_id"]==1 and a["day"]==3 for a in run["assignments"])
    assert registrar.get("/api/workspace").json()["rooms"]==before["rooms"]
    reason={"reason":"Lab 2A maintenance on Thursday"}
    assert registrar.post(f'/api/optimization/{run["id"]}/approve',json=reason).status_code==200
    assert registrar.post(f'/api/optimization/{run["id"]}/publish',json=reason).status_code==200
    current=registrar.get("/api/workspace").json()
    assert "3:14" in next(r for r in current["rooms"] if r["id"]==1)["unavailable"]
    assert current["conflicts"]==[]

def test_infeasible_locked_capacity_returns_clear_failure(db):
    session=db.get(m.TimetableSession,4); room=db.get(m.Room,session.room_id); room.capacity=1; db.commit()
    result=solve(snapshot(db))
    assert result["status"]=="Infeasible"
    assert "no eligible" in result["explanation"]

def test_stale_run_is_rejected_after_inputs_change(registrar):
    run=registrar.post("/api/optimization",json={}).json()
    sign_in(registrar,"admin")
    room=registrar.get("/api/data/rooms").json()[0]; ident=room.pop("id"); room.pop("source",None); room["capacity"]=25
    assert registrar.put(f"/api/data/rooms/{ident}",json={"data":room,"reason":"Updated capacity after inspection"}).status_code==200
    assert registrar.post(f'/api/optimization/{run["id"]}/approve',json={"reason":"Approve a now stale proposal"}).status_code==409

def test_manual_move_preview_confirmation_and_lock(registrar,db):
    state=registrar.get("/api/workspace").json()
    locked=next(s for s in state["sessions"] if s["locked"])
    body={"room_id":locked["room_id"],"day":2,"start":15,"revision":state["revision"],"reason":"Faculty preference adjustment","confirm":False}
    assert registrar.post(f'/api/timetable/{locked["id"]}/move',json=body).status_code==409
    session=next(s for s in state["sessions"] if s["id"]==6)
    body.update(room_id=8,day=1,start=15)
    preview=registrar.post(f'/api/timetable/{session["id"]}/move',json=body)
    assert preview.status_code==200 and not preview.json()["conflicts"]
    assert db.get(m.TimetableSession,session["id"]).day==session["day"]
    body["confirm"]=True
    assert registrar.post(f'/api/timetable/{session["id"]}/move',json=body).status_code==200
    assert any(x["action"]=="MANUAL OVERRIDE" for x in registrar.get("/api/audit").json())

@pytest.mark.parametrize("role",["student","faculty","admissions","hr","facilities","programme"])
def test_roles_cannot_optimize_or_read_sensitive_audit(client,role):
    sign_in(client,role)
    assert client.post("/api/optimization",json={}).status_code==403
    assert client.get("/api/audit").status_code==403
    assert client.get("/api/emails").status_code==403

def test_student_scope_and_assistant_safety(client):
    sign_in(client,"student")
    data=client.get("/api/workspace").json()
    assert all(s["cohort_id"]==1 for s in data["sessions"])
    assert client.get("/api/data/students").status_code==403
    assert client.get("/api/data/users").status_code==403
    assert client.post("/api/assistant",json={"query":"Who changed this?"}).status_code==403
    before=data["revision"]
    answer=client.post("/api/assistant",json={"query":"Why is CS302 in conflict?"})
    assert answer.status_code==200
    assert "CS302" in answer.json()["answer"]
    assert client.get("/api/workspace").json()["revision"]==before

@pytest.mark.parametrize("entity,data",[
 ("rooms",{"name":"Test room","building":"Demo block","capacity":45,"kind":"Classroom"}),
 ("faculty",{"name":"Test Faculty","code":"TESTF001","department":"Computing","max_hours":18}),
 ("programmes",{"name":"Demo programme test","department":"Computing"}),
 ("cohorts",{"name":"Test cohort","programme_id":1,"size":30,"level":5}),
 ("modules",{"code":"TESTM001","name":"Demo test module","programme_id":1,"faculty_id":1,"cohort_id":1,"room_type":"Classroom"}),
 ("students",{"code":"TESTS001","name":"Test student","email":"test@example.test","cohort_id":1})])
def test_crud_validation_and_audit(client,entity,data):
    sign_in(client,"admin")
    created=client.post(f"/api/data/{entity}",json={"data":data,"reason":"Create test academic record"})
    assert created.status_code==200,created.text
    obj=created.json(); ident=obj.pop("id")
    obj={key:value for key,value in obj.items() if key in ENTITIES[entity][1].model_fields}
    obj["name"]="Updated test record"
    assert client.put(f"/api/data/{entity}/{ident}",json={"data":obj,"reason":"Correct academic record name"}).status_code==200
    assert client.request("DELETE",f"/api/data/{entity}/{ident}",json={"reason":"Remove unused test record"}).status_code==200
    logs=client.get("/api/audit").json()
    assert {"CREATE","UPDATE","DELETE"}.issubset({x["action"] for x in logs if x["entity"]==f"{entity}/{ident}"})

def test_invalid_room_and_reference_validation(client):
    sign_in(client,"admin")
    assert client.post("/api/data/rooms",json={"data":{"name":"X","building":"B","capacity":-1},"reason":"Test invalid capacity"}).status_code==422
    assert client.post("/api/data/modules",json={"data":{"code":"X","name":"X","programme_id":1,"faculty_id":999,"cohort_id":1},"reason":"Test missing faculty"}).status_code==422


def test_removed_bulk_import_endpoint_is_not_available(client):
    assert client.post("/api/import",json={}).status_code==404

def test_assistant_capacity_workload_context_and_no_fake_room_fix(registrar):
    answer=registrar.post("/api/assistant",json={"query":"Which room has capacity for 45 students?"}).json()
    assert any("Lab 4B" in item for item in answer["items"])
    answer=registrar.post("/api/assistant",json={"query":"What is the safest alternative?","context":{"session_id":1}}).json()
    assert "room-only move cannot" in answer["answer"]
    assert registrar.post("/api/assistant",json={"query":"Who has the heaviest faculty workload?"}).json()["items"]

def test_email_demo_delivery_and_schedule_validation(registrar,db):
    email=m.Email(recipient="demo@example.test",subject="Room changed",body="Updated timetable")
    db.add(email);db.commit()
    r=registrar.put(f"/api/emails/{email.id}",json={"subject":"Room updated","body":"Please review the timetable","action":"send"})
    assert r.status_code==200 and r.json()["status"]=="Demo delivered"
    r=registrar.put(f"/api/emails/{email.id}",json={"subject":"Room updated","body":"Please review","action":"schedule","scheduled_at":"2020-01-01T10:00:00+00:00"})
    assert r.status_code==422


def test_rte_can_prepare_deduplicated_custom_email_drafts(registrar):
    response=registrar.post("/api/emails/recipients",json={
        "custom_recipients":["External.Contact@example.test","external.contact@example.test"],
        "subject":"Assessment update",
        "body":"Please review the revised assessment information.",
    })
    assert response.status_code==200,response.text
    assert response.json()=={"prepared":1,"student_recipients":0,"custom_recipients":1}
    invalid=registrar.post("/api/emails/recipients",json={
        "custom_recipients":["not-an-email"],"subject":"Assessment update","body":"Please review the revised assessment information.",
    })
    assert invalid.status_code==422
