# SatyaNetra Backend

FastAPI + SQLAlchemy backend for the existing SatyaNetra frontend. This ZIP preserves the starter project and adds a source-attributed public bribery/corruption case dataset.

## What changed in this update

- Added `data/public_cases.json`: curated examples of publicly reported bribery/corruption cases in Rajasthan and Madhya Pradesh, India, and Louisiana, United States. Every record carries a source URL, publisher, publication date, status basis, last-reviewed date, and amount context.
- Added `data/source_catalog.json` with official agency/report portals for ongoing source collection.
- Added `GET /api/v1/public-cases` with optional `state`, `jurisdiction`, and `category` filters.
- Added `GET /api/v1/public-cases/sources`.
- Changed public report-reference lookup to return workflow status and timestamps only; it no longer returns the report description, location, or contact email to anyone who knows a reference.
- Changed login input from an unvalidated generic dictionary to a Pydantic schema.
- Added tests for case provenance, filtering, and sensitive report lookup fields.

## Important data-integrity notes

This is a **curated seed dataset**, not a complete national or international register, not a live feed, and not a representative statistical sample. Do not describe it as “all cases”. Public case announcements vary in coverage and legal status.

- The data does **not** establish that Rajasthan, Bihar, Uttar Pradesh, Telangana, Delhi, or Louisiana has the “highest bribery” rate. Counts of news articles, arrests, FIRs, indictments, convictions, complaints, and perception indices measure different things. A defensible ranking needs a comparable, clearly defined denominator and consistent official data across every jurisdiction.
- Some records are allegations or indictments; others are reported guilty pleas or convictions. The `case_status` and `status_basis` fields preserve that distinction. An allegation is not proof of guilt.
- Reported money amounts are not necessarily comparable. `amount_context` explains whether the figure is an alleged demand, alleged payment, or another financial figure.
- Sources are linked for human verification. The backend does not scrape the internet automatically or continuously refresh case statuses.
- For national breadth, official annual-report portals are catalogued, but this seed set currently has case-level examples primarily from Rajasthan and Madhya Pradesh. It does not yet include verified individual case records for Delhi, Uttar Pradesh, Bihar, or Telangana. Those should be added only after source-level review.

## API

- `GET /api/v1/health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/reports`
- `GET /api/v1/reports/{reference}` — public status-only response
- `GET /api/v1/reports` — authenticated
- `PATCH /api/v1/reports/{reference}/status` — reviewer/admin
- `POST /api/v1/official-responses`
- `POST /api/v1/ai/ask` — rule-based mock unless a provider adapter is implemented
- `GET /api/v1/public-cases?state=Louisiana`
- `GET /api/v1/public-cases?jurisdiction=India`
- `GET /api/v1/public-cases/sources`
- `GET /api/v1/transparency-index` — still explicitly unimplemented; no validated index is calculated.

OpenAPI docs when running: `http://127.0.0.1:8000/docs`.

## Windows / VS Code setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `JWT_SECRET` in `.env` to a unique random value before running. Keep `.env` private.

```powershell
uvicorn app.main:app --reload
```

## Tests

```powershell
pytest -q
```

The test suite could not be executed successfully in the code-editing environment because the dependency installation was blocked by unavailable network access (`pwdlib` was not installed). Run the commands above in an environment with package access before relying on the changes. This is an honest execution limitation, not a passing test claim.

## Docker

```powershell
docker compose up --build
```

Review `.env.example` and `docker-compose.yml` before exposing the API publicly. Do not commit credentials or use development defaults in production.

## Security and implementation status

This remains an early-stage prototype, not a production-ready whistleblowing platform. Public report lookup has been narrowed to status-only, but additional work remains before handling real sensitive allegations:

- Add rate limiting for login, report creation, and reference lookup at a trusted proxy or application layer.
- Add a private tracking secret or authenticated ownership model for reporter status access.
- Link identified report submissions to the authenticated owner; the current guest-capable endpoint does not yet establish that relationship.
- Persist official responses in a dedicated database entity rather than an audit event.
- Implement secure evidence upload/download, malware scanning, retention, and access auditing.
- Implement password reset, email verification, account lifecycle, controlled privileged-account provisioning, and token revocation.
- Replace startup `create_all` reliance with a migration-led deployment process and add non-destructive upgrade migrations.
- Review production JWT secret enforcement, CORS, TLS, trusted hosts, backups, monitoring, and PostgreSQL integration.
- Connect the frontend's actual JavaScript to these API endpoints; the frontend HTML was not supplied in this ZIP and was not modified.
- Connect a verified external AI provider only after credentials and its API contract are available. No watsonx.ai integration is claimed.

Never use this sample dataset as evidence that a person or organisation is guilty, or as a risk score for an individual.
