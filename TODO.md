# Proceeds Navigator — Implementation Checklist

Generated: 2026-04-24  
Track completion here. Do not delete items; mark [x] when done.

---

## Phase 3 — Planning Documents
- [x] CLAUDE.md
- [x] spec.md
- [x] TODO.md
- [x] .env.example (updated)

## Phase 4 — Python Package Foundation
- [x] proceeds_navigator/__init__.py
- [x] proceeds_navigator/pyproject.toml
- [x] proceeds_navigator/requirements.txt
- [x] proceeds_navigator/requirements-dev.txt
- [x] proceeds_navigator/config/counties.yaml
- [x] proceeds_navigator/config/scoring.yaml

## Phase 5 — Database Layer
- [x] proceeds_navigator/db/__init__.py
- [x] proceeds_navigator/db/models.py
- [x] proceeds_navigator/db/session.py
- [x] proceeds_navigator/db/migrations/ (Alembic setup)

## Phase 6 — Tests First (Unit)
- [x] tests/__init__.py
- [x] tests/conftest.py
- [x] tests/unit/__init__.py
- [x] tests/unit/test_normalizer.py
- [x] tests/unit/test_scorer.py
- [x] tests/unit/test_deduplicator.py
- [x] tests/unit/test_document_generator.py

## Phase 7 — ETL Layer
- [x] proceeds_navigator/etl/__init__.py
- [x] proceeds_navigator/etl/normalizer.py
- [x] proceeds_navigator/etl/deduplicator.py
- [x] proceeds_navigator/etl/enricher.py

## Phase 8 — Scoring Engine
- [x] proceeds_navigator/scoring/__init__.py
- [x] proceeds_navigator/scoring/scorer.py
- [x] proceeds_navigator/scoring/explainer.py

## Phase 9 — Scrapers
- [x] proceeds_navigator/scraper/__init__.py
- [x] proceeds_navigator/scraper/base.py
- [x] proceeds_navigator/scraper/http.py
- [x] proceeds_navigator/scraper/browser.py
- [x] proceeds_navigator/scraper/snapshot.py
- [x] proceeds_navigator/scraper/counties/__init__.py
- [x] proceeds_navigator/scraper/counties/fresno.py
- [x] proceeds_navigator/scraper/counties/san_diego.py
- [x] proceeds_navigator/scraper/counties/sacramento.py
- [x] proceeds_navigator/scraper/counties/los_angeles.py

## Phase 10 — FastAPI Backend
- [x] proceeds_navigator/api/__init__.py
- [x] proceeds_navigator/api/main.py
- [x] proceeds_navigator/api/deps.py
- [x] proceeds_navigator/api/schemas.py
- [x] proceeds_navigator/api/routers/__init__.py
- [x] proceeds_navigator/api/routers/leads.py
- [x] proceeds_navigator/api/routers/cases.py
- [x] proceeds_navigator/api/routers/documents.py
- [x] proceeds_navigator/api/routers/export.py

## Phase 11 — Documents
- [x] proceeds_navigator/documents/__init__.py
- [x] proceeds_navigator/documents/generator.py
- [x] proceeds_navigator/documents/templates/outreach_intro.txt.j2
- [x] proceeds_navigator/documents/templates/outreach_followup.txt.j2
- [x] proceeds_navigator/documents/templates/intake_form.txt.j2
- [x] proceeds_navigator/documents/templates/document_checklist.txt.j2
- [x] proceeds_navigator/documents/templates/service_agreement.txt.j2
- [x] proceeds_navigator/documents/templates/claim_checklist.txt.j2
- [x] proceeds_navigator/documents/templates/case_summary.txt.j2

## Phase 12 — CLI
- [x] proceeds_navigator/cli/__init__.py
- [x] proceeds_navigator/cli/commands.py

## Phase 13 — Dashboard
- [x] dashboard/package.json
- [x] dashboard/vite.config.ts
- [x] dashboard/tsconfig.json
- [x] dashboard/index.html
- [x] dashboard/src/main.tsx
- [x] dashboard/src/App.tsx
- [x] dashboard/src/api/client.ts
- [x] dashboard/src/api/types.ts
- [x] dashboard/src/pages/LeadList.tsx
- [x] dashboard/src/pages/LeadDetail.tsx
- [x] dashboard/src/pages/CaseList.tsx
- [x] dashboard/src/pages/CaseDetail.tsx
- [x] dashboard/src/components/LeadTable.tsx
- [x] dashboard/src/components/ScoreBadge.tsx
- [x] dashboard/src/components/RiskFlag.tsx
- [x] dashboard/src/components/StatusChip.tsx
- [x] dashboard/src/components/ComplianceNotice.tsx
- [x] dashboard/src/components/Layout.tsx

## Phase 14 — Integration Tests + Snapshots
- [x] tests/snapshots/fresno_sample.html
- [x] tests/snapshots/san_diego_sample.html
- [x] tests/integration/__init__.py
- [x] tests/integration/test_fresno_connector.py
- [x] tests/integration/test_san_diego_connector.py
- [x] tests/integration/test_sacramento_connector.py
- [x] tests/integration/test_los_angeles_connector.py
- [x] tests/e2e/test_dashboard_flow.py

## Phase 15 — Scripts + Docker
- [x] scripts/setup.sh
- [x] scripts/run_scrapers.sh
- [x] scripts/export_csv.sh
- [x] scripts/init_db.py
- [x] docker-compose.yml (updated for new services)
- [x] proceeds_navigator/Dockerfile
- [x] dashboard/Dockerfile

## Phase 16 — Verification
- [ ] All unit tests pass
- [ ] All integration tests pass (snapshot-based)
- [ ] API health endpoint returns 200
- [ ] Dashboard loads without errors
- [ ] CSV export produces valid file
- [ ] Document generation produces output for all 7 types

## Legal Review Items (Block on go-live, not development)
- [ ] LR-001 through LR-010 — see CLAUDE.md
- [ ] Service agreement template reviewed by attorney before use
- [ ] Compliance footer language approved

## Known Issues / Next Actions (update as discovered)
- County URLs are placeholder — REQUIRES manual verification before production scraping
- Playwright integration requires `playwright install chromium` on new machines
- Service agreement template is a DRAFT — must not be used without attorney review
