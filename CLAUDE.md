# Proceeds Navigator — CLAUDE.md

Durable project rules and memory for Claude Code sessions. Always read this file at the start of any session.

## Project Identity

- **Software**: Proceeds Navigator
- **Business**: Golden State Claimant Advisors (operator: Michael Camelio)
- **Purpose**: Lawful public-record monitoring and claimant assistance for California tax-sale excess proceeds
- **Governing statute**: California Revenue & Taxation Code § 4675
- **Target counties (v1)**: Fresno, San Diego, Sacramento, Los Angeles

## Repo Layout

```
proceeds_navigator/   Python package: scraper, ETL, scoring, API, CLI, documents
tests/                All tests (unit, integration, e2e)
dashboard/            React/Vite frontend
scripts/              Shell scripts for setup, scraping, export
data/                 Runtime data — GITIGNORED (db, snapshots, exports)
```

Legacy Pi demo app files (`frontend/`, `backend/`, `reverse-proxy/`) are from the original repo template. Do not modify them; they are not part of this project.

## Stack

| Layer | Choice |
|---|---|
| Python | 3.11+ |
| Database | SQLite (Alembic migrations; upgrade path to PostgreSQL) |
| ORM | SQLAlchemy 2.0 (mapped_column / Mapped types) |
| API | FastAPI + Pydantic v2 |
| HTTP scraping | httpx + BeautifulSoup4 |
| JS scraping | Playwright (only when static fails) |
| Templates | Jinja2 |
| CLI | Typer + Rich |
| Logging | structlog |
| Dashboard | React 18 + Vite + TypeScript + Tailwind CSS |
| Data fetching | TanStack Query v5 |
| Tests | pytest + pytest-asyncio + httpx (test client) |

## Inviolable Rules

1. **No automated claim filing.** The system generates documents for human review only. No form submission, e-filing, or county portal interaction.
2. **No identity spoofing.** Never represent the operator as a government agency, attorney, or the claimant themselves.
3. **Compliance footer required.** Every client-facing document must include: *"You may be able to file a claim directly with the county at no cost. This firm is not a government agency and does not provide legal advice."*
4. **REQUIRES_LEGAL_REVIEW flag is blocking.** Any lead or document marked `REQUIRES_LEGAL_REVIEW` must not be used in outreach until a licensed California attorney has reviewed it.
5. **No private data sources.** All data must come from publicly accessible county web pages, official notices, or information provided directly by the client.
6. **Human review gates.** The `review_status` field must be manually updated to `qualified` before any case can be created.
7. **Idempotent scraper runs.** Content hashing prevents duplicate leads. Running a scraper twice must not create duplicate rows.
8. **County rules are config-driven.** All county-specific URLs, selectors, deadlines, and form references live in `proceeds_navigator/config/counties.yaml`. Never hardcode them in scraper logic.
9. **No fake data as real.** Test fixtures are clearly labeled. Snapshot HTML files in `tests/snapshots/` are either real archived pages or clearly marked synthetic.
10. **Tests are not deleted to make builds pass.** If a test fails due to an implementation change, update the test to match the new correct behavior and document why.

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

Run before each new scraper deployment. Mark date verified.

- [ ] Fresno: Tax Collector auction results URL — REQUIRES VERIFICATION
- [ ] San Diego: Treasurer-Tax Collector excess proceeds URL — REQUIRES VERIFICATION
- [ ] Sacramento: Tax Collector auction results URL — REQUIRES VERIFICATION
- [ ] Los Angeles: TTC excess proceeds portal URL — REQUIRES VERIFICATION

## Lead Scoring Weights (matches config/scoring.yaml)

| Dimension | Max |
|---|---|
| source_reliability | 20 |
| proceeds_existence | 25 |
| claimant_traceability | 20 |
| document_complexity | 10 |
| deadline_urgency | 15 |
| penalty_legal_ambiguity | −10 |
| penalty_low_confidence_entity | −5 |
| penalty_missing_apn | −5 |

## Database Migration Protocol

1. Edit `proceeds_navigator/db/models.py`
2. Run `alembic revision --autogenerate -m "description"`
3. Review generated migration in `proceeds_navigator/db/migrations/versions/`
4. Run `alembic upgrade head`
5. Never edit migration files that have been applied to production

## Development Commands

```bash
# Setup
./scripts/setup.sh

# Run all scrapers
./scripts/run_scrapers.sh

# Export CSV
./scripts/export_csv.sh

# Start API
cd proceeds_navigator && uvicorn api.main:app --reload --port 8000

# Start dashboard
cd dashboard && npm run dev

# Run tests
cd proceeds_navigator && pytest ../tests/ -v

# Run single test module
pytest tests/unit/test_scorer.py -v
```

## Adding a New County

1. Add county entry to `proceeds_navigator/config/counties.yaml`
2. Create `proceeds_navigator/scraper/counties/<county>.py` extending `BaseScraper`
3. Register in `proceeds_navigator/scraper/counties/__init__.py`
4. Add snapshot fixture in `tests/snapshots/<county>_sample.html`
5. Add integration test in `tests/integration/test_<county>_connector.py`
6. Verify URL and selectors manually before first production run
7. Add county to `CLAUDE.md` County Config Verification Checklist

## Document Template Versions

Templates are versioned. When a template changes, bump `TEMPLATE_VERSION` in `proceeds_navigator/documents/generator.py` and record the change reason here.

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-04-24 | Initial templates |

## Secrets and Environment

See `.env.example` for all required variables. Never commit `.env` or `data/`.

Required at minimum:
- `DATABASE_URL` — SQLite path or PostgreSQL DSN
- `SECRET_KEY` — FastAPI session/signing key
- `LOG_LEVEL` — debug / info / warning
- `DATA_DIR` — absolute path to runtime data directory
