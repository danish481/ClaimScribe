import { useState, useEffect, useCallback } from 'react'
import {
  Play, RefreshCw, Inbox, CheckCircle, AlertTriangle,
  Loader2, Package, Clock, ChevronRight, Database, UserCheck,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

interface PipelineStatus {
  inbox_pending: number
  outbox_counts: Record<string, number>
  manifest: {
    total_processed_ever: number
    by_category: Record<string, number>
  }
  last_run: PipelineRun | null
  schedule_interval_minutes: number
  storage_backend: string
}

interface PipelineRun {
  run_id: string
  triggered_by: string
  started_at: string
  completed_at?: string
  files_found: number
  files_processed: number
  files_skipped: number
  files_failed: number
  counts_by_category: Record<string, number>
  errors: string[]
  status?: string
}

interface OutboxFile {
  filename: string
  claim_number: string
  source_file: string
  confidence: number
  phi_detected: boolean
  processed_at: string
  review_reason?: string
  classifier_scores?: Record<string, number>
}

const CATEGORY_STYLE: Record<string, string> = {
  inpatient:  'bg-blue-50 text-blue-700 border-blue-200',
  outpatient: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  pharmacy:   'bg-violet-50 text-violet-700 border-violet-200',
  unknown:    'bg-slate-50 text-slate-500 border-slate-200',
  review:     'bg-red-50 text-red-700 border-red-200',
}

const CATEGORY_BG: Record<string, string> = {
  inpatient:  'bg-blue-500',
  outpatient: 'bg-emerald-500',
  pharmacy:   'bg-violet-500',
  unknown:    'bg-slate-400',
  review:     'bg-red-500',
}

const CATEGORY_ROW_BG: Record<string, string> = {
  inpatient:  'hover:bg-blue-50/60',
  outpatient: 'hover:bg-emerald-50/60',
  pharmacy:   'hover:bg-violet-50/60',
  unknown:    'hover:bg-slate-50',
  review:     'bg-red-50/40 hover:bg-red-50/80 border-l-4 border-l-red-400',
}

export default function PipelinePanel() {
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [runs, setRuns] = useState<PipelineRun[]>([])
  const [outbox, setOutbox] = useState<Record<string, OutboxFile[]>>({})
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [reviewFiles, setReviewFiles] = useState<OutboxFile[]>([])
  const [assigning, setAssigning] = useState<string | null>(null)
  const [triggering, setTriggering] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const [statusRes, runsRes, reviewRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/pipeline/status`),
        fetch(`${API_URL}/api/v1/pipeline/runs?limit=10`),
        fetch(`${API_URL}/api/v1/pipeline/review`),
      ])
      const statusData = await statusRes.json()
      const runsData = await runsRes.json()
      const reviewData = await reviewRes.json()
      setStatus(statusData)
      setRuns(runsData.runs || [])
      setReviewFiles(reviewData.files || [])
      setError(null)
    } catch {
      setError('Cannot reach backend. Is the server running?')
    } finally {
      setLoading(false)
    }
  }, [])

  const assignFile = async (filename: string, targetCategory: string) => {
    setAssigning(filename)
    try {
      await fetch(`${API_URL}/api/v1/pipeline/review/${encodeURIComponent(filename)}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_category: targetCategory, assigned_by: 'reviewer' }),
      })
      await fetchStatus()
    } finally {
      setAssigning(null)
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 15000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  const loadOutbox = async (category: string) => {
    if (activeCategory === category) {
      setActiveCategory(null)
      return
    }
    setActiveCategory(category)
    if (!outbox[category]) {
      try {
        const res = await fetch(`${API_URL}/api/v1/pipeline/outbox/${category}`)
        const data = await res.json()
        setOutbox(prev => ({ ...prev, [category]: data.files || [] }))
      } catch {
        setOutbox(prev => ({ ...prev, [category]: [] }))
      }
    }
  }

  const triggerRun = async () => {
    setTriggering(true)
    try {
      await fetch(`${API_URL}/api/v1/pipeline/trigger`, { method: 'POST' })
      setTimeout(fetchStatus, 3000)
    } finally {
      setTriggering(false)
    }
  }

  const fmtDate = (s: string) =>
    new Date(s).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto mb-3" />
        <p className="text-slate-500">{error}</p>
      </div>
    )
  }

  const categories = ['review', 'inpatient', 'outpatient', 'pharmacy', 'unknown']
  const totalOutbox = Object.values(status?.outbox_counts ?? {}).reduce((a, b) => a + b, 0)

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">Ingestion Pipeline</h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Auto-runs every {status?.schedule_interval_minutes ?? 30} min ·
            Storage: <span className="font-medium">{status?.storage_backend ?? 'local'}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchStatus} className="btn-secondary text-sm px-3 py-2">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={triggerRun}
            disabled={triggering}
            className="btn-primary text-sm"
          >
            {triggering ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Play className="w-4 h-4 mr-2" />
            )}
            Run Now
          </button>
        </div>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: 'Inbox Pending',
            value: status?.inbox_pending ?? 0,
            icon: Inbox,
            color: status?.inbox_pending ? 'text-amber-600' : 'text-slate-400',
            bg: status?.inbox_pending ? 'bg-amber-50' : 'bg-slate-50',
          },
          {
            label: 'Total in Outbox',
            value: totalOutbox,
            icon: Package,
            color: 'text-primary-600',
            bg: 'bg-primary-50',
          },
          {
            label: 'All-Time Processed',
            value: status?.manifest.total_processed_ever ?? 0,
            icon: Database,
            color: 'text-medical-600',
            bg: 'bg-medical-50',
          },
          {
            label: 'Schedule (min)',
            value: status?.schedule_interval_minutes ?? 30,
            icon: Clock,
            color: 'text-slate-600',
            bg: 'bg-slate-50',
          },
        ].map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="card p-4 flex items-center gap-3">
            <div className={`w-10 h-10 ${bg} rounded-xl flex items-center justify-center flex-shrink-0`}>
              <Icon className={`w-5 h-5 ${color}`} />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800">{value}</p>
              <p className="text-xs text-slate-400">{label}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">

        {/* Outbox Buckets */}
        <div className="card">
          <div className="p-5 border-b border-slate-100">
            <h3 className="font-semibold text-slate-800">Outbox Buckets</h3>
            <p className="text-xs text-slate-400 mt-0.5">Click a category to inspect files</p>
          </div>
          <div className="divide-y divide-slate-100">
            {categories.map(cat => {
              const count = status?.outbox_counts?.[cat] ?? 0
              const isOpen = activeCategory === cat
              return (
                <div key={cat}>
                  <button
                    onClick={() => loadOutbox(cat)}
                    className={`w-full flex items-center gap-3 p-4 transition-colors text-left ${CATEGORY_ROW_BG[cat] ?? 'hover:bg-slate-50'}`}
                  >
                    <div className={`w-2.5 h-2.5 rounded-full ${CATEGORY_BG[cat] ?? 'bg-slate-400'}`} />
                    <div className="flex-1">
                      <span className="font-medium text-slate-700 capitalize">{cat}</span>
                      {cat === 'unknown' && (
                        <span className="ml-2 text-xs text-slate-400">(no keywords matched — routes to Review)</span>
                      )}
                      {cat === 'review' && (
                        <span className="ml-2 text-xs text-amber-500">awaiting human assignment</span>
                      )}
                    </div>
                    <span className={`px-2.5 py-0.5 rounded-lg border text-xs font-medium ${CATEGORY_STYLE[cat] ?? ''}`}>
                      {count} files
                    </span>
                    <ChevronRight className={`w-4 h-4 text-slate-300 transition-transform ${isOpen ? 'rotate-90' : ''}`} />
                  </button>

                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="px-4 pb-4 space-y-2 max-h-64 overflow-y-auto">
                          {(outbox[cat] ?? []).length === 0 ? (
                            <p className="text-xs text-slate-400 py-2">No files yet</p>
                          ) : (
                            (outbox[cat] ?? []).map(f => (
                              <div key={f.filename} className="p-3 bg-slate-50 rounded-xl text-xs">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="font-mono font-semibold text-slate-700">{f.claim_number}</span>
                                  {f.phi_detected && (
                                    <span className="text-amber-500 flex items-center gap-1">
                                      <AlertTriangle className="w-3 h-3" /> PHI masked
                                    </span>
                                  )}
                                </div>
                                <div className="flex gap-3 text-slate-400">
                                  <span>{f.source_file}</span>
                                  <span>·</span>
                                  <span>{((f.confidence ?? 0) * 100).toFixed(0)}% confidence</span>
                                  <span>·</span>
                                  <span>{fmtDate(f.processed_at)}</span>
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            })}
          </div>
        </div>

        {/* Run History */}
        <div className="card">
          <div className="p-5 border-b border-slate-100">
            <h3 className="font-semibold text-slate-800">Run History</h3>
            <p className="text-xs text-slate-400 mt-0.5">Last 10 pipeline executions</p>
          </div>
          <div className="divide-y divide-slate-50 max-h-[420px] overflow-y-auto">
            {runs.length === 0 ? (
              <div className="p-8 text-center">
                <Clock className="w-8 h-8 text-slate-200 mx-auto mb-2" />
                <p className="text-sm text-slate-400">No runs yet — click Run Now</p>
              </div>
            ) : (
              runs.map(run => (
                <div key={run.run_id} className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {run.files_failed === 0 ? (
                        <CheckCircle className="w-4 h-4 text-medical-500 flex-shrink-0" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                      )}
                      <span className="text-sm font-medium text-slate-700 font-mono">{run.run_id}</span>
                      <span className="text-xs text-slate-400 capitalize">{run.triggered_by}</span>
                    </div>
                    <span className="text-xs text-slate-400">{fmtDate(run.started_at)}</span>
                  </div>
                  <div className="flex gap-4 text-xs text-slate-500 ml-6">
                    <span className="text-medical-600 font-medium">{run.files_processed} processed</span>
                    {run.files_skipped > 0 && <span>{run.files_skipped} skipped</span>}
                    {run.files_failed > 0 && (
                      <span className="text-red-500">{run.files_failed} failed</span>
                    )}
                    {Object.entries(run.counts_by_category).map(([cat, n]) => (
                      <span key={cat} className="capitalize">{cat}: {n}</span>
                    ))}
                  </div>
                  {run.errors.length > 0 && (
                    <div className="mt-2 ml-6 text-xs text-red-400 space-y-0.5">
                      {run.errors.slice(0, 2).map((e, i) => <div key={i}>{e}</div>)}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Review Queue — always visible */}
      <div className="card border-amber-200 border-2">
        <div className="p-5 border-b border-amber-100 bg-amber-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <UserCheck className="w-5 h-5 text-amber-600" />
            <div>
              <h3 className="font-semibold text-amber-800">Review Queue</h3>
              <p className="text-xs text-amber-600 mt-0.5">
                {reviewFiles.length === 0
                  ? 'No documents pending — all claims classified with high confidence'
                  : `${reviewFiles.length} document${reviewFiles.length !== 1 ? 's' : ''} need human assignment — ambiguous or low-confidence classification`}
              </p>
            </div>
          </div>
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
            reviewFiles.length > 0
              ? 'bg-amber-100 text-amber-700 border-amber-300'
              : 'bg-slate-100 text-slate-400 border-slate-200'
          }`}>
            {reviewFiles.length} pending
          </span>
        </div>

        {reviewFiles.length === 0 ? (
          <div className="p-8 text-center">
            <CheckCircle className="w-8 h-8 text-medical-400 mx-auto mb-2" />
            <p className="text-sm text-slate-500">All documents routed successfully</p>
            <p className="text-xs text-slate-400 mt-1">
              Documents land here when confidence &lt; 60% or two categories score close together
            </p>
          </div>
        ) : (
          <div className="divide-y divide-amber-50">
            {reviewFiles.map(f => (
              <div key={f.filename} className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                      <span className="font-mono text-sm font-semibold text-slate-700">{f.claim_number}</span>
                    </div>
                    <p className="text-xs text-slate-500 mb-1">{f.source_file}</p>
                    {f.review_reason && (
                      <p className="text-xs text-amber-600 mb-2">{f.review_reason}</p>
                    )}
                    {f.classifier_scores && (
                      <div className="flex gap-3 mb-3">
                        {Object.entries(f.classifier_scores)
                          .sort(([, a], [, b]) => b - a)
                          .map(([cat, score]) => (
                            <div key={cat} className="text-xs">
                              <span className="text-slate-400 capitalize">{cat}: </span>
                              <span className="font-semibold text-slate-600">{((score as number) * 100).toFixed(0)}%</span>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 mt-2">
                  <span className="text-xs text-slate-400 self-center mr-1">Assign to:</span>
                  {['inpatient', 'outpatient', 'pharmacy'].map(cat => (
                    <button
                      key={cat}
                      onClick={() => assignFile(f.filename, cat)}
                      disabled={assigning === f.filename}
                      className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors capitalize
                        ${CATEGORY_STYLE[cat]} hover:opacity-80 disabled:opacity-50`}
                    >
                      {assigning === f.filename ? <Loader2 className="w-3 h-3 animate-spin inline" /> : cat}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* How it works */}
      <div className="card p-5">
        <h3 className="font-semibold text-slate-700 mb-3 text-sm">How the Pipeline Works</h3>
        <div className="grid sm:grid-cols-4 gap-3">
          {[
            { step: '1', label: 'Drop files', desc: 'Place any PDF/image/TXT in data/inbox/' },
            { step: '2', label: 'Scan & dedup', desc: 'SHA-256 hash prevents reprocessing' },
            { step: '3', label: 'Classify & redact', desc: 'OCR → classify → PHI masked' },
            { step: '4', label: 'Route to bucket', desc: 'JSON output → outbox/{category}/' },
          ].map(({ step, label, desc }) => (
            <div key={step} className="flex gap-3">
              <div className="w-6 h-6 bg-primary-100 text-primary-700 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                {step}
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700">{label}</p>
                <p className="text-xs text-slate-400 mt-0.5">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
