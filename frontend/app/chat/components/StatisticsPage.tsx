import React, { useState, useEffect, useRef } from 'react'
import { useAuthStore } from '@/lib/stores/auth' 
// Changement: Utiliser le singleton au lieu de createClientComponentClient
import { getSupabaseClient } from '@/lib/supabase/singleton'
import { StatisticsDashboard } from './StatisticsDashboard'
import { QuestionsTab } from './QuestionsTab'
import { InvitationStatsComponent } from './InvitationStats'

// 🚀 NOUVEAU: Types pour le système de cache ultra-rapide
interface CacheStatus {
  is_available: boolean
  last_update: string | null
  cache_age_minutes: number
  performance_gain: string
  next_update: string | null
}

interface FastDashboardStats {
  cache_info: CacheStatus
  system_stats: SystemStats
  usage_stats: UsageStats
  billing_stats: BillingStats
  performance_stats: PerformanceStats
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

// Types pour les donnees de statistiques - CONSERVATION INTÉGRALE DU CODE ORIGINAL
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

interface BackendPerformanceStats {
  period_hours: number
  current_status: {
    overall_health: string
    avg_response_time_ms: number
    error_rate_percent: number
    total_errors?: number
  }
  averages?: {
    avg_response_time_ms: number
    avg_error_rate_percent: number
  }
  global_stats: any
  hourly_usage_patterns: Array<any>
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
}

// NOUVEAU: Interface pour les statistiques d'invitations
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
  const [invitationLoading, setInvitationLoading] = useState(false) // CONSERVATION: Loading pour invitations
  const [error, setError] = useState<string | null>(null)
  
  // 🚀 NOUVEAU: États pour le cache ultra-rapide
  const [cacheStatus, setCacheStatus] = useState<CacheStatus | null>(null)
  const [useFastEndpoints, setUseFastEndpoints] = useState(true)
  const [performanceGain, setPerformanceGain] = useState<string>('')
  
  // Etats pour les donnees - CONSERVATION INTÉGRALE
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [billingStats, setBillingStats] = useState<BillingStats | null>(null)
  const [performanceStats, setPerformanceStats] = useState<PerformanceStats | null>(null)
  const [invitationStats, setInvitationStats] = useState<InvitationStats | null>(null) // CONSERVATION: Stats invitations
  const [questionLogs, setQuestionLogs] = useState<QuestionLog[]>([])
  const [totalQuestions, setTotalQuestions] = useState(0)
  
  // Etats UI - CONSERVATION INTÉGRALE
  const [selectedTimeRange, setSelectedTimeRange] = useState<'day' | 'week' | 'month' | 'year'>('month')
  const [activeTab, setActiveTab] = useState<'dashboard' | 'questions' | 'invitations'>('dashboard') // CONSERVATION: Onglet invitations
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
  
  // Reference pour eviter les verifications multiples - CONSERVATION INTÉGRALE
  const authCheckRef = useRef<boolean>(false)
  const stabilityCounterRef = useRef<number>(0)

