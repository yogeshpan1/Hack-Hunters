from fastapi import HTTPException
from .models import AuditLog, ScheduleVersion, Student, User, Notification, Email
from .scheduling import serialize

def audit(db,user,action,entity,previous=None,new=None,reason="User request",result="Recorded"):
    db.add(AuditLog(user_id=user.id,actor=user.name,role=user.role,action=action,entity=entity,previous=previous or {},new=new or {},reason=reason,result=result))

def revision(db):
    return db.get(ScheduleVersion,1).revision

def bump(db,expected=None):
    expected=revision(db) if expected is None else expected
    db.bump_revision(expected)
    return expected+1

def communicate(db,session,reason):
    title=f'{session["code"]} · timetable updated'
    body=f'{session["code"]}: {session["room"]}, {["Monday","Tuesday","Wednesday","Thursday","Friday"][session["day"]]} {session["start"]:02}:00. {reason}'
    db.add(Notification(cohort_id=session["cohort_id"],faculty_id=session["faculty_id"],title=title,body=body))
    recipients={s.email for s in db.find(Student,{"cohort_id":session["cohort_id"],"status":"Active"})}
    recipients.update(u.email for u in db.find(User,{"faculty_id":session["faculty_id"],"active":True}))
    if not any(u for u in recipients if u.endswith("@nexus.demo")):
        recipients.add(f'faculty{session["faculty_id"]}@example.test')
    for email in sorted(recipients): db.add(Email(recipient=email,subject=title,body=body))
    return len(recipients)

def visible_sessions(user,sessions):
    if user.role=="Student": return [s for s in sessions if s["cohort_id"]==user.cohort_id]
    if user.role=="Faculty": return [s for s in sessions if s["faculty_id"]==user.faculty_id]
    return sessions
