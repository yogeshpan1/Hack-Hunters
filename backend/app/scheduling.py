from collections import Counter, defaultdict
from ortools.sat.python import cp_model
from .models import Room, Faculty, Cohort, Module, TimetableSession, Rule, Student, ExamSession

DAYS=["Monday","Tuesday","Wednesday","Thursday","Friday","Sunday"]
START_TICK, END_TICK = 13, 34

def ticks(start, duration):
    return range(round(start*2), round((start+duration)*2))

def time_label(hour):
    minutes=round(hour*60)
    return f"{minutes//60:02}:{minutes%60:02}"

def scenario_blocks(session, room_id, day, scenario):
    if not scenario or scenario.get("day") != day:
        return False
    return session["faculty_id"] == scenario.get("faculty_id") if scenario.get("kind")=="faculty" else room_id == scenario.get("room_id")

def patterns_overlap(first, second):
    return first == "Weekly" or second == "Weekly" or first == second

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
    data={key:[serialize(x) for x in db.find(model)] for key,model in [("rooms",Room),("faculty",Faculty),("cohorts",Cohort),("modules",Module),("sessions",TimetableSession),("rules",Rule),("exams",ExamSession)]}
    enrolled=Counter(db.count_by(Student,"cohort_id",{"status":"Active"}))
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
        cohort_label=" + ".join(c["name"] for c in groups)
        if s.get("section_label"):
            cohort_label=f"{cohort_label} · {s['section_label']}"
        result.append({**s,"code":m["code"],"module":m["name"],"faculty_id":f["id"],"faculty":f["name"],"cohort_id":c["id"],"cohort_ids":cids,"cohort":cohort_label,"study_levels":sorted({group.get("study_level", "Second Year") for group in groups}),"size":s.get("planned_size") or sum(c["size"] for c in groups),"room":r["name"],"capacity":r["capacity"],"room_type":s.get("room_type") or m["room_type"],"resources":s.get("resources") if s.get("resources") is not None else m["resources"]})
    return result

def academic_policy_conflicts(sessions):
    issues=[]; reported=set()
    def add(kind, rows, detail):
        issue_id=f"{kind}-"+"-".join(str(row["id"]) for row in rows)
        if issue_id in reported:
            return
        reported.add(issue_id)
        issues.append({"id":issue_id,"kind":kind,"session_ids":[row["id"] for row in rows],"code":rows[0]["code"],"detail":detail,"severity":"Critical"})
    by_cohort=defaultdict(list); by_faculty=defaultdict(list)
    for session in sessions:
        levels=set(session["study_levels"])
        for cohort_id in session["cohort_ids"]: by_cohort[cohort_id].append(session)
        by_faculty[session["faculty_id"]].append(session)
        if "Masters" in levels and session["start"]+session["duration"]>9: add("Masters teaching window",[session],"Masters teaching must finish by 09:00.")
        if "Third Year" in levels and session["start"]+session["duration"]>11: add("Third Year teaching window",[session],"Third Year teaching must finish by 11:00.")
        if "Third Year" in levels and session["session_type"]=="Tutorial": add("Third Year session pattern",[session],"Third Year programmes use lectures and workshops, not tutorials.")
        if not levels.intersection({"Third Year","Masters"}) and session["start"]<7: add("Teaching hours",[session],"Undergraduate teaching begins at 07:00; only Third Year and Masters sessions may start at 06:30.")
        expected={"Lecture":1.5,"Tutorial":1,"Workshop":2}.get(session["session_type"])
        if expected is not None and session["duration"]!=expected: add("Pedagogy duration",[session],f'{session["session_type"]} sessions must run for {expected:g} hour(s).')
    for cohort_sessions in by_cohort.values():
        by_day=defaultdict(list)
        for session in cohort_sessions: by_day[session["day"]].append(session)
        for day_sessions in by_day.values():
            # Alternating A/B-week deliveries never happen in the same week.
            # Evaluate daily policies separately for each delivery week while
            # retaining common Weekly classes in both evaluations.
            for delivery_week in ("A Week", "B Week"):
                ordered=sorted((session for session in day_sessions if patterns_overlap(session.get("week_pattern","Weekly"),delivery_week)),key=lambda session:session["start"])
                levels={level for session in ordered for level in session["study_levels"]}
                for index,previous in enumerate(ordered):
                    for current in ordered[index+1:]:
                        ranks={"Lecture":0,"Tutorial":1,"Workshop":2}
                        if previous['module_id']==current['module_id'] and ranks.get(previous['session_type'],0)>ranks.get(current['session_type'],2):
                            add("Pedagogy order",[previous,current],"Same-day delivery of a module follows Lecture, Tutorial, then Workshop.")
                if "Third Year" in levels:
                    if len(ordered)>2: add("Third Year daily load",ordered,"Third Year cohorts may have at most two classes in one day.")
                    workshops=[session for session in ordered if session["session_type"]=="Workshop"]
                    non_workshops=[session for session in ordered if session["session_type"] not in {"Workshop","Teaching"}]
                    if len(workshops)>1 or (workshops and non_workshops): add("Third Year session pattern",ordered,"Third Year workshop days contain one workshop; two-class days are lecture-only.")
                if "First Year" in levels:
                    uninterrupted=1
                    for previous,current in zip(ordered,ordered[1:]):
                        uninterrupted=uninterrupted+1 if current["start"]-(previous["start"]+previous["duration"])<1 else 1
                        if uninterrupted>2: add("First Year break",[previous,current],"First Year cohorts need a minimum one-hour break after one or two consecutive classes.")
    for faculty_sessions in by_faculty.values():
        if any("Masters" in session["study_levels"] for session in faculty_sessions):
            for session in faculty_sessions:
                if "Masters" not in session["study_levels"] and session["start"]<9: add("Masters faculty handover",[session],"Faculty who teach Masters classes cannot be scheduled with undergraduate teaching before 09:00.")
    return issues

