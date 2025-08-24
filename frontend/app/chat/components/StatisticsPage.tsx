import React, { useState, useEffect, useRef } from 'react'
import { useAuthStore } from '@/lib/stores/auth' 
import { getSupabaseClient } from '@/lib/supabase/singleton'
import { StatisticsDashboard } from './StatisticsDashboard'
import { QuestionsTab } from './QuestionsTab'
import { InvitationStatsComponent } from './InvitationStats'

// 🚀 Types pour le système de cache ultra-rapide
interface CacheStatus {
  is_available: boolean
  last_update: string | null
  cache_age_minutes: number
  performance_gain: string | number  // 🔧 CORRECTION: Support string ET number
  next_update: string | null
}

interface FastDashboardStats {
  cache_info: CacheStatus
  system_stats: SystemStats
  usage_stats: UsageStats
  billing_stats: BillingStats
  performance_stats: PerformanceStats
  // 🚀 AJOUT: Support pour la nouvelle structure backend
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
  performance_gain?: number  // 🚀 AJOUT: Support optionnel performance_gain
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
  const { user } = useAuthStore() 
  
  const [authStatus, setAuthStatus] = useState<'initializing' | 'checking' | 'ready' | 'unauthorized' | 'forbidden'>('initializing')
  const [statsLoading, setStatsLoading] = useState(false)
  const [questionsLoading, setQuestionsLoading] = useState(false)
  const [invitationLoading, setInvitationLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // 🚀 États pour le cache ultra-rapide
  const [cacheStatus, setCacheStatus] = useState<CacheStatus | null>(null)
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
  
  // Référence pour éviter les vérifications multiples
  const authCheckRef = useRef<boolean>(false)
  const stabilityCounterRef = useRef<number>(0)

  // LOGIQUE D'AUTHENTIFICATION
  useEffect(() => {
    let timeoutId: NodeJS.Timeout

    const performAuthCheck = () => {
      if (authStatus === 'ready' && authCheckRef.current) {
        return
      }

      console.log('[StatisticsPage] Auth check (cache ultra-rapide):', { 
        user: user === undefined ? 'undefined' : user === null ? 'null' : 'defined',
        email: user?.email,
        user_type: user?.user_type,
        stabilityCounter: stabilityCounterRef.current,
        currentAuthStatus: authStatus
      })

      if (user === undefined) {
        console.log('[StatisticsPage] Phase 1: Attente initialisation auth (cache)...')
        setAuthStatus('initializing')
        stabilityCounterRef.current = 0
        return
      }

      if (user !== null && (!user.email || !user.user_type)) {
        console.log('[StatisticsPage] Phase 2: Données utilisateur incomplètes, attente (cache)...')
        setAuthStatus('checking')
        stabilityCounterRef.current = 0
        return
      }

      if (authStatus !== 'ready') {
        stabilityCounterRef.current++
      }

      if (stabilityCounterRef.current < 2 && authStatus !== 'ready') {
        console.log(`[StatisticsPage] Stabilisation (cache)... (${stabilityCounterRef.current}/2)`)
        setAuthStatus('checking')
        timeoutId = setTimeout(performAuthCheck, 150)
        return
      }

      if (user === null) {
        console.log('[StatisticsPage] Utilisateur non connecté (cache)')
        setAuthStatus('unauthorized')
        setError("Vous devez être connecté pour accéder à cette page")
        return
      }

      if (user.user_type !== 'super_admin') {
        console.log('[StatisticsPage] Permissions insuffisantes (cache):', user.user_type)
        setAuthStatus('forbidden')
        setError("Accès refusé - Permissions super_admin requises")
        return
      }

      if (!authCheckRef.current) {
        console.log('[StatisticsPage] Authentification réussie (cache ultra-rapide):', user.email)
        setAuthStatus('ready')
        setError(null)
        authCheckRef.current = true
      }
    }

    timeoutId = setTimeout(performAuthCheck, 50)

    return () => {
      if (timeoutId) clearTimeout(timeoutId)
    }
  }, [user, authStatus])

  // 🚀 Charger les statistiques avec le système de cache ultra-rapide
  useEffect(() => {
    if (authStatus === 'ready' && !statsLoading) {
      console.log('[StatisticsPage] Lancement chargement des statistiques (CACHE ULTRA-RAPIDE)')
      loadAllStatistics()
    }
  }, [authStatus, selectedTimeRange])

  // Charger les questions si nécessaire
  useEffect(() => {
    if (authStatus === 'ready' && activeTab === 'questions' && !questionsLoading) {
      console.log('[StatisticsPage] Lancement chargement des questions (CACHE ULTRA-RAPIDE)')
      loadQuestionLogs()
    }
  }, [authStatus, activeTab, currentPage])

  // Charger les invitations
  useEffect(() => {
    if (authStatus === 'ready' && activeTab === 'invitations' && !invitationLoading) {
      console.log('[StatisticsPage] Lancement chargement des invitations (CACHE ULTRA-RAPIDE)')
      loadInvitationStats()
    }
  }, [authStatus, activeTab])

  // FONCTION POUR RÉCUPÉRER LES HEADERS D'AUTHENTIFICATION
  const getAuthHeaders = async (): Promise<Record<string, string>> => {
    try {
      console.log('🔐 getAuthHeaders: Début...')
      
      try {
        const supabase = getSupabaseClient()
        console.log('🔐 getAuthHeaders: Supabase client récupéré')
        
        const { data: { session }, error } = await supabase.auth.getSession()
        console.log('🔐 getAuthHeaders: Session récupérée:', { 
          hasSession: !!session, 
          hasError: !!error,
          hasAccessToken: !!session?.access_token,
          errorMessage: error?.message
        })
        
        if (session?.access_token && !error) {
          console.log('✅ Token trouvé via Supabase getSession()')
          return {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json'
          }
        }
      } catch (supabaseError) {
        console.log('⚠️ Supabase getSession() échoué, essai cookies...')
      }
      
      console.log('🍪 Tentative récupération token depuis cookies...')
      const cookieToken = getCookieToken()
      if (cookieToken) {
        console.log('✅ Token trouvé dans cookies')
        return {
          'Authorization': `Bearer ${cookieToken}`,
          'Content-Type': 'application/json'
        }
      }
      
      console.error('❌ Aucun token trouvé (ni Supabase ni cookies)')
      return {}
      
    } catch (error) {
      console.error('❌ Erreur getAuthHeaders:', error)
      return {}
    }
  }

  // FONCTION HELPER POUR EXTRAIRE LE TOKEN DES COOKIES
  const getCookieToken = (): string | null => {
    try {
      const cookies = document.cookie.split(';')
      const sbCookie = cookies.find(cookie => 
        cookie.trim().startsWith('sb-cdrmjshmkdfwwtsfdvbl-auth-token=')
      )
      
      if (sbCookie) {
        const cookieValue = sbCookie.split('=')[1]
        const decodedValue = decodeURIComponent(cookieValue)
        const parsed = JSON.parse(decodedValue)
        
        if (parsed && parsed.access_token) {
          console.log('🍪 Token extrait des cookies avec succès')
          return parsed.access_token
        }
      }
      
      console.log('🍪 Pas de cookie Supabase trouvé')
      return null
    } catch (error) {
      console.error('❌ Erreur parsing cookie:', error)
      return null
    }
  }

  // 🚀 Charger toutes les statistiques avec le cache ultra-rapide
  const loadAllStatistics = async () => {
    if (statsLoading) return
    
    console.log('🚀 [StatisticsPage] DÉBUT chargement statistiques ULTRA-RAPIDE')
    setStatsLoading(true)
    setError(null)

    const startTime = performance.now()

    try {
      const headers = await getAuthHeaders()

      console.log('⚡ Tentative endpoint cache ultra-rapide: /api/v1/stats-fast/dashboard')
      
      const fastResponse = await fetch('/api/v1/stats-fast/dashboard', { headers })
      
      if (!fastResponse.ok) {
        throw new Error(`Erreur cache endpoint: ${fastResponse.status} - ${fastResponse.statusText}`)
      }

      const fastData: FastDashboardStats = await fastResponse.json()
      console.log('🎉 SUCCÈS endpoint ultra-rapide!', fastData)
      
      const loadTime = performance.now() - startTime
      console.log(`⚡ Performance ULTRA-RAPIDE: ${loadTime.toFixed(0)}ms`)
      
      // 🔧 CORRECTION 2: Conversion sécurisée en string pour l'affichage
      const performanceGainValue = fastData.performanceStats?.performance_gain || 
                                   fastData.performance_stats?.performance_gain || 
                                   fastData.cache_info?.performance_gain || 
                                   0
      
      // Convertir en string pour compatibilité avec les composants existants
      const performanceGainString = typeof performanceGainValue === 'number' 
        ? `${performanceGainValue}%` 
        : performanceGainValue?.toString() || '0%'
      
      // Mettre à jour le statut du cache
      const updatedCacheStatus = {
        ...fastData.cache_info,
        performance_gain: performanceGainString  // Toujours string pour compatibilité
      }
      setCacheStatus(updatedCacheStatus)
      setPerformanceGain(`${loadTime.toFixed(0)}ms (vs ${performanceGainString})`)
      
      // 🚀 Support pour les deux structures de données (nouvelle et ancienne)
      const systemStatsData = fastData.systemStats || fastData.system_stats
      const usageStatsData = fastData.usageStats || fastData.usage_stats  
      const billingStatsData = fastData.billingStats || fastData.billing_stats
      const performanceStatsData = fastData.performanceStats || fastData.performance_stats
      
      // 🔧 CORRECTION: Conversion sécurisée des systemStats
      const safeSystemStats = systemStatsData ? {
        ...systemStatsData,
        system_health: systemStatsData.system_health ? {
          ...systemStatsData.system_health,
          error_rate: typeof systemStatsData.system_health.error_rate === 'string'
            ? parseFloat(systemStatsData.system_health.error_rate) || 0
            : (systemStatsData.system_health.error_rate || 0)
        } : systemStatsData.system_health
      } : null
      
      // 🔧 CORRECTION: Conversion sécurisée des billingStats  
      const safeBillingStats = billingStatsData ? {
        ...billingStatsData,
        total_revenue: typeof billingStatsData.total_revenue === 'string'
          ? parseFloat(billingStatsData.total_revenue) || 0
          : (billingStatsData.total_revenue || 0)
      } : null
      
      // 🔧 CORRECTION: Conversion sécurisée des strings en numbers pour éviter erreur toFixed
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
      
      // Utiliser les données mises en cache avec conversions sécurisées
      setSystemStats(safeSystemStats)
      setUsageStats(usageStatsData)
      setBillingStats(safeBillingStats)
      setPerformanceStats(safePerformanceStats)
      
      // 🔧 PROTECTION: Log des types pour debug
      console.log('🔍 Types de données après conversion:', {
        systemStats: safeSystemStats ? {
          error_rate: `${safeSystemStats.system_health?.error_rate} (${typeof safeSystemStats.system_health?.error_rate})`
        } : 'null',
        billingStats: safeBillingStats ? {
          total_revenue: `${safeBillingStats.total_revenue} (${typeof safeBillingStats.total_revenue})`
        } : 'null',
        performanceStats: safePerformanceStats ? {
          avg_response_time: `${safePerformanceStats.avg_response_time} (${typeof safePerformanceStats.avg_response_time})`,
          openai_costs: `${safePerformanceStats.openai_costs} (${typeof safePerformanceStats.openai_costs})`
        } : 'null'
      })
      
      console.log('✅ Toutes les statistiques chargées depuis le cache ultra-rapide!')

    } catch (err) {
      console.error('❌ [StatisticsPage] Erreur chargement statistiques:', err)
      setError(`Erreur lors du chargement des statistiques: ${err}`)
    } finally {
      setStatsLoading(false)
    }
  }

  // 🚀 Charger les questions avec le cache ultra-rapide  
  const loadQuestionLogs = async () => {
    if (questionsLoading) return
    
    console.log('⚡ [Questions] Chargement ULTRA-RAPIDE')
    setQuestionsLoading(true)
    const startTime = performance.now()
    
    try {
      const headers = await getAuthHeaders()
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: questionsPerPage.toString()
      })

      const fastResponse = await fetch(`/api/v1/stats-fast/questions?${params}`, { headers })
      
      if (!fastResponse.ok) {
        throw new Error(`Erreur cache questions: ${fastResponse.status} - ${fastResponse.statusText}`)
      }

      const fastData: FastQuestionsResponse = await fastResponse.json()
      console.log('🎉 Questions chargées depuis le cache ultra-rapide!', fastData)
      
      const loadTime = performance.now() - startTime
      console.log(`⚡ Questions Performance: ${loadTime.toFixed(0)}ms`)
      
      // Mettre à jour le statut du cache
      setCacheStatus(fastData.cache_info)
      
      // Adapter les données pour l'UI
      const adaptedQuestions: QuestionLog[] = fastData.questions.map(q => ({
        id: q.id,
        timestamp: q.timestamp,
        user_email: q.user_email,
        user_name: q.user_name,
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
    } finally {
      setQuestionsLoading(false)
    }
  }

  // 🚀 Charger les invitations avec le cache ultra-rapide
  const loadInvitationStats = async () => {
    console.log('⚡ [Invitations] Chargement ULTRA-RAPIDE')
    
    if (invitationLoading) return
    
    setInvitationLoading(true)
    setError(null)
    const startTime = performance.now()

    try {
      const headers = await getAuthHeaders()
      
      if (!headers || !('Authorization' in headers) || !headers.Authorization) {
        throw new Error('Pas de token d\'authentification disponible')
      }

      console.log('⚡ Tentative endpoint cache: /api/v1/stats-fast/invitations')
      
      const fastResponse = await fetch('/api/v1/stats-fast/invitations', { headers })
      
      if (!fastResponse.ok) {
        throw new Error(`Erreur cache invitations: ${fastResponse.status} - ${fastResponse.statusText}`)
      }

      const fastData: FastInvitationStats = await fastResponse.json()
      console.log('🎉 Invitations chargées depuis le cache ultra-rapide!', fastData)
      
      const loadTime = performance.now() - startTime
      console.log(`⚡ Invitations Performance: ${loadTime.toFixed(0)}ms`)
      
      // Mettre à jour le statut du cache
      setCacheStatus(fastData.cache_info)
      setInvitationStats(fastData.invitation_stats)

    } catch (err) {
      console.error('[StatisticsPage] Erreur chargement stats invitations:', err)
      setError(`Erreur lors du chargement des statistiques d'invitations: ${err}`)
      
      // Définir des stats par défaut en cas d'erreur
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

  // Fonctions helpers
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

  // RENDU CONDITIONNEL
  
  if (authStatus === 'initializing') {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Initialisation (cache ultra-rapide)...</p>
        </div>
      </div>
    )
  }

  if (authStatus === 'checking') {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Vérification des permissions (cache)...</p>
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
          <p className="text-sm text-gray-500 mb-6">Votre rôle actuel : <span className="font-medium">{user?.user_type || 'non défini'}</span></p>
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
          <p className="text-gray-600">Chargement des statistiques (cache ultra-rapide)...</p>
          <p className="text-xs text-gray-400 mt-2">⚡ Performance optimisée avec cache</p>
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
            onClick={loadAllStatistics}
            className="w-full bg-blue-600 text-white px-6 py-2 hover:bg-blue-700 transition-colors"
          >
            Réessayer
          </button>
        </div>
      </div>
    )
  }

  // PAGE PRINCIPALE - Header avec indicateurs de cache
  return (
    <div className="min-h-screen bg-gray-100">
      {/* 🚀 Header avec indicateurs de performance cache */}
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
                  onClick={() => setActiveTab('dashboard')}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'dashboard' 
                      ? 'text-blue-600 border-b-2 border-blue-600' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Tableau de bord
                </button>
                <button
                  onClick={() => setActiveTab('questions')}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'questions' 
                      ? 'text-blue-600 border-b-2 border-blue-600' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Questions & Réponses
                </button>
                <button
                  onClick={() => setActiveTab('invitations')}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'invitations' 
                      ? 'text-blue-600 border-b-2 border-blue-600' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  🔧 Invitations
                </button>
              </div>
              
              {/* 🚀 Indicateurs de performance cache */}
              {cacheStatus && (
                <div className="flex items-center space-x-3">
                  {cacheStatus.is_available ? (
                    <div className="flex items-center space-x-1 text-green-600">
                      <div className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></div>
                      <span className="text-xs font-medium">Cache Actif</span>
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                        {performanceGain}
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-1 text-red-600">
                      <div className="w-2 h-2 bg-red-600 rounded-full"></div>
                      <span className="text-xs font-medium">Cache Indisponible</span>
                    </div>
                  )}
                </div>
              )}
            </div>
            
            <div className="flex items-center space-x-4">
              {activeTab === 'dashboard' && (
                <button
                  onClick={loadAllStatistics}
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
                  onClick={loadQuestionLogs}
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
                  onClick={loadInvitationStats}
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
        
        {/* 🚀 Barre de statut cache détaillée */}
        {cacheStatus && cacheStatus.is_available && (
          <div className="bg-green-50 border-t border-green-200 px-4 py-2">
            <div className="max-w-7xl mx-auto flex items-center justify-between text-xs">
              <div className="flex items-center space-x-4">
                <span className="text-green-700">
                  📅 Dernière MÀJ: {cacheStatus.last_update ? new Date(cacheStatus.last_update).toLocaleString('fr-FR') : 'N/A'}
                </span>
                <span className="text-green-700">
                  ⏱️ Âge du cache: {cacheStatus.cache_age_minutes}min
                </span>
                <span className="text-green-700">
                  🚀 Gain: {typeof cacheStatus.performance_gain === 'string' ? cacheStatus.performance_gain : `${cacheStatus.performance_gain}%`}
                </span>
              </div>
              <div className="text-green-600">
                🔄 Prochaine MÀJ: {cacheStatus.next_update ? new Date(cacheStatus.next_update).toLocaleString('fr-FR') : 'Automatique'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' ? (
          <StatisticsDashboard
            systemStats={systemStats}
            usageStats={usageStats}
            billingStats={billingStats}
            performanceStats={performanceStats}
            cacheStatus={cacheStatus ? {
              ...cacheStatus,
              performance_gain: typeof cacheStatus.performance_gain === 'string' 
                ? cacheStatus.performance_gain 
                : `${cacheStatus.performance_gain}%`
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
            cacheStatus={cacheStatus ? {
              ...cacheStatus,
              performance_gain: typeof cacheStatus.performance_gain === 'string' 
                ? cacheStatus.performance_gain 
                : `${cacheStatus.performance_gain}%`
            } : null}
          />
        ) : activeTab === 'invitations' ? (
          <>
            {invitationLoading ? (
              <div className="bg-white border border-gray-200 p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Chargement des statistiques d'invitations...</p>
                <p className="text-xs text-gray-400 mt-2">⚡ Mode ultra-rapide</p>
              </div>
            ) : (
              <InvitationStatsComponent 
                invitationStats={invitationStats} 
                cacheStatus={cacheStatus ? {
                  ...cacheStatus,
                  performance_gain: typeof cacheStatus.performance_gain === 'string' 
                    ? cacheStatus.performance_gain 
                    : `${cacheStatus.performance_gain}%`
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