from collections import Counter, defaultdict
from ortools.sat.python import cp_model
from .models import Room, Faculty, Cohort, Module, TimetableSession, Rule, Student

DAYS=["Monday","Tuesday","Wednesday","Thursday","Friday","Sunday"]
START_TICK, END_TICK = 13, 34

def ticks(start, duration):
    return range(round(start*2), round((start+duration)*2))

def time_label(hour):
    minutes=round(hour*60)
    return f"{minutes//60:02}:{minutes%60:02}"

def unavailable_at(values, day, start, duration):
    # Legacy integer day:hour entries reserve the full hour; .5 entries reserve 30 minutes.
    for value in values:
        d,h=value.split(':'); h=float(h)
        length=.5 if '.' in value else 1
        if int(d)==day and start<h+length and h<start+duration: return True
    return False


def serialize(obj):
    return obj.model_dump(exclude={"password_hash"})

def snapshot(db):
    data={key:[serialize(x) for x in db.find(model)] for key,model in [("rooms",Room),("faculty",Faculty),("cohorts",Cohort),("modules",Module),("sessions",TimetableSession),("rules",Rule)]}
    enrolled=Counter([x.cohort_id for x in db.find(Student,{"status":"Active"})])
    for cohort in data["cohorts"]:
        cohort["size"]=max(cohort["size"],enrolled[cohort["id"]])
    return data

def enriched(data, assignments=None):
    rooms={r["id"]:r for r in data["rooms"]}; mods={m["id"]:m for m in data["modules"]}
    faculty={f["id"]:f for f in data["faculty"]}; cohorts={c["id"]:c for c in data["cohorts"]}
    edits={s["id"]:s for s in assignments or []}
    result=[]
    for original in data["sessions"]:
        s={**original,**edits.get(original["id"],{})}; m=mods[s["module_id"]]; r=rooms[s["room_id"]]
        cids=s.get("cohort_ids") or [m["cohort_id"]]; groups=[cohorts[i] for i in cids]; c=groups[0]
        f=faculty[s.get("faculty_id") or m["faculty_id"]]
        result.append({**s,"code":m["code"],"module":m["name"],"faculty_id":f["id"],"faculty":f["name"],"cohort_id":c["id"],"cohort_ids":cids,"cohort":" + ".join(c["name"] for c in groups),"size":sum(c["size"] for c in groups),"room":r["name"],"capacity":r["capacity"],"room_type":s.get("room_type") or m["room_type"],"resources":s.get("resources") if s.get("resources") is not None else m["resources"]})
    return result

def conflicts(data, assignments=None, scenario=None):
    sessions=enriched(data,assignments); rooms={r["id"]:r for r in data["rooms"]}; faculty={f["id"]:f for f in data["faculty"]}; issues=[]
    def add(kind,ss,detail):
        issues.append({"id":f"{kind}-"+"-".join(str(s["id"]) for s in ss),"kind":kind,"session_ids":[s["id"] for s in ss],"code":ss[0]["code"],"detail":detail,"severity":"Critical"})
    for s in sessions:
        r=rooms[s["room_id"]]; f=faculty[s["faculty_id"]]
        if s["size"]>r["capacity"]: add("Capacity",[s],f'{s["size"]} students · {r["capacity"]}-seat {r["name"]}')
        if "Computers" in s["resources"] and s["size"]>r.get("pc_count",0): add("PC capacity",[s],f'{s["size"]} students need computers; {r["name"]} has {r.get("pc_count",0)} confirmed PCs')
        if r["kind"]!=s["room_type"] or not set(s["resources"]).issubset(r["equipment"]): add("Equipment",[s],f'{s["code"]} requires {s["room_type"]} with {", ".join(s["resources"])}')
        if not r["active"] or unavailable_at(r["unavailable"],s["day"],s["start"],s["duration"]) or (scenario and scenario.get("room_id")==r["id"] and scenario.get("day")==s["day"]): add("Room unavailable",[s],f'{r["name"]} is unavailable at this time')
        if unavailable_at(f["unavailable"],s["day"],s["start"],s["duration"]): add("Faculty unavailable",[s],f'{f["name"]} is unavailable at this time')
        if not (0<=s["day"]<6 and 6.5<=s["start"] and s["start"]+s["duration"]<=17): add("Teaching hours",[s],"Session falls outside Sunday–Friday, 06:30–17:00")
    for i,a in enumerate(sessions):
        for b in sessions[i+1:]:
            if a["day"]!=b["day"] or a["start"]>=b["start"]+b["duration"] or b["start"]>=a["start"]+a["duration"]: continue
            for field,kind in [("room_id","Room clash"),("faculty_id","Faculty clash"),("cohort_id","Cohort overlap")]:
                if (bool(set(a["cohort_ids"])&set(b["cohort_ids"])) if field=="cohort_id" else a[field]==b[field]): add(kind,[a,b],f'{a["code"]} and {b["code"]} overlap on {DAYS[a["day"]]} at {time_label(max(a["start"],b["start"]))}')
    return issues

def metrics(data,assignments=None,scenario=None):
    sessions=enriched(data,assignments); issues=conflicts(data,assignments,scenario); affected={i for c in issues for i in c["session_ids"]}; loads=Counter()
    for s in sessions: loads[s["faculty_id"]]+=s["duration"]
    occupied={(s["room_id"],s["day"],h) for s in sessions for h in ticks(s["start"],s["duration"])}
    available={(r["id"],d,h) for r in data["rooms"] if r["active"] for d in range(6) for h in range(START_TICK,END_TICK) if not unavailable_at(r["unavailable"],d,h/2,.5) and not (scenario and scenario.get("room_id")==r["id"] and scenario.get("day")==d)}
    overload=sum(loads[f["id"]]>f["max_hours"] for f in data["faculty"])
    return {"health":round(100*(1-len(affected)/len(sessions)),1) if sessions else 0,"conflicts":len(issues),"conflict_free":round(100*(1-len(affected)/len(sessions)),1) if sessions else 0,"utilization":round(100*len(occupied&available)/max(1,len(available)),1),"faculty_balance":round(100*(1-overload/len(data["faculty"])),1) if data["faculty"] else 0,"overloads":overload,"sessions":len(sessions),"teaching_hours":sum(s["duration"] for s in sessions)}

