"""MongoDB document repository with request-scoped, multi-document transactions."""
import os
from copy import deepcopy
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError, OperationFailure
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
MONGODB_URI = (os.getenv("MONGODB_URI") or "mongodb://127.0.0.1:27017/?replicaSet=nexus-rs")
MONGODB_DATABASE = (os.getenv("MONGODB_DATABASE") or "nexus")
client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)

class StorageConflict(Exception):
    pass

UNIQUE = {"users": ["email"], "programmes": ["name"], "faculty": ["code"], "cohorts": ["name"], "students": ["code"], "rooms": ["name"], "modules": ["code"]}
REFERENCES = {
    "users": {"faculty_id": "faculty", "cohort_id": "cohorts"},
    "cohorts": {"programme_id": "programmes"},
    "students": {"cohort_id": "cohorts"},
    "modules": {"programme_id": "programmes", "faculty_id": "faculty", "cohort_id": "cohorts"},
    "sessions": {"module_id": "modules", "room_id": "rooms", "faculty_id":"faculty"},
    "exams": {"module_id": "modules", "room_id": "rooms", "invigilator_id": "faculty"},
    "optimization_runs": {"user_id": "users"}, "audit_logs": {"user_id": "users"},
    "approvals": {"run_id": "optimization_runs", "user_id": "users"},
    "notifications": {"user_id": "users", "cohort_id": "cohorts", "faculty_id": "faculty"},
}

def initialize_database(database=None):
    from .models import Document
    db = database if database is not None else client[MONGODB_DATABASE]
    db.client.admin.command("ping")
    if not db.client.admin.command("hello").get("setName"):
        raise RuntimeError("NEXUS requires a MongoDB replica set for atomic schedule publication. Run scripts/start-mongodb.ps1.")
    for model in Document.__subclasses__():
        if model.collection not in db.list_collection_names():
            db.create_collection(model.collection)
        db[model.collection].create_index("id", unique=True)
        for field in UNIQUE.get(model.collection, []):
            db[model.collection].create_index(field, unique=True)
    if "counters" not in db.list_collection_names(): db.create_collection("counters")
    db["students"].create_index([("cohort_id",1),("status",1)])
    db["sessions"].create_index([("day",1),("room_id",1)])
    db["conflicts"].create_index([("revision",1),("session_ids",1)])
    db["conflict_snapshots"].create_index("revision",unique=True)
    db["audit_logs"].create_index([("entity",1),("id",-1)])
    return db

