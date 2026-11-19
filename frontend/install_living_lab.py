"""Additive patch to frontend/src/App.jsx. Run from anywhere: python install_living_lab.py
Never overwrites App.jsx without first creating a backup.
"""
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
app = HERE / 'src' / 'App.jsx'
if not app.is_file():
    sys.exit(f'ERROR: {app} missing; place installer in FIBREPRINT/frontend/')
source = app.read_text(encoding='utf-8')
updated = source
imp = "import LivingLab, { TextureInterlude } from './LivingLab';"
if imp not in updated:
    # Insert before the first import to avoid touching existing imports.
    updated = imp + '\n' + updated
if '<TextureInterlude/>' not in updated and '<TextureInterlude />' not in updated:
    anchor = '<section id="workbench"'
    if anchor not in updated:
        sys.exit('ERROR: workbench anchor not found; App.jsx NOT edited. Please share current App.jsx.')
    updated = updated.replace(anchor, '<TextureInterlude/>\n      ' + anchor, 1)
if '<LivingLab/>' not in updated and '<LivingLab />' not in updated:
    anchor = '</main>'
    if anchor not in updated:
        sys.exit('ERROR: main closing tag not found; App.jsx NOT edited.')
    updated = updated.replace(anchor, '<LivingLab/>\n    ' + anchor, 1)
if source == updated:
    print('ALREADY INSTALLED. No changes made.')
else:
    backup = app.with_name('App.jsx.before_living_lab.bak')
    if not backup.exists(): shutil.copy2(app, backup)
    app.write_text(updated, encoding='utf-8')
    print('INSTALLED. Original backup:', backup)
print('Check frontend/src/LivingLab.jsx and living-lab.css; public/images/mascot/fibre-detective.png')
