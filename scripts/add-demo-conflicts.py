"""Add two audited, optimizer-resolvable room clashes to the configured workspace."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.db import MongoSession
from app.demo_conflicts import add_demo_conflicts

if __name__ == '__main__':
    with MongoSession() as db:
        print(json.dumps(add_demo_conflicts(db), indent=2))
