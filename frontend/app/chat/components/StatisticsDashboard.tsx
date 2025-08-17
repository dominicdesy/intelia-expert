import React from 'react'

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

interface StatisticsDashboardProps {
  systemStats: SystemStats | null
  usageStats: UsageStats | null
  billingStats: BillingStats | null
  performanceStats: PerformanceStats | null
}

export const StatisticsDashboard: React.FC<StatisticsDashboardProps> = ({
  systemStats,
  usageStats,
  billingStats,
  performanceStats
}) => {
  return (
    <>
      {/* KPIs Row - EXACT Compass Style */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Utilisateurs Actifs - Sans icône */}
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Utilisateurs Actifs</p>
            <p className="text-2xl font-semibold text-gray-900">{usageStats?.unique_users || 0}</p>
          </div>
        </div>

        {/* Questions ce mois - Sans icône */}
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Questions ce mois</p>
            <p className="text-2xl font-semibold text-gray-900">{usageStats?.questions_this_month || 0}</p>
          </div>
        </div>

        {/* Revenus Totaux - Sans icône */}
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Revenus Totaux</p>
            <p className="text-2xl font-semibold text-gray-900">${billingStats?.total_revenue || 0}</p>
          </div>
        </div>

        {/* Temps de Réponse - Sans icône */}
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Temps de Réponse</p>
            <p className="text-2xl font-semibold text-gray-900">{performanceStats?.avg_response_time || 0}s</p>
          </div>
        </div>
      </div>

      {/* Main Content Grid - Style Compass avec layout exact */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Sources des Réponses - Table style Compass */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-base font-medium text-gray-900">Sources des Réponses</h3>
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
                          className={`h-2 ${getSourceColor(source)}`}
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                      <span className="text-sm font-medium text-gray-900 w-12 text-right">{count}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Santé du Système - Style Compass exact */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-base font-medium text-gray-900">Santé du Système</h3>
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
                <span className="text-sm font-medium text-green-600">
                  {performanceStats?.cache_hit_rate?.toFixed(1) || '0.0'}%
                </span>
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
            </div>
          </div>
        </div>
      </div>

      {/* Tables Section - Style Compass exact comme dans les images */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Top Users Table - Style exact Compass */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-base font-medium text-gray-900">Utilisateurs les Plus Actifs</h3>
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
                  <tr key={user.email} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm text-gray-900 truncate max-w-32">{user.email}</td>
                    <td className="px-4 py-2 text-sm text-gray-600">{user.question_count}</td>
                    <td className="px-4 py-2">
                      <span className={`inline-flex items-center px-2 py-1 text-xs font-medium ${
                        user.plan === 'enterprise' ? 'bg-purple-100 text-purple-800' :
                        user.plan === 'professional' ? 'bg-blue-100 text-blue-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {user.plan}
                      </span>
                    </td>
                  </tr>
                )) || []}
              </tbody>
            </table>
          </div>
        </div>

        {/* Plans Distribution - Style exact Compass */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-base font-medium text-gray-900">Répartition des Plans</h3>
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
          </div>
        </div>
      </div>

      {/* Costs Section - Style Compass exact avec fond blanc */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-base font-medium text-gray-900">Coûts et Performance</h3>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-white border border-gray-200">
              <p className="text-lg font-semibold text-red-600">${performanceStats?.openai_costs?.toFixed(2) || '0.00'}</p>
              <p className="text-xs text-gray-600">Coûts OpenAI</p>
            </div>
            <div className="text-center p-3 bg-white border border-gray-200">
              <p className="text-lg font-semibold text-yellow-600">{performanceStats?.error_count || 0}</p>
              <p className="text-xs text-gray-600">Erreurs</p>
            </div>
            <div className="text-center p-3 bg-white border border-gray-200">
              <p className="text-lg font-semibold text-green-600">{systemStats?.system_health?.total_requests || 0}</p>
              <p className="text-xs text-gray-600">Requêtes Totales</p>
            </div>
            <div className="text-center p-3 bg-white border border-gray-200">
              <p className="text-lg font-semibold text-blue-600">{usageStats?.questions_today || 0}</p>
              <p className="text-xs text-gray-600">Questions Aujourd'hui</p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}