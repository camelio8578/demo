import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import ComplianceNotice from '../components/ComplianceNotice'
import StatusChip from '../components/StatusChip'
import { getCases } from '../api/client'

const COUNTIES = [
  'Los Angeles',
  'San Diego',
  'Orange',
  'Riverside',
  'San Bernardino',
  'Sacramento',
  'Alameda',
  'Contra Costa',
  'Fresno',
  'Kern',
]

const STAGES = ['intake', 'docs_gathering', 'claim_prep', 'filed', 'resolved']

function deadlineCellClass(deadline: string | null): string {
  if (!deadline) return ''
  const daysUntil = Math.ceil((new Date(deadline).getTime() - Date.now()) / 86_400_000)
  if (daysUntil <= 60) return 'text-red-700 font-semibold'
  if (daysUntil <= 90) return 'text-yellow-700 font-semibold'
  return 'text-gray-700'
}

export default function CaseList() {
  const navigate = useNavigate()
  const [county, setCounty] = useState('')
  const [stage, setStage] = useState('')
  const [page, setPage] = useState(1)
  const pageSize = 25

  const params = {
    county: county || undefined,
    stage: stage || undefined,
    page,
  }

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['cases', params],
    queryFn: () => getCases(params),
  })

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1

  return (
    <div className="flex flex-col min-h-full">
      <ComplianceNotice />

      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900">Cases</h1>
          {data && (
            <span className="text-sm text-gray-500">{data.total.toLocaleString()} total cases</span>
          )}
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap gap-3 mb-6 p-4 bg-white rounded-lg border border-gray-200">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">County</label>
            <select
              value={county}
              onChange={(e) => { setCounty(e.target.value); setPage(1) }}
              className="block w-44 text-sm border border-gray-300 rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All counties</option>
              {COUNTIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Stage</label>
            <select
              value={stage}
              onChange={(e) => { setStage(e.target.value); setPage(1) }}
              className="block w-40 text-sm border border-gray-300 rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All stages</option>
              {STAGES.map((s) => (
                <option key={s} value={s} className="capitalize">{s.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => { setCounty(''); setStage(''); setPage(1) }}
              className="text-sm text-indigo-600 hover:text-indigo-800 underline"
            >
              Clear filters
            </button>
          </div>
        </div>

        {isLoading && (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          </div>
        )}

        {isError && (
          <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4 mb-4">
            Error loading cases: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        )}

        {data && (
          <>
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Case #</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Client</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">County</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">APN</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Deadline</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Stage</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Fee Signed</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.items.length === 0 && (
                      <tr>
                        <td colSpan={8} className="px-4 py-10 text-center text-gray-400">
                          No cases found matching the current filters.
                        </td>
                      </tr>
                    )}
                    {data.items.map((c) => (
                      <tr key={c.id} className="hover:bg-gray-50">
                        <td className="px-3 py-3 font-mono text-xs text-gray-700">{c.case_number}</td>
                        <td className="px-3 py-3 text-gray-700">{c.client_name ?? '—'}</td>
                        <td className="px-3 py-3 text-gray-700">{c.county}</td>
                        <td className="px-3 py-3 font-mono text-xs text-gray-600">{c.parcel_apn ?? '—'}</td>
                        <td className={clsx('px-3 py-3 text-xs', deadlineCellClass(c.claim_deadline))}>
                          {c.claim_deadline ? new Date(c.claim_deadline).toLocaleDateString() : '—'}
                        </td>
                        <td className="px-3 py-3">
                          <StatusChip status={c.stage} />
                        </td>
                        <td className="px-3 py-3 text-center">
                          {c.fee_agreement_signed ? (
                            <span className="text-green-600 font-bold">✓</span>
                          ) : (
                            <span className="text-gray-300">—</span>
                          )}
                        </td>
                        <td className="px-3 py-3">
                          <button
                            onClick={() => navigate(`/cases/${c.id}`)}
                            className="text-indigo-600 hover:text-indigo-800 font-medium text-xs underline"
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-gray-600">
                  Page {page} of {totalPages}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-md disabled:opacity-40 hover:bg-gray-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-md disabled:opacity-40 hover:bg-gray-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
