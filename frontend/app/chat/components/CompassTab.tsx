/**
 * CompassTab - Compass integration admin interface
 * Version: 1.0.0
 * Date: 2025-10-30
 * Description: Admin UI for configuring user Compass barn mappings
 */
"use client";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/lib/api/client";
import { secureLog } from "@/lib/utils/secureLogger";
import { BarnConfigModal } from "./BarnConfigModal";
import { BarnDataPreview } from "./BarnDataPreview";

// Types
interface BarnConfig {
  compass_device_id: string;
  client_number: string;
  name: string;
  enabled: boolean;
}

interface UserCompassConfig {
  id?: string;
  user_id: string;
  user_email: string;
  compass_enabled: boolean;
  barns: BarnConfig[];
  created_at?: string;
  updated_at?: string;
}

interface CompassDevice {
  id: string;
  name: string;
  entity_id?: number;
}

interface ConnectionStatus {
  connected: boolean;
  base_url: string;
  has_token: boolean;
  timestamp?: string;
  error?: string;
}

export const CompassTab: React.FC = () => {
  // State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userConfigs, setUserConfigs] = useState<UserCompassConfig[]>([]);
  const [devices, setDevices] = useState<CompassDevice[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus | null>(null);

  // Modal state
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserCompassConfig | null>(null);

  // Preview state
  const [showPreview, setShowPreview] = useState(false);
  const [previewUserId, setPreviewUserId] = useState<string | null>(null);

  // Load all data on mount
  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    setError(null);

    try {
      await Promise.all([
        loadUserConfigs(),
        loadDevices(),
        testConnection()
      ]);
    } catch (err) {
      secureLog.error("[CompassTab] Error loading data:", err);
      setError(`Erreur lors du chargement: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const loadUserConfigs = async () => {
    try {
      secureLog.log("[CompassTab] Loading user configs...");

      const response = await apiClient.getSecure<UserCompassConfig[]>(
        "compass/admin/users"
      );

      if (!response.success) {
        throw new Error(response.error?.message || "Failed to load user configs");
      }

      setUserConfigs(response.data || []);
      secureLog.log(`[CompassTab] Loaded ${response.data?.length || 0} user configs`);
    } catch (err) {
      secureLog.error("[CompassTab] Error loading user configs:", err);
      throw err;
    }
  };

  const loadDevices = async () => {
    try {
      secureLog.log("[CompassTab] Loading Compass devices...");

      const response = await apiClient.getSecure<CompassDevice[]>(
        "compass/admin/compass/devices"
      );

      if (!response.success) {
        throw new Error(response.error?.message || "Failed to load devices");
      }

      setDevices(response.data || []);
      secureLog.log(`[CompassTab] Loaded ${response.data?.length || 0} devices`);
    } catch (err) {
      secureLog.error("[CompassTab] Error loading devices:", err);
      throw err;
    }
  };

  const testConnection = async () => {
    try {
      secureLog.log("[CompassTab] Testing Compass connection...");

      const response = await apiClient.getSecure<ConnectionStatus>(
        "compass/admin/compass/test-connection"
      );

      if (!response.success) {
        setConnectionStatus({
          connected: false,
          base_url: "",
          has_token: false,
          error: response.error?.message || "Connection failed"
        });
        return;
      }

      setConnectionStatus(response.data || null);
      secureLog.log("[CompassTab] Connection status:", response.data);
    } catch (err) {
      secureLog.error("[CompassTab] Error testing connection:", err);
      setConnectionStatus({
        connected: false,
        base_url: "",
        has_token: false,
        error: String(err)
      });
    }
  };

  const handleEditUser = (config: UserCompassConfig) => {
    secureLog.log("[CompassTab] Edit user:", config.user_email);
    setSelectedUser(config);
    setShowConfigModal(true);
  };

  const handleSaveConfig = async (config: UserCompassConfig) => {
    try {
      secureLog.log("[CompassTab] Saving config for user:", config.user_id);

      const response = await apiClient.postSecure(
        `compass/admin/users/${config.user_id}`,
        {
          compass_enabled: config.compass_enabled,
          barns: config.barns
        }
      );

      if (!response.success) {
        throw new Error(response.error?.message || "Failed to save config");
      }

      secureLog.log("[CompassTab] Config saved successfully");
      setShowConfigModal(false);
      setSelectedUser(null);

      // Reload configs
      await loadUserConfigs();
    } catch (err) {
      secureLog.error("[CompassTab] Error saving config:", err);
      alert(`Erreur lors de la sauvegarde: ${err}`);
    }
  };

  const handlePreview = (userId: string) => {
    secureLog.log("[CompassTab] Preview data for user:", userId);
    setPreviewUserId(userId);
    setShowPreview(true);
  };

  const handleToggleEnabled = async (config: UserCompassConfig) => {
    try {
      const newEnabled = !config.compass_enabled;
      secureLog.log(`[CompassTab] Toggle enabled for ${config.user_email}: ${newEnabled}`);

      const response = await apiClient.postSecure(
        `compass/admin/users/${config.user_id}`,
        {
          compass_enabled: newEnabled,
          barns: config.barns
        }
      );

      if (!response.success) {
        throw new Error(response.error?.message || "Failed to toggle");
      }

      // Reload configs
      await loadUserConfigs();
    } catch (err) {
      secureLog.error("[CompassTab] Error toggling enabled:", err);
      alert(`Erreur lors de la modification: ${err}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 my-4">
        <div className="flex items-center space-x-2">
          <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
          </svg>
          <span className="text-red-800">{error}</span>
        </div>
        <button
          onClick={loadAllData}
          className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
        >
          Réessayer
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Compass Integration
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Configure Compass barn mappings for users
            </p>
          </div>
          <button
            onClick={loadAllData}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Actualiser</span>
          </button>
        </div>
      </div>

      {/* Connection Status */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          État de la connexion Compass
        </h3>
        {connectionStatus ? (
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${connectionStatus.connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className={`font-medium ${connectionStatus.connected ? 'text-green-700' : 'text-red-700'}`}>
                {connectionStatus.connected ? 'Connecté' : 'Déconnecté'}
              </span>
            </div>
            <div className="text-sm text-gray-600">
              <strong>API URL:</strong> {connectionStatus.base_url}
            </div>
            <div className="text-sm text-gray-600">
              <strong>Token configuré:</strong> {connectionStatus.has_token ? 'Oui' : 'Non'}
            </div>
            {connectionStatus.error && (
              <div className="text-sm text-red-600">
                <strong>Erreur:</strong> {connectionStatus.error}
              </div>
            )}
            <div className="text-sm text-gray-600">
              <strong>Appareils disponibles:</strong> {devices.length}
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Test de connexion en cours...</p>
        )}
      </div>

      {/* User Configs Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Configurations utilisateurs ({userConfigs.length})
          </h3>
        </div>

        {userConfigs.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-gray-600">Aucune configuration Compass</p>
            <p className="text-sm text-gray-500 mt-1">Les configurations apparaîtront ici lorsqu'elles seront créées</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Utilisateur
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    État
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Poulaillers
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {userConfigs.map((config) => (
                  <tr key={config.user_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {config.user_email}
                      </div>
                      <div className="text-xs text-gray-500">
                        ID: {config.user_id.substring(0, 8)}...
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button
                        onClick={() => handleToggleEnabled(config)}
                        className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          config.compass_enabled
                            ? 'bg-green-100 text-green-800 hover:bg-green-200'
                            : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                        }`}
                      >
                        {config.compass_enabled ? 'Activé' : 'Désactivé'}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {config.barns.length} poulailler{config.barns.length > 1 ? 's' : ''}
                      </div>
                      <div className="text-xs text-gray-500">
                        {config.barns.filter(b => b.enabled).length} activé{config.barns.filter(b => b.enabled).length > 1 ? 's' : ''}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                      <button
                        onClick={() => handleEditUser(config)}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        Configurer
                      </button>
                      <button
                        onClick={() => handlePreview(config.user_id)}
                        className="text-green-600 hover:text-green-800 font-medium"
                      >
                        Prévisualiser
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      {showConfigModal && selectedUser && (
        <BarnConfigModal
          userConfig={selectedUser}
          devices={devices}
          onSave={handleSaveConfig}
          onClose={() => {
            setShowConfigModal(false);
            setSelectedUser(null);
          }}
        />
      )}

      {showPreview && previewUserId && (
        <BarnDataPreview
          userId={previewUserId}
          onClose={() => {
            setShowPreview(false);
            setPreviewUserId(null);
          }}
        />
      )}
    </div>
  );
};
