# Proceeds Navigator — Technical Specification

**Version**: 1.0.0  
**Date**: 2026-04-24  
**Status**: Approved for implementation

---

## 1. Overview

Proceeds Navigator is a private, internal operations platform for Golden State Claimant Advisors. It monitors California county public records for tax-sale excess proceeds opportunities, scores and prioritizes leads, manages case workflows, and generates compliant outreach and case documents.

The system is not a legal services platform. It does not file claims, submit forms, or impersonate claimants. All legally sensitive outputs require manual human review before use.

---

## 2. Governing Law

| Statute | Subject |
|---|---|
| California Revenue & Taxation Code § 4675 | Excess proceeds claims — right, procedure, deadline |
| Cal. R&T Code § 3692 | Tax sales |
| Cal. R&T Code § 3700–3712 | Tax deed recording |
| Cal. Bus. & Prof. Code (various) | **REQUIRES HUMAN LEGAL REVIEW** — non-attorney service regulation |

The 1-year claim period under § 4675 runs from the date the tax deed is recorded. **REQUIRES HUMAN LEGAL REVIEW — confirm trigger date.**

---

## 3. System Boundaries

### In Scope
- Public-record web monitoring (county tax collector pages, agenda items, public notices)
- Lead normalization and storage
- Lead scoring and prioritization
- Case workflow management
- Compliant document template generation
- CSV export
- Internal dashboard for manual review

### Out of Scope (permanently excluded)
- Automated claim submission to any county
- Access to non-public data sources
- Representation of the operator as a government agency or attorney
- Generation of forged or falsified documents
- Automated assignment or contract execution
- Contact with claimants via automated dialing or mass email systems

---

## 4. County Sources (v1)

All source URLs are marked REQUIRES_VERIFICATION and must be confirmed before each scraper deployment.

### 4.1 Fresno County
- **Agency**: Fresno County Tax Collector
- **Source type**: Auction results list, excess proceeds notices
- **URL**: REQUIRES_VERIFICATION — see `config/counties.yaml`
- **Scrape method**: Static HTTP first, Playwright fallback
- **Claim filing location**: Fresno County Tax Collector office
- **Known forms**: REQUIRES_VERIFICATION

### 4.2 San Diego County
- **Agency**: San Diego County Treasurer-Tax Collector
- **Source type**: Excess proceeds announcements, auction results
- **URL**: REQUIRES_VERIFICATION — see `config/counties.yaml`
- **Scrape method**: Static HTTP first, Playwright fallback
- **Claim filing location**: SD County Treasurer-Tax Collector
- **Known forms**: REQUIRES_VERIFICATION

### 4.3 Sacramento County
- **Agency**: Sacramento County Tax Collector
- **Source type**: Auction results, public notices
- **URL**: REQUIRES_VERIFICATION — see `config/counties.yaml`
- **Scrape method**: Static HTTP first, Playwright fallback
- **Claim filing location**: Sacramento County Tax Collector
- **Known forms**: REQUIRES_VERIFICATION

### 4.4 Los Angeles County
- **Agency**: LA County Treasurer and Tax Collector (TTC)
- **Source type**: Excess proceeds lists, public auction announcements
- **URL**: REQUIRES_VERIFICATION — see `config/counties.yaml`
- **Scrape method**: Static HTTP first, Playwright fallback
- **Claim filing location**: LA County TTC
- **Known forms**: REQUIRES_VERIFICATION

---

## 5. Data Model

### 5.1 Lead

The core unit of the system. One row per unique identified opportunity.

```
id                      INTEGER PK
county                  TEXT NOT NULL           -- fresno | san_diego | sacramento | los_angeles
source_type             TEXT NOT NULL           -- auction_list | agenda_item | notice | press_release | web_page
source_url              TEXT
page_title              TEXT
parcel_apn              TEXT                    -- Assessor Parcel Number
situs_address           TEXT                    -- Property street address
sale_date               DATE
notice_date             DATE
board_item_id           TEXT
excess_proceeds_signal  TEXT                    -- Raw signal text from page
excess_proceeds_amount  REAL                    -- Parsed dollar amount (NULL if not visible)
likely_claimant_type    TEXT                    -- former_owner | lienholder | unknown
likely_claimant_name    TEXT
claimant_source_basis   TEXT                    -- How claimant was identified
priority_rank           INTEGER                 -- 1 (highest) to 5
score                   REAL                    -- 0.0 to 100.0
score_explanation       TEXT                    -- JSON: dimension → points + reason
legal_risk_flag         TEXT                    -- low | medium | high | REQUIRES_LEGAL_REVIEW
review_status           TEXT DEFAULT 'pending'  -- pending | reviewed | qualified | disqualified | archived
outreach_status         TEXT DEFAULT 'none'     -- none | drafted | sent | responded | engaged | closed
notes                   TEXT
last_checked_at         DATETIME
content_hash            TEXT                    -- SHA-256 of (county+apn+sale_date+source_url)
created_at              DATETIME
updated_at              DATETIME
```

