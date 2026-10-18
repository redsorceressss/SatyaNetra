# SatyaNetra ML Data Directory

This directory is an optional local cache / standalone fallback location for public case reference data.

## Primary Data Source
In the standard project configuration, the ML engine accesses the authoritative curated public case dataset directly from:
`satyanetra-backend/data/public_cases.json` (i.e. `../data/public_cases.json` relative to this component). Do not keep a second copy here when running inside the backend; the two would drift apart.

## Fallback
If the parent repository is not present (e.g. when deploying `satyanetra_ml` in an isolated container or microservice), a copy of `public_cases.json` can be placed here (`data/public_cases.json`) or referenced via the `SATYANETRA_DATA_PATH` environment variable.

## Data Principles
- All cases must carry official provenance (title, source URL, publisher, date, legal status basis).
- Curated cases are reference examples, NOT an exhaustive national registry.
- Do not fabricate synthetic training records as real cases.
