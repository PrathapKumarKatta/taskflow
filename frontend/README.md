# TaskFlow frontend

React + TypeScript + Vite frontend for the FastAPI backend in the parent directory. TanStack Query manages API state, cache invalidation, and background refresh; Lucide supplies icons and DM Sans is bundled locally.

## Run the whole application

From the repository root:

```powershell
uv run python scripts/init_env.py
docker compose up --build -d
```

Open [TaskFlow](http://127.0.0.1:3000). Create an account or select **Explore a live demo**. The demo creates a unique user, workspace, two projects and nine real tasks in PostgreSQL. It does not use static mock data. Demo data remains in the development database; each demo visit gets a separate account. Demo passwords are random and are not displayed, so create a regular account if you want to sign back in later.

## Develop locally

Keep the API running at `http://127.0.0.1:8000`, then from `frontend`:

```powershell
npm ci --no-audit --no-fund
npm run dev
```

Open the printed address, normally `http://127.0.0.1:5173`. Vite proxies `/api` and `/health` to FastAPI. The production nginx container uses the same paths and serves the SPA on port 3000. Both configurations use same-origin requests, so a browser CORS override is unnecessary. Do not put JWT secrets or database credentials into the frontend.

```powershell
npm run build
```

Build runs TypeScript with strict and unused-symbol checks, then writes production assets to `dist/`. The lockfile pins the installed dependency tree. GitHub Actions builds both this app and its Docker image.

## User flows

- Register, sign in, sign out, and update your full name. An expired session returns to sign-in with a message. Tokens live in sessionStorage, clear on logout, and are not persisted across browser sessions. This is a client-rendered app using the existing bearer-token API; an HTTP-only cookie session would require a backend auth change.
- Create and switch workspaces, then create and switch projects. The selected workspace/project survives page refresh within the same tab, separately for each user.
- See workspace totals and overdue work in Overview. My tasks shows your assignments in the current project, as indicated in the page subtitle.
- Browse tasks in a four-column board on desktop, two columns on narrow screens, or a paginated table. Search literal title/description text, filter by priority/status/your assignments, and sort by date or priority.
- Create tasks with a description, status, priority, assignee and timezone-aware due date. Datetime input uses your local timezone and sends an ISO timestamp to the API.
- Drag editable tasks between columns on desktop. Keyboard and touch users can open a task to change status, use the table status selector, or use its complete/reopen button.
- Open a task to edit, comment, or inspect activity. Updates send the original expected version. A conflict preserves changed draft fields. **Load latest version** rebases those fields onto the latest server state; saving sends only changed fields with the latest expected version.
- Owners and admins can add registered users by user ID. Owners can grant/revoke admin; admins can only manage ordinary members. Profile settings can copy your user ID. Names for other members are shown as abbreviated IDs because the API intentionally returns membership IDs rather than other users' profiles.
- Task and workspace deletion require confirmation in the interface. Only the owner can delete the workspace, with its exact name as confirmation. The API independently enforces all permissions.

Task filtering, sorting, and pagination run on the server. The board requests up to 40 tasks per page; the list requests 10. Both views expose page controls. Separate project statistics keep totals accurate across pages. Search requests are debounced by 250 ms. There is no claim of real-time synchronization: successful changes invalidate related queries, focus refreshes stale data, and version checks prevent overwriting concurrent edits.

The local frontend proxy causes login requests to share the proxy's IP for the backend limiter. This is adequate for local use. For deployment, configure the API to trust only the known proxy and forward client addresses there, then use HTTPS and a same-origin reverse proxy. The API docs link uses the configured API origin. The repository-root Vercel configuration deploys the frontend and API together under one origin.

## Verification

The production TypeScript/Vite build is checked, and the live browser flow is exercised against FastAPI/PostgreSQL: demo setup, task creation, versioned task update, comment persistence, and stale-write conflict handling. The backend's separate integration suite covers authorization and database rules.

Run `npm test` for frontend regression tests and `npm audit --audit-level=high` for dependency checks. CI runs these before building.
