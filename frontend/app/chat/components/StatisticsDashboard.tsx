'use client'

import React from 'react'

// === Types (compatible with original) ===
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
  features_enabled?: {
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
  monthly_breakdown: { [month: string]: number }
}

interface BillingStats {
  plans?: {
    [planName: string]: {
      user_count: number
      revenue: number
    }
  }
  total_revenue: number
  top_users?: Array<{
    email: string
    question_count: number
    plan: string
  }>
}

interface PerformanceStats {
  avg_response_time: number
  openai_costs?: number
  error_count?: number
  cache_hit_rate: number
}

interface StatisticsDashboardProps {
  systemStats: SystemStats | null
  usageStats: UsageStats | null
  billingStats: BillingStats | null
  performanceStats: PerformanceStats | null
  /** Nouvel attribut optionnel : utilisateurs actifs du mois précédent (calculé dans StatisticsPage) */
  activePrevMonth?: number
}

export const StatisticsDashboard: React.FC<StatisticsDashboardProps> = ({
  systemStats,
  usageStats,
  billingStats,
  performanceStats,
  activePrevMonth
}) => {
  // --- Ajouts: série 12 mois + export CSV ---
  const monthlyEntries = usageStats?.monthly_breakdown
    ? Object.entries(usageStats.monthly_breakdown).sort(([a],[b])=>a.localeCompare(b)).slice(-12)
    : []
  const monthlySeries = monthlyEntries.map(([ym, v]) => {
    const [yy, mm] = ym.split('-')
    const label = new Date(Number(yy), Number(mm)-1, 1).toLocaleDateString('fr-FR', { month: 'short' })
    return { label, value: Number(v) || 0 }
  })
  const monthlyMax = Math.max(1, ...monthlySeries.map(d=>d.value))

  const sourceDist = usageStats?.source_distribution || { rag_retriever:0, openai_fallback:0, perfstore:0 }
  const sources = [
    { name:'RAG', value: sourceDist.rag_retriever },
    { name:'OpenAI', value: sourceDist.openai_fallback },
    { name:'Perfstore', value: sourceDist.perfstore },
  ]
  const sourceMax = Math.max(1, ...sources.map(s=>s.value))
  const sourceTotal = sources.reduce((s,x)=>s+x.value,0)

  function exportStatsCSV(){
    const lines:string[] = []
    lines.push('Section,Clé,Valeur')
    lines.push(`KPI,Utilisateurs actifs,${usageStats?.unique_users ?? 0}`)
    if (typeof activePrevMonth === 'number') lines.push(`KPI,Utilisateurs actifs (mois précédent),${activePrevMonth}`)
    lines.push(`KPI,Questions total,${usageStats?.total_questions ?? 0}`)
    lines.push(`KPI,Questions ce mois,${usageStats?.questions_this_month ?? 0}`)
    lines.push(`KPI,Questions aujourd\'hui,${usageStats?.questions_today ?? 0}`)
    lines.push(`KPI,Revenus totaux,$${billingStats?.total_revenue ?? 0}`)
    lines.push(`KPI,Temps moyen de réponse,${performanceStats?.avg_response_time ?? 0}s`)
    lines.push(`KPI,Cache hit,${performanceStats?.cache_hit_rate ?? 0}%`)
    const csv = 'data:text/csv;charset=utf-8,' + encodeURIComponent(lines.join('\n'))
    const a = document.createElement('a'); a.href = csv; a.download = 'stats_export.csv'; document.body.appendChild(a); a.click(); a.remove()
  }

  // Sécurité sur données nulles
  const sys = systemStats
  const use = usageStats
  const bill = billingStats
  const perf = performanceStats

  // 12 derniers mois (étiquettes FR) — hauteur réduite (~40%) via h-24
  const monthlyEntries = use?.monthly_breakdown
    ? Object.entries(use.monthly_breakdown).sort(([a],[b])=>a.localeCompare(b)).slice(-12)
    : []
  const monthlySeries = monthlyEntries.map(([ym, v]) => {
    const [yy, mm] = ym.split('-')
    const label = new Date(Number(yy), Number(mm)-1, 1).toLocaleDateString('fr-FR', { month: 'short' })
    return { label, value: Number(v) || 0 }
  })
  const monthlyMax = Math.max(1, ...monthlySeries.map(d=>d.value))

  const sourceDist = use?.source_distribution || { rag_retriever:0, openai_fallback:0, perfstore:0 }
  const sources = [
    { name:'RAG', value: sourceDist.rag_retriever },
    { name:'OpenAI', value: sourceDist.openai_fallback },
    { name:'Perfstore', value: sourceDist.perfstore },
  ]
  const sourceMax = Math.max(1, ...sources.map(s=>s.value))
  const sourceTotal = sources.reduce((s,x)=>s+x.value,0)

  // Export CSV (statistiques)
  function exportStatsCSV(){
    const lines:string[] = []
    lines.push('Section,Clé,Valeur')
    lines.push(`KPI,Utilisateurs actifs,${use?.unique_users ?? 0}`)
    if (typeof activePrevMonth === 'number') lines.push(`KPI,Utilisateurs actifs (mois précédent),${activePrevMonth}`)
    lines.push(`KPI,Questions total,${use?.total_questions ?? 0}`)
    lines.push(`KPI,Questions ce mois,${use?.questions_this_month ?? 0}`)
    lines.push(`KPI,Questions aujourd'hui,${use?.questions_today ?? 0}`)
    lines.push(`KPI,Revenus totaux,$${bill?.total_revenue ?? 0}`)
    lines.push(`KPI,Temps moyen de réponse,${perf?.avg_response_time ?? 0}s`)
    lines.push(`KPI,Cache hit,${perf?.cache_hit_rate ?? 0}%`)
    if (typeof perf?.openai_costs === 'number') lines.push(`Coûts,OpenAI,$${perf.openai_costs}`)
    if (typeof perf?.error_count === 'number') lines.push(`Système,Erreurs,${perf.error_count}`)
    if (typeof sys?.system_health?.total_requests === 'number') lines.push(`Système,Requêtes totales,${sys.system_health.total_requests}`)

    lines.push('Mensuel,Mois,Questions')
    monthlyEntries.forEach(([m, v]) => lines.push(`Mensuel,${m},${v}`))

    lines.push('Sources,Nom,Valeur')
    sources.forEach(s => lines.push(`Sources,${s.name},${s.value}`))

    const csv = 'data:text/csv;charset=utf-8,' + encodeURIComponent(lines.join('\n'))
    const a = document.createElement('a')
    a.href = csv; a.download = 'stats_export.csv'
    document.body.appendChild(a); a.click(); a.remove()
  }

  return (
    <>
      {/* Toolbar (export) */}
      <div className="flex items-center justify-end mb-4">
        <button
          onClick={exportStatsCSV}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700"
        >
          ⬇ Exporter
        </button>
      </div>

      {/* KPIs */}
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
              <p className="text-2xl font-bold text-gray-900">{use?.unique_users ?? 0}</p>
              {typeof activePrevMonth === 'number' && (
                <p className="text-xs text-gray-500 mt-1">Mois précédent: {activePrevMonth} utilisateurs actifs</p>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h18M9 7v14m6-14v14" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Questions ce mois</p>
              <p className="text-2xl font-bold text-gray-900">{use?.questions_this_month ?? 0}</p>
              <p className="text-xs text-gray-500 mt-1">Aujourd'hui: {use?.questions_today ?? 0}</p>
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
              <p className="text-2xl font-bold text-gray-900">${bill?.total_revenue ?? 0}</p>
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
              <p className="text-2xl font-bold text-gray-900">{perf?.avg_response_time ?? 0}s</p>
              <p className="text-xs text-gray-500 mt-1">Cache hit: {perf?.cache_hit_rate ?? 0}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Activité — 12 derniers mois */}
      <div className="bg-white p-6 rounded-lg shadow-sm border mb-8">
        <div className="mb-2">
          <h3 className="text-lg font-semibold text-gray-900">Activité — 12 derniers mois</h3>
          <p className="text-xs text-gray-500">Questions / mois</p>
        </div>
        <div className="h-24 flex items-end gap-2">
          {monthlySeries.map((d, i) => {
            const h = Math.max(4, Math.round((d.value / monthlyMax) * 88)) // hauteur compacte
            return (
              <div key={i} className="flex flex-col items-center gap-1">
                <div className="w-6 rounded-md bg-blue-500" style={{ height: h }} />
                <span className="text-[10px] text-gray-500">{d.label}</span>
              </div>
            )
          })}
          {monthlySeries.length === 0 && (
            <div className="text-sm text-gray-500">Aucune donnée mensuelle</div>
          )}
        </div>
      </div>

      {/* Sources des réponses */}
      <div className="bg-white p-6 rounded-lg shadow-sm border mb-8">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Sources des réponses</h3>
          <span className="text-xs text-gray-500">Total: {sourceTotal}</span>
        </div>
        <div className="space-y-3">
          {sources.map((s, i) => {
            const w = Math.round((s.value / sourceMax) * 100)
            const pct = sourceTotal > 0 ? ((s.value / sourceTotal) * 100).toFixed(1) : '0.0'
            return (
              <div key={i} className="flex items-center gap-2">
                <div className="w-32 text-sm text-gray-700">{s.name}</div>
                <div className="flex-1 h-2 rounded-full bg-gray-200">
                  <div className="h-2 rounded-full bg-indigo-600" style={{ width: `${w}%` }} />
                </div>
                <div className="w-24 text-right text-sm text-gray-700">{s.value} ({pct}%)</div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Santé système / mini cartes */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-xl border p-4"><p className="text-xs text-gray-500">Uptime</p><p className="mt-1 text-lg font-semibold">{sys?.system_health?.uptime_hours?.toFixed?.(1) ?? '0.0'}h</p></div>
        <div className="rounded-xl border p-4"><p className="text-xs text-gray-500">Taux d’erreur</p><p className="mt-1 text-lg font-semibold">{sys?.system_health?.error_rate?.toFixed?.(1) ?? '0.0'}%</p></div>
        <div className="rounded-xl border p-4"><p className="text-xs text-gray-500">Requêtes</p><p className="mt-1 text-lg font-semibold">{(sys?.system_health?.total_requests ?? 0).toLocaleString()}</p></div>
        <div className="rounded-xl border p-4"><p className="text-xs text-gray-500">RAG Global</p><p className="mt-1 text-lg font-semibold">{sys?.system_health?.rag_status?.global ? 'Actif' : 'Inactif'}</p></div>
      </div>
    </>
  )
}
