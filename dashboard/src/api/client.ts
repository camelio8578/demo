import axios from 'axios'
import type {
  LeadListResponse,
  LeadDetail,
  CaseListResponse,
  CaseDetail,
  DocumentRecord,
  HealthResponse,
} from './types'

const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

const http = axios.create({ baseURL })

export interface LeadListParams {
  county?: string
  review_status?: string
  page?: number
  page_size?: number
  score_min?: number
}

export interface CaseListParams {
  county?: string
  stage?: string
  page?: number
}

export async function getLeads(params: LeadListParams = {}): Promise<LeadListResponse> {
  const { data } = await http.get<LeadListResponse>('/leads', { params })
  return data
}

export async function getLead(id: number): Promise<LeadDetail> {
  const { data } = await http.get<LeadDetail>(`/leads/${id}`)
  return data
}

export async function updateLeadStatus(
  id: number,
  body: { review_status?: string; outreach_status?: string; notes?: string }
): Promise<LeadDetail> {
  const { data } = await http.patch<LeadDetail>(`/leads/${id}`, body)
  return data
}

export async function rescoreLead(id: number): Promise<LeadDetail> {
  const { data } = await http.post<LeadDetail>(`/leads/${id}/rescore`)
  return data
}

export async function getCases(params: CaseListParams = {}): Promise<CaseListResponse> {
  const { data } = await http.get<CaseListResponse>('/cases', { params })
  return data
}

export async function getCase(id: number): Promise<CaseDetail> {
  const { data } = await http.get<CaseDetail>(`/cases/${id}`)
  return data
}

export async function createCase(body: {
  lead_id: number
  client_name?: string
  client_contact?: string
  claim_deadline?: string
}): Promise<CaseDetail> {
  const { data } = await http.post<CaseDetail>('/cases', body)
  return data
}

export async function updateCase(
  id: number,
  body: Partial<{
    stage: string
    client_name: string
    notes: string
    fee_agreement_signed: boolean
  }>
): Promise<CaseDetail> {
  const { data } = await http.patch<CaseDetail>(`/cases/${id}`, body)
  return data
}

export async function getCaseDocuments(caseId: number): Promise<DocumentRecord[]> {
  const { data } = await http.get<DocumentRecord[]>(`/cases/${caseId}/documents`)
  return data
}

export async function generateDocument(caseId: number, doc_type: string): Promise<DocumentRecord> {
  const { data } = await http.post<DocumentRecord>(`/cases/${caseId}/documents`, { doc_type })
  return data
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await http.get<HealthResponse>('/health')
  return data
}
