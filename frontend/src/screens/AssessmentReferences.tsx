import {useEffect,useState} from "react";
import {api,errorText} from "../api";
import {Panel,Badge,ErrorNotice} from "../components/ui";
type Reference={id:string;module_code:string;module_title:string;component:string;type:string;date:string|null;window_start:string|null;window_end:string|null;source:string;notes:string;data_status:string};
export default function AssessmentReferences(){
 const [rows,setRows]=useState<Reference[]>([]),[error,setError]=useState("");
 useEffect(()=>{void api.get<Reference[]>("/assessment-references").then(r=>setRows(r.data)).catch(e=>setError(errorText(e)));},[]);
 if(error)return <ErrorNotice message={error}/>;if(!rows.length)return null;
 return <Panel className="assessment-source"><div className="section-heading"><div><h2>Published assessment references</h2><p>AY 2025–26 · Level 5 · historical source material</p></div><Badge tone="orange">REFERENCE ONLY</Badge></div><p className="data-banner">These deadlines and examination windows are separate from scheduled exam allocations. Exact exam times, venues and invigilators were not supplied.</p><div className="table-wrap"><table><thead><tr><th>Module</th><th>Assessment</th><th>Deadline / window</th><th>Source</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td><code>{r.module_code}</code><small>{r.module_title}</small></td><td>{r.component}<small>{r.type}</small></td><td>{r.date||[r.window_start,r.window_end].filter(Boolean).join(" – ")||"To be confirmed"}<small>{r.notes}</small></td><td><small>{r.source}</small></td></tr>)}</tbody></table></div></Panel>;
}
