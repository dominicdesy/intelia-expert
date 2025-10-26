"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

interface MetricRecord {
  recorded_at: string;
  model: string;
  provider: string;
  feature: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  request_count: number;
}

interface MetricsHistoryResponse {
  success: boolean;
  count: number;
  start_date: string;
  end_date: string;
  metrics: MetricRecord[];
}

interface MonthlySummary {
  month: string;
  total_cost_usd: number;
  total_tokens: number;
  total_requests: number;
  unique_models: number;
}

interface MetricsSummary {
  totalCost: number;
  totalTokens: number;
  totalRequests: number;
  costByModel: Array<{ model: string; cost: number }>;
  tokensByModel: Array<{ model: string; tokens: number }>;
  tokensByType: Array<{ type: string; tokens: number }>;
  monthlyData: MonthlySummary[];
  lastSync: string | null;
}

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884D8"];

export default function PrometheusMetrics() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<MetricsSummary>({
    totalCost: 0,
    totalTokens: 0,
    totalRequests: 0,
    costByModel: [],
    tokensByModel: [],
    tokensByType: [],
    monthlyData: [],
    lastSync: null,
  });

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch monthly summary (last 6 months)
      const monthlyResponse = await fetch(
        "/api/v1/metrics/metrics-monthly-summary?months=6"
      );

      if (!monthlyResponse.ok) {
        throw new Error("Failed to fetch monthly metrics");
      }

      const monthlyData = await monthlyResponse.json();

      // Calculate totals from monthly data
      const totalCost = monthlyData.summary.reduce(
        (sum: number, month: MonthlySummary) => sum + month.total_cost_usd,
        0
      );
      const totalTokens = monthlyData.summary.reduce(
        (sum: number, month: MonthlySummary) => sum + month.total_tokens,
        0
      );
      const totalRequests = monthlyData.summary.reduce(
        (sum: number, month: MonthlySummary) => sum + month.total_requests,
        0
      );

      // Fetch detailed history for current month to get breakdown by model
      const now = new Date();
      const firstDayOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
      const startDate = firstDayOfMonth.toISOString().split("T")[0];

      const historyResponse = await fetch(
        `/api/v1/metrics/metrics-history?start_date=${startDate}`
      );

      if (!historyResponse.ok) {
        throw new Error("Failed to fetch metrics history");
      }

      const historyData: MetricsHistoryResponse = await historyResponse.json();

      // Aggregate by model
      const modelCosts: Record<string, number> = {};
      const modelTokens: Record<string, number> = {};
      const typeTotals: Record<string, number> = {
        prompt: 0,
        completion: 0,
      };

      historyData.metrics.forEach((record) => {
        // Cost by model
        if (!modelCosts[record.model]) {
          modelCosts[record.model] = 0;
        }
        modelCosts[record.model] += record.cost_usd;

        // Tokens by model
        if (!modelTokens[record.model]) {
          modelTokens[record.model] = 0;
        }
        modelTokens[record.model] += record.total_tokens;

        // Tokens by type
        typeTotals.prompt += record.prompt_tokens;
        typeTotals.completion += record.completion_tokens;
      });

      const costByModel = Object.entries(modelCosts).map(([model, cost]) => ({
        model,
        cost,
      }));

      const tokensByModel = Object.entries(modelTokens).map(
        ([model, tokens]) => ({
          model,
          tokens,
        })
      );

      const tokensByType = [
        { type: "prompt", tokens: typeTotals.prompt },
        { type: "completion", tokens: typeTotals.completion },
      ].filter((t) => t.tokens > 0);

      setMetrics({
        totalCost,
        totalTokens,
        totalRequests,
        costByModel,
        tokensByModel,
        tokensByType,
        monthlyData: monthlyData.summary,
        lastSync: new Date().toISOString(),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
      console.error("Failed to fetch metrics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 60000); // Refresh every 60s
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Chargement des métriques...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-red-800 font-semibold mb-2">
          Erreur de connexion à Prometheus
        </h3>
        <p className="text-red-600 text-sm">{error}</p>
        <button
          onClick={fetchMetrics}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Réessayer
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="text-sm text-blue-600 font-medium mb-1">
            Coût Total
          </div>
          <div className="text-3xl font-bold text-blue-900">
            ${metrics.totalCost.toFixed(4)}
          </div>
          <div className="text-xs text-blue-500 mt-1">USD</div>
        </div>

        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="text-sm text-green-600 font-medium mb-1">
            Tokens Totaux
          </div>
          <div className="text-3xl font-bold text-green-900">
            {metrics.totalTokens.toLocaleString()}
          </div>
          <div className="text-xs text-green-500 mt-1">tokens</div>
        </div>

        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
          <div className="text-sm text-purple-600 font-medium mb-1">
            Requêtes Totales
          </div>
          <div className="text-3xl font-bold text-purple-900">
            {metrics.totalRequests}
          </div>
          <div className="text-xs text-purple-500 mt-1">requêtes</div>
        </div>
      </div>

      {/* Monthly Cost Trend - Most Important Chart */}
      {metrics.monthlyData.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            📈 Évolution des Coûts LLM (6 derniers mois)
          </h3>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={metrics.monthlyData.slice().reverse()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip
                formatter={(value: number) => `$${value.toFixed(2)}`}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="total_cost_usd"
                stroke="#0088FE"
                strokeWidth={2}
                name="Coût mensuel (USD)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost by Model (Current Month) */}
        {metrics.costByModel.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Coût par Modèle (Mois en cours)
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={metrics.costByModel}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="model" />
                <YAxis />
                <Tooltip
                  formatter={(value: number) => `$${value.toFixed(6)}`}
                />
                <Legend />
                <Bar dataKey="cost" fill="#0088FE" name="Coût (USD)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Tokens by Type */}
        {metrics.tokensByType.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Répartition Tokens (Prompt vs Completion)
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={metrics.tokensByType}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.type}: ${entry.tokens.toLocaleString()}`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="tokens"
                >
                  {metrics.tokensByType.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => value.toLocaleString()} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Tokens by Model */}
        {metrics.tokensByModel.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Tokens par Modèle (Mois en cours)
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={metrics.tokensByModel}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="model" />
                <YAxis />
                <Tooltip formatter={(value: number) => value.toLocaleString()} />
                <Legend />
                <Bar dataKey="tokens" fill="#00C49F" name="Tokens" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Monthly Summary Table */}
        {metrics.monthlyData.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-6 lg:col-span-2">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              📊 Résumé Mensuel
            </h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Mois
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Coût Total
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tokens
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Requêtes
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Modèles
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {metrics.monthlyData.map((month) => (
                    <tr key={month.month}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {month.month}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${month.total_cost_usd.toFixed(4)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {month.total_tokens.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {month.total_requests}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {month.unique_models}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Refresh Info */}
      <div className="text-center text-sm text-gray-500">
        <p>Mise à jour automatique toutes les 60 secondes</p>
        {metrics.lastSync && (
          <p className="text-xs text-gray-400 mt-1">
            Dernière mise à jour: {new Date(metrics.lastSync).toLocaleTimeString('fr-FR')}
          </p>
        )}
        <p className="text-xs text-gray-400 mt-1">
          💡 Les données sont synchronisées quotidiennement depuis Prometheus vers PostgreSQL
        </p>
      </div>
    </div>
  );
}
