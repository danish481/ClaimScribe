import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, Shield, Sparkles, Clock } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

const suggestedQueries = [
  'What type of claim is this document?',
  'Analyze the billing codes in this document',
  'What compliance issues should I check?',
  'Summarize the key information',
  'Explain the HIPAA implications',
  'What is the claim processing workflow?',
]

interface LLMChatProps {
  initialDocumentId?: string | null
  initialFilename?: string | null
}

export default function LLMChat({ initialDocumentId, initialFilename }: LLMChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I am ClaimScribe AI, your healthcare document analysis assistant. I can help you understand claim documents, billing codes, compliance requirements, and more. How can I assist you today?',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sentDocIdRef = useRef<string | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const sendMessageWithDocId = async (content: string, docId: string | null) => {
    if (!content.trim()) return

    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const body: Record<string, unknown> = { query: content, include_sources: true }
      if (docId) body.document_ids = [docId]
      const response = await fetch(`${API_URL}/api/v1/llm/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      const data = await response.json()

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.response || 'I apologize, but I could not process your request at this time. Please try again.',
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      // Fallback response when backend is unavailable
      const fallbackMessage: Message = {
        role: 'assistant',
        content: generateFallbackResponse(content),
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, fallbackMessage])
    } finally {
      setLoading(false)
    }
  }

  const generateFallbackResponse = (query: string): string => {
    const q = query.toLowerCase()
    if (q.includes('classify') || q.includes('type')) {
      return 'Based on healthcare document analysis patterns, I can classify claims into three main categories:\n\n**Inpatient Claims**: Hospital admissions, overnight stays, surgeries requiring admission\n**Outpatient Claims**: Clinic visits, emergency room, same-day procedures\n**Pharmacy Claims**: Prescriptions, medication dispensing, drug costs\n\nWould you like me to analyze a specific document?'
    }
    if (q.includes('code') || q.includes('icd') || q.includes('cpt')) {
      return 'Medical coding is essential for claims processing:\n\n- **ICD-10 Codes**: Diagnosis classification (e.g., J18.9 for pneumonia)\n- **CPT Codes**: Procedures and services (e.g., 99213 for office visit)\n- **HCPCS Codes**: Supplies and equipment\n- **NDC Codes**: National Drug Code for pharmacy claims\n\nProper coding ensures accurate reimbursement and compliance.'
    }
    if (q.includes('hipaa') || q.includes('compliance') || q.includes('privacy')) {
      return 'HIPAA compliance in claims processing involves:\n\n1. **Administrative Safeguards**: Workforce training, access management\n2. **Physical Safeguards**: Secure facilities, workstation security\n3. **Technical Safeguards**: Encryption (AES-128), audit controls\n4. **Breach Notification**: Timely reporting of any data incidents\n5. **Minimum Necessary**: Limiting PHI access to what\'s required\n\nClaimScribe implements all these with automated PHI detection and encryption.'
    }
    return 'Thank you for your question about healthcare claims processing.\n\nI can assist with:\n- Document classification and analysis\n- Medical coding interpretation (ICD-10, CPT, HCPCS)\n- HIPAA compliance guidance\n- Claims workflow optimization\n- Billing and reimbursement questions\n\nCould you please share more details or upload a document you\'d like me to analyze?'
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (initialDocumentId && initialDocumentId !== sentDocIdRef.current) {
      sentDocIdRef.current = initialDocumentId
      const label = initialFilename ? `"${initialFilename}"` : `document ID ${initialDocumentId}`
      sendMessageWithDocId(
        `Please analyze ${label}. Classify the claim type, highlight any PHI, and summarize the key findings.`,
        initialDocumentId,
      )
    }
  }, [initialDocumentId, initialFilename])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessageWithDocId(input, null)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="card overflow-hidden" style={{ height: '700px' }}>
        {/* Chat Header */}
        <div className="p-4 border-b border-slate-100 bg-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-800">Healthcare AI Assistant</h3>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-medical-500 rounded-full animate-pulse" />
                <span className="text-xs text-slate-400">Powered by Gemini 2.5 Flash</span>
              </div>
            </div>
            <div className="ml-auto flex items-center gap-1.5 px-3 py-1 bg-medical-50 rounded-lg">
              <Shield className="w-3.5 h-3.5 text-medical-600" />
              <span className="text-xs font-medium text-medical-600">PHI-Safe</span>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{ height: 'calc(700px - 140px)' }}>
          <AnimatePresence>
            {messages.map((message, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
              >
                {/* Avatar */}
                <div className={`
                  w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0
                  ${message.role === 'assistant'
                    ? 'bg-gradient-to-br from-primary-500 to-primary-600'
                    : 'bg-slate-200'
                  }
                `}>
                  {message.role === 'assistant' ? (
                    <Sparkles className="w-4 h-4 text-white" />
                  ) : (
                    <User className="w-4 h-4 text-slate-600" />
                  )}
                </div>

                {/* Message Bubble */}
                <div className={`
                  max-w-[80%] px-4 py-3 rounded-2xl
                  ${message.role === 'assistant'
                    ? 'bg-white border border-slate-100 shadow-sm'
                    : 'bg-primary-600 text-white'
                  }
                `}>
                  <div className="text-sm whitespace-pre-wrap leading-relaxed">
                    {message.content}
                  </div>
                  <div className={`
                    text-xs mt-2 flex items-center gap-1
                    ${message.role === 'assistant' ? 'text-slate-400' : 'text-primary-200'}
                  `}>
                    <Clock className="w-3 h-3" />
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-3"
            >
              <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div className="bg-white border border-slate-100 rounded-2xl px-4 py-3 shadow-sm">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 text-primary-600 animate-spin" />
                  <span className="text-sm text-slate-500">Analyzing...</span>
                </div>
              </div>
            </motion.div>
          )}

          {/* Suggested Queries - Show initially */}
          {messages.length === 1 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="mt-6"
            >
              <p className="text-xs text-slate-400 mb-3">Suggested questions</p>
              <div className="flex flex-wrap gap-2">
                {suggestedQueries.map((query) => (
                  <button
                    key={query}
                    onClick={() => sendMessageWithDocId(query, null)}
                    className="px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm text-slate-600 hover:border-primary-300 hover:text-primary-700 transition-colors"
                  >
                    {query}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-slate-100 bg-white">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about claims, codes, compliance..."
              className="flex-1 input-field"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="btn-primary px-5"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </form>
          <p className="text-xs text-slate-400 mt-2 text-center">
            All queries are PHI-filtered and audit-logged for HIPAA compliance
          </p>
        </div>
      </div>
    </div>
  )
}
