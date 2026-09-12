"""Revisioned conflict snapshots persisted inside the academic-data transaction."""
from pymongo import ReturnDocument
from .models import Conflict, ConflictSnapshot, ScheduleVersion
from .scheduling import conflicts, snapshot


def persist_conflicts(db):
    version=db.first(ScheduleVersion)
    if not version: return
    issues=conflicts(snapshot(db))
    transaction=db._transaction()
    db.database.conflicts.delete_many({'revision':version.revision},session=transaction)
    for issue in issues:
        ident=db.database.counters.find_one_and_update({'_id':'conflicts'},{'$inc':{'value':1}},upsert=True,return_document=ReturnDocument.AFTER,session=transaction)['value']
        value=Conflict(id=ident,key=issue['id'],revision=version.revision,**{k:v for k,v in issue.items() if k!='id'})
        db.database.conflicts.insert_one(value.model_dump(),session=transaction)
    summary=ConflictSnapshot(id=version.revision,revision=version.revision,conflict_count=len(issues))
    db.database.conflict_snapshots.replace_one({'revision':version.revision},summary.model_dump(),upsert=True,session=transaction)
