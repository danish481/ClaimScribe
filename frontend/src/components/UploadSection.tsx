import { useState, useCallback, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import Webcam from 'react-webcam'
import {
  Upload, Camera, FileText, X, CheckCircle, AlertTriangle,
  Loader2, FileSearch, Shield, Sparkles, ChevronRight
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface UploadSectionProps {
  onDocumentProcessed: () => void
}

interface UploadResult {
  document_id: string
  filename: string
  status: string
  message: string
  detected_type?: string
  confidence?: number
  extracted_text_preview?: string
  processing_time_ms?: number
  phi_detected?: boolean
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

export default function UploadSection({ onDocumentProcessed }: UploadSectionProps) {
  const [activeMode, setActiveMode] = useState<'file' | 'camera'>('file')
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<UploadResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [cameraEnabled, setCameraEnabled] = useState(false)
  const webcamRef = useRef<Webcam>(null)

  // File dropzone
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return
    await processFile(acceptedFiles[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.tif', '.tiff'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: false,
  })

  const processFile = async (file: File) => {
    setUploading(true)
    setResult(null)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${API_URL}/api/v1/documents/upload`, {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed')
      }

      setResult(data)
      onDocumentProcessed()
    } catch (err: any) {
      setError(err.message || 'An error occurred during upload')
    } finally {
      setUploading(false)
    }
  }

  const capturePhoto = async () => {
    if (!webcamRef.current) return

    const imageSrc = webcamRef.current.getScreenshot()
    if (!imageSrc) return

    // Convert base64 to blob
    const response = await fetch(imageSrc)
    const blob = await response.blob()
    const file = new File([blob], 'camera-capture.jpg', { type: 'image/jpeg' })

    await processFile(file)
  }

  const clearResult = () => {
    setResult(null)
    setError(null)
  }

  const getTypeColor = (type?: string) => {
    switch (type) {
      case 'inpatient': return 'bg-blue-50 text-blue-700 border-blue-200'
      case 'outpatient': return 'bg-emerald-50 text-emerald-700 border-emerald-200'
      case 'pharmacy': return 'bg-violet-50 text-violet-700 border-violet-200'
      default: return 'bg-slate-50 text-slate-700 border-slate-200'
    }
  }

  const getTypeIcon = (type?: string) => {
    switch (type) {
      case 'inpatient': return <FileText className="w-4 h-4" />
      case 'outpatient': return <FileSearch className="w-4 h-4" />
      case 'pharmacy': return <Shield className="w-4 h-4" />
      default: return <FileText className="w-4 h-4" />
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Mode Toggle */}
      <div className="flex justify-center mb-8">
        <div className="inline-flex bg-white rounded-2xl p-1 shadow-card border border-slate-100">
          <button
            onClick={() => { setActiveMode('file'); setCameraEnabled(false) }}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium transition-all ${
              activeMode === 'file'
                ? 'bg-primary-600 text-white shadow-soft'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Upload className="w-4 h-4" />
            Upload File
          </button>
          <button
            onClick={() => { setActiveMode('camera'); setCameraEnabled(true) }}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium transition-all ${
              activeMode === 'camera'
                ? 'bg-primary-600 text-white shadow-soft'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Camera className="w-4 h-4" />
            Camera Capture
          </button>
        </div>
      </div>

      <div className="grid lg:grid-cols-5 gap-8">
        {/* Upload Area */}
        <div className="lg:col-span-3">
          <AnimatePresence mode="wait">
            {activeMode === 'file' ? (
              <motion.div
                key="file"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
              >
                {/* Dropzone */}
                <div
                  {...getRootProps()}
                  className={`
                    relative border-2 border-dashed rounded-3xl p-12 text-center cursor-pointer
                    transition-all duration-300
                    ${isDragActive
                      ? 'border-primary-500 bg-primary-50/50'
                      : 'border-slate-200 bg-white hover:border-primary-300 hover:bg-slate-50/50'
                    }
                    ${uploading ? 'pointer-events-none opacity-60' : ''}
                  `}
                >
                  <input {...getInputProps()} />

                  <div className="flex flex-col items-center gap-4">
                    <div className={`
                      w-20 h-20 rounded-3xl flex items-center justify-center transition-all
                      ${isDragActive
                        ? 'bg-primary-100 scale-110'
                        : 'bg-slate-100'
                      }
                    `}>
                      {uploading ? (
                        <Loader2 className="w-10 h-10 text-primary-600 animate-spin" />
                      ) : (
                        <Upload className={`w-10 h-10 ${isDragActive ? 'text-primary-600' : 'text-slate-400'}`} />
                      )}
                    </div>

                    <div>
                      <p className="text-lg font-semibold text-slate-800 mb-1">
                        {isDragActive ? 'Drop your file here' : 'Drag & drop your document'}
                      </p>
                      <p className="text-sm text-slate-400">
                        or click to browse from your computer
                      </p>
                    </div>

                    <div className="flex flex-wrap justify-center gap-2 mt-2">
                      {['PDF', 'PNG', 'JPG', 'TIFF', 'DOCX', 'TXT'].map((format) => (
                        <span
                          key={format}
                          className="px-3 py-1 text-xs font-medium bg-slate-100 text-slate-500 rounded-lg"
                        >
                          {format}
                        </span>
                      ))}
                    </div>

                    <p className="text-xs text-slate-400 mt-2">
                      Maximum file size: 50MB
                    </p>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="camera"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <div className="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-soft">
                  {cameraEnabled ? (
                    <div className="relative">
                      <Webcam
                        ref={webcamRef}
                        audio={false}
                        screenshotFormat="image/jpeg"
                        className="w-full aspect-[4/3] object-cover"
                      />
                      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-3">
                        <button
                          onClick={capturePhoto}
                          disabled={uploading}
                          className="flex items-center gap-2 px-6 py-3 bg-white/90 backdrop-blur-sm text-slate-800 rounded-full font-medium shadow-lg hover:bg-white transition-colors"
                        >
                          {uploading ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                          ) : (
                            <Camera className="w-5 h-5" />
                          )}
                          Capture Document
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-20 gap-4">
                      <Camera className="w-16 h-16 text-slate-300" />
                      <p className="text-slate-500">Camera access is required</p>
                      <button
                        onClick={() => setCameraEnabled(true)}
                        className="btn-primary"
                      >
                        Enable Camera
                      </button>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="mt-4 p-4 bg-red-50 border border-red-200 rounded-2xl flex items-start gap-3"
              >
                <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-800">Processing Error</p>
                  <p className="text-sm text-red-600 mt-1">{error}</p>
                </div>
                <button onClick={clearResult} className="ml-auto">
                  <X className="w-4 h-4 text-red-400 hover:text-red-600" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-2">
          <AnimatePresence>
            {result ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="card p-6"
              >
                {/* Success Header */}
                <div className="flex items-start gap-3 mb-6">
                  <div className="w-12 h-12 bg-medical-50 rounded-2xl flex items-center justify-center flex-shrink-0">
                    <CheckCircle className="w-6 h-6 text-medical-500" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-800">Processing Complete</h3>
                    <p className="text-sm text-slate-400">{result.filename}</p>
                  </div>
                  <button onClick={clearResult} className="ml-auto">
                    <X className="w-4 h-4 text-slate-400 hover:text-slate-600" />
                  </button>
                </div>

                {/* Classification Result */}
                <div className="mb-6">
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                    Detected Type
                  </p>
                  <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl border ${getTypeColor(result.detected_type)}`}>
                    {getTypeIcon(result.detected_type)}
                    <span className="font-semibold capitalize">{result.detected_type || 'Unknown'}</span>
                  </div>
                </div>

                {/* Metrics */}
                <div className="space-y-3 mb-6">
                  <div className="flex justify-between items-center py-2 border-b border-slate-50">
                    <span className="text-sm text-slate-500">Confidence</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-primary-500 to-primary-400 rounded-full transition-all"
                          style={{ width: `${(result.confidence || 0) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-semibold text-slate-700">
                        {((result.confidence || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  <div className="flex justify-between py-2 border-b border-slate-50">
                    <span className="text-sm text-slate-500">Processing Time</span>
                    <span className="text-sm font-medium text-slate-700">
                      {result.processing_time_ms?.toFixed(0)}ms
                    </span>
                  </div>

                  <div className="flex justify-between py-2 border-b border-slate-50">
                    <span className="text-sm text-slate-500">PHI Detected</span>
                    <span className={`text-sm font-medium ${result.phi_detected ? 'text-amber-600' : 'text-medical-600'}`}>
                      {result.phi_detected ? 'Yes - Masked' : 'None'}
                    </span>
                  </div>

                  <div className="flex justify-between py-2">
                    <span className="text-sm text-slate-500">Document ID</span>
                    <span className="text-sm font-mono text-slate-600">
                      {result.document_id?.slice(0, 12)}...
                    </span>
                  </div>
                </div>

                {/* Text Preview */}
                {result.extracted_text_preview && (
                  <div className="mb-6">
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                      Extracted Preview
                    </p>
                    <div className="p-3 bg-slate-50 rounded-xl text-xs text-slate-600 font-mono leading-relaxed max-h-32 overflow-y-auto">
                      {result.extracted_text_preview}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3">
                  <button
                    onClick={() => onDocumentProcessed()}
                    className="flex-1 btn-primary text-sm py-2.5"
                  >
                    <Sparkles className="w-4 h-4 mr-2" />
                    View in Dashboard
                  </button>
                </div>
              </motion.div>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="card p-8 text-center"
              >
                <div className="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <FileSearch className="w-8 h-8 text-slate-300" />
                </div>
                <h3 className="font-semibold text-slate-700 mb-1">Ready to Process</h3>
                <p className="text-sm text-slate-400">
                  Upload a document to see AI classification results here
                </p>

                <div className="mt-6 space-y-2">
                  {[
                    { label: 'OCR Text Extraction', icon: FileText },
                    { label: 'PHI Detection & Masking', icon: Shield },
                    { label: 'ML Classification', icon: Sparkles },
                    { label: 'MLflow Tracking', icon: ChevronRight },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center gap-3 px-4 py-2.5 bg-slate-50 rounded-xl">
                      <item.icon className="w-4 h-4 text-slate-400" />
                      <span className="text-sm text-slate-500">{item.label}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
