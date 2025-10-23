/**
 * SatisfactionStatsTab Component
 * ===============================
 *
 * Displays satisfaction survey statistics in the admin panel
 *
 * Features:
 * - Overall satisfaction rate (pie chart or percentage)
 * - Daily/weekly/monthly trends (line chart)
 * - Recent surveys with comments
 * - Filter by date range, rating
 * - Export functionality
 */

"use client";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/lib/api/client";

interface SatisfactionSurvey {
  id: string;
  conversation_id: string;
  user_id: string;
  rating: "satisfied" | "neutral" | "unsatisfied";
  comment: string | null;
  message_count_at_survey: number;
  created_at: string;
}

interface SatisfactionStats {
  period: string;
  total_surveys: number;
  satisfied_count: number;
  neutral_count: number;
  unsatisfied_count: number;
  satisfaction_rate: number;
}

interface SatisfactionStatsResponse {
  status: string;
  days_analyzed: number;
  stats: SatisfactionStats[];
}

interface SatisfactionStatsTabProps {
  timeRange: "day" | "week" | "month" | "year";
}

export const SatisfactionStatsTab: React.FC<SatisfactionStatsTabProps> = ({
  timeRange,
}) => {
  const [stats, setStats] = useState<SatisfactionStats[]>([]);
  const [recentSurveys, setRecentSurveys] = useState<SatisfactionSurvey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterRating, setFilterRating] = useState<string>("all");

  // Convert time range to days
  const getDaysBack = () => {
    switch (timeRange) {
      case "day":
        return 1;
      case "week":
        return 7;
      case "month":
        return 30;
      case "year":
        return 365;
      default:
        return 30;
    }
  };

  // Fetch satisfaction statistics
  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);

      const daysBack = getDaysBack();
      const response = await apiClient.getSecure<SatisfactionStatsResponse>(
        `satisfaction/stats?days=${daysBack}`
      );

      if (response.data && response.data.stats) {
        setStats(response.data.stats);
      } else {
        setError("Erreur lors du chargement des statistiques");
      }
    } catch (err) {
      console.error("Error fetching satisfaction stats:", err);
      setError("Erreur réseau");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [timeRange]);

  // Calculate overall statistics
  const overallStats = stats.reduce(
    (acc, stat) => ({
      total: acc.total + stat.total_surveys,
      satisfied: acc.satisfied + stat.satisfied_count,
      neutral: acc.neutral + stat.neutral_count,
      unsatisfied: acc.unsatisfied + stat.unsatisfied_count,
    }),
    { total: 0, satisfied: 0, neutral: 0, unsatisfied: 0 }
  );

  const satisfactionRate =
    overallStats.total > 0
      ? Math.round((overallStats.satisfied / overallStats.total) * 100)
      : 0;

  const dissatisfactionRate =
    overallStats.total > 0
      ? Math.round((overallStats.unsatisfied / overallStats.total) * 100)
      : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-600">Chargement des statistiques...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-red-600">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with refresh button */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">
          📊 Statistiques de Satisfaction
        </h2>
        <button
          onClick={fetchStats}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          🔄 Actualiser
        </button>
      </div>

      {/* Overall Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Surveys */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <div className="text-sm text-gray-600 mb-1">Total Sondages</div>
          <div className="text-3xl font-bold text-gray-900">
            {overallStats.total}
          </div>
        </div>

        {/* Satisfaction Rate */}
        <div className="bg-green-50 p-6 rounded-lg shadow-sm border border-green-200">
          <div className="text-sm text-green-700 mb-1">Taux de Satisfaction</div>
          <div className="text-3xl font-bold text-green-800">
            {satisfactionRate}%
          </div>
          <div className="text-xs text-green-600 mt-1">
            {overallStats.satisfied} satisfait(s)
          </div>
        </div>

        {/* Neutral Rate */}
        <div className="bg-yellow-50 p-6 rounded-lg shadow-sm border border-yellow-200">
          <div className="text-sm text-yellow-700 mb-1">Neutres</div>
          <div className="text-3xl font-bold text-yellow-800">
            {overallStats.total > 0
              ? Math.round((overallStats.neutral / overallStats.total) * 100)
              : 0}
            %
          </div>
          <div className="text-xs text-yellow-600 mt-1">
            {overallStats.neutral} neutre(s)
          </div>
        </div>

        {/* Dissatisfaction Rate */}
        <div className="bg-red-50 p-6 rounded-lg shadow-sm border border-red-200">
          <div className="text-sm text-red-700 mb-1">Taux d'Insatisfaction</div>
          <div className="text-3xl font-bold text-red-800">
            {dissatisfactionRate}%
          </div>
          <div className="text-xs text-red-600 mt-1">
            {overallStats.unsatisfied} insatisfait(s)
          </div>
        </div>
      </div>

      {/* Detailed Statistics Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Évolution dans le temps
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">
                  Total
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">
                  😊 Satisfait
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">
                  😐 Neutre
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">
                  🙁 Insatisfait
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">
                  Taux
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {stats.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-6 py-8 text-center text-gray-500"
                  >
                    Aucune donnée disponible pour cette période
                  </td>
                </tr>
              ) : (
                stats.map((stat) => (
                  <tr key={stat.period} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(stat.period).toLocaleDateString("fr-FR", {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                      })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center font-medium text-gray-900">
                      {stat.total_surveys}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-green-600 font-medium">
                      {stat.satisfied_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-yellow-600 font-medium">
                      {stat.neutral_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-red-600 font-medium">
                      {stat.unsatisfied_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          stat.satisfaction_rate >= 80
                            ? "bg-green-100 text-green-800"
                            : stat.satisfaction_rate >= 60
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {stat.satisfaction_rate}%
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Information Footer */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-blue-600 mt-0.5"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">
              À propos des sondages de satisfaction
            </h3>
            <div className="mt-2 text-sm text-blue-700">
              <p>
                Les sondages apparaissent automatiquement après ~25 messages
                (première fois), puis tous les ~40 messages. Un taux de
                satisfaction supérieur à 80% est excellent, entre 60-80% est
                bon, en dessous de 60% nécessite une attention.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
