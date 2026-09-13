from conftest import sign_in
from app import models as m
from app.scheduling import conflicts, snapshot


def test_superadmin_creates_rte_and_ssd_with_expected_boundaries(client):
    sign_in(client, "admin")
    rte = client.post("/api/data/users", json={"data":{"name":"RTE","email":"rte@test.example","role":"RTE","password":"pass"},"reason":"Create RTE"})
    ssd = client.post("/api/data/users", json={"data":{"name":"SSD","email":"ssd@test.example","role":"SSD","password":"pass"},"reason":"Create SSD"})
    assert rte.status_code == 200 and ssd.status_code == 200
    login = client.post("/api/auth/login", json={"email":"rte@test.example","password":"pass"})
    client.headers["Authorization"] = "Bearer " + login.json()["token"]
    assert client.get("/api/audit").status_code == 403
    assert client.get("/api/data/users").status_code == 403
    assert client.post("/api/optimization", json={}).status_code == 200
    login = client.post("/api/auth/login", json={"email":"ssd@test.example","password":"pass"})
    client.headers["Authorization"] = "Bearer " + login.json()["token"]
    assert client.get("/api/timetable").status_code == 200
    assert client.post("/api/assistant", json={"query":"Which room has capacity for 45 students?"}).status_code == 200
    assert client.post("/api/optimization", json={}).status_code == 403
    assert client.post("/api/data/rooms", json={"data":{"name":"X","building":"B","capacity":20},"reason":"Should fail"}).status_code == 403


def test_study_level_policies_are_detected(db):
    cohort = db.get(m.Cohort, 1)
    cohort.study_level = "Third Year"
    third = db.get(m.TimetableSession, 1)
    third.start, third.duration, third.session_type = 10, 1.5, "Tutorial"
    assert "Third Year teaching window" in {item["kind"] for item in conflicts(snapshot(db))}
    assert "Third Year session pattern" in {item["kind"] for item in conflicts(snapshot(db))}
    cohort.study_level = "Masters"
    third.start, third.duration, third.session_type = 8, 2, "Lecture"
    assert "Masters teaching window" in {item["kind"] for item in conflicts(snapshot(db))}
