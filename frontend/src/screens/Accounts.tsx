import {useEffect,useState} from "react";
import {Plus,ShieldCheck,UserCog} from "lucide-react";
import {useApp} from "../context";
import {api,errorText} from "../api";
import {Badge,Button,Empty,ErrorNotice,Modal,PageHeader,Panel} from "../components/ui";
import type {User} from "../types";

const roles=["SuperAdmin","RTE","SSD"];

export default function Accounts(){
 const {can,notify}=useApp(); const [accounts,setAccounts]=useState<User[]>([]),[editor,setEditor]=useState(false),[error,setError]=useState("");
 async function load(){try{setAccounts((await api.get<User[]>("/data/users")).data);setError("");}catch(e){setError(errorText(e));}}
 useEffect(()=>{if(can("SuperAdmin"))void load();},[can]);
 if(!can("SuperAdmin"))return <Empty title="SuperAdmin access required" description="Only SuperAdmins can manage local NEXUS accounts."/>;
 return <><PageHeader eyebrow="ADMINISTRATION / ACCESS" title="Account Management" subtitle="Create and manage local SuperAdmin, RTE, and SSD accounts." actions={<Button variant="primary" onClick={()=>setEditor(true)}><Plus size={16}/>Add account</Button>}/>{error&&<ErrorNotice message={error}/>}<Panel><div className="table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Access</th></tr></thead><tbody>{accounts.map(account=><tr key={account.id}><td><strong>{account.name}</strong></td><td>{account.email}</td><td><Badge tone={account.role==="SuperAdmin"?"maroon":account.role==="RTE"?"blue":"neutral"}>{account.role}</Badge></td><td>{account.role==="SuperAdmin"?"All features, accounts and Change Log":account.role==="RTE"?"Operations and scheduling, excluding accounts and Change Log":"Read-only timetable, exams, rooms and database assistant"}</td></tr>)}</tbody></table></div></Panel>{editor&&<AccountEditor onClose={()=>setEditor(false)} onSaved={async()=>{setEditor(false);await load();notify("Account created.");}}/>}</>;
}

function AccountEditor({onClose,onSaved}:{onClose:()=>void;onSaved:()=>Promise<void>}){
 const [name,setName]=useState(""),[email,setEmail]=useState(""),[password,setPassword]=useState(""),[role,setRole]=useState("RTE"),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 async function save(){setBusy(true);setError("");try{await api.post("/data/users",{data:{name,email,role,password,active:true},reason:"Created local role account"});await onSaved();}catch(e){setError(errorText(e));}finally{setBusy(false);}}
 return <Modal title="Create local account" onClose={onClose}><form className="modal-body" onSubmit={event=>{event.preventDefault();void save();}}><div className="notice"><ShieldCheck size={17}/><div><strong>Role boundaries</strong><p>SuperAdmin: all features, accounts and Change Log. RTE: all operational features except accounts and Change Log. SSD: read-only information access.</p></div></div><label>Name<input required value={name} onChange={event=>setName(event.target.value)}/></label><label>Email<input required type="email" value={email} onChange={event=>setEmail(event.target.value)}/></label><label>Temporary password<input required minLength={4} type="password" value={password} onChange={event=>setPassword(event.target.value)}/></label><label>Role<select value={role} onChange={event=>setRole(event.target.value)}>{roles.map(value=><option key={value}>{value}</option>)}</select></label>{error&&<ErrorNotice message={error}/>}<div className="actions"><Button type="button" onClick={onClose}>Cancel</Button><Button variant="primary" disabled={busy}><UserCog size={15}/>{busy?"Creating…":"Create account"}</Button></div></form></Modal>;
}
