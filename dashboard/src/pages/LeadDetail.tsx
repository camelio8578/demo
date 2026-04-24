import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import ComplianceNotice from '../components/ComplianceNotice'
import ScoreBadge from '../components/ScoreBadge'
import RiskFlag from '../components/RiskFlag'
import StatusChip from '../components/StatusChip'
import { getLead, updateLeadStatus, createCase } from '../api/client'

const REVIEW_STATUSES = ['pending', 'reviewed', 'qualified', 'disqualified', 'archived']
const OUTREACH_STATUSES = ['none', 'drafted', 'sent', 'responded', 'engaged', 'closed']

interface CreateCaseModalProps {
  leadId: number
  onClose: () => void
  onSuccess: (caseId: number) => void
}

function CreateCaseModal({ leadId, onClose, onSuccess }: CreateCaseModalProps) {
  const [clientName, setClientName] = useState('')
  const [clientContact, setClientContact] = useState('')
  const [claimDeadline, setClaimDeadline] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const caseRecord = await createCase({
        lead_id: leadId,
        client_name: clientName || undefined,
        client_contact: clientContact || undefined,
        claim_deadline: claimDeadline || undefined,
      })
      onSuccess(caseRecord.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create case')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Create Case</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Client Name</label>
            <input
              type="text"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              className="block w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Optional"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Client Contact</label>
            <input
              type="text"
              value={clientContact}
              onChange={(e) => setClientContact(e.target.value)}
              className="block w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Email or phone (optional)"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Claim Deadline</label>
            <input
              type="date"
              value={claimDeadline}
              onChange={(e) => setClaimDeadline(e.target.value)}
              className="block w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          {error && (
            <p className="text-sm text-red-600">{error}</p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              {submitting ? 'Creating…' : 'Create Case'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function LeadDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const leadId = Number(id)

  const [scoreAccordionOpen, setScoreAccordionOpen] = useState(false)
  const [notesValue, setNotesValue] = useState<string | null>(null)
  const [showCreateCase, setShowCreateCase] = useState(false)
  const [saveNotesError, setSaveNotesError] = useState('')
  const [statusSaving, setStatusSaving] = useState(false)

  const { data: lead, isLoading, isError } = useQuery({
    queryKey: ['lead', leadId],
    queryFn: () => getLead(leadId),
    enabled: !isNaN(leadId),
  })

  const updateMutation = useMutation({
    mutationFn: (body: { review_status?: string; outreach_status?: string; notes?: string }) =>
      updateLeadStatus(leadId, body),
    onSuccess: (updated) => {
      queryClient.setQueryData(['lead', leadId], updated)
      queryClient.invalidateQueries({ queryKey: ['leads'] })
    },
  })

  const currentNotes = notesValue !== null ? notesValue : (lead?.notes ?? '')

  async function handleStatusChange(field: 'review_status' | 'outreach_status', value: string) {
    setStatusSaving(true)
    try {
      await updateMutation.mutateAsync({ [field]: value })
    } finally {
      setStatusSaving(false)
    }
  }

  async function handleSaveNotes() {
    setSaveNotesError('')
    try {
      await updateMutation.mutateAsync({ notes: currentNotes })
      setNotesValue(null)
    } catch (err) {
      setSaveNotesError(err instanceof Error ? err.message : 'Failed to save notes')
    }
  }

  async function handleQualify() {
    await updateMutation.mutateAsync({ review_status: 'qualified' })
  }

  async function handleDisqualify() {
    await updateMutation.mutateAsync({ review_status: 'disqualified' })
  }

  if (isLoading) {
    return (
      <div className="flex flex-col min-h-full">
        <ComplianceNotice />
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      </div>
    )
  }

  if (isError || !lead) {
    return (
      <div className="flex flex-col min-h-full">
        <ComplianceNotice />
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4">
            Failed to load lead #{leadId}.
          </div>
          <Link to="/leads" className="mt-4 inline-block text-indigo-600 hover:underline text-sm">
            ← Back to Leads
          </Link>
        </div>
      </div>
    )
  }

  const canQualify = lead.review_status === 'pending' || lead.review_status === 'reviewed'
  const canCreateCase = lead.review_status === 'qualified'
  const scoreEntries = lead.score_explanation ? Object.entries(lead.score_explanation) : []

  return (
    <div className="flex flex-col min-h-full">
      <ComplianceNotice />

      <div className="p-6 max-w-5xl w-full">
        {/* Back link */}
        <Link to="/leads" className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:underline mb-4">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Leads
        </Link>

        {/* Header */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold text-gray-900 font-mono">{lead.parcel_apn ?? 'No APN'}</h1>
              <p className="text-gray-600 mt-1">{lead.situs_address ?? 'No address on record'}</p>
              <div className="flex flex-wrap gap-3 mt-2 text-sm text-gray-500">
                <span><span className="font-medium">County:</span> {lead.county}</span>
                {lead.sale_date && (
                  <span><span className="font-medium">Sale Date:</span> {new Date(lead.sale_date).toLocaleDateString()}</span>
                )}
                {lead.excess_proceeds_amount != null && (
                  <span>
                    <span className="font-medium">Excess Proceeds:</span>{' '}
                    {lead.excess_proceeds_amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                  </span>
                )}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {canQualify && (
                <button
                  onClick={handleQualify}
                  disabled={updateMutation.isPending}
                  className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:opacity-50"
                >
                  Qualify Lead
                </button>
              )}
              <button
                onClick={handleDisqualify}
                disabled={updateMutation.isPending || lead.review_status === 'disqualified'}
                className="px-4 py-2 bg-red-600 text-white text-sm rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                Disqualify
              </button>
              {canCreateCase && (
                <button
                  onClick={() => setShowCreateCase(true)}
                  className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700"
                >
                  Create Case
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left column */}
          <div className="lg:col-span-2 space-y-4">
            {/* Score section */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Score</h2>
              <div className="flex items-center gap-3 mb-3">
                <ScoreBadge score={lead.score} />
                <span className="text-sm text-gray-500">
                  {lead.priority_rank != null ? `Priority rank #${lead.priority_rank}` : ''}
                </span>
              </div>

              {scoreEntries.length > 0 && (
                <div>
                  <button
                    onClick={() => setScoreAccordionOpen((o) => !o)}
                    className="flex items-center gap-1 text-sm text-indigo-600 hover:underline"
                  >
                    <svg
                      className={`w-4 h-4 transition-transform ${scoreAccordionOpen ? 'rotate-90' : ''}`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    {scoreAccordionOpen ? 'Hide' : 'Show'} score breakdown
                  </button>

                  {scoreAccordionOpen && (
                    <div className="mt-3 border border-gray-100 rounded-md overflow-hidden">
                      <table className="min-w-full text-sm">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Dimension</th>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Points</th>
                            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Reason</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {scoreEntries.map(([dim, { points, reason }]) => (
                            <tr key={dim}>
                              <td className="px-3 py-2 font-medium text-gray-700 capitalize">{dim.replace(/_/g, ' ')}</td>
                              <td className="px-3 py-2 text-gray-600 font-mono">{points >= 0 ? `+${points}` : points}</td>
                              <td className="px-3 py-2 text-gray-600">{reason}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Claimant info */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Claimant Information</h2>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <dt className="text-gray-500 font-medium">Type</dt>
                <dd className="text-gray-800 capitalize">{lead.likely_claimant_type}</dd>
                <dt className="text-gray-500 font-medium">Name</dt>
                <dd className="text-gray-800">{lead.likely_claimant_name ?? '—'}</dd>
                {lead.claimant_source_basis && (
                  <>
                    <dt className="text-gray-500 font-medium">Basis</dt>
                    <dd className="text-gray-800">{lead.claimant_source_basis}</dd>
                  </>
                )}
              </dl>
            </div>

            {/* Source info */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Source</h2>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <dt className="text-gray-500 font-medium">Type</dt>
                <dd className="text-gray-800 capitalize">{lead.source_type.replace(/_/g, ' ')}</dd>
                {lead.page_title && (
                  <>
                    <dt className="text-gray-500 font-medium">Page Title</dt>
                    <dd className="text-gray-800">{lead.page_title}</dd>
                  </>
                )}
                {lead.notice_date && (
                  <>
                    <dt className="text-gray-500 font-medium">Notice Date</dt>
                    <dd className="text-gray-800">{new Date(lead.notice_date).toLocaleDateString()}</dd>
                  </>
                )}
                {lead.board_item_id && (
                  <>
                    <dt className="text-gray-500 font-medium">Board Item</dt>
                    <dd className="text-gray-800 font-mono text-xs">{lead.board_item_id}</dd>
                  </>
                )}
                {lead.excess_proceeds_signal && (
                  <>
                    <dt className="text-gray-500 font-medium">Signal Text</dt>
                    <dd className="text-gray-800 italic text-xs col-span-1">{lead.excess_proceeds_signal}</dd>
                  </>
                )}
                {lead.source_url && (
                  <>
                    <dt className="text-gray-500 font-medium">URL</dt>
                    <dd>
                      <a
                        href={lead.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-indigo-600 hover:underline text-xs break-all"
                      >
                        {lead.source_url}
                      </a>
                    </dd>
                  </>
                )}
              </dl>
            </div>

            {/* Notes */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Notes</h2>
              <textarea
                value={currentNotes}
                onChange={(e) => setNotesValue(e.target.value)}
                rows={4}
                className="block w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                placeholder="Add internal notes…"
              />
              {saveNotesError && (
                <p className="text-xs text-red-600 mt-1">{saveNotesError}</p>
              )}
              <div className="flex justify-end mt-2">
                <button
                  onClick={handleSaveNotes}
                  disabled={updateMutation.isPending}
                  className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                >
                  Save Notes
                </button>
              </div>
            </div>
          </div>

          {/* Right column */}
          <div className="space-y-4">
            {/* Risk flag */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Legal Risk</h2>
              <RiskFlag flag={lead.legal_risk_flag} />
            </div>

            {/* Status controls */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Status</h2>
              {statusSaving && (
                <p className="text-xs text-gray-500 mb-2">Saving…</p>
              )}
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Review Status</label>
                  <div className="flex items-center gap-2">
                    <StatusChip status={lead.review_status} />
                    <select
                      value={lead.review_status}
                      onChange={(e) => handleStatusChange('review_status', e.target.value)}
                      className="flex-1 text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      {REVIEW_STATUSES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Outreach Status</label>
                  <div className="flex items-center gap-2">
                    <StatusChip status={lead.outreach_status} />
                    <select
                      value={lead.outreach_status}
                      onChange={(e) => handleStatusChange('outreach_status', e.target.value)}
                      className="flex-1 text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      {OUTREACH_STATUSES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            </div>

            {/* Metadata */}
            <div className="bg-white rounded-lg border border-gray-200 p-5 text-xs text-gray-500 space-y-1">
              <p><span className="font-medium">Lead ID:</span> {lead.id}</p>
              <p><span className="font-medium">Created:</span> {new Date(lead.created_at).toLocaleDateString()}</p>
              {lead.last_checked_at && (
                <p><span className="font-medium">Last Checked:</span> {new Date(lead.last_checked_at).toLocaleDateString()}</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {showCreateCase && (
        <CreateCaseModal
          leadId={leadId}
          onClose={() => setShowCreateCase(false)}
          onSuccess={(caseId) => {
            setShowCreateCase(false)
            navigate(`/cases/${caseId}`)
          }}
        />
      )}
    </div>
  )
}
