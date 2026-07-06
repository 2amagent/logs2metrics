# log-triage dashboard

Thin-client review console for the log-triage API (Phase 1 of the project).
Two views:

- **`/pending`** — new templates awaiting categorization, with sample lines,
  match counts, and a severity + mute control.
- **`/categorized`** — already-categorized templates, with the same controls
  for re-categorization.

No business logic lives here — every view is a direct read of
`GET /api/templates` and every mutation is a direct call to
`POST /api/templates/{id}/categorize` on the FastAPI service.

## Why Next.js instead of a static page

The API itself intentionally stays unaware of the dashboard. All browser
traffic goes through this app's own `/api/[...path]` route handler, which
proxies to the FastAPI service server-side. That seam is what lets this app
add auth (session cookies, SSO, whatever) later without ever touching the
Python API's surface — the API only ever needs to trust requests that already
carry whatever this app decides to attach to them.

## Running locally

```bash
cp .env.local.example .env.local   # set LOGTRIAGE_API_URL if not localhost:8000
npm install
npm run dev
```

Requires the log-triage API running (see the top-level README) — `npm run
dev` alone won't show any templates without it.

## Structure

- `src/app/api/[...path]/route.ts` — proxy to `LOGTRIAGE_API_URL`, forwards
  `/api/...` calls made from the browser to the FastAPI service's own `/api/...`
  routes.
- `src/lib/api.ts` — typed client. Server Components (`pending`/`categorized`
  pages) call the FastAPI service directly for their initial data; the
  browser-side mutation (`categorizeTemplate`) goes through the proxy so it
  stays same-origin.
- `src/components/` — `TemplateCard`, `SeverityBadge`, `CategorizeForm`
  (client component handling the categorize mutation), `Nav`.

## Deployment

Not yet wired into docker-compose or the Helm chart — run it standalone
against a reachable API for now (set `LOGTRIAGE_API_URL` accordingly).
