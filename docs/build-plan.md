# Industrial Labor Intelligence Platform — Build Plan

This is the source-of-truth product plan. The repo scaffolding implements
Phase 0 and an early-Phase 1 cut. The text below is preserved verbatim
from the strategy document and should be updated as the product evolves.

---

## Strategic Context & What We're Actually Building

Lightcast's moat is breadth: 18B+ data points, 220K scrape sources, quarterly government integrations, 25 years of ML-refined taxonomies. Their weakness is that their data is **inferred and lagged** — job postings are demand signals, not outcomes. They have no ground-truth compensation, no closed-loop hiring data, no project-level telemetry, and their industrial/construction vertical is one of dozens they serve generically.

This platform's edge is **transaction-layer specificity** in a vertical Lightcast treats as noise. Every architectural decision should serve that goal.

---

## Phase 0 — Foundation Architecture (Weeks 1–6)

### 0.1 Core Data Model

Design the labor graph schema first. Everything else is downstream of this.

**Entity types:**

- `Person` — canonical identity (not a profile dump)
- `Organization` — employer, with NAICS/NOC/sector tags
- `Role` — a specific position, tied to person + org + time range
- `Project` — infrastructure/construction project (ENR, owner, contractor, location, type, value)
- `HiringEvent` — a closed placement or confirmed hire (the gold asset)
- `Posting` — a scraped job advertisement (raw demand signal)
- `CompensationRecord` — salary/rate with source confidence score
- `RecruiterInteraction` — internal CRM data from the search business

**Relationships:**

- Person → Role (at Org, on Project)
- Role → Skills (extracted, not self-reported)
- HiringEvent → Person + Role + CompensationRecord
- Posting → Organization + Occupation + Skills + Location + Source

**Key design rule:** Separate raw scraped data from enriched canonical records. Raw data gets ingested and queued. Enrichment (dedup, normalization, entity resolution) is a pipeline stage, not an application concern.

### 0.2 Tech Stack Decisions

| Layer | Choice | Rationale |
|---|---|---|
| Scraping orchestration | Python + Playwright/Scrapy + Celery | Headless JS rendering for dynamic sites; Celery for distributed job queues |
| Raw storage | S3-compatible object store | Cheap, immutable raw HTML/JSON archival |
| Processing queue | Redis + Celery or Kafka | Job dispatch and dedup pipeline |
| Primary DB | PostgreSQL (pgvector extension) | Relational for structured entities; vector for embedding-based dedup and skill matching |
| Graph layer | Neo4j or Apache AGE on Postgres | Mobility and career path queries are graph-native |
| Search/analytics | Elasticsearch or OpenSearch | Full-text job title / skill search, faceted filtering |
| API | FastAPI (Python) | Async, typed, fast to iterate |
| Frontend | Next.js + TypeScript | SSR for analytics dashboards |
| ML/Enrichment | Python + HuggingFace Transformers | NER, classification, embedding |
| Infrastructure | AWS (or GCP) + Terraform | IaC from day one; avoid config drift |

---

(Phases 1–6 omitted here for brevity — see project-tracking doc; mirror in
this file when the plan changes.)
