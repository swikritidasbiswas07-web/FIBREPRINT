import React, { useState } from 'react';
import { ArrowUpRight, ArrowRight, Eye, EyeOff, LockKeyhole, Check, AlertCircle, Layers3 } from 'lucide-react';
import './auth.css';

// Photo: Marija Zaric / Unsplash. Real editorial source: https://unsplash.com/photos/EK2Re7OKOls
// Local fallback is the already-installed editorial linen visual from v0.27.
const WEB_PHOTO = 'https://images.unsplash.com/photo-1697987215011-fa6a00e71561?auto=format&fit=crop&w=1500&q=86';
const FALLBACK_PHOTO = '/images/editorial/linen.webp';

export default function Auth({ onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [photo, setPhoto] = useState(WEB_PHOTO);
  const isRegister = mode === 'register';

  const switchMode = next => {
    setMode(next);
    setError('');
    setPassword('');
  };

  const submit = async event => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const response = await fetch(`/api/auth/${isRegister ? 'register' : 'login'}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(isRegister ? { name: name.trim(), email: email.trim(), password } : { email: email.trim(), password }),
      });
      const body = await response.text();
      let data;
      try { data = body ? JSON.parse(body) : null; } catch { throw new Error('The server returned an unreadable response. Check the FastAPI terminal.'); }
      if (!response.ok) {
        const detail = typeof data?.detail === 'string' ? data.detail : `Sign-in request failed (${response.status}).`;
        throw new Error(detail);
      }
      if (!data?.access_token || !data?.user) throw new Error('The server did not return account access details.');
      sessionStorage.setItem('fp_access_token', data.access_token);
      onAuthenticated(data.user, data.access_token);
    } catch (err) {
      setError(err?.message || 'Unable to connect. Is the FastAPI backend running?');
    } finally { setBusy(false); }
  };

  return (
    <div className="auth-shell fp-auth-v31">
      <header className="auth-topbar">
        <a href="/" className="brand" aria-label="FIBREPRINT home">
          <span className="brand-monogram">f<span className="slash">/</span>p</span>
          <span className="brand-word">FIBREPRINT <small>MATERIAL INTELLIGENCE LAB</small></span>
        </a>
        <span className="auth-header-right">THE TEXTILE FIELD LAB <i aria-hidden="true" /></span>
      </header>

      <main className="auth-layout">
        <section className="auth-editorial" aria-label="Introduction to the textile research laboratory">
          <img className="auth-photo" src={photo} onError={() => photo !== FALLBACK_PHOTO && setPhoto(FALLBACK_PHOTO)} alt="Close-up editorial photograph of a naturally woven textile" />
          <div className="auth-photo-veil" aria-hidden="true" />
          <div className="auth-editorial-inner">
            <span className="auth-small-mark"><span className="auth-dot"/> INSIDE THE MATERIAL</span>
            <h1>THE STORY<br/>IS IN THE <em>THREAD.</em></h1>
            <p>Every fabric holds a material story. Investigate its structure, examine the evidence, and see what washing leaves behind.</p>
            <div className="auth-photo-footer">
              <span>FIBREPRINT / A MATERIAL INTELLIGENCE LAB</span>
              <a href="https://unsplash.com/photos/a-close-up-view-of-a-woven-material-EK2Re7OKOls" target="_blank" rel="noreferrer">Photo: Marija Zaric / Unsplash <ArrowUpRight size={14}/></a>
            </div>
          </div>
        </section>

        <section className="auth-form-side">
          <div className="auth-form-inner">
            <div className="auth-form-ornament"><span>f<span>/</span>p</span><span>YOUR SPACE TO INVESTIGATE</span></div>
            <div className="auth-copy">
              <span className="auth-kicker"><LockKeyhole size={15} /> MATERIAL RESEARCH WORKSPACE</span>
              <h2>{isRegister ? <>Begin <em>here.</em></> : <>Welcome <em>back.</em></>}</h2>
              <p>{isRegister ? 'Make your own field notebook. Start with a specimen, then follow the evidence.' : 'Pick up your investigation where you left off.'}</p>
            </div>
            <div className="auth-pills" role="group" aria-label="Account access">
              <button type="button" aria-pressed={!isRegister} className={!isRegister ? 'active' : ''} onClick={() => switchMode('login')}>SIGN IN</button>
              <button type="button" aria-pressed={isRegister} className={isRegister ? 'active' : ''} onClick={() => switchMode('register')}>CREATE ACCOUNT</button>
            </div>
            <form className="auth-form" onSubmit={submit}>
              {isRegister && <label><span>YOUR NAME</span><input name="name" value={name} minLength={2} maxLength={80} autoComplete="name" placeholder="Full name" onChange={e => setName(e.target.value)} required /></label>}
              <label><span>EMAIL ADDRESS</span><input name="email" type="email" value={email} autoComplete="email" placeholder="you@example.com" onChange={e => setEmail(e.target.value)} required /></label>
              <label><span>PASSWORD</span><div className="auth-password"><input name="password" type={showPassword ? 'text' : 'password'} value={password} minLength={isRegister ? 10 : 1} autoComplete={isRegister ? 'new-password' : 'current-password'} placeholder={isRegister ? 'At least 10 characters' : 'Enter your password'} onChange={e => setPassword(e.target.value)} required/><button type="button" onClick={() => setShowPassword(v => !v)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={18}/> : <Eye size={18}/>}</button></div></label>
              {isRegister && <div className="auth-help"><Check size={15}/> At least 10 characters. Never reuse a password.</div>}
              {error && <div role="alert" className="auth-error"><AlertCircle size={18}/><span>{error}</span></div>}
              <button disabled={busy} type="submit" className="auth-submit"><span>{busy ? 'CONNECTING…' : isRegister ? 'CREATE MY WORKSPACE' : 'ENTER THE LAB'}</span><ArrowUpRight size={20}/></button>
            </form>
            <div className="auth-under-form">{isRegister ? 'Already have an account?' : 'Your first visit?'} <button type="button" onClick={() => switchMode(isRegister ? 'login' : 'register')}>{isRegister ? 'Sign in' : 'Create an account'} <ArrowRight size={15}/></button></div>
            <div className="auth-privacy"><Layers3 size={16}/><span>Research-only prototype. Account verification and password recovery are not yet available.</span></div>
          </div>
          <div className="auth-form-foot"><span>OBSERVE / QUESTION / VERIFY</span><span>FIBREPRINT · 2026</span></div>
        </section>
      </main>
    </div>
  );
}
