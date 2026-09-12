from fastapi import HTTPException
from .models import AuditLog, ScheduleVersion, Student, User, Notification, Email, Faculty
from .scheduling import serialize,time_label,DAYS

def audit(db,user,action,entity,previous=None,new=None,reason="User request",result="Recorded"):
    db.add(AuditLog(user_id=user.id,actor=user.name,role=user.role,action=action,entity=entity,previous=previous or {},new=new or {},reason=reason,result=result))

def revision(db):
    return db.get(ScheduleVersion,1).revision

def bump(db,expected=None):
    expected=revision(db) if expected is None else expected
    db.bump_revision(expected)
    return expected+1

def communicate(db,session,reason,user=None):
    title=f'{session["code"]} · timetable updated'
    body=f'{session["code"]}: {session["room"]}, {DAYS[session["day"]]} {time_label(session["start"])}. {reason}'
    db.add(Notification(faculty_id=session["faculty_id"],title=title,body=body))
    for cid in session.get("cohort_ids",[session["cohort_id"]]): db.add(Notification(cohort_id=cid,title=title,body=body))
    recipients={s.email for s in db.find(Student,{"cohort_id":{"$in":session.get("cohort_ids",[session["cohort_id"]])},"status":"Active"})}
    recipients.update(u.email for u in db.find(User,{"faculty_id":session["faculty_id"],"active":True}))
    faculty=db.get(Faculty,session["faculty_id"])
    if faculty and faculty.email: recipients.add(faculty.email)
    for email in sorted(recipients): db.add(Email(recipient=email,subject=title,body=body))
    if user:
        for action,detail in [("AFFECTED USERS IDENTIFIED",{"recipients":len(recipients)}),("NOTIFICATIONS CREATED",{"cohorts":session.get("cohort_ids",[session["cohort_id"]]),"faculty_id":session["faculty_id"]}),("EMAILS PREPARED",{"drafts":len(recipients),"delivery":"Not sent"})]:
            audit(db,user,action,f"Session {session['id']}",new=detail,reason=reason)
    return len(recipients)

def visible_sessions(user,sessions):
    if user.role=="Student": return [s for s in sessions if user.cohort_id in s.get("cohort_ids",[s["cohort_id"]])]
    if user.role=="Faculty": return [s for s in sessions if s["faculty_id"]==user.faculty_id]
    return sessions
