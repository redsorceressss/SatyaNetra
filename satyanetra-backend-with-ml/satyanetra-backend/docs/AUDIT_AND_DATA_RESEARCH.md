# Backend Audit and Change Report

## Supplied baseline

The ZIP contained a compact FastAPI application (`app/main.py`, `models.py`, `schemas.py`, `security.py`, `database.py`, `ai.py`, and `config.py`), one initial migration, a small API test file, Docker configuration, and README.

## Issues identified and changes made

1. **Public report lookup exposed sensitive report fields.** The endpoint returned the full `ReportOut` model to anyone who knew a reference. It now returns only reference, workflow status, and timestamps.
2. **Login input was untyped.** Login now uses a Pydantic `LoginIn` schema.
3. **No public sourced-case data existed.** Added curated JSON case records with source links, publication dates, source type, case status, status basis, and amount context.
4. **No API for the public-case data existed.** Added filtered `/api/v1/public-cases` and source catalog endpoint.
5. **The documentation overstated what can be inferred from case reports.** Added a data-integrity warning that a curated collection is not a representative sample and cannot establish a “highest bribery” ranking.

## Data research coverage

The seed dataset includes publicly reported examples for Rajasthan and Madhya Pradesh in India and Louisiana in the United States. Source examples include Indian Express and Times of India reporting, plus U.S. Department of Justice press releases. Official Rajasthan and Bihar reporting portals and national grievance-report references are catalogued as source discovery starting points; grievance statistics are not treated as bribery statistics.

The current case-level data does not yet provide verified examples for every requested state (Delhi, Uttar Pradesh, Bihar, and Telangana). This is stated openly rather than filling gaps with invented or unverified cases. Each source should be opened and the current court/agency status rechecked before production publication.

## Important baseline risks still present

- No application-level rate limiting.
- No complete reporter ownership / second-secret tracking mechanism.
- Official responses are not stored in a dedicated response table.
- Evidence metadata exists but upload/download workflows are absent.
- No password reset, email verification, token revocation, or controlled privileged-role provisioning workflow.
- `Base.metadata.create_all()` is used on startup; production should rely on Alembic migrations and a tested upgrade process.
- Frontend source HTML was not part of the supplied ZIP, so frontend integration could not be inspected or changed.
- AI is a transparent mock; no external model is called.
- Automated test execution was blocked by the environment's missing dependencies and unavailable package network. Tests have been updated but are not claimed to pass.

## Recommended next work

1. Run the suite in a network-enabled Python 3.12 environment.
2. Add regression/security tests and verify database migration behaviour.
3. Add reviewed case records from the relevant official anti-corruption bureaus and court/DOJ records for each target jurisdiction.
4. Use comparable official denominators and definitions before any index or state ranking is displayed.
5. Implement reporter access controls, response persistence, evidence handling, and frontend integration before production use.
