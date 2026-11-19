import React, { useEffect, useState } from 'react';
import { ArrowUpRight, X, Sparkles } from 'lucide-react';
import './living-lab.css';

const notes = [
  { label: 'FIELD NOTE / 1', text: 'A fibre can be tiny, but its behaviour depends on the whole fabric: yarn, construction and finish.' },
  { label: 'FIELD NOTE / 2', text: 'Not all microfibres are plastic. Cotton, wool and synthetic textiles can all shed fibres.' },
  { label: 'FIELD NOTE / 3', text: 'The 155 measured release records are source-matched. Prediction for a new fabric remains research-only.' },
  { label: 'FIELD NOTE / 4', text: 'A washing protocol matters as much as its reported units. Different experiments are not automatically comparable.' }
];

// Additive enhancement: no backend calls, no model predictions, no page structure changes.
export default function LivingLab() {
  const [note, setNote] = useState(0);
  const [open, setOpen] = useState(false);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) return;
    const targets = [...document.querySelectorAll('.hero-grid, .fp-atlas-card, .process-node, .fact-stage, .evidence-head, .fp-model-readiness, .fp-textile-atlas, .workbench-head')];
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('fp-visible');
          observer.unobserve(entry.target);
        }
      }
    }, { threshold: 0.09, rootMargin: '0px 0px 30px 0px' });
    targets.forEach(node => {
      // Prevent hiding existing content: these classes only add motion to visible cards.
      node.classList.add('fp-can-reveal');
      if (node.getBoundingClientRect().top < window.innerHeight * 0.92) node.classList.add('fp-visible');
      else observer.observe(node);
    });
    return () => { observer.disconnect(); targets.forEach(node => node.classList.remove('fp-can-reveal', 'fp-visible')); };
  }, []);

  if (hidden) return null;
  return <aside className={'fp-companion' + (open ? ' is-open' : '')} aria-label="FIBREPRINT field guide">
    {open && <div className="fp-companion-note" role="status">
      <div className="fp-companion-note-top"><span>{notes[note].label}</span><button type="button" onClick={() => setOpen(false)} aria-label="Close field note"><X size={15}/></button></div>
      <p>{notes[note].text}</p>
      <div className="fp-companion-note-foot"><span>FIBREPRINT / POCKET FIELD GUIDE</span><button type="button" onClick={() => setNote(i => (i + 1) % notes.length)}>Next note <ArrowUpRight size={14}/></button></div>
    </div>}
    <div className="fp-companion-dock">
      <button className="fp-companion-character" type="button" onClick={() => setOpen(value => !value)} aria-label={open ? 'Close field guide' : 'Ask the fibre detective'} aria-expanded={open}>
        <img src="/images/mascot/fibre-detective.png" alt="Teal fibre detective with a magnifying glass" loading="lazy" />
      </button>
      <div className="fp-companion-title"><span><Sparkles size={12}/> MEET THE GUIDE</span><strong>Fibre Detective</strong><button type="button" onClick={() => setOpen(v => !v)}>{open ? 'Hide field note' : 'A field note for you'} <ArrowUpRight size={13}/></button></div>
      <button className="fp-companion-dismiss" type="button" aria-label="Dismiss mascot" onClick={() => setHidden(true)}><X size={14}/></button>
    </div>
  </aside>;
}

export function TextureInterlude(){
  const textures = [
    {src:'/images/fabrics/denim.webp', name:'THE WEAVE', text:'A closer look at textile construction.', tag:'ILLUSTRATIVE TEXTURE'},
    {src:'/images/fabrics/fleece.webp', name:'THE SURFACE', text:'Raised fibres and structures worth investigating.', tag:'ILLUSTRATIVE TEXTURE'},
    {src:'/images/microscopy/polyester-sem.jpg', name:'THE MICROSCOPY', text:'A view into material-scale questions.', tag:'ILLUSTRATIVE MICROGRAPH'}
  ];
  return <section className="fp-texture-interlude" aria-label="Textile observation gallery">
    <div className="fp-texture-heading"><span>SPECIMEN INTERLUDE / OBSERVE FIRST</span><h2>Look a little <em>closer.</em></h2><p>Three views of the material question. Photographs and microscopy imagery are visual references, not verified measurements of the specimen you entered.</p></div>
    <div className="fp-texture-grid">{textures.map((t,i)=><figure className="fp-texture-card" key={t.name}>
      <div className="fp-texture-image"><img src={t.src} alt={t.name + ': illustrative textile imagery'} loading="lazy"/><span>{t.tag}</span></div>
      <figcaption><small>FIELD STUDY / {i+1}</small><strong>{t.name}</strong><p>{t.text}</p></figcaption>
    </figure>)}</div>
    <p className="fp-texture-caveat">Local visual assets already used within FIBREPRINT. See the original archive and microscope sections for image credits and research context.</p>
  </section>;
}