def exam_commitments(session, data):
    from datetime import date
    issues=[]
    mods={m['id']:m for m in data['modules']}
    for exam in data.get('exams',[]):
        weekday=date.fromisoformat(exam['date']).weekday()
        day=5 if weekday==6 else weekday
        if weekday==5 or session['day']!=day or session['start']>=exam['start']+exam['duration'] or exam['start']>=session['start']+session['duration']: continue
        allocations=exam.get('venue_allocations') or []
        rooms=[a['room_id'] for a in allocations] if allocations else exam.get('room_ids') or [exam['room_id']]
        staff=[fid for a in allocations for fid in a['invigilator_ids']] if allocations else exam.get('invigilator_ids') or [exam['invigilator_id']]
        cohorts=exam.get('cohort_ids') or ([mods[exam['module_id']]['cohort_id']] if exam['module_id'] in mods else [])
        if session['room_id'] in rooms or session['faculty_id'] in staff or set(session['cohort_ids'])&set(cohorts): issues.append(f"Exam {exam['id']} on {exam['date']} reserves this room, faculty member or cohort.")
    return issues


def conflicts(data, assignments=None, scenario=None):
    sessions=enriched(data,assignments); rooms={r["id"]:r for r in data["rooms"]}; faculty={f["id"]:f for f in data["faculty"]}; issues=[]
    def add(kind,ss,detail):
        issues.append({"id":f"{kind}-"+"-".join(str(s["id"]) for s in ss),"kind":kind,"session_ids":[s["id"] for s in ss],"code":ss[0]["code"],"detail":detail,"severity":"Critical"})
    issues.extend(academic_policy_conflicts(sessions))
    for session in sessions:
        if faculty[session["faculty_id"]].get("attends_masters") and "Masters" not in session["study_levels"] and session["start"]<9:
            add("Masters faculty handover",[session],"This faculty member attends Masters classes; undergraduate teaching starts at 09:00 or later.")
    for s in sessions:
        r=rooms[s["room_id"]]; f=faculty[s["faculty_id"]]
        for detail in exam_commitments(s,data): add("Exam commitment",[s],detail)
        if s["size"]>r["capacity"]: add("Capacity",[s],f'{s["size"]} students · {r["capacity"]}-seat {r["name"]}')
        if "Computers" in s["resources"] and s["size"]>r.get("pc_count",0): add("PC capacity",[s],f'{s["size"]} students need computers; {r["name"]} has {r.get("pc_count",0)} confirmed PCs')
        if r["kind"]!=s["room_type"] or not set(s["resources"]).issubset(r["equipment"]): add("Equipment",[s],f'{s["code"]} requires {s["room_type"]} with {", ".join(s["resources"])}')
        if not r["active"] or unavailable_at(r["unavailable"],s["day"],s["start"],s["duration"]): add("Room unavailable",[s],f'{r["name"]} is unavailable at this time')
        if scenario_blocks(s,r["id"],s["day"],scenario): add("Scenario unavailable",[s],f'This {scenario.get("kind", "room")} is unavailable on {DAYS[s["day"]]}.')
        if unavailable_at(f["unavailable"],s["day"],s["start"],s["duration"]): add("Faculty unavailable",[s],f'{f["name"]} is unavailable at this time')
        if not (0<=s["day"]<6 and 6.5<=s["start"] and s["start"]+s["duration"]<=17): add("Teaching hours",[s],"Session falls outside Sunday–Friday, 06:30–17:00")
    for i,a in enumerate(sessions):
        for b in sessions[i+1:]:
            if not patterns_overlap(a.get("week_pattern","Weekly"),b.get("week_pattern","Weekly")) or a["day"]!=b["day"] or a["start"]>=b["start"]+b["duration"] or b["start"]>=a["start"]+a["duration"]: continue
            for field,kind in [("room_id","Room clash"),("faculty_id","Faculty clash"),("cohort_id","Cohort overlap")]:
                if (bool(set(a["cohort_ids"])&set(b["cohort_ids"])) if field=="cohort_id" else a[field]==b[field]): add(kind,[a,b],f'{a["code"]} and {b["code"]} overlap on {DAYS[a["day"]]} at {time_label(max(a["start"],b["start"]))}')
    return issues

