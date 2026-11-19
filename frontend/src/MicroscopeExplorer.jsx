import React, { useState } from 'react';
import { ArrowUpRight, ChevronLeft, ChevronRight, Eye, EyeOff, Layers3, Microscope, ScanSearch, SplitSquareHorizontal, ZoomIn, ZoomOut } from 'lucide-react';
import './microscope.css';

/**
 * Educational drawings, not microscope captures or quantitative scientific simulations.
 * Text explicitly separates schematic design from published experimental evidence.
 */
const SPECIMENS = [
  {id:'1',label:'Plain woven',family:'FABRIC STRUCTURE',sub:'Interlaced yarns',type:'woven',tone:'#82b5b7',deep:'#326d79',detail:'Warp and weft yarns cross at approximately right angles. Tightness, yarn construction and finishing can influence release.',notes:['Two perpendicular yarn systems','Interlacement points constrain movement','Shedding cannot be inferred from appearance alone']},
  {id:'2',label:'Jersey knit',family:'FABRIC STRUCTURE',sub:'Interlocking loops',type:'knit',tone:'#d2c2a6',deep:'#8d7657',detail:'A knitted construction is built from linked loops. Loop geometry and yarn characteristics are relevant to shedding behaviour.',notes:['Interconnected loops','Stretch depends on construction','Fibre type alone is not enough']},
  {id:'3',label:'Raised fleece',family:'SURFACE FINISH',sub:'Raised surface fibres',type:'fleece',tone:'#b3a4b8',deep:'#655771',detail:'Raised and brushed fabric surfaces expose fibre ends. Experimental shedding results depend on the textile and the laundering protocol.',notes:['Surface pile and exposed ends','Finishing alters the surface','No universal release rate is assumed']},
  {id:'4',label:'Filament bundle',family:'YARN MORPHOLOGY',sub:'Continuous-filament schematic',type:'filament',tone:'#a5c3a4',deep:'#517754',detail:'A filament yarn comprises continuous fibres. Yarn construction, twist and treatment affect its behaviour under laundering.',notes:['Long, continuous strands','Bundled yarn architecture','Material identity needs independent evidence']},
];

// Actual published image pages. Captions intentionally distinguish fibre morphology
// from textile construction; an isolated fibre does not verify fabric construction.
const MICROGRAPHS = [
 {id:'M1',label:'Polyester fibre',family:'SYNTHETIC FIBRE',sub:'CSIRO ScienceImage photograph',image:'/images/microscopy/polyester-sem.jpg',source:'https://commons.wikimedia.org/wiki/File:CSIRO_ScienceImage_8440_Polyester_fibre.jpg',detail:'Microscopy photograph of a polyester fibre. This is an individual fibre observation, not a measurement of shedding or a knitted/woven textile sample.',notes:['Inspect the visible fibre morphology','Do not infer garment construction from this image','Original attribution and licensing appear on the source page']},
 {id:'M2',label:'Cotton fibre',family:'NATURAL FIBRE',sub:'CSIRO ScienceImage photograph',image:'/images/microscopy/cotton-sem.jpg',source:'https://commons.wikimedia.org/wiki/File:CSIRO_ScienceImage_8114_Cotton_fibre.jpg',detail:'Microscopy photograph of cotton fibre morphology. Textile structure and chemical verification require separate supporting evidence.',notes:['Compare visible fibre structure','This image does not show shedding rate','Preserve source credits and any visible scale markings']},
 {id:'M3',label:'Cotton microstructure',family:'OPTICAL MICROGRAPH',sub:'Microscopy of cotton fibres',image:'/images/microscopy/cotton-optical.png',source:'https://commons.wikimedia.org/wiki/File:Microstructure_of_Cotton_Fibers_10%25_20.png',detail:'Cotton fibre microstructure observed through microscopy. Its scale information belongs to the original image, not to the display zoom control.',notes:['Observe twists and overlapping fibres','Preserve the source image and scale information','No release prediction follows from appearance alone']},
 {id:'M4',label:'Merino wool fibre',family:'ANIMAL FIBRE',sub:'CSIRO electron micrograph',image:'/images/microscopy/wool-sem.jpg',source:'https://commons.wikimedia.org/wiki/File:CSIRO_ScienceImage_2487_Electron_Microscope_Image_of_Merino_Wool_Fibre.jpg',detail:'Electron microscopy photograph of Merino wool fibre. Used here as an additional material-science specimen, not as an example of continuous synthetic filament.',notes:['Inspect fibre surface morphology','Animal fibres differ from synthetic filaments','Do not treat this photograph as a quantitative shedding test']},
];

