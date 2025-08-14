import React, { useState, useEffect } from 'react'
import { useAuthStore } from '../hooks/useAuthStore'

// Types pour les données de statistiques
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
  features_enabled: {
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
  monthly_breakdown: {
    [month: string]: number
  }
}

interface BillingStats {
  plans: {
    [planName: string]: {
      user_count: number
      revenue: number
    }
  }
  total_revenue: number
  top_users: Array<{
    email: string
    question_count: number
    plan: string
  }>
}

interface PerformanceStats {
  avg_response_time: number
  openai_costs: number
  error_count: number
  cache_hit_rate: number
}

interface QuestionLog {
  id: string
  timestamp: string
  user_email: string
  user_name: string
  question: string
  response: string
  response_source: 'rag_retriever' | 'openai_fallback' | 'perfstore' | 'agricultural_validator'
  confidence_score: number
  response_time: number
  language: string
  session_id: string
  feedback: number | null // 1 pour positif, -1 pour négatif, null pour pas de feedback
  feedback_comment: string | null
}

export const StatisticsPage: React.FC = () => {
  const { user } = useAuthStore()
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [billingStats, setBillingStats] = useState<BillingStats | null>(null)
  const [performanceStats, setPerformanceStats] = useState<PerformanceStats | null>(null)
  const [questionLogs, setQuestionLogs] = useState<QuestionLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
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

  // Vérification des permissions super_admin
  const isSuperAdmin = user?.user_type === 'super_admin'

  useEffect(() => {
    if (!isSuperAdmin) {
      setError("Accès refusé - Permissions super_admin requises")
      setLoading(false)
      return
    }

    loadAllStatistics()
  }, [isSuperAdmin, selectedTimeRange])

  useEffect(() => {
    if (activeTab === 'questions') {
      loadQuestionLogs()
    }
  }, [activeTab, questionFilters, currentPage])

  const loadAllStatistics = async () => {
    setLoading(true)
    setError(null)

    try {
      const token = localStorage.getItem('supabase_token') || sessionStorage.getItem('supabase_token')
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }

      // Charger toutes les statistiques en parallèle
      const [systemRes, usageRes, billingRes, performanceRes] = await Promise.allSettled([
        fetch('/api/admin/stats', { headers }),
        fetch('/api/v1/logging/analytics/dashboard', { headers }),
        fetch('/api/v1/billing/admin/stats', { headers }), // Endpoint hypothétique
        fetch('/api/v1/logging/analytics/performance', { headers })
      ])

      // Traitement des résultats
      if (systemRes.status === 'fulfilled' && systemRes.value.ok) {
        setSystemStats(await systemRes.value.json())
      }

      if (usageRes.status === 'fulfilled' && usageRes.value.ok) {
        setUsageStats(await usageRes.value.json())
      }

      if (billingRes.status === 'fulfilled' && billingRes.value.ok) {
        setBillingStats(await billingRes.value.json())
      } else {
        // Mock data si l'endpoint n'existe pas encore
        setBillingStats({
          plans: {
            essential: { user_count: 15, revenue: 750 },
            professional: { user_count: 8, revenue: 2400 },
            enterprise: { user_count: 2, revenue: 2000 }
          },
          total_revenue: 5150,
          top_users: [
            { email: 'dominic.desy@intelia.com', question_count: 245, plan: 'enterprise' },
            { email: 'vincent.guyonnet18@gmail.com', question_count: 156, plan: 'professional' },
            { email: 'claude.bouchard@intelia.com', question_count: 98, plan: 'professional' }
          ]
        })
      }

      if (performanceRes.status === 'fulfilled' && performanceRes.value.ok) {
        setPerformanceStats(await performanceRes.value.json())
      } else {
        // Mock data
        setPerformanceStats({
          avg_response_time: 1.8,
          openai_costs: 127.35,
          error_count: 12,
          cache_hit_rate: 85.2
        })
      }

    } catch (err) {
      console.error('Erreur chargement statistiques:', err)
      setError('Erreur lors du chargement des statistiques')
    } finally {
      setLoading(false)
    }
  }

  const loadQuestionLogs = async () => {
    try {
      const token = localStorage.getItem('supabase_token') || sessionStorage.getItem('supabase_token')
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }

      // Construire les paramètres de requête
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: questionsPerPage.toString(),
        search: questionFilters.search,
        source: questionFilters.source,
        confidence: questionFilters.confidence,
        feedback: questionFilters.feedback,
        user: questionFilters.user,
        time_range: selectedTimeRange
      })

      // 🔄 NOUVEAU: Essayer plusieurs endpoints pour récupérer les données réelles
      const endpointsToTry = [
        `/api/v1/logging/analytics/conversations-with-feedback?${params}`, // Endpoint idéal pour récupérer conversations + feedback
        `/api/v1/logging/analytics/questions?${params}`, // Endpoint questions seules
        `/api/v1/conversations/all-with-feedback?${params}`, // Alternative conversations
        `/api/v1/logging/analytics/user-interactions?${params}` // Alternative interactions
      ]

      let questionsLoaded = false

      for (const endpoint of endpointsToTry) {
        try {
          console.log(`🔍 Tentative endpoint: ${endpoint}`)
          const response = await fetch(endpoint, { headers })
          
          if (response.ok) {
            const data = await response.json()
            console.log(`✅ Données récupérées via ${endpoint}:`, data)
            
            // 🔧 Adapter selon la structure de réponse
            let questions = []
            
            if (Array.isArray(data)) {
              questions = data
            } else if (data.conversations && Array.isArray(data.conversations)) {
              questions = data.conversations
            } else if (data.questions && Array.isArray(data.questions)) {
              questions = data.questions
            } else if (data.interactions && Array.isArray(data.interactions)) {
              questions = data.interactions
            } else if (data.data && Array.isArray(data.data)) {
              questions = data.data
            }

            // 🔧 Transformer les données si nécessaire
            const transformedQuestions = questions.map((item: any) => ({
              id: item.id || item.conversation_id || item.session_id,
              timestamp: item.timestamp || item.created_at || item.updated_at,
              user_email: item.user_email || item.email || item.user_id,
              user_name: item.user_name || item.full_name || item.name || item.user_email?.split('@')[0] || 'Utilisateur',
              question: item.question || item.user_message || item.prompt || item.content,
              response: item.response || item.ai_response || item.answer || item.completion,
              response_source: item.response_source || item.source || item.provider || 'unknown',
              confidence_score: item.confidence_score || item.confidence || item.score || 0.5,
              response_time: item.response_time || item.response_time_ms / 1000 || item.duration || 0,
              language: item.language || item.lang || 'fr',
              session_id: item.session_id || item.conversation_id || item.id,
              feedback: item.feedback || item.feedback_score || null,
              feedback_comment: item.feedback_comment || item.comment || item.feedback_text || null
            }))

            setQuestionLogs(transformedQuestions)
            questionsLoaded = true
            console.log(`✅ ${transformedQuestions.length} questions chargées depuis ${endpoint}`)
            break

          } else {
            console.log(`❌ ${endpoint}: ${response.status} ${response.statusText}`)
          }
        } catch (err) {
          console.log(`❌ Erreur ${endpoint}:`, err)
        }
      }

      // Si aucun endpoint ne fonctionne, utiliser des données mockées pour demo
      if (!questionsLoaded) {
        console.log('⚠️ Aucun endpoint disponible, utilisation de données mockées')
        const mockQuestions: QuestionLog[] = [
          {
            id: '1',
            timestamp: '2025-08-14T10:30:00Z',
            user_email: 'dominic.desy@intelia.com',
            user_name: 'Dominic Desy',
            question: 'Quelles sont les causes de mortalité élevée chez les poulets de chair de 3 semaines?',
            response: 'Les causes principales de mortalité chez les poulets de chair de 3 semaines incluent:\n\n**Maladies infectieuses:**\n- Coccidiose (très fréquente à cet âge)\n- Syndrome de mort subite\n- Infections bactériennes (E. coli, Salmonella)\n\n**Facteurs environnementaux:**\n- Qualité de l\'air (ammoniac, CO2)\n- Température inadéquate\n- Densité trop élevée',
            response_source: 'rag_retriever',
            confidence_score: 0.92,
            response_time: 1.8,
            language: 'fr',
            session_id: 'session_123',
            feedback: 1,
            feedback_comment: 'Excellente réponse, très complète'
          },
          {
            id: '2',
            timestamp: '2025-08-14T09:15:00Z',
            user_email: 'vincent.guyonnet18@gmail.com',
            user_name: 'Vincent Guyonnet',
            question: 'Comment optimiser la conversion alimentaire des poules pondeuses?',
            response: 'Pour optimiser la conversion alimentaire des poules pondeuses, voici les stratégies clés:\n\n**Alimentation:**\n- Adapter la densité énergétique selon l\'âge\n- Optimiser le ratio lysine/énergie\n- Utiliser des enzymes digestives\n\n**Management:**\n- Contrôler la température (18-22°C optimal)\n- Assurer un éclairage approprié (14-16h)\n- Maintenir la qualité de l\'eau',
            response_source: 'openai_fallback',
            confidence_score: 0.78,
            response_time: 2.3,
            language: 'fr',
            session_id: 'session_456',
            feedback: null,
            feedback_comment: null
          },
          {
            id: '3',
            timestamp: '2025-08-14T08:45:00Z',
            user_email: 'claude.bouchard@intelia.com',
            user_name: 'Claude Bouchard',
            question: 'What are the optimal protein levels for broiler feed?',
            response: 'Optimal protein levels for broiler feed vary by growth phase:\n\n**Starter phase (0-10 days):** 23-24% crude protein\n**Grower phase (11-24 days):** 20-22% crude protein\n**Finisher phase (25+ days):** 18-20% crude protein\n\nThese levels should be adjusted based on:\n- Genetic line requirements\n- Environmental conditions\n- Target performance goals',
            response_source: 'perfstore',
            confidence_score: 0.95,
            response_time: 1.2,
            language: 'en',
            session_id: 'session_789',
            feedback: 1,
            feedback_comment: 'Perfect answer with specific values'
          },
          {
            id: '4',
            timestamp: '2025-08-14T07:20:00Z',
            user_email: 'dominic.desy@intelia.com',
            user_name: 'Dominic Desy',
            question: 'Quel est le meilleur film de 2024?',
            response: 'Je suis désolé, mais cette question ne concerne pas le domaine agricole et avicole. Je suis spécialisé dans l\'expertise agricole.\n\n**Voici quelques sujets que je peux vous aider :**\n• Nutrition animale et formulation d\'aliments\n• Santé et pathologies aviaires\n• Management et conduite d\'élevage\n• Performances zootechniques',
            response_source: 'agricultural_validator',
            confidence_score: 0.99,
            response_time: 0.8,
            language: 'fr',
            session_id: 'session_999',
            feedback: -1,
            feedback_comment: 'Trop restrictif, devrait permettre quelques questions générales'
          }
        ]
        setQuestionLogs(mockQuestions)
        console.log('📝 Données mockées chargées pour démo')
      }
    } catch (err) {
      console.error('❌ Erreur générale lors du chargement des logs questions:', err)
      // Fallback sur données mockées en cas d'erreur
      setQuestionLogs([])
    }
  }

  const getConfidenceColor = (score: number) => {
    if (score >= 0.9) return 'text-green-600 bg-green-100'
    if (score >= 0.7) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-600 bg-red-100'
  }

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'rag_retriever': return 'text-blue-600 bg-blue-100'
      case 'openai_fallback': return 'text-purple-600 bg-purple-100'
      case 'perfstore': return 'text-green-600 bg-green-100'
      case 'agricultural_validator': return 'text-orange-600 bg-orange-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getFeedbackIcon = (feedback: number | null) => {
    if (feedback === 1) return '👍'
    if (feedback === -1) return '👎'
    return '❓'
  }

  const filteredQuestions = questionLogs.filter(q => {
    if (questionFilters.search && !q.question.toLowerCase().includes(questionFilters.search.toLowerCase()) && 
        !q.response.toLowerCase().includes(questionFilters.search.toLowerCase()) &&
        !q.user_email.toLowerCase().includes(questionFilters.search.toLowerCase())) {
      return false
    }
    if (questionFilters.source !== 'all' && q.response_source !== questionFilters.source) return false
    if (questionFilters.confidence !== 'all') {
      const score = q.confidence_score
      if (questionFilters.confidence === 'high' && score < 0.9) return false
      if (questionFilters.confidence === 'medium' && (score < 0.7 || score >= 0.9)) return false
      if (questionFilters.confidence === 'low' && score >= 0.7) return false
    }
    if (questionFilters.feedback !== 'all') {
      if (questionFilters.feedback === 'positive' && q.feedback !== 1) return false
      if (questionFilters.feedback === 'negative' && q.feedback !== -1) return false
      if (questionFilters.feedback === 'none' && q.feedback !== null) return false
      if (questionFilters.feedback === 'with_comments' && !q.feedback_comment) return false
      if (questionFilters.feedback === 'no_comments' && q.feedback_comment) return false
    }
    if (questionFilters.user !== 'all' && q.user_email !== questionFilters.user) return false
    return true
  })

  const paginatedQuestions = filteredQuestions.slice(
    (currentPage - 1) * questionsPerPage,
    currentPage * questionsPerPage
  )

  const totalPages = Math.ceil(filteredQuestions.length / questionsPerPage)
  const uniqueUsers = [...new Set(questionLogs.map(q => q.user_email))]

  if (!isSuperAdmin) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full text-center">
          <div className="text-red-600 text-6xl mb-4">🚫</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Accès refusé</h2>
          <p className="text-gray-600 mb-6">Cette page est réservée aux super administrateurs.</p>
          <button
            onClick={() => window.history.back()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retour
          </button>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement des statistiques...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full text-center">
          <div className="text-red-600 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Erreur</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={loadAllStatistics}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Réessayer
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => window.history.back()}
                className="text-gray-600 hover:text-gray-900 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </button>
              <h1 className="text-2xl font-bold text-gray-900">Statistiques Administrateur</h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setActiveTab('dashboard')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeTab === 'dashboard' 
                      ? 'bg-white text-blue-600 shadow-sm' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  📊 Tableau de Bord
                </button>
                <button
                  onClick={() => setActiveTab('questions')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeTab === 'questions' 
                      ? 'bg-white text-blue-600 shadow-sm' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  💬 Questions & Réponses
                </button>
              </div>
              
              {activeTab === 'dashboard' && (
                <>
                  <select
                    value={selectedTimeRange}
                    onChange={(e) => setSelectedTimeRange(e.target.value as any)}
                    className="border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="day">Aujourd'hui</option>
                    <option value="week">Cette semaine</option>
                    <option value="month">Ce mois</option>
                    <option value="year">Cette année</option>
                  </select>
                  
                  <button
                    onClick={loadAllStatistics}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm"
                  >
                    🔄 Actualiser
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {activeTab === 'dashboard' ? (
          <>
            {/* KPIs Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <div className="flex items-center">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM9 3a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Utilisateurs Actifs</p>
                    <p className="text-2xl font-bold text-gray-900">{usageStats?.unique_users || 0}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <div className="flex items-center">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Questions ce mois</p>
                    <p className="text-2xl font-bold text-gray-900">{usageStats?.questions_this_month || 0}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <div className="flex items-center">
                  <div className="p-2 bg-yellow-100 rounded-lg">
                    <svg className="w-6 h-6 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Revenus Totaux</p>
                    <p className="text-2xl font-bold text-gray-900">${billingStats?.total_revenue || 0}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <div className="flex items-center">
                  <div className="p-2 bg-red-100 rounded-lg">
                    <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Temps de Réponse</p>
                    <p className="text-2xl font-bold text-gray-900">{performanceStats?.avg_response_time || 0}s</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {/* Usage Sources Chart */}
              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Sources des Réponses</h3>
                <div className="space-y-4">
                  {usageStats?.source_distribution && Object.entries(usageStats.source_distribution).map(([source, count]) => {
                    const total = Object.values(usageStats.source_distribution).reduce((a, b) => a + b, 0)
                    const percentage = total > 0 ? (count / total * 100).toFixed(1) : 0
                    
                    return (
                      <div key={source} className="flex items-center">
                        <div className="w-32 text-sm text-gray-600 capitalize">
                          {source.replace('_', ' ')}
                        </div>
                        <div className="flex-1 mx-4">
                          <div className="bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${percentage}%` }}
                            ></div>
                          </div>
                        </div>
                        <div className="w-16 text-sm text-gray-900 font-medium text-right">
                          {count} ({percentage}%)
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* System Health */}
              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Santé du Système</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Uptime</span>
                    <span className="text-sm font-medium text-gray-900">
                      {systemStats?.system_health.uptime_hours.toFixed(1)}h
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Taux d'erreur</span>
                    <span className={`text-sm font-medium ${systemStats?.system_health.error_rate && systemStats.system_health.error_rate < 5 ? 'text-green-600' : 'text-red-600'}`}>
                      {systemStats?.system_health.error_rate.toFixed(1)}%
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Cache Hit Rate</span>
                    <span className="text-sm font-medium text-green-600">
                      {performanceStats?.cache_hit_rate.toFixed(1)}%
                    </span>
                  </div>
                  
                  <div className="mt-4 pt-4 border-t">
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Services RAG</h4>
                    <div className="space-y-2">
                      {systemStats?.system_health.rag_status && Object.entries(systemStats.system_health.rag_status).map(([service, status]) => (
                        <div key={service} className="flex items-center justify-between">
                          <span className="text-xs text-gray-600 capitalize">{service}</span>
                          <span className={`text-xs px-2 py-1 rounded-full ${status ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {status ? 'Actif' : 'Inactif'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Tables Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Users */}
              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Utilisateurs les Plus Actifs</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left text-sm font-medium text-gray-600 pb-2">Utilisateur</th>
                        <th className="text-left text-sm font-medium text-gray-600 pb-2">Questions</th>
                        <th className="text-left text-sm font-medium text-gray-600 pb-2">Plan</th>
                      </tr>
                    </thead>
                    <tbody>
                      {billingStats?.top_users.map((user, index) => (
                        <tr key={user.email} className="border-b border-gray-100">
                          <td className="py-3 text-sm text-gray-900">{user.email}</td>
                          <td className="py-3 text-sm text-gray-600">{user.question_count}</td>
                          <td className="py-3">
                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                              user.plan === 'enterprise' ? 'bg-purple-100 text-purple-800' :
                              user.plan === 'professional' ? 'bg-blue-100 text-blue-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {user.plan}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Plans Distribution */}
              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Répartition des Plans</h3>
                <div className="space-y-4">
                  {billingStats?.plans && Object.entries(billingStats.plans).map(([planName, data]) => (
                    <div key={planName} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <p className="text-sm font-medium text-gray-900 capitalize">{planName}</p>
                        <p className="text-xs text-gray-600">{data.user_count} utilisateurs</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-gray-900">${data.revenue}</p>
                        <p className="text-xs text-gray-600">revenus</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Costs Section */}
            <div className="mt-8 bg-white p-6 rounded-lg shadow-sm border">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Coûts et Performance</h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="text-center">
                  <p className="text-2xl font-bold text-red-600">${performanceStats?.openai_costs.toFixed(2)}</p>
                  <p className="text-sm text-gray-600">Coûts OpenAI</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-yellow-600">{performanceStats?.error_count}</p>
                  <p className="text-sm text-gray-600">Erreurs</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-green-600">{systemStats?.system_health.total_requests}</p>
                  <p className="text-sm text-gray-600">Requêtes Totales</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-blue-600">{usageStats?.questions_today}</p>
                  <p className="text-sm text-gray-600">Questions Aujourd'hui</p>
                </div>
              </div>
            </div>
          </>
        ) : (
          /* Questions & Réponses Tab */
          <div className="space-y-6">
            {/* Filtres */}
            <div className="bg-white p-6 rounded-lg shadow-sm border">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Filtres et Recherche</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Recherche</label>
                  <input
                    type="text"
                    value={questionFilters.search}
                    onChange={(e) => setQuestionFilters(prev => ({ ...prev, search: e.target.value }))}
                    placeholder="Rechercher dans questions/réponses..."
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Source</label>
                  <select
                    value={questionFilters.source}
                    onChange={(e) => setQuestionFilters(prev => ({ ...prev, source: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="all">Toutes les sources</option>
                    <option value="rag_retriever">RAG Retriever</option>
                    <option value="openai_fallback">OpenAI Fallback</option>
                    <option value="perfstore">PerfStore</option>
                    <option value="agricultural_validator">Validator</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Confiance</label>
                  <select
                    value={questionFilters.confidence}
                    onChange={(e) => setQuestionFilters(prev => ({ ...prev, confidence: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="all">Tous niveaux</option>
                    <option value="high">Élevée (≥90%)</option>
                    <option value="medium">Moyenne (70-89%)</option>
                    <option value="low">Faible (&lt;70%)</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Feedback</label>
                  <select
                    value={questionFilters.feedback}
                    onChange={(e) => setQuestionFilters(prev => ({ ...prev, feedback: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="all">Tous feedback</option>
                    <option value="positive">Positif 👍</option>
                    <option value="negative">Négatif 👎</option>
                    <option value="none">Aucun feedback</option>
                    <option value="with_comments">Avec commentaires 💬</option>
                    <option value="no_comments">Sans commentaires</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Utilisateur</label>
                  <select
                    value={questionFilters.user}
                    onChange={(e) => setQuestionFilters(prev => ({ ...prev, user: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="all">Tous utilisateurs</option>
                    {uniqueUsers.map(email => (
                      <option key={email} value={email}>{email}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Période</label>
                  <select
                    value={selectedTimeRange}
                    onChange={(e) => setSelectedTimeRange(e.target.value as any)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="day">Aujourd'hui</option>
                    <option value="week">Cette semaine</option>
                    <option value="month">Ce mois</option>
                    <option value="year">Cette année</option>
                  </select>
                </div>
              </div>
              
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-gray-600">
                  {filteredQuestions.length} question(s) trouvée(s) sur {questionLogs.length} au total
                </p>
                <button
                  onClick={() => {
                    setQuestionFilters({
                      search: '',
                      source: 'all',
                      confidence: 'all',
                      feedback: 'all',
                      user: 'all'
                    })
                    setCurrentPage(1)
                  }}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  Réinitialiser les filtres
                </button>
              </div>
            </div>

            {/* Section Analyse des Commentaires */}
            <div className="bg-white p-6 rounded-lg shadow-sm border">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">📝 Analyse des Commentaires de Feedback</h3>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Statistiques des commentaires */}
                <div>
                  <h4 className="text-md font-medium text-gray-800 mb-3">Statistiques Générales</h4>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Total des feedback:</span>
                      <span className="font-medium">{questionLogs.filter(q => q.feedback !== null).length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Avec commentaires:</span>
                      <span className="font-medium">{questionLogs.filter(q => q.feedback_comment).length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Feedback positifs:</span>
                      <span className="font-medium text-green-600">{questionLogs.filter(q => q.feedback === 1).length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Feedback négatifs:</span>
                      <span className="font-medium text-red-600">{questionLogs.filter(q => q.feedback === -1).length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Taux de satisfaction:</span>
                      <span className="font-medium">
                        {questionLogs.filter(q => q.feedback !== null).length > 0 ? 
                          ((questionLogs.filter(q => q.feedback === 1).length / 
                            questionLogs.filter(q => q.feedback !== null).length) * 100).toFixed(1) + '%' 
                          : '0%'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Commentaires récents */}
                <div>
                  <h4 className="text-md font-medium text-gray-800 mb-3">Commentaires Récents</h4>
                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {questionLogs
                      .filter(q => q.feedback_comment)
                      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                      .slice(0, 5)
                      .map((question) => (
                        <div key={question.id} className="border border-gray-200 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs text-gray-500">{question.user_email}</span>
                            <span className="text-lg">{getFeedbackIcon(question.feedback)}</span>
                          </div>
                          <p className="text-sm text-gray-700 italic">"{question.feedback_comment}"</p>
                          <p className="text-xs text-gray-500 mt-1">
                            {new Date(question.timestamp).toLocaleDateString('fr-FR')}
                          </p>
                        </div>
                      ))}
                    
                    {questionLogs.filter(q => q.feedback_comment).length === 0 && (
                      <p className="text-sm text-gray-500 italic">Aucun commentaire disponible</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Bouton pour exporter les commentaires */}
              <div className="mt-6 pt-4 border-t border-gray-200">
                <button
                  onClick={() => {
                    const commentsData = questionLogs
                      .filter(q => q.feedback_comment)
                      .map(q => ({
                        date: new Date(q.timestamp).toLocaleDateString('fr-FR'),
                        user: q.user_email,
                        question: q.question.substring(0, 100) + '...',
                        feedback: q.feedback === 1 ? 'Positif' : 'Négatif',
                        comment: q.feedback_comment,
                        source: q.response_source,
                        confidence: (q.confidence_score * 100).toFixed(1) + '%'
                      }))
                    
                    const csvContent = "data:text/csv;charset=utf-8," + 
                      "Date,Utilisateur,Question,Feedback,Commentaire,Source,Confiance\n" +
                      commentsData.map(row => 
                        Object.values(row).map(field => `"${field}"`).join(',')
                      ).join('\n')
                    
                    const encodedUri = encodeURI(csvContent)
                    const link = document.createElement("a")
                    link.setAttribute("href", encodedUri)
                    link.setAttribute("download", `commentaires_feedback_${new Date().toISOString().split('T')[0]}.csv`)
                    document.body.appendChild(link)
                    link.click()
                    document.body.removeChild(link)
                  }}
                  className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors text-sm"
                >
                  📊 Exporter les Commentaires (CSV)
                </button>
              </div>
            </div>

            {/* Liste des Questions */}
            <div className="bg-white rounded-lg shadow-sm border">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Questions et Réponses</h3>
              </div>
              
              <div className="divide-y divide-gray-200">
                {paginatedQuestions.map((question) => (
                  <div key={question.id} className="p-6 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        {/* En-tête de la question */}
                        <div className="flex items-center space-x-3 mb-3">
                          <div className="flex-shrink-0">
                            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                              <span className="text-blue-600 text-sm font-medium">
                                {question.user_name.split(' ').map(n => n[0]).join('').toUpperCase()}
                              </span>
                            </div>
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-gray-900">{question.user_name}</p>
                            <p className="text-xs text-gray-500">{question.user_email}</p>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getSourceColor(question.response_source)}`}>
                              {question.response_source.replace('_', ' ')}
                            </span>
                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(question.confidence_score)}`}>
                              {(question.confidence_score * 100).toFixed(0)}%
                            </span>
                            <span className="text-lg" title={`Feedback: ${question.feedback === 1 ? 'Positif' : question.feedback === -1 ? 'Négatif' : 'Aucun'}`}>
                              {getFeedbackIcon(question.feedback)}
                            </span>
                            {/* 💬 NOUVEAU: Indicateur de commentaire */}
                            {question.feedback_comment && (
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800 border border-purple-300" title="Contient un commentaire détaillé">
                                💬 Commentaire
                              </span>
                            )}
                          </div>
                        </div>
                        
                        {/* Question */}
                        <div className="mb-4">
                          <p className="text-sm font-medium text-gray-900 mb-2">❓ Question:</p>
                          <p className="text-sm text-gray-700 bg-blue-50 p-3 rounded-md">
                            {question.question}
                          </p>
                        </div>
                        
                        {/* Réponse */}
                        <div className="mb-4">
                          <p className="text-sm font-medium text-gray-900 mb-2">💬 Réponse:</p>
                          <div className="text-sm text-gray-700 bg-gray-50 p-3 rounded-md max-h-40 overflow-y-auto">
                            {question.response.split('\n').map((line, index) => (
                              <p key={index} className={line.startsWith('**') ? 'font-semibold' : ''}>
                                {line}
                              </p>
                            ))}
                          </div>
                        </div>
                        
                        {/* Métadonnées */}
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <div className="flex items-center space-x-4">
                            <span>🕒 {new Date(question.timestamp).toLocaleString('fr-FR')}</span>
                            <span>⚡ {question.response_time}s</span>
                            <span>🌐 {question.language.toUpperCase()}</span>
                            <span>🔗 {question.session_id}</span>
                          </div>
                          <button
                            onClick={() => setSelectedQuestion(question)}
                            className="text-blue-600 hover:text-blue-800 font-medium"
                          >
                            Voir détails →
                          </button>
                        </div>
                        
                        {/* Commentaire de feedback */}
                        {question.feedback_comment && (
                          <div className="mt-3 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-400 rounded-r-lg">
                            <div className="flex items-start space-x-3">
                              <div className="flex-shrink-0">
                                <span className="text-2xl">{getFeedbackIcon(question.feedback)}</span>
                              </div>
                              <div className="flex-1">
                                <p className="text-sm font-medium text-blue-900 mb-1">Commentaire utilisateur:</p>
                                <p className="text-sm text-blue-800 italic leading-relaxed">
                                  "{question.feedback_comment}"
                                </p>
                                <p className="text-xs text-blue-600 mt-2">
                                  Feedback {question.feedback === 1 ? 'positif' : 'négatif'} • {new Date(question.timestamp).toLocaleDateString('fr-FR')}
                                </p>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                      className="px-3 py-1 border rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Précédent
                    </button>
                    <span className="text-sm text-gray-600">
                      Page {currentPage} sur {totalPages}
                    </span>
                    <button
                      onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                      disabled={currentPage === totalPages}
                      className="px-3 py-1 border rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Suivant
                    </button>
                  </div>
                  <div className="text-sm text-gray-600">
                    Affichage de {(currentPage - 1) * questionsPerPage + 1} à {Math.min(currentPage * questionsPerPage, filteredQuestions.length)} sur {filteredQuestions.length}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Modal de détail de question */}
        {selectedQuestion && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-gray-200 flex items-center justify-between">
                <h3 className="text-xl font-semibold text-gray-900">Détails de la Question</h3>
                <button
                  onClick={() => setSelectedQuestion(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="p-6 space-y-6">
                {/* Informations utilisateur */}
                <div>
                  <h4 className="text-lg font-medium text-gray-900 mb-3">👤 Utilisateur</h4>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p><span className="font-medium">Nom:</span> {selectedQuestion.user_name}</p>
                    <p><span className="font-medium">Email:</span> {selectedQuestion.user_email}</p>
                    <p><span className="font-medium">Session:</span> {selectedQuestion.session_id}</p>
                    <p><span className="font-medium">Timestamp:</span> {new Date(selectedQuestion.timestamp).toLocaleString('fr-FR')}</p>
                  </div>
                </div>
                
                {/* Question complète */}
                <div>
                  <h4 className="text-lg font-medium text-gray-900 mb-3">❓ Question</h4>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <p className="text-gray-800">{selectedQuestion.question}</p>
                  </div>
                </div>
                
                {/* Réponse complète */}
                <div>
                  <h4 className="text-lg font-medium text-gray-900 mb-3">💬 Réponse Complète</h4>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <pre className="text-gray-800 whitespace-pre-wrap font-sans text-sm">
                      {selectedQuestion.response}
                    </pre>
                  </div>
                </div>
                
                {/* Métriques */}
                <div>
                  <h4 className="text-lg font-medium text-gray-900 mb-3">📊 Métriques</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-gray-50 p-3 rounded-lg text-center">
                      <p className="text-sm text-gray-600">Source</p>
                      <p className="font-medium">{selectedQuestion.response_source.replace('_', ' ')}</p>
                    </div>
                    <div className="bg-gray-50 p-3 rounded-lg text-center">
                      <p className="text-sm text-gray-600">Confiance</p>
                      <p className="font-medium">{(selectedQuestion.confidence_score * 100).toFixed(1)}%</p>
                    </div>
                    <div className="bg-gray-50 p-3 rounded-lg text-center">
                      <p className="text-sm text-gray-600">Temps de réponse</p>
                      <p className="font-medium">{selectedQuestion.response_time}s</p>
                    </div>
                    <div className="bg-gray-50 p-3 rounded-lg text-center">
                      <p className="text-sm text-gray-600">Langue</p>
                      <p className="font-medium">{selectedQuestion.language.toUpperCase()}</p>
                    </div>
                  </div>
                </div>
                
                {/* Feedback */}
                <div>
                  <h4 className="text-lg font-medium text-gray-900 mb-3">💭 Feedback Utilisateur</h4>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="flex items-center space-x-3 mb-3">
                      <span className="text-2xl">{getFeedbackIcon(selectedQuestion.feedback)}</span>
                      <span className="font-medium">
                        {selectedQuestion.feedback === 1 ? 'Feedback Positif' : 
                         selectedQuestion.feedback === -1 ? 'Feedback Négatif' : 
                         'Aucun feedback'}
                      </span>
                    </div>
                    {selectedQuestion.feedback_comment && (
                      <div className="bg-white p-3 rounded border">
                        <p className="text-sm text-gray-700">{selectedQuestion.feedback_comment}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}