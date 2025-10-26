"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
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
  Area,
  AreaChart,
  ComposedChart,
} from "recharts";

// ============================================
// TYPES
// ============================================

interface CostByUser {
  user_id: string;
  email: string;
  total_cost_usd: number;
  total_tokens: number;
  total_requests: number;
  models_used: number;
}

interface TokenRatio {
  model: string;
  provider: string;
  avg_prompt_tokens: number;
  avg_completion_tokens: number;
  completion_to_prompt_ratio: number;
  total_requests: number;
}

interface ErrorRate {
  provider: string;
  total_requests: number;
  successful_requests: number;
  error_requests: number;
  error_rate_percent: number;
}

interface InfrastructureCost {
  date: string;
  llm_cost_usd: number;
  do_cost_usd: number;
  weaviate_cost_usd: number;
  supabase_cost_usd: number;
  twilio_cost_usd: number;
  mrr_usd: number;
  total_cost_usd: number;
  margin_usd: number;
}

interface MonthlySummary {
  month: string;
  total_cost_usd: number;
  total_tokens: number;
  total_requests: number;
}

interface BusinessMetrics {
  // LLM Analytics
  costByUser: CostByUser[];
  tokenRatios: TokenRatio[];
  errorRates: ErrorRate[];
  monthlyLLM: MonthlySummary[];

  // Infrastructure Costs
  infrastructureCosts: InfrastructureCost[];

  // Summary
  totalLLMCost: number;
  totalInfraCost: number;
  totalRevenue: number;
  netMargin: number;

  lastSync: string | null;
}

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884D8", "#FF6B9D", "#C9E4DE", "#845EC2"];

// ============================================
// COMPONENT
// ============================================