### 5.2 Case

Created manually from a qualified lead.

```
id                      INTEGER PK
lead_id                 INTEGER FK → leads.id
case_number             TEXT UNIQUE             -- GS-YYYY-NNNN
client_name             TEXT
client_contact          TEXT                    -- phone or email
county                  TEXT
parcel_apn              TEXT
claim_deadline          DATE                    -- Calculated: deed_recording_date + 365 days
stage                   TEXT                    -- intake | docs_gathering | claim_prep | filed | resolved | closed
outcome                 TEXT
fee_agreement_signed    BOOLEAN DEFAULT FALSE
notes                   TEXT
created_at              DATETIME
updated_at              DATETIME
```

### 5.3 Document

```
id                      INTEGER PK
case_id                 INTEGER FK → cases.id
doc_type                TEXT                    -- outreach_intro | outreach_followup | intake_form |
                                                --   document_checklist | service_agreement |
                                                --   claim_checklist | case_summary
file_path               TEXT                    -- Relative to DATA_DIR/exports/
generated_at            DATETIME
template_version        TEXT
```

### 5.4 ScrapeRun

```
id                      INTEGER PK
county                  TEXT
started_at              DATETIME
completed_at            DATETIME
leads_found             INTEGER
leads_new               INTEGER
error_count             INTEGER
status                  TEXT                    -- success | partial | failed
snapshot_path           TEXT
```

---

## 6. Lead Scoring Specification

Scores range 0–100. Every lead receives a `score_explanation` JSON object with per-dimension breakdown.

### Dimensions

**Source Reliability (max 20)**
- Official county auction/excess-proceeds page: 20
- County agenda item: 15
- County press release: 10
- Indirect mention on county site: 5

**Proceeds Existence Likelihood (max 25)**
- Dollar amount explicitly stated: 25
- Amount range implied: 15
- "Excess proceeds" keyword present: 8
- Ambiguous signal: 3

**Claimant Traceability (max 20)**
- Named former owner found in same source: 20
- Lienholder identified with recorded instrument: 15
- Entity name partially matched: 10
- Unknown / no name: 5

**Document Complexity (max 10)**
- Simple — single owner, no known liens: 10
- Moderate — LLC/trust owner or one lien: 6
- Complex — multiple liens or competing claims: 3

**Deadline Urgency (max 15)**
- More than 6 months remaining: 5
- 3–6 months remaining: 10
- Less than 3 months remaining: 15
- Deadline unknown: 0

**Penalties**
- Legal ambiguity (competing claimants, unclear ownership): −10
- Low-confidence entity match (partial name, no APN): −5
- Missing APN: −5

### Risk Flag Logic

| Condition | Flag |
|---|---|
| Lienholder or assignee as likely claimant | REQUIRES_LEGAL_REVIEW |
| Amount > $50,000 | REQUIRES_LEGAL_REVIEW |
| Multiple competing claimant signals | REQUIRES_LEGAL_REVIEW |
| Complex lien structure, LLC/trust ownership | high |
| Incomplete address/APN, indirect signal | medium |
| Clear former owner, stated amount, within deadline | low |

### Priority Rank

Derived from score:

| Score | Rank |
|---|---|
| 80–100 | 1 |
| 60–79 | 2 |
| 40–59 | 3 |
| 20–39 | 4 |
| 0–19 | 5 |

---

## 7. Scraper Design

### 7.1 Execution Flow

```
1. Load county config from counties.yaml
2. Attempt static HTTP fetch (httpx)
3. On JS-detection → retry with Playwright
4. Save HTML snapshot to data/snapshots/<county>_<timestamp>.html
5. Parse with BeautifulSoup4 using CSS selectors from config
6. On selector failure → keyword/text fallback parser
7. Normalize raw rows to Lead schema
8. Compute content_hash
9. Upsert to database (skip if hash exists)
10. Write ScrapeRun record
```

### 7.2 Resilience Rules

- Selector config is versioned in `counties.yaml`
- Keyword fallback is always available independent of selectors
- Snapshot is always saved before parsing (even on parse failure)
- Scraper returns partial results on non-fatal errors
- All errors are logged with structlog at ERROR level
- Scraper run status: `success` (0 errors), `partial` (some errors), `failed` (0 leads extracted)

### 7.3 Rate Limiting

- Minimum 2-second delay between requests to the same county
- Respect `Retry-After` headers
- Maximum 3 retries with exponential backoff (2s, 4s, 8s)
- No concurrent requests to the same county domain

---

## 8. API Specification

