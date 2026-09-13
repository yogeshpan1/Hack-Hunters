"""Read-only search and deterministic, context-aware database assistance."""
from fastapi import APIRouter,Depends
from .db import get_db
from .auth import current_user,require
from . import models as m,schemas as s
from .scheduling import snapshot,enriched,conflicts,serialize,DAYS,time_label,unavailable_at
router=APIRouter()

@router.get("/api/integrations/status")
def integrations(user=Depends(current_user)):
    from .providers import provider_status
    return provider_status()


@router.get("/api/search")
def search(q:str="",db=Depends(get_db),user=Depends(current_user)):
    from .main import workspace
    if not q.strip(): return []
    w=workspace(db,user); results=[]
    for key in ["rooms","faculty","modules","cohorts","programmes"]:
        for row in w[key]:
            if q.lower() in str(row).lower(): results.append({"entity":key,"id":row["id"],"label":row.get("code",row.get("name")),"detail":row.get("name","")})
    if user.role not in ["Faculty","Student"]:
        sources=[("students",m.Student)] if user.role in ["SuperAdmin","Super Admin","Registrar","RTE"] else []
        if user.role in ["SuperAdmin","Super Admin","Registrar"]: sources += [("audit",m.AuditLog),("exams",m.ExamSession)]
        for key,model in sources:
            for row in db.find(model,descending=True,limit=500):
                value=serialize(row)
                if q.lower() in str(value).lower(): results.append({"entity":key,"id":row.id,"label":value.get("code",value.get("action",f"Exam {row.id}")),"detail":value.get("name",value.get("entity",value.get("date","")))})
    return results[:30]

@router.post("/api/assistant")
def assistant(body:s.Question,db=Depends(get_db),user=Depends(current_user)):
    from .main import workspace,audit_log
    import re
    from .providers import normalize_question
    query, ai_used = normalize_question(body.query, body.history)
    w=workspace(db,user); q=query.lower(); ctx=body.context; sessions=w["sessions"]
    target=next((x for x in sessions if x["id"]==ctx.get("session_id") or x["code"].lower() in q),None)
    answer=""; items=[]; action=None
    room_context=next((r for r in w['rooms'] if r['id']==ctx.get('room_id')),None)
    if not target and room_context and any(x in q for x in ['better','alternative','this','change']):
        matching=[x for x in sessions if x['room_id']==room_context['id']]
        if len(matching)==1: target=matching[0]
        elif len(matching)>1: return {'answer':f"{room_context['name']} has multiple sessions. Select the teaching session so I can check its exact cohort, teacher, capacity and time.",'items':[f"{x['code']} · {DAYS[x['day']]} {time_label(x['start'])}" for x in matching],'action':'timetable','mode':'Structured database assistant','context':ctx}
        else: return {'answer':f"{room_context['name']} has no teaching sessions in the current view. There is no class allocation to improve.",'items':[],'action':None,'mode':'Structured database assistant','context':ctx}
    if "who changed" in q or "audit" in q:
        require(user,["SuperAdmin"]); rows=audit_log(db,user)
        if target: rows=[x for x in rows if x["entity"]==f'Session {target["id"]}']
        elif room_context: rows=[x for x in rows if x['entity'] in [f"rooms/{room_context['id']}",room_context['name']]]
        items=[f'{x["actor"]}: {x["action"]} · {x["reason"]}' for x in rows[:5]]; answer="These are the recorded changes." if items else "There are no recorded changes for this session."
    elif "workload" in q or "overload" in q or "heaviest" in q:
        loads=[(f,sum(x["duration"] for x in sessions if x["faculty_id"]==f["id"])) for f in w["faculty"] if not ctx.get("faculty_id") or f["id"]==ctx["faculty_id"]]; loads.sort(key=lambda x:-x[1]); items=[f'{f["name"]}: {h} hours / {f["max_hours"]} weekly target' for f,h in loads]; answer="Teaching hours are calculated from the current timetable. Moving sessions can improve daily distribution, but does not reduce total teaching hours."
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
        items=[f'{f["name"]} · {f["department"]}' for f in w["faculty"] if ("computing" not in q or "computing" in f["department"].lower()) and (not ctx.get("faculty_id") or f["id"]==ctx["faculty_id"])]; answer="Faculty records available to your role."
    elif any(word in q for word in ["room","lab","capacity","projector"]):
        cap=re.search(r"(?:for|accommodate|capacity(?: for)?)\s*(\d+)",q); minimum=int(cap.group(1)) if cap else 0
        day=next((i for i,d in enumerate(DAYS) if d.lower() in q),None); tm=re.search(r"(?:at|after)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",q); hour=(int(tm.group(1))+(int(tm.group(2) or 0)/60)) if tm else None
        if hour is not None and ((tm.group(3)=="pm" and hour<12) or (not tm.group(3) and hour<6.5)): hour+=12
        for r in w["rooms"]:
            if not r["active"] or r["capacity"]<minimum or ("lab" in q and r["kind"]!="Lab"): continue
            if any(word in q and equipment not in r["equipment"] for word,equipment in [("projector","Projector"),(" ac","AC")]): continue
            if day is not None and hour is not None:
                # Availability must use all bookings, even for a restricted user.
                if hour<6.5 or hour+1>17 or unavailable_at(r["unavailable"],day,hour,1) or any(x["room_id"]==r["id"] and x["day"]==day and x["start"]<hour+1 and hour<x["start"]+x["duration"] for x in enriched(snapshot(db))): continue
            items.append(f'{r["name"]} · {r["capacity"]} seats · {", ".join(r["equipment"])}')
        answer="Matching rooms from the database."+(" Availability checked for the requested one-hour slot." if day is not None and hour is not None else " Specify a weekday and hour to check availability.")
    elif "optimiz" in q or "simulate" in q:
        require(user,["RTE"]); answer="Open Optimization Lab to calculate alternatives. The published schedule changes only after approval and publication."; action="optimization"
    else:
        answer="I support timetable conflicts, room capacity and availability, faculty workload, and audit queries. Select a timetable session and ask why it conflicts, or ask ‘Find a free lab Thursday at 2’."
    if user.role=="SSD": action=None
    return {"answer":answer,"items":items,"action":action,"mode":"AI-assisted database search" if ai_used else "Structured database assistant","context":ctx}
