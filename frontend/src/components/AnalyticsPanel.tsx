import { useState, useEffect } from 'react'
import {
  FileText, TrendingUp, Shield, Brain, Clock, Activity,
  AlertTriangle, CheckCircle, Loader2
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
  AreaChart, Area,
} from 'recharts'
import { motion } from 'framer-motion'

interface AnalyticsProps {
  refreshTrigger: number
}

const COLORS = {
  inpatient: '#3b82f6',
  outpatient: '#10b981',
  pharmacy: '#8b5cf6',
  unknown: '#94a3b8',
}

// Demo data
const typeDistribution = [
  { name: 'Inpatient', value: 42, color: COLORS.inpatient },
  { name: 'Outpatient', value: 35, color: COLORS.outpatient },
  { name: 'Pharmacy', value: 23, color: COLORS.pharmacy },
]

const processingTrend = [
  { time: '00:00', documents: 12, avgConfidence: 0.89 },
  { time: '04:00', documents: 8, avgConfidence: 0.91 },
  { time: '08:00', documents: 25, avgConfidence: 0.87 },
  { time: '12:00', documents: 45, avgConfidence: 0.93 },
  { time: '16:00', documents: 38, avgConfidence: 0.90 },
  { time: '20:00', documents: 20, avgConfidence: 0.92 },
]

const confidenceByType = [
  { type: 'Inpatient', confidence: 0.92, count: 42 },
  { type: 'Outpatient', confidence: 0.88, count: 35 },
  { type: 'Pharmacy', confidence: 0.95, count: 23 },
]

const recentActivity = [
  { event: 'Document classified', detail: 'claim_123.pdf → Inpatient', time: '2 min ago', status: 'success' },
  { event: 'PHI detected', detail: 'Masking applied to 3 fields', time: '5 min ago', status: 'warning' },
  { event: 'MLflow logging', detail: 'Run logged: run_abc123', time: '8 min ago', status: 'success' },
  { event: 'Document uploaded', detail: 'pharmacy_rx.pdf uploaded', time: '12 min ago', status: 'success' },
  { event: 'OCR completed', detail: 'Text extracted: 2,400 chars', time: '15 min ago', status: 'success' },
]

