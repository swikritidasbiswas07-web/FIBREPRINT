# FIBREPRINT v0.2 — Editorial login + research workbench

This ZIP **updates the existing starter** with a full sign-in / create-account screen. It contains all source files, not just a standalone login component.

## What works
- Register with name, email and password (minimum 10 characters).
- Login, session restoration on reload, sign out.
- SQLite accounts and sessions persisted on the backend; passwords hashed using PBKDF2-HMAC-SHA256 with unique per-user salts.
- Cryptographically random bearer tokens, stored as SHA256 hashes in SQLite and expiring after 12 hours.
- `/api/evaluate` and `/api/validate-csv` require authentication.
- Protected research workbench and existing fabric/wash steps retained.
- No paid authentication provider, no API key needed.

**Security scope:** Suitable for LOCAL MVP DEMONSTRATION, not public production without HTTPS, abuse protection/rate limiting, email verification, password reset, account recovery, CSRF/session strategy review, audit logging and more robust session handling. Do not use real personal credentials for a publicly deployed prototype yet. The password is never stored in plaintext. The bearer token is kept in `sessionStorage` (cleared when the tab closes) and is vulnerable to XSS, so deploy only after appropriate hardening. Login is not connected to Google or any external identity system. Existing fabric settings are currently client-side only, not per-user persisted.

## Windows startup (PowerShell)

Open the newly extracted `FIBREPRINT_MVP_Login_v02` folder in VS Code.

### Terminal 1 — backend
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### Terminal 2 — frontend
```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```
Open `http://localhost:5173`. Register a new account, sign in, and open your workbench.

If you already have the old environment running: **stop both old terminals** (`Ctrl+C`) and start them from the new `backend` / `frontend` folder. You can optionally use your old virtual environment, but avoid confusing two different local app copies.

## Backend routes
- `POST /api/auth/register` — `{name,email,password}`
- `POST /api/auth/login` — `{email,password}`
- `GET /api/auth/me` — bearer token required
- `POST /api/auth/logout` — revokes bearer token
- `GET /api/health` and `GET /api/sources` — public
- `POST /api/evaluate`, `POST /api/validate-csv` — bearer token required

SQLite database is created on first account action at `backend/data/fibreprint_users.sqlite3`. Override with `FIBREPRINT_DB_PATH` for tests.

## Current scientific limits
No trained microfiber emission predictor is included. Predictions remain unavailable until research data are curated and the scientific model is validated. Auth credentials are unrelated to prediction quality.


## What is new in v0.3 — Research Studio

- Field Notes: four clickable, study-specific facts with limitations and primary DOI links.
- Material Quiz: five interactive evidence-backed questions, answers, explanations and sources. No account data is stored for quiz scores.
- Pocket Reference: expandable six-term textile science glossary.
- Research Ledger: expanded from three to five verified references and DOI links.
- All login/registration and existing workbench functions are retained.

**Scientific note:** All displayed numerical observations are cited **literature findings**, never outputs from the not-yet-validated FIBREPRINT model.

**Local upgrade:** Stop both servers, unzip this release into a new folder, then run the same backend and frontend commands as v0.2. Your existing local SQLite account database is **not automatically migrated** to the new folder. To keep existing accounts locally, stop both versions and copy `backend/data/fibreprint_users.sqlite3` (unless you configured a different path using `FIBREPRINT_DB_PATH`) from the old version to the new one.
