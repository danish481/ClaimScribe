import { useState } from 'react'
import Header from './components/Header'
import Hero from './components/Hero'
import UploadSection from './components/UploadSection'
import Dashboard from './components/Dashboard'
import LLMChat from './components/LLMChat'
import AnalyticsPanel from './components/AnalyticsPanel'
import Footer from './components/Footer'

function App() {
  const [activeTab, setActiveTab] = useState<'upload' | 'dashboard' | 'chat' | 'analytics'>('upload')
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleDocumentProcessed = () => {
    setRefreshTrigger(prev => prev + 1)
    setActiveTab('dashboard')
  }

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Navigation */}
      <Header activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Hero Section - Always visible */}
      <Hero />

      {/* Main Content Area */}
      <main className="section-container pb-20">
        {/* Tab Navigation */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex bg-white rounded-2xl p-1.5 shadow-card border border-slate-100">
            {[
              { id: 'upload' as const, label: 'Process Documents', icon: 'Upload' },
              { id: 'dashboard' as const, label: 'Documents', icon: 'FileText' },
              { id: 'chat' as const, label: 'AI Assistant', icon: 'MessageSquare' },
              { id: 'analytics' as const, label: 'Analytics', icon: 'BarChart3' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  relative px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200
                  ${activeTab === tab.id
                    ? 'bg-primary-600 text-white shadow-soft'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content Panels */}
        <div className="animate-fade-in">
          {activeTab === 'upload' && (
            <UploadSection onDocumentProcessed={handleDocumentProcessed} />
          )}
          {activeTab === 'dashboard' && (
            <Dashboard refreshTrigger={refreshTrigger} />
          )}
          {activeTab === 'chat' && (
            <LLMChat />
          )}
          {activeTab === 'analytics' && (
            <AnalyticsPanel refreshTrigger={refreshTrigger} />
          )}
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  )
}

export default App