function MicrographImage({specimen,zoom=1,caption=true}) {
 return <div className="fp-micrograph-shell">
   <div className="fp-micrograph-viewport"><img loading="lazy" src={specimen.image} alt={`Microscopy specimen: ${specimen.label}`} style={{transform:`scale(${zoom})`}} onError={e=>{e.currentTarget.style.display='none'; e.currentTarget.parentNode.classList.add('fp-image-missing')}}/><div className="fp-micrograph-tag">ACTUAL SOURCE IMAGE / {specimen.id}</div></div>
   {caption&&<a className="fp-photo-source micro-photo-credit" href={specimen.source} target="_blank" rel="noopener noreferrer" title={specimen.source}><span>IMAGE SOURCE</span><span className="fp-source-url">{specimen.source}</span><ArrowUpRight size={12}/></a>}
 </div>;
}

function TextileDrawing({specimen, zoom=1.25, annotations=true, idSuffix='main'}) {
  const p = `fp-${idSuffix}-${specimen.type}`;
  return <svg viewBox="0 0 540 410" className="micro-svg" xmlns="http://www.w3.org/2000/svg" role="img" aria-label={`Illustrative diagram of ${specimen.label}; not an actual microscope image`}>
    <defs>
      <pattern id={`${p}-grain`} width="12" height="12" patternUnits="userSpaceOnUse"><path d="M0 2L12 10 M-2 9L6 15" stroke="#fff" strokeOpacity=".035" fill="none" strokeWidth="1"/></pattern>
      <filter id={`${p}-shadow`} x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="2" dy="3" stdDeviation="2.5" floodColor="#041a1e" floodOpacity=".32"/></filter>
      <clipPath id={`${p}-clip`}><rect x="0" y="0" width="540" height="410"/></clipPath>
    </defs>
    <rect width="540" height="410" fill="#142f35"/>
    <g clipPath={`url(#${p}-clip)`}>
      <g transform={`translate(270 205) scale(${zoom}) translate(-270 -205)`} filter={`url(#${p}-shadow)`}>
        {specimen.type==='woven' && <>
          {Array.from({length:13},(_,i)=><path key={`h${i}`} d={`M-65 ${i*37-22} Q170 ${i*37-34} 300 ${i*37-22} T620 ${i*37-22}`} fill="none" stroke={i%2?specimen.deep:specimen.tone} strokeWidth="20" strokeLinecap="round" opacity=".98"/>)}
          {Array.from({length:17},(_,i)=><g key={`v${i}`}><path d={`M${i*36-18} -60 Q${i*36-30} 205 ${i*36-18} 480`} fill="none" stroke={i%2?specimen.tone:specimen.deep} strokeWidth="20" strokeLinecap="round" strokeDasharray="22 22"/></g>)}
        </>}
        {specimen.type==='knit' && Array.from({length:9},(_,r)=>Array.from({length:10},(_,c)=>{
          const x=c*58-13+(r%2)*28,y=r*54-23;
          return <path key={`${r}-${c}`} d={`M${x-17} ${y-27} Q${x-32} ${y-8} ${x-15} ${y+9} C${x-9} ${y+22} ${x+8} ${y+25} ${x+15} ${y+9} Q${x+33} ${y-7} ${x+17} ${y-27}`} stroke={c%2?specimen.deep:specimen.tone} strokeWidth="13" strokeLinecap="round" fill="none"/>
        }))}
        {specimen.type==='fleece'&&<>
          {Array.from({length:23},(_,i)=><path key={`base${i}`} d={`M-50 ${i*21-40}Q255 ${i*21-55} 590 ${i*21-32}`} stroke={i%2?specimen.deep:specimen.tone} strokeWidth="13" strokeLinecap="round" fill="none"/>)}
          {Array.from({length:130},(_,i)=>{const x=(i*77)%590-25,y=(i*49)%470-30,ang=(i%5-2)*18;return <path key={`tuft${i}`} d={`M${x} ${y} q${ang} -22 ${ang+12} -29 q15 -9 21 5`} stroke={i%3===0?'#e6dce7':specimen.tone} strokeWidth={i%4===0?3:2} strokeLinecap="round" opacity=".85" fill="none"/>})}
        </>}
        {specimen.type==='filament'&&Array.from({length:31},(_,i)=>{
          const y=25+i*13;
          return <path key={i} d={`M-60 ${y} C135 ${y-50+(i%4)*8} 205 ${y+70-(i%3)*11} 325 ${y+12} S520 ${y-15} 625 ${y+10}`} stroke={i%4===0?'#d4e7d5':i%2?specimen.deep:specimen.tone} strokeWidth={i%4===0?5:9} opacity=".95" fill="none" strokeLinecap="round"/>
        })}
      </g>
      <rect width="540" height="410" fill={`url(#${p}-grain)`}/>
      <path d="M270 0 V410 M0 205 H540" stroke="#e0efed" strokeOpacity=".12" strokeDasharray="5 8" strokeWidth="1"/>
      <circle cx="270" cy="205" r="122" fill="none" stroke="#e0efed" strokeOpacity=".27" strokeWidth="1"/>
      {annotations&&<>
        <circle cx="371" cy="125" r="4" fill="#f5e7c5"/><path d="M371 125 L423 93 L505 93" stroke="#f5e7c5" fill="none" strokeWidth="1.5"/><text x="505" y="82" textAnchor="end" fontSize="12" fontFamily="Arial" fill="#f5e7c5">{specimen.type==='knit'?'LOOP':specimen.type==='fleece'?'SURFACE PILE':specimen.type==='filament'?'FILAMENT':'YARN'}</text>
        <circle cx="162" cy="287" r="4" fill="#f5e7c5"/><path d="M162 287 L112 319 L35 319" stroke="#f5e7c5" fill="none" strokeWidth="1.5"/><text x="35" y="338" fontSize="12" fontFamily="Arial" fill="#f5e7c5">STRUCTURE</text>
      </>}
    </g>
    <g fill="#e6f0ee" fontFamily="Arial" fontSize="11"><text x="20" y="26" letterSpacing="2">ILLUSTRATIVE STRUCTURE VIEW</text><text x="20" y="388">SCHEMATIC • NOT MICROSCOPY</text><text x="518" y="388" textAnchor="end">ZOOM {zoom.toFixed(1)}× (DISPLAY)</text></g>
  </svg>;
}

