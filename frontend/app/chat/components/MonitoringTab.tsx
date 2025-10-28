/**
 * MonitoringTab - Affichage des logs de monitoring des services
 * Version: 1.0.0
 * Last modified: 2025-10-28
 */

import React, { useState, useEffect } from "react";
import { apiClient } from "@/lib/api/client";
import { secureLog } from "@/lib/utils/secureLogger";

interface LogEntry {
  timestamp: string;
  service: string;
  level: string;
  message: string;
  context?: Record<string, any>;
}

interface ServiceHealth {
  service: string;
  status: string;
  last_check: string;
  response_time_ms: number | null;
  error_message?: string;
}

interface MonitoringSummary {
  total_logs: number;
  errors: number;
  warnings: number;
  total_services: number;
  healthy_services: number;
  last_update: string;
}

export const MonitoringTab: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [services, setServices] = useState<ServiceHealth[]>([]);
  const [summary, setSummary] = useState<MonitoringSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filtres
  const [filterService, setFilterService] = useState<string>("");
  const [filterLevel, setFilterLevel] = useState<string>("");
  const [limit, setLimit] = useState<number>(100);

  // Auto-refresh
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30); // secondes

  // Fonction pour récupérer les logs
  const fetchLogs = async () => {
    try {
      const params = new URLSearchParams();
      if (limit) params.append("limit", limit.toString());
      if (filterService) params.append("service", filterService);
      if (filterLevel) params.append("level", filterLevel);

      const response = await apiClient.get(`/monitoring/logs?${params.toString()}`);

      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
        setError(null);
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (err) {
      secureLog.error("[MonitoringTab] Error fetching logs:", err);
      setError("Failed to fetch logs");
    }
  };

  // Fonction pour récupérer l'état des services
  const fetchServices = async () => {
    try {
      const response = await apiClient.get("/monitoring/services");

      if (response.ok) {
        const data = await response.json();
        setServices(data.services || []);
      }
    } catch (err) {
      secureLog.error("[MonitoringTab] Error fetching services:", err);
    }
  };

  // Fonction pour récupérer le résumé
  const fetchSummary = async () => {
    try {
      const response = await apiClient.get("/monitoring/summary");

      if (response.ok) {
        const data = await response.json();
        setSummary(data);
      }
    } catch (err) {
      secureLog.error("[MonitoringTab] Error fetching summary:", err);
    }
  };

  // Fonction pour tout récupérer
  const fetchAll = async () => {
    setLoading(true);
    await Promise.all([fetchLogs(), fetchServices(), fetchSummary()]);
    setLoading(false);
  };

  // Effet initial
  useEffect(() => {
    fetchAll();
  }, [filterService, filterLevel, limit]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchAll();
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, filterService, filterLevel, limit]);

  // Fonction pour obtenir la couleur selon le niveau
  const getLevelColor = (level: string) => {
    switch (level) {
      case "ERROR":
        return "text-red-600 bg-red-50";
      case "WARNING":
        return "text-yellow-600 bg-yellow-50";
      case "INFO":
        return "text-blue-600 bg-blue-50";
      default:
        return "text-gray-600 bg-gray-50";
    }
  };

  // Fonction pour obtenir la couleur du status
  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "text-green-600 bg-green-50";
      case "degraded":
        return "text-yellow-600 bg-yellow-50";
      case "unhealthy":
        return "text-red-600 bg-red-50";
      default:
        return "text-gray-600 bg-gray-50";
    }
  };

  // Formater la date
  const formatDate = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        day: "2-digit",
        month: "2-digit",
      });
    } catch {
      return timestamp;
    }
  };

  if (loading && logs.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Chargement des logs...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header avec résumé */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-500">Total Logs</div>
            <div className="text-2xl font-bold text-gray-900">{summary.total_logs}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-500">Errors</div>
            <div className="text-2xl font-bold text-red-600">{summary.errors}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-500">Warnings</div>
            <div className="text-2xl font-bold text-yellow-600">{summary.warnings}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-500">Services</div>
            <div className="text-2xl font-bold text-blue-600">
              {summary.healthy_services}/{summary.total_services}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-500">Last Update</div>
            <div className="text-sm font-medium text-gray-900">{formatDate(summary.last_update)}</div>
          </div>
        </div>
      )}

      {/* État des services */}
      {services.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Services Status</h3>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {services.map((service) => (
                <div key={service.service} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-gray-900">{service.service}</span>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                        service.status
                      )}`}
                    >
                      {service.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <div>
                      Response Time:{" "}
                      <span className="font-medium">
                        {service.response_time_ms ? `${service.response_time_ms.toFixed(0)}ms` : "N/A"}
                      </span>
                    </div>
                    <div>
                      Last Check: <span className="font-medium">{formatDate(service.last_check)}</span>
                    </div>
                    {service.error_message && (
                      <div className="text-red-600">Error: {service.error_message}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Contrôles */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex flex-wrap gap-4 items-end">
          {/* Filtre par service */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-2">Service</label>
            <select
              value={filterService}
              onChange={(e) => setFilterService(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Services</option>
              <option value="ai-service">AI Service</option>
              <option value="llm-service">LLM Service</option>
            </select>
          </div>

          {/* Filtre par niveau */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-2">Level</label>
            <select
              value={filterLevel}
              onChange={(e) => setFilterLevel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Levels</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>

          {/* Limite */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium text-gray-700 mb-2">Limit</label>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value={50}>50 logs</option>
              <option value={100}>100 logs</option>
              <option value={200}>200 logs</option>
              <option value={500}>500 logs</option>
            </select>
          </div>

          {/* Auto-refresh */}
          <div className="flex items-center space-x-3">
            <label className="flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">Auto-refresh ({refreshInterval}s)</span>
            </label>
          </div>

          {/* Bouton refresh manuel */}
          <button
            onClick={fetchAll}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </div>

      {/* Erreur */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <svg
              className="h-5 w-5 text-red-600 mr-2"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-red-800">{error}</span>
          </div>
        </div>
      )}

      {/* Liste des logs */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Logs {logs.length > 0 && `(${logs.length})`}
          </h3>
        </div>
        <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
          {logs.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-500">No logs available</div>
          ) : (
            logs.map((log, index) => (
              <div key={index} className="px-6 py-3 hover:bg-gray-50 transition-colors">
                <div className="flex items-start space-x-3">
                  {/* Timestamp */}
                  <div className="text-xs text-gray-500 w-24 flex-shrink-0 pt-1">
                    {formatDate(log.timestamp)}
                  </div>

                  {/* Service */}
                  <div className="text-xs font-medium text-gray-700 w-28 flex-shrink-0 pt-1">
                    {log.service}
                  </div>

                  {/* Level */}
                  <div className="flex-shrink-0">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${getLevelColor(log.level)}`}
                    >
                      {log.level}
                    </span>
                  </div>

                  {/* Message */}
                  <div className="flex-1 text-sm text-gray-900">
                    {log.message}
                    {log.context && Object.keys(log.context).length > 0 && (
                      <details className="mt-1">
                        <summary className="text-xs text-blue-600 cursor-pointer hover:text-blue-800">
                          Show context
                        </summary>
                        <pre className="mt-2 text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                          {JSON.stringify(log.context, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default MonitoringTab;
