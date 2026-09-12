import axios from "axios";
export const api=axios.create({baseURL:"/api",timeout:60000});
api.interceptors.request.use(config=>{const token=sessionStorage.getItem("nexus-token");if(token)config.headers.Authorization=`Bearer ${token}`;return config;});
export function errorText(error:unknown):string {
  if(axios.isAxiosError(error)){const detail=error.response?.data?.detail;return typeof detail==="string"?detail:Array.isArray(detail)?detail.map(x=>x.msg).join("; "):error.response?"This operation could not be completed.":"Cannot reach NEXUS. Check that the backend is running.";}
  return error instanceof Error?error.message:"Something went wrong.";
}
