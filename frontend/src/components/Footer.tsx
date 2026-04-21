import { Shield, ExternalLink, Heart } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

export default function Footer() {
  return (
    <footer className="border-t border-slate-100 bg-white">
      <div className="section-container py-12">
        <div className="grid md:grid-cols-3 gap-8">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 bg-gradient-to-br from-primary-600 to-primary-700 rounded-lg flex items-center justify-center">
                <Shield className="w-4 h-4 text-white" />
              </div>
              <span className="text-lg font-bold text-slate-800">ClaimScribe AI</span>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed">
              Healthcare Document Intelligence Platform for automated
              claims processing with HIPAA compliance and MLflow tracking.
            </p>
          </div>

          {/* Links */}
          <div>
            <h4 className="font-semibold text-slate-700 mb-4">Platform</h4>
            <ul className="space-y-2">
              {[
                { label: 'API Documentation', href: '/docs' },
                { label: 'Health Status', href: `${API_URL}/api/v1/health/status` },
                { label: 'Metrics', href: `${API_URL}/api/v1/monitoring/metrics` },
              ].map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-slate-400 hover:text-primary-600 transition-colors inline-flex items-center gap-1"
                  >
                    {link.label}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Tech Stack */}
          <div>
            <h4 className="font-semibold text-slate-700 mb-4">Technology</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-primary-400 rounded-full" />
                FastAPI + Python 3.11
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                React 18 + TypeScript
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-violet-400 rounded-full" />
                MLflow 2.12 + scikit-learn
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-amber-400 rounded-full" />
                Tesseract OCR + Gemini Flash
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full" />
                Docker + GitHub Actions CI/CD
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-10 pt-6 border-t border-slate-100 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-400">
            ClaimScribe AI - Healthcare Document Intelligence Platform
          </p>
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <span>Built with</span>
            <Heart className="w-3 h-3 text-red-400 fill-red-400" />
            <span>for production-grade healthcare AI</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
