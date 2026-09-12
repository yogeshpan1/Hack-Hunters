import {NavLink,Outlet,useLocation,useNavigate} from "react-router-dom";
import {LayoutDashboard,CalendarRange,GraduationCap,FlaskConical,Waypoints,ChartNoAxesCombined,Building2,Users,Boxes,BookOpen,SlidersHorizontal,History,Search,Bell,PanelLeftClose,PanelLeft,LogOut,Settings,ChevronRight} from "lucide-react";
import {roleLabel} from "../types";
import NexusSeal from "./Brand";
import {Button} from "./ui";
import {useApp} from "../context";

export const NAV=[
 {group:"OPERATE",path:"overview",label:"Command Center",icon:LayoutDashboard},{group:"OPERATE",path:"timetable",label:"Timetable Studio",icon:CalendarRange},{group:"OPERATE",path:"exams",label:"Examinations",icon:GraduationCap},
 {group:"INTELLIGENCE",path:"optimization",label:"Optimization Lab",icon:FlaskConical,roles:["Registrar"]},{group:"INTELLIGENCE",path:"whatif",label:"What-If Simulator",icon:Waypoints,roles:["Registrar"]},{group:"INTELLIGENCE",path:"analytics",label:"Analytics",icon:ChartNoAxesCombined},
 {group:"MANAGE",path:"rooms",label:"Rooms & Resources",icon:Building2},{group:"MANAGE",path:"faculty",label:"Faculty Intelligence",icon:Users},{group:"MANAGE",path:"cohorts",label:"Cohort Flow",icon:Waypoints},{group:"MANAGE",path:"modules",label:"Modules",icon:Boxes},{group:"MANAGE",path:"programmes",label:"Programmes",icon:BookOpen},
 {group:"ADMINISTRATION",path:"students",label:"Students",icon:GraduationCap,roles:["Registrar"]},
 {group:"SYSTEM",path:"rules",label:"Scheduling Rules",icon:SlidersHorizontal},{group:"SYSTEM",path:"notifications",label:"Communications",icon:Bell},{group:"SYSTEM",path:"audit",label:"Change Log",icon:History,roles:["Registrar"]},{group:"SYSTEM",path:"settings",label:"Settings",icon:Settings}
];

export default function Shell(){
 const {user,workspace,collapsed,setCollapsed,setPalette,logout,can}=useApp();
 const location=useLocation();
 const navigate=useNavigate();
 const active=NAV.find(item=>location.pathname===`/${item.path}`);
 const items=NAV.filter(item=>!item.roles||can(...item.roles));
 return <div className={`app-shell ${collapsed?"collapsed":""}`}>
  <aside className="sidebar">
   <NavLink to="/overview" className="brand-lockup"><NexusSeal size={38}/><div><span>ISLINGTON COLLEGE</span><strong>NEXUS</strong></div></NavLink>
   <nav aria-label="Main navigation">{items.map((item,index)=>{const Icon=item.icon;return <div key={item.path}>{(index===0||items[index-1].group!==item.group)&&<div className="nav-group">{item.group}</div>}<NavLink to={`/${item.path}`} className="nav-link" title={item.label}><Icon size={17}/><span>{item.label}</span></NavLink></div>;})}</nav>
   <div className="sidebar-footer"><Button variant="ghost" aria-label="Toggle sidebar" onClick={()=>setCollapsed(!collapsed)}>{collapsed?<PanelLeft size={17}/>:<PanelLeftClose size={17}/>}</Button></div>
  </aside>
  <div className="main-column">
   <header className="topbar">
    <div className="breadcrumb">Islington College<ChevronRight size={13}/><strong>{active?.label||"NEXUS"}</strong></div>
    <button className="search-trigger" onClick={()=>setPalette(true)}><Search size={16}/><span>Search people, rooms, modules or ask NEXUS…</span><kbd>Ctrl K</kbd></button>
    <div className="topbar-tools"><Button variant="ghost" aria-label="Notifications" onClick={()=>navigate("/notifications")}><Bell size={17}/></Button><div className="user-chip"><span className="avatar">{user?.name.split(" ").map(part=>part[0]).slice(0,2).join("")}</span><div>{user?.name}<small>{roleLabel(user?.role)}</small></div></div><Button variant="ghost" aria-label="Sign out" onClick={logout}><LogOut size={16}/></Button></div>
   </header>
   <main key={location.pathname}><Outlet/></main>
   <footer className="app-footer"><span>NEXUS <span className="muted">/</span> Academic Operations Intelligence</span><span>College planning · Revision {workspace?.revision}</span></footer>
  </div>
 </div>;
}
