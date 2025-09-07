import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useAuthStore } from '@/lib/stores/auth' 
import { apiClient } from '@/lib/api/client'
import { StatisticsDashboard } from './StatisticsDashboard'
import { QuestionsTab } from './QuestionsTab'
import { InvitationStatsComponent } from './InvitationStats'

// Hook personnalisé pour l'authentification robuste (inspiré d'InviteFriendModal)
const useRobustAuth = () => {
  const { user } = useAuthStore()
  
  return useMemo(() => {
    // Priorité 1: Store Zustand
    if (user?.email && user?.user_type) {
      console.log('[useRobustAuth] Utilisateur trouvé dans le store:', user.email, user.user_type)
      return user
    }
    
    // Priorité 2: Fallback localStorage/sessionStorage (comme InviteFriendModal)
    try {
      const authKeys = ['intelia-expert-auth', 'supabase.auth.token']
      
      for (const key of authKeys) {
        const stored = localStorage.getItem(key) || sessionStorage.getItem(key)
        if (stored) {
          const authData = JSON.parse(stored)
          
          let userEmail, userName, userId, userType
          
          // Format Intelia
          if (authData.access_token && authData.user) {
            userEmail = authData.user.email
            userName = authData.user.name || userEmail.split('@')[0]
            userId = authData.user.id
            userType = authData.user.user_type
            
            console.log('[useRobustAuth] Utilisateur trouvé dans localStorage (Intelia):', userEmail, userType)
          }
          // Format Supabase
          else if (authData.user?.email) {
            userEmail = authData.user.email
            userName = authData.user.user_metadata?.name || authData.user.name || userEmail.split('@')[0]
            userId = authData.user.id
            userType = authData.user.user_metadata?.user_type || authData.user.user_type
            
            console.log('[useRobustAuth] Utilisateur trouvé dans localStorage (Supabase):', userEmail, userType)
          }
          
          if (userEmail && userType) {
            return {
              email: userEmail,
              name: userName,
              id: userId,
              user_type: userType
            }
          }
        }
      }
    } catch (e) {
      console.warn('[useRobustAuth] Erreur récupération auth fallback:', e)
    }
    
    console.log('[useRobustAuth] Aucun utilisateur trouvé')
    return null
  }, [user])
}

// Types pour le système de cache ultra-rapide
interface CacheStatus {
  is_available: boolean
  last_update: string | null
  cache_age_minutes: number
  performance_gain: string | number
  next_update: string | null
}

interface FastDashboardStats {
  cache_info: CacheStatus
  system_stats: SystemStats
  usage_stats: UsageStats
  billing_stats: BillingStats
  performance_stats: PerformanceStats
  systemStats?: SystemStats
  usageStats?: UsageStats
  billingStats?: BillingStats
  performanceStats?: PerformanceStats & { performance_gain: number }
}

interface FastQuestionsResponse {
  cache_info: CacheStatus
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

interface FastInvitationStats {
  cache_info: CacheStatus
  invitation_stats: InvitationStats
}

// Interface pour les données d'invitation depuis l'endpoint global-enhanced
interface GlobalInvitationStats {
  total_invitations: number
  total_accepted: number
  total_pending: number
  global_acceptance_rate: number
  active_inviters: number
  unique_inviters: number
  top_inviters_by_sent: Array<{
    inviter_email: string
    inviter_name: string
    invitations_sent: number
    invitations_accepted: number
    acceptance_rate: number
  }>
  top_inviters_by_accepted: Array<{
    inviter_email: string
    inviter_name: string
    invitations_sent: number
    invitations_accepted: number
    acceptance_rate: number
  }>
}

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
  median_response_time: number
  min_response_time: number
  max_response_time: number
  response_time_count: number
  openai_costs: number
  error_count: number
  cache_hit_rate: number
  performance_gain?: number
}

interface InvitationStats {
  total_invitations_sent: number
  total_invitations_accepted: number
  acceptance_rate: number
  unique_inviters: number
  top_inviters: Array<{
    inviter_email: string
    inviter_name: string
    invitations_sent: number
    invitations_accepted: number
    acceptance_rate: number
  }>
  top_accepted: Array<{
    inviter_email: string
    inviter_name: string
    invitations_accepted: number
    invitations_sent: number
    acceptance_rate: number
  }>
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
  session_id: string
  feedback: number | null
  feedback_comment: string | null
}

