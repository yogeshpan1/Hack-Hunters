import {useState} from "react";
import {ArrowRight,ShieldCheck,Waypoints,CalendarRange,History} from "lucide-react";
import {useApp} from "../context";
import {errorText} from "../api";
import NexusSeal from "../components/Brand";
import {Button,ErrorNotice} from "../components/ui";

export default function Login(){
 const {login}=useApp();
 const [email,setEmail]=useState(""),[password,setPassword]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState("");
 return <div className="login">
  <section className="login-brand">
   <div className="login-lockup"><NexusSeal size={74}/><div><span>ISLINGTON COLLEGE</span><h2>NEXUS</h2></div></div>
   <div className="login-story"><span className="eyebrow">ACADEMIC OPERATIONS INTELLIGENCE</span><h1>Complex schedules.<br/>Clear decisions.</h1><p>Bring people, spaces, and academic time together. Make every change with confidence.</p><div className="login-capabilities"><span><CalendarRange/>Understand your timetable</span><span><Waypoints/>Find a valid way forward</span><span><History/>Keep every decision accountable</span></div></div>
   <div className="login-brand-footer">BUILT FOR ACADEMIC OPERATIONS <span>ISLINGTON · NEPAL</span></div>
  </section>
  <section className="login-form"><div className="login-form-inner"><span className="eyebrow">YOUR ACADEMIC WORKSPACE</span><h1>Welcome to NEXUS.</h1><p>Sign in to your college planning workspace.</p>
   <form onSubmit={async e=>{e.preventDefault();setBusy(true);setError("");try{await login(email,password);}catch(err){setError(errorText(err));}finally{setBusy(false);}}}>
    <label>Email address<input type="email" required value={email} onChange={e=>setEmail(e.target.value)} autoComplete="username"/></label>
    <label>Password<input type="password" required value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password"/></label>
    {error&&<ErrorNotice message={error}/>}<Button variant="primary" disabled={busy}>{busy?"Signing in…":"Enter workspace"}<ArrowRight size={17}/></Button>
   </form>
   <div className="demo-login"><ShieldCheck size={18}/><div><strong>Administrator-managed access</strong><p>The first administrator creates additional administrators and staff accounts. Contact your administrator for access.</p></div></div>
   <small>College inventory and curriculum loaded from supplied sources. Local application authentication.</small>
  </div><div className="login-ecosystem">Part of the innovation ecosystem<img src="/ing.png" alt="ING"/></div></section>
 </div>;
}
