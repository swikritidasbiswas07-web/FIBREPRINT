import React, {useState} from 'react';
import {ArrowUpRight, AlertTriangle, BookOpen, ChevronDown, ChevronUp, FlaskConical, ShieldAlert} from 'lucide-react';
import './research-results.css';

/* Snapshot derived from the user's v0.17 and v0.18 research JSON reports.
 * This is NOT a serving model. Refresh figures only after a documented rerun.
 */
const MODELS = [
  {label:'Random Forest',mae:94.95,r2:0.186},
  {label:'RF + keywords',mae:95.55,r2:0.155},
  {label:'Ridge',mae:87.95,r2:0.425},
  {label:'Ridge + keywords',mae:81.05,r2:0.494},
];
const wash = [160.12,126.10,89.18,75.47,62.93];
export default function ResearchResults(){
  const [expanded,setExpanded]=useState(false);
  return <section id="research-results" className="fp-results" aria-labelledby="fp-results-heading">
    <div className="fp-results-top">
      <div><span className="fp-results-eyebrow">RESEARCH RECORD / 1</span><h2 id="fp-results-heading">What the model <em>actually knows.</em></h2><p>Measured evaluation results from a single published laundry study — not predictions for your own fabric.</p></div>
      <div className="fp-results-status"><ShieldAlert size={16}/><span>RESEARCH-ONLY<br/>NOT DEPLOYABLE</span></div>
    </div>
    <div className="fp-results-stats" aria-label="Experimental evaluation summary">
      <div><small>FABRICS</small><strong>37</strong><span>independent specimens</span></div>
      <div><small>MEASUREMENTS</small><strong>155</strong><span>mass-release records</span></div>
      <div><small>BEST EXPLORATORY MAE</small><strong>81.05</strong><span>mg/kg · Ridge + keywords</span></div>
      <div><small>BEST EXPLORATORY R²</small><strong>0.494</strong><span>same grouped folds</span></div>
    </div>
    <div className="fp-results-grid">
      <div className="fp-results-chart"><div className="fp-results-chart-title"><span>MODEL COMPARISON</span><small>5-fold group-held-out MAE · lower is better</small></div>{MODELS.map(m=><div key={m.label} className="fp-results-bar-row"><span>{m.label}</span><div className="fp-results-bar-track"><div className={m.label==='Ridge + keywords'?'fp-results-bar chosen':'fp-results-bar'} style={{width:`${m.mae / 110 * 100}%`}}/></div><b>{m.mae.toFixed(2)}</b></div>)}<p className="fp-results-chart-note">The tested keyword flags were extracted from fabric descriptions, not measured fibre morphology.</p></div>
      <div className="fp-results-chart"><div className="fp-results-chart-title"><span>WASH-SPECIFIC ERROR</span><small>Original Random Forest · mg/kg</small></div><div className="fp-results-washes">{wash.map((n,i)=><div key={i} className="fp-results-wash"><strong>{i+1}</strong><div className="fp-results-wash-track"><div style={{height:`${n/175*100}%`}}/></div><small>{n.toFixed(1)}</small></div>)}</div><p className="fp-results-chart-note">Washes 1–2 contain 22 specimens each; washes 3–5 contain 37 each. This is not a controlled trend estimate.</p></div>
    </div>
    <div className="fp-results-bottom">
      <div className="fp-results-robust"><span>ROBUSTNESS CHECK</span><strong>14 / 20 splits</strong><p>Ridge + keywords beat Random Forest in 14 of 20 repeated grouped test partitions. These repeated splits are not independent external validations.</p></div>
      <div className="fp-results-robust warning"><span>IMPORTANT FAILURE MODE</span><strong>High-release underprediction</strong><p>All 14 measured high-release observations (≥400 mg/kg) were underpredicted by the original Random Forest. Extreme fabrics remain a concern.</p></div>
    </div>
    <button type="button" className="fp-results-disclosure" aria-expanded={expanded} onClick={()=>setExpanded(v=>!v)}><span><BookOpen size={17}/> Study limitations and source</span>{expanded?<ChevronUp size={17}/>:<ChevronDown size={17}/>}</button>
    {expanded&&<div className="fp-results-disclosure-body"><p>Data extracted from Vassilenko et al. (2021), PLOS ONE. All 155 extracted mass observations passed the source-workbook structural alignment check on 18 November 2026. This does not independently verify the experimental methodology. Descriptive keywords are proxies, not direct surface measurements; the models were explored after inspecting earlier errors. No external validation, inference-time reliability guarantee or calibrated uncertainty interval is available.</p><a href="https://doi.org/10.1371/journal.pone.0250346" target="_blank" rel="noopener noreferrer">Read the study <ArrowUpRight size={15}/></a><p className="fp-results-fine">Snapshot: v0.17 grouped-fold comparison and v0.18 repeated-split diagnostics, 18 November 2026.</p></div>}
  </section>;
}
