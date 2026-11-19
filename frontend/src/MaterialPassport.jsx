import React, {useEffect,useRef,useState} from 'react';
import {ArrowRight,ArrowUpRight,BookOpen,Check,ChevronLeft,ChevronRight,FlaskConical,Info,Layers3,Microscope,Search,X,ZoomIn,ZoomOut} from 'lucide-react';
import './material-passport.css';

const NOTES={
  woven:{what:'Warp and weft yarns intersect to make a stable woven surface.',inspect:['Yarn density and interlacing pattern','Loose ends, fuzzing and surface abrasion','Finishing treatments and wash history'],question:'How might yarn twist, finish and repeated washing change what is released?'},
  knit:{what:'Knitted structures are built from connected loops and can stretch differently from woven surfaces.',inspect:['Loop size and stitch density','Exposed yarn surfaces and pilling','Fabric weight and pre-wash treatment'],question:'How might loop geometry and surface wear affect release during laundering?'},
  fleece:{what:'A raised or brushed surface changes the exposed fibre ends and surface character.',inspect:['Extent of raised pile or brushing','Loose fibres visible on the surface','Fabric construction beneath the pile'],question:'Would an untreated and a brushed specimen behave differently in an identical wash?'},
};
const guide=[
  {label:'Fibre identity',value:'Not verified',detail:'A texture photograph cannot establish chemical composition.'},
  {label:'Weight / GSM',value:'Not measured',detail:'Requires a weighed sample of known area.'},
  {label:'Release rate',value:'Not validated',detail:'Cannot be inferred from a photograph.'},
];
const doi='https://doi.org/10.1177/00405175241260066';
export default function MaterialPassport({specimens,selectedIndex,onClose,onInvestigate}){
  const [index,setIndex]=useState(selectedIndex ?? 0);
  const [activeTab,setActiveTab]=useState('profile');
  const [zoom,setZoom]=useState(false);
  const [showAnnotations,setShowAnnotations]=useState(true);
  const dialogRef=useRef(null);
  const [lensPoint,setLensPoint]=useState({x:50,y:50});
  const specimen=specimens[index];
  const explainer=NOTES[specimen.construction] || NOTES.woven;
  useEffect(()=>{setIndex(selectedIndex ?? 0);setActiveTab('profile');setZoom(false);setLensPoint({x:50,y:50})},[selectedIndex]);
  useEffect(()=>{
    const previousActive=document.activeElement;
    const previousOverflow=document.body.style.overflow;
    document.body.style.overflow='hidden';
    dialogRef.current?.focus();
    return ()=>{document.body.style.overflow=previousOverflow;previousActive?.focus?.()};
  },[]);
  useEffect(()=>{
    const handler=e=>{
      if(e.key==='Escape'){e.preventDefault();onClose();return;}
      if(['INPUT','TEXTAREA','SELECT'].includes(e.target?.tagName)||e.target?.isContentEditable)return;
      if(e.key==='ArrowLeft'||e.key==='ArrowRight'){
        e.preventDefault();
        setIndex(i=>(i+(e.key==='ArrowRight'?1:-1)+specimens.length)%specimens.length);
        setZoom(false);setLensPoint({x:50,y:50});
      }
      if(e.key==='Tab'){
        const nodes=[...(dialogRef.current?.querySelectorAll('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])') || [])];
        if(!nodes.length)return;
        const first=nodes[0],last=nodes[nodes.length-1];
        if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
        else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
      }
    };
    document.addEventListener('keydown',handler);
    return ()=>document.removeEventListener('keydown',handler);
  },[onClose,specimens.length]);
  const move=delta=>{setIndex(i=>(i+delta+specimens.length)%specimens.length);setZoom(false);setLensPoint({x:50,y:50})};
  const moveLens=e=>{
    if(!zoom)return;
    const box=e.currentTarget.getBoundingClientRect();
    const x=Math.max(0,Math.min(100,(e.clientX-box.left)/box.width*100));
    const y=Math.max(0,Math.min(100,(e.clientY-box.top)/box.height*100));
    setLensPoint({x,y});
  };
  return <div className="mp-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}>
    <section ref={dialogRef} tabIndex={-1} className="mp-dialog" role="dialog" aria-modal="true" aria-label={`${specimen.name} material passport`}>
      <div className="mp-topline"><div className="mp-topbrand"><span className="mp-mark">f/p</span><span>FIBREPRINT <b>/ MATERIAL ARCHIVE</b></span></div><div className="mp-top-actions"><span>SPECIMEN {index+1} OF {specimens.length}</span><button className="mp-icon-button" onClick={onClose} aria-label="Close material passport"><X size={19}/></button></div></div>
      <div className="mp-layout">
        <div className="mp-visual">
          <div className={'mp-image '+(zoom?'is-zoomed':'')} onPointerMove={moveLens} style={{'--lens-x':`${lensPoint.x}%`,'--lens-y':`${lensPoint.y}%`}}><img src={specimen.file} alt={`Photographic textile reference: ${specimen.name}`}/>{showAnnotations&&<><span className="mp-image-corner">{specimen.id} · SURFACE REFERENCE</span><div className="mp-image-scope"><span className="mp-crosshair">+</span><span>VISIBLE SURFACE<br/>NOT A LAB ASSAY</span></div></>}<span className="mp-magnification" aria-live="polite">DISPLAY {zoom?'1.6×':'1×'}{zoom?' · MOVE TO INSPECT':''}</span>{zoom&&<span className="mp-focus-guide" aria-hidden="true"/>}</div>
          <div className="mp-image-tools"><button onClick={()=>setZoom(z=>!z)}>{zoom?<ZoomOut size={15}/>:<ZoomIn size={15}/>} {zoom?'Reset image':'Inspect texture'}</button><button onClick={()=>setShowAnnotations(v=>!v)}><Search size={15}/>{showAnnotations?'Hide labels':'Show labels'}</button></div>
          <a className="mp-photo-credit" href={specimen.source} target="_blank" rel="noopener noreferrer"><span>IMAGE SOURCE</span><span className="mp-credit-url">{specimen.source}</span><ArrowUpRight size={13}/></a>
          <div className="mp-visual-footer"><span>ARCHIVE / PHOTOGRAPHIC REFERENCE</span><div><button aria-label="Previous specimen" onClick={()=>move(-1)}><ChevronLeft size={18}/></button><span>{index+1} / {specimens.length}</span><button aria-label="Next specimen" onClick={()=>move(1)}><ChevronRight size={18}/></button></div></div>
        </div>
        <div className="mp-content">
          <div className="mp-id"><span>TEXTILE PASSPORT</span><span>ARCHIVE RECORD · 2026</span></div>
          <h2>{specimen.name}</h2><p className="mp-lede">{specimen.detail}</p>
          <div className="mp-tabs" role="tablist" aria-label="Passport information"><button role="tab" aria-selected={activeTab==='profile'} className={activeTab==='profile'?'active':''} onClick={()=>setActiveTab('profile')}><Layers3 size={16}/> Profile</button><button role="tab" aria-selected={activeTab==='inquiry'} className={activeTab==='inquiry'?'active':''} onClick={()=>setActiveTab('inquiry')}><BookOpen size={16}/> Research questions</button></div>
          {activeTab==='profile'?<div className="mp-tab-panel"><div className="mp-attributes"><div><span>CONSTRUCTION</span><strong>{specimen.construction}</strong></div><div><span>SAMPLE STATUS</span><strong>Illustrative</strong></div><div><span>FIBRE CONTENT</span><strong>Unverified</strong></div></div><p className="mp-description">{explainer.what} This is a visual example, not an identified or tested fabric sample.</p><div className="mp-subhead">WHAT'S KNOWN / WHAT NEEDS TESTING</div><div className="mp-readiness">{guide.map(item=><div key={item.label} className="mp-readiness-item"><span>{item.label}</span><strong className="mp-readiness-status"><span className="mp-status-dot" aria-hidden="true"/>{item.value}</strong><small>{item.detail}</small></div>)}</div></div>:<div className="mp-tab-panel mp-research"><div className="mp-subhead">UNDER INVESTIGATION</div><ul>{explainer.inspect.map((observation,i)=><li key={observation}><b>{i+1}</b><span>{observation}</span></li>)}</ul><p className="mp-question"><Info size={17}/> {explainer.question}</p><a href={doi} target="_blank" rel="noopener noreferrer">Textile structure and release — peer-reviewed review <ArrowUpRight size={15}/></a></div>}
          <div className="mp-actions"><button className="mp-primary" onClick={()=>onInvestigate(specimen)}><FlaskConical size={17}/> Load construction into workbench <ArrowRight size={17}/></button><button className="mp-secondary" onClick={()=>{onClose();requestAnimationFrame(()=>document.querySelector('#microscope')?.scrollIntoView({behavior:'smooth',block:'start'}))}}><Microscope size={16}/> Open microscope</button></div>
          <p className="mp-disclaimer"><Check size={14}/> No shedding number is generated from this photograph. All experimental inputs remain editable.</p><p className="mp-keyhint">KEYBOARD / ← → CHANGE SPECIMEN · ESC CLOSE</p>
        </div>
      </div>
    </section>
  </div>;
}
