# Deploying to Fly.io

Goal: get the plaintext front end on a public HTTPS URL with a managed
Postgres backend.

## One-time setup

1. Install the flyctl CLI: <https://fly.io/docs/hands-on/install-flyctl/>
2. Sign in: `fly auth login`
3. Pick a unique app name and edit `fly.toml` — set `app = "<your-name>"`
   and `primary_region = "<region>"` (e.g. `yyz`, `iad`, `lhr`).

## Provision Postgres with pgvector

Fly's newer **Managed Postgres** (Supabase-backed) ships with the
`vector` extension enabled and is the easiest path:

```bash
fly mpg create --name lip-db --region yyz
fly mpg attach lip-db --app lip   # writes DATABASE_URL into the app
```

`fly mpg attach` sets `DATABASE_URL`. The app reads
`LIP_DATABASE_URL`, so map it once:

```bash
fly secrets set \
  LIP_DATABASE_URL="$(fly mpg connect lip-db --print-url)" \
  --app lip
```

Alternatives:

- **Neon** — free tier, has pgvector. Create a project, copy the
  connection string, run `fly secrets set LIP_DATABASE_URL="postgres://..."`.
- **Supabase** — same. Use the "session pooler" connection string.

## First deploy

```bash
fly launch --no-deploy --copy-config        # registers the app, skips build
fly deploy                                  # builds the image, rolls a machine
```

`alembic upgrade head` runs on every container boot (see the `CMD` in
`Dockerfile`), so the schema lands automatically on first deploy.

## Verify

```bash
fly open                                   # opens https://<app>.fly.dev
curl https://<app>.fly.dev/healthz
```

You should see the plaintext front end with empty-state messages for
each section — the DB is migrated but no scrapers have run yet.

## Run a scrape (optional, while you're connected)

The web container alone doesn't run Celery. To ingest postings without
adding a worker machine, you can one-shot a scrape inside the existing
container:

```bash
fly ssh console --app lip
> python -c "from lip.scraping.tasks import run_spider; run_spider('job_bank_canada')"
```

(Long-term, add a `worker` process group in `fly.toml` running
`celery -A lip.worker.app worker` plus a beat machine for scheduling.)

## Custom domain

```bash
fly certs add labor.example.com --app lip
# Add the CNAME record Fly prints to your DNS.
```

## Operating notes

- `auto_stop_machines = true` in `fly.toml` means the app sleeps when
  idle and wakes on the first request. Cold start is ~1s.
- Free tier covers one shared-cpu-1x machine with 512MB RAM, which is
  fine for the plaintext UI. Bump `[[vm]] memory` when adding ML
  enrichment workers.
- Logs: `fly logs --app lip`.
- Roll back: `fly releases list --app lip` → `fly deploy --image <prev>`.
