import {useEffect,useState} from "react";
import {AlertTriangle,ArrowDownRight,ArrowRight,CheckCircle2,FlaskConical,LockKeyhole,Play,ShieldCheck,Waypoints} from "lucide-react";
import {useApp} from "../context";
import {api,errorText} from "../api";
import {AskNexus,Badge,Button,Empty,ErrorNotice,Modal,PageHeader,Panel} from "../components/ui";
import {DAYS,time,type Readiness,type Run} from "../types";

type SolverOptions={whatif?:boolean;room?:number;day?:number;onStage:(label:string)=>void};

async function streamOptimizer({whatif=false,room,day,onStage}:SolverOptions):Promise<Run>{
 const response=await fetch("/api/optimization/stream",{
  method:"POST",
  headers:{"Content-Type":"application/json",Authorization:"Bearer "+(sessionStorage.getItem("nexus-token")||"")},
  body:JSON.stringify(whatif?{room_id:room,day}:{}),
 });
 if(!response.ok){
  const payload=await response.json().catch(()=>({}));
  throw new Error(payload.detail||"Calculation failed.");
 }
 if(!response.body)throw new Error("No solver response received.");

 const reader=response.body.getReader(),decoder=new TextDecoder();
 let buffer="",result:Run|null=null;
 const receive=(line:string)=>{
  if(!line.trim())return;
  const event=JSON.parse(line) as {type:string;label?:string;detail?:string;run?:Run};
  if(event.type==="stage"&&event.label)onStage(event.label);
  if(event.type==="error")throw new Error(event.detail||"Calculation failed.");
  if(event.type==="result"&&event.run)result=event.run;
 };
 while(true){
  const {done,value}=await reader.read();
  buffer+=decoder.decode(value,{stream:!done});
  const lines=buffer.split("\n");
  buffer=lines.pop()||"";
  lines.forEach(receive);
  if(done)break;
 }
 receive(buffer);
 if(!result)throw new Error("The solver connection ended before a result was received.");
 return result;
}

function ReadinessPanel({readiness}:{readiness:Readiness}){
 return <Panel className="readiness-panel">
  <h2>Data readiness</h2>
  <div>{readiness.checks.map(check=><p key={check.key} title={check.detail}>
   {check.ready?<CheckCircle2 size={15}/>:<AlertTriangle size={15}/>}
   <span>{check.label}<small>{check.detail}</small></span>
  </p>)}</div>
 </Panel>;
}

type ResultReviewProps={
 run:Run|null;
 busy:boolean;
 reason:string;
 setReason:(value:string)=>void;
 onAction:(action:"approve"|"publish"|"discard")=>void;
 compact?:boolean;
};

