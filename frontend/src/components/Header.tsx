import { Shield, Activity } from 'lucide-react'

interface HeaderProps {
  activeTab: string
  onTabChange: (tab: 'upload' | 'dashboard' | 'chat' | 'analytics') => void
}

export default function Header({ activeTab: _activeTab, onTabChange: _onTabChange }: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-slate-100">
      <div className="section-container">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-9 h-9 bg-gradient-to-br from-primary-600 to-primary-700 rounded-xl shadow-soft">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-slate-900">ClaimScribe</span>
              <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-primary-50 text-primary-700 rounded-md border border-primary-100 uppercase tracking-wider">
                AI
              </span>
            </div>
          </div>

          {/* Center Stats */}
          <div className="hidden md:flex items-center gap-6">
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Activity className="w-4 h-4 text-medical-500" />
              <span>System</span>
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-medical-500 rounded-full animate-pulse" />
                <span className="text-medical-600 font-medium">Online</span>
              </span>
            </div>
            <div className="h-4 w-px bg-slate-200" />
            <span className="text-xs text-slate-400">HIPAA Compliant</span>
            <div className="h-4 w-px bg-slate-200" />
            <span className="text-xs text-slate-400">MLflow v2.12</span>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-3">
            <a
              href="http://localhost:5000"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 rounded-xl transition-colors"
            >
              MLflow
            </a>
            <a
              href="/docs"
              target="_blank"
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-xl transition-colors shadow-soft"
            >
              API Docs
            </a>
          </div>
        </div>
      </div>
    </header>
  )
}
