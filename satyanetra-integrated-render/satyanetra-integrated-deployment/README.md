# SatyaNetra — frontend + Python API + ML

This repository contains the existing single-file SatyaNetra website and the FastAPI backend with its integrated ML engine. The website is hosted as a **static site**; the Python API/ML engine must run as a **separate Render Web Service**. Static hosting cannot execute Python, connect to a database, or run the ML package by itself. Both services can live in this one GitHub repository.

## Repository layout

```text
SatyaNetra/
├── frontend/
│   ├── index.html       # Existing visual website, preserved and wired to API when configured
│   └── config.js        # Set the public API base URL here; no secrets
├── backend/             # FastAPI API, SQLAlchemy models, migrations, data and ML package
│   ├── app/main.py
│   ├── requirements.txt
│   ├── satyanetra_ml/
│   └── data/public_cases.json
├── .gitignore
└── README.md
```

## Deploy the backend on Render

Create **New → Web Service** and connect this repository. Choose the **Python** runtime, not Docker. Set:

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Set environment variables in Render (not in GitHub):

- `JWT_SECRET`: a unique, cryptographically random secret of at least 32 characters. Do not use the development default.
- `CORS_ORIGINS`: the exact deployed frontend origin, e.g. `https://satyanetra-frontend.onrender.com` (no path; comma-separated only if needed).
- `ENVIRONMENT`: `production`
- `DATABASE_URL`: preferably a Render PostgreSQL connection URL using SQLAlchemy's expected `postgresql+psycopg://...` scheme.
- `AI_PROVIDER`: `mock` unless a real, implemented provider adapter is configured. The current AI endpoint is a rule-based guidance service, not a hosted LLM.

The default SQLite database on a typical ephemeral web-service filesystem is not durable across service replacement/redeploys. Configure persistent PostgreSQL before treating reports as durable. Review migrations and database setup before production.

After deployment, test `https://YOUR-API-URL.onrender.com/api/v1/health` and `https://YOUR-API-URL.onrender.com/docs`. Also test `POST /api/v1/ai/analyze-report` with synthetic text. A health response alone does not prove that the ML engine or durable database works.

## Deploy the frontend as a Render Static Site

Create **New → Static Site** using the same GitHub repository. Set:

- Root Directory: `frontend`
- Build Command: leave blank
- Publish Directory: `.`

After the backend is deployed, edit `frontend/config.js` in GitHub and set:

```js
window.SATYANETRA_API_BASE_URL = "https://YOUR-API-URL.onrender.com";
```

Replace the example with your real backend URL and redeploy the static site. Add the resulting frontend origin to the backend's `CORS_ORIGINS` environment variable and redeploy the backend. Do not add API keys or secret values to `config.js`; all browser users can read it.

## Frontend integration currently wired

- Report form submits to `POST /api/v1/reports` when the API base URL is configured. In API mode, this endpoint currently does **not** accept evidence attachments, external-source links/context, or a linked demo payment; the UI blocks submission if these unsupported optional fields are populated rather than silently discarding them.
- The explicit **Analyze description with SatyaNetra ML** button calls `POST /api/v1/ai/analyze-report`. Analysis is user-triggered; scores and indicators are leads for human review, not evidence of guilt.
- SatyaNetra AI question widget calls `POST /api/v1/ai/ask`. This backend currently returns rule-based mock guidance; it is not a live external LLM integration.
- If `config.js` is blank, the website remains in its original browser-only demo mode. It does not save or transmit reports.

## Run locally on Windows

From the repository root, open PowerShell:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and replace JWT_SECRET with a random secret before running
uvicorn app.main:app --reload
```

Serve the frontend with VS Code Live Server or another static server. Set `frontend/config.js` to `http://127.0.0.1:8000` and set `CORS_ORIGINS` in backend `.env` to the actual local frontend origin (often `http://127.0.0.1:5500`).

## Important limitations

This is a prototype, not a production whistleblowing service. The backend README and deployment guide document outstanding security and operational work. Do not submit real sensitive allegations until persistent storage, authorization, abuse/rate controls, retention, backups, monitoring and privacy controls have been reviewed. Never treat ML similarity or heuristic indicators as proof of wrongdoing.
