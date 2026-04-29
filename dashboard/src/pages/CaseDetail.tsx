import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import ComplianceNotice from '../components/ComplianceNotice'
import { getCase, updateCase, getCaseDocuments, generateDocument } from '../api/client'
import type { DocumentRecord } from '../api/types'

const STAGES = ['intake', 'docs_gathering', 'claim_prep', 'filed', 'resolved'] as const
type Stage = typeof STAGES[number]

const DOC_TYPES = [
  { value: 'service_agreement', label: 'Service Agreement' },
  { value: 'retainer_letter', label: 'Retainer Letter' },
  { value: 'claim_form', label: 'Claim Form' },
  { value: 'cover_letter', label: 'Cover Letter' },
  { value: 'authorization_form', label: 'Authorization Form' },
  { value: 'demand_letter', label: 'Demand Letter' },
  { value: 'engagement_letter', label: 'Engagement Letter' },
]

function StageProgressBar({ current }: { current: string }) {
  const currentIndex = STAGES.indexOf(current as Stage)

  return (
    <div className="flex items-center gap-0 w-full">
      {STAGES.map((stage, i) => {
        const isCompleted = i < currentIndex
        const isCurrent = i === currentIndex
        const isLast = i === STAGES.length - 1

        return (
          <div key={stage} className="flex items-center flex-1">
            <div className="flex flex-col items-center flex-1">
              <div
                className={clsx(
                  'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2',
                  isCompleted && 'bg-indigo-600 border-indigo-600 text-white',
                  isCurrent && 'bg-white border-indigo-600 text-indigo-600',
                  !isCompleted && !isCurrent && 'bg-gray-100 border-gray-300 text-gray-400'
                )}
              >
                {isCompleted ? (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>
              <span className={clsx(
                'text-xs mt-1 text-center capitalize',
                isCurrent ? 'text-indigo-600 font-semibold' : 'text-gray-400'
              )}>
                {stage.replace(/_/g, ' ')}
              </span>
            </div>
            {!isLast && (
              <div className={clsx(
                'h-0.5 flex-shrink w-full mx-0',
                i < currentIndex ? 'bg-indigo-600' : 'bg-gray-200'
              )} />
            )}
          </div>
        )
      })}
    </div>
  )
}

function DeadlineCountdown({ deadline }: { deadline: string | null }) {
  if (!deadline) {
    return <span className="text-gray-400">No deadline set</span>
  }

  const deadlineDate = new Date(deadline)
  const daysUntil = Math.ceil((deadlineDate.getTime() - Date.now()) / 86_400_000)
  const formatted = deadlineDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })

  let countdownClass = 'text-gray-700'
  let countdownText = `${daysUntil} days remaining`

  if (daysUntil < 0) {
    countdownClass = 'text-red-700 font-bold'
    countdownText = `${Math.abs(daysUntil)} days overdue`
  } else if (daysUntil <= 60) {
    countdownClass = 'text-red-600 font-semibold'
  } else if (daysUntil <= 90) {
    countdownClass = 'text-yellow-600 font-semibold'
  }

  return (
    <div>
      <span className="text-gray-800">{formatted}</span>
      <span className={clsx('ml-2 text-sm', countdownClass)}>({countdownText})</span>
    </div>
  )
}

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const caseId = Number(id)

  const [stageDraft, setStageDraft] = useState<string | null>(null)
  const [notesDraft, setNotesDraft] = useState<string | null>(null)
  const [selectedDocType, setSelectedDocType] = useState('service_agreement')
  const [generatingDoc, setGeneratingDoc] = useState(false)
  const [docError, setDocError] = useState('')
  const [saveStageError, setSaveStageError] = useState('')
  const [saveNotesError, setSaveNotesError] = useState('')

  const { data: caseData, isLoading, isError } = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => getCase(caseId),
    enabled: !isNaN(caseId),
  })

  const { data: documents, refetch: refetchDocs } = useQuery({
    queryKey: ['case-documents', caseId],
    queryFn: () => getCaseDocuments(caseId),
    enabled: !isNaN(caseId),
  })

  const updateMutation = useMutation({
    mutationFn: (body: Parameters<typeof updateCase>[1]) => updateCase(caseId, body),
    onSuccess: (updated) => {
      queryClient.setQueryData(['case', caseId], updated)
      queryClient.invalidateQueries({ queryKey: ['cases'] })
    },
  })

  async function handleSaveStage() {
    if (!stageDraft) return
    setSaveStageError('')
    try {
      await updateMutation.mutateAsync({ stage: stageDraft })
      setStageDraft(null)
    } catch (err) {
      setSaveStageError(err instanceof Error ? err.message : 'Failed to save stage')
    }
  }

  async function handleSaveNotes() {
    setSaveNotesError('')
    try {
      await updateMutation.mutateAsync({ notes: notesDraft ?? '' })
      setNotesDraft(null)
    } catch (err) {
      setSaveNotesError(err instanceof Error ? err.message : 'Failed to save notes')
    }
  }

  async function handleFeeToggle() {
    if (!caseData) return
    await updateMutation.mutateAsync({ fee_agreement_signed: !caseData.fee_agreement_signed })
  }

  async function handleGenerateDocument() {
    setGeneratingDoc(true)
    setDocError('')
    try {
      await generateDocument(caseId, selectedDocType)
      await refetchDocs()
    } catch (err) {
      setDocError(err instanceof Error ? err.message : 'Failed to generate document')
    } finally {
      setGeneratingDoc(false)
    }
  }

  function docDownloadUrl(doc: DocumentRecord) {
    return `/api/v1/documents/${doc.id}/download`
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

  if (isError || !caseData) {
    return (
      <div className="flex flex-col min-h-full">
        <ComplianceNotice />
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4">
            Failed to load case #{caseId}.
          </div>
          <Link to="/cases" className="mt-4 inline-block text-indigo-600 hover:underline text-sm">
            ← Back to Cases
          </Link>
        </div>
      </div>
    )
  }

  const currentStage = stageDraft ?? caseData.stage
  const currentNotes = notesDraft !== null ? notesDraft : (caseData.notes ?? '')

  const docsGrouped = (documents ?? []).reduce<Record<string, DocumentRecord[]>>((acc, doc) => {
    if (!acc[doc.doc_type]) acc[doc.doc_type] = []
    acc[doc.doc_type].push(doc)
    return acc
  }, {})

  return (
    <div className="flex flex-col min-h-full">
      <ComplianceNotice />

      <div className="p-6 max-w-5xl w-full">
        {/* Back link */}
        <Link to="/cases" className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:underline mb-4">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Cases
        </Link>

        {/* Header */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold text-gray-900 font-mono">{caseData.case_number}</h1>
              <p className="text-gray-700 mt-1 text-lg">{caseData.client_name ?? 'No client name'}</p>
              <div className="flex flex-wrap gap-3 mt-2 text-sm text-gray-500">
                <span><span className="font-medium">County:</span> {caseData.county}</span>
                {caseData.parcel_apn && (
                  <span><span className="font-medium">APN:</span> <span className="font-mono">{caseData.parcel_apn}</span></span>
                )}
                {caseData.lead_id && (
                  <span>
                    <span className="font-medium">Lead:</span>{' '}
                    <Link to={`/leads/${caseData.lead_id}`} className="text-indigo-600 hover:underline">
                      #{caseData.lead_id}
                    </Link>
                  </span>
                )}
              </div>
            </div>
            <div className="text-right">
              <div className="flex items-center gap-2 justify-end">
                <label className="text-sm text-gray-600 font-medium">Fee Agreement Signed</label>
                <input
                  type="checkbox"
                  checked={caseData.fee_agreement_signed}
                  onChange={handleFeeToggle}
                  className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Stage progression */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-4">
          <h2 className="text-base font-semibold text-gray-800 mb-5">Stage Progression</h2>
          <StageProgressBar current={currentStage} />

          <div className="flex items-center gap-3 mt-6">
            <label className="text-sm font-medium text-gray-700">Update Stage:</label>
            <select
              value={currentStage}
              onChange={(e) => setStageDraft(e.target.value)}
              className="text-sm border border-gray-300 rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {STAGES.map((s) => (
                <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
              ))}
            </select>
            <button
              onClick={handleSaveStage}
              disabled={updateMutation.isPending || stageDraft === null}
              className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              Save Stage
            </button>
            {saveStageError && <p className="text-xs text-red-600">{saveStageError}</p>}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            {/* Claim deadline */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-2">Claim Deadline</h2>
              <DeadlineCountdown deadline={caseData.claim_deadline} />
            </div>

            {/* Document generation */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Documents</h2>

              {selectedDocType === 'service_agreement' && (
                <div className="mb-3 flex items-start gap-2 bg-amber-50 border border-amber-300 text-amber-800 rounded-md px-3 py-2 text-sm">
                  <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                  </svg>
                  DRAFT — Requires attorney review before sending to client.
                </div>
              )}

              <div className="flex items-center gap-3 mb-4">
                <select
                  value={selectedDocType}
                  onChange={(e) => setSelectedDocType(e.target.value)}
                  className="text-sm border border-gray-300 rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {DOC_TYPES.map((dt) => (
                    <option key={dt.value} value={dt.value}>{dt.label}</option>
                  ))}
                </select>
                <button
                  onClick={handleGenerateDocument}
                  disabled={generatingDoc}
                  className="px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                >
                  {generatingDoc ? 'Generating…' : 'Generate Document'}
                </button>
              </div>

              {docError && (
                <p className="text-sm text-red-600 mb-3">{docError}</p>
              )}

              {/* Document list */}
              {documents && documents.length > 0 ? (
                <div className="space-y-3">
                  {Object.entries(docsGrouped).map(([docType, docs]) => {
                    const docLabel = DOC_TYPES.find((d) => d.value === docType)?.label ?? docType
                    return (
                      <div key={docType}>
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-1">{docLabel}</p>
                        <div className="space-y-1">
                          {docs.sort((a, b) => new Date(b.generated_at).getTime() - new Date(a.generated_at).getTime()).map((doc) => (
                            <div key={doc.id} className="flex items-center justify-between bg-gray-50 rounded px-3 py-2 text-sm border border-gray-100">
                              <div className="text-gray-600 text-xs">
                                Generated {new Date(doc.generated_at).toLocaleString()}
                                {doc.template_version && (
                                  <span className="ml-2 text-gray-400">v{doc.template_version}</span>
                                )}
                              </div>
                              <a
                                href={docDownloadUrl(doc)}
                                download
                                className="text-indigo-600 hover:text-indigo-800 text-xs font-medium underline"
                              >
                                Download
                              </a>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="text-sm text-gray-400">No documents generated yet.</p>
              )}
            </div>

            {/* Notes */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Notes</h2>
              <textarea
                value={currentNotes}
                onChange={(e) => setNotesDraft(e.target.value)}
                rows={4}
                className="block w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                placeholder="Add case notes…"
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
            {/* Case metadata */}
            <div className="bg-white rounded-lg border border-gray-200 p-5 text-sm space-y-2">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Details</h2>
              <dl className="space-y-2">
                <div className="flex justify-between">
                  <dt className="text-gray-500">Case ID</dt>
                  <dd className="font-mono text-gray-700">{caseData.id}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Created</dt>
                  <dd className="text-gray-700">{new Date(caseData.created_at).toLocaleDateString()}</dd>
                </div>
                {caseData.client_contact && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Contact</dt>
                    <dd className="text-gray-700 text-xs">{caseData.client_contact}</dd>
                  </div>
                )}
                {caseData.outcome && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Outcome</dt>
                    <dd className="text-gray-700 capitalize">{caseData.outcome}</dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Fee agreement */}
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Fee Agreement</h2>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="fee-signed-sidebar"
                  checked={caseData.fee_agreement_signed}
                  onChange={handleFeeToggle}
                  className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                />
                <label htmlFor="fee-signed-sidebar" className="text-sm text-gray-700 cursor-pointer">
                  Fee agreement signed
                </label>
              </div>
              <p className={clsx(
                'text-xs mt-2',
                caseData.fee_agreement_signed ? 'text-green-600' : 'text-orange-600'
              )}>
                {caseData.fee_agreement_signed ? 'Agreement on file' : 'Not yet signed'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
