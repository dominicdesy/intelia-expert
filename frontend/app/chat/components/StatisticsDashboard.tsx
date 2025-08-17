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
                {systemStats?.system_health?.uptime_hours?.toFixed(1) || '0.0'}h
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Taux d'erreur</span>
              <span className={`text-sm font-medium ${(systemStats?.system_health?.error_rate || 0) < 5 ? 'text-green-600' : 'text-red-600'}`}>
                {systemStats?.system_health?.error_rate?.toFixed(1) || '0.0'}%
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Cache Hit Rate</span>
              <span className="text-sm font-medium text-green-600">
                {performanceStats?.cache_hit_rate?.toFixed(1) || '0.0'}%
              </span>
            </div>
            
            <div className="mt-4 pt-4 border-t">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Services RAG</h4>
              <div className="space-y-2">
                {systemStats?.system_health?.rag_status && Object.entries(systemStats.system_health.rag_status).map(([service, status]) => (
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
                {billingStats?.top_users?.map((user, index) => (
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
                )) || []}
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
            <p className="text-2xl font-bold text-red-600">${performanceStats?.openai_costs?.toFixed(2) || '0.00'}</p>
            <p className="text-sm text-gray-600">Coûts OpenAI</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-yellow-600">{performanceStats?.error_count || 0}</p>
            <p className="text-sm text-gray-600">Erreurs</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">{systemStats?.system_health?.total_requests || 0}</p>
            <p className="text-sm text-gray-600">Requêtes Totales</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-600">{usageStats?.questions_today || 0}</p>
            <p className="text-sm text-gray-600">Questions Aujourd'hui</p>
          </div>
        </div>
      </div>
    </>
  )
}