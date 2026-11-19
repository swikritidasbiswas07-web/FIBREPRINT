"""Optional: fix misleading field in existing v0.22 report and script, without re-training.
Place in backend and run: .venv\\Scripts\\python.exe fix_applicability_v22.py
"""
from pathlib import Path
import json
import shutil

root=Path(__file__).resolve().parent
script=root/'analyze_applicability.py'
report=root/'data'/'vassilenko_applicability_report.json'
old='missed_interval_violations_by_warning'
new='caught_interval_violations_by_warning'
if script.exists():
    content=script.read_text(encoding='utf-8')
    if old in content:
        backup=script.with_suffix('.py.before_v25.bak')
        if not backup.exists():shutil.copy2(script,backup)
        script.write_text(content.replace(old,new),encoding='utf-8')
        print('Fixed analyzer field name. Backup:',backup)
if report.exists():
    obj=json.loads(report.read_text(encoding='utf-8'))
    summary=obj.get('summary',{})
    if old in summary:
        caught=summary.pop(old)
        total=summary.get('total_interval_violations')
        if not isinstance(total,int) or not isinstance(caught,int) or caught>total or caught<0:
            raise ValueError('Cannot reconcile original warning counts')
        summary[new]=caught
        summary['unflagged_interval_violations']=total-caught
        backup=report.with_suffix('.json.before_v25.bak')
        if not backup.exists():shutil.copy2(report,backup)
        report.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print('Corrected diagnostic report (caught =',caught,', unflagged =',total-caught,').')
else: print('Report missing; rerun analyzer after script fix.')
print('Done; this does not change any model, result or experimental status.')