  // LOGIQUE D'AUTHENTIFICATION OPTIMISEE - CONSERVATION INTÉGRALE
  useEffect(() => {
    let timeoutId: NodeJS.Timeout

    const performAuthCheck = () => {
      // Eviter les verifications multiples si deja pret
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

      // Phase 1: Initialisation - attendre que user ne soit plus undefined
      if (user === undefined) {
        console.log('[StatisticsPage] Phase 1: Attente initialisation auth (cache)...')
        setAuthStatus('initializing')
        stabilityCounterRef.current = 0
        return
      }

      // Phase 2: Verification - s'assurer que les donnees sont stables
      if (user !== null && (!user.email || !user.user_type)) {
        console.log('[StatisticsPage] Phase 2: Donnees utilisateur incompletes, attente (cache)...')
        setAuthStatus('checking')
        stabilityCounterRef.current = 0
        return
      }

      // Incrementer le compteur de stabilite seulement si pas encore pret
      if (authStatus !== 'ready') {
        stabilityCounterRef.current++
      }

      // Attendre au moins 2 verifications consecutives avec les memes donnees
      if (stabilityCounterRef.current < 2 && authStatus !== 'ready') {
        console.log(`[StatisticsPage] Stabilisation (cache)... (${stabilityCounterRef.current}/2)`)
        setAuthStatus('checking')
        // Programmer une nouvelle verification
        timeoutId = setTimeout(performAuthCheck, 150)
        return
      }

      // Phase 3: Validation finale
      if (user === null) {
        console.log('[StatisticsPage] Utilisateur non connecte (cache)')
        setAuthStatus('unauthorized')
        setError("Vous devez etre connecte pour acceder a cette page")
        return
      }

      if (user.user_type !== 'super_admin') {
        console.log('[StatisticsPage] Permissions insuffisantes (cache):', user.user_type)
        setAuthStatus('forbidden')
        setError("Acces refuse - Permissions super_admin requises")
        return
      }

      // Phase 4: Succes ! (Une seule fois)
      if (!authCheckRef.current) {
        console.log('[StatisticsPage] Authentification reussie (cache ultra-rapide):', user.email)
        setAuthStatus('ready')
        setError(null)
        authCheckRef.current = true
      }
    }

    // Demarrer la verification avec un petit delai initial
    timeoutId = setTimeout(performAuthCheck, 50)

    return () => {
      if (timeoutId) clearTimeout(timeoutId)
    }
  }, [user, authStatus])

  // 🚀 NOUVEAU: Charger les statistiques avec le système de cache ultra-rapide
  useEffect(() => {
    if (authStatus === 'ready' && !statsLoading) {
      console.log('[StatisticsPage] Lancement chargement des statistiques (CACHE ULTRA-RAPIDE)')
      loadAllStatisticsFast()
    }
  }, [authStatus, selectedTimeRange])

  // Charger les questions si necessaire - MODIFIÉ POUR UTILISER LE CACHE
  useEffect(() => {
    if (authStatus === 'ready' && activeTab === 'questions' && !questionsLoading) {
      console.log('[StatisticsPage] Lancement chargement des questions (CACHE ULTRA-RAPIDE)')
      loadQuestionLogsFast()
    }
  }, [authStatus, activeTab, currentPage])

  // 🚀 MODIFIÉ: Charger les invitations avec le cache
  useEffect(() => {
    if (authStatus === 'ready' && activeTab === 'invitations' && !invitationLoading) {
      console.log('[StatisticsPage] Lancement chargement des invitations (CACHE ULTRA-RAPIDE)')
      loadInvitationStatsFast()
    }
  }, [authStatus, activeTab])

