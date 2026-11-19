# FIBREPRINT / Living Lab visual upgrade

This is an additive UI layer. No API, authentication, research metrics, scientific safeguards or data files are replaced.

## Files

- `frontend/src/LivingLab.jsx` — optional dismissible fibre-detective companion; a visually rich texture interlude; lightweight entry animation.
- `frontend/src/living-lab.css` — slow fibre current and dot drift over hero; fabric-card hover; mobile and reduced-motion styles.
- `frontend/public/images/mascot/fibre-detective.png` — transparent mascot image.
- `frontend/install_living_lab.py` — safe idempotent App.jsx insertion, creates a backup before editing.

The texture interlude reuses images already loaded in prior FIBREPRINT versions: `frontend/public/images/fabrics/denim.webp`, `.../fleece.webp`, `frontend/public/images/microscopy/polyester-sem.jpg`. Check that these exist. Image labels say *illustrative*. Photo credits remain in original archive sections.

## Setup

1. Copy files into exact locations above (create the `mascot` folder if necessary).
2. From `FIBREPRINT/frontend/` run:

   `python install_living_lab.py`

3. If Windows has no `python` command, run `py install_living_lab.py`.
4. Start or refresh Vite: `npm.cmd run dev`.
5. Confirm hero's subtle motion, texture strip before the workbench, companion in the lower right, and **all** existing scientific sections and login still work.

## Undo

Restore `frontend/src/App.jsx.before_living_lab.bak` over `App.jsx`. Remove the new files. Do not delete any research scripts or v0.25 backend files.

## Notes

The field notes are informational and do not connect to the LLM or predict release. The companion can be dismissed. Mobile styles and `prefers-reduced-motion` are included. The animated overlay uses CSS only and should not interfere with interactions.
