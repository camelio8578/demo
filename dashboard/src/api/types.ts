export interface LeadSummary {
  id: number
  county: string
  source_type: string
  parcel_apn: string | null
  situs_address: string | null
  sale_date: string | null
  excess_proceeds_amount: number | null
  likely_claimant_type: string
  likely_claimant_name: string | null
  score: number | null
  priority_rank: number | null
  legal_risk_flag: string
  review_status: string
  outreach_status: string
  created_at: string
}

export interface LeadDetail extends LeadSummary {
  source_url: string | null
  page_title: string | null
  notice_date: string | null
  board_item_id: string | null
  excess_proceeds_signal: string | null
  claimant_source_basis: string | null
  score_explanation: Record<string, { points: number; reason: string }> | null
  notes: string | null
  last_checked_at: string | null
  content_hash: string | null
}

export interface LeadListResponse {
  total: number
  page: number
  page_size: number
  items: LeadSummary[]
}

export interface CaseSummary {
  id: number
  case_number: string
  lead_id: number | null
  client_name: string | null
  county: string
  parcel_apn: string | null
  claim_deadline: string | null
  stage: string
  fee_agreement_signed: boolean
  created_at: string
}

export interface CaseDetail extends CaseSummary {
  client_contact: string | null
  outcome: string | null
  notes: string | null
}

export interface CaseListResponse {
  total: number
  page: number
  page_size: number
  items: CaseSummary[]
}

export interface DocumentRecord {
  id: number
  case_id: number
  doc_type: string
  file_path: string | null
  generated_at: string
  template_version: string | null
}

export interface HealthResponse {
  status: string
  version: string
  lead_count: number
  case_count: number
  last_scrape_runs: Array<{
    county: string
    started_at: string
    status: string
    leads_found: number
    leads_new: number
  }>
}
