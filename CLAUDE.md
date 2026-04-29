# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

- **Software**: Proceeds Navigator
- **Business**: Golden State Claimant Advisors (operator: Michael Camelio)
- **Purpose**: Lawful public-record monitoring and claimant assistance for California tax-sale excess proceeds
- **Governing statute**: California Revenue & Taxation Code § 4675
- **Target counties (v1)**: Fresno, San Diego, Sacramento, Los Angeles

## Repo Layout

```
proceeds_navigator/   Python package: scraper, ETL, scoring, API, CLI, documents
tests/                unit/, integration/, e2e/
dashboard/            React/Vite frontend
scripts/              Shell scripts for setup, scraping, export
data/                 Runtime data — GITIGNORED (db, snapshots, exports)
```

Legacy Pi demo app files (`frontend/`, `backend/`, `reverse-proxy/`) are from the original repo template. Do not modify them.

## Development Commands

```bash
# First-time setup
./scripts/setup.sh

# API server (reload mode)
cd proceeds_navigator && uvicorn api.main:app --reload --port 8000

# Dashboard dev server
cd dashboard && npm run dev

# Run all tests (from repo root)
cd proceeds_navigator && pytest ../tests/ -v

# Run a single test file
pytest tests/unit/test_scorer.py -v

# Run a single test by name
pytest tests/unit/test_scorer.py::TestScorerPenalties::test_missing_apn_applies_penalty -v

# Run all scrapers via CLI
python -m proceeds_navigator.cli.commands scrape

# Run one county
python -m proceeds_navigator.cli.commands scrape --county fresno

# Database migration (after editing models.py)
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Stack

| Layer | Choice |
|---|---|
| Python | 3.11+ |
| Database | SQLite (WAL mode; Alembic migrations; upgrade path to PostgreSQL) |
| ORM | SQLAlchemy 2.0 (`mapped_column` / `Mapped` typed syntax) |
| API | FastAPI + Pydantic v2 |
| HTTP scraping | httpx + BeautifulSoup4 |
| JS scraping | Playwright (only when static fetch fails) |
| Templates | Jinja2 (`StrictUndefined` — all variables must be supplied) |
| CLI | Typer + Rich |
| Logging | structlog |
| Dashboard | React 18 + Vite + TypeScript + Tailwind CSS + TanStack Query v5 |
| Tests | pytest + FastAPI `TestClient` (httpx) |

## Architecture: Data Flow

```
County website HTML
      │
      ▼
BaseScraper.scrape() / parse()        scraper/counties/<county>.py
      │  raw lead dicts
      ▼
Normalizer.normalize()                etl/normalizer.py
      │  validates county, source_type; parses dates/amounts; infers claimant_type
      ▼
Enricher.enrich()                     etl/enricher.py
      │  adds claimant_source_basis, uppercases APN
      ▼
Deduplicator.filter_new()             etl/deduplicator.py
      │  SHA-256 of county|parcel_apn|sale_date|source_url
      ▼
LeadScorer.score()                    scoring/scorer.py
      │  returns ScoreResult(score, priority_rank, legal_risk_flag, explanation)
      ▼
Lead row in SQLite DB                 db/models.py
      │
      ▼ (operator marks review_status = "qualified")
Case created via POST /api/v1/cases   api/routers/cases.py
      │
      ▼
DocumentGenerator.save()              documents/generator.py
      │  renders Jinja2 template with DocumentContext
      ▼