export default function BusinessAnalytics() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<BusinessMetrics>({
    costByUser: [],
    tokenRatios: [],
    errorRates: [],
    monthlyLLM: [],
    infrastructureCosts: [],
    totalLLMCost: 0,
    totalInfraCost: 0,
    totalRevenue: 0,
    netMargin: 0,
    lastSync: null,
  });

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch all metrics in parallel using apiClient.getSecure
      const [
        costByUserRes,
        tokenRatiosRes,
        errorRatesRes,
        monthlyLLMRes,
        infraCostsRes
      ] = await Promise.all([
        apiClient.getSecure("metrics/cost-by-user?limit=20"),
        apiClient.getSecure("metrics/token-ratios"),
        apiClient.getSecure("metrics/error-rates"),
        apiClient.getSecure("metrics/metrics-monthly-summary?months=6"),
        apiClient.getSecure("metrics/infrastructure-costs?days=30")
      ]);

      // Check responses
      if (!costByUserRes.success) throw new Error(costByUserRes.error?.message || "Failed to fetch cost by user");
      if (!tokenRatiosRes.success) throw new Error(tokenRatiosRes.error?.message || "Failed to fetch token ratios");
      if (!errorRatesRes.success) throw new Error(errorRatesRes.error?.message || "Failed to fetch error rates");
      if (!monthlyLLMRes.success) throw new Error(monthlyLLMRes.error?.message || "Failed to fetch monthly LLM");
      if (!infraCostsRes.success) throw new Error(infraCostsRes.error?.message || "Failed to fetch infrastructure costs");

      const costByUser = costByUserRes.data;
      const tokenRatios = tokenRatiosRes.data;
      const errorRates = errorRatesRes.data;
      const monthlyLLM = monthlyLLMRes.data;
      const infraCosts = infraCostsRes.data;

      // Calculate summary
      const totalLLMCost = monthlyLLM.summary?.reduce((sum: number, m: MonthlySummary) => sum + m.total_cost_usd, 0) || 0;
      const latestInfra = infraCosts.costs?.[0];
      const totalRevenue = latestInfra?.mrr_usd * 6 || 0; // 6 months of MRR
      const totalInfraCost = infraCosts.costs?.reduce((sum: number, c: InfrastructureCost) => sum + c.total_cost_usd, 0) || 0;
      const netMargin = totalRevenue - totalLLMCost - totalInfraCost;

      setMetrics({
        costByUser: costByUser.users || [],
        tokenRatios: tokenRatios.ratios || [],
        errorRates: errorRates.providers || [],
        monthlyLLM: monthlyLLM.summary || [],
        infrastructureCosts: infraCosts.costs || [],
        totalLLMCost,
        totalInfraCost,
        totalRevenue,
        netMargin,
        lastSync: new Date().toISOString(),
      });

      setLoading(false);
    } catch (err: any) {
      console.error("[BusinessAnalytics] Error:", err);
      setError(err.message || "Erreur lors du chargement des métriques");
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("fr-CA", {
      style: "currency",
      currency: "USD",
    }).format(value);
  };

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat("fr-CA").format(value);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-600">Chargement des analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-red-800 font-semibold mb-2">Erreur</h3>
        <p className="text-red-600">{error}</p>
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
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Business Analytics</h1>
          <p className="text-gray-600 mt-1">
            Vue d'ensemble des coûts, revenus et rentabilité
          </p>
        </div>
        <button
          onClick={fetchMetrics}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Actualiser
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-green-500">
          <p className="text-sm text-gray-600 mb-1">Revenus (6 mois)</p>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(metrics.totalRevenue)}</p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-500">
          <p className="text-sm text-gray-600 mb-1">Coûts LLM</p>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(metrics.totalLLMCost)}</p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-purple-500">
          <p className="text-sm text-gray-600 mb-1">Coûts Infrastructure</p>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(metrics.totalInfraCost)}</p>
        </div>

        <div className={`bg-white rounded-lg shadow-md p-6 border-l-4 ${metrics.netMargin >= 0 ? 'border-green-600' : 'border-red-600'}`}>
          <p className="text-sm text-gray-600 mb-1">Marge Nette</p>
          <p className={`text-2xl font-bold ${metrics.netMargin >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(metrics.netMargin)}
          </p>
        </div>
      </div>

      {/* Revenue vs Costs Chart */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Revenus vs Coûts (30 derniers jours)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={metrics.infrastructureCosts}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
            <Legend />
            <Area
              type="monotone"
              dataKey="mrr_usd"
              fill="#10B981"
              stroke="#10B981"
              name="Revenus (MRR)"
              fillOpacity={0.3}
            />
            <Line
              type="monotone"
              dataKey="total_cost_usd"
              stroke="#EF4444"
              strokeWidth={2}
              name="Coûts Totaux"
            />
            <Line
              type="monotone"
              dataKey="margin_usd"
              stroke="#3B82F6"
              strokeWidth={2}
              name="Marge"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Cost by User */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Top 20 Utilisateurs par Coûts LLM</h2>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={metrics.costByUser.slice(0, 10)}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="email" angle={-45} textAnchor="end" height={100} />
            <YAxis />
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
            <Legend />
            <Bar dataKey="total_cost_usd" fill="#3B82F6" name="Coût USD" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Token Efficiency */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Efficacité des Tokens par Modèle</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={metrics.tokenRatios}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="model" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="avg_prompt_tokens" fill="#8B5CF6" name="Prompt Tokens (avg)" />
            <Bar dataKey="avg_completion_tokens" fill="#10B981" name="Completion Tokens (avg)" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Error Rates */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Taux d'Erreur par Provider</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {metrics.errorRates.map((provider, index) => (
            <div key={index} className="border rounded-lg p-4">
              <h3 className="font-semibold text-lg mb-2">{provider.provider}</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total:</span>
                  <span className="font-medium">{formatNumber(provider.total_requests)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-green-600">Succès:</span>
                  <span className="font-medium">{formatNumber(provider.successful_requests)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-red-600">Erreurs:</span>
                  <span className="font-medium">{formatNumber(provider.error_requests)}</span>
                </div>
                <div className="flex justify-between pt-2 border-t">
                  <span className="text-gray-600">Taux d'erreur:</span>
                  <span className={`font-bold ${provider.error_rate_percent > 5 ? 'text-red-600' : 'text-green-600'}`}>
                    {provider.error_rate_percent.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Infrastructure Costs Breakdown */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Répartition des Coûts Infrastructure</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={metrics.infrastructureCosts.slice(0, 7)}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
            <Legend />
            <Bar dataKey="llm_cost_usd" stackId="a" fill="#3B82F6" name="LLM" />
            <Bar dataKey="do_cost_usd" stackId="a" fill="#10B981" name="Digital Ocean" />
            <Bar dataKey="weaviate_cost_usd" stackId="a" fill="#F59E0B" name="Weaviate" />
            <Bar dataKey="supabase_cost_usd" stackId="a" fill="#8B5CF6" name="Supabase" />
            <Bar dataKey="twilio_cost_usd" stackId="a" fill="#EF4444" name="Twilio" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Monthly LLM Costs */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Évolution Mensuelle LLM (6 mois)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={metrics.monthlyLLM}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
            <Legend />
            <Line
              type="monotone"
              dataKey="total_cost_usd"
              stroke="#3B82F6"
              strokeWidth={2}
              name="Coût USD"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Last Sync */}
      {metrics.lastSync && (
        <div className="text-center text-sm text-gray-500">
          Dernière synchronisation: {new Date(metrics.lastSync).toLocaleString("fr-CA")}
        </div>
      )}
    </div>
  );
}