def solve(data,scenario=None,progress=None):
    progress=progress or (lambda stage,label:None)
    progress("constraints","Checking constraints")
    model=cp_model.CpModel(); sessions=enriched(data); faculty={f["id"]:f for f in data["faculty"]}; options={}; bookings=defaultdict(list); costs=[]
    weights={r["name"]:r["weight"] for r in data["rules"] if r["kind"]=="Soft"}
    cohort_day=defaultdict(list); faculty_day=defaultdict(list)
    progress("capacity","Checking room capacity, type and equipment")
    eligible={s['id']:[r for r in data['rooms'] if r['active'] and r['capacity']>=s['size'] and r['kind']==s['room_type'] and set(s['resources'])<=set(r['equipment']) and ('Computers' not in s['resources'] or r.get('pc_count',0)>=s['size'])] for s in sessions}
    progress("availability","Checking faculty and room availability")
    for s in sessions:
        candidates=[]
        for r in eligible[s["id"]]:
            if not r["active"] or r["capacity"]<s["size"] or r["kind"]!=s["room_type"] or not set(s["resources"]).issubset(r["equipment"]): continue
            if "Computers" in s["resources"] and r.get("pc_count",0)<s["size"]: continue
            for d in range(6):
                if scenario and scenario.get("room_id")==r["id"] and scenario.get("day")==d: continue
                for tick in range(START_TICK,END_TICK-round(s["duration"]*2)+1):
                    h=tick/2
                    if s["locked"] and (r["id"],d,h)!=(s["room_id"],s["day"],s["start"]): continue
                    if unavailable_at(r["unavailable"],d,h,s["duration"]) or unavailable_at(faculty[s["faculty_id"]]["unavailable"],d,h,s["duration"]): continue
                    v=model.NewBoolVar(f's{s["id"]}_r{r["id"]}_{d}_{h}')
                    candidates.append((v,{"id":s["id"],"room_id":r["id"],"day":d,"start":h}))
                    changed=(r["id"],d,h)!=(s["room_id"],s["day"],s["start"])
                    cost=int(changed)*weights.get("Minimize changes",10)+(weights.get("Avoid first period",2) if h==6.5 else 0)
                    costs.append(cost*v)
                    for hour in ticks(h,s["duration"]):
                        for kind,ident in [("room",r["id"]),("faculty",s["faculty_id"])]+[("cohort",cid) for cid in s["cohort_ids"]]: bookings[kind,ident,d,hour].append(v)
                    for cid in s["cohort_ids"]: cohort_day[cid,d].append(v)
                    faculty_day[s["faculty_id"],d].append(round(s["duration"]*2)*v)
        if not candidates:
            return {"status":"Infeasible","assignments":[],"explanation":f'{s["code"]} has no eligible room/time. Check capacity, equipment, availability, and its lock.'}
        model.AddExactlyOne(v for v,_ in candidates); options[s["id"]]=candidates
    progress("cohorts","Enforcing room, faculty and combined-cohort overlaps")
    for values in bookings.values(): model.AddAtMostOne(values)
    for key,values in cohort_day.items():
        used=model.NewBoolVar(f"cohort_day_{key}"); model.AddMaxEquality(used,values); costs.append(weights.get("Compact cohort days",1)*used)
    for key,values in faculty_day.items():
        excess=model.NewIntVar(0,200,f"excess_{key}"); model.Add(excess>=sum(values)-8); costs.append(weights.get("Balance faculty days",2)*excess)
    model.Minimize(sum(costs)); solver=cp_model.CpSolver(); solver.parameters.max_time_in_seconds=12; solver.parameters.num_search_workers=1; solver.parameters.random_seed=42
    progress("search","Testing alternatives with CP-SAT")
    status=solver.Solve(model)
    progress("validation","Independently checking solver output")
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        return {"status":"Infeasible" if status==cp_model.INFEASIBLE else "Timed out","assignments":[],"explanation":"No valid schedule found within the constraints." if status==cp_model.INFEASIBLE else "The solver reached its time limit without a valid solution. Try relaxing preferences or increasing available rooms."}
    assignments=[a for candidates in options.values() for v,a in candidates if solver.Value(v)]
    assert not conflicts(data,assignments,scenario), "Solver output failed independent validation"
    return {"status":"Review","assignments":assignments,"explanation":f'CP-SAT found a {"proven optimal" if status==cp_model.OPTIMAL else "feasible"} schedule with zero hard conflicts. Capacity, required equipment, availability, and session locks were independently rechecked. Weekly teaching totals remain unchanged; the solver balances their distribution across days.'}

def changes_for(data,assignments):
    before={s["id"]:s for s in enriched(data)}; changes=[]
    for s in enriched(data,assignments):
        old=before[s["id"]]
        if any(old[k]!=s[k] for k in ["room_id","day","start"]):
            changes.append({"id":s["id"],"code":s["code"],"before":{"room":old["room"],"day":old["day"],"start":old["start"]},"after":{"room":s["room"],"day":s["day"],"start":s["start"]},"reason":"Satisfies room capacity, equipment and availability; avoids room, faculty and cohort overlaps while minimizing disruption."})
    return changes
