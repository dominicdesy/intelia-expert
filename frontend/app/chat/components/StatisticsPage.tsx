'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useAuthStore } from '@/lib/stores/auth' 
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { StatisticsDashboard } from './StatisticsDashboard'
import { QuestionsTab } from './QuestionsTab'

// Types (compatibles avec l'existant)
interface SystemStats {
  system_health: {
    uptime_hours: number
    total_requests: number
    error_rate: number
    rag_status: {
      global: boolean
      broiler: boolean
      layer: boolean
    }
  }
  billing_stats: {
    plans_available: number
    plan_names: string[]
  }
  features_enabled?: {
    analytics: boolean
    billing: boolean
    authentication: boolean
    openai_fallback: boolean
  }
}

interface UsageStats {
  unique_users: number
  total_questions: number
  questions_today: number
  questions_this_month: number
  source_distribution: {
    rag_retriever: number
    openai_fallback: number
    perfstore: number
  }
  monthly_breakdown: { [month: string]: number }
}

interface BillingStats {
  plans?: {
    [planName: string]: {
      user_count: number
      revenue: number
    }
  }
  total_revenue: number
  top_users?: Array<{
    email: string
    question_count: number
    plan: string
  }>
}

interface PerformanceStats {
  avg_response_time: number
  median_response_time?: number
  min_response_time?: number
  max_response_time?: number
  response_time_count?: number
  openai_costs?: number
  error_count?: number
  cache_hit_rate: number
}

interface QuestionLog {
  id: string
  timestamp: string
  user_email: string
  user_name: string
  question: string
  response: string
  response_source: 'rag' | 'openai_fallback' | 'table_lookup' | 'validation_rejected' | 'quota_exceeded' | 'unknown'
  confidence_score: number
  response_time: number
  language: string
  session_id?: string
  feedback: number | null
  feedback_comment: string | null
}

interface QuestionsApiResponse {
  questions: QuestionLog[]
  pagination: {
    page: number
    limit: number
    total: number
    pages: number
    has_next?: boolean
    has_prev?: boolean
  }
  meta?: {
    retrieved: number
    user_role: string
    timestamp: string
  }
}

