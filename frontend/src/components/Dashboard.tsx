import { useState, useEffect } from 'react'
import {
  FileText, Clock, Shield, Brain, Download, ChevronRight,
  AlertTriangle, CheckCircle, Loader2
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface DashboardProps {
  refreshTrigger: number
}

interface Document {
  document_id: string
  filename: string
  file_format: string
  file_size_bytes: number
  status: string
  detected_type: string
  confidence: number
  extracted_text: string
  masked_text?: string
  structured_data?: Record<string, any>
  phi_detected: boolean
  mlflow_run_id?: string
  created_at: string
  processed_at?: string
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Dashboard({ refreshTrigger }: DashboardProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/documents/`)
      const data = await response.json()
      setDocuments(data.documents || [])
    } catch (err) {
      console.error('Failed to fetch documents:', err)
      // Use demo data if backend unavailable
      setDocuments([
        {
          document_id: 'demo-1',
          filename: 'claim_hospital_stay_2024.pdf',
          file_format: 'pdf',
          file_size_bytes: 245760,
          status: 'completed',
          detected_type: 'inpatient',
          confidence: 0.94,
          extracted_text: 'HOSPITAL ADMISSION CLAIM...',
          phi_detected: true,
          mlflow_run_id: 'run_abc123',
          created_at: new Date().toISOString(),
          processed_at: new Date().toISOString(),
        },
        {
          document_id: 'demo-2',
          filename: 'pharmacy_prescription_rx.pdf',
          file_format: 'pdf',
          file_size_bytes: 102400,
          status: 'completed',
          detected_type: 'pharmacy',
          confidence: 0.97,
          extracted_text: 'PRESCRIPTION CLAIM...',
          phi_detected: false,
          mlflow_run_id: 'run_def456',
          created_at: new Date(Date.now() - 86400000).toISOString(),
          processed_at: new Date(Date.now() - 86400000).toISOString(),
        },
        {
          document_id: 'demo-3',
          filename: 'clinic_visit_receipt.pdf',
          file_format: 'pdf',
          file_size_bytes: 153600,
          status: 'completed',
          detected_type: 'outpatient',
          confidence: 0.89,
          extracted_text: 'OUTPATIENT CLINIC VISIT...',
          phi_detected: true,
          mlflow_run_id: 'run_ghi789',
          created_at: new Date(Date.now() - 172800000).toISOString(),
          processed_at: new Date(Date.now() - 172800000).toISOString(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDocuments()
  }, [refreshTrigger])

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'inpatient': return 'bg-blue-50 text-blue-700 border-blue-200'
      case 'outpatient': return 'bg-emerald-50 text-emerald-700 border-emerald-200'
      case 'pharmacy': return 'bg-violet-50 text-violet-700 border-violet-200'
      default: return 'bg-slate-50 text-slate-700 border-slate-200'
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      {/* Document List */}
      <div className="lg:col-span-2">
        <div className="card">
          <div className="p-6 border-b border-slate-100">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-800">Processed Documents</h2>
                <p className="text-sm text-slate-400 mt-1">
                  {documents.length} document{documents.length !== 1 ? 's' : ''} processed
                </p>
              </div>
              <button
                onClick={() => {/* Export all */}}
                className="btn-secondary text-sm"
              >
                <Download className="w-4 h-4 mr-2" />
                Export All
              </button>
            </div>
          </div>

          <div className="divide-y divide-slate-50">
            <AnimatePresence>
              {documents.map((doc, index) => (
                <motion.div
                  key={doc.document_id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => setSelectedDoc(doc)}
                  className={`
                    p-4 flex items-center gap-4 cursor-pointer transition-colors
                    ${selectedDoc?.document_id === doc.document_id
                      ? 'bg-primary-50/50'
                      : 'hover:bg-slate-50'
                    }
                  `}
                >
                  {/* File Icon */}
                  <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center flex-shrink-0">
                    <FileText className="w-5 h-5 text-slate-500" />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-slate-800 truncate">{doc.filename}</p>
                      {doc.phi_detected && (
                        <Shield className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-slate-400">{formatBytes(doc.file_size_bytes)}</span>
                      <span className="text-xs text-slate-300">·</span>
                      <span className="text-xs text-slate-400">{formatDate(doc.created_at)}</span>
                    </div>
                  </div>

                  {/* Type Badge */}
                  <div className={`px-3 py-1 rounded-lg border text-xs font-medium capitalize ${getTypeColor(doc.detected_type)}`}>
                    {doc.detected_type}
                  </div>

                  {/* Confidence */}
                  <div className="text-right flex-shrink-0 w-16">
                    <div className="text-sm font-semibold text-slate-700">
                      {(doc.confidence * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-slate-400">confidence</div>
                  </div>

                  <ChevronRight className="w-4 h-4 text-slate-300" />
                </motion.div>
              ))}
            </AnimatePresence>

            {documents.length === 0 && (
              <div className="p-12 text-center">
                <FileText className="w-12 h-12 text-slate-200 mx-auto mb-3" />
                <p className="text-slate-400">No documents processed yet</p>
                <p className="text-sm text-slate-300 mt-1">Upload a document to get started</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Document Detail Panel */}
      <div className="lg:col-span-1">
        <AnimatePresence mode="wait">
          {selectedDoc ? (
            <motion.div
              key={selectedDoc.document_id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="card p-6"
            >
              <h3 className="font-semibold text-slate-800 mb-4">Document Details</h3>

              <div className="space-y-4">
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Type</p>
                  <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium capitalize ${getTypeColor(selectedDoc.detected_type)}`}>
                    {selectedDoc.detected_type}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Confidence</p>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-500 rounded-full"
                        style={{ width: `${selectedDoc.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold">{(selectedDoc.confidence * 100).toFixed(1)}%</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Status</p>
                    <div className="flex items-center gap-1.5">
                      <CheckCircle className="w-4 h-4 text-medical-500" />
                      <span className="text-sm font-medium text-slate-700 capitalize">{selectedDoc.status}</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">PHI Status</p>
                    <div className="flex items-center gap-1.5">
                      {selectedDoc.phi_detected ? (
                        <>
                          <AlertTriangle className="w-4 h-4 text-amber-500" />
                          <span className="text-sm font-medium text-amber-600">Detected</span>
                        </>
                      ) : (
                        <>
                          <Shield className="w-4 h-4 text-medical-500" />
                          <span className="text-sm font-medium text-medical-600">Clean</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">File Size</p>
                  <p className="text-sm text-slate-700">{formatBytes(selectedDoc.file_size_bytes)}</p>
                </div>

                {selectedDoc.mlflow_run_id && (
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">MLflow Run</p>
                    <a
                      href={`http://localhost:5000/#/experiments/runs/${selectedDoc.mlflow_run_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary-600 hover:text-primary-700 font-mono"
                    >
                      {selectedDoc.mlflow_run_id.slice(0, 16)}...
                    </a>
                  </div>
                )}

                {selectedDoc.structured_data && (
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Inferred Data</p>
                    <div className="space-y-1.5">
                      {Object.entries(selectedDoc.structured_data)
                        .filter(([key]) => !key.startsWith('score_') && !key.startsWith('potential_'))
                        .slice(0, 6)
                        .map(([key, value]) => (
                          <div key={key} className="flex justify-between py-1.5 border-b border-slate-50 last:border-0">
                            <span className="text-xs text-slate-500 capitalize">{key.replace(/_/g, ' ')}</span>
                            <span className="text-xs font-medium text-slate-700">
                              {Array.isArray(value) ? `${value.length} items` : String(value).slice(0, 30)}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {/* Text Preview */}
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Text Preview</p>
                  <div className="p-3 bg-slate-50 rounded-xl text-xs text-slate-600 font-mono leading-relaxed max-h-40 overflow-y-auto">
                    {selectedDoc.masked_text || selectedDoc.extracted_text}
                  </div>
                </div>

                <button className="w-full btn-primary text-sm py-2.5">
                  <Brain className="w-4 h-4 mr-2" />
                  Analyze with AI
                </button>
              </div>
            </motion.div>
          ) : (
            <div className="card p-8 text-center">
              <div className="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <FileText className="w-8 h-8 text-slate-300" />
              </div>
              <p className="text-slate-500">Select a document to view details</p>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
