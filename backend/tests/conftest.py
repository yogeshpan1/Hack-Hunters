import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.db import Base,get_db
from app.main import app
from app.seed import seed

@pytest.fixture
def db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine,expire_on_commit=False)
    with factory() as session:
        seed(session)
        yield session
    engine.dispose()

@pytest.fixture
def client(db):
    app.dependency_overrides[get_db]=lambda:db
    c=TestClient(app)
    yield c
    app.dependency_overrides.clear()

@pytest.fixture
def registrar(client):
    r=client.post("/api/auth/login",json={"email":"registrar@nexus.demo","password":"NexusDemo!2026"})
    assert r.status_code==200
    client.headers["Authorization"]="Bearer "+r.json()["token"]
    return client

def sign_in(client,role):
    r=client.post("/api/auth/login",json={"email":f"{role}@nexus.demo","password":"NexusDemo!2026"})
    assert r.status_code==200
    client.headers["Authorization"]="Bearer "+r.json()["token"]
