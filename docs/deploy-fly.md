# Deploying to Fly.io

Goal: get the plaintext front end on a public HTTPS URL with a managed
Postgres backend.

## TL;DR — getting your app live (`laborint.fly.dev`)

The traceback you'd see if you skip this: `connection refused on 127.0.0.1:5432`.
That means `LIP_DATABASE_URL` isn't set. Fix:

```bash
# 1. Get a Postgres URL with pgvector available. Two easy options:
#    a) Neon (free, has pgvector): create a project at https://console.neon.tech,
#       copy the connection string from the dashboard. It looks like:
#       postgresql://USER:PASSWORD@ep-xyz.neon.tech/neondb?sslmode=require
#    b) Fly Managed Postgres: fly mpg create --name lip-db --region yyz

# 2. Tell the app where the DB is. `postgres://` and `postgresql://` are both
#    accepted — config.py rewrites them to `postgresql+psycopg://` automatically.
fly secrets set LIP_DATABASE_URL='postgresql://USER:PASSWORD@ep-xyz.neon.tech/neondb?sslmode=require' \
  --app laborint

# 3. Redeploy so the secret is picked up.
fly deploy --app laborint

# 4. Watch it come up.
fly logs --app laborint
fly open --app laborint    # opens https://laborint.fly.dev
```

If migrations succeed you'll see `INFO uvicorn.access` lines and the
page at `https://laborint.fly.dev/` loads with empty-state messages.

## One-time setup (for new apps)

1. Install flyctl: <https://fly.io/docs/hands-on/install-flyctl/>
2. Sign in: `fly auth login`
3. Edit `fly.toml`: set `app = "<your-name>"` and `primary_region`.

## Provisioning Postgres

### Option A — Neon (recommended, fastest)

1. Sign up at <https://console.neon.tech>.
2. Create a project; default region near your Fly region.
3. Copy the connection string from "Connection Details". Use the
   pooled connection string if available.
4. `fly secrets set LIP_DATABASE_URL='<paste>' --app <app>`

pgvector is preinstalled on Neon — the `CREATE EXTENSION vector`
in our first migration will succeed.

### Option B — Fly Managed Postgres

```bash
fly mpg create --name lip-db --region yyz
fly mpg attach lip-db --app <app>
fly secrets set LIP_DATABASE_URL="$(fly mpg connect lip-db --print-url)" --app <app>
```

`fly mpg attach` also sets `DATABASE_URL`; we override with
`LIP_DATABASE_URL` since the app reads that prefix.

### Option C — Supabase

1. Create a project at <https://supabase.com>.
2. Settings → Database → Connection Pooling → "Session" mode →
   copy the connection string.
3. `fly secrets set LIP_DATABASE_URL='<paste>' --app <app>`

## First deploy

```bash
fly launch --no-deploy --copy-config     # registers the app
fly deploy                               # builds the image, rolls a machine
```

`alembic upgrade head` runs on every container boot (see `CMD` in
`Dockerfile`), so the schema lands automatically.

## Verify

```bash
fly open --app <app>                     # opens https://<app>.fly.dev
curl https://<app>.fly.dev/healthz
```

You should see the plaintext front end with empty-state messages for
each section — the DB is migrated but no scrapers have run yet.

## Run a scrape (optional)

The web container alone doesn't run Celery. To ingest postings without
adding a worker machine, one-shot a scrape inside the existing container:

```bash
fly ssh console --app <app>
> python -c "from lip.scraping.tasks import run_spider; run_spider('job_bank_canada')"
```

(Long-term, add a `worker` process group in `fly.toml` running
`celery -A lip.worker.app worker` plus a beat machine for scheduling.)

## Custom domain

```bash
fly certs add labor.example.com --app <app>
# Add the CNAME record Fly prints to your DNS.
```

## Operating notes

- `auto_stop_machines = true` in `fly.toml` means the app sleeps when
  idle and wakes on the first request. Cold start is ~1s.
- Free tier covers one shared-cpu-1x machine with 512MB RAM, which is
  fine for the plaintext UI. Bump `[[vm]] memory` when adding ML
  enrichment workers.
- Logs: `fly logs --app <app>`.
- Roll back: `fly releases list --app <app>` → `fly deploy --image <prev>`.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `connection refused on 127.0.0.1:5432` | `LIP_DATABASE_URL` not set; app fell back to local default | `fly secrets set LIP_DATABASE_URL='...'` |
| `password authentication failed` | URL has wrong credentials | Re-copy the connection string from your DB provider |
| `extension "vector" is not available` | Postgres provider doesn't ship pgvector | Use Neon / Supabase / Fly MPG — or install it as superuser |
| `Connection timed out` from a private host | Pooled vs direct host mismatch | Use the pooled / "session pooler" connection string |
