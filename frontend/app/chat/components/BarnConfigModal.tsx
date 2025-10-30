/**
 * BarnConfigModal - Modal for configuring user barn mappings
 * Version: 1.0.0
 * Date: 2025-10-30
 * Description: Admin interface to configure Compass device → client number mappings
 */
"use client";

import React, { useState, useEffect } from "react";
import { secureLog } from "@/lib/utils/secureLogger";
import { SearchableSelect, SearchableSelectItem } from "./SearchableSelect";

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
}

interface CompassDevice {
  id: string;
  name: string;
  entity_id?: number;
}

interface BarnConfigModalProps {
  userConfig: UserCompassConfig;
  devices: CompassDevice[];
  onSave: (config: UserCompassConfig) => Promise<void>;
  onClose: () => void;
}

export const BarnConfigModal: React.FC<BarnConfigModalProps> = ({
  userConfig,
  devices,
  onSave,
  onClose
}) => {
  // State
  const [config, setConfig] = useState<UserCompassConfig>(userConfig);
  const [saving, setSaving] = useState(false);

  // Initialize config if empty
  useEffect(() => {
    if (config.barns.length === 0) {
      // Add one default barn
      setConfig({
        ...config,
        barns: [{
          compass_device_id: "",
          client_number: "1",
          name: "Poulailler 1",
          enabled: true
        }]
      });
    }
  }, []);

  const handleToggleEnabled = () => {
    setConfig({
      ...config,
      compass_enabled: !config.compass_enabled
    });
  };

  const handleAddBarn = () => {
    const newBarnNumber = (config.barns.length + 1).toString();
    setConfig({
      ...config,
      barns: [
        ...config.barns,
        {
          compass_device_id: "",
          client_number: newBarnNumber,
          name: `Poulailler ${newBarnNumber}`,
          enabled: true
        }
      ]
    });
  };

  const handleRemoveBarn = (index: number) => {
    setConfig({
      ...config,
      barns: config.barns.filter((_, i) => i !== index)
    });
  };

  const handleBarnChange = (index: number, field: keyof BarnConfig, value: any) => {
    const newBarns = [...config.barns];
    newBarns[index] = {
      ...newBarns[index],
      [field]: value
    };
    setConfig({
      ...config,
      barns: newBarns
    });
  };

  const handleSave = async () => {
    // Validation
    if (config.compass_enabled && config.barns.length === 0) {
      alert("Veuillez ajouter au moins un poulailler ou désactiver Compass");
      return;
    }

    // Check for duplicate client numbers
    const clientNumbers = config.barns.map(b => b.client_number);
    const duplicates = clientNumbers.filter((num, index) => clientNumbers.indexOf(num) !== index);
    if (duplicates.length > 0) {
      alert(`Numéros de poulailler en double: ${duplicates.join(", ")}`);
      return;
    }

    // Check for empty device IDs
    const emptyDevices = config.barns.filter(b => !b.compass_device_id);
    if (emptyDevices.length > 0 && config.compass_enabled) {
      alert("Tous les poulaillers doivent avoir un appareil Compass sélectionné");
      return;
    }

    try {
      setSaving(true);
      await onSave(config);
    } catch (err) {
      secureLog.error("[BarnConfigModal] Error saving:", err);
      alert(`Erreur lors de la sauvegarde: ${err}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              Configuration Compass
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {userConfig.user_email}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {/* Enable Toggle */}
          <div className="flex items-center justify-between bg-gray-50 p-4 rounded-lg">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">
                Activer Compass
              </h3>
              <p className="text-xs text-gray-600 mt-1">
                Permettre à cet utilisateur d'interroger ses poulaillers via Compass
              </p>
            </div>
            <button
              onClick={handleToggleEnabled}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                config.compass_enabled ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  config.compass_enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Barns Configuration */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-900">
                Poulaillers configurés
              </h3>
              <button
                onClick={handleAddBarn}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center space-x-1"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>Ajouter un poulailler</span>
              </button>
            </div>

            {config.barns.length === 0 ? (
              <div className="text-center py-8 bg-gray-50 rounded-lg">
                <p className="text-gray-600">Aucun poulailler configuré</p>
                <button
                  onClick={handleAddBarn}
                  className="mt-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  Ajouter le premier poulailler
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {config.barns.map((barn, index) => (
                  <div key={index} className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-medium text-gray-900">
                        Poulailler {index + 1}
                      </h4>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleBarnChange(index, 'enabled', !barn.enabled)}
                          className={`text-xs px-2 py-1 rounded-full ${
                            barn.enabled
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-200 text-gray-800'
                          }`}
                        >
                          {barn.enabled ? 'Activé' : 'Désactivé'}
                        </button>
                        <button
                          onClick={() => handleRemoveBarn(index)}
                          className="text-red-600 hover:text-red-800"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {/* Compass Device */}
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Appareil Compass
                        </label>
                        <SearchableSelect
                          items={devices.map(device => ({
                            id: device.id.toString(),
                            label: device.name,
                            subtitle: `ID: ${device.id}${device.entity_id ? ` • Entity: ${device.entity_id}` : ''}`,
                            data: device
                          }))}
                          onSelect={(item) => {
                            handleBarnChange(index, 'compass_device_id', item.id);
                            // Auto-fill name if empty
                            if (!barn.name || barn.name.startsWith('Poulailler')) {
                              handleBarnChange(index, 'name', item.label);
                            }
                          }}
                          selectedId={barn.compass_device_id}
                          placeholder="Rechercher un appareil..."
                          emptyMessage="Aucun appareil trouvé"
                        />
                      </div>

                      {/* Client Number */}
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Numéro client
                        </label>
                        <input
                          type="text"
                          value={barn.client_number}
                          onChange={(e) => handleBarnChange(index, 'client_number', e.target.value)}
                          placeholder="1, 2, 3..."
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Numéro que l'utilisateur utilisera ("poulailler 2")
                        </p>
                      </div>

                      {/* Barn Name */}
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Nom du poulailler
                        </label>
                        <input
                          type="text"
                          value={barn.name}
                          onChange={(e) => handleBarnChange(index, 'name', e.target.value)}
                          placeholder="Poulailler Est"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Nom affiché dans les réponses
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Help Text */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-blue-900 mb-2">
              Comment ça fonctionne ?
            </h4>
            <ul className="text-xs text-blue-800 space-y-1">
              <li>• <strong>Appareil Compass</strong>: L'ID de l'appareil dans Compass (849, 850, etc.)</li>
              <li>• <strong>Numéro client</strong>: Le numéro que l'utilisateur utilisera dans ses questions ("poulailler 2")</li>
              <li>• <strong>Nom</strong>: Le nom affiché dans les réponses du GPT ("Poulailler Est")</li>
              <li>• Les utilisateurs pourront demander: "Quelle est la température dans mon poulailler 2?"</li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-end space-x-3">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Annuler
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
          >
            {saving && (
              <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            <span>{saving ? 'Sauvegarde...' : 'Sauvegarder'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
