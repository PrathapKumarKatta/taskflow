# TaskFlow deployment verification

Verified on 24 October 2026.

## Live application

- App: https://taskflow-virid-three.vercel.app
- API docs: https://taskflow-virid-three.vercel.app/docs
- Database readiness: https://taskflow-virid-three.vercel.app/health/ready
- Source: https://github.com/PrathapKumarKatta/taskflow
- Vercel project: `taskflow`, scope `prathapkumarkattas-projects`

The repository root contains `vercel.json`. Vercel Services (currently beta) builds the Vite frontend in `frontend` and the FastAPI service at the repository root together. API, health, and documentation paths route to FastAPI; other requests route to the SPA. Production uses same-origin API requests, so no `VITE_API_BASE_URL` override is required. Python is pinned to 3.12; Node is 24.

GitHub auto-deployment is connected to `main`. Keep credentials in Vercel environment settings. The application reuses the configured production PostgreSQL database. No schema migration was required for this release. Readiness compares the installed Alembic revisions against the bundled migration heads and returns 503 if they differ.

## Verification evidence

- 71 backend tests passed against dedicated local PostgreSQL.
- Frontend regression tests passed for draft-preserving conflict recovery and bounded server pagination/filtering.
- Python lint/format checks, TypeScript checks, and the production frontend build passed.
- Frontend dependency audit: zero reported vulnerabilities.
- GitHub CI passed, including frontend/backend Docker builds.
- Live HTTP checks passed for registration/login, task creation/update, stale version rejection (409), outsider access denial (404), comments, search/pagination, and project statistics.
- The temporary HTTP verification workspace was deleted after testing.
- Browser verification passed for demo setup, the connected task board, and persisting a task edit to version 2.

## Reminder delivery boundary

The Vercel release hosts the web app and API. It does not provision Redis, an always-running Celery worker/beat scheduler, or an SMTP account. Production currently uses the console email backend. To send real reminders, deploy the existing worker and exactly one beat instance against the same database with a reachable Redis broker and configure SMTP through the worker host's secret manager. The Docker and single-VM examples remain available in `docs/deployment`.

Reminder code now checks active workspace membership, serializes delivery with workspace changes, and reactivates eligible cancelled records. Previously sent records remain deduplicated.

## Repository replacement

The former `PrathapKumarKatta/TaskFlow` repository was backed up locally and renamed to `taskflow-legacy-20261024` while the replacement was verified. GitHub rejected deletion with HTTP 403 (`Must have admin rights to Repository`), so it is archived pending deletion by an account with repository-delete permission. `DSA_DOJO` was preserved.