export const StatisticsPage: React.FC = () => {
  const { user } = useAuthStore()

  const [authStatus, setAuthStatus] = useState<'initializing' | 'checking' | 'ready' | 'unauthorized' | 'forbidden'>('initializing')
  const [statsLoading, setStatsLoading] = useState(false)
  const [questionsLoading, setQuestionsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Data
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [billingStats, setBillingStats] = useState<BillingStats | null>(null)
  const [performanceStats, setPerformanceStats] = useState<PerformanceStats | null>(null)
  const [questionLogs, setQuestionLogs] = useState<QuestionLog[]>([])
  const [totalQuestions, setTotalQuestions] = useState(0)

  // UI
  const [selectedTimeRange, setSelectedTimeRange] = useState<'day' | 'week' | 'month' | 'year'>('month')
  const [activeTab, setActiveTab] = useState<'dashboard' | 'questions'>('dashboard')
  const [questionFilters, setQuestionFilters] = useState({
    search: '',
    source: 'all',
    confidence: 'all',
    feedback: 'all',
    user: 'all'
  })
  const [currentPage, setCurrentPage] = useState(1)
  const [questionsPerPage] = useState(20)
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionLog | null>(null)

  // Refs
  const authCheckRef = useRef<boolean>(false)

  // Auth check simple
  useEffect(() => {
    const supabase = createClientComponentClient()
    setAuthStatus('checking')
    supabase.auth.getSession()
      .then(({ data }) => {
        if (data.session) setAuthStatus('ready')
        else setAuthStatus('unauthorized')
      })
      .catch(() => setAuthStatus('forbidden'))
  }, [])

  // Loaders (à adapter à tes endpoints)
  const loadAllStatistics = async () => {
    try {
      setStatsLoading(true); setError(null)
      const headers: HeadersInit = { 'Content-Type': 'application/json' }

      const [sysRes, usageRes, billRes, perfRes] = await Promise.all([
        fetch('/api/admin/system-stats', { headers }),
        fetch('/api/admin/usage-stats', { headers }),
        fetch('/api/admin/billing-stats', { headers }),
        fetch('/api/admin/performance-stats', { headers }),
      ])

      if (!sysRes.ok || !usageRes.ok || !billRes.ok || !perfRes.ok) {
        throw new Error('Une ou plusieurs requêtes ont échoué')
      }

      const sys = await sysRes.json() as SystemStats
      const use = await usageRes.json() as UsageStats
      const bill = await billRes.json() as BillingStats
      const perf = await perfRes.json() as PerformanceStats

      setSystemStats(sys); setUsageStats(use); setBillingStats(bill); setPerformanceStats(perf)
    } catch (err:any) {
      setError(`Erreur chargement statistiques: ${String(err?.message || err)}`)
    } finally { setStatsLoading(false) }
  }

  const mapResponseSource = (source: string): QuestionLog['response_source'] => {
    switch (source) {
      case 'rag': return 'rag'
      case 'openai_fallback': return 'openai_fallback'
      case 'table_lookup': return 'table_lookup'
      case 'validation_rejected': return 'validation_rejected'
      case 'quota_exceeded': return 'quota_exceeded'
      default: return 'unknown'
    }
  }

  const loadQuestionLogs = async () => {
    try {
      setQuestionsLoading(true); setError(null)
      const headers: HeadersInit = { 'Content-Type': 'application/json' }
      const res = await fetch('/api/admin/question-logs', { headers })
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      const data: QuestionsApiResponse = await res.json()
      const adapted: QuestionLog[] = data.questions.map(q => ({ ...q, response_source: mapResponseSource(q.response_source) }))
      setQuestionLogs(adapted); setTotalQuestions(data.pagination.total)
    } catch (err:any) {
      setError(`Erreur chargement questions: ${String(err?.message || err)}`); setQuestionLogs([])
    } finally { setQuestionsLoading(false) }
  }

  useEffect(() => {
    if (authStatus === 'ready') {
      loadAllStatistics()
      loadQuestionLogs()
    }
  }, [authStatus])

  // Calcul MAU du mois précédent (utilisateurs actifs, basé sur logs)
  const activePrevMonth = React.useMemo(() => {
    try {
      if (!questionLogs || questionLogs.length === 0) return 0
      const now = new Date()
      const prevStart = new Date(now.getFullYear(), now.getMonth() - 1, 1).getTime()
      const prevEnd = new Date(now.getFullYear(), now.getMonth(), 1).getTime()
      const set = new Set<string>()
      for (const q of questionLogs) {
        const t = new Date(q.timestamp).getTime()
        if (t >= prevStart && t < prevEnd) set.add(q.user_email)
      }
      return set.size
    } catch { return 0 }
  }, [questionLogs])

  // Render
  if (authStatus !== 'ready') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Barre d'onglets : Statistiques / Q&A */}
      <div className="bg-white/80 backdrop-blur border-b">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-14 flex items-end">
          <button
            onClick={()=>setActiveTab('dashboard')}
            className={`mr-4 pb-2 text-sm border-b-2 -mb-px ${activeTab==='dashboard' ? 'text-blue-700 border-blue-600' : 'text-gray-600 border-transparent hover:text-blue-700'}`}
          >
            Statistiques
          </button>
          <button
            onClick={()=>setActiveTab('questions')}
            className={`mr-4 pb-2 text-sm border-b-2 -mb-px ${activeTab==='questions' ? 'text-blue-700 border-blue-600' : 'text-gray-600 border-transparent hover:text-blue-700'}`}
          >
            Q&A
          </button>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {activeTab === 'dashboard' && (
          <StatisticsDashboard
            systemStats={systemStats}
            usageStats={usageStats}
            billingStats={billingStats}
            performanceStats={performanceStats}
            activePrevMonth={activePrevMonth}
          />
        )}

        {activeTab === 'questions' && (
          <QuestionsTab
            questionLogs={questionLogs}
            questionFilters={questionFilters}
            setQuestionFilters={setQuestionFilters}
            selectedTimeRange={selectedTimeRange}
            setSelectedTimeRange={setSelectedTimeRange}
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
            questionsPerPage={questionsPerPage}
            setSelectedQuestion={setSelectedQuestion}
            isLoading={questionsLoading}
            totalQuestions={totalQuestions}
          />
        )}
      </main>
    </div>
  )
}