### Base URL
`http://localhost:8000/api/v1`

### Endpoints

#### Leads
```
GET    /leads                   List leads (filter: county, status, risk_flag, score_min)
GET    /leads/{id}              Get lead detail with score breakdown
PATCH  /leads/{id}/status       Update review_status or outreach_status
GET    /leads/{id}/score        Rescore a lead
```

#### Cases
```
GET    /cases                   List cases
POST   /cases                   Create case from lead (requires lead review_status=qualified)
GET    /cases/{id}              Get case detail
PATCH  /cases/{id}              Update case fields
DELETE /cases/{id}              Archive case (soft delete)
```

#### Documents
```
POST   /cases/{id}/documents    Generate document for case
GET    /cases/{id}/documents    List documents for case
GET    /documents/{id}/download Download generated document
```

#### Export
```
GET    /export/leads.csv        Export leads to CSV
GET    /export/cases.csv        Export cases to CSV
```

#### Health
```
GET    /health                  Returns system status and last scrape times
```

---

## 9. Dashboard Specification

### Pages

1. **Lead List** — Filterable table of all leads. Columns: County, APN, Address, Score, Risk Flag, Review Status, Outreach Status, Sale Date. Sortable. Paginated.
2. **Lead Detail** — Full lead data, score breakdown accordion, risk flag explanation, action buttons (Qualify, Disqualify, Archive, Generate Outreach).
3. **Case List** — All cases with stage, client name, deadline, county.
4. **Case Detail** — Full case data, stage progression, document list, generate document buttons.
5. **Documents** — All generated documents with download links.

### Compliance Notice

Every page header includes: *"For internal use only. All outreach must be reviewed before sending. Clients may file directly with counties at no cost."*

---

## 10. Document Templates

All templates use Jinja2. Required compliance footer on all client-facing templates:

```
---
NOTICE: Golden State Claimant Advisors is not a government agency and does not
provide legal advice. You may be eligible to file a claim directly with
{{ county_name }} County at no cost. Engaging this firm is entirely optional.
---
```

### Template Variables (all templates)

```
operator_name, operator_address, operator_phone, operator_email
client_name, client_address
county_name, parcel_apn, situs_address
sale_date, claim_deadline
case_number, generated_date
```

### Template List

1. `outreach_intro.txt.j2` — First contact letter
2. `outreach_followup.txt.j2` — Follow-up if no response within 14 days
3. `intake_form.txt.j2` — Intake questionnaire for qualified claimant
4. `document_checklist.txt.j2` — List of documents claimant must gather
5. `service_agreement.txt.j2` — Fee arrangement draft (**REQUIRES LEGAL REVIEW before use**)
6. `claim_checklist.txt.j2` — Step-by-step claim preparation guide
7. `case_summary.txt.j2` — Internal case summary for operator records

---

## 11. Testing Requirements

### Unit Tests (run offline, no network)
- `test_normalizer.py` — Raw scraper output → Lead model
- `test_scorer.py` — Score calculation for known inputs
- `test_deduplicator.py` — Hash generation and dedup logic
- `test_document_generator.py` — Template rendering with known context

### Integration Tests (network-isolated, use snapshots)
- `test_fresno_connector.py` — Parse snapshot → leads
- `test_san_diego_connector.py`
- `test_sacramento_connector.py`
- `test_los_angeles_connector.py`

### E2E Tests
- `test_dashboard_flow.py` — API: create lead → qualify → create case → generate document

### Test Standards
- No test deletes allowed to make build pass
- Every new normalizer parser gets a corresponding snapshot test
- Scoring tests must assert exact dimension scores, not just total
- Integration tests must run against saved snapshot HTML, not live URLs

---

## 12. Compliance Architecture

### Flags in Code

Use `# LEGAL_REVIEW_REQUIRED:` comments on any code path that:
- Generates a document a client will sign
- Calculates a deadline used for outreach timing
- Determines who a "party of interest" is
- Touches assignment or representation logic

### Audit Log

Every lead status change and document generation writes a structured log entry with:
`timestamp, operator, entity_type, entity_id, action, old_value, new_value`

---

## 13. Configuration Files

### `.env` Variables

```
DATABASE_URL=sqlite:///./data/proceeds_navigator.db
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
LOG_LEVEL=info
DATA_DIR=/home/user/demo/data
SCRAPE_DELAY_SECONDS=2
MAX_RETRIES=3
OPERATOR_NAME=Golden State Claimant Advisors
OPERATOR_ADDRESS=
OPERATOR_PHONE=
OPERATOR_EMAIL=
PLAYWRIGHT_HEADLESS=true
```

### `config/counties.yaml`

Config-driven per-county rules. See file for full structure.

### `config/scoring.yaml`

Scoring weights. Editable without code changes.
