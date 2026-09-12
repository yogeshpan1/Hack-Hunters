import {Component,useLayoutEffect,type ReactNode} from "react";
import {BrowserRouter,Routes,Route,Navigate,useLocation} from "react-router-dom";
import {AppProvider,useApp} from "./context";
import {Startup} from "./components/Brand";
import Shell from "./components/Shell";
import {CommandPalette,Assistant,Toaster} from "./components/Intelligence";
import {Button,ErrorNotice} from "./components/ui";
import Login from "./screens/Login";
import Overview from "./screens/Overview";
import Timetable from "./screens/Timetable";
import Optimization from "./screens/Optimization";
import Records from "./screens/Records";
import {Audit,Rules,Analytics} from "./screens/PlanningInsights";
import Exams from "./screens/Examinations";
import {Communications,Settings} from "./screens/System";
class ErrorBoundary extends Component<{children:ReactNode},{error:boolean}>{state={error:false};static getDerivedStateFromError(){return {error:true};}render(){return this.state.error?<div className="empty"><h1>NEXUS encountered a display error.</h1><p>Reload the workspace to recover your session.</p><Button onClick={()=>window.location.reload()}>Reload workspace</Button></div>:this.props.children;}}
function ScrollToTop(){const {pathname}=useLocation();useLayoutEffect(()=>{window.scrollTo(0,0);},[pathname]);return null;}
function Content(){const {user,workspace,loading,error,refresh,logout}=useApp();if(loading)return <div className="empty">Opening your academic workspace…</div>;if(!user)return <Login/>;if(!workspace)return <div className="empty"><ErrorNotice message={error||"Loading workspace…"}/><Button onClick={()=>void refresh().catch(()=>{})}>Retry</Button><Button onClick={logout}>Sign out</Button></div>;return <><Routes><Route element={<Shell/>}><Route path="/overview" element={<Overview/>}/><Route path="/timetable" element={<Timetable/>}/><Route path="/optimization" element={<Optimization/>}/><Route path="/whatif" element={<Optimization whatif/>}/>{["rooms","faculty","programmes","modules","cohorts","students"].map(entity=><Route key={entity} path={`/${entity}`} element={<Records entity={entity}/>}/>)}<Route path="/audit" element={<Audit/>}/><Route path="/rules" element={<Rules/>}/><Route path="/analytics" element={<Analytics/>}/><Route path="/notifications" element={<Communications/>}/><Route path="/exams" element={<Exams/>}/><Route path="/settings" element={<Settings/>}/><Route path="*" element={<Navigate to="/overview" replace/>}/></Route></Routes><CommandPalette/><Assistant/><Toaster/></>;}
export default function App(){return <ErrorBoundary><BrowserRouter><ScrollToTop/><AppProvider><Startup/><Content/></AppProvider></BrowserRouter></ErrorBoundary>;}
