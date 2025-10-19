"use client";

import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { buildApiUrl } from "@/lib/api/config";

interface HistoryEntry {
  id: number;
  action_type: string;
  target_entity: string;
  admin_email: string;
  old_value: any;
  new_value: any;
  created_at: string;
  status: string;
  change_summary: string;
}

interface AdminHistoryLogProps {
  accessToken: string;
}

export default function AdminHistoryLog({
  accessToken,
}: AdminHistoryLogProps) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [limit, setLimit] = useState(50);
  const [filterType, setFilterType] = useState<string>("all");

  useEffect(() => {
    fetchHistory();
  }, [limit]);

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(
        buildApiUrl(`/billing/admin/history?limit=${limit}`),
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Erreur lors du chargement de l'historique");
      }

      const data = await response.json();
      setHistory(data.history || []);
    } catch (error) {
      console.error("[AdminHistoryLog] Erreur fetch history:", error);
      toast.error("Erreur lors du chargement de l'historique");
    } finally {
      setIsLoading(false);
    }
  };

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case "price_change":
        return "💰";
      case "quota_change":
        return "📊";
      case "name_change":
        return "✏️";
      case "tier_change":
        return "🎯";
      default:
        return "📝";
    }
  };

  const getActionColor = (actionType: string) => {
    switch (actionType) {
      case "price_change":
        return "bg-green-100 text-green-800";
      case "quota_change":
        return "bg-blue-100 text-blue-800";
      case "name_change":
        return "bg-purple-100 text-purple-800";
      case "tier_change":
        return "bg-orange-100 text-orange-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getActionLabel = (actionType: string) => {
    switch (actionType) {
      case "price_change":
        return "Prix";
      case "quota_change":
        return "Quota";
      case "name_change":
        return "Nom";
      case "tier_change":
        return "Tier";
      default:
        return actionType;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "À l'instant";
    if (diffMins < 60) return `Il y a ${diffMins} min`;
    if (diffHours < 24) return `Il y a ${diffHours}h`;
    if (diffDays < 7) return `Il y a ${diffDays}j`;

    return date.toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const filteredHistory =
    filterType === "all"
      ? history
      : history.filter((entry) => entry.action_type === filterType);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              Historique des Modifications Admin
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              {filteredHistory.length} modifications enregistrées
            </p>
          </div>
          <button
            onClick={fetchHistory}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            🔄 Actualiser
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Type:</label>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">Tous</option>
              <option value="price_change">Prix</option>
              <option value="quota_change">Quota</option>
              <option value="name_change">Nom</option>
              <option value="tier_change">Tier</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Limite:</label>
            <select
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            >
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Entité
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Modification
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Admin
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Statut
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredHistory.map((entry) => (
              <tr key={entry.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 inline-flex items-center text-xs leading-5 font-semibold rounded-full ${getActionColor(
                      entry.action_type
                    )}`}
                  >
                    <span className="mr-1">{getActionIcon(entry.action_type)}</span>
                    {getActionLabel(entry.action_type)}
                  </span>
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm font-medium text-gray-900">
                    {entry.target_entity}
                  </span>
                </td>

                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 max-w-md">
                    {entry.change_summary}
                  </div>
                  {entry.old_value && entry.new_value && (
                    <details className="mt-1">
                      <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                        Voir détails
                      </summary>
                      <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
                        <div className="mb-1">
                          <span className="font-semibold text-red-600">Avant:</span>{" "}
                          <code className="text-xs">
                            {JSON.stringify(entry.old_value)}
                          </code>
                        </div>
                        <div>
                          <span className="font-semibold text-green-600">Après:</span>{" "}
                          <code className="text-xs">
                            {JSON.stringify(entry.new_value)}
                          </code>
                        </div>
                      </div>
                    </details>
                  )}
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    {entry.admin_email.split("@")[0]}
                  </div>
                  <div className="text-xs text-gray-500">
                    @{entry.admin_email.split("@")[1]}
                  </div>
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    {formatDate(entry.created_at)}
                  </div>
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      entry.status === "completed"
                        ? "bg-green-100 text-green-800"
                        : entry.status === "failed"
                        ? "bg-red-100 text-red-800"
                        : "bg-yellow-100 text-yellow-800"
                    }`}
                  >
                    {entry.status === "completed"
                      ? "✓ Complété"
                      : entry.status === "failed"
                      ? "✕ Échoué"
                      : "⟳ En cours"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredHistory.length === 0 && (
        <div className="px-6 py-12 text-center text-gray-500">
          {filterType === "all"
            ? "Aucune modification enregistrée"
            : `Aucune modification de type "${getActionLabel(filterType)}" trouvée`}
        </div>
      )}
    </div>
  );
}
