import csv
import io
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from .db import Base,engine,SessionLocal,get_db
from . import models as m, schemas as s
from .auth import current_user,require,token_for,verify_password,password_hash,public_user,MANAGE
from .scheduling import snapshot,enriched,conflicts,metrics,solve,changes_for,serialize,DAYS
from .services import audit,revision,bump,communicate,visible_sessions
from .seed import seed

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with SessionLocal() as db: seed(db)
    yield

app=FastAPI(title="NEXUS · Academic Operations Intelligence",version="1.0.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["http://127.0.0.1:5173","http://localhost:5173"],allow_methods=["GET","POST","PUT","PATCH","DELETE"],allow_headers=["Authorization","Content-Type"])

@app.exception_handler(IntegrityError)
async def integrity_error(request,exc):
    return JSONResponse(status_code=409,content={"detail":"A record with that code/name already exists, or a referenced record is missing/in use."})

@app.get("/api/health")
def health(db=Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status":"ok","demo":True,"database":"connected"}

@app.post("/api/auth/login")
def login(body:s.Login,db=Depends(get_db)):
    user=db.scalar(select(m.User).where(m.User.email==body.email.lower()))
    if not user or not user.active or not verify_password(body.password,user.password_hash): raise HTTPException(401,"Incorrect email or password.")
    audit(db,user,"SIGNED IN","User",reason="Local demo authentication"); db.commit()
    return {"token":token_for(user),"user":public_user(user)}

@app.get("/api/auth/me")
def me(user=Depends(current_user)): return public_user(user)

@app.get("/api/workspace")
def workspace(db=Depends(get_db),user=Depends(current_user)):
    data=snapshot(db); sessions=visible_sessions(user,enriched(data)); ids={x["id"] for x in sessions}; issues=[c for c in conflicts(data) if set(c["session_ids"])&ids]
    if user.role in ["Student","Faculty"]:
        mids={x["module_id"] for x in sessions}; fids={x["faculty_id"] for x in sessions}; cids={x["cohort_id"] for x in sessions}
        data["sessions"]=[x for x in data["sessions"] if x["id"] in ids]; data["modules"]=[x for x in data["modules"] if x["id"] in mids]; data["faculty"]=[x for x in data["faculty"] if x["id"] in fids]; data["cohorts"]=[x for x in data["cohorts"] if x["id"] in cids]
        issues=conflicts(data)
    return {**data,"sessions":sessions,"conflicts":issues,"metrics":metrics(data),"programmes":[serialize(x) for x in db.scalars(select(m.Programme)).all()],"revision":revision(db),"demo":True}

@app.get("/api/timetable")
def timetable(db=Depends(get_db),user=Depends(current_user)):
    return visible_sessions(user,enriched(snapshot(db)))

@app.get("/api/conflicts")
def get_conflicts(db=Depends(get_db),user=Depends(current_user)):
    return workspace(db,user)["conflicts"]

@app.post("/api/timetable/{ident}/move")
def move(ident:int,body:s.Move,db=Depends(get_db),user=Depends(current_user)):
    require(user,["Registrar"]); obj=db.get(m.TimetableSession,ident)
    if not obj: raise HTTPException(404,"Session not found.")
    if obj.locked: raise HTTPException(409,"Unlock the session before moving it.")
    if not db.get(m.Room,body.room_id): raise HTTPException(422,"Room does not exist.")
    if body.revision!=revision(db): raise HTTPException(409,"The schedule changed. Refresh before moving this session.")
    data=snapshot(db); assignments=[{"id":ident,"room_id":body.room_id,"day":body.day,"start":body.start}]
    issues=[x for x in conflicts(data,assignments) if ident in x["session_ids"]]
    result={"conflicts":issues,"before":metrics(data),"after":metrics(data,assignments),"changes":changes_for(data,assignments)}
    if not body.confirm: return result
    if issues: raise HTTPException(409,"This move violates hard constraints. Choose a valid room and time.")
    bump(db,body.revision); old=serialize(obj)
    obj.room_id=body.room_id; obj.day=body.day; obj.start=body.start; obj.state="override"
    audit(db,user,"MANUAL OVERRIDE",f"Session {ident}",old,serialize(obj),body.reason,"Published")
    session=next(x for x in enriched(data,assignments) if x["id"]==ident); count=communicate(db,session,body.reason)
    db.commit(); return {**result,"status":"Published","recipients":count}

@app.post("/api/timetable/{ident}/lock")
def lock(ident:int,body:s.Lock,db=Depends(get_db),user=Depends(current_user)):
    require(user,["Registrar"]); obj=db.get(m.TimetableSession,ident)
    if not obj: raise HTTPException(404,"Session not found.")
    bump(db,body.revision); old=serialize(obj); obj.locked=body.locked; obj.state="locked" if body.locked else "normal"
    audit(db,user,"SESSION LOCK",f"Session {ident}",old,serialize(obj),body.reason); db.commit(); return serialize(obj)

@app.post("/api/optimization")
def optimize(body:s.RunInput,db=Depends(get_db),user=Depends(current_user)):
    require(user,["Registrar"]); data=snapshot(db); scenario={}
    if body.room_id is not None:
        if not db.get(m.Room,body.room_id) or body.day is None: raise HTTPException(422,"Select an existing room and a weekday.")
        scenario={"room_id":body.room_id,"day":body.day}
    rev=revision(db); result=solve(data,scenario)
    run=m.OptimizationRun(user_id=user.id,status=result["status"],kind="what-if" if scenario else "optimization",revision=rev,before=metrics(data),after=metrics(data,result["assignments"],scenario),assignments=result["assignments"],changes=changes_for(data,result["assignments"]) if result["assignments"] else [],scenario=scenario,explanation=result["explanation"])
    db.add(run); db.flush(); audit(db,user,"SIMULATION CREATED",f"Run {run.id}",new={"status":run.status,"scenario":scenario},reason="Scenario analysis" if scenario else "Schedule optimization",result=run.status); db.commit(); return serialize(run)

@app.post("/api/what-if")
def what_if(body:s.RunInput,db=Depends(get_db),user=Depends(current_user)):
    if body.room_id is None: raise HTTPException(422,"Select a room to close.")
    return optimize(body,db,user)

@app.get("/api/optimization")
def runs(db=Depends(get_db),user=Depends(current_user)):
    require(user,["Registrar"]); return [serialize(x) for x in db.scalars(select(m.OptimizationRun).order_by(m.OptimizationRun.id.desc()).limit(30)).all()]

@app.post("/api/optimization/{ident}/{action}")
def run_action(ident:int,action:str,body:s.Reason,db=Depends(get_db),user=Depends(current_user)):
    require(user,["Registrar"]); run=db.get(m.OptimizationRun,ident)
    if not run: raise HTTPException(404,"Run not found.")
    if action not in ["approve","publish","discard"]: raise HTTPException(404,"Unknown action.")
    if action=="discard":
        if run.status not in ["Review","Approved"]: raise HTTPException(409,"This run cannot be discarded.")
        run.status="Discarded"
    else:
        if run.revision!=revision(db): raise HTTPException(409,"Schedule inputs changed. Run a fresh simulation.")
        if action=="approve":
            if run.status!="Review": raise HTTPException(409,"Only reviewed results can be approved.")
            run.status="Approved"; db.add(m.Approval(run_id=run.id,user_id=user.id,reason=body.reason))
        else:
            if run.status!="Approved": raise HTTPException(409,"Approve this result before publishing.")
            data=snapshot(db)
            if conflicts(data,run.assignments,run.scenario): raise HTTPException(409,"The proposed timetable no longer passes validation.")
            bump(db,run.revision)
            if run.scenario:
                room=db.get(m.Room,run.scenario["room_id"]); before=serialize(room); room.unavailable=sorted(set(room.unavailable)|{f'{run.scenario["day"]}:{h}' for h in range(9,17)})
                audit(db,user,"ROOM AVAILABILITY",room.name,before,serialize(room),body.reason)
            changed_ids={c["id"] for c in run.changes}
            for a in run.assignments:
                if a["id"] not in changed_ids: continue
                obj=db.get(m.TimetableSession,a["id"]); before=serialize(obj)
                obj.room_id=a["room_id"]; obj.day=a["day"]; obj.start=a["start"]; obj.state="optimized"
                audit(db,user,"SESSION OPTIMIZED",f"Session {obj.id}",before,serialize(obj),body.reason,"Published")
            for session in enriched(data,run.assignments):
                if session["id"] in changed_ids: communicate(db,session,body.reason)
            run.status="Published"
    audit(db,user,f"RUN {action.upper()}",f"Run {ident}",new={"status":run.status},reason=body.reason,result=run.status); db.commit(); return serialize(run)

ENTITIES={"rooms":(m.Room,s.RoomInput),"faculty":(m.Faculty,s.FacultyInput),"programmes":(m.Programme,s.ProgrammeInput),"cohorts":(m.Cohort,s.CohortInput),"modules":(m.Module,s.ModuleInput),"students":(m.Student,s.StudentInput),"users":(m.User,s.UserInput),"rules":(m.Rule,s.RuleInput)}

def entity_info(entity):
    if entity not in ENTITIES: raise HTTPException(404,"Unknown collection.")
    return ENTITIES[entity]

def validate_payload(entity,payload,db):
    _,schema=entity_info(entity)
    try: values=schema.model_validate(payload).model_dump()
    except ValidationError as exc: raise HTTPException(422,"; ".join(e["msg"] for e in exc.errors()))
    for field,model in [("programme_id",m.Programme),("faculty_id",m.Faculty),("cohort_id",m.Cohort)]:
        if values.get(field) is not None and not db.get(model,values[field]): raise HTTPException(422,f"Invalid {field}.")
    if entity=="modules" and db.get(m.Cohort,values["cohort_id"]).programme_id!=values["programme_id"]: raise HTTPException(422,"Module and cohort programmes must match.")
    if entity=="users":
        if values["role"]=="Faculty" and not values.get("faculty_id"): raise HTTPException(422,"Faculty users require a faculty assignment.")
        if values["role"]=="Student" and not values.get("cohort_id"): raise HTTPException(422,"Student users require a cohort assignment.")
    return values

@app.get("/api/data/{entity}")
def records(entity:str,db=Depends(get_db),user=Depends(current_user)):
    model,_=entity_info(entity)
    if entity=="users": require(user,[])
    if entity=="students": require(user,["Registrar","Admissions","Programme Admin"])
    if user.role in ["Student","Faculty"] and entity in ["faculty","modules","cohorts"]: return workspace(db,user)[entity]
    return [serialize(x) for x in db.scalars(select(model).order_by(model.id)).all()]

@app.post("/api/data/{entity}")
def create(entity:str,body:s.Mutation,db=Depends(get_db),user=Depends(current_user)):
    model,_=entity_info(entity); require(user,MANAGE.get(entity,[])); values=validate_payload(entity,body.data,db)
    if entity=="rules": raise HTTPException(403,"The supported rule set is fixed; edit soft weights instead.")
    if entity=="users":
        password=values.pop("password")
        if not password: raise HTTPException(422,"A new user needs a password.")
        values["password_hash"]=password_hash(password)
    obj=model(**values); db.add(obj); db.flush(); bump(db); audit(db,user,"CREATE",f"{entity}/{obj.id}",new=serialize(obj),reason=body.reason); db.commit(); return serialize(obj)

@app.put("/api/data/{entity}/{ident}")
def edit(entity:str,ident:int,body:s.Mutation,db=Depends(get_db),user=Depends(current_user)):
    model,_=entity_info(entity); require(user,MANAGE.get(entity,[])); obj=db.get(model,ident)
    if not obj: raise HTTPException(404,"Record not found.")
    if entity=="rules" and obj.kind=="Hard": raise HTTPException(403,"Hard constraints cannot be disabled.")
    values=validate_payload(entity,body.data,db)
    if entity=="users":
        if ident==user.id and (not values["active"] or values["role"]!="Super Admin"): raise HTTPException(409,"You cannot remove your own administrator access.")
        password=values.pop("password")
        if password: values["password_hash"]=password_hash(password)
    old=serialize(obj)
    for k,v in values.items(): setattr(obj,k,v)
    bump(db); audit(db,user,"UPDATE",f"{entity}/{ident}",old,serialize(obj),body.reason); db.commit(); return serialize(obj)

@app.delete("/api/data/{entity}/{ident}")
def remove(entity:str,ident:int,body:s.Reason,db=Depends(get_db),user=Depends(current_user)):
    model,_=entity_info(entity); require(user,MANAGE.get(entity,[])); obj=db.get(model,ident)
    if not obj: raise HTTPException(404,"Record not found.")
    if entity in ["users","rules"]: raise HTTPException(403,"Disable users or edit rule weights instead of deleting.")
    old=serialize(obj); db.delete(obj); db.flush(); bump(db); audit(db,user,"DELETE",f"{entity}/{ident}",old,reason=body.reason); db.commit(); return {"deleted":ident}

@app.post("/api/import")
def import_data(body:s.ImportInput,db=Depends(get_db),user=Depends(current_user)):
    require(user,MANAGE[body.entity]); errors=[]; values=[]
    for i,row in enumerate(body.rows,1):
        try: values.append(validate_payload(body.entity,row,db))
        except HTTPException as exc: errors.append({"row":i,"error":exc.detail})
    if errors: return {"valid":False,"errors":errors,"count":len(body.rows)}
    model,_=entity_info(body.entity)
    keys=["name"] if body.entity in ["rooms","programmes","cohorts"] else ["code"]
    for key in keys:
        seen=set(db.scalars(select(getattr(model,key))).all())
        for i,row in enumerate(values,1):
            if row[key] in seen: errors.append({"row":i,"error":f"Duplicate {key}: {row[key]}"})
            seen.add(row[key])
    if errors: return {"valid":False,"errors":errors,"count":len(body.rows)}
    if body.confirm:
        for value in values: db.add(model(**value))
        db.flush(); bump(db); audit(db,user,"DATA IMPORT",body.entity,new={"rows":len(values)},reason="Validated bulk import"); db.commit()
    return {"valid":True,"imported":body.confirm,"count":len(values),"errors":[]}

@app.get("/api/audit")
def audit_log(db=Depends(get_db),user=Depends(current_user)):
    require(user,["Registrar"]); return [serialize(x) for x in db.scalars(select(m.AuditLog).order_by(m.AuditLog.id.desc()).limit(500)).all()]

@app.get("/api/audit/export")
def export_audit(db=Depends(get_db),user=Depends(current_user)):
    rows=audit_log(db,user); out=io.StringIO(); fields=["timestamp","actor","role","action","entity","previous","new","reason","result"]; writer=csv.DictWriter(out,fieldnames=fields,extrasaction="ignore"); writer.writeheader()
    for row in rows:
        writer.writerow({k:("'"+str(v) if str(v).startswith(("=","+","-","@")) else v) for k,v in row.items()})
    return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=nexus-audit.csv"})

@app.get("/api/notifications")
def notifications(db=Depends(get_db),user=Depends(current_user)):
    rows=db.scalars(select(m.Notification).order_by(m.Notification.id.desc())).all()
    if user.role=="Student": rows=[x for x in rows if x.user_id==user.id or x.cohort_id==user.cohort_id]
    elif user.role=="Faculty": rows=[x for x in rows if x.user_id==user.id or x.faculty_id==user.faculty_id]
    return [serialize(x) for x in rows]

@app.get("/api/emails")
def emails(db=Depends(get_db),user=Depends(current_user)):
    require(user,["Registrar"]); return [serialize(x) for x in db.scalars(select(m.Email).order_by(m.Email.id.desc()).limit(1000)).all()]

@app.put("/api/emails/{ident}")
def edit_email(ident:int,body:s.EmailInput,db=Depends(get_db),user=Depends(current_user)):
    require(user,["Registrar"]); obj=db.get(m.Email,ident)
    if not obj: raise HTTPException(404,"Email not found.")
    old=serialize(obj); obj.subject=body.subject; obj.body=body.body
    obj.status={"draft":"Draft","send":"Demo delivered","schedule":"Demo scheduled"}[body.action]; obj.scheduled_at=body.scheduled_at if body.action=="schedule" else None
    if body.action=="schedule":
        try:
            stamp=datetime.fromisoformat(body.scheduled_at.replace("Z","+00:00"))
            if stamp.tzinfo is None or stamp<=datetime.now(timezone.utc): raise ValueError()
        except (ValueError,AttributeError): raise HTTPException(422,"Choose a future date and time with a timezone.")
    audit(db,user,"EMAIL "+body.action.upper(),f"Email {ident}",old,serialize(obj),"Demo communication workflow",obj.status); db.commit(); return serialize(obj)

@app.post("/api/emails/deliver-due")
def deliver_due(db=Depends(get_db),user=Depends(current_user)):
    require(user,["Registrar"]); count=0
    for email in db.scalars(select(m.Email).where(m.Email.status=="Demo scheduled")).all():
        if datetime.fromisoformat(email.scheduled_at)<=datetime.now(timezone.utc):
            email.status="Demo delivered"; count+=1; audit(db,user,"EMAIL DEMO DELIVERY",f"Email {email.id}",reason="Process due demo outbox")
    db.commit(); return {"delivered":count}

@app.get("/api/exams")
def exams(db=Depends(get_db),user=Depends(current_user)):
    data=snapshot(db); modules={x["id"]:x for x in data["modules"]}; rooms={x["id"]:x for x in data["rooms"]}; cohorts={x["id"]:x for x in data["cohorts"]}; faculty={x["id"]:x for x in data["faculty"]}; rows=[]
    all_exams=db.scalars(select(m.ExamSession)).all()
    for exam in all_exams:
        mod=modules[exam.module_id]; room=rooms[exam.room_id]; cohort=cohorts[mod["cohort_id"]]
        if user.role=="Student" and user.cohort_id!=cohort["id"]: continue
        if user.role=="Faculty" and user.faculty_id!=exam.invigilator_id: continue
        issues=[]
        if cohort["size"]>room["capacity"]: issues.append("Venue capacity exceeded")
        for other in all_exams:
            if exam.id==other.id or exam.date!=other.date or exam.start>=other.start+other.duration or other.start>=exam.start+exam.duration: continue
            if exam.room_id==other.room_id: issues.append("Venue clash")
            if exam.invigilator_id==other.invigilator_id: issues.append("Invigilator clash")
            if mod["cohort_id"]==modules[other.module_id]["cohort_id"]: issues.append("Cohort clash")
        rows.append({**serialize(exam),"code":mod["code"],"module":mod["name"],"room":room["name"],"capacity":room["capacity"],"students":cohort["size"],"invigilator":faculty[exam.invigilator_id]["name"],"conflicts":issues})
    return rows

@app.get("/api/search")
def search(q:str="",db=Depends(get_db),user=Depends(current_user)):
    if not q.strip(): return []
    w=workspace(db,user); results=[]
    for key in ["rooms","faculty","modules","cohorts","programmes"]:
        for row in w[key]:
            if q.lower() in str(row).lower(): results.append({"entity":key,"id":row["id"],"label":row.get("code",row.get("name")),"detail":row.get("name","")})
    return results[:30]

@app.post("/api/assistant")
def assistant(body:s.Question,db=Depends(get_db),user=Depends(current_user)):
    import re
    w=workspace(db,user); q=body.query.lower(); ctx=body.context; sessions=w["sessions"]
    target=next((x for x in sessions if x["id"]==ctx.get("session_id") or x["code"].lower() in q),None)
    answer=""; items=[]; action=None
    if "who changed" in q or "audit" in q:
        require(user,["Registrar"]); rows=audit_log(db,user)
        if target: rows=[x for x in rows if x["entity"]==f'Session {target["id"]}']
        items=[f'{x["actor"]}: {x["action"]} · {x["reason"]}' for x in rows[:5]]; answer="These are the recorded changes." if items else "There are no recorded changes for this session."
    elif "workload" in q or "overload" in q or "heaviest" in q:
        loads=[(f,sum(x["duration"] for x in sessions if x["faculty_id"]==f["id"])) for f in w["faculty"]]; loads.sort(key=lambda x:-x[1]); items=[f'{f["name"]}: {h} hours / {f["max_hours"]} weekly target' for f,h in loads]; answer="Teaching hours are calculated from the current timetable. Moving sessions can improve daily distribution, but does not reduce total teaching hours."
    elif target and any(word in q for word in ["conflict","why","alternative","safe","resolve","room"]):
        issues=[x["detail"] for x in w["conflicts"] if target["id"] in x["session_ids"]]; answer=f'{target["code"]} has {len(issues)} hard constraint issue(s). '+" ".join(issues)
        valid=[]; data=snapshot(db)
        for r in w["rooms"]:
            a=[{"id":target["id"],"room_id":r["id"],"day":target["day"],"start":target["start"]}]
            if not any(target["id"] in x["session_ids"] for x in conflicts(data,a)): valid.append(r)
        items=[f'{r["name"]} · {r["capacity"]} seats · valid at the current time' for r in valid]
        if not valid: answer+=" A room-only move cannot resolve all constraints; simulate changes to time and room together."
        action="optimization"
    elif "faculty" in q:
        items=[f'{f["name"]} · {f["department"]}' for f in w["faculty"] if "computing" not in q or f["department"]=="Computing"]; answer="Faculty records available to your role."
    elif any(word in q for word in ["room","lab","capacity","projector"]):
        cap=re.search(r"(?:for|capacity(?: for)?)\s*(\d+)",q); minimum=int(cap.group(1)) if cap else 0
        day=next((i for i,d in enumerate(DAYS) if d.lower() in q),None); tm=re.search(r"(?:at|after)\s*(\d{1,2})",q); hour=int(tm.group(1)) if tm else None
        if hour is not None and hour<9: hour+=12
        for r in w["rooms"]:
            if not r["active"] or r["capacity"]<minimum or ("lab" in q and r["kind"]!="Lab"): continue
            if any(word in q and equipment not in r["equipment"] for word,equipment in [("projector","Projector"),(" ac","AC")]): continue
            if day is not None and hour is not None:
                # Availability must use all bookings, even for a restricted user.
                if f"{day}:{hour}" in r["unavailable"] or any(x["room_id"]==r["id"] and x["day"]==day and x["start"]<=hour<x["start"]+x["duration"] for x in enriched(snapshot(db))): continue
            items.append(f'{r["name"]} · {r["capacity"]} seats · {", ".join(r["equipment"])}')
        answer="Matching rooms from the database."+(" Availability checked for the requested one-hour slot." if day is not None and hour is not None else " Specify a weekday and hour to check availability.")
    elif "optimiz" in q or "simulate" in q:
        require(user,["Registrar"]); answer="Open Optimization Lab to calculate alternatives. The published schedule changes only after approval and publication."; action="optimization"
    else:
        answer="I support timetable conflicts, room capacity and availability, faculty workload, and audit queries. Try ‘Why is CS302 in conflict?’ or ‘Find a free lab Thursday at 2’."
    return {"answer":answer,"items":items,"action":action,"mode":"Structured database assistant","context":ctx}

@app.get("/api/analytics")
def analytics(db=Depends(get_db),user=Depends(current_user)):
    w=workspace(db,user)
    return {"metrics":w["metrics"],"room_hours":[{"name":r["name"],"hours":sum(x["duration"] for x in w["sessions"] if x["room_id"]==r["id"])} for r in w["rooms"]],"daily_hours":[{"name":day[:3],"hours":sum(x["duration"] for x in w["sessions"] if x["day"]==i)} for i,day in enumerate(DAYS)]}
