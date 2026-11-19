import React, {useEffect,useState} from 'react';

/* Scientific evidence status is distinct from serving-model installation state. */
export default function ResearchStatus({token}) {
  const [data,setData]=useState(null);
  const [error,setError]=useState('');
  useEffect(()=>{
    const controller=new AbortController();
    if(!token){setError('Please sign in to view the research audit.');return;}
    fetch('/api/research/status',{
      headers:{Authorization:`Bearer ${token}`},signal:controller.signal
    }).then(async response=>{
      if(!response.ok) throw new Error(`Research status unavailable (HTTP ${response.status})`);
      return response.json();
    }).then(setData).catch(err=>{if(err.name!=='AbortError')setError(err.message)});
    return ()=>controller.abort();
  },[token]);
  const source = data?.source_integrity;
  const experiment = data?.experiments;
  const external = data?.external_validation;
  return <div className="fp-model-readiness" aria-label="Scientific research and serving readiness">
    <div>
      <span>RESEARCH EXPERIMENTS / CURRENT STATUS</span>
      <strong>{error?'STATUS UNAVAILABLE':data?'RESEARCH ONLY — NOT DEPLOYABLE':'CHECKING RESEARCH AUDITS'}</strong>
      <p>{error||data?.message||'Loading audited research evidence from the backend.'}</p>
      {experiment?.group_conformal_status==='RUN_AND_DOCUMENTED'&&<p>Fabric-grouped calibration: documented · {experiment.repetitions} exploratory partitions.</p>}
      {experiment?.applicability_status==='RUN_AND_DOCUMENTED'&&<p>Applicability check: {experiment.diagnostic_interval_failures_flagged} of {experiment.diagnostic_total_interval_failures} interval failures flagged; {experiment.diagnostic_interval_failures_unflagged} missed.</p>}
    </div>
    <div>
      <span>DATA INTEGRITY / EXTERNAL CHECK</span>
      <strong>{source?.status==='STRUCTURAL_AUDIT_PASS' ? `${source.matched_mass_measurements} / 155 MATCHED` : 'NOT VERIFIED'}</strong>
      <p>{source?.status==='STRUCTURAL_AUDIT_PASS' ? `${source.source_fabrics} source fabrics; structural audit passed.` : 'Source audit data not verified on this backend.'}</p>
      <p>External validation: {external?.status?.replaceAll('_',' ')||'CHECKING'}.</p>
      <small>No live release estimate or guaranteed prediction interval is available.</small>
    </div>
  </div>;
}
