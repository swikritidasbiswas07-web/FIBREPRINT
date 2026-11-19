import React,{useState,useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.jsx';
import Auth from './Auth.jsx';
import './styles.css';
import './auth.css';
function Root(){
 const [session,setSession]=useState(null);
 const [checking,setChecking]=useState(true);
 useEffect(()=>{
  const token=sessionStorage.getItem('fp_access_token');
  if(!token){setChecking(false);return;}
  fetch('/api/auth/me',{headers:{Authorization:'Bearer '+token}})
   .then(async res=>{if(!res.ok)throw new Error('expired');const user=await res.json();setSession({user,token})})
   .catch(()=>sessionStorage.removeItem('fp_access_token'))
   .finally(()=>setChecking(false));
 },[]);
 const logOut=async()=>{
   if(session?.token){try{await fetch('/api/auth/logout',{method:'POST',headers:{Authorization:'Bearer '+session.token}})}catch(e){/* network may be unavailable */}}
   sessionStorage.removeItem('fp_access_token');setSession(null);
 };
 if(checking)return <div className="auth-loading">FIBREPRINT <span>OPENING THE LAB…</span></div>;
 if(!session)return <Auth onAuthenticated={(user,token)=>setSession({user,token})}/>;
 return <App user={session.user} token={session.token} onLogout={logOut}/>;
}
createRoot(document.getElementById('root')).render(<Root/>);