function ResultReview({run,busy,reason,setReason,onAction,compact=false}:ResultReviewProps){
 if(!run)return <Empty title={busy?"Evaluating your timetable…":"Ready when you are"} description={busy?"Checking constraints and searching for a feasible allocation. Results will appear here.":"Run a calculation to see real before-and-after metrics and proposed session changes."}/>;
 const failed=["Infeasible","Timed out"].includes(run.status);
 const canDecide=["Review","Approved"].includes(run.status);
 return <div className={"result-content "+(compact?"compact-result":"")}>
  <div className={"notice "+(failed?"error":"success")}>
   {failed?<AlertTriangle size={19}/>:<CheckCircle2 size={19}/>}
   <p>{run.explanation}</p>
  </div>
  {!failed&&<>
   <div className="comparison-grid">
    {[
     ["Hard conflicts",run.before.conflicts,run.after.conflicts,""],
     ["Conflict-free sessions",run.before.conflict_free,run.after.conflict_free,"%"],
     ["Room utilization",run.before.utilization,run.after.utilization,"%"],
     ["Session changes",0,run.changes.length,""],
    ].map(([label,before,after,suffix])=><div key={String(label)}>
     <span>{label}</span>
     <div><s>{before}{suffix}</s><ArrowRight size={19}/><strong>{after}{suffix}</strong></div>
    </div>)}
   </div>
   {run.changes.length?compact?
    <div className="drawer-change-list">{run.changes.map(change=><div className="drawer-change" key={change.id}>
     <strong>{change.code}</strong>
     <span>{change.before.room} · {DAYS[change.before.day]} {time(change.before.start)}</span>
     <ArrowRight size={14}/>
     <span>{change.after.room} · {DAYS[change.after.day]} {time(change.after.start)}</span>
    </div>)}</div>:
    <div className="table-wrap"><table><thead><tr><th>Session</th><th>Current allocation</th><th>Proposed allocation</th><th>Reason</th></tr></thead><tbody>
     {run.changes.map(change=><tr key={change.id}><td className="mono">{change.code}</td><td>{change.before.room}<small>{DAYS[change.before.day]} {time(change.before.start)}</small></td><td><span className="success-text">{change.after.room}</span><small>{DAYS[change.after.day]} {time(change.after.start)}</small></td><td className="reason-cell">{change.reason}</td></tr>)}
    </tbody></table></div>:
    <Empty title="No session moves required"/>
   }
   {canDecide&&<div className="approval-bar">
    <label>Decision reason<input value={reason} onChange={event=>setReason(event.target.value)} placeholder="Why should this plan be applied?"/></label>
    <div className="actions">
     <Button disabled={busy||reason.trim().length<5} onClick={()=>onAction("discard")}>Discard</Button>
     <Button variant="primary" disabled={busy||reason.trim().length<5} onClick={()=>onAction(run.status==="Review"?"approve":"publish")}><ShieldCheck size={16}/>{run.status==="Review"?"Approve changes":"Publish approved schedule"}</Button>
    </div>
   </div>}
   <div className="workflow-steps">{["Review","Approved","Published"].map((step,index)=><span className={run.status===step?"active":""} key={step}>{index+1}. {step}{index<2&&<ArrowRight size={14}/>}</span>)}</div>
  </>}
  {!compact&&<AskNexus context={{label:"Optimization run "+run.id}}/>}
 </div>;
}