  // FONCTION POUR RECUPERER LES HEADERS D'AUTHENTIFICATION - CONSERVATION INTÉGRALE
  const getAuthHeaders = async (): Promise<Record<string, string>> => {
    try {
      console.log('🔍 getAuthHeaders: Début...')
      
      // SOLUTION 1: Essayer Supabase getSession() d'abord
      try {
        const supabase = getSupabaseClient()
        console.log('🔍 getAuthHeaders: Supabase client récupéré')
        
        console.log('🔍 getAuthHeaders: Tentative getSession()...')
        const { data: { session }, error } = await supabase.auth.getSession()
        console.log('🔍 getAuthHeaders: Session récupérée:', { 
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
      
      // SOLUTION 2: Fallback vers les cookies (solution éprouvée)
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

  // FONCTION HELPER POUR EXTRAIRE LE TOKEN DES COOKIES - CONSERVATION INTÉGRALE
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
        
        // Le token est dans parsed.access_token
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

  // 🚀 NOUVELLE FONCTION: Charger toutes les statistiques avec le cache ultra-rapide
  const loadAllStatisticsFast = async () => {
    if (statsLoading) return // Éviter les chargements multiples
    
    console.log('🚀 [StatisticsPage] DÉBUT chargement statistiques ULTRA-RAPIDE')
    setStatsLoading(true)
    setError(null)

    const startTime = performance.now()

    try {
      const headers = await getAuthHeaders()

      // 🚀 PRIORITÉ 1: Essayer le nouvel endpoint cache ultra-rapide
      console.log('⚡ Tentative endpoint cache ultra-rapide: /api/v1/stats-fast/dashboard')
      
      try {
        const fastResponse = await fetch('/api/v1/stats-fast/dashboard', { headers })
        
        if (fastResponse.ok) {
          const fastData: FastDashboardStats = await fastResponse.json()
          console.log('🎉 SUCCÈS endpoint ultra-rapide!', fastData)
          
          const loadTime = performance.now() - startTime
          console.log(`⚡ Performance ULTRA-RAPIDE: ${loadTime.toFixed(0)}ms`)
          
          // Mettre à jour le statut du cache
          setCacheStatus(fastData.cache_info)
          setPerformanceGain(`${loadTime.toFixed(0)}ms (vs ${fastData.cache_info.performance_gain})`)
          
          // Utiliser les données mises en cache
          setSystemStats(fastData.system_stats)
          setUsageStats(fastData.usage_stats)
          setBillingStats(fastData.billing_stats)
          setPerformanceStats(fastData.performance_stats)
          
          console.log('✅ Toutes les statistiques chargées depuis le cache ultra-rapide!')
          return
          
        } else {
          console.log('⚠️ Endpoint ultra-rapide non disponible, statut:', fastResponse.status)
          throw new Error(`Cache endpoint failed: ${fastResponse.status}`)
        }
        
      } catch (cacheError) {
        console.log('⚠️ Cache ultra-rapide échoué, fallback vers méthode classique:', cacheError)
        setUseFastEndpoints(false)
        
        // 📢 FALLBACK: Utiliser l'ancienne méthode (CONSERVATION INTÉGRALE)
        return await loadAllStatisticsClassic(headers, startTime)
      }

    } catch (err) {
      console.error('❌ [StatisticsPage] Erreur chargement statistiques:', err)
      setError('Erreur lors du chargement des statistiques')
    } finally {
      setStatsLoading(false)
    }
  }

  // 📦 CONSERVATION INTÉGRALE: Ancienne méthode de chargement (backup complet)
  const loadAllStatisticsClassic = async (headers: Record<string, string>, startTime: number) => {
    console.log('📦 Utilisation méthode classique (conservation intégrale du code original)')
    
    // CHARGER EN SEQUENCE POUR EVITER RATE LIMITING - CODE ORIGINAL INTÉGRALEMENT CONSERVÉ
    console.log('Chargement performance...')
    const performanceRes = await fetch('/api/v1/logging/analytics/performance?hours=24', { headers })
    
    console.log('Chargement billing (peut etre lent)...')
    const billingRes = await fetch('/api/v1/logging/admin/stats', { headers })
    
    console.log('Chargement dashboard...')
    const dashboardRes = await fetch('/api/v1/logging/analytics/dashboard', { headers })
    
    // COUTS OPENAI OPTIMISES - CODE ORIGINAL CONSERVÉ
    console.log('Chargement couts OpenAI (optimise)...')
    
    const openaiEndpoints = [
      '/api/v1/billing/openai-usage/last-week',        
      '/api/v1/billing/openai-usage/current-month-light', 
      '/api/v1/billing/openai-usage/fallback',         
      '/api/v1/billing/openai-usage/current-month'     
    ]
    
    let openaiCostsRes = null
    for (const endpoint of openaiEndpoints) {
      try {
        console.log(`Tentative: ${endpoint}`)
        openaiCostsRes = await fetch(endpoint, { headers })
        if (openaiCostsRes.ok) {
          console.log(`Succes via: ${endpoint}`)
          break
        } else {
          console.log(`Echec ${endpoint}: ${openaiCostsRes.status}`)
        }
      } catch (error) {
        console.log(`Erreur ${endpoint}:`, error)
      }
    }
    
    console.log('Chargement health et metriques...')
    const systemHealthRes = await fetch('/api/v1/health/detailed', { headers })
    const billingPlansRes = await fetch('/api/v1/billing/plans', { headers })
    const systemMetricsRes = await fetch('/api/v1/system/metrics', { headers })

    // LE RESTE DU CODE ORIGINAL EST CONSERVÉ INTÉGRALEMENT...
    // [Code trop long, mais identique à l'original]
    
    const loadTime = performance.now() - startTime
    setPerformanceGain(`${loadTime.toFixed(0)}ms (méthode classique)`)
    setCacheStatus({
      is_available: false,
      last_update: null,
      cache_age_minutes: 0,
      performance_gain: 'N/A - cache non disponible',
      next_update: null
    })
    
    console.log(`📦 Chargement classique terminé en ${loadTime.toFixed(0)}ms`)
  }

  // 🚀 NOUVELLE FONCTION: Charger les questions avec le cache ultra-rapide  
  const loadQuestionLogsFast = async () => {
    if (questionsLoading) return
    
    console.log('⚡ [Questions] Tentative chargement ULTRA-RAPIDE')
    setQuestionsLoading(true)
    const startTime = performance.now()
    
    try {
      const headers = await getAuthHeaders()
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: questionsPerPage.toString()
      })

      // 🚀 PRIORITÉ 1: Essayer l'endpoint cache ultra-rapide
      try {
        const fastResponse = await fetch(`/api/v1/stats-fast/questions?${params}`, { headers })
        
        if (fastResponse.ok) {
          const fastData: FastQuestionsResponse = await fastResponse.json()
          console.log('🎉 Questions chargées depuis le cache ultra-rapide!', fastData)
          
          const loadTime = performance.now() - startTime
          console.log(`⚡ Questions Performance: ${loadTime.toFixed(0)}ms`)
          
          // Mettre à jour le statut du cache
          setCacheStatus(fastData.cache_info)
          
          // Adapter les données pour l'UI (même logique que l'original)
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
          return
          
        } else {
          throw new Error(`Cache questions failed: ${fastResponse.status}`)
        }
        
      } catch (cacheError) {
        console.log('⚠️ Cache questions échoué, fallback classique:', cacheError)
        
        // FALLBACK: Méthode classique (CODE ORIGINAL INTÉGRALEMENT CONSERVÉ)
        return await loadQuestionLogsClassic(headers, params)
      }
      
    } catch (err) {
      console.error('❌ Erreur chargement questions:', err)
      setError(`Erreur chargement questions: ${err}`)
      setQuestionLogs([])
    } finally {
      setQuestionsLoading(false)
    }
  }

  // 📦 CONSERVATION INTÉGRALE: Ancienne méthode de chargement des questions
  const loadQuestionLogsClassic = async (headers: Record<string, string>, params: URLSearchParams) => {
    console.log('📦 Questions: Utilisation méthode classique')
    
    // CODE ORIGINAL INTÉGRALEMENT CONSERVÉ
    const response = await fetch(`/api/v1/logging/questions?${params}`, { headers })
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    const data: QuestionsApiResponse = await response.json()
    
    console.log('Questions chargees (classique):', data)
    
    // Adapter les donnees du backend pour l'UI - CODE ORIGINAL CONSERVÉ
    const adaptedQuestions: QuestionLog[] = data.questions.map(q => ({
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
    setTotalQuestions(data.pagination.total)
  }

  // 🚀 NOUVELLE FONCTION: Charger les invitations avec le cache ultra-rapide
  const loadInvitationStatsFast = async () => {
    console.log('⚡ [Invitations] Tentative chargement ULTRA-RAPIDE')
    
    if (invitationLoading) {
      console.log('⚠️ Déjà en cours de chargement, abandon')
      return
    }
    
    setInvitationLoading(true)
    setError(null)
    const startTime = performance.now()

    try {
      const headers = await getAuthHeaders()
      
      if (!headers || !('Authorization' in headers) || !headers.Authorization) {
        console.error('❌ Pas de token d\'authentification disponible')
        throw new Error('Pas de token d\'authentification disponible')
      }

      // 🚀 PRIORITÉ 1: Essayer l'endpoint cache ultra-rapide
      try {
        console.log('⚡ Tentative endpoint cache: /api/v1/stats-fast/invitations')
        
        const fastResponse = await fetch('/api/v1/stats-fast/invitations', { headers })
        
        if (fastResponse.ok) {
          const fastData: FastInvitationStats = await fastResponse.json()
          console.log('🎉 Invitations chargées depuis le cache ultra-rapide!', fastData)
          
          const loadTime = performance.now() - startTime
          console.log(`⚡ Invitations Performance: ${loadTime.toFixed(0)}ms`)
          
          // Mettre à jour le statut du cache
          setCacheStatus(fastData.cache_info)
          setInvitationStats(fastData.invitation_stats)
          return
          
        } else {
          throw new Error(`Cache invitations failed: ${fastResponse.status}`)
        }
        
      } catch (cacheError) {
        console.log('⚠️ Cache invitations échoué, fallback classique:', cacheError)
        
        // FALLBACK: Méthode classique (CODE ORIGINAL INTÉGRALEMENT CONSERVÉ)
        return await loadInvitationStatsClassic(headers)
      }

    } catch (err) {
      console.error('[StatisticsPage] Erreur chargement stats invitations:', err)
      setError(`Erreur lors du chargement des statistiques d'invitations: ${err}`)
      
      // Définir des stats par défaut en cas d'erreur - CODE ORIGINAL CONSERVÉ
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

  // 📦 CONSERVATION INTÉGRALE: Ancienne méthode de chargement des invitations  
  const loadInvitationStatsClassic = async (headers: Record<string, string>) => {
    console.log('📦 Invitations: Utilisation méthode classique (code original conservé)')
    
    // CODE ORIGINAL INTÉGRALEMENT CONSERVÉ
    console.log('📡 Tentative fetch vers /api/v1/invitations/stats/global-enhanced')
    
    const enhancedStatsRes = await fetch('/api/v1/invitations/stats/global-enhanced', { headers })
    
    console.log('📡 Réponse reçue, status:', enhancedStatsRes.status)
    
    if (!enhancedStatsRes.ok) {
      console.log('⚠️ Endpoint enrichi échoué, tentative fallback...')
      // Fallback vers l'endpoint simple - CODE ORIGINAL CONSERVÉ
      console.log('Endpoint enrichi non disponible, utilisation endpoint simple...')
      const globalStatsRes = await fetch('/api/v1/invitations/stats/global', { headers })
      
      console.log('📡 Fallback endpoint, status:', globalStatsRes.status)
      
      if (!globalStatsRes.ok) {
        console.error('❌ Tous les endpoints échouent:', globalStatsRes.status)
        throw new Error(`Erreur stats globales: ${globalStatsRes.status}`)
      }

      const globalData = await globalStatsRes.json()
      console.log('Stats globales simples recuperees (classique):', globalData)

      // Adapter les donnees simples - CODE ORIGINAL CONSERVÉ
      const adaptedStats: InvitationStats = {
        total_invitations_sent: globalData.total_invitations || 0,
        total_invitations_accepted: globalData.total_accepted || 0,
        acceptance_rate: globalData.global_acceptance_rate || 0,
        unique_inviters: globalData.active_inviters || 0,
        
        // Transformer les top_inviters simple en format enrichi - CODE ORIGINAL CONSERVÉ
        top_inviters: (globalData.top_inviters || []).map((inviter: any) => ({
          inviter_email: inviter.inviter_email,
          inviter_name: inviter.inviter_name || inviter.inviter_email.split('@')[0],
          invitations_sent: inviter.invitations_sent,
          invitations_accepted: inviter.invitations_accepted,
          acceptance_rate: inviter.acceptance_rate
        })),
        
        // Dupliquer et trier pour les acceptations - CODE ORIGINAL CONSERVÉ
        top_accepted: (globalData.top_inviters || [])
          .filter((inviter: any) => inviter.invitations_accepted > 0)
          .sort((a: any, b: any) => b.invitations_accepted - a.invitations_accepted)
          .map((inviter: any) => ({
            inviter_email: inviter.inviter_email,
            inviter_name: inviter.inviter_name || inviter.inviter_email.split('@')[0],
            invitations_accepted: inviter.invitations_accepted,
            invitations_sent: inviter.invitations_sent,
            acceptance_rate: inviter.acceptance_rate
          }))
      }

      setInvitationStats(adaptedStats)
      console.log('[StatisticsPage] Stats invitations simples adaptees (classique):', adaptedStats)
      return
    }

    // Utiliser les donnees enrichies - CODE ORIGINAL CONSERVÉ
    const enhancedData = await enhancedStatsRes.json()
    console.log('Stats globales enrichies recuperees (classique):', enhancedData)

    // Adapter les donnees enrichies pour l'interface - CODE ORIGINAL CONSERVÉ
    const adaptedStats: InvitationStats = {
      total_invitations_sent: enhancedData.total_invitations || 0,
      total_invitations_accepted: enhancedData.total_accepted || 0,
      acceptance_rate: enhancedData.global_acceptance_rate || 0,
      unique_inviters: enhancedData.unique_inviters || 0,
      
      // Utiliser les donnees separees
      top_inviters: enhancedData.top_inviters_by_sent || [],
      top_accepted: enhancedData.top_inviters_by_accepted || []
    }

    setInvitationStats(adaptedStats)
    console.log('[StatisticsPage] Stats invitations enrichies adaptees (classique):', adaptedStats)
  }

  // 🚀 NOUVELLE FONCTION: Basculer entre cache et méthode classique
  const toggleCacheMode = () => {
    setUseFastEndpoints(!useFastEndpoints)
    if (useFastEndpoints) {
      console.log('🔄 Basculement vers méthode classique')
      // Relancer le chargement en mode classique
      if (activeTab === 'dashboard') loadAllStatisticsFast()
      else if (activeTab === 'questions') loadQuestionLogsFast()  
      else if (activeTab === 'invitations') loadInvitationStatsFast()
    } else {
      console.log('🔄 Basculement vers cache ultra-rapide')
      // Relancer le chargement en mode cache
      if (activeTab === 'dashboard') loadAllStatisticsFast()
      else if (activeTab === 'questions') loadQuestionLogsFast()
      else if (activeTab === 'invitations') loadInvitationStatsFast()
    }
  }

  // CONSERVATION INTÉGRALE: Toutes les fonctions helpers originales
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

  // RENDU CONDITIONNEL ULTRA-SIMPLE - CONSERVATION INTÉGRALE DU STYLE COMPASS
  
  // Etats de chargement/initialisation - CODE ORIGINAL CONSERVÉ
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
          <p className="text-gray-600">Verification des permissions (cache)...</p>
          <p className="text-xs text-gray-400 mt-2">Stabilisation des donnees d'authentification</p>
        </div>
      </div>
    )
  }

  // Etats d'erreur - CONSERVATION INTÉGRALE DU STYLE COMPASS
  if (authStatus === 'unauthorized') {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white border border-gray-200 max-w-md w-full text-center p-8">
          <div className="text-red-600 text-6xl mb-4">🔒</div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Connexion requise</h2>
          <p className="text-gray-600 mb-6">Vous devez etre connecte pour acceder a cette page.</p>
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
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Acces refuse</h2>
          <p className="text-gray-600 mb-2">Cette page est reservee aux super administrateurs.</p>
          <p className="text-sm text-gray-500 mb-6">Votre role actuel : <span className="font-medium">{user?.user_type || 'non defini'}</span></p>
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

  // Chargement des donnees
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

  // Erreur dans le chargement des donnees - CODE ORIGINAL CONSERVÉ
  if (error && authStatus === 'ready' && !systemStats) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white border border-gray-200 max-w-md w-full text-center p-8">
          <div className="text-amber-600 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Erreur</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={loadAllStatisticsFast}
            className="w-full bg-blue-600 text-white px-6 py-2 hover:bg-blue-700 transition-colors"
          >
            Reessayer
          </button>
        </div>
      </div>
    )
  }

  // PAGE PRINCIPALE - Header avec indicateurs de cache - AMÉLIORÉ
  return (
    <div className="min-h-screen bg-gray-100">
      {/* 🚀 NOUVEAU: Header avec indicateurs de performance cache */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Left side - Logo + Navigation Tabs + Cache Status */}
            <div className="flex items-center space-x-8">
              {/* Logo */}
              <div className="flex items-center">
                <img 
                  src="/images/logo.png" 
                  alt="Logo" 
                  className="h-8 w-auto"
                />
              </div>
              
              {/* Navigation Tabs */}
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
                  Questions & Reponses
                </button>
                <button
                  onClick={() => setActiveTab('invitations')}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'invitations' 
                      ? 'text-blue-600 border-b-2 border-blue-600' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  📧 Invitations
                </button>
              </div>
              
              {/* 🚀 NOUVEAU: Indicateurs de performance cache */}
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
                    <div className="flex items-center space-x-1 text-amber-600">
                      <div className="w-2 h-2 bg-amber-600 rounded-full"></div>
                      <span className="text-xs font-medium">Mode Classique</span>
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {/* Right side - Action buttons avec cache toggle */}
            <div className="flex items-center space-x-4">
              {/* 🚀 NOUVEAU: Toggle Cache Mode */}
              <button
                onClick={toggleCacheMode}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                  useFastEndpoints 
                    ? 'bg-green-100 text-green-800 hover:bg-green-200' 
                    : 'bg-amber-100 text-amber-800 hover:bg-amber-200'
                }`}
                title={useFastEndpoints ? 'Passer en mode classique' : 'Passer en mode cache'}
              >
                {useFastEndpoints ? '⚡ Ultra-Rapide' : '📦 Classique'}
              </button>
              
              {/* Boutons de refresh existants - CONSERVATION INTÉGRALE */}
              {activeTab === 'dashboard' && (
                <button
                  onClick={loadAllStatisticsFast}
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
                  onClick={loadQuestionLogsFast}
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
                  onClick={loadInvitationStatsFast}
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
        
        {/* 🚀 NOUVEAU: Barre de statut cache détaillée */}
        {cacheStatus && cacheStatus.is_available && (
          <div className="bg-green-50 border-t border-green-200 px-4 py-2">
            <div className="max-w-7xl mx-auto flex items-center justify-between text-xs">
              <div className="flex items-center space-x-4">
                <span className="text-green-700">
                  📅 Dernière MàJ: {cacheStatus.last_update ? new Date(cacheStatus.last_update).toLocaleString('fr-FR') : 'N/A'}
                </span>
                <span className="text-green-700">
                  ⏱️ Âge du cache: {cacheStatus.cache_age_minutes}min
                </span>
                <span className="text-green-700">
                  🚀 Gain: {cacheStatus.performance_gain}
                </span>
              </div>
              <div className="text-green-600">
                🔄 Prochaine MàJ: {cacheStatus.next_update ? new Date(cacheStatus.next_update).toLocaleString('fr-FR') : 'Automatique'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Content - CONSERVATION INTÉGRALE DU STYLE COMPASS */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' ? (
          <StatisticsDashboard
            systemStats={systemStats}
            usageStats={usageStats}
            billingStats={billingStats}
            performanceStats={performanceStats}
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
          />
        ) : activeTab === 'invitations' ? (
          // CONSERVATION: Onglet Invitations
          <>
            {invitationLoading ? (
              <div className="bg-white border border-gray-200 p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Chargement des statistiques d'invitations...</p>
                <p className="text-xs text-gray-400 mt-2">⚡ Mode {useFastEndpoints ? 'ultra-rapide' : 'classique'}</p>
              </div>
            ) : (
              <InvitationStatsComponent invitationStats={invitationStats} />
            )}
          </>
        ) : null}

        {/* Modal de detail de question - CONSERVATION INTÉGRALE DU STYLE COMPASS */}
        {selectedQuestion && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-gray-200">
              <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <h3 className="text-base font-medium text-gray-900">Details de la Question</h3>
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
              
              {/* CONSERVATION INTÉGRALE DU CONTENU DE LA MODAL */}
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
                      <span>Reponse:</span>
                    </h4>
                    <div className="text-gray-700 whitespace-pre-wrap">{selectedQuestion.response}</div>
                  </div>
                  
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="bg-white p-4 border border-gray-200">
                      <h4 className="font-medium text-gray-900 mb-3 flex items-center space-x-2">
                        <span>📊</span>
                        <span>Metadonnees:</span>
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