/**
 * BarnDataPreview - Preview real-time barn data from Compass
 * Version: 1.0.0
 * Date: 2025-10-30
 * Description: Shows real-time sensor data for all configured barns
 */
"use client";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/lib/api/client";
import { secureLog } from "@/lib/utils/secureLogger";

// Types
interface BarnData {
  device_id: string;
  client_number: string;
  name: string;
  temperature?: number;
  humidity?: number;
  average_weight?: number;
  age_days?: number;
  timestamp?: string;
}

interface BarnDataPreviewProps {
  userId: string;
  onClose: () => void;
}

export const BarnDataPreview: React.FC<BarnDataPreviewProps> = ({ userId, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [barnsData, setBarnsData] = useState<BarnData[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadBarnData();
  }, [userId]);

  const loadBarnData = async () => {
    try {
      setLoading(true);
      setError(null);
      secureLog.log("[BarnDataPreview] Loading barn data for user:", userId);

      // Note: We need to use admin endpoint with user_id parameter
      // For now, we'll show a message that this requires direct backend access
      const response = await apiClient.getSecure<BarnData[]>(
        `compass/admin/users/${userId}/barns-data`
      );

      if (!response.success) {
        throw new Error(response.error?.message || "Failed to load barn data");
      }

      setBarnsData(response.data || []);
      secureLog.log(`[BarnDataPreview] Loaded ${response.data?.length || 0} barns`);
    } catch (err) {
      secureLog.error("[BarnDataPreview] Error loading barn data:", err);
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadBarnData();
    setRefreshing(false);
  };

  const formatValue = (value: number | undefined, unit: string): string => {
    if (value === undefined || value === null) {
      return "N/A";
    }
    return `${value.toFixed(1)} ${unit}`;
  };

  const formatDate = (timestamp: string | undefined): string => {
    if (!timestamp) return "N/A";
    try {
      return new Date(timestamp).toLocaleString('fr-FR');
    } catch {
      return timestamp;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              Données Temps Réel Compass
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Prévisualisation des données des poulaillers
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleRefresh}
              disabled={refreshing || loading}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
              title="Actualiser"
            >
              <svg className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Chargement des données...</p>
              </div>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center space-x-2">
                <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
                </svg>
                <span className="text-red-800">{error}</span>
              </div>
              <button
                onClick={handleRefresh}
                className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
              >
                Réessayer
              </button>
            </div>
          ) : barnsData.length === 0 ? (
            <div className="text-center py-12">
              <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-gray-600">Aucun poulailler configuré</p>
              <p className="text-sm text-gray-500 mt-1">
                Configurez les poulaillers pour voir leurs données
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {barnsData.map((barn) => (
                <div key={barn.device_id} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                  {/* Barn Header */}
                  <div className="bg-gradient-to-r from-blue-500 to-blue-600 px-4 py-3">
                    <h3 className="text-white font-semibold">
                      {barn.name}
                    </h3>
                    <p className="text-blue-100 text-xs mt-1">
                      Poulailler {barn.client_number} • Device #{barn.device_id}
                    </p>
                  </div>

                  {/* Barn Data */}
                  <div className="p-4 space-y-3">
                    {/* Temperature */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <svg className="w-5 h-5 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                        <span className="text-sm text-gray-700">Température</span>
                      </div>
                      <span className="text-sm font-semibold text-gray-900">
                        {formatValue(barn.temperature, "°C")}
                      </span>
                    </div>

                    {/* Humidity */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                        </svg>
                        <span className="text-sm text-gray-700">Humidité</span>
                      </div>
                      <span className="text-sm font-semibold text-gray-900">
                        {formatValue(barn.humidity, "%")}
                      </span>
                    </div>

                    {/* Weight */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
                        </svg>
                        <span className="text-sm text-gray-700">Poids moyen</span>
                      </div>
                      <span className="text-sm font-semibold text-gray-900">
                        {barn.average_weight ? formatValue(barn.average_weight, "g") : "N/A"}
                      </span>
                    </div>

                    {/* Age */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <svg className="w-5 h-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="text-sm text-gray-700">Âge du troupeau</span>
                      </div>
                      <span className="text-sm font-semibold text-gray-900">
                        {barn.age_days ? `${barn.age_days} jours` : "N/A"}
                      </span>
                    </div>

                    {/* Timestamp */}
                    <div className="pt-2 border-t border-gray-200">
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span>Dernière mise à jour</span>
                        <span>{formatDate(barn.timestamp)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-600">
              {barnsData.length > 0 && (
                <>
                  {barnsData.length} poulailler{barnsData.length > 1 ? 's' : ''} •
                  Données en temps réel depuis Compass
                </>
              )}
            </p>
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Fermer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
