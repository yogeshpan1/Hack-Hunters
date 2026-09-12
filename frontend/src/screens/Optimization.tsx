import {useEffect,useState} from "react";
import {AlertTriangle,ArrowRight,CheckCircle2,Play,ShieldCheck,Waypoints} from "lucide-react";
import {useApp} from "../context";
import {api,errorText} from "../api";
import {AskNexus,Badge,Button,Empty,ErrorNotice,Modal,PageHeader,Panel} from "../components/ui";
import {DAYS,time,type Readiness,type Run} from "../types";

type SolverOptions={strategy?:"balanced"|"rooms"|"faculty";whatif?:boolean;room?:number;day?:number;onStage:(label:string)=>void};

async function streamOptimizer({strategy="balanced",whatif=false,room,day,onStage}:SolverOptions):Promise<Run>{
 const response=await fetch("/api/optimization/stream",{
  method:"POST",
  headers:{"Content-Type":"application/json",Authorization:"Bearer "+(sessionStorage.getItem("nexus-token")||"")},
  body:JSON.stringify(whatif?{room_id:room,day,strategy}:{strategy}),
 });
 if(!response.ok){
  const payload=await response.json().catch(()=>({}));
  throw new Error(typeof payload.detail==="string"?payload.detail:Array.isArray(payload.detail)?payload.detail.map((item:{msg:string})=>item.msg).join("; "):"Calculation failed.");
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
 if(!run)return <Empty title={busy?"Evaluating your timetableâ€¦":"Ready when you are"} description={busy?"Checking constraints and searching for a feasible allocation. Results will appear here.":"Run a calculation to see real before-and-after metrics and proposed session changes."}/>;
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
     <span>{change.before.room} Â· {DAYS[change.before.day]} {time(change.before.start)}</span>
     <ArrowRight size={14}/>
     <span>{change.after.room} Â· {DAYS[change.after.day]} {time(change.after.start)}</span>
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
 const {workspace:w,refresh,notify}=useApp();
 const [candidates,setCandidates]=useState<(Run|null)[]>([null,null,null]),[selected,setSelected]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState(""),[stages,setStages]=useState<string[]>([]),[reason,setReason]=useState(""),[review,setReview]=useState(false);
 const [room,setRoom]=useState(0),[day,setDay]=useState(3),[readiness,setReadiness]=useState<Readiness|null>(null);
 useEffect(()=>{void api.get<Readiness>("/readiness").then(r=>setReadiness(r.data)).catch(e=>setError(errorText(e)));},[w?.revision]);
 if(!w)return null;
 const roomId=room||w.rooms[0]?.id,affected=w.sessions.filter(s=>s.room_id===roomId&&s.day===day),run=candidates[selected];
 async function calculate(){
  setBusy(true);setError("");setCandidates([null,null,null]);setStages([]);setSelected(0);setReason("");
  try{
   const strategies=(whatif?["balanced"]:["balanced","rooms","faculty"]) as ("balanced"|"rooms"|"faculty")[];
   for(let i=0;i<strategies.length;i++){
    const result=await streamOptimizer({strategy:strategies[i],whatif,room:roomId,day,onStage:label=>setStages(current=>[...current,`${whatif?"Simulation":"Option "+String.fromCharCode(65+i)} · ${label}`])});
    setCandidates(current=>current.map((value,index)=>index===i?result:value));
   }
  }catch(e){setError(errorText(e));}finally{setBusy(false);}
 }
 async function action(actionName:"approve"|"publish"|"discard"){
  if(!run)return;setBusy(true);setError("");
  try{const {data}=await api.post<Run>(`/optimization/${run.id}/${actionName}`,{reason});setCandidates(current=>current.map(r=>r?.id===data.id?data:r));await refresh();notify(`Run ${data.status.toLowerCase()}.`);}catch(e){setError(errorText(e));}finally{setBusy(false);}
 }
 const runButton=<Button variant="primary" disabled={busy||!readiness?.ready} onClick={()=>void calculate()}><Play size={15}/>{busy?"Calculating…":whatif?"Run simulation":"Run optimizer"}</Button>;
 const resetScenario=()=>{setCandidates([null,null,null]);setReason("");};
 const comparison=[["Conflict-free sessions",...candidates.map(r=>r?.after.conflict_free??"—")],["Room utilization",...candidates.map(r=>r?.after.utilization??"—")],["Faculty within weekly target",...candidates.map(r=>r?.after.faculty_balance??"—")],["Hard conflicts",...candidates.map(r=>r?.after.conflicts??"—")],["Session changes",...candidates.map(r=>r?.changes.length??"—")]];
 return <div className="recorded-planning">
  <PageHeader eyebrow={whatif?"INTELLIGENCE · SIMULATION":"INTELLIGENCE · OPTIMIZATION"} title={whatif?"What happens if…?":"Optimization Lab"} subtitle={whatif?"Model a disruption, see what breaks, and review a resolution before you commit.":"Generate, compare and select a feasible schedule."} actions={!whatif&&runButton}/>
  {error&&<ErrorNotice message={error}/>}
  {whatif?<>
   <div className="scenario-sentence"><span>Simulate: Room</span><select aria-label="Scenario room" disabled={busy} value={roomId} onChange={e=>{setRoom(Number(e.target.value));resetScenario();}}>{w.rooms.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}</select><span>becomes unavailable on</span><select aria-label="Scenario day" disabled={busy} value={day} onChange={e=>{setDay(Number(e.target.value));resetScenario();}}>{DAYS.map((d,i)=><option key={d} value={i}>{d}</option>)}</select>{runButton}</div>
   <div className="recorded-kpis three">{[["Affected sessions",affected.length],["Affected cohorts",new Set(affected.flatMap(s=>s.cohort_ids)).size],["Affected faculty",new Set(affected.map(s=>s.faculty_id)).size]].map(([label,value])=><Panel key={label}><span className="eyebrow">{label}</span><strong>{value}</strong></Panel>)}</div>
   <div className="scenario-columns">{["Before","After incident","After optimization"].map((label,i)=>{
    const ready=i===0||!!run,success=run&&["Review","Approved","Published"].includes(run.status);
    const value=i===0?w.metrics.conflicts:i===1?run?.incident?.conflicts??null:success?run.after.conflicts:null;
    const use=i===0?w.metrics.utilization:i===1?run?.incident?.utilization??null:success?run.after.utilization:null;
    return <Panel key={label} className={i===1?"incident-card":i===2?"resolved-card":""}><h3><i/>{label}</h3><p className="fine-print">{i===0?"Current committed schedule":i===1?`${w.rooms.find(r=>r.id===roomId)?.name} closed · ${DAYS[day]}`:"NEXUS proposed resolution"}</p><div className="scenario-metric"><span>Conflicts</span><strong>{ready?value??"—":"—"}</strong></div><div className="conflict-ticks">{Array.from({length:8},(_,k)=><i key={k} className={ready&&value&&k<value?"filled":""}/>)}</div><div className="scenario-metric"><span>Room utilization</span><b>{ready&&use!==null?`${use}%`:"—"}</b></div><div className="meter teal"><span style={{width:`${ready?use||0:0}%`}}/></div><p className="scenario-note">{i===0?"Baseline operating state across Islington College.":i===1?"Each affected session needs an alternative room or time.":run?run.explanation:"Run the simulation to calculate an alternative."}</p></Panel>;
   })}</div>
   {busy&&<Panel className="planning-progress">{stages.at(-1)||"Preparing simulation…"}</Panel>}
   {run&&<Panel className="scenario-proposals"><div className="section-heading"><h2>Proposed movements</h2><Badge>{run.status}</Badge></div><ResultReview compact run={run} busy={busy} reason={reason} setReason={setReason} onAction={action}/></Panel>}
  </>:<div className="candidate-layout">
   <Panel className="candidate-engine"><h3><span className="live-dot"/>Constraint Solver</h3><p className="fine-print">Candidate generation · live calculation</p><div className={"solver-matrix "+(busy?"calculating":"")}>{Array.from({length:56},(_,i)=><i key={i} className={w.sessions.some(s=>s.day===i%6&&s.start<=6.5+Math.floor(i/6)&&s.start+s.duration>6.5+Math.floor(i/6))?"occupied density-2":""}/>)}</div><div className="engine-kpis">{[["Sessions",w.sessions.length],["Hard constraints",w.rules.filter(r=>r.kind==="Hard").length],["Soft constraints",w.rules.filter(r=>r.kind==="Soft").length],["Feasible candidates",candidates.filter(r=>r&&["Review","Approved","Published"].includes(r.status)).length]].map(([label,value])=><div key={label}><strong>{value}</strong><span>{label}</span></div>)}</div><div className="engine-stages" role="status">{stages.length?stages.slice(-8).map((label,i)=><p key={i}><CheckCircle2 size={14}/>{label}</p>):<p>Ready to test balanced, room-fit and faculty-day priorities.</p>}</div>{readiness&&!readiness.ready&&<ReadinessPanel readiness={readiness}/>}</Panel>
   <div className="candidate-results">{!candidates.some(Boolean)?<Panel className="candidate-empty"><Waypoints size={36}/><h3>{busy?"Evaluating candidate schedules…":"Candidate schedules appear here"}</h3><p>Run the optimizer to compare three scheduling priorities.<br/>Every candidate is independently checked against hard constraints.</p></Panel>:<>
    <div className="candidate-cards">{["Balanced allocation","Best room fit","Balanced faculty days"].map((label,i)=><button className={"panel candidate-card "+(selected===i?"selected":"")} key={label} disabled={!candidates[i]||busy} onClick={()=>{setSelected(i);setReason("");}}><span className="eyebrow">Option {String.fromCharCode(65+i)}</span><h3>{label}</h3><strong>{candidates[i]?.after.health??"—"}<small>/100</small></strong><div className="meter teal"><span style={{width:`${candidates[i]?.after.health||0}%`}}/></div><Badge tone={selected===i?"blue":"neutral"}>{candidates[i]?.status||"Waiting"}{selected===i&&candidates[i]?" · Selected":""}</Badge></button>)}</div>
    <Panel className="comparison-matrix"><div className="section-heading"><h2>Comparison Matrix</h2><Badge>Calculated metrics</Badge></div><div className="table-wrap"><table><thead><tr><th>Metric</th>{["A","B","C"].map(x=><th key={x}>Option {x}</th>)}</tr></thead><tbody>{comparison.map(row=><tr key={row[0]}><td>{row[0]}</td>{row.slice(1).map((value,i)=><td key={i} className={i===selected?"matrix-selected":""}>{value}</td>)}</tr>)}</tbody></table></div><p className="panel-note">Different priorities may produce the same allocation. Score shows the percentage of conflict-free sessions.</p><div className="candidate-actions"><span>Option {String.fromCharCode(65+selected)} selected</span><Button disabled={!run||busy} onClick={()=>setReview(true)}>Preview & approve<ArrowRight size={14}/></Button></div></Panel>
   </>}</div>
  </div>}
  {whatif&&readiness&&!readiness.ready&&<ReadinessPanel readiness={readiness}/>}
  {review&&<Modal wide title={`Option ${String.fromCharCode(65+selected)} · Review schedule`} onClose={()=>setReview(false)}><div className="modal-body"><ResultReview run={run} busy={busy} reason={reason} setReason={setReason} onAction={action}/>{error&&<ErrorNotice message={error}/>}</div></Modal>}
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
   <Button variant="primary" disabled={busy||!readiness?.ready} onClick={()=>void calculate()}><Play size={16}/>{busy?"Calculating alternativesâ€¦":"Run conflict resolution"}</Button>
   {busy&&<div className="solver-progress drawer-progress" role="status">{stages.map((label,index)=><div key={label} className="active"><span>{index<stages.length-1?<CheckCircle2 size={14}/>:String(index+1).padStart(2,"0")}</span>{label}</div>)}</div>}
   {error&&<ErrorNotice message={error}/>}
   {run&&<ResultReview compact run={run} busy={busy} reason={reason} setReason={setReason} onAction={action}/>}
  </div>
 </Modal>;
}
