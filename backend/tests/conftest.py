from credentials import TEST_PASSWORD, SECOND_PASSWORD
import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.db import client as mongo_client, MongoSession, initialize_database, get_db
from app.main import app
from demo_seed import seed

@pytest.fixture
def empty_database():
    name='nexus_test_'+uuid.uuid4().hex
    database=initialize_database(mongo_client[name])
    yield database
    assert name.startswith('nexus_test_') and len(name)==43
    mongo_client.drop_database(name)

@pytest.fixture
def database(empty_database):
    with MongoSession(empty_database) as db: seed(db)
    return empty_database

@pytest.fixture
def db(database):
    with MongoSession(database) as db: yield db

@pytest.fixture
def client(database):
    def request_db():
        with MongoSession(database) as db: yield db
    app.dependency_overrides[get_db]=request_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def registrar(client):
    sign_in(client,'registrar')
    return client

def sign_in(client,role):
    response=client.post('/api/auth/login',json={'email':f'{role}@nexus.demo','password':TEST_PASSWORD})
    assert response.status_code==200,response.text
    client.headers['Authorization']='Bearer '+response.json()['token']

@pytest.fixture(autouse=True)
def bootstrap_environment(monkeypatch):
    monkeypatch.setenv('NEXUS_ADMIN_EMAIL','admin@example.test')
    monkeypatch.setenv('NEXUS_ADMIN_PASSWORD',TEST_PASSWORD)
    monkeypatch.setenv('NEXUS_LOAD_DEMO','false')
