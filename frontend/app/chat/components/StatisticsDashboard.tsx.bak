import React from 'react'

// 🚀 NOUVEAU: Interface pour les réponses cache ultra-rapides
interface CacheDashboardResponse {
  cache_info: {
    is_available: boolean
    last_update: string | null
    cache_age_minutes: number
    performance_gain: string
    next_update: string | null
  }
  system_stats: SystemStats
  usage_stats: UsageStats
  billing_stats: BillingStats
  performance_stats: PerformanceStats
}

// CONSERVATION INTÉGRALE: Interfaces existantes
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

// 🚀 MODIFIÉE: Props avec support du cache
interface StatisticsDashboardProps {
  systemStats: SystemStats | null
  usageStats: UsageStats | null
  billingStats: BillingStats | null
  performanceStats: PerformanceStats | null
  // 🚀 NOUVEAU: Props optionnelles pour le cache
  cacheStatus?: {
    is_available: boolean
    last_update: string | null
    cache_age_minutes: number
    performance_gain: string
    next_update: string | null
  } | null
  isLoading?: boolean
  useFastEndpoints?: boolean
}

export const StatisticsDashboard: React.FC<StatisticsDashboardProps> = ({
  systemStats,
  usageStats,
  billingStats,
  performanceStats,
  // 🚀 NOUVEAU: Propriétés cache avec valeurs par défaut
  cacheStatus = null,
  isLoading = false,
  useFastEndpoints = true
}) => {
  
  // 🚀 NOUVEAU: Indicateur de chargement amélioré
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement du tableau de bord...</p>
          <p className="text-sm text-gray-400 mt-2">
            {useFastEndpoints ? '⚡ Mode cache ultra-rapide' : '📦 Mode classique'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* 🚀 NOUVEAU: Header avec informations de performance cache */}
      {cacheStatus && cacheStatus.is_available && (
        <div className="bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-600 rounded-full animate-pulse"></div>
                <h3 className="text-lg font-semibold text-green-900">🚀 Tableau de Bord Ultra-Rapide</h3>
              </div>
              <div className="flex items-center space-x-6 text-sm">
                <div className="text-green-700">
                  <span className="font-medium">⚡ Performance:</span> {cacheStatus.performance_gain}
                </div>
                <div className="text-blue-700">
                  <span className="font-medium">📅 Dernière MàJ:</span> {cacheStatus.last_update ? new Date(cacheStatus.last_update).toLocaleString('fr-FR', { 
                    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                  }) : 'N/A'}
                </div>
                <div className="text-indigo-700">
                  <span className="font-medium">⏱️ Âge du cache:</span> {cacheStatus.cache_age_minutes} minutes
                </div>
              </div>
            </div>
            <div className="bg-white bg-opacity-80 px-3 py-1 rounded-full">
              <span className="text-sm font-medium text-green-800">Données optimisées</span>
            </div>
          </div>
        </div>
      )}

      {/* KPIs Row - CONSERVATION INTÉGRALE EXACT Compass Style - AVEC indicateurs cache */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Utilisateurs Actifs - AVEC badge cache */}
        <div className="bg-white border border-gray-200 p-4 relative">
          <div>
            <p className="text-sm text-gray-600 mb-1">Utilisateurs Actifs</p>
            <p className="text-2xl font-semibold text-gray-900">{usageStats?.unique_users || 0}</p>
            {/* 🚀 NOUVEAU: Badge cache dans le coin */}
            {cacheStatus?.is_available && (
              <div className="absolute top-2 right-2">
                <div className="w-2 h-2 bg-green-500 rounded-full" title="Données en cache"></div>
              </div>
            )}
          </div>
        </div>

        {/* Questions ce mois - AVEC indicateur de fraîcheur */}
        <div className="bg-white border border-gray-200 p-4 relative">
          <div>
            <p className="text-sm text-gray-600 mb-1">Questions ce mois</p>
            <p className="text-2xl font-semibold text-gray-900">{usageStats?.questions_this_month || 0}</p>
            {cacheStatus?.is_available && (
              <>
                <div className="absolute top-2 right-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
                <p className="text-xs text-green-600 mt-1">⚡ Cache {cacheStatus.cache_age_minutes}min</p>
              </>
            )}
          </div>
        </div>

        {/* Revenus Totaux - AVEC performance */}
        <div className="bg-white border border-gray-200 p-4 relative">
          <div>
            <p className="text-sm text-gray-600 mb-1">Revenus Totaux</p>
            <p className="text-2xl font-semibold text-gray-900">${billingStats?.total_revenue || 0}</p>
            {cacheStatus?.is_available && (
              <>
                <div className="absolute top-2 right-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
                <p className="text-xs text-blue-600 mt-1">{cacheStatus.performance_gain}</p>
              </>
            )}
          </div>
        </div>

        {/* Temps de Réponse - AVEC source */}
        <div className="bg-white border border-gray-200 p-4 relative">
          <div>
            <p className="text-sm text-gray-600 mb-1">Temps de Réponse</p>
            <p className="text-2xl font-semibold text-gray-900">{performanceStats?.avg_response_time || 0}s</p>
            {cacheStatus ? (
              <>
                <div className="absolute top-2 right-2">
                  <div className={`w-2 h-2 rounded-full ${
                    cacheStatus.is_available ? 'bg-green-500' : 'bg-amber-500'
                  }`}></div>
                </div>
                <p className={`text-xs mt-1 ${
                  cacheStatus.is_available ? 'text-green-600' : 'text-amber-600'
                }`}>
                  {cacheStatus.is_available ? '⚡ Cache' : '📦 Direct'}
                </p>
              </>
            ) : (
              <p className="text-xs text-gray-500 mt-1">Mode standard</p>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Grid - CONSERVATION INTÉGRALE Style Compass avec layout exact */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Sources des Réponses - AVEC indicateurs cache Table style Compass */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-medium text-gray-900">Sources des Réponses</h3>
              {/* 🚀 NOUVEAU: Indicateur de source des données */}
              {cacheStatus && (
                <span className={`text-xs px-2 py-1 rounded ${
                  cacheStatus.is_available 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-amber-100 text-amber-800'
                }`}>
                  {cacheStatus.is_available ? '⚡ Cache' : '📦 Direct'}
                </span>
              )}
            </div>
          </div>
          <div className="p-4">
            <div className="space-y-3">
              {usageStats?.source_distribution && Object.entries(usageStats.source_distribution).map(([source, count]) => {
                const total = Object.values(usageStats.source_distribution).reduce((a, b) => a + b, 0)
                const percentage = total > 0 ? (count / total * 100).toFixed(1) : 0
                
                const getSourceColor = (source: string) => {
                  switch (source) {
                    case 'rag_retriever': return 'bg-blue-500'
                    case 'openai_fallback': return 'bg-purple-500'
                    case 'perfstore': return 'bg-green-500'
                    default: return 'bg-gray-400'
                  }
                }
                
                const getSourceLabel = (source: string) => {
                  switch (source) {
                    case 'rag_retriever': return 'RAG Retriever'
                    case 'openai_fallback': return 'OpenAI Fallback'
                    case 'perfstore': return 'Performance Store'
                    default: return source
                  }
                }
                
                return (
                  <div key={source} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className={`w-3 h-3 ${getSourceColor(source)}`}></div>
                      <span className="text-sm text-gray-700">{getSourceLabel(source)}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-16 bg-gray-200 h-2">
                        <div 
                          className={`h-2 ${getSourceColor(source)} transition-all duration-300`}
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                      <span className="text-sm font-medium text-gray-900 w-12 text-right">{count}</span>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* 🚀 NOUVEAU: Footer avec informations de cache */}
            {cacheStatus && cacheStatus.is_available && (
              <div className="mt-4 pt-3 border-t border-gray-100">
                <div className="flex items-center justify-between text-xs text-green-600">
                  <span>📊 Données optimisées par cache</span>
                  <span>⏱️ MàJ: {cacheStatus.last_update ? new Date(cacheStatus.last_update).toLocaleString('fr-FR', {
                    hour: '2-digit', minute: '2-digit'
                  }) : 'N/A'}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Santé du Système - CONSERVATION INTÉGRALE Style Compass exact AVEC cache */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-medium text-gray-900">Santé du Système</h3>
              {/* 🚀 NOUVEAU: Indicateur temps réel vs cache */}
              {cacheStatus && (
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    cacheStatus.is_available ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
                  }`}></div>
                  <span className="text-xs text-gray-600">
                    {cacheStatus.is_available ? 'Cache' : 'Temps réel'}
                  </span>
                </div>
              )}
            </div>
          </div>
          <div className="p-4">
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Uptime</span>
                <span className="text-sm font-medium text-gray-900">
                  {systemStats?.system_health?.uptime_hours?.toFixed(1) || '0.0'}h
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Taux d'erreur</span>
                <span className={`text-sm font-medium ${(systemStats?.system_health?.error_rate || 0) < 5 ? 'text-green-600' : 'text-red-600'}`}>
                  {systemStats?.system_health?.error_rate?.toFixed(1) || '0.0'}%
                </span>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Cache Hit Rate</span>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-green-600">
                    {performanceStats?.cache_hit_rate?.toFixed(1) || '0.0'}%
                  </span>
                  {/* 🚀 NOUVEAU: Indicateur de performance cache système */}
                  {cacheStatus?.is_available && (
                    <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                      Ultra-rapide
                    </span>
                  )}
                </div>
              </div>
              
              <div className="pt-3 border-t border-gray-200">
                <p className="text-sm font-medium text-gray-900 mb-2">Services RAG</p>
                <div className="space-y-2">
                  {systemStats?.system_health?.rag_status && Object.entries(systemStats.system_health.rag_status).map(([service, status]) => (
                    <div key={service} className="flex justify-between items-center">
                      <span className="text-xs text-gray-600 capitalize">{service}</span>
                      <span className={`text-xs px-2 py-1 ${status ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {status ? 'Actif' : 'Inactif'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 🚀 NOUVEAU: Section de performance du cache système */}
              {cacheStatus && (
                <div className="pt-3 border-t border-gray-200">
                  <p className="text-sm font-medium text-gray-900 mb-2">Performance Cache</p>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-600">Statut</span>
                      <span className={`text-xs px-2 py-1 ${
                        cacheStatus.is_available ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {cacheStatus.is_available ? 'Actif' : 'Inactif'}
                      </span>
                    </div>
                    {cacheStatus.is_available && (
                      <>
                        <div className="flex justify-between items-center">
                          <span className="text-xs text-gray-600">Gain perf.</span>
                          <span className="text-xs font-medium text-green-600">
                            {cacheStatus.performance_gain}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-xs text-gray-600">Âge cache</span>
                          <span className={`text-xs font-medium ${
                            cacheStatus.cache_age_minutes < 30 ? 'text-green-600' :
                            cacheStatus.cache_age_minutes < 45 ? 'text-yellow-600' :
                            'text-red-600'
                          }`}>
                            {cacheStatus.cache_age_minutes}min
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tables Section - CONSERVATION INTÉGRALE Style Compass exact comme dans les images */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Top Users Table - CONSERVATION INTÉGRALE Style exact Compass AVEC cache */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-medium text-gray-900">Utilisateurs les Plus Actifs</h3>
              {/* 🚀 NOUVEAU: Métadonnées de cache */}
              {cacheStatus && cacheStatus.is_available && (
                <div className="text-xs text-green-600 flex items-center space-x-2">
                  <div className="w-1.5 h-1.5 bg-green-600 rounded-full"></div>
                  <span>Cache {cacheStatus.cache_age_minutes}min</span>
                </div>
              )}
            </div>
          </div>
          <div className="overflow-hidden">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Utilisateur</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Questions</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Plan</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {billingStats?.top_users?.slice(0, 5).map((user, index) => (
                  <tr key={user.email || `user-${index}`} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm text-gray-900 max-w-48">
                      <div className="truncate" title={user.email || 'Email non disponible'}>
                        {user.email || 'Utilisateur anonyme'}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600">{user.question_count || 0}</td>
                    <td className="px-4 py-2">
                      <span className={`inline-flex items-center px-2 py-1 text-xs font-medium ${
                        user.plan === 'enterprise' ? 'bg-purple-100 text-purple-800' :
                        user.plan === 'professional' ? 'bg-blue-100 text-blue-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {user.plan || 'non défini'}
                      </span>
                    </td>
                  </tr>
                )) || []}
                {(!billingStats?.top_users || billingStats.top_users.length === 0) && (
                  <tr>
                    <td colSpan={3} className="px-4 py-8 text-center text-gray-500">
                      <div className="text-gray-400 text-2xl mb-2">👥</div>
                      <p>Aucune donnée utilisateur disponible</p>
                      <p className="text-xs mt-1">
                        {cacheStatus?.is_available ? 
                          'Cache actif - Données en cours de chargement' : 
                          'Les statistiques d\'utilisation sont en cours de chargement'
                        }
                      </p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Plans Distribution - CONSERVATION INTÉGRALE Style exact Compass AVEC cache */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-medium text-gray-900">Répartition des Plans</h3>
              {/* 🚀 NOUVEAU: Indicateur de performance */}
              {cacheStatus && cacheStatus.is_available && (
                <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                  {cacheStatus.performance_gain}
                </span>
              )}
            </div>
          </div>
          <div className="p-4">
            <div className="space-y-3">
              {billingStats?.plans && Object.entries(billingStats.plans).map(([planName, data]) => (
                <div key={planName} className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200">
                  <div>
                    <p className="text-sm font-medium text-gray-900 capitalize">{planName}</p>
                    <p className="text-xs text-gray-600">{data.user_count} utilisateurs</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-gray-900">${data.revenue}</p>
                    <p className="text-xs text-gray-600">revenus</p>
                  </div>
                </div>
              ))}
            </div>

            {/* 🚀 NOUVEAU: Information sur la source des données plans */}
            {cacheStatus && (
              <div className="mt-4 pt-3 border-t border-gray-200">
                <div className="flex items-center justify-between text-xs">
                  <span className={`${
                    cacheStatus.is_available ? 'text-green-600' : 'text-amber-600'
                  }`}>
                    {cacheStatus.is_available ? 
                      '⚡ Données optimisées par cache' : 
                      '📦 Données en temps réel'
                    }
                  </span>
                  {cacheStatus.is_available && (
                    <span className="text-gray-500">
                      Prochaine MàJ: {cacheStatus.next_update ? new Date(cacheStatus.next_update).toLocaleString('fr-FR', {
                        hour: '2-digit', minute: '2-digit'
                      }) : 'Auto'}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Costs Section - CONSERVATION INTÉGRALE Style Compass exact avec fond blanc et POLICE NOIRE AVEC cache */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-medium text-gray-900">Coûts et Performance</h3>
            {/* 🚀 NOUVEAU: Statut global du cache */}
            {cacheStatus && (
              <div className="flex items-center space-x-3">
                {cacheStatus.is_available ? (
                  <>
                    <div className="flex items-center space-x-1 text-green-600">
                      <div className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></div>
                      <span className="text-sm font-medium">Cache Actif</span>
                    </div>
                    <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                      🚀 {cacheStatus.performance_gain} gain
                    </span>
                  </>
                ) : (
                  <div className="flex items-center space-x-1 text-amber-600">
                    <div className="w-2 h-2 bg-amber-600 rounded-full"></div>
                    <span className="text-sm font-medium">Mode Standard</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Coûts OpenAI - AVEC indicateur cache */}
            <div className="text-center p-3 bg-white border border-gray-200 relative">
              <p className="text-lg font-semibold text-gray-900">${performanceStats?.openai_costs?.toFixed(2) || '0.00'}</p>
              <p className="text-xs text-gray-600">Coûts OpenAI</p>
              {cacheStatus?.is_available && (
                <div className="absolute top-1 right-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full" title="Données en cache"></div>
                </div>
              )}
            </div>

            {/* Erreurs - AVEC indicateur cache */}
            <div className="text-center p-3 bg-white border border-gray-200 relative">
              <p className="text-lg font-semibold text-gray-900">{performanceStats?.error_count || 0}</p>
              <p className="text-xs text-gray-600">Erreurs</p>
              {cacheStatus?.is_available && (
                <div className="absolute top-1 right-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              )}
            </div>

            {/* Requêtes Totales - AVEC indicateur cache */}
            <div className="text-center p-3 bg-white border border-gray-200 relative">
              <p className="text-lg font-semibold text-gray-900">{systemStats?.system_health?.total_requests || 0}</p>
              <p className="text-xs text-gray-600">Requêtes Totales</p>
              {cacheStatus?.is_available && (
                <div className="absolute top-1 right-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              )}
            </div>

            {/* Questions Aujourd'hui - AVEC indicateur cache */}
            <div className="text-center p-3 bg-white border border-gray-200 relative">
              <p className="text-lg font-semibold text-gray-900">{usageStats?.questions_today || 0}</p>
              <p className="text-xs text-gray-600">Questions Aujourd'hui</p>
              {cacheStatus?.is_available && (
                <div className="absolute top-1 right-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              )}
            </div>
          </div>

          {/* 🚀 NOUVEAU: Section détaillée de métriques de cache */}
          {cacheStatus && (
            <div className="mt-6 pt-4 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-900 mb-3">Métriques de Performance Cache</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                
                <div className="bg-gradient-to-br from-green-50 to-green-100 p-3 rounded-lg border border-green-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-green-800">Statut Cache</span>
                    <div className={`w-2 h-2 rounded-full ${
                      cacheStatus.is_available ? 'bg-green-600 animate-pulse' : 'bg-red-600'
                    }`}></div>
                  </div>
                  <p className="text-lg font-semibold text-green-900">
                    {cacheStatus.is_available ? 'Actif' : 'Inactif'}
                  </p>
                  <p className="text-xs text-green-700 mt-1">
                    {cacheStatus.is_available ? 
                      'Données ultra-rapides disponibles' : 
                      'Utilisation des endpoints directs'
                    }
                  </p>
                </div>

                <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-3 rounded-lg border border-blue-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-blue-800">Gain Performance</span>
                    <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.293l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <p className="text-lg font-semibold text-blue-900">
                    {cacheStatus.is_available ? cacheStatus.performance_gain : 'Standard'}
                  </p>
                  <p className="text-xs text-blue-700 mt-1">
                    {cacheStatus.is_available ? 
                      'Accélération vs méthode classique' : 
                      'Performance de base'
                    }
                  </p>
                </div>

                <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 p-3 rounded-lg border border-indigo-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-indigo-800">Prochaine MàJ</span>
                    <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <p className="text-lg font-semibold text-indigo-900">
                    {cacheStatus.next_update ? new Date(cacheStatus.next_update).toLocaleString('fr-FR', {
                      hour: '2-digit', minute: '2-digit'
                    }) : 'Auto'}
                  </p>
                  <p className="text-xs text-indigo-700 mt-1">
                    {cacheStatus.is_available ? 
                      'Actualisation automatique programmée' : 
                      'Pas de cache planifié'
                    }
                  </p>
                </div>

              </div>

              {/* 🚀 NOUVEAU: Barre de progression de fraîcheur du cache */}
              {cacheStatus.is_available && (
                <div className="mt-4">
                  <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                    <span>Fraîcheur des données du tableau de bord</span>
                    <span>
                      {Math.max(0, 60 - cacheStatus.cache_age_minutes)} minutes avant expiration
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 h-2 rounded-full overflow-hidden">
                    <div 
                      className={`h-2 rounded-full transition-all duration-500 ${
                        cacheStatus.cache_age_minutes < 20 ? 'bg-green-500' :
                        cacheStatus.cache_age_minutes < 40 ? 'bg-yellow-500' :
                        cacheStatus.cache_age_minutes < 55 ? 'bg-orange-500' :
                        'bg-red-500'
                      }`}
                      style={{ 
                        width: `${Math.max(5, Math.min(100, 100 - (cacheStatus.cache_age_minutes / 60 * 100)))}%` 
                      }}
                    ></div>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Très récent</span>
                    <span>À actualiser</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  )
}