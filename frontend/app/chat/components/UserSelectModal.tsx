/**
 * UserSelectModal - Modal for selecting a user to configure Compass
 * Version: 1.0.0
 * Date: 2025-10-30
 */
"use client";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/lib/api/client";
import { secureLog } from "@/lib/utils/secureLogger";
import { SearchableSelect, SearchableSelectItem } from "./SearchableSelect";

interface AvailableUser {
  user_id: string;
  email: string;
  name?: string;
  has_compass_config: boolean;
  compass_enabled: boolean;
}

interface UserSelectModalProps {
  onSelect: (userId: string, email: string) => void;
  onClose: () => void;
}

export const UserSelectModal: React.FC<UserSelectModalProps> = ({
  onSelect,
  onClose
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [users, setUsers] = useState<AvailableUser[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  useEffect(() => {
    loadAvailableUsers();
  }, []);

  const loadAvailableUsers = async () => {
    try {
      setLoading(true);
      setError(null);

      secureLog.log("[UserSelectModal] Loading available users...");

      const response = await apiClient.getSecure<AvailableUser[]>(
        "compass/admin/available-users"
      );

      if (!response.success) {
        throw new Error(response.error?.message || "Failed to load users");
      }

      setUsers(response.data || []);
      secureLog.log(`[UserSelectModal] Loaded ${response.data?.length || 0} users`);
    } catch (err) {
      secureLog.error("[UserSelectModal] Error loading users:", err);
      setError(`Erreur lors du chargement: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectUser = () => {
    if (!selectedUserId) return;

    const selectedUser = users.find(u => u.user_id === selectedUserId);
    if (!selectedUser) return;

    secureLog.log("[UserSelectModal] User selected:", selectedUser.email);
    onSelect(selectedUser.user_id, selectedUser.email);
  };

  const handleClose = () => {
    secureLog.log("[UserSelectModal] Modal closed");
    onClose();
  };

  // Convert users to SearchableSelectItem format
  const userItems: SearchableSelectItem[] = users.map(user => ({
    id: user.user_id,
    label: user.email,
    subtitle: user.has_compass_config
      ? `✓ Déjà configuré${user.compass_enabled ? ' (actif)' : ' (inactif)'}`
      : '○ Pas encore configuré',
    data: user
  }));

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleClose}
      ></div>

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          className="relative bg-white rounded-lg shadow-xl max-w-lg w-full"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Sélectionner un utilisateur
              </h3>
              <button
                onClick={handleClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="px-6 py-4">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
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
                  onClick={loadAvailableUsers}
                  className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
                >
                  Réessayer
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  Recherchez et sélectionnez un utilisateur pour configurer l'accès Compass.
                  {users.filter(u => !u.has_compass_config).length > 0 && (
                    <span className="block mt-1 text-blue-600">
                      {users.filter(u => !u.has_compass_config).length} utilisateur(s) sans configuration
                    </span>
                  )}
                </p>

                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Utilisateur
                  </label>
                  <SearchableSelect
                    items={userItems}
                    onSelect={(item) => setSelectedUserId(item.id)}
                    selectedId={selectedUserId || undefined}
                    placeholder="Rechercher par email..."
                    emptyMessage="Aucun utilisateur trouvé"
                  />
                </div>

                {selectedUserId && (
                  <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-start space-x-2">
                      <svg className="w-5 h-5 text-blue-500 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"/>
                      </svg>
                      <div className="text-sm text-blue-800">
                        {users.find(u => u.user_id === selectedUserId)?.has_compass_config ? (
                          <p>
                            <strong>Cet utilisateur a déjà une configuration.</strong> Vous pourrez la modifier dans l'écran suivant.
                          </p>
                        ) : (
                          <p>
                            Vous allez créer une nouvelle configuration Compass pour cet utilisateur.
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Annuler
            </button>
            <button
              onClick={handleSelectUser}
              disabled={!selectedUserId || loading}
              className={`px-4 py-2 rounded-lg transition-colors ${
                selectedUserId && !loading
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              Continuer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
