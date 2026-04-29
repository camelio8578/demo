import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import ComplianceNotice from '../components/ComplianceNotice'
import ScoreBadge from '../components/ScoreBadge'
import RiskFlag from '../components/RiskFlag'
import StatusChip from '../components/StatusChip'
import { getLeads } from '../api/client'

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

const REVIEW_STATUSES = ['pending', 'reviewed', 'qualified', 'disqualified', 'archived']

export default function LeadList() {
  const navigate = useNavigate()
  const [county, setCounty] = useState('')
  const [reviewStatus, setReviewStatus] = useState('')
  const [scoreMin, setScoreMin] = useState('')
  const [page, setPage] = useState(1)
  const pageSize = 25

  const filters = {
    county: county || undefined,
    review_status: reviewStatus || undefined,
    score_min: scoreMin ? Number(scoreMin) : undefined,
    page,
    page_size: pageSize,
  }

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['leads', filters],
    queryFn: () => getLeads(filters),
  })

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1

  function handleFilterChange() {
    setPage(1)
  }

  return (
    <div className="flex flex-col min-h-full">
      <ComplianceNotice />

      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900">Leads</h1>
          {data && (
            <span className="text-sm text-gray-500">{data.total.toLocaleString()} total leads</span>
          )}
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap gap-3 mb-6 p-4 bg-white rounded-lg border border-gray-200">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">County</label>
            <select
              value={county}
              onChange={(e) => { setCounty(e.target.value); handleFilterChange() }}
              className="block w-44 text-sm border border-gray-300 rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All counties</option>
              {COUNTIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Review Status</label>
            <select
              value={reviewStatus}
              onChange={(e) => { setReviewStatus(e.target.value); handleFilterChange() }}
              className="block w-40 text-sm border border-gray-300 rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All statuses</option>
              {REVIEW_STATUSES.map((s) => (
                <option key={s} value={s} className="capitalize">{s}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Min Score</label>
            <input
              type="number"
              min={0}
              max={100}
              value={scoreMin}
              onChange={(e) => { setScoreMin(e.target.value); handleFilterChange() }}
              placeholder="0–100"
              className="block w-24 text-sm border border-gray-300 rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={() => { setCounty(''); setReviewStatus(''); setScoreMin(''); setPage(1) }}
              className="text-sm text-indigo-600 hover:text-indigo-800 underline"
            >
              Clear filters
            </button>
          </div>
        </div>

        {/* Table */}
        {isLoading && (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          </div>
        )}

        {isError && (
          <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4 mb-4">
            Error loading leads: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        )}

        {data && (
          <>
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Priority</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">County</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">APN</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Address</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Score</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Risk</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Review</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Outreach</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Sale Date</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.items.length === 0 && (
                      <tr>
                        <td colSpan={10} className="px-4 py-10 text-center text-gray-400">
                          No leads found matching the current filters.
                        </td>
                      </tr>
                    )}
                    {data.items.map((lead) => (
                      <tr key={lead.id} className="hover:bg-gray-50">
                        <td className="px-3 py-3 text-gray-700 font-mono text-xs">
                          {lead.priority_rank ?? '—'}
                        </td>
                        <td className="px-3 py-3 text-gray-700">{lead.county}</td>
                        <td className="px-3 py-3 font-mono text-xs text-gray-600">
                          {lead.parcel_apn ?? '—'}
                        </td>
                        <td className="px-3 py-3 text-gray-700 max-w-xs truncate">
                          {lead.situs_address ?? '—'}
                        </td>
                        <td className="px-3 py-3">
                          <ScoreBadge score={lead.score} />
                        </td>
                        <td className="px-3 py-3">
                          <RiskFlag flag={lead.legal_risk_flag} />
                        </td>
                        <td className="px-3 py-3">
                          <StatusChip status={lead.review_status} />
                        </td>
                        <td className="px-3 py-3">
                          <StatusChip status={lead.outreach_status} />
                        </td>
                        <td className="px-3 py-3 text-gray-600 text-xs">
                          {lead.sale_date ? new Date(lead.sale_date).toLocaleDateString() : '—'}
                        </td>
                        <td className="px-3 py-3">
                          <button
                            onClick={() => navigate(`/leads/${lead.id}`)}
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

            {/* Pagination */}
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
