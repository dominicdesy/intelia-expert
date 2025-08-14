import React, { useState, useEffect, useRef } from 'react'
import { useAuthStore } from '../hooks/useAuthStore'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { StatisticsDashboard } from './StatisticsDashboard'
import { QuestionsTab } from './QuestionsTab'

// Types pour les données de statistiques (identiques à avant)
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
  feedback: number | null
  feedback_comment: string | null
}

export const StatisticsPage: React.FC = () => {
  const { user } = useAuthStore()
  
  // 🚀 NOUVELLE APPROCHE : Utiliser un délai d'attente plus intelligent
  const [authStatus, setAuthStatus] = useState<'initializing' | 'checking' | 'ready' | 'unauthorized' | 'forbidden'>('initializing')
  const [statsLoading, setStatsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // États pour les données
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [billingStats, setBillingStats] = useState<BillingStats | null>(null)
  const [performanceStats, setPerformanceStats] = useState<PerformanceStats | null>(null)
  const [questionLogs, setQuestionLogs] = useState<QuestionLog[]>([])
  
  // États UI
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
  
  // Référence pour éviter les vérifications multiples
  const authCheckRef = useRef<boolean>(false)
  const stabilityCounterRef = useRef<number>(0)

  // 🚀 LOGIQUE D'AUTHENTIFICATION ULTRA-ROBUSTE
  useEffect(() => {
    let timeoutId: NodeJS.Timeout

    const performAuthCheck = () => {
      console.log('🔍 [StatisticsPage] Auth check:', { 
        user: user === undefined ? 'undefined' : user === null ? 'null' : 'defined',
        email: user?.email,
        user_type: user?.user_type,
        stabilityCounter: stabilityCounterRef.current
      })

      // Phase 1: Initialisation - attendre que user ne soit plus undefined
      if (user === undefined) {
        console.log('⏳ [StatisticsPage] Phase 1: Attente initialisation auth...')
        setAuthStatus('initializing')
        stabilityCounterRef.current = 0
        return
      }

      // Phase 2: Vérification - s'assurer que les données sont stables
      if (user !== null && (!user.email || !user.user_type)) {
        console.log('⏳ [StatisticsPage] Phase 2: Données utilisateur incomplètes, attente...')
        setAuthStatus('checking')
        stabilityCounterRef.current = 0
        return
      }

      // Incrémenter le compteur de stabilité
      stabilityCounterRef.current++

      // Attendre au moins 2 vérifications consécutives avec les mêmes données
      if (stabilityCounterRef.current < 2) {
        console.log(`⏳ [StatisticsPage] Stabilisation... (${stabilityCounterRef.current}/2)`)
        setAuthStatus('checking')
        // Programmer une nouvelle vérification
        timeoutId = setTimeout(performAuthCheck, 150)
        return
      }

      // Phase 3: Validation finale
      if (user === null) {
        console.log('❌ [StatisticsPage] Utilisateur non connecté')
        setAuthStatus('unauthorized')
        setError("Vous devez être connecté pour accéder à cette page")
        return
      }

      if (user.user_type !== 'super_admin') {
        console.log('🚫 [StatisticsPage] Permissions insuffisantes:', user.user_type)
        setAuthStatus('forbidden')
        setError("Accès refusé - Permissions super_admin requises")
        return
      }

      // Phase 4: Succès !
      if (!authCheckRef.current) {
        console.log('✅ [StatisticsPage] Authentification réussie:', user.email)
        setAuthStatus('ready')
        setError(null)
        authCheckRef.current = true
      }
    }

    // Démarrer la vérification avec un petit délai initial
    timeoutId = setTimeout(performAuthCheck, 50)

    return () => {
      if (timeoutId) clearTimeout(timeoutId)
    }
  }, [user])

  // Charger les statistiques uniquement quand tout est prêt
  useEffect(() => {
    if (authStatus === 'ready' && !statsLoading) {
      console.log('🔄 [StatisticsPage] Lancement chargement des statistiques')
      loadAllStatistics()
    }
  }, [authStatus, selectedTimeRange])

  // Charger les questions si nécessaire
  useEffect(() => {
    if (authStatus === 'ready' && activeTab === 'questions') {
      console.log('🔄 [StatisticsPage] Lancement chargement des questions')
      loadQuestionLogs()
    }
  }, [authStatus, activeTab, questionFilters, currentPage])

  // Fonction pour récupérer les headers d'authentification
  const getAuthHeaders = async () => {
    try {
      const supabase = createClientComponentClient()
      const { data: { session }, error } = await supabase.auth.getSession()
      
      if (error || !session) {
        console.error('Erreur récupération session:', error)
        return {}
      }
      
      return {
        'Authorization': `Bearer ${session.access_token}`,
        'Content-Type': 'application/json'
      }
    } catch (error) {
      console.error('Erreur getAuthHeaders:', error)
      return {}
    }
  }

  const loadAllStatistics = async () => {
    if (statsLoading) return // Éviter les chargements multiples
    
    console.log('📊 [StatisticsPage] Début chargement statistiques')
    setStatsLoading(true)
    setError(null)

    try {
      const headers = await getAuthHeaders()

      const [systemRes, usageRes, billingRes, performanceRes] = await Promise.allSettled([
        fetch('/api/admin/stats', { headers }),
        fetch('/api/v1/logging/analytics/dashboard', { headers }),
        fetch('/api/v1/billing/admin/stats', { headers }),
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
        // Mock data de fallback
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
        setPerformanceStats({
          avg_response_time: 1.8,
          openai_costs: 127.35,
          error_count: 12,
          cache_hit_rate: 85.2
        })
      }

      console.log('✅ [StatisticsPage] Statistiques chargées')
    } catch (err) {
      console.error('❌ [StatisticsPage] Erreur chargement statistiques:', err)
      setError('Erreur lors du chargement des statistiques')
    } finally {
      setStatsLoading(false)
    }
  }

  const loadQuestionLogs = async () => {
    try {
      const headers = await getAuthHeaders()
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

      // Données mockées pour la démo
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
        // ... autres questions mockées
      ]
      
      setQuestionLogs(mockQuestions)
    } catch (err) {
      console.error('Erreur chargement questions:', err)
      setQuestionLogs([])
    }
  }

  const getFeedbackIcon = (feedback: number | null) => {
    if (feedback === 1) return '👍'
    if (feedback === -1) return '👎'
    return '❓'
  }

  // 🎯 RENDU CONDITIONNEL ULTRA-SIMPLE
  
  // États de chargement/initialisation
  if (authStatus === 'initializing') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Initialisation...</p>
        </div>
      </div>
    )
  }

  if (authStatus === 'checking') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Vérification des permissions...</p>
          <p className="text-xs text-gray-400 mt-2">Stabilisation des données d'authentification</p>
        </div>
      </div>
    )
  }

  // États d'erreur
  if (authStatus === 'unauthorized') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full text-center">
          <div className="text-red-600 text-6xl mb-4">🔒</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Connexion requise</h2>
          <p className="text-gray-600 mb-6">Vous devez être connecté pour accéder à cette page.</p>
          <button
            onClick={() => window.location.href = '/login'}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors mr-3"
          >
            Se connecter
          </button>
          <button
            onClick={() => window.history.back()}
            className="bg-gray-600 text-white px-6 py-2 rounded-lg hover:bg-gray-700 transition-colors"
          >
            Retour
          </button>
        </div>
      </div>
    )
  }

  if (authStatus === 'forbidden') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full text-center">
          <div className="text-red-600 text-6xl mb-4">🚫</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Accès refusé</h2>
          <p className="text-gray-600 mb-2">Cette page est réservée aux super administrateurs.</p>
          <p className="text-sm text-gray-500 mb-6">Votre rôle actuel : {user?.user_type || 'non défini'}</p>
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

  // Chargement des données
  if (statsLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement des statistiques...</p>
        </div>
      </div>
    )
  }

  // Erreur dans le chargement des données
  if (error && authStatus === 'ready') {
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

  // 🎉 PAGE PRINCIPALE - ENFIN !
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
              <div className="text-sm text-gray-500">
                Connecté en tant que <span className="font-medium text-green-600">{user?.email}</span> 
                <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
                  {user?.user_type}
                </span>
              </div>
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
          <StatisticsDashboard
            systemStats={systemStats}
            usageStats={usageStats}
            billingStats={billingStats}
            performanceStats={performanceStats}
          />
        ) : (
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
          />
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
              
              <div className="p-6">
                <p className="text-center text-gray-500">Détails de la question sélectionnée s'afficheraient ici.</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}