class MongoSession:
    def __init__(self, database=None):
        self.database = database if database is not None else client[MONGODB_DATABASE]
        self.session = None
        self.cache = {}
        self.original = {}
        self.new = set()
        self.deleted = set()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()

    def _transaction(self):
        if self.session is None:
            self.session = self.database.client.start_session()
        if not self.session.in_transaction:
            self.session.start_transaction(read_concern=ReadConcern("snapshot"), write_concern=WriteConcern("majority"))
        return self.session

    def ping(self): self.database.client.admin.command("ping")

    def _object(self, model, raw):
        if raw is None: return None
        key=(model.collection,raw["id"])
        if key not in self.cache:
            raw.pop("_id",None)
            obj=model.model_validate(raw)
            self.cache[key]=obj
            self.original[key]=deepcopy(obj.model_dump())
        return self.cache[key]

    def get(self, model, ident):
        key=(model.collection,ident)
        if key in self.deleted: return None
        if key in self.cache: return self.cache[key]
        return self._object(model,self.database[model.collection].find_one({"id":ident},session=self._transaction()))

    def find(self, model, query=None, descending=False, limit=0):
        self.flush()
        cursor=self.database[model.collection].find(query or {},session=self._transaction()).sort("id",-1 if descending else 1)
        if limit: cursor=cursor.limit(limit)
        return [self._object(model,raw) for raw in cursor]

    def first(self, model, query=None):
        rows=self.find(model,query,limit=1)
        return rows[0] if rows else None

    def count_by(self, model, field, query=None):
        pipeline = [
            {"$match": query or {}},
            {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
        ]
        return {
            row["_id"]: row["count"]
            for row in self.database[model.collection].aggregate(pipeline, session=self._transaction())
            if row["_id"] is not None
        }

    def add(self, obj):
        collection=obj.collection
        if obj.id is None:
            counter=self.database.counters.find_one_and_update({"_id":collection},{"$inc":{"value":1}},upsert=True,return_document=ReturnDocument.AFTER,session=self._transaction())
            obj.id=counter["value"]
        else:
            self.database.counters.update_one({"_id":collection},{"$max":{"value":obj.id}},upsert=True,session=self._transaction())
        key=(collection,obj.id)
        if key in self.cache: raise StorageConflict("Duplicate document id.")
        self.cache[key]=obj
        self.new.add(key)

    def delete(self, obj): self.deleted.add((obj.collection,obj.id))

    def flush(self):
        try:
            for key in list(self.new):
                obj=self.cache[key]
                self.database[key[0]].insert_one(obj.model_dump(),session=self._transaction())
                self.new.remove(key)
                self.original[key]=None
        except DuplicateKeyError as exc:
            raise StorageConflict("A record with that code, name, or email already exists.") from exc

    def bump_revision(self, expected):
        from .models import ScheduleVersion
        result=self.database.schedule_versions.update_one({"id":1,"revision":expected},{"$set":{"revision":expected+1}},session=self._transaction())
        if result.modified_count != 1: raise StorageConflict("The schedule changed. Refresh and simulate again.")
        obj=self.get(ScheduleVersion,1)
        obj.revision=expected+1
        self.original[(obj.collection,1)]=deepcopy(obj.model_dump())

    def commit(self):
        try:
            self.flush()
            changed=[]
            for key,obj in self.cache.items():
                if key in self.deleted: continue
                value=obj.model_dump()
                if value!=self.original.get(key):
                    self.database[key[0]].replace_one({"id":obj.id},value,session=self._transaction())
                    changed.append((key,value))
            for collection,ident in self.deleted:
                if collection=="cohorts" and self.database.sessions.find_one({"cohort_ids":ident},session=self._transaction()):
                    raise StorageConflict("This cohort is referenced by a combined teaching session.")
                for source,fields in REFERENCES.items():
                    for field,target in fields.items():
                        if target==collection and self.database[source].find_one({field:ident},session=self._transaction()):
                            raise StorageConflict("This record is still referenced by another record.")
                self.database[collection].delete_one({"id":ident},session=self._transaction())
            for (collection,_),value in changed:
                if collection=="sessions":
                    for cid in value.get("cohort_ids",[]):
                        if not self.database.cohorts.find_one({"id":cid},session=self._transaction()): raise StorageConflict("Referenced session cohort does not exist.")
                for field,target in REFERENCES.get(collection,{}).items():
                    ident=value.get(field)
                    if ident is not None and not self.database[target].find_one({"id":ident},session=self._transaction()):
                        raise StorageConflict(f"Referenced {target} record does not exist.")
            if any(k[0]=="users" for k,_ in changed) or any(k[0]=="users" for k in self.deleted):
                if not self.database.users.find_one({"role":{"$in":["Registrar","Super Admin"]},"active":True},session=self._transaction()):
                    raise StorageConflict("At least one active Registrar must remain.")
            if any(k[0] in {"rooms","faculty","cohorts","students","modules","sessions","rules","schedule_versions"} for k,_ in changed) or any(k[0] in {"rooms","faculty","cohorts","students","modules","sessions"} for k in self.deleted):
                from .conflict_store import persist_conflicts
                persist_conflicts(self)
            if self.session and self.session.in_transaction: self.session.commit_transaction()
            self.cache.clear();self.original.clear();self.deleted.clear()
        except (DuplicateKeyError,OperationFailure) as exc:
            self.rollback()
            if isinstance(exc,DuplicateKeyError) or exc.has_error_label("TransientTransactionError"):
                raise StorageConflict("A concurrent update or duplicate record prevented this change. Refresh and retry.") from exc
            raise
        except Exception:
            self.rollback()
            raise

    def rollback(self):
        if self.session and self.session.in_transaction: self.session.abort_transaction()
        self.cache.clear();self.original.clear();self.new.clear();self.deleted.clear()

    def close(self):
        self.rollback()
        if self.session: self.session.end_session();self.session=None

SessionLocal=MongoSession

def get_db():
    with MongoSession() as db:
        try: yield db
        except OperationFailure as exc:
            if exc.has_error_label("TransientTransactionError"):
                raise StorageConflict("A concurrent update prevented this change. Refresh and retry.") from exc
            raise