def metrics(data,assignments=None,scenario=None):
    sessions=enriched(data,assignments); issues=conflicts(data,assignments,scenario); affected={i for c in issues for i in c["session_ids"]}; loads=Counter()
    for s in sessions: loads[s["faculty_id"]]+=s["duration"]
    occupied={(s["room_id"],s["day"],h) for s in sessions for h in ticks(s["start"],s["duration"])}
    available={(r["id"],d,h) for r in data["rooms"] if r["active"] for d in range(6) for h in range(START_TICK,END_TICK) if not unavailable_at(r["unavailable"],d,h/2,.5) and not (scenario and scenario.get("kind", "room")=="room" and scenario.get("room_id")==r["id"] and scenario.get("day")==d)}
    overload=sum(loads[f["id"]]>f["max_hours"] for f in data["faculty"])
    return {"health":round(100*(1-len(affected)/len(sessions)),1) if sessions else 0,"conflicts":len(issues),"conflict_free":round(100*(1-len(affected)/len(sessions)),1) if sessions else 0,"utilization":round(100*len(occupied&available)/max(1,len(available)),1),"faculty_balance":round(100*(1-overload/len(data["faculty"])),1) if data["faculty"] else 0,"overloads":overload,"sessions":len(sessions),"teaching_hours":sum(s["duration"] for s in sessions)}

