import React from "react";

// Interfaces pour les données de statistiques
interface SystemStats {
  system_health: {
    uptime_hours: number;
    total_requests: number;
    error_rate: number;
    memory_percent_container?: number; // 🐳 NOUVEAU
    rag_status: {
      global: boolean;
      broiler: boolean;
      layer: boolean;
    };
  };
  billing_stats: {
    plans_available: number;
    plan_names: string[];
  };
  features_enabled: {
    analytics: boolean;
    billing: boolean;
    authentication: boolean;
    openai_fallback: boolean;
    container_memory_calculation?: boolean; // 🐳 NOUVEAU
  };
}

interface UsageStats {
  unique_users: number;
  total_questions: number;
  questions_today: number;
  questions_this_month: number;
  source_distribution: {
    rag_retriever: number;
    openai_fallback: number;
    perfstore: number;
  };
  monthly_breakdown: {
    [month: string]: number;
  };
}

interface BillingStats {
  plans: {
    [planName: string]: {
      user_count: number;
      revenue: number;
    };
  };
  total_revenue: number;
  top_users: Array<{
    email: string;
    first_name?: string;
    last_name?: string;
    question_count: number;
    plan: string;
  }>;
}

interface PerformanceStats {
  avg_response_time: number;
  median_response_time: number;
  min_response_time: number;
  max_response_time: number;
  response_time_count: number;
  openai_costs: number;
  error_count: number;
  cache_hit_rate: number;
  performance_gain?: number;
}

// Props avec support du cache (version production épurée)
interface StatisticsDashboardProps {
  systemStats: SystemStats | null;
  usageStats: UsageStats | null;
  billingStats: BillingStats | null;
  performanceStats: PerformanceStats | null;
  cacheStatus?: {
    is_available: boolean;
    last_update: string | null;
    cache_age_minutes: number;
    performance_gain: string;
    next_update: string | null;
  } | null;
  isLoading?: boolean;
}

export const StatisticsDashboard: React.FC<StatisticsDashboardProps> = ({
  systemStats,
  usageStats,
  billingStats,
  performanceStats,
  cacheStatus = null,
  isLoading = false,
}) => {
  // Indicateur de chargement amélioré
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement du tableau de bord...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* KPIs Row - Simplifié: 2 KPIs uniquement */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Utilisateurs Actifs */}
        <div className="bg-white border border-gray-200 p-6 relative">
          <div>
            <p className="text-sm text-gray-600 mb-1">Utilisateurs Actifs</p>
            <p className="text-3xl font-semibold text-gray-900">
              {usageStats?.unique_users || 0}
            </p>
            {cacheStatus?.is_available && (
              <div className="absolute top-2 right-2">
                <div
                  className="w-2 h-2 bg-green-500 rounded-full"
                  title="Données en cache"
                ></div>
              </div>
            )}
          </div>
        </div>

        {/* Questions ce mois */}
        <div className="bg-white border border-gray-200 p-6 relative">
          <div>
            <p className="text-sm text-gray-600 mb-1">Questions ce mois</p>
            <p className="text-3xl font-semibold text-gray-900">
              {usageStats?.questions_this_month || 0}
            </p>
            {cacheStatus?.is_available && (
              <div className="absolute top-2 right-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Table Utilisateurs les Plus Actifs - Pleine largeur */}
      <div className="mb-6">
        {/* Top Users Table */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-base font-medium text-gray-900">
              Utilisateurs les Plus Actifs
            </h3>
          </div>
          <div className="overflow-hidden">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Prénom
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Nom
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Courriel
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Questions
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Plan
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {billingStats?.top_users?.slice(0, 5).map((user, index) => (
                  <tr
                    key={user.email || `user-${index}`}
                    className="hover:bg-gray-50"
                  >
                    <td className="px-4 py-2 text-sm text-gray-900">
                      {user.first_name || "-"}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-900">
                      {user.last_name || "-"}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-900 max-w-48">
                      <div
                        className="truncate"
                        title={user.email || "Email non disponible"}
                      >
                        {user.email || "Utilisateur anonyme"}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600">
                      {user.question_count || 0}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`inline-flex items-center px-2 py-1 text-xs font-medium ${
                          user.plan === "enterprise"
                            ? "bg-purple-100 text-purple-800"
                            : user.plan === "professional"
                              ? "bg-blue-100 text-blue-800"
                              : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {user.plan || "non défini"}
                      </span>
                    </td>
                  </tr>
                )) || []}
                {(!billingStats?.top_users ||
                  billingStats.top_users.length === 0) && (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-8 text-center text-gray-500"
                    >
                      <div className="text-gray-400 text-2xl mb-2">👥</div>
                      <p>Aucune donnée utilisateur disponible</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </>
  );
};
