from conftest import sign_in
from app import models as m
from app.scheduling import snapshot

def test_roster_count_cannot_be_hidden_by_smaller_planning_size(db):
    db.get(m.Cohort,1).size=1
    db.commit()
    assert next(c for c in snapshot(db)["cohorts"] if c["id"]==1)["size"]==34

def test_disabled_user_loses_api_access_immediately(client,db):
    sign_in(client,"faculty")
    db.get(m.User,7).active=False
    db.commit()
    assert client.get("/api/workspace").status_code==401

def test_hard_rules_and_unknown_fields_are_rejected(client):
    sign_in(client,"admin")
    assert client.put("/api/data/rules/1",json={"data":{"weight":0},"reason":"Try to disable capacity"}).status_code==403
    assert client.post("/api/data/rooms",json={"data":{"name":"Test","building":"X","capacity":40,"role":"Super Admin"},"reason":"Check unexpected fields"}).status_code==422
