"""Safely integrate v0.25 with existing FIBREPRINT files. Backs up each file.
Run from backend directory: .venv\\Scripts\\python.exe install_v25.py
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import shutil
import sys


def patch(path, change):
    original = path.read_text(encoding='utf-8')
    updated = change(original)
    if updated == original:
        print('UNCHANGED', path)
        return
    backup = path.with_suffix(path.suffix + '.before_v25.bak')
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(updated, encoding='utf-8')
    print('UPDATED', path, '(backup:', backup.name + ')')


def patch_api(src):
    if 'from .research_status import router as research_router' not in src:
        anchor = 'from .model_engine import model_status, evaluate_model'
        if anchor not in src: raise ValueError('main.py has changed: cannot find model_engine import; no automatic edit')
        src=src.replace(anchor,anchor+'\nfrom .research_status import router as research_router',1)
    if 'app.include_router(research_router)' not in src:
        match=re.search(r'^app\s*=\s*FastAPI\(.*\)\s*$',src,re.M)
        if not match: raise ValueError('main.py has changed: cannot find FastAPI declaration; no automatic edit')
        src=src[:match.end()]+'\napp.include_router(research_router)'+src[match.end():]
    return src


def patch_frontend(src):
    if "import ResearchStatus from './ResearchStatus';" not in src:
        anchor="import ResearchResults from './ResearchResults';"
        if anchor not in src: raise ValueError('App.jsx missing ResearchResults import; no automatic edit')
        src=src.replace(anchor,anchor+"\nimport ResearchStatus from './ResearchStatus';",1)
    # Replace only the two-column, model-artifact-derived readiness panel;
    # preserve authentication, workbench, ResearchResults, ExternalEvidence, microscope.
    start='<div className="fp-model-readiness">'
    end='<div className="csv-area">'
    if '<ResearchStatus token={token}/>' not in src:
        a=src.find(start)
        b=src.find(end,a+len(start)) if a>=0 else -1
        if a<0 or b<0: raise ValueError('App.jsx readiness panel not found; no automatic edit')
        src=src[:a]+'<ResearchStatus token={token}/>'+src[b:]
    # This is a research-only state, not a generic training failure.
    if "'RESEARCH ONLY — NO SERVING MODEL'" not in src:
        src=src.replace("(report?.prediction_status||'NOT YET VALIDATED').replaceAll('_',' ')",
                        "(report?.prediction_status==='NOT_TRAINED'?'RESEARCH ONLY — NO SERVING MODEL':(report?.prediction_status||'NOT YET VALIDATED').replaceAll('_',' '))")
    return src


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--backend',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--frontend',type=Path,default=None)
    args=parser.parse_args()
    backend=args.backend.resolve()
    frontend=args.frontend.resolve() if args.frontend else backend.parent/'frontend'/'src'
    api=backend/'app'/'main.py'
    source=backend/'app'/'research_status.py'
    ui=frontend/'App.jsx'
    component=frontend/'ResearchStatus.jsx'
    for path in [api,source,ui,component]:
        if not path.is_file():
            parser.error('Missing required file: '+str(path))
    # Compute both patches before writing anything; no partial writes on mismatch.
    try:
        original_api=api.read_text(encoding='utf-8')
        original_ui=ui.read_text(encoding='utf-8')
        patch_api(original_api)
        patch_frontend(original_ui)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    patch(api,patch_api)
    patch(ui,patch_frontend)
    print('DONE. Research endpoint: GET /api/research/status (requires login).')
    print('Original copies are saved as *.before_v25.bak')

if __name__=='__main__': main()
