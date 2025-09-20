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
      {/* KPIs Row - Avec indicateurs discrets de cache */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {/* Utilisateurs Actifs */}
        <div className="bg-white border border-gray-200 p-4 relative">
          <div>
            <p className="text-sm text-gray-600 mb-1">Utilisateurs Actifs</p>
            <p className="text-2xl font-semibold text-gray-900">
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
        <div className="bg-white border border-gray-200 p-4 relative">
          <div>
            <p className="text-sm text-gray-600 mb-1">Questions ce mois</p>
            <p className="text-2xl font-semibold text-gray-900">
              {usageStats?.questions_this_month || 0}
            </p>
            {cacheStatus?.is_available && (
              <div className="absolute top-2 right-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              </div>
            )}
          </div>
        </div>

        {/* 🐳 NOUVEAU: Mémoire Conteneur */}
        <div className="bg-white border border-gray-200 p-4 relative">
          <div>
            <p className="text-sm text-gray-600 mb-1">Mémoire Conteneur</p>
            <p
              className={`text-2xl font-semibold ${
                (systemStats?.system_health?.memory_percent_container || 0) < 70
                  ? "text-green-600"
                  : (systemStats?.system_health?.memory_percent_container ||
                        0) < 85
                    ? "text-orange-600"
                    : "text-red-600"
              }`}
            >
              {systemStats?.system_health?.memory_percent_container?.toFixed(
                1,
              ) || "0.0"}
              %
            </p>
            {systemStats?.features_enabled?.container_memory_calculation && (
              <div className="absolute top-2 right-2">
                <div
                  className="w-2 h-2 bg-blue-500 rounded-full"
                  title="Calcul mémoire conteneur activé"
                ></div>
              </div>
            )}
          </div>
        </div>

        {/* Revenus Totaux */}
        <div className="bg-white border border-gray-200 p-4 relative">
          <div>
            <p className="text-sm text-gray-600 mb-1">Revenus Totaux</p>
            <p className="text-2xl font-semibold text-gray-900">
              ${billingStats?.total_revenue || 0}
            </p>
            {cacheStatus?.is_available && (
              <div className="absolute top-2 right-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Sources des Réponses */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-base font-medium text-gray-900">
              Sources des Réponses
            </h3>
          </div>
          <div className="p-4">
            <div className="space-y-3">
              {usageStats?.source_distribution &&
                Object.entries(usageStats.source_distribution).map(
                  ([source, count]) => {
                    const total = Object.values(
                      usageStats.source_distribution,
                    ).reduce((a, b) => a + b, 0);
                    const percentage =
                      total > 0 ? ((count / total) * 100).toFixed(1) : 0;

                    const getSourceColor = (source: string) => {
                      switch (source) {
                        case "rag_retriever":
                          return "bg-blue-500";
                        case "openai_fallback":
                          return "bg-purple-500";
                        case "perfstore":
                          return "bg-green-500";
                        default:
                          return "bg-gray-400";
                      }
                    };

                    const getSourceLabel = (source: string) => {
                      switch (source) {
                        case "rag_retriever":
                          return "RAG Retriever";
                        case "openai_fallback":
                          return "OpenAI Fallback";
                        case "perfstore":
                          return "Performance Store";
                        default:
                          return source;
                      }
                    };

                    return (
                      <div
                        key={source}
                        className="flex items-center justify-between"
                      >
                        <div className="flex items-center space-x-2">
                          <div
                            className={`w-3 h-3 ${getSourceColor(source)}`}
                          ></div>
                          <span className="text-sm text-gray-700">
                            {getSourceLabel(source)}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="w-16 bg-gray-200 h-2">
                            <div
                              className={`h-2 ${getSourceColor(source)} transition-all duration-300`}
                              style={{ width: `${percentage}%` }}
                            ></div>
                          </div>
                          <span className="text-sm font-medium text-gray-900 w-12 text-right">
                            {count}
                          </span>
                        </div>
                      </div>
                    );
                  },
                )}
            </div>
          </div>
        </div>

        {/* Santé du Système - ÉTENDUE avec mémoire */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-base font-medium text-gray-900">
              Santé du Système
            </h3>
          </div>
          <div className="p-4">
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Uptime</span>
                <span className="text-sm font-medium text-gray-900">
                  {systemStats?.system_health?.uptime_hours?.toFixed(1) ||
                    "0.0"}
                  h
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Taux d'erreur</span>
                <span
                  className={`text-sm font-medium ${(systemStats?.system_health?.error_rate || 0) < 5 ? "text-green-600" : "text-red-600"}`}
                >
                  {systemStats?.system_health?.error_rate?.toFixed(1) || "0.0"}%
                </span>
              </div>

              {/* 🐳 NOUVEAU: Métriques mémoire détaillées */}
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Mémoire conteneur</span>
                <div className="flex items-center space-x-2">
                  <span
                    className={`text-sm font-medium ${
                      (systemStats?.system_health?.memory_percent_container ||
                        0) < 70
                        ? "text-green-600"
                        : (systemStats?.system_health
                              ?.memory_percent_container || 0) < 85
                          ? "text-orange-600"
                          : "text-red-600"
                    }`}
                  >
                    {systemStats?.system_health?.memory_percent_container?.toFixed(
                      1,
                    ) || "0.0"}
                    %
                  </span>
                  {systemStats?.features_enabled
                    ?.container_memory_calculation && (
                    <span
                      className="text-xs bg-blue-100 text-blue-800 px-1 py-0.5 rounded"
                      title="Calcul mémoire conteneur activé"
                    >
                      Docker
                    </span>
                  )}
                </div>
              </div>

              {/* Barre de progression mémoire */}
              {systemStats?.system_health?.memory_percent_container !==
                undefined && (
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Utilisation mémoire</span>
                    <span>
                      {systemStats.system_health.memory_percent_container < 50
                        ? "Optimale"
                        : systemStats.system_health.memory_percent_container <
                            70
                          ? "Normale"
                          : systemStats.system_health.memory_percent_container <
                              85
                            ? "Élevée"
                            : "Critique"}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-2 rounded-full transition-all duration-500 ${
                        systemStats.system_health.memory_percent_container < 50
                          ? "bg-green-500"
                          : systemStats.system_health.memory_percent_container <
                              70
                            ? "bg-blue-500"
                            : systemStats.system_health
                                  .memory_percent_container < 85
                              ? "bg-orange-500"
                              : "bg-red-500"
                      }`}
                      style={{
                        width: `${Math.min(100, systemStats.system_health.memory_percent_container)}%`,
                      }}
                    ></div>
                  </div>
                </div>
              )}

              <div className="pt-3 border-t border-gray-200">
                <p className="text-sm font-medium text-gray-900 mb-2">
                  Services RAG
                </p>
                <div className="space-y-2">
                  {systemStats?.system_health?.rag_status &&
                    Object.entries(systemStats.system_health.rag_status).map(
                      ([service, status]) => (
                        <div
                          key={service}
                          className="flex justify-between items-center"
                        >
                          <span className="text-xs text-gray-600 capitalize">
                            {service}
                          </span>
                          <span
                            className={`text-xs px-2 py-1 ${status ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}
                          >
                            {status ? "Actif" : "Inactif"}
                          </span>
                        </div>
                      ),
                    )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tables Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
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
                    Utilisateur
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
                      colSpan={3}
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

        {/* Plans Distribution */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-base font-medium text-gray-900">
              Répartition des Plans
            </h3>
          </div>
          <div className="p-4">
            <div className="space-y-3">
              {billingStats?.plans &&
                Object.entries(billingStats.plans).map(([planName, data]) => (
                  <div
                    key={planName}
                    className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900 capitalize">
                        {planName}
                      </p>
                      <p className="text-xs text-gray-600">
                        {data.user_count} utilisateurs
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-gray-900">
                        ${data.revenue}
                      </p>
                      <p className="text-xs text-gray-600">revenus</p>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>

      {/* Costs and Performance Section - ÉTENDUE */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-base font-medium text-gray-900">
            Coûts et Performance
          </h3>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Coûts OpenAI */}
            <div className="text-center p-3 bg-white border border-gray-200">
              <p className="text-lg font-semibold text-gray-900">
                ${performanceStats?.openai_costs?.toFixed(2) || "0.00"}
              </p>
              <p className="text-xs text-gray-600">Coûts OpenAI</p>
            </div>

            {/* Erreurs */}
            <div className="text-center p-3 bg-white border border-gray-200">
              <p className="text-lg font-semibold text-gray-900">
                {performanceStats?.error_count || 0}
              </p>
              <p className="text-xs text-gray-600">Erreurs</p>
            </div>

            {/* Requêtes Totales */}
            <div className="text-center p-3 bg-white border border-gray-200">
              <p className="text-lg font-semibold text-gray-900">
                {systemStats?.system_health?.total_requests || 0}
              </p>
              <p className="text-xs text-gray-600">Requêtes Totales</p>
            </div>

            {/* 🐳 NOUVEAU: Santé Mémoire */}
            <div className="text-center p-3 bg-white border border-gray-200">
              <p
                className={`text-lg font-semibold ${
                  (systemStats?.system_health?.memory_percent_container || 0) <
                  70
                    ? "text-green-600"
                    : (systemStats?.system_health?.memory_percent_container ||
                          0) < 85
                      ? "text-orange-600"
                      : "text-red-600"
                }`}
              >
                {systemStats?.features_enabled?.container_memory_calculation
                  ? "Optimisé"
                  : "Standard"}
              </p>
              <p className="text-xs text-gray-600">Calcul Mémoire</p>
            </div>
          </div>

          {/* Section de métriques de performance détaillées */}
          {performanceStats && (
            <div className="mt-6 pt-4 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-900 mb-3">
                Métriques de Performance Détaillées
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white border border-gray-200 p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-800">
                      Temps Médian
                    </span>
                  </div>
                  <p className="text-lg font-semibold text-blue-900">
                    {performanceStats.median_response_time?.toFixed(1) || "0.0"}
                    s
                  </p>
                  <p className="text-xs text-blue-700 mt-1">
                    Temps de réponse médian
                  </p>
                </div>

                <div className="bg-white border border-gray-200 p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-green-800">
                      Min/Max
                    </span>
                  </div>
                  <p className="text-lg font-semibold text-green-900">
                    {performanceStats.min_response_time?.toFixed(1) || "0.0"}s /{" "}
                    {performanceStats.max_response_time?.toFixed(1) || "0.0"}s
                  </p>
                  <p className="text-xs text-green-700 mt-1">
                    Temps min et max
                  </p>
                </div>

                <div className="bg-white border border-gray-200 p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-purple-800">
                      Cache Hit
                    </span>
                  </div>
                  <p className="text-lg font-semibold text-purple-900">
                    {performanceStats.cache_hit_rate?.toFixed(1) || "0.0"}%
                  </p>
                  <p className="text-xs text-purple-700 mt-1">
                    Taux de succès cache
                  </p>
                </div>
              </div>

              {/* Barre de progression des performances */}
              {performanceStats.avg_response_time && (
                <div className="mt-4">
                  <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                    <span>Performance globale du système</span>
                    <span>
                      {performanceStats.avg_response_time < 2
                        ? "Excellent"
                        : performanceStats.avg_response_time < 5
                          ? "Bon"
                          : performanceStats.avg_response_time < 10
                            ? "Acceptable"
                            : "À améliorer"}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-2 rounded-full transition-all duration-500 ${
                        performanceStats.avg_response_time < 2
                          ? "bg-green-500"
                          : performanceStats.avg_response_time < 5
                            ? "bg-blue-500"
                            : performanceStats.avg_response_time < 10
                              ? "bg-yellow-500"
                              : "bg-red-500"
                      }`}
                      style={{
                        width: `${Math.min(100, Math.max(10, 100 - performanceStats.avg_response_time * 5))}%`,
                      }}
                    ></div>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Rapide (&lt;2s)</span>
                    <span>Lent (&gt;10s)</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
};
