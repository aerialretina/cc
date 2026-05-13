# Deploying without a terminal

End state: every push to this branch automatically deploys to
`https://laborint.fly.dev`. You wire it up once via two web UIs
(GitHub + Fly), then never touch the CLI again.

## One-time setup

### 1. Get a Fly API token

Use a **deploy token** scoped to the app — it works in SSO-locked orgs
where personal access tokens are disabled.

1. Open <https://fly.io/apps/laborint/tokens>.
2. Click **Create Deploy Token**, name it `github-actions`, save it.
   You'll see the token once — copy it somewhere safe for the next step.

If that page errors out (older UI) or your org disables app-scoped
tokens, use the org tokens page instead:

- Open <https://fly.io/dashboard> → click the org → **Tokens** in the
  sidebar → **Create Token** → save it.

If you see a banner saying *"Access Tokens cannot be created for your
account because an organization you are a member of requires Single
Sign On (SSO)"*, that refers specifically to **personal** tokens —
deploy tokens and org tokens are still available via the two URLs
above.

### 2. Put the token into GitHub

1. Open <https://github.com/aerialretina/cc/settings/secrets/actions>.
2. Click **New repository secret**.
   - Name: `FLY_API_TOKEN`
   - Secret: paste the Fly token from step 1.
3. Save.

### 3. Set the database URL on the Fly app

1. Open <https://fly.io/apps/laborint/secrets>.
2. Click **Add secret**.
   - Key: `LIP_DATABASE_URL`
   - Value: your full Neon connection string, e.g.
     `postgresql://neondb_owner:...@ep-...neon.tech/neondb?sslmode=require`
3. Save. Fly will roll the existing machines automatically — but
   those machines may not have the latest code yet, so do step 4
   next anyway.

## Trigger the deploy

You have two ways to kick off a deploy, neither needs a terminal:

- **Manual button:** open
  <https://github.com/aerialretina/cc/actions/workflows/fly-deploy.yml>
  and click **Run workflow** on the branch
  `claude/labor-intelligence-platform-Mt7F5`.
- **Automatic:** any push to that branch or to `main` triggers
  `.github/workflows/fly-deploy.yml`.

## Watch it happen

1. **Build + deploy:** the workflow's "Deploy" job streams flyctl
   output in the GitHub Actions UI. You'll see the image build,
   then the machine roll.
2. **App boot:** open <https://fly.io/apps/laborint/monitoring>.
   The first lines should be `alembic.runtime.migration` running the
   schema, then `Uvicorn running on http://0.0.0.0:8080`.
3. **Verify:** load <https://laborint.fly.dev/>. You should see the
   plaintext UI with empty-state messages on every section.

## Running a scrape from the UI

Once the app is up you need an admin token to authenticate ingestion runs.
This is a separate secret from the Fly deploy token.

### 1. Pick an admin token

Any long random string works. From a browser address bar, open
<https://www.uuidgenerator.net/> and copy a v4 UUID, or just type a
26+ character string of letters and digits. Call this value `TOK`
in the steps below.

### 2. Set the token on the Fly app

1. Open <https://fly.io/apps/laborint/secrets>.
2. Add secret: key `LIP_ADMIN_TOKEN`, value `TOK`.
3. Save. Fly will auto-roll the machines.

### 3. Mirror the token into GitHub

1. Open <https://github.com/aerialretina/cc/settings/secrets/actions>.
2. Add repo secret: name `LIP_ADMIN_TOKEN`, value `TOK` (same string).

### 4. Run a scrape

Open
<https://github.com/aerialretina/cc/actions/workflows/scrape.yml> →
**Run workflow** → pick branch `claude/labor-intelligence-platform-Mt7F5` →
leave `spider = job_bank_canada`, `max_postings = 100` →
**Run workflow**.

The job POSTs `https://laborint.fly.dev/admin/scrape/job_bank_canada`
with the admin token and prints the JSON response. Healthy looks like:

```json
{
  "spider": "job_bank_canada",
  "seen": 100,
  "ingested_raw": 100,
  "enriched": 100,
  "took_seconds": 47.3,
  "canonical_postings_total": 100,
  "raw_postings_total": 100
}
```

Now reload <https://laborint.fly.dev/ui/postings> — the table will be
populated. <https://laborint.fly.dev/ui/organizations> will show the
employers that resolved.

### Notes

- The scrape runs synchronously inside the web container — no
  Celery worker required. Cap `max_postings` so the run stays
  under Fly's HTTP timeout (~60–120 s by default).
- Each click is additive: re-running upserts new postings and
  refreshes `last_seen_at` on ones already in the DB.
- S3 archiving is silently skipped on Fly (no `LIP_S3_ENDPOINT`).
  Postings still land in Postgres; raw HTML snapshots are not
  retained until you wire up an object store.

## Rotating the Neon password

You pasted the live Neon password earlier — rotate it once the app is up:

1. Neon Console → your project → **Roles** → reset password on
   `neondb_owner`.
2. Copy the new connection string.
3. Repeat step 3 of the one-time setup (Fly dashboard → Secrets →
   edit `LIP_DATABASE_URL` with the new URL).
4. Fly auto-rolls the machines; no manual redeploy needed.

## Common errors (from the GitHub Actions log)

| Error in the log | Fix |
|---|---|
| `Error: FLY_API_TOKEN secret not set` | Step 2 above wasn't done, or the secret name was wrong (must be `FLY_API_TOKEN`). |
| `Error: app "laborint" not found` | The Fly app name differs. Edit `.github/workflows/fly-deploy.yml` and change `--app laborint`. |
| `connection refused on 127.0.0.1:5432` (in Fly logs, not Actions) | `LIP_DATABASE_URL` wasn't set on the Fly app. Step 3 above. |
| `HTTP 503` from `/admin/scrape` | `LIP_ADMIN_TOKEN` not set on the Fly app. Re-do step 2 of "Running a scrape from the UI". |
| `HTTP 401` from `/admin/scrape` | `LIP_ADMIN_TOKEN` on the Fly app and on GitHub Actions don't match. They must be identical. |
| `HTTP 500` with `connection refused` | The `LIP_DATABASE_URL` secret is missing or malformed. Inspect the latest Fly logs for the `[boot] db ...` diagnostic line. |