export default function MicroscopeExplorer() {
  const [active,setActive]=useState(0);
  const [view,setView]=useState('schematics');
  const photoMode=view==='micrographs';
  const specimens=photoMode?MICROGRAPHS:SPECIMENS;
  const [second,setSecond]=useState(1);
  const [compare,setCompare]=useState(false);
  const [zoom,setZoom]=useState(1.25);
  const [labels,setLabels]=useState(true);
  const specimen=specimens[active];
  const next=(step)=>{setActive(x=>(x+step+specimens.length)%specimens.length)};
  return <section id="microscope" className="micro-section">
    <div className="studio-kicker micro-kicker">4 / UNDER THE MICROSCOPE <span>AN INTERACTIVE TEXTILE ATLAS</span></div>
    <div className="micro-intro"><div><div className="micro-eyebrow"><Microscope size={16}/> THE MATERIAL OBSERVATORY</div><h2>LOOK<br/><em>CLOSER.</em></h2></div><p>Before a fabric sheds, it has a structure. Explore how yarns, loops, raised surfaces and filament bundles differ — then connect those observations to the research.</p></div>
    <div className="fp-micro-mode" role="group" aria-label="Image mode"><button className={!photoMode?'selected':''} type="button" onClick={()=>{setView('schematics');setActive(0);setSecond(1);setZoom(1.25)}}>Structure illustrations</button><button className={photoMode?'selected':''} type="button" onClick={()=>{setView('micrographs');setActive(0);setSecond(1);setZoom(1)}}>Real microscopy photographs</button><p>{photoMode?'These are genuine source images of individual fibres. They do not demonstrate whole-fabric construction or shedding performance.':'Conceptual illustrations of fabric and yarn construction — not micrographs.'}</p></div>
    <div className="micro-shell">
      <aside className="micro-specimens"><div className="micro-side-heading">THE SPECIMEN DRAWER <span>4 ENTRIES</span></div>{specimens.map((s,i)=><button key={s.id} type="button" className={`micro-specimen ${active===i?'is-active':''}`} onClick={()=>setActive(i)} aria-pressed={active===i}><span className="micro-number">{s.id}</span><span><strong>{s.label}</strong><small>{s.sub}</small></span><ChevronRight size={16}/></button>)}<div className="micro-side-foot">{photoMode?'The photographs show fibre morphology; they are not evidence of emission rates.':'Drawings explain material structure; they do not measure emissions.'}</div></aside>
      <div className="micro-stage"><div className="micro-stage-top"><span><ScanSearch size={16}/> SPECIMEN / FP–{specimen.id}</span><span>{specimen.family}</span></div>
        <div className={compare?'micro-views is-comparing':'micro-views'}><div className="micro-picture">{photoMode?<MicrographImage specimen={specimen} zoom={zoom}/>:<TextileDrawing specimen={specimen} zoom={zoom} annotations={labels} idSuffix="primary"/>}</div>{compare&&<div className="micro-picture">{photoMode?<MicrographImage specimen={MICROGRAPHS[second]} zoom={zoom}/>:<TextileDrawing specimen={SPECIMENS[second]} zoom={zoom} annotations={labels} idSuffix="secondary"/>}<div className="micro-compare-label">COMPARISON / {specimens[second].label}</div></div>}</div>
        <div className="micro-toolstrip"><div className="micro-zoom"><ZoomOut size={17}/><label htmlFor="micro-zoom-range">Display zoom</label><input id="micro-zoom-range" aria-label="Display zoom" type="range" min="1" max={photoMode?"2":"2.1"} step="0.05" value={zoom} onChange={e=>setZoom(Number(e.target.value))}/><ZoomIn size={17}/><output>{zoom.toFixed(1)}×</output></div>{!photoMode&&<button className={labels?'micro-toggle active':'micro-toggle'} onClick={()=>setLabels(v=>!v)}>{labels?<Eye size={16}/>:<EyeOff size={16}/>} Labels {labels?'on':'off'}</button>}<button className={compare?'micro-toggle active':'micro-toggle'} onClick={()=>setCompare(v=>!v)}><SplitSquareHorizontal size={16}/> Compare {compare?'on':'off'}</button></div>
        {compare&&<div className="micro-select-compare"><label htmlFor="micro-comparison">Compare against</label><select id="micro-comparison" value={second} onChange={e=>setSecond(Number(e.target.value))}>{specimens.map((s,i)=><option key={s.id} value={i}>{s.label}</option>)}</select></div>}
      </div>
      <aside className="micro-notes"><div className="micro-notes-meta">{photoMode?'MICROGRAPH RECORD':'SPECIMEN RECORD'} / {specimen.id}</div><h3>{specimen.label}</h3><span className="micro-notes-sub">{specimen.sub}</span><p>{specimen.detail}</p><div className="micro-rule"/><span className="micro-mini-label">WHAT TO OBSERVE</span><ul>{specimen.notes.map(n=><li key={n}>{n}</li>)}</ul><div className="micro-notice"><Layers3 size={17}/><span>Appearance alone cannot quantify shedding, confirm chemistry, or substitute for a tested model.</span></div><div className="micro-arrows"><button type="button" onClick={()=>next(-1)} aria-label="Previous specimen"><ChevronLeft/></button><span>{active+1} / 4</span><button type="button" onClick={()=>next(1)} aria-label="Next specimen"><ChevronRight/></button></div></aside>
    </div>
    <div className="micro-evidence"><div><span>THE SCIENTIFIC FOOTNOTE</span><p>Research reviews report that textile structure, yarn characteristics and treatments can influence microfiber release. Schematics clarify textile structures; sourced microscopy images show fibre morphology. Neither constitutes a measured shedding rate, a fabric-composition assay, or a validated release prediction.</p></div><a href="https://doi.org/10.1177/00405175241260066" target="_blank" rel="noopener noreferrer">Read the textile-structure review <ArrowUpRight size={17}/></a></div>
  </section>;
}