def solve(data,scenario=None,progress=None,strategy='balanced'):
    progress=progress or (lambda stage,label:None)
    progress("constraints","Checking constraints")
    model=cp_model.CpModel(); sessions=enriched(data); faculty={f["id"]:f for f in data["faculty"]}; options={}; bookings=defaultdict(list); costs=[]
    weights={r["name"]:r["weight"] for r in data["rules"] if r["kind"]=="Soft"}
    if strategy=='faculty': weights['Balance faculty days']=max(20,weights.get('Balance faculty days',2)*5)
    cohort_day=defaultdict(list); faculty_day=defaultdict(list); first_year_day=defaultdict(list); third_year_day=defaultdict(list); third_workshops=defaultdict(list); third_non_workshops=defaultdict(list); first_year_starts=defaultdict(list); second_year_options=defaultdict(list)
    masters_faculty={s["faculty_id"] for s in sessions if "Masters" in s["study_levels"]}|{f["id"] for f in data["faculty"] if f.get("attends_masters")}
    progress("capacity","Checking room capacity, type and equipment")
    # Full-catalogue planning can contain hundreds of valid sessions. Retain the
    # best-fit alternatives plus the current room, which gives the optimizer a
    # meaningful choice without creating an unnecessarily large search model.
    def suitable_rooms(session):
        choices=[room for room in data["rooms"] if room["active"] and room["capacity"]>=session["size"] and room["kind"]==session["room_type"] and set(session["resources"]).issubset(room["equipment"]) and ("Computers" not in session["resources"] or room.get("pc_count",0)>=session["size"])]
        choices.sort(key=lambda room:(room["capacity"]-session["size"],room["id"]))
        selected=choices[:6]
        current=next((room for room in choices if room["id"]==session["room_id"]),None)
        if current and current not in selected:
            selected.append(current)
        return selected
    eligible={s['id']:suitable_rooms(s) for s in sessions}
    # A repair only needs to explore sessions involved in a current conflict or
    # the selected What-If incident. Stable sessions remain fixed, which keeps
    # the full-catalogue simulation responsive and limits disruption.
    repair_ids={session_id for issue in conflicts(data,scenario=scenario) for session_id in issue["session_ids"]}
    progress("availability","Checking faculty and room availability")
    for s in sessions:
        levels=set(s["study_levels"])
        expected={"Lecture":1.5,"Tutorial":1,"Workshop":2}.get(s["session_type"])
        if expected is not None and s["duration"] != expected:
            return {"status":"Infeasible","assignments":[],"explanation":f'{s["code"]} has an invalid {s["session_type"]} duration. Correct the session before optimization.'}
        candidates=[]
        fixed=s["id"] not in repair_ids
        room_choices=eligible[s["id"]] if not fixed else [next(room for room in data["rooms"] if room["id"]==s["room_id"])]
        day_choices=range(6) if not fixed else (s["day"],)
        tick_choices=range(START_TICK,END_TICK-round(s["duration"]*2)+1) if not fixed else (round(s["start"]*2),)
        for r in room_choices:
            if not fixed and (not r["active"] or r["capacity"]<s["size"] or r["kind"]!=s["room_type"] or not set(s["resources"]).issubset(r["equipment"])): continue
            if not fixed and "Computers" in s["resources"] and r.get("pc_count",0)<s["size"]: continue
            for d in day_choices:
                if not fixed and scenario_blocks(s,r["id"],d,scenario): continue
                for tick in tick_choices:
                    h=tick/2
                    if "Masters" in levels and h+s["duration"]>9: continue
                    if "Third Year" in levels and (h+s["duration"]>11 or s["session_type"]=="Tutorial"): continue
                    if not levels.intersection({"Third Year","Masters"}) and h<7: continue
                    if "Masters" not in levels and s["faculty_id"] in masters_faculty and h<9: continue
                    if s["locked"] and (r["id"],d,h)!=(s["room_id"],s["day"],s["start"]): continue
                    if unavailable_at(r["unavailable"],d,h,s["duration"]) or unavailable_at(faculty[s["faculty_id"]]["unavailable"],d,h,s["duration"]): continue
                    candidate={"id":s["id"],"room_id":r["id"],"day":d,"start":h}
                    if exam_commitments({**s,**candidate},data): continue
                    v=model.NewBoolVar(f's{s["id"]}_r{r["id"]}_{d}_{h}')
                    candidates.append((v,candidate))
                    changed=(r["id"],d,h)!=(s["room_id"],s["day"],s["start"])
                    cost=int(changed)*weights.get("Minimize changes",10)+(weights.get("Avoid first period",2) if h==6.5 else 0)
                    if strategy=='rooms': cost += (r['capacity']-s['size'])//5
                    costs.append(cost*v)
                    for hour in ticks(h,s["duration"]):
                        patterns=("A Week","B Week") if s.get("week_pattern","Weekly")=="Weekly" else (s["week_pattern"],)
                        for kind,ident in [("room",r["id"]),("faculty",s["faculty_id"])]+[("cohort",cid) for cid in s["cohort_ids"]]:
                            for pattern in patterns: bookings[kind,ident,d,hour,pattern].append(v)
                    delivery_weeks=("A Week","B Week") if s.get("week_pattern","Weekly")=="Weekly" else (s["week_pattern"],)
                    for cid in s["cohort_ids"]:
                        for delivery_week in delivery_weeks:
                            cohort_day[cid,d,delivery_week].append(v)
                            if "Second Year" in levels: second_year_options[cid,d,delivery_week].append((v,tick,round((h+s["duration"])*2)))
                            if "First Year" in levels:
                                first_year_day[cid,d,delivery_week].append(v)
                                first_year_starts[cid,d,delivery_week,tick].append(v)
                            if "Third Year" in levels:
                                third_year_day[cid,d,delivery_week].append(v)
                                (third_workshops if s["session_type"]=="Workshop" else third_non_workshops)[cid,d,delivery_week].append(v)
                    faculty_day[s["faculty_id"],d].append(round(s["duration"]*2)*v)
        if not candidates:
            return {"status":"Infeasible","assignments":[],"explanation":f'{s["code"]} has no eligible room/time. Check capacity, equipment, availability, and its lock.'}
        model.AddExactlyOne(v for v,_ in candidates); options[s["id"]]=candidates
    progress("cohorts","Enforcing room, faculty and combined-cohort overlaps")
    for values in bookings.values(): model.AddAtMostOne(values)
    for key,values in cohort_day.items():
        used=model.NewBoolVar(f"cohort_day_{key}"); model.AddMaxEquality(used,values); costs.append(weights.get("Compact cohort days",1)*used)
    # Automaton counts class starts since the last two idle half-hour ticks.
    # More than two classes are allowed once a full one-hour break resets the count.
    transitions=[]
    for count in range(3):
        for idle in range(2):
            state=count*2+idle
            transitions.append((state,0,0 if idle else count*2+1))
            transitions.append((state,1,count*2))
            if count<2: transitions.append((state,2,(count+1)*2))
    for cid,day,delivery_week in first_year_day:
        labels=[]
        for tick in range(START_TICK,END_TICK):
            label=model.NewIntVar(0,2,f"break_{cid}_{day}_{delivery_week}_{tick}")
            model.Add(label==sum(bookings['cohort',cid,day,tick,delivery_week])+sum(first_year_starts[cid,day,delivery_week,tick]))
            labels.append(label)
        model.AddAutomaton(labels,0,list(range(6)),transitions)
    for values in third_year_day.values(): model.Add(sum(values)<=2)
    for key,values in third_workshops.items():
        model.Add(sum(values)<=1)
        model.Add(sum(third_non_workshops[key])<=2*(1-sum(values)))
    # The teaching order applies within a day; recurring weeks can span delivery cycles.
    rank={"Lecture":0,"Tutorial":1,"Workshop":2}
    session_start={}; session_day={}
    for s in sessions:
        start=model.NewIntVar(13,34,f"start_{s['id']}"); day=model.NewIntVar(0,5,f"day_{s['id']}")
        model.Add(start==sum(round(a['start']*2)*v for v,a in options[s['id']]))
        model.Add(day==sum(a['day']*v for v,a in options[s['id']]))
        session_start[s['id']]=start; session_day[s['id']]=day
    for i,a in enumerate(sessions):
        for b in sessions[i+1:]:
            if a['module_id']!=b['module_id'] or not set(a['cohort_ids'])&set(b['cohort_ids']) or a['session_type'] not in rank or b['session_type'] not in rank or rank[a['session_type']]==rank[b['session_type']]: continue
            first,second=(a,b) if rank[a['session_type']]<rank[b['session_type']] else (b,a)
            same=model.NewBoolVar(f"same_day_{a['id']}_{b['id']}")
            model.Add(session_day[a['id']]==session_day[b['id']]).OnlyEnforceIf(same)
            model.Add(session_day[a['id']]!=session_day[b['id']]).OnlyEnforceIf(same.Not())
            model.Add(session_start[first['id']]+round(first['duration']*2)<=session_start[second['id']]).OnlyEnforceIf(same)
    for key,values in second_year_options.items():
        first=model.NewIntVar(13,34,f"first_{key}"); last=model.NewIntVar(13,34,f"last_{key}")
        used=model.NewBoolVar(f"second_used_{key}"); model.AddMaxEquality(used,[v for v,_,_ in values])
        for v,start,end in values:
            model.Add(first<=start).OnlyEnforceIf(v); model.Add(last>=end).OnlyEnforceIf(v)
        span=model.NewIntVar(0,21,f"span_{key}")
        model.Add(span==last-first).OnlyEnforceIf(used); model.Add(span==0).OnlyEnforceIf(used.Not())
        costs.append(weights.get("Compact second-year gaps",3)*span)
    for key,values in faculty_day.items():
        excess=model.NewIntVar(0,200,f"excess_{key}"); model.Add(excess>=sum(values)-8); costs.append(weights.get("Balance faculty days",2)*excess)
    model.Minimize(sum(costs)); solver=cp_model.CpSolver(); solver.parameters.max_time_in_seconds=6; solver.parameters.num_search_workers=1; solver.parameters.random_seed=42
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