export default function AnalyticsPanel({ refreshTrigger }: AnalyticsProps) {
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setTimeout(() => setLoading(false), 800)
  }, [refreshTrigger])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Documents', value: '128', change: '+12%', icon: FileText, color: 'blue' },
          { label: 'Avg Confidence', value: '91.4%', change: '+2.3%', icon: Brain, color: 'emerald' },
          { label: 'PHI Detection Rate', value: '34%', change: '-5%', icon: Shield, color: 'amber' },
          { label: 'Processing Time', value: '1.2s', change: '-0.3s', icon: Clock, color: 'violet' },
        ].map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="card p-5"
          >
            <div className="flex items-start justify-between mb-3">
              <div className={`
                w-10 h-10 rounded-xl flex items-center justify-center
                ${stat.color === 'blue' ? 'bg-blue-50' : ''}
                ${stat.color === 'emerald' ? 'bg-emerald-50' : ''}
                ${stat.color === 'amber' ? 'bg-amber-50' : ''}
                ${stat.color === 'violet' ? 'bg-violet-50' : ''}
              `}>
                <stat.icon className={`
                  w-5 h-5
                  ${stat.color === 'blue' ? 'text-blue-600' : ''}
                  ${stat.color === 'emerald' ? 'text-emerald-600' : ''}
                  ${stat.color === 'amber' ? 'text-amber-600' : ''}
                  ${stat.color === 'violet' ? 'text-violet-600' : ''}
                `} />
              </div>
              <span className={`
                text-xs font-medium px-2 py-0.5 rounded-full
                ${stat.change.startsWith('+') ? 'bg-emerald-50 text-emerald-600' : 'bg-blue-50 text-blue-600'}
              `}>
                {stat.change}
              </span>
            </div>
            <p className="text-2xl font-bold text-slate-800">{stat.value}</p>
            <p className="text-sm text-slate-400 mt-1">{stat.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Type Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card p-6"
        >
          <h3 className="font-semibold text-slate-800 mb-1">Claim Type Distribution</h3>
          <p className="text-sm text-slate-400 mb-6">Breakdown by classification</p>

          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={typeDistribution}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={4}
                dataKey="value"
              >
                {typeDistribution.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '12px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
                  fontSize: '12px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>

          <div className="flex justify-center gap-4 mt-4">
            {typeDistribution.map((item) => (
              <div key={item.name} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: item.color }} />
                <span className="text-xs text-slate-500">{item.name}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Confidence by Type */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card p-6"
        >
          <h3 className="font-semibold text-slate-800 mb-1">Classification Confidence</h3>
          <p className="text-sm text-slate-400 mb-6">Average confidence by type</p>

          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={confidenceByType} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
              <YAxis type="category" dataKey="type" width={80} tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '12px',
                  fontSize: '12px',
                }}
                formatter={(value: number) => `${(value * 100).toFixed(1)}%`}
              />
              <Bar dataKey="confidence" fill="#3b82f6" radius={[0, 6, 6, 0]} barSize={24} />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Processing Trend */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card p-6"
        >
          <h3 className="font-semibold text-slate-800 mb-1">Processing Volume</h3>
          <p className="text-sm text-slate-400 mb-6">Documents processed over time</p>

          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={processingTrend}>
              <defs>
                <linearGradient id="colorDocs" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="time" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: 'white',
                  border: '1px solid #e2e8f0',
                  borderRadius: '12px',
                  fontSize: '12px',
                }}
              />
              <Area
                type="monotone"
                dataKey="documents"
                stroke="#3b82f6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorDocs)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>
      </div>

      {/* Bottom Row: Activity + System Health */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="card p-6"
        >
          <h3 className="font-semibold text-slate-800 mb-1">Recent Activity</h3>
          <p className="text-sm text-slate-400 mb-4">Latest processing events</p>

          <div className="space-y-3">
            {recentActivity.map((activity, index) => (
              <div key={index} className="flex items-start gap-3 p-3 bg-slate-50/50 rounded-xl">
                <div className={`
                  w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
                  ${activity.status === 'success' ? 'bg-emerald-50' : 'bg-amber-50'}
                `}>
                  {activity.status === 'success' ? (
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-700">{activity.event}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{activity.detail}</p>
                </div>
                <span className="text-xs text-slate-400 flex-shrink-0">{activity.time}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* System Health */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="card p-6"
        >
          <h3 className="font-semibold text-slate-800 mb-1">System Health</h3>
          <p className="text-sm text-slate-400 mb-4">Component status overview</p>

          <div className="space-y-3">
            {[
              { name: 'API Server', status: 'Operational', health: 'good', icon: Activity },
              { name: 'OCR Engine', status: 'Tesseract Ready', health: 'good', icon: FileText },
              { name: 'Classifier', status: 'Keyword + ML', health: 'good', icon: Brain },
              { name: 'MLflow Tracking', status: 'Connected', health: 'good', icon: TrendingUp },
              { name: 'LLM Service', status: 'Gemini Flash', health: 'good', icon: Brain },
              { name: 'Encryption', status: 'AES-128 Active', health: 'good', icon: Shield },
            ].map((component) => (
              <div key={component.name} className="flex items-center justify-between p-3 bg-slate-50/50 rounded-xl">
                <div className="flex items-center gap-3">
                  <component.icon className="w-4 h-4 text-slate-400" />
                  <span className="text-sm text-slate-700">{component.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">{component.status}</span>
                  <span className={`
                    w-2 h-2 rounded-full
                    ${component.health === 'good' ? 'bg-emerald-500' : ''}
                    ${component.health === 'warning' ? 'bg-amber-500' : ''}
                    ${component.health === 'error' ? 'bg-red-500' : ''}
                  `} />
                </div>
              </div>
            ))}
          </div>

          {/* MLflow Link */}
          <a
            href="http://localhost:5000"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 mt-4 p-3 bg-primary-50 hover:bg-primary-100 rounded-xl text-sm font-medium text-primary-700 transition-colors"
          >
            <TrendingUp className="w-4 h-4" />
            Open MLflow Tracking UI
          </a>
        </motion.div>
      </div>
    </div>
  )
}
