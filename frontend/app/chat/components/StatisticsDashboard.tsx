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
      {/* KPIs Row - Style Compass */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Utilisateurs Actifs */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM9 3a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900">{usageStats?.unique_users || 0}</p>
              <p className="text-sm font-medium text-gray-500">Utilisateurs Actifs</p>
            </div>
          </div>
        </div>

        {/* Questions ce mois */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center shadow-lg">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900">{usageStats?.questions_this_month || 0}</p>
              <p className="text-sm font-medium text-gray-500">Questions ce mois</p>
            </div>
          </div>
        </div>

        {/* Revenus Totaux */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="w-12 h-12 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl flex items-center justify-center shadow-lg">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                </svg>
              </div>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900">${billingStats?.total_revenue || 0}</p>
              <p className="text-sm font-medium text-gray-500">Revenus Totaux</p>
            </div>
          </div>
        </div>

        {/* Temps de Réponse */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900">{performanceStats?.avg_response_time || 0}s</p>
              <p className="text-sm font-medium text-gray-500">Temps de Réponse</p>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row - Style Compass */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-8">
        {/* Sources des Réponses */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Sources des Réponses</h3>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span className="text-xs text-gray-500 font-medium">Distribution actuelle</span>
            </div>
          </div>
          <div className="space-y-5">
            {usageStats?.source_distribution && Object.entries(usageStats.source_distribution).map(([source, count]) => {
              const total = Object.values(usageStats.source_distribution).reduce((a, b) => a + b, 0)
              const percentage = total > 0 ? (count / total * 100).toFixed(1) : 0
              
              const getSourceColor = (source: string) => {
                switch (source) {
                  case 'rag_retriever': return 'bg-blue-500'
                  case 'openai_fallback': return 'bg-purple-500'
                  case 'perfstore': return 'bg-emerald-500'
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
                <div key={source} className="flex items-center space-x-4">
                  <div className="flex items-center space-x-3 w-40">
                    <div className={`w-3 h-3 rounded-full ${getSourceColor(source)}`}></div>
                    <span className="text-sm font-medium text-gray-700">{getSourceLabel(source)}</span>
                  </div>
                  <div className="flex-1">
                    <div className="bg-gray-100 rounded-full h-2 overflow-hidden">
                      <div 
                        className={`h-2 rounded-full transition-all duration-700 ease-out ${getSourceColor(source)}`}
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                  </div>
                  <div className="text-right w-20">
                    <div className="text-sm font-bold text-gray-900">{count}</div>
                    <div className="text-xs text-gray-500">{percentage}%</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Santé du Système */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Santé du Système</h3>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
              <span className="text-xs text-emerald-600 font-medium">En ligne</span>
            </div>
          </div>
          
          <div className="space-y-6">
            {/* Métriques principales */}
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-600">Uptime</span>
                  <span className="text-lg font-bold text-gray-900">
                    {systemStats?.system_health?.uptime_hours?.toFixed(1) || '0.0'}h
                  </span>
                </div>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-600">Taux d'erreur</span>
                  <span className={`text-lg font-bold ${(systemStats?.system_health?.error_rate || 0) < 5 ? 'text-emerald-600' : 'text-red-500'}`}>
                    {systemStats?.system_health?.error_rate?.toFixed(1) || '0.0'}%
                  </span>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-600">Cache Hit Rate</span>
                <span className="text-lg font-bold text-emerald-600">
                  {performanceStats?.cache_hit_rate?.toFixed(1) || '0.0'}%
                </span>
              </div>
            </div>
            
            {/* Services RAG */}
            <div className="border-t border-gray-100 pt-6">
              <h4 className="text-sm font-semibold text-gray-900 mb-4">Services RAG</h4>
              <div className="grid grid-cols-1 gap-3">
                {systemStats?.system_health?.rag_status && Object.entries(systemStats.system_health.rag_status).map(([service, status]) => (
                  <div key={service} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-sm font-medium text-gray-700 capitalize">{service}</span>
                    <div className="flex items-center space-x-2">
                      <div className={`w-2 h-2 rounded-full ${status ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
                      <span className={`text-xs font-medium ${status ? 'text-emerald-700' : 'text-red-700'}`}>
                        {status ? 'Actif' : 'Inactif'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tables Row - Style Compass */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-8">
        {/* Top Users */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Utilisateurs les Plus Actifs</h3>
            <span className="text-xs text-gray-500 font-medium">Ce mois</span>
          </div>
          <div className="overflow-hidden">
            <div className="space-y-3">
              {billingStats?.top_users?.slice(0, 5).map((user, index) => (
                <div key={user.email} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center text-white text-xs font-bold">
                      {index + 1}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-900 truncate max-w-40">{user.email}</div>
                      <div className="text-xs text-gray-500">{user.question_count} questions</div>
                    </div>
                  </div>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    user.plan === 'enterprise' ? 'bg-purple-100 text-purple-700' :
                    user.plan === 'professional' ? 'bg-blue-100 text-blue-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {user.plan}
                  </span>
                </div>
              )) || []}
            </div>
          </div>
        </div>

        {/* Plans Distribution */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Répartition des Plans</h3>
            <span className="text-xs text-gray-500 font-medium">Revenus actifs</span>
          </div>
          <div className="space-y-4">
            {billingStats?.plans && Object.entries(billingStats.plans).map(([planName, data]) => (
              <div key={planName} className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg p-4 border border-gray-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-white text-sm font-bold ${
                      planName === 'enterprise' ? 'bg-gradient-to-br from-purple-500 to-purple-600' :
                      planName === 'professional' ? 'bg-gradient-to-br from-blue-500 to-blue-600' :
                      planName === 'basic' ? 'bg-gradient-to-br from-emerald-500 to-emerald-600' :
                      'bg-gradient-to-br from-gray-400 to-gray-500'
                    }`}>
                      {planName.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900 capitalize">{planName}</p>
                      <p className="text-xs text-gray-600">{data.user_count} utilisateurs</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-gray-900">${data.revenue}</p>
                    <p className="text-xs text-gray-600">revenus</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Coûts et Performance - Style Compass */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">Coûts et Performance</h3>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
            <span className="text-xs text-gray-500 font-medium">Dernières 24h</span>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Coûts OpenAI */}
          <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-xl p-6 border border-red-200">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                </svg>
              </div>
            </div>
            <div className="mt-4">
              <p className="text-2xl font-bold text-red-700">${performanceStats?.openai_costs?.toFixed(2) || '0.00'}</p>
              <p className="text-sm font-medium text-red-600">Coûts OpenAI</p>
            </div>
          </div>

          {/* Erreurs */}
          <div className="bg-gradient-to-br from-amber-50 to-orange-100 rounded-xl p-6 border border-amber-200">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
            </div>
            <div className="mt-4">
              <p className="text-2xl font-bold text-amber-700">{performanceStats?.error_count || 0}</p>
              <p className="text-sm font-medium text-amber-600">Erreurs</p>
            </div>
          </div>

          {/* Requêtes Totales */}
          <div className="bg-gradient-to-br from-emerald-50 to-green-100 rounded-xl p-6 border border-emerald-200">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-green-500 rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
            </div>
            <div className="mt-4">
              <p className="text-2xl font-bold text-emerald-700">{systemStats?.system_health?.total_requests || 0}</p>
              <p className="text-sm font-medium text-emerald-600">Requêtes Totales</p>
            </div>
          </div>

          {/* Questions Aujourd'hui */}
          <div className="bg-gradient-to-br from-blue-50 to-indigo-100 rounded-xl p-6 border border-blue-200">
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-500 rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
            </div>
            <div className="mt-4">
              <p className="text-2xl font-bold text-blue-700">{usageStats?.questions_today || 0}</p>
              <p className="text-sm font-medium text-blue-600">Questions Aujourd'hui</p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}