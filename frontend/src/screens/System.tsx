import {useEffect,useState} from "react";
import {useNavigate} from "react-router-dom";
import {ArrowRight,Mail,Bell,Send,Save} from "lucide-react";
import {useApp} from "../context";
import {api,errorText} from "../api";
import {PageHeader,Panel,Button,Badge,Modal,Empty,ErrorNotice} from "../components/ui";
import type {RecordData} from "../types";

export function Communications(){
 const {can,notify}=useApp();
 const [tab,setTab]=useState("notifications");
 const [rows,setRows]=useState<RecordData[]>([]);
 const [error,setError]=useState("");
 const [selected,setSelected]=useState<RecordData|null>(null);
 const [subject,setSubject]=useState("");
 const [body,setBody]=useState("");
 const [scheduled,setScheduled]=useState("");
 const [busy,setBusy]=useState(false);
 const [liveEmail,setLiveEmail]=useState(false);
 useEffect(()=>{void api.get("/integrations/status").then(r=>setLiveEmail(r.data.email_enabled)).catch(()=>setLiveEmail(false));},[]);

 async function load(){
  try{setRows((await api.get(`/${tab}`)).data);}
  catch(error){setError(errorText(error));}
 }
 useEffect(()=>{void load();},[tab]);

 async function save(action:string){
  if(!selected)return;
  setBusy(true);
  try{
   await api.put(`/emails/${selected.id}`,{subject,body,action,scheduled_at:action==="schedule"?new Date(scheduled).toISOString():null});
   setSelected(null);
   await load();
   notify(action==="send"?"Demo delivery recorded. No external email was sent.":"Email saved.");
  }catch(error){setError(errorText(error));}
  finally{setBusy(false);}
 }

 return <>
  <PageHeader eyebrow="SYSTEM / COMMUNICATIONS" title="Notifications & Email" subtitle="Keep affected people informed when approved schedules change." actions={can("Registrar")&&<Button onClick={async()=>{try{const response=await api.post("/emails/deliver-due");notify(`${response.data.delivered} due demo emails processed.`);await load();}catch(error){setError(errorText(error));}}}>Process due demo emails</Button>}/>
  <div className="record-toolbar"><div className="segmented"><button className={tab==="notifications"?"active":""} onClick={()=>setTab("notifications")}><Bell size={15}/>Notifications</button>{can("Registrar")&&<button className={tab==="emails"?"active":""} onClick={()=>setTab("emails")}><Mail size={15}/>Email outbox</button>}</div><Badge tone="orange">DEMO DELIVERY</Badge></div>
  {error&&<ErrorNotice message={error}/>}
  <Panel>{rows.length?<div className="table-wrap"><table><thead><tr><th>{tab==="emails"?"Recipient":"Created"}</th><th>Subject / message</th><th>Status</th><th/></tr></thead><tbody>{rows.map(row=><tr key={row.id}><td>{tab==="emails"?String(row.recipient):new Date(String(row.timestamp)).toLocaleString()}</td><td><strong>{String(row.subject||row.title)}</strong><small>{String(row.body)}</small></td><td><Badge tone="blue">{String(row.status||"Created")}</Badge></td><td>{tab==="emails"&&<Button onClick={()=>{setSelected(row);setSubject(String(row.subject));setBody(String(row.body));}}>Open draft<ArrowRight size={14}/></Button>}</td></tr>)}</tbody></table></div>:<Empty title={tab==="emails"?"No email drafts yet":"No notifications yet"} description="Publishing a timetable change identifies affected people and prepares communications automatically."/>}</Panel>
  {selected&&<Modal title="Email composer · Demo delivery" onClose={()=>setSelected(null)}><div className="modal-body"><label>To<input readOnly value={String(selected.recipient)}/></label><label>Subject<input value={subject} onChange={event=>setSubject(event.target.value)}/></label><label>Message<textarea rows={7} value={body} onChange={event=>setBody(event.target.value)}/></label><label>Schedule for<input type="datetime-local" value={scheduled} onChange={event=>setScheduled(event.target.value)}/></label><p className="fine-print">Scheduled messages are delivered in demo mode when “Process due demo emails” runs. No SMTP provider is connected.</p><div className="actions">{liveEmail&&!selected.provider_id&&<Button disabled={busy} onClick={async()=>{if(!window.confirm(`Send this email to ${String(selected.recipient)} through Resend?`))return;setBusy(true);setError("");try{await api.put(`/emails/${selected.id}`,{subject,body,action:"draft"});await api.post(`/emails/${selected.id}/send-live`);setSelected(null);await load();notify("Email accepted by Resend.");}catch(e){setError(errorText(e));}finally{setBusy(false);}}}>Send real email</Button>}<Button disabled={busy||!!selected.provider_id} onClick={()=>void save("draft")}><Save size={15}/>Save draft</Button><Button disabled={busy||!scheduled} onClick={()=>void save("schedule")}>Schedule</Button><Button variant="primary" disabled={busy} onClick={()=>void save("send")}><Send size={15}/>Demo send now</Button></div>{error&&<ErrorNotice message={error}/>}</div></Modal>}
 </>;
}

export function Settings(){
 const {user}=useApp();
 const navigate=useNavigate();
 return <><PageHeader eyebrow="SYSTEM / PREFERENCES" title="Workspace Settings" subtitle="Your session and the boundaries of this demo workspace."/><Panel className="settings-panel"><div><span>Signed in as</span><strong>{user?.name} · {user?.role}</strong></div><div><span>Academic year</span><strong>2026 / 27 · Single demo planning period</strong></div><div><span>Data source</span><Badge>COLLEGE INVENTORY</Badge></div><div><span>Database</span><strong>MongoDB · local replica set</strong></div><div><span>Assistant</span><strong>Structured database queries</strong></div><div><span>Communications</span><strong>Demo outbox · No external delivery</strong></div><div><span>Timetable updates</span><strong>Recalculate from Timetable Studio</strong></div><Button onClick={()=>navigate("/rules")}>Review scheduling rules<ArrowRight size={15}/></Button></Panel></>;
}
