"""Initial college inventory and exactly one bootstrap administrator.

Current teaching allocations and people must be entered by administrators.
The synthetic solver fixture lives exclusively under backend/tests.
"""
import json
import os
from pathlib import Path
from .models import User, Programme, Room, Rule, ScheduleVersion, AuditLog
from .auth import password_hash

CATALOG_PATH = Path(__file__).resolve().parents[1] / 'data' / 'college_catalog.json'

def seed(db):
    from .reference_seed import load_reference_demo
    if db.first(User):
        load_reference_demo(db)
        return
    catalog=json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    for record in catalog['programmes']: db.add(Programme(**record))
    for record in catalog['rooms']: db.add(Room(**record))
    password=os.getenv('NEXUS_ADMIN_PASSWORD','')
    if len(password)<10: raise ValueError('NEXUS_ADMIN_PASSWORD must have at least 10 characters.')
    email=os.getenv('NEXUS_ADMIN_EMAIL','').strip().lower()
    if '@' not in email: raise ValueError('Set NEXUS_ADMIN_EMAIL before initializing an empty database.')
    admin=User(id=1,name=os.getenv('NEXUS_ADMIN_NAME') or 'NEXUS Administrator',email=email,password_hash=password_hash(password),role='Super Admin')
    db.add(admin)
    db.add(ScheduleVersion(id=1,revision=1))
    for name in ['No room double booking','No faculty double booking','No cohort overlaps','Capacity and required equipment','Availability and locked sessions']:
        db.add(Rule(name=name,kind='Hard',weight=1))
    for name,weight in [('Minimize changes',10),('Avoid first period',2),('Compact cohort days',1),('Balance faculty days',2)]:
        db.add(Rule(name=name,kind='Soft',weight=weight))
    db.add(AuditLog(user_id=admin.id,actor=admin.name,role=admin.role,action='COLLEGE INITIALIZED',entity='College inventory',reason='Imported supplied classroom inventory and UG/PG brochure curriculum; created the first administrator.',new={'rooms':len(catalog['rooms']),'programmes':len(catalog['programmes'])},result='Ready'))
    db.commit()
    load_reference_demo(db)
