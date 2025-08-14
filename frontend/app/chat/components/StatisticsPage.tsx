import React, { useState, useEffect } from 'react'
import { useAuthStore } from '../hooks/useAuthStore'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { StatisticsDashboard } from './StatisticsDashboard'
import { QuestionsTab } from './QuestionsTab'

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
  
  // ✅ AMÉLIORATION : État d'authentification unifié
  const [authState, setAuthState] = useState<'loading' | 'authenticated' | 'unauthorized' | 'access_denied'>('loading')

  // ✅ AMÉLIORATION : Effet unifié pour gérer l'authentification
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Attendre un peu pour s'assurer que l'auth store est initialisé
        await new Promise(resolve => setTimeout(resolve, 100))
        
        if (user === null) {
          // Utilisateur pas connecté
          setAuthState('unauthorized')
          setError("Vous devez être connecté pour accéder à cette page")
          setLoading(false)
          return
        }
        
        if (user === undefined) {
          // Auth store encore en train de charger
          return
        }
        
        // Utilisateur connecté, vérifier les permissions
        if (user.user_type !== 'super_admin') {
          setAuthState('access_denied')
          setError("Accès refusé - Permissions super_admin requises")
          setLoading(false)
          return
        }
        
        // Tout est OK
        setAuthState('authenticated')
        console.log('✅ Utilisateur super_admin authentifié:', user.email)
        
      } catch (err) {
        console.error('Erreur vérification auth:', err)
        setAuthState('unauthorized')
        setError("Erreur de vérification d'authentification")
        setLoading(false)
      }
    }

    checkAuth()
  }, [user])

  // ✅ AMÉLIORATION : Charger les stats seulement quand authentifié
  useEffect(() => {
    if (authState === 'authenticated') {
      loadAllStatistics()
    }
  }, [authState, selectedTimeRange])

  // ✅ AMÉLIORATION : Charger les questions seulement quand authentifié
  useEffect(() => {
    if (authState === 'authenticated' && activeTab === 'questions') {
      loadQuestionLogs()
    }
  }, [authState, activeTab, questionFilters, currentPage])

  // Fonction pour récupérer les headers d'authentification
  const getAuthHeaders = async () => {
    try {
      const supabase = createClientComponentClient()
      
      const { data: { session }, error } = await supabase.auth.getSession()
      
      if (error || !session) {
        console.error('Erreur récupération session:', error)
        return {}
      }
      
      const token = session.access_token
      console.log('Token récupéré:', token ? 'OK' : 'MISSING')
      
      return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    } catch (error) {
      console.error('Erreur getAuthHeaders:', error)
      return {}
    }
  }

  const loadAllStatistics = async () => {
    console.log('🔄 Chargement des statistiques...')
    setLoading(true)
    setError(null)

    try {
      const headers = await getAuthHeaders()

      // Charger toutes les statistiques en parallèle
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
      const headers = await getAuthHeaders()

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

      // Essayer plusieurs endpoints pour récupérer les données réelles
      const endpointsToTry = [
        `/api/v1/logging/analytics/conversations-with-feedback?${params}`,
        `/api/v1/logging/analytics/questions?${params}`,
        `/api/v1/conversations/all-with-feedback?${params}`,
        `/api/v1/logging/analytics/user-interactions?${params}`
      ]

      let questionsLoaded = false

      for (const endpoint of endpointsToTry) {
        try {
          console.log(`Tentative endpoint: ${endpoint}`)
          const response = await fetch(endpoint, { headers })
          
          if (response.ok) {
            const data = await response.json()
            console.log(`Données récupérées via ${endpoint}:`, data)
            
            // Adapter selon la structure de réponse
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

            // Transformer les données si nécessaire
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
            console.log(`${transformedQuestions.length} questions chargées depuis ${endpoint}`)
            break

          } else {
            console.log(`${endpoint}: ${response.status} ${response.statusText}`)
          }
        } catch (err) {
          console.log(`Erreur ${endpoint}:`, err)
        }
      }

      // Si aucun endpoint ne fonctionne, utiliser des données mockées pour demo
      if (!questionsLoaded) {
        console.log('Aucun endpoint disponible, utilisation de données mockées')
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
        console.log('Données mockées chargées pour démo')
      }
    } catch (err) {
      console.error('Erreur générale lors du chargement des logs questions:', err)
      setQuestionLogs([])
    }
  }

  const getFeedbackIcon = (feedback: number | null) => {
    if (feedback === 1) return '👍'
    if (feedback === -1) return '👎'
    return '❓'
  }

  // ✅ AMÉLIORATION : États d'affichage plus clairs
  
  // État de chargement de l'authentification
  if (authState === 'loading') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Vérification des permissions...</p>
        </div>
      </div>
    )
  }

  // Utilisateur non connecté
  if (authState === 'unauthorized') {
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

  // Accès refusé (pas super_admin)
  if (authState === 'access_denied') {
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

  // Erreur dans le chargement des données
  if (error && authState === 'authenticated') {
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

  // ✅ PAGE PRINCIPALE - affiché seulement si authentifié et autorisé
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
              {/* ✅ AMÉLIORATION : Indicateur de statut utilisateur */}
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
                    <div className="bg-gray-50 p-3 rounded-lg text-center">
                      <p className="text-sm text-gray-600">Source</p>
                      <p className="font-medium">{selectedQuestion.response_source.replace('_', ' ')}</p>
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