# SatyaNetra API deployment and frontend connection

## 1. Local backend

Run these commands in the `satyanetra-backend` directory on Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set a unique, random `JWT_SECRET` of at least 32 characters. Keep `.env` private and never commit it. For local development, `DATABASE_URL=sqlite:///./satyanetra.db` is suitable for a basic smoke test.

Start the API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check `http://127.0.0.1:8000/api/v1/health` and open `http://127.0.0.1:8000/docs`.

## 2. Frontend API base URL

The local API base URL is:

`http://127.0.0.1:8000/api/v1`

The website's JavaScript should use that base URL while developing locally. When deployed, replace it with the actual HTTPS URL assigned to the deployed backend, followed by `/api/v1`. Do not put a guessed URL in the backend `.env`.

If the frontend is plain HTML/JavaScript, define a single API base URL in its configuration or JavaScript file and have requests use it consistently. If the frontend uses a build tool, use that tool's documented public environment-variable convention. Never put `JWT_SECRET`, database credentials, or private AI keys in frontend code.

## 3. CORS

`CORS_ORIGINS` is a comma-separated list of exact frontend origins, including scheme and port, without a trailing API path. Example for local development:

`CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500`

When the website is hosted, set this backend environment variable to the real website origin (for example `https://your-real-site.example`) and retain local origins only if you still need local development. Do not copy the example domain literally.

## 4. Deployment requirements

- Deploy the backend to a Python/FastAPI-compatible host and configure environment variables in that host's dashboard.
- Use managed PostgreSQL for a persistent deployed database; do not rely on an ephemeral local SQLite file for production.
- Set `DATABASE_URL` to the database URL supplied by your host, in SQLAlchemy/psycopg format.
- Set a strong, unique `JWT_SECRET`; never use the example/default secret in production.
- Configure `CORS_ORIGINS` to the exact deployed frontend origin.
- Enable HTTPS and configure backups, monitoring, and access controls.
- Once deployed, verify `https://YOUR-REAL-BACKEND-HOST/api/v1/health` and `https://YOUR-REAL-BACKEND-HOST/docs` using the actual host URL.
- Then configure the frontend's API base URL to `https://YOUR-REAL-BACKEND-HOST/api/v1`.

## 5. Dataset and AI limitations

The public cases endpoint reads `data/public_cases.json`; the Docker image must include the `data` directory. This project uses curated seed records, not a continuously updated official registry. The AI endpoint currently uses a rule-based mock unless an implemented provider adapter is added. Setting an AI provider name or API key alone does not implement that integration.

## 6. Before handling real sensitive reports

This remains a prototype. The README documents outstanding security and workflow work, including rate limiting, safe ownership/tracking, privileged-account provisioning, evidence upload/download security, and migration-led deployment. Do not treat it as production-ready for sensitive whistleblower submissions until those controls are implemented and independently tested.
