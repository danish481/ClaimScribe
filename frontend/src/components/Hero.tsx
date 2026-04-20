import { FileSearch, Brain, Lock, TrendingUp } from 'lucide-react'
import { motion } from 'framer-motion'

const features = [
  {
    icon: FileSearch,
    label: 'Document Ingestion',
    desc: 'PDF, OCR, Images',
  },
  {
    icon: Brain,
    label: 'AI Classification',
    desc: 'Inpatient · Outpatient · Pharmacy',
  },
  {
    icon: Lock,
    label: 'HIPAA Security',
    desc: 'Encryption & PHI Masking',
  },
  {
    icon: TrendingUp,
    label: 'MLflow Tracking',
    desc: 'Model Versioning & Metrics',
  },
]

export default function Hero() {
  return (
    <section className="relative overflow-hidden gradient-hero border-b border-slate-100">
      {/* Decorative Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary-100/50 rounded-full blur-3xl" />
        <div className="absolute -bottom-20 -left-20 w-60 h-60 bg-medical-100/40 rounded-full blur-3xl" />
      </div>

      <div className="relative section-container py-16 md:py-24">
        <div className="text-center max-w-4xl mx-auto">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white/80 backdrop-blur-sm rounded-full border border-slate-200 shadow-sm mb-8"
          >
            <span className="w-2 h-2 bg-medical-500 rounded-full animate-pulse" />
            <span className="text-sm font-medium text-slate-600">
              Healthcare Document Intelligence Platform
            </span>
          </motion.div>

          {/* Title */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-4xl md:text-6xl font-extrabold tracking-tight mb-6"
          >
            <span className="text-slate-900">Automated Claims</span>
            <br />
            <span className="gradient-text">Processing & Intelligence</span>
          </motion.h1>

          {/* Description */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-lg md:text-xl text-slate-500 max-w-2xl mx-auto mb-10 leading-relaxed"
          >
            ClaimScribe AI ingests, classifies, and analyzes health insurance
            claim documents with enterprise-grade security and MLflow-tracked
            model versioning.
          </motion.p>

          {/* Feature Pills */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-wrap justify-center gap-4"
          >
            {features.map((feature, index) => (
              <motion.div
                key={feature.label}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4, delay: 0.4 + index * 0.1 }}
                className="flex items-center gap-3 px-5 py-3 bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-100 shadow-soft hover:shadow-elevated transition-shadow"
              >
                <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-br from-primary-50 to-primary-100 rounded-xl">
                  <feature.icon className="w-5 h-5 text-primary-600" />
                </div>
                <div className="text-left">
                  <div className="text-sm font-semibold text-slate-800">{feature.label}</div>
                  <div className="text-xs text-slate-400">{feature.desc}</div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  )
}