export default function Optimization({whatif=false}:{whatif?:boolean}){
 const {workspace,refresh,notify,can}=useApp();
 const [run,setRun]=useState<Run|null>(null);
 const [history,setHistory]=useState<Run[]>([]);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [room,setRoom]=useState(1);
 const [day,setDay]=useState(3);
 const [reason,setReason]=useState("");
 const [stages,setStages]=useState<string[]>([]);
 const [readiness,setReadiness]=useState<Readiness|null>(null);

 useEffect(()=>{
  void api.get<Run[]>("/optimization").then(response=>setHistory(response.data)).catch(problem=>setError(errorText(problem)));
  setRun(null);
 },[whatif]);
 useEffect(()=>{
  void api.get<Readiness>("/readiness").then(response=>setReadiness(response.data)).catch(problem=>setError(errorText(problem)));
 },[workspace?.revision]);
 if(!workspace)return null;
 if(!can("Registrar"))return <Empty title="Registrar access required"/>;
 const affected=workspace.sessions.filter(session=>session.room_id===room&&session.day===day);

 async function calculate(){
  setBusy(true);setError("");setStages([]);setRun(null);
  try{
   const next=await streamOptimizer({whatif,room,day,onStage:label=>setStages(current=>[...current,label])});
   setRun(next);
   setHistory(current=>[next,...current]);
  }catch(problem){setError(errorText(problem));}
  finally{setBusy(false);}
 }
 async function action(actionName:"approve"|"publish"|"discard"){
  if(!run)return;
  setBusy(true);setError("");
  try{
   const {data}=await api.post<Run>("/optimization/"+run.id+"/"+actionName,{reason});
   setRun(data);
   setHistory(current=>current.map(item=>item.id===data.id?data:item));
   await refresh();
   notify(actionName==="publish"?"Schedule published. Audit, notifications, and email drafts created.":"Run "+data.status.toLowerCase()+".");
  }catch(problem){setError(errorText(problem));}
  finally{setBusy(false);}
 }

 return <div className={"optimization-page "+(whatif?"scenario-page":"")}>
  <PageHeader
   eyebrow={"INTELLIGENCE / "+(whatif?"SCENARIO PLANNING":"CONSTRAINT SOLVER")}
   title={whatif?"What happens if…?":"Optimization Lab"}
   subtitle={whatif?"Explore disruption safely. Compare the impact before making a change.":"Find a valid schedule. Understand every change before you approve it."}
   actions={<Button variant="primary" disabled={busy||!readiness?.ready} onClick={()=>void calculate()}><Play size={15}/>{busy?"Calculating…":whatif?"Run simulation":"Run optimizer"}</Button>}
  />
  {whatif&&<div className="scenario-sentence">
   <span>Room</span>
   <select aria-label="Scenario room" value={room} onChange={event=>{setRoom(Number(event.target.value));setRun(null);}}>{workspace.rooms.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select>
   <span>becomes unavailable on</span>
   <select aria-label="Scenario day" value={day} onChange={event=>{setDay(Number(event.target.value));setRun(null);}}>{DAYS.map((label,index)=><option key={label} value={index}>{label}</option>)}</select>
   <Badge tone="orange">{affected.length} sessions affected</Badge>
  </div>}
  {readiness&&<ReadinessPanel readiness={readiness}/>}
  <div className="optimization-layout">
   <Panel className="solver-panel">
    <div className="solver-icon">{whatif?<Waypoints size={28}/>:<FlaskConical size={28}/>}</div>
    <span className="eyebrow">{whatif?"A TEMPORARY SCENARIO":"GOOGLE OR-TOOLS · CP-SAT"}</span>
    <h2>{whatif?"What if a room closes?":"A better allocation starts here."}</h2>
    <p>{whatif?"Make a room unavailable for one day. NEXUS will calculate a feasible alternative timetable.":"Evaluate room capacity, lecturer availability, cohort overlaps, and fixed commitments together."}</p>
    {whatif&&<div className="form-grid">
     <label>Room<select value={room} onChange={event=>{setRoom(Number(event.target.value));setRun(null);}}>{workspace.rooms.map(item=><option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
     <label>Unavailable on<select value={day} onChange={event=>{setDay(Number(event.target.value));setRun(null);}}>{DAYS.map((label,index)=><option value={index} key={label}>{label}</option>)}</select></label>
    </div>}
    <div className={"solver-matrix "+(busy?"calculating":"")} aria-label="Current timetable occupancy">
     {Array.from({length:40},(_,index)=>{
      const weekday=index%5,hour=9+Math.floor(index/5);
      const count=workspace.sessions.filter(session=>session.day===weekday&&session.start<=hour&&session.start+session.duration>hour).length;
      return <i key={index} className={count?"occupied density-"+Math.min(3,count):""} style={{animationDelay:String(index*45)+"ms"}}/>;
     })}
    </div>
    <div className="solver-summary">
     <div><strong>{whatif?affected.length:workspace.metrics.conflicts}</strong><span>{whatif?"Affected sessions":"Hard conflicts"}</span></div>
     <div><strong>{workspace.sessions.filter(item=>item.locked).length}</strong><span>Locked sessions</span></div>
     <div><strong>{workspace.rules.length}</strong><span>Scheduling rules</span></div>
    </div>
    <Button variant="primary" disabled={busy||!readiness?.ready} onClick={()=>void calculate()}><Play size={16}/>{busy?"Calculating alternatives…":whatif?"Simulate room closure":"Run optimizer"}<ArrowRight size={16}/></Button>
    <p className="fine-print"><ShieldCheck size={14}/>Your published timetable stays unchanged until approval and publication.</p>
    {busy&&<div className="solver-progress" role="status">{stages.map((label,index)=><div key={label} className="active"><span>{index<stages.length-1?<CheckCircle2 size={14}/>:String(index+1).padStart(2,"0")}</span>{label}</div>)}</div>}
   </Panel>
   <Panel className="constraints-summary">
    <div className="section-heading"><h2>{whatif?"Impact preview":"Constraints in play"}</h2><LockKeyhole size={16}/></div>
    {whatif?affected.length?affected.map(session=><div className="compact-row" key={session.id}><strong>{session.code}</strong><span>{session.faculty}<small>{session.cohort} · {time(session.start)}</small></span></div>):<Empty title="No sessions directly affected" description="The full timetable will still be checked."/>:workspace.rules.filter(rule=>rule.kind==="Hard").map(rule=><div className="rule-summary" key={rule.id}><ShieldCheck size={17}/><span>{rule.name}</span><Badge>HARD</Badge></div>)}
    <div className="panel-note">{whatif?"Room closure is saved only when the scenario is published.":"No hard constraint can be switched off."}</div>
   </Panel>
  </div>
  {error&&<ErrorNotice message={error}/>}
  <Panel className="results-panel">
   <div className="section-heading"><div><span className="eyebrow">REVIEW / DECIDE / APPLY</span><h2>{run?"Run "+String(run.id).padStart(3,"0")+" · "+run.kind:"Your next allocation"}</h2></div>{run&&<Badge tone={run.status==="Published"?"green":run.status==="Review"?"blue":"orange"}>{run.status}</Badge>}</div>
   <ResultReview run={run} busy={busy} reason={reason} setReason={setReason} onAction={action}/>
  </Panel>
  {history.length>0&&<Panel className="run-history">
   <div className="section-heading"><h2>Recent calculations</h2><ArrowDownRight size={16}/></div>
   {history.slice(0,5).map(item=><button className="history-row" key={item.id} onClick={()=>{setRun(item);setReason("");}}><span className="mono">RUN {item.id}</span><span>{item.kind}<small>{new Date(item.created_at).toLocaleString()}</small></span><span>{item.before.conflicts} → {item.after.conflicts} conflicts</span><Badge>{item.status}</Badge><ArrowRight size={14}/></button>)}
  </Panel>}
 </div>;
}

export function OptimizationDrawer({onClose}:{onClose:()=>void}){
 const {workspace,refresh,notify,can}=useApp();
 const [run,setRun]=useState<Run|null>(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [reason,setReason]=useState("");
 const [stages,setStages]=useState<string[]>([]);
 const [readiness,setReadiness]=useState<Readiness|null>(null);

 useEffect(()=>{
  void api.get<Readiness>("/readiness").then(response=>setReadiness(response.data)).catch(problem=>setError(errorText(problem)));
 },[workspace?.revision]);
 if(!workspace||!can("Registrar"))return null;

 async function calculate(){
  setBusy(true);setError("");setStages([]);setRun(null);
  try{setRun(await streamOptimizer({onStage:label=>setStages(current=>[...current,label])}));}
  catch(problem){setError(errorText(problem));}
  finally{setBusy(false);}
 }
 async function action(actionName:"approve"|"publish"|"discard"){
  if(!run)return;
  setBusy(true);setError("");
  try{
   const {data}=await api.post<Run>("/optimization/"+run.id+"/"+actionName,{reason});
   setRun(data);
   await refresh();
   notify(actionName==="publish"?"Schedule published. Audit, notifications, and email drafts created.":"Run "+data.status.toLowerCase()+".");
  }catch(problem){setError(errorText(problem));}
  finally{setBusy(false);}
 }

 return <Modal drawer title="Resolve schedule conflicts" onClose={onClose}>
  <div className="modal-body optimization-drawer">
   <div className="drawer-optimizer-intro">
    <span className="eyebrow">CONSTRAINT SOLVER</span>
    <h3>Resolve conflicts without leaving the timetable.</h3>
    <p>NEXUS checks room capacity, equipment, faculty availability, cohort overlaps, and locked sessions before proposing a plan.</p>
   </div>
   <div className="drawer-optimizer-stats">
    <div><strong>{workspace.metrics.conflicts}</strong><span>Hard conflicts</span></div>
    <div><strong>{workspace.sessions.filter(session=>session.locked).length}</strong><span>Locked sessions</span></div>
    <div><strong>{workspace.rules.length}</strong><span>Rules in force</span></div>
   </div>
   {readiness&&<ReadinessPanel readiness={readiness}/>}
   <Button variant="primary" disabled={busy||!readiness?.ready} onClick={()=>void calculate()}><Play size={16}/>{busy?"Calculating alternatives…":"Run conflict resolution"}</Button>
   {busy&&<div className="solver-progress drawer-progress" role="status">{stages.map((label,index)=><div key={label} className="active"><span>{index<stages.length-1?<CheckCircle2 size={14}/>:String(index+1).padStart(2,"0")}</span>{label}</div>)}</div>}
   {error&&<ErrorNotice message={error}/>}
   {run&&<ResultReview compact run={run} busy={busy} reason={reason} setReason={setReason} onAction={action}/>}
  </div>
 </Modal>;
}
