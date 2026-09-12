from app.models import User, Programme, Faculty, Cohort, Student, Room, Module, TimetableSession, ExamSession, Rule, ScheduleVersion, AuditLog
from app.auth import password_hash

def seed(db):
    if db.first(User):
        return
    names = ["BSc (Hons) Computing", "Computing with AI", "Computer Networking & IT Security", "Multimedia Technologies", "MSc IT", "BA Business Administration", "BA Accounting & Finance", "MBA"]
    for i, name in enumerate(names, 1):
        db.add(Programme(id=i, name=name, department="Computing" if i <= 5 else "Business"))
    db.flush()
    for i, name in enumerate(["Priya Sharma", "Aarav Shrestha", "Nisha Karki", "Suman Gurung", "Anita Thapa", "Bikash Rai"], 1):
        db.add(Faculty(id=i, name=name, code=f"DEMO-F{i:03}", department="Computing" if i <= 4 else "Business", max_hours=14 if i == 1 else 18, unavailable=["4:15", "4:16"] if i == 1 else []))
    for i, size in enumerate([34, 28, 22, 30, 26, 32, 24, 20], 1):
        db.add(Cohort(id=i, name=f"{'CMP' if i<=5 else 'BUS'}-{i:02} · L{5 if i<=4 else 6}", programme_id=i, size=size, level=5 if i<=4 else 6))
    db.flush()
    rooms = [("Lab 2A",24,"Lab","Lab Cluster"),("Lab 4B",48,"Lab","Lab Cluster"),("B204",40,"Classroom","Main Building"),("K101",60,"Classroom","Kumari Block"),("Studio 1",36,"Studio","Studio Wing"),("B301",32,"Classroom","Main Building"),("Lab 3C",32,"Lab","Lab Cluster"),("K202",45,"Classroom","Kumari Block")]
    for i,(name,cap,kind,building) in enumerate(rooms,1):
        db.add(Room(id=i,name=name,capacity=cap,pc_count=cap if kind=="Lab" else 0,kind=kind,building=building,equipment=["Projector","AC","Whiteboard","Internet"]+(["Computers"] if kind=="Lab" else []),unavailable=[]))
    modules = [("CS302","Database Systems",1,1,1,"Lab"),("CS205","Web Application Development",1,2,1,"Lab"),("AI301","Machine Learning",2,1,2,"Lab"),("NW303","Network Infrastructure",3,3,3,"Lab"),("MM201","Digital Media Studio",4,4,4,"Studio"),("IT501","Research Methods",5,4,5,"Classroom"),("BA201","Organisational Behaviour",6,5,6,"Classroom"),("AF301","Financial Reporting",7,6,7,"Classroom"),("MBA501","Strategic Management",8,5,8,"Classroom"),("CS304","Software Engineering",1,3,1,"Classroom")]
    for i,(code,name,p,f,c,kind) in enumerate(modules,1):
        db.add(Module(id=i,code=code,name=name,programme_id=p,faculty_id=f,cohort_id=c,room_type=kind,resources=["Computers"] if kind=="Lab" else ["Projector"]))
    db.flush()
    # Deliberately invalid starting schedule, resolved by the actual solver.
    rows=[(1,1,1,11),(2,1,1,11),(3,2,1,11),(4,7,0,9),(5,5,0,11),(6,3,0,13),(7,6,0,9),(8,3,1,9),(9,4,2,11),(10,3,1,11),(1,1,3,11),(2,2,2,9),(3,7,3,11),(4,1,4,9),(5,5,2,13),(6,8,4,11),(7,6,3,9),(8,3,3,13),(9,4,4,13),(10,8,2,11),(1,2,0,15),(3,2,4,15),(2,7,4,11),(7,3,2,13)]
    for i,(m,r,d,s) in enumerate(rows,1):
        db.add(TimetableSession(id=i,module_id=m,room_id=r,day=d,start=s,duration=2,locked=i==4,state="locked" if i==4 else "normal"))
    for c in db.find(Cohort):
        for j in range(c.size):
            n=(c.id-1)*100+j+1
            db.add(Student(code=f"DEMO-S{n:04}",name=f"Demo student {n:04}",email=f"student{n:04}@example.test",cohort_id=c.id))
    hashed=password_hash("NexusDemo!2026")
    users=[("R. Bhandari","registrar","Registrar"),("System Administrator","admin","Super Admin"),("Admissions Office","admissions","Admissions"),("HR Office","hr","HR Admin"),("Programme Office","programme","Programme Admin"),("Facilities Office","facilities","Facilities Admin"),("Priya Sharma","faculty","Faculty"),("Demo Student","student","Student")]
    for i,(name,handle,role) in enumerate(users,1):
        db.add(User(id=i,name=name,email=f"{handle}@nexus.demo",password_hash=hashed,role=role,faculty_id=1 if role=="Faculty" else None,cohort_id=1 if role=="Student" else None))
    db.add(ScheduleVersion(id=1,revision=1))
    for name in ["No room double booking","No faculty double booking","No cohort overlaps","Capacity and required equipment","Availability and locked sessions"]:
        db.add(Rule(name=name,kind="Hard",weight=1))
    for name,weight in [("Minimize changes",10),("Avoid first period",2),("Compact cohort days",1),("Balance faculty days",2)]:
        db.add(Rule(name=name,kind="Soft",weight=weight))
    db.flush()
    db.add(AuditLog(user_id=2,actor="System Administrator",role="Super Admin",action="DEMO INITIALIZED",entity="Academic timetable",reason="Deterministic fictional dataset for the hackathon",new={"sessions":len(rows)},result="Ready"))
    for i in range(1,6):
        db.add(ExamSession(module_id=i,room_id=2 if i<5 else 5,invigilator_id=i,date=f"2026-12-{7+i:02}",start=10,duration=2,status="Draft"))
    db.commit()
