# Labor Intelligence Platform (LIP)

Industrial labor intelligence for construction, energy, and industrial sectors. The product turns scraped postings, government statistics, and closed-loop CRM placements into a queryable labor graph with placement-verified compensation, project-level demand signals, and mobility intelligence.

This repo is the Phase 0 / early Phase 1 scaffold described in `docs/build-plan.md`.

## What's in here

- **`src/lip/models/`** — SQLAlchemy ORM for the labor graph (Person, Organization, Role, Project, HiringEvent, Posting, CompensationRecord, RecruiterInteraction) — §0.1.
- **`migrations/`** — Alembic migration creating the initial schema.
- **`src/lip/api/`** — FastAPI app exposing the v1 endpoints from §5.1. Endpoints are wired to the DB; queries return real rows once data is ingested.
- **`src/lip/scraping/`** — Scraper orchestration (Celery + Playwright), a base `Spider` class, and a working Job Bank Canada spider (public API, NOC-tagged — the best legal/structural fit for a first source).
- **`src/lip/enrichment/`** — Three-stage dedup pipeline (source hash → cross-source normalized key over 60-day rolling window → semantic similarity), plus occupation/skill/comp/org/location enrichment module skeletons with explicit interfaces.
- **`src/lip/taxonomy/`** — NOC 2021 and SOC 2018 backbones, plus the industrial overlay taxonomy (construction, energy, industrial, skilled trades) from §2.1.
- **`src/lip/government/`** — Skeleton ETL connectors for BLS (QCEW, OEWS, JOLTS) and StatCan (LFS, SEPH) per §3.
- **`src/lip/crm/`** — Event log schema for the recruiter-generated proprietary data layer (§4.1).
- **`docker-compose.yml`** — Postgres (pgvector), Redis, MinIO (S3-compatible), Elasticsearch for local dev.
- **`.github/workflows/ci.yml`** — Lint, type-check, test.

## What's intentionally not built yet

- Frontend (Next.js dashboard) — comes after pipeline produces high-confidence enriched records (per "What Not to Build (Yet)").
- The full 300+ source spider fleet — start with Job Bank Canada, then expand to Tier 1 company career pages.
- Trained ML models for occupation classification and skills NER — interfaces are in place; first models are trained once 2,000 labeled examples exist.
- Neo4j / graph layer — Postgres + Apache AGE will be added once mobility queries justify it.
- Terraform — local dev runs against docker-compose; cloud IaC lands once a target account exists.

## Quick start

```bash
cp .env.example .env
docker compose up -d postgres redis minio
pip install -e ".[dev]"
alembic upgrade head
uvicorn lip.api.main:app --reload
```

Run the worker in another shell:

```bash
celery -A lip.worker.app worker --loglevel=info
celery -A lip.worker.app beat --loglevel=info  # scheduled scrapes
```

## Architecture summary

```
        ┌────────────────┐
        │ Scrape sources │   (Tier 1 career pages, Tier 2 niche boards,
        └────────┬───────┘    Tier 3 general, government APIs)
                 │
                 ▼
        ┌────────────────┐
        │  Spider pool   │   Celery workers, Playwright for JS sites,
        │ (rate-limited) │   residential proxies where required.
        └────────┬───────┘
                 ▼
       ┌──────────────────┐
       │ Raw archive (S3) │   Immutable HTML/JSON snapshots.
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │ Extraction queue │   Field parser → raw Posting rows.
       └────────┬─────────┘
                ▼
       ┌──────────────────┐    ┌─────────────────────┐
       │ Dedup pipeline   │───▶│ Canonical Postings  │
       │ (3 stages)       │    └──────────┬──────────┘
       └──────────────────┘               │
                                          ▼
                              ┌────────────────────────┐
                              │ Enrichment pipeline    │
                              │ • Occupation (NOC/SOC) │
                              │ • Industrial overlay   │
                              │ • Skills NER           │
                              │ • Comp extract/estimate│
                              │ • Org resolution       │
                              │ • Location geocode     │
                              └──────────┬─────────────┘
                                         ▼
       ┌──────────────────┐    ┌────────────────────────┐
       │  Gov data ETL    │───▶│   Labor graph (Postgres │
       │  BLS / StatCan   │    │   + pgvector + Apache   │
       └──────────────────┘    │   AGE for mobility)     │
                               └──────────┬──────────────┘
       ┌──────────────────┐               │
       │ CRM events       │───────────────┘
       │ (closed-loop)    │
       └──────────────────┘
                                         ▼
                              ┌────────────────────────┐
                              │  FastAPI (v1)          │
                              │  /postings /compensation│
                              │  /labor-supply /mobility│
                              │  /organizations /projects│
                              └────────────────────────┘
```

See `docs/build-plan.md` for the full plan.
