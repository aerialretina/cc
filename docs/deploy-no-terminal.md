# Deploying without a terminal

End state: every push to this branch automatically deploys to
`https://laborint.fly.dev`. You wire it up once via two web UIs
(GitHub + Fly), then never touch the CLI again.

## One-time setup

### 1. Get a Fly API token

1. Open <https://fly.io/user/personal_access_tokens>.
2. Click **Create access token**, name it `github-actions`, save it.
   You'll see the token once — copy it somewhere safe for the next step.

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
