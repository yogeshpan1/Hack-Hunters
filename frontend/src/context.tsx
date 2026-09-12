import {createContext,useCallback,useContext,useEffect,useState,type ReactNode} from "react";
import {api,errorText} from "./api";
import type {User,Workspace} from "./types";
type Toast={id:number;text:string;tone:string};
type ContextValue={selectedContext:Record<string,unknown>;setSelectedContext:(v:Record<string,unknown>)=>void;user:User|null;workspace:Workspace|null;loading:boolean;error:string;refresh:()=>Promise<void>;login:(email:string,password:string)=>Promise<void>;logout:()=>void;collapsed:boolean;setCollapsed:(v:boolean)=>void;palette:boolean;setPalette:(v:boolean)=>void;assistant:Record<string,unknown>|null;setAssistant:(v:Record<string,unknown>|null)=>void;notify:(text:string,tone?:string)=>void;toasts:Toast[];dismiss:(id:number)=>void;can:(...roles:string[])=>boolean};
const Context=createContext<ContextValue|null>(null);
export function AppProvider({children}:{children:ReactNode}){
 const [selectedContext,setSelectedContext]=useState<Record<string,unknown>>({});
 const [user,setUser]=useState<User|null>(null),[workspace,setWorkspace]=useState<Workspace|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState("");
 const [collapsed,setCollapsed]=useState(false),[palette,setPalette]=useState(false),[assistant,setAssistant]=useState<Record<string,unknown>|null>(null),[toasts,setToasts]=useState<Toast[]>([]);
 const notify=useCallback((text:string,tone="success")=>{const id=Date.now()+Math.random();setToasts(t=>[...t,{id,text,tone}]);setTimeout(()=>setToasts(t=>t.filter(x=>x.id!==id)),5000);},[]);
 const refresh=useCallback(async()=>{try{const {data}=await api.get<Workspace>("/workspace");setWorkspace(data);setError("");}catch(e){setError(errorText(e));throw e;}},[]);
 useEffect(()=>{const handler=(e:KeyboardEvent)=>{if((e.ctrlKey||e.metaKey)&&e.key==="k"){e.preventDefault();setPalette(v=>!v);}};window.addEventListener("keydown",handler);return()=>window.removeEventListener("keydown",handler);},[]);
 useEffect(()=>{async function init(){try{if(sessionStorage.getItem("nexus-token")){setUser((await api.get<User>("/auth/me")).data);await refresh();}}catch{sessionStorage.removeItem("nexus-token");setUser(null);}finally{setLoading(false);}}void init();},[refresh]);
 async function login(email:string,password:string){const {data}=await api.post("/auth/login",{email,password});sessionStorage.setItem("nexus-token",data.token);setUser(data.user);await refresh();}
 function logout(){sessionStorage.removeItem("nexus-token");setUser(null);setWorkspace(null);setAssistant(null);setPalette(false);setSelectedContext({});}
 return <Context.Provider value={{selectedContext,setSelectedContext,user,workspace,loading,error,refresh,login,logout,collapsed,setCollapsed,palette,setPalette,assistant,setAssistant,notify,toasts,dismiss:id=>setToasts(t=>t.filter(x=>x.id!==id)),can:(...roles)=>!!user&&(["Registrar","Super Admin"].includes(user.role)||roles.includes(user.role))}}>{children}</Context.Provider>;
}
export function useApp(){const value=useContext(Context);if(!value)throw new Error("Missing AppProvider");return value;}
