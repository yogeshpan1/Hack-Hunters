"""Optimization calculation service; simulation never publishes assignments."""
from fastapi import HTTPException
from . import models as m
from .auth import require
from .scheduling import snapshot,solve,metrics,changes_for,serialize
from .services import revision,audit

def calculate_run(body,db,user,progress=None):
    require(user,["Registrar"]); data=snapshot(db); scenario={}
    if body.room_id is not None:
        if not db.get(m.Room,body.room_id) or body.day is None: raise HTTPException(422,"Select an existing room and a weekday.")
        scenario={"room_id":body.room_id,"day":body.day}
    rev=revision(db); result=solve(data,scenario,progress)
    run=m.OptimizationRun(user_id=user.id,status=result["status"],kind="what-if" if scenario else "optimization",revision=rev,before=metrics(data),after=metrics(data,result["assignments"],scenario),assignments=result["assignments"],changes=changes_for(data,result["assignments"]) if result["assignments"] else [],scenario=scenario,explanation=result["explanation"])
    db.add(run); db.flush(); audit(db,user,"SIMULATION CREATED",f"Run {run.id}",new={"status":run.status,"scenario":scenario},reason="Scenario analysis" if scenario else "Schedule optimization",result=run.status); db.commit(); return serialize(run)