export const StatisticsPage: React.FC = () => {
  const currentUser = useRobustAuth() // Utilise le nouveau hook robuste
  
  const [authStatus, setAuthStatus] = useState<'initializing' | 'checking' | 'ready' | 'unauthorized' | 'forbidden'>('initializing')
  const [statsLoading, setStatsLoading] = useState(false)
  const [questionsLoading, setQuestionsLoading] = useState(false)
  const [invitationLoading, setInvitationLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // États pour le cache ultra-rapide - SÉPARÉS par onglet
  const [dashboardCacheStatus, setDashboardCacheStatus] = useState<CacheStatus | null>(null)
  const [questionsCacheStatus, setQuestionsCacheStatus] = useState<CacheStatus | null>(null)  
  const [invitationCacheStatus, setInvitationCacheStatus] = useState<CacheStatus | null>(null)
  const [performanceGain, setPerformanceGain] = useState<string>('')
  
  // États pour les données
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [billingStats, setBillingStats] = useState<BillingStats | null>(null)
  const [performanceStats, setPerformanceStats] = useState<PerformanceStats | null>(null)
  const [invitationStats, setInvitationStats] = useState<InvitationStats | null>(null)
  const [questionLogs, setQuestionLogs] = useState<QuestionLog[]>([])
  const [totalQuestions, setTotalQuestions] = useState(0)
  
  // États UI
  const [selectedTimeRange, setSelectedTimeRange] = useState<'day' | 'week' | 'month' | 'year'>('month')
  const [activeTab, setActiveTab] = useState<'dashboard' | 'questions' | 'invitations'>('dashboard')
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
  
  // Références pour éviter les chargements multiples
  const authCheckRef = useRef<boolean>(false)
  const stabilityCounterRef = useRef<number>(0)
  const dashboardLoadedRef = useRef<boolean>(false)
  const questionsLoadedRef = useRef<Map<string, boolean>>(new Map())
  const invitationsLoadedRef = useRef<boolean>(false)

  // 🔧 FIX: Reset forcé des références à chaque mount
  useEffect(() => {
    console.log('[StatisticsPage] 🔧 RESET forcé des références au mount')
    dashboardLoadedRef.current = false
    authCheckRef.current = false
    stabilityCounterRef.current = 0
    questionsLoadedRef.current.clear()
    invitationsLoadedRef.current = false
  }, [])

  // 🔧 FIX: Logique d'authentification simplifiée
  useEffect(() => {
    console.log('[StatisticsPage] 🔧 Auth check simplifié:', { 
      hasUser: !!currentUser,
      email: currentUser?.email,
      userType: currentUser?.user_type
    })

    if (currentUser === undefined) {
      console.log('[StatisticsPage] Initialisation auth...')
      setAuthStatus('initializing')
    } else if (currentUser === null) {
      console.log('[StatisticsPage] Utilisateur non connecté')
      setAuthStatus('unauthorized')
      setError("Vous devez être connecté pour accéder à cette page")
    } else if (currentUser.user_type !== 'super_admin') {
      console.log('[StatisticsPage] Permissions insuffisantes:', currentUser.user_type)
      setAuthStatus('forbidden')
      setError("Accès refusé - Permissions super_admin requises")
    } else {
      console.log('[StatisticsPage] Authentification réussie:', currentUser.email)
      setAuthStatus('ready')
      setError(null)
    }
  }, [currentUser])

  // 🔧 FIX: Chargement des statistiques avec condition simplifiée
  useEffect(() => {
    if (authStatus === 'ready' && !statsLoading && !systemStats) {
      console.log('[StatisticsPage] 🔧 Lancement chargement des statistiques (condition simplifiée)')
      loadAllStatistics()
    }
  }, [authStatus, statsLoading, systemStats])

  // Chargement des questions - SEULEMENT SI NÉCESSAIRE
  useEffect(() => {
    if (authStatus === 'ready' && activeTab === 'questions' && !questionsLoading) {
      const pageKey = `${currentPage}-${questionsPerPage}`
      if (!questionsLoadedRef.current.get(pageKey)) {
        console.log('[StatisticsPage] Lancement chargement des questions pour page:', pageKey)
        questionsLoadedRef.current.set(pageKey, true)
        loadQuestionLogs()
      }
    }
  }, [authStatus, activeTab, currentPage])

  // Chargement des invitations - UNE SEULE FOIS PAR VISITE
  useEffect(() => {
    if (authStatus === 'ready' && activeTab === 'invitations' && !invitationLoading && !invitationsLoadedRef.current) {
      console.log('[StatisticsPage] Lancement chargement des invitations')
      invitationsLoadedRef.current = true
      loadInvitationStats()
    }
  }, [authStatus, activeTab])

  // Reset des références quand on change d'onglet
  const handleTabChange = (newTab: 'dashboard' | 'questions' | 'invitations') => {
    if (newTab !== activeTab) {
      console.log('[StatisticsPage] Changement onglet:', activeTab, '->', newTab)
      
      // Reset seulement si nécessaire
      if (newTab === 'questions') {
        questionsLoadedRef.current.clear()
      }
      
      setActiveTab(newTab)
    }
  }

  // MÉTHODE CORRIGÉE: Utilisation d'apiClient.getSecure avec debug amélioré
  const loadAllStatistics = async () => {
    if (statsLoading) {
      console.log('[StatisticsPage] Chargement déjà en cours, annulation...')
      return
    }
    
    console.log('[StatisticsPage] DÉBUT chargement statistiques avec utilisateur:', currentUser?.email)
    setStatsLoading(true)
    setError(null)

    const startTime = performance.now()

    try {
      // Vérification manuelle du token avant l'appel API
      const authToken = localStorage.getItem('intelia-expert-auth')
      console.log('[StatisticsPage] Token disponible dans localStorage:', !!authToken)
      
      console.log('[StatisticsPage] DEBUG: baseURL from apiClient:', apiClient.getBaseURL())
      console.log('⚡ Tentative endpoint cache via apiClient: stats-fast/dashboard')
      
      // CORRECTION: Utilise apiClient.getSecure() au lieu de apiClient.get()
      const response = await apiClient.getSecure<FastDashboardStats>('stats-fast/dashboard')
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Erreur lors du chargement des statistiques')
      }

      if (!response.data) {
        throw new Error('Réponse vide du serveur')
      }

      const fastData = response.data
      console.log('🎉 SUCCÈS endpoint avec apiClient!', fastData)
      
      const loadTime = performance.now() - startTime
      console.log(`⚡ Performance: ${loadTime.toFixed(0)}ms`)
      
      const performanceGainValue = fastData.performanceStats?.performance_gain || 
                                   fastData.performance_stats?.performance_gain || 
                                   fastData.cache_info?.performance_gain || 
                                   0
      
      const performanceGainString = typeof performanceGainValue === 'number' 
        ? `${performanceGainValue}%` 
        : performanceGainValue?.toString() || '0%'
      
      const updatedCacheStatus = {
        ...fastData.cache_info,
        performance_gain: performanceGainString
      }
      setDashboardCacheStatus(updatedCacheStatus)
      setPerformanceGain(`${loadTime.toFixed(0)}ms (vs ${performanceGainString})`)
      
      const systemStatsData = fastData.systemStats || fastData.system_stats
      const usageStatsData = fastData.usageStats || fastData.usage_stats  
      const billingStatsData = fastData.billingStats || fastData.billing_stats
      const performanceStatsData = fastData.performanceStats || fastData.performance_stats
      
      const safeSystemStats = systemStatsData ? {
        ...systemStatsData,
        system_health: systemStatsData.system_health ? {
          ...systemStatsData.system_health,
          error_rate: typeof systemStatsData.system_health.error_rate === 'string'
            ? parseFloat(systemStatsData.system_health.error_rate) || 0
            : (systemStatsData.system_health.error_rate || 0)
        } : systemStatsData.system_health
      } : null
      
      const safeBillingStats = billingStatsData ? {
        ...billingStatsData,
        total_revenue: typeof billingStatsData.total_revenue === 'string'
          ? parseFloat(billingStatsData.total_revenue) || 0
          : (billingStatsData.total_revenue || 0)
      } : null
      
      const safePerformanceStats = performanceStatsData ? {
        ...performanceStatsData,
        avg_response_time: typeof performanceStatsData.avg_response_time === 'string' 
          ? parseFloat(performanceStatsData.avg_response_time) || 0
          : (performanceStatsData.avg_response_time || 0),
        median_response_time: typeof performanceStatsData.median_response_time === 'string'
          ? parseFloat(performanceStatsData.median_response_time) || 0
          : (performanceStatsData.median_response_time || 0),
        min_response_time: typeof performanceStatsData.min_response_time === 'string'
          ? parseFloat(performanceStatsData.min_response_time) || 0
          : (performanceStatsData.min_response_time || 0),
        max_response_time: typeof performanceStatsData.max_response_time === 'string'
          ? parseFloat(performanceStatsData.max_response_time) || 0
          : (performanceStatsData.max_response_time || 0),
        response_time_count: typeof performanceStatsData.response_time_count === 'string'
          ? parseInt(performanceStatsData.response_time_count) || 0
          : (performanceStatsData.response_time_count || 0),
        openai_costs: typeof performanceStatsData.openai_costs === 'string'
          ? parseFloat(performanceStatsData.openai_costs) || 0
          : (performanceStatsData.openai_costs || 0),
        error_count: typeof performanceStatsData.error_count === 'string'
          ? parseInt(performanceStatsData.error_count) || 0
          : (performanceStatsData.error_count || 0),
        cache_hit_rate: typeof performanceStatsData.cache_hit_rate === 'string'
          ? parseFloat(performanceStatsData.cache_hit_rate) || 0
          : (performanceStatsData.cache_hit_rate || 0),
        performance_gain: typeof performanceStatsData.performance_gain === 'string'
          ? parseFloat(performanceStatsData.performance_gain) || 0
          : (performanceStatsData.performance_gain || 0)
      } : null
      
      setSystemStats(safeSystemStats)
      setUsageStats(usageStatsData)
      setBillingStats(safeBillingStats)
      setPerformanceStats(safePerformanceStats)
      
      console.log('✅ Toutes les statistiques chargées depuis le cache!')

    } catch (err) {
      console.error('❌ [StatisticsPage] Erreur chargement statistiques:', err)
      setError(`Erreur lors du chargement des statistiques: ${err}`)
      // 🔧 FIX: Ne plus reset dashboardLoadedRef.current, laisser la condition !systemStats gérer
    } finally {
      setStatsLoading(false)
    }
  }
	  
  // MÉTHODE CORRIGÉE: Charger les questions avec apiClient.getSecure
  const loadQuestionLogs = async () => {
    if (questionsLoading) {
      console.log('[Questions] Chargement déjà en cours, annulation...')
      return
    }
  
    console.log('⚡ [Questions] Chargement avec apiClient')
    setQuestionsLoading(true)
    const startTime = performance.now()
  
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: questionsPerPage.toString()
      })

      // CORRECTION: Utilise apiClient.getSecure() avec URL relative
      const response = await apiClient.getSecure<FastQuestionsResponse>(`stats-fast/questions?${params}`)
    
      if (!response.success) {
        throw new Error(response.error?.message || 'Erreur lors du chargement des questions')
      }

      if (!response.data) {
        throw new Error('Réponse vide du serveur')
      }

      const fastData = response.data
      console.log('🎉 Questions chargées avec apiClient!', fastData)
    
      const loadTime = performance.now() - startTime
      console.log(`⚡ Questions Performance: ${loadTime.toFixed(0)}ms`)
    
      // Utilise le cache_info depuis l'API
      const realCacheInfo = fastData.cache_info || {
        is_available: false,
        last_update: null,
        cache_age_minutes: 0,
        performance_gain: `${loadTime.toFixed(0)}ms`,
        next_update: null
      }
    
      // Enrichir avec le temps de chargement réel
      const enrichedCacheInfo = {
        ...realCacheInfo,
        performance_gain: realCacheInfo.is_available 
          ? realCacheInfo.performance_gain 
          : `${loadTime.toFixed(0)}ms (direct)`
      }
    
      setQuestionsCacheStatus(enrichedCacheInfo)

      const adaptedQuestions: QuestionLog[] = fastData.questions.map(q => ({
        id: q.id,
        timestamp: q.timestamp,
        user_email: q.user_email,
        user_name: q.user_name || (q.user_email || "").split('@')[0].replace('.', ' ').replace(/\b\w/g, l => l.toUpperCase()),
        question: q.question,
        response: q.response,
        response_source: mapResponseSource(q.response_source),
        confidence_score: q.confidence_score,
        response_time: q.response_time,
        language: q.language,
        session_id: q.session_id,
        feedback: q.feedback,
        feedback_comment: q.feedback_comment
      }))
      
      setQuestionLogs(adaptedQuestions)
      setTotalQuestions(fastData.pagination.total)
      
    } catch (err) {
      console.error('❌ Erreur chargement questions:', err)
      setError(`Erreur chargement questions: ${err}`)
      setQuestionLogs([])
      // Reset la référence pour permettre un retry
      const pageKey = `${currentPage}-${questionsPerPage}`
      questionsLoadedRef.current.delete(pageKey)
    } finally {
      setQuestionsLoading(false)
    }
  }

  // MÉTHODE CORRIGÉE: Charger les invitations avec l'endpoint fonctionnel
  const loadInvitationStats = async () => {
    if (invitationLoading) {
      console.log('[Invitations] Chargement déjà en cours, annulation...')
      return
    }
    
    console.log('⚡ [Invitations] Chargement avec apiClient - ENDPOINT CORRIGÉ')
    setInvitationLoading(true)
    setError(null)
    const startTime = performance.now()

    try {
      console.log('⚡ Utilisation endpoint fonctionnel: invitations/stats/global-enhanced')
      
      // CORRECTION: Utilise l'endpoint qui fonctionne réellement
      const response = await apiClient.getSecure<GlobalInvitationStats>('invitations/stats/global-enhanced')
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Erreur lors du chargement des invitations')
      }

      if (!response.data) {
        throw new Error('Réponse vide du serveur')
      }

      const globalData = response.data
      console.log('🎉 Invitations chargées avec endpoint fonctionnel!', globalData)
      
      const loadTime = performance.now() - startTime
      console.log(`⚡ Invitations Performance: ${loadTime.toFixed(0)}ms`)
      
      // Adapter les données au format attendu par le composant React
      const adaptedCacheStatus: CacheStatus = {
        is_available: false, // Pas de cache pour cet endpoint
        last_update: new Date().toISOString(),
        cache_age_minutes: 0,
        performance_gain: `${loadTime.toFixed(0)}ms (direct)`,
        next_update: null
      }
      
      const adaptedInvitationStats: InvitationStats = {
        total_invitations_sent: globalData.total_invitations,
        total_invitations_accepted: globalData.total_accepted,
        acceptance_rate: globalData.global_acceptance_rate,
        unique_inviters: globalData.unique_inviters,
        top_inviters: globalData.top_inviters_by_sent || [],
        top_accepted: globalData.top_inviters_by_accepted || []
      }
      
      setInvitationCacheStatus(adaptedCacheStatus)
      setInvitationStats(adaptedInvitationStats)

      console.log('✅ Données d\'invitations adaptées:', adaptedInvitationStats)

    } catch (err) {
      console.error('[StatisticsPage] Erreur chargement stats invitations:', err)
      setError(`Erreur lors du chargement des statistiques d'invitations: ${err}`)
      
      // Reset la référence pour permettre un retry
      invitationsLoadedRef.current = false
      
      setInvitationStats({
        total_invitations_sent: 0,
        total_invitations_accepted: 0,
        acceptance_rate: 0,
        unique_inviters: 0,
        top_inviters: [],
        top_accepted: []
      })
    } finally {
      setInvitationLoading(false)
    }
  }

  // Fonctions helpers - IDENTIQUES
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

  const getFeedbackIcon = (feedback: number | null): string => {
    if (feedback === 1) return '👍'
    if (feedback === -1) return '👎'
    return '❓'
  }

  // RENDU CONDITIONNEL - IDENTIQUE
  
  if (authStatus === 'initializing') {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Initialisation...</p>
        </div>
      </div>
    )
  }

  if (authStatus === 'checking') {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Vérification des permissions...</p>
          <p className="text-xs text-gray-400 mt-2">Stabilisation des données d'authentification</p>
        </div>
      </div>
    )
  }

  if (authStatus === 'unauthorized') {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white border border-gray-200 max-w-md w-full text-center p-8">
          <div className="text-red-600 text-6xl mb-4">🔒</div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Connexion requise</h2>
          <p className="text-gray-600 mb-6">Vous devez être connecté pour accéder à cette page.</p>
          <div className="flex space-x-3">
            <button
              onClick={() => window.location.href = '/login'}
              className="flex-1 bg-blue-600 text-white px-6 py-2 hover:bg-blue-700 transition-colors"
            >
              Se connecter
            </button>
            <button
              onClick={() => window.history.back()}
              className="flex-1 bg-gray-100 text-gray-700 px-6 py-2 hover:bg-gray-200 transition-colors border border-gray-300"
            >
              Retour
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (authStatus === 'forbidden') {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white border border-gray-200 max-w-md w-full text-center p-8">
          <div className="text-red-600 text-6xl mb-4">🚫</div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Accès refusé</h2>
          <p className="text-gray-600 mb-2">Cette page est réservée aux super administrateurs.</p>
          <p className="text-sm text-gray-500 mb-6">Votre rôle actuel : <span className="font-medium">{currentUser?.user_type || 'non défini'}</span></p>
          <button
            onClick={() => window.history.back()}
            className="w-full bg-blue-600 text-white px-6 py-2 hover:bg-blue-700 transition-colors"
          >
            Retour
          </button>
        </div>
      </div>
    )
  }

  // Chargement des données
  if (statsLoading && !systemStats) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement des statistiques...</p>
        </div>
      </div>
    )
  }

  // Erreur dans le chargement des données
  if (error && authStatus === 'ready' && !systemStats) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white border border-gray-200 max-w-md w-full text-center p-8">
          <div className="text-amber-600 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Erreur</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => {
              // 🔧 FIX: Reset seulement les données, pas les refs
              setSystemStats(null)
              setError(null)
              loadAllStatistics()
            }}
            className="w-full bg-blue-600 text-white px-6 py-2 hover:bg-blue-700 transition-colors"
          >
            Réessayer
          </button>
        </div>
      </div>
    )
  }

  // PAGE PRINCIPALE - AVEC GESTION CORRECTE DES ONGLETS
  return (
    <div className="min-h-screen bg-gray-100">
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-8">
              <div className="flex items-center">
                <img 
                  src="/images/logo.png" 
                  alt="Logo" 
                  className="h-8 w-auto"
                />
              </div>
              
              <div className="flex items-center space-x-8">
                <button
                  onClick={() => handleTabChange('dashboard')}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'dashboard' 
                      ? 'text-blue-600 border-b-2 border-blue-600' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Tableau de bord
                </button>
                <button
                  onClick={() => handleTabChange('questions')}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'questions' 
                      ? 'text-blue-600 border-b-2 border-blue-600' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Questions & Réponses
                </button>
                <button
                  onClick={() => handleTabChange('invitations')}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'invitations' 
                      ? 'text-blue-600 border-b-2 border-blue-600' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Invitations
                </button>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {activeTab === 'dashboard' && (
                <button
                  onClick={() => {
                    // 🔧 FIX: Reset seulement les données, pas les refs
                    setSystemStats(null)
                    setError(null)
                    loadAllStatistics()
                  }}
                  disabled={statsLoading}
                  className="bg-blue-600 text-white px-3 py-1 text-sm hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center space-x-1"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <span>{statsLoading ? 'Loading...' : 'Refresh'}</span>
                </button>
              )}

              {activeTab === 'questions' && (
                <button
                  onClick={() => {
                    questionsLoadedRef.current.clear()
                    loadQuestionLogs()
                  }}
                  disabled={questionsLoading}
                  className="bg-blue-600 text-white px-3 py-1 text-sm hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center space-x-1"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <span>{questionsLoading ? 'Loading...' : 'Refresh'}</span>
                </button>
              )}

              {activeTab === 'invitations' && (
                <button
                  onClick={() => {
                    invitationsLoadedRef.current = false
                    loadInvitationStats()
                  }}
                  disabled={invitationLoading}
                  className="bg-blue-600 text-white px-3 py-1 text-sm hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center space-x-1"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <span>{invitationLoading ? 'Loading...' : 'Refresh'}</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' ? (
          <StatisticsDashboard
            systemStats={systemStats}
            usageStats={usageStats}
            billingStats={billingStats}
            performanceStats={performanceStats}
            cacheStatus={dashboardCacheStatus ? {
              ...dashboardCacheStatus,
              performance_gain: typeof dashboardCacheStatus.performance_gain === 'string' 
                ? dashboardCacheStatus.performance_gain 
                : `${dashboardCacheStatus.performance_gain}%`
            } : null}
            isLoading={statsLoading}
          />
        ) : activeTab === 'questions' ? (
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
            cacheStatus={questionsCacheStatus ? {
              ...questionsCacheStatus,
              performance_gain: typeof questionsCacheStatus.performance_gain === 'string' 
                ? questionsCacheStatus.performance_gain 
                : `${questionsCacheStatus.performance_gain}%`
            } : null}
          />
        ) : activeTab === 'invitations' ? (
          <>
            {invitationLoading && !invitationStats ? (
              <div className="bg-white border border-gray-200 p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Chargement des statistiques d'invitations...</p>
              </div>
            ) : (
              <InvitationStatsComponent 
                invitationStats={invitationStats} 
                cacheStatus={invitationCacheStatus ? {
                  ...invitationCacheStatus,
                  performance_gain: typeof invitationCacheStatus.performance_gain === 'string' 
                    ? invitationCacheStatus.performance_gain 
                    : `${invitationCacheStatus.performance_gain}%`
                } : null}
                isLoading={invitationLoading}
              />
            )}
          </>
        ) : null}

        {/* Modal de détail de question */}
        {selectedQuestion && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-gray-200">
              <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <h3 className="text-base font-medium text-gray-900">Détails de la Question</h3>
                </div>
                <button
                  onClick={() => setSelectedQuestion(null)}
                  className="text-gray-400 hover:text-gray-600 p-1"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="p-4">
                <div className="space-y-4">
                  <div className="bg-blue-50 p-4 border border-blue-200">
                    <h4 className="font-medium text-gray-900 mb-2 flex items-center space-x-2">
                      <span>❓</span>
                      <span>Question:</span>
                    </h4>
                    <p className="text-gray-700">{selectedQuestion.question}</p>
                  </div>
                  
                  <div className="bg-gray-50 p-4 border border-gray-200">
                    <h4 className="font-medium text-gray-900 mb-2 flex items-center space-x-2">
                      <span>💬</span>
                      <span>Réponse:</span>
                    </h4>
                    <div className="text-gray-700 whitespace-pre-wrap">{selectedQuestion.response}</div>
                  </div>
                  
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="bg-white p-4 border border-gray-200">
                      <h4 className="font-medium text-gray-900 mb-3 flex items-center space-x-2">
                        <span>📊</span>
                        <span>Métadonnées:</span>
                      </h4>
                      <table className="w-full text-sm">
                        <tbody className="space-y-2">
                          <tr>
                            <td className="text-gray-600 py-1">Source:</td>
                            <td className="font-medium py-1">{selectedQuestion.response_source}</td>
                          </tr>
                          <tr>
                            <td className="text-gray-600 py-1">Confiance:</td>
                            <td className="font-medium py-1">{(selectedQuestion.confidence_score * 100).toFixed(1)}%</td>
                          </tr>
                          <tr>
                            <td className="text-gray-600 py-1">Temps:</td>
                            <td className="font-medium py-1">{selectedQuestion.response_time}s</td>
                          </tr>
                          <tr>
                            <td className="text-gray-600 py-1">Langue:</td>
                            <td className="font-medium py-1">{selectedQuestion.language}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    
                    <div className="bg-white p-4 border border-gray-200">
                      <h4 className="font-medium text-gray-900 mb-3 flex items-center space-x-2">
                        <span>👤</span>
                        <span>Utilisateur:</span>
                      </h4>
                      <table className="w-full text-sm">
                        <tbody className="space-y-2">
                          <tr>
                            <td className="text-gray-600 py-1">Email:</td>
                            <td className="font-medium py-1">{selectedQuestion.user_email}</td>
                          </tr>
                          <tr>
                            <td className="text-gray-600 py-1">Session:</td>
                            <td className="font-medium py-1">{selectedQuestion.session_id.substring(0, 12)}...</td>
                          </tr>
                          <tr>
                            <td className="text-gray-600 py-1">Date:</td>
                            <td className="font-medium py-1">{new Date(selectedQuestion.timestamp).toLocaleString('fr-FR')}</td>
                          </tr>
                          <tr>
                            <td className="text-gray-600 py-1">Feedback:</td>
                            <td className="text-lg py-1">{getFeedbackIcon(selectedQuestion.feedback)}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                  
                  {selectedQuestion.feedback_comment && (
                    <div className="bg-purple-50 p-4 border border-purple-200">
                      <h4 className="font-medium text-gray-900 mb-2 flex items-center space-x-2">
                        <span>💭</span>
                        <span>Commentaire:</span>
                      </h4>
                      <p className="text-gray-700 italic">"{selectedQuestion.feedback_comment}"</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}