.txt file in EXPORTS_DIR
```

## Architecture: Key Design Decisions

**Scraper → ETL separation**: Scrapers return raw dicts; normalization and scoring are separate pipeline steps. Never put business logic inside a scraper's `parse()`.

**Config-driven county rules**: All county URLs, CSS selectors, keyword fallbacks, and claim deadlines live in `proceeds_navigator/config/counties.yaml`. Scrapers read `load_county_config(self.county_key)` — never hardcode these.

**Deduplication via content hash**: `content_hash` (SHA-256) has a `UNIQUE` constraint in the DB. The `Deduplicator` also deduplicates within a single batch to prevent race conditions on repeated runs.

**API dependency injection for DB**: All endpoints receive `db: Session = Depends(get_db)` — including the health endpoint. This is critical: the health endpoint must not call `get_engine()` directly, or it will bypass test overrides and create a separate in-memory SQLite database.

**Test isolation**: E2E tests use `poolclass=StaticPool` and `app.dependency_overrides[get_db]` to ensure all sessions share one physical SQLite connection. If you add new endpoints that touch the DB, they must use `Depends(get_db)`.

**Human review gate**: `POST /api/v1/cases` returns 422 if `lead.review_status != "qualified"`. This is a hard compliance requirement — do not relax it.

**Document templates use `StrictUndefined`**: Every variable referenced in a `.j2` template must appear in `DocumentContext`. Missing variables raise at render time, not silently produce empty strings.

**Legal risk escalation**: `LeadScorer` automatically sets `legal_risk_flag = "REQUIRES_LEGAL_REVIEW"` for any lienholder lead or any lead with `excess_proceeds_amount >= LEGAL_REVIEW_AMOUNT_THRESHOLD` (env, default $50,000). The `service_agreement` doc type is also in `_LEGAL_REVIEW_DOCS` in the documents router.

## Scoring Weights

| Dimension | Max pts |
|---|---|
| proceeds_existence | 25 |
| source_reliability | 20 |
| claimant_traceability | 20 |
| deadline_urgency | 15 |
| document_complexity | 10 |
| penalty_missing_apn | −5 |
| penalty_unknown_entity | −5 |

Priority ranks: 1 (≥80), 2 (≥60), 3 (≥40), 4 (≥20), 5 (<20). Deadline urgency is measured as days elapsed since `sale_date` (the 1-year RTC § 4675 deadline runs from the tax deed recording date).

## Adding a New County

1. Add entry to `proceeds_navigator/config/counties.yaml`
2. Create `proceeds_navigator/scraper/counties/<county>.py` extending `BaseScraper`
3. Register in `proceeds_navigator/scraper/counties/__init__.py`
4. Add snapshot fixture in `tests/snapshots/<county>_sample.html`
5. Add integration test in `tests/integration/test_<county>_connector.py`
6. Add county to the County Config Verification Checklist below

## Database Migration Protocol

1. Edit `proceeds_navigator/db/models.py`
2. `alembic revision --autogenerate -m "description"`
3. Review the generated file in `proceeds_navigator/db/migrations/versions/`
4. `alembic upgrade head`
5. Never edit migration files that have already been applied to production

## Document Template Versions

When a template changes, bump `TEMPLATE_VERSION` in `proceeds_navigator/documents/generator.py` and record below.

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-04-24 | Initial templates |

## Inviolable Rules

1. **No automated claim filing.** Documents are generated for human review only. No form submission, e-filing, or county portal interaction.
2. **No identity spoofing.** Never represent the operator as a government agency, attorney, or the claimant.
3. **Compliance footer required.** Every client-facing document must include: *"You may be able to file a claim directly with the county at no cost. This firm is not a government agency and does not provide legal advice."*
4. **REQUIRES_LEGAL_REVIEW is blocking.** Any lead or document with this flag must not be used in outreach until a licensed California attorney has reviewed it.
5. **No private data sources.** All data must come from publicly accessible county pages or information provided directly by the client.
6. **Human review gate.** `review_status` must be manually set to `qualified` before a case can be created.
7. **Idempotent scraper runs.** Content hashing prevents duplicates. Running a scraper twice must not create duplicate rows.
8. **Tests are not deleted to make builds pass.** Update the test to match the new correct behavior and document why.

## Legal Review Items (Open — Do Not Close Without Attorney Sign-Off)

- [ ] LR-001: Fee cap for non-attorney claimant assistants under CA law
- [ ] LR-002: Business licensing requirements (professional fiduciary? LDA?)
- [ ] LR-003: Assignment of proceeds — lawfulness and county variation
- [ ] LR-004: Authorized representative documentation per county
- [ ] LR-005: RTC § 4675 deadline trigger (recording date vs. notice date)
- [ ] LR-006: Priority order among competing claimants
- [ ] LR-007: Compliance footer sufficiency under CA consumer protection law
- [ ] LR-008: Contact restriction rules for former property owners
- [ ] LR-009: Use of public assessor/recorder data for outreach
- [ ] LR-010: Local ordinance variations beyond RTC § 4675

## County Config Verification Checklist

Verify before each new scraper deployment.

- [ ] Fresno: Tax Collector auction results URL — REQUIRES VERIFICATION
- [ ] San Diego: Treasurer-Tax Collector excess proceeds URL — REQUIRES VERIFICATION
- [ ] Sacramento: Tax Collector auction results URL — REQUIRES VERIFICATION
- [ ] Los Angeles: TTC excess proceeds portal URL — REQUIRES VERIFICATION

## Secrets and Environment

See `.env.example` for all variables. Never commit `.env` or `data/`.

Minimum required:
- `DATABASE_URL` — SQLite path or PostgreSQL DSN
- `SECRET_KEY` — FastAPI session/signing key
- `DATA_DIR` — absolute path to runtime data directory
- `OPERATOR_NAME` / `OPERATOR_ADDRESS` / `OPERATOR_PHONE` / `OPERATOR_EMAIL` — appear in every generated document
