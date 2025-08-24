import React from 'react'

// Interface pour les statistiques d'invitations - COMPLÈTE
interface InvitationStats {
  total_invitations_sent: number
  total_invitations_accepted: number
  acceptance_rate: number
  unique_inviters: number
  top_inviters: Array<{
    inviter_email: string
    inviter_name: string
    invitations_sent: number
    invitations_accepted: number
    acceptance_rate: number
  }>
  top_accepted: Array<{
    inviter_email: string
    inviter_name: string
    invitations_accepted: number
    invitations_sent: number
    acceptance_rate: number
  }>
}

// Props avec support du cache complet
interface InvitationStatsProps {
  invitationStats: InvitationStats | null
  cacheStatus?: {
    is_available: boolean
    last_update: string | null
    cache_age_minutes: number
    performance_gain: string
    next_update: string | null
  } | null
  isLoading?: boolean
}

export const InvitationStatsComponent: React.FC<InvitationStatsProps> = ({
  invitationStats,
  cacheStatus = null,
  isLoading = false
}) => {
  
  // Affichage pendant le chargement
  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 p-8 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Chargement des statistiques d'invitations...</p>
      </div>
    )
  }

  if (!invitationStats) {
    return (
      <div className="bg-white border border-gray-200 p-4">
        <div className="text-center text-gray-500">
          <div className="text-gray-400 text-2xl mb-2">📨</div>
          <p>Statistiques d'invitations non disponibles</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header avec informations de cache (version discrète) */}
      {cacheStatus && cacheStatus.is_available && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-600 rounded-full"></div>
                <h3 className="text-sm font-medium text-green-900">Données optimisées</h3>
              </div>
              <div className="flex items-center space-x-4 text-xs text-green-700">
                <span>Mis à jour: {cacheStatus.last_update ? new Date(cacheStatus.last_update).toLocaleString('fr-FR', { 
                  month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                }) : 'N/A'}</span>
                <span>Âge: {cacheStatus.cache_age_minutes}min</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Section d'information si cache indisponible */}
      {cacheStatus && !cacheStatus.is_available && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <div className="flex items-center space-x-2 text-amber-800">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span className="text-sm font-medium">Cache indisponible - Données en temps réel</span>
          </div>
        </div>
      )}

      {/* KPIs Invitations - Version complète */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Invitations Envoyées</p>
            <p className="text-2xl font-semibold text-gray-900">{invitationStats.total_invitations_sent}</p>
            {cacheStatus && (
              <p className="text-xs text-gray-400 mt-1">
                {cacheStatus.is_available ? 'Cache' : 'Direct'}
              </p>
            )}
          </div>
        </div>

        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Invitations Acceptées</p>
            <p className="text-2xl font-semibold text-green-600">{invitationStats.total_invitations_accepted}</p>
            {cacheStatus && cacheStatus.is_available && (
              <p className="text-xs text-green-500 mt-1">Données mises en cache</p>
            )}
          </div>
        </div>

        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Utilisateurs Inviteurs</p>
            <p className="text-2xl font-semibold text-gray-900">{invitationStats.unique_inviters}</p>
            {!cacheStatus?.is_available && (
              <p className="text-xs text-amber-500 mt-1">Mode direct</p>
            )}
          </div>
        </div>

        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Taux d'Acceptation</p>
            <p className="text-2xl font-semibold text-blue-600">{invitationStats.acceptance_rate.toFixed(1)}%</p>
            {cacheStatus?.is_available && (
              <p className="text-xs text-blue-500 mt-1">Optimisé</p>
            )}
          </div>
        </div>
      </div>

      {/* Graphique de progression du taux d'acceptation */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-base font-medium text-gray-900">Analyse du Taux d'Acceptation</h3>
        </div>
        <div className="p-4">
          <div className="mb-4">
            <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
              <span>Taux global d'acceptation</span>
              <span className="font-medium text-gray-900">{invitationStats.acceptance_rate.toFixed(1)}%</span>
            </div>
            
            {/* Barre de progression avec couleurs conditionnelles */}
            <div className="w-full bg-gray-200 h-4 rounded-full overflow-hidden">
              <div 
                className={`h-4 rounded-full transition-all duration-500 ${
                  invitationStats.acceptance_rate >= 75 ? 'bg-green-500' :
                  invitationStats.acceptance_rate >= 50 ? 'bg-blue-500' :
                  invitationStats.acceptance_rate >= 25 ? 'bg-yellow-500' :
                  'bg-red-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(5, invitationStats.acceptance_rate))}%` }}
              ></div>
            </div>
            
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0%</span>
              <span>25%</span>
              <span>50%</span>
              <span>75%</span>
              <span>100%</span>
            </div>
          </div>

          {/* Métriques détaillées */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            <div className="bg-blue-50 p-3 border border-blue-200 rounded">
              <div className="text-center">
                <p className="text-lg font-semibold text-blue-600">{invitationStats.total_invitations_sent}</p>
                <p className="text-xs text-blue-700">Total Envoyées</p>
              </div>
            </div>
            
            <div className="bg-green-50 p-3 border border-green-200 rounded">
              <div className="text-center">
                <p className="text-lg font-semibold text-green-600">{invitationStats.total_invitations_accepted}</p>
                <p className="text-xs text-green-700">Total Acceptées</p>
              </div>
            </div>
            
            <div className="bg-gray-50 p-3 border border-gray-200 rounded">
              <div className="text-center">
                <p className="text-lg font-semibold text-gray-600">{invitationStats.total_invitations_sent - invitationStats.total_invitations_accepted}</p>
                <p className="text-xs text-gray-700">En Attente</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tables des Top Inviters - Version complète avec toutes les données */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Top 5 Inviteurs par Nombre d'Invitations */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-medium text-gray-900">Top 5 - Invitations Envoyées</h3>
              {cacheStatus && (
                <span className={`text-xs px-2 py-1 rounded ${
                  cacheStatus.is_available 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {cacheStatus.is_available ? 'Cache' : 'Direct'}
                </span>
              )}
            </div>
          </div>
          <div className="overflow-hidden">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Rang</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Inviteur</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Envoyées</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Acceptées</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Taux</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {invitationStats.top_inviters.slice(0, 5).map((inviter, index) => (
                  <tr key={inviter.inviter_email || `inviter-${index}`} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm font-bold text-gray-900">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                        index === 0 ? 'bg-yellow-500' :
                        index === 1 ? 'bg-gray-400' :
                        index === 2 ? 'bg-orange-600' :
                        'bg-blue-500'
                      }`}>
                        {index + 1}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-900 max-w-48">
                      <div className="truncate" title={inviter.inviter_email}>
                        <div className="font-medium">{inviter.inviter_name || 'Nom non disponible'}</div>
                        <div className="text-xs text-gray-500">{inviter.inviter_email}</div>
                      </div>
                    </td>
                    <td className="px-4 py-2 text-sm font-medium text-blue-900">{inviter.invitations_sent}</td>
                    <td className="px-4 py-2 text-sm text-green-600 font-medium">{inviter.invitations_accepted}</td>
                    <td className="px-4 py-2">
                      <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                        inviter.acceptance_rate >= 70 ? 'bg-green-100 text-green-800' :
                        inviter.acceptance_rate >= 40 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {inviter.acceptance_rate.toFixed(0)}%
                      </span>
                    </td>
                  </tr>
                ))}
                {invitationStats.top_inviters.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                      <div className="text-gray-400 text-2xl mb-2">📨</div>
                      <p>Aucun inviteur trouvé</p>
                      {cacheStatus && (
                        <p className="text-xs text-gray-400 mt-1">
                          Mode {cacheStatus.is_available ? 'cache' : 'direct'} - Aucune donnée
                        </p>
                      )}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top 5 Inviteurs par Acceptations */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-medium text-gray-900">Top 5 - Invitations Acceptées</h3>
              {cacheStatus && cacheStatus.is_available && (
                <span className="text-xs text-green-600">{cacheStatus.cache_age_minutes}min</span>
              )}
            </div>
          </div>
          <div className="overflow-hidden">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Rang</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Inviteur</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Acceptées</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Efficacité</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {invitationStats.top_accepted.slice(0, 5).map((inviter, index) => (
                  <tr key={inviter.inviter_email || `accepted-${index}`} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm font-bold text-gray-900">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                        index === 0 ? 'bg-green-500' :
                        index === 1 ? 'bg-blue-500' :
                        index === 2 ? 'bg-purple-500' :
                        'bg-indigo-500'
                      }`}>
                        {index + 1}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-900 max-w-48">
                      <div className="truncate" title={inviter.inviter_email}>
                        <div className="font-medium">{inviter.inviter_name || 'Nom non disponible'}</div>
                        <div className="text-xs text-gray-500">{inviter.inviter_email}</div>
                      </div>
                    </td>
                    <td className="px-4 py-2 text-sm font-bold text-green-600 text-lg">{inviter.invitations_accepted}</td>
                    <td className="px-4 py-2 text-sm text-gray-600">{inviter.invitations_sent}</td>
                    <td className="px-4 py-2">
                      <div className="flex items-center space-x-2">
                        <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                          inviter.acceptance_rate >= 70 ? 'bg-green-100 text-green-800' :
                          inviter.acceptance_rate >= 40 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {inviter.acceptance_rate.toFixed(0)}%
                        </span>
                        {inviter.acceptance_rate >= 80 && (
                          <span className="text-green-600 text-sm">🏆</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {invitationStats.top_accepted.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                      <div className="text-gray-400 text-2xl mb-2">✅</div>
                      <p>Aucune invitation acceptée</p>
                      {cacheStatus && (
                        <p className="text-xs text-gray-400 mt-1">
                          Données {cacheStatus.is_available ? 'en cache' : 'directes'} - Aucun résultat
                        </p>
                      )}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Section de Performance Invitations détaillée */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-medium text-gray-900">Performance des Invitations</h3>
            {cacheStatus && cacheStatus.last_update && (
              <div className="text-xs text-gray-500">
                Dernière MàJ: {new Date(cacheStatus.last_update).toLocaleString('fr-FR')}
              </div>
            )}
          </div>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="text-center p-4 bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 rounded-lg relative">
              <p className="text-2xl font-bold text-blue-900">{invitationStats.total_invitations_sent}</p>
              <p className="text-sm text-blue-700">Total Envoyées</p>
              {cacheStatus?.is_available && (
                <div className="absolute top-2 right-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              )}
            </div>
            <div className="text-center p-4 bg-gradient-to-br from-green-50 to-green-100 border border-green-200 rounded-lg relative">
              <p className="text-2xl font-bold text-green-900">{invitationStats.total_invitations_accepted}</p>
              <p className="text-sm text-green-700">Total Acceptées</p>
              {cacheStatus?.is_available && (
                <div className="absolute top-2 right-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              )}
            </div>
            <div className="text-center p-4 bg-gradient-to-br from-gray-50 to-gray-100 border border-gray-200 rounded-lg relative">
              <p className="text-2xl font-bold text-gray-900">{invitationStats.total_invitations_sent - invitationStats.total_invitations_accepted}</p>
              <p className="text-sm text-gray-700">En Attente</p>
              {cacheStatus?.is_available && (
                <div className="absolute top-2 right-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              )}
            </div>
            <div className="text-center p-4 bg-gradient-to-br from-purple-50 to-purple-100 border border-purple-200 rounded-lg relative">
              <p className="text-2xl font-bold text-purple-900">{invitationStats.acceptance_rate.toFixed(1)}%</p>
              <p className="text-sm text-purple-700">Taux Global</p>
              {cacheStatus?.is_available && (
                <div className="absolute top-2 right-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              )}
            </div>
          </div>

          {/* Métriques avancées */}
          <div className="border-t border-gray-200 pt-4">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Analyse Avancée</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              
              <div className="bg-white border border-gray-200 p-3 rounded">
                <div className="text-center">
                  <p className="text-lg font-semibold text-indigo-600">{invitationStats.unique_inviters}</p>
                  <p className="text-xs text-indigo-700">Inviteurs Actifs</p>
                </div>
              </div>

              <div className="bg-white border border-gray-200 p-3 rounded">
                <div className="text-center">
                  <p className="text-lg font-semibold text-teal-600">
                    {invitationStats.unique_inviters > 0 ? 
                      (invitationStats.total_invitations_sent / invitationStats.unique_inviters).toFixed(1) : 
                      '0.0'
                    }
                  </p>
                  <p className="text-xs text-teal-700">Moy. par Inviteur</p>
                </div>
              </div>

              <div className="bg-white border border-gray-200 p-3 rounded">
                <div className="text-center">
                  <p className="text-lg font-semibold text-orange-600">
                    {invitationStats.total_invitations_accepted > 0 ? 
                      (invitationStats.total_invitations_accepted / invitationStats.unique_inviters).toFixed(1) : 
                      '0.0'
                    }
                  </p>
                  <p className="text-xs text-orange-700">Succès par Inviteur</p>
                </div>
              </div>

              <div className="bg-white border border-gray-200 p-3 rounded">
                <div className="text-center">
                  <p className={`text-lg font-semibold ${
                    invitationStats.acceptance_rate >= 75 ? 'text-green-600' :
                    invitationStats.acceptance_rate >= 50 ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {invitationStats.acceptance_rate >= 75 ? 'Excellent' :
                     invitationStats.acceptance_rate >= 50 ? 'Bon' :
                     'À améliorer'}
                  </p>
                  <p className="text-xs text-gray-700">Performance</p>
                </div>
              </div>

            </div>
          </div>

          {/* Section d'informations sur le cache détaillée */}
          {cacheStatus && (
            <div className="mt-6 pt-4 border-t border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className={`inline-flex items-center space-x-1 ${
                    cacheStatus.is_available ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {cacheStatus.is_available ? (
                      <>
                        <div className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></div>
                        <span className="font-medium">Cache Actif</span>
                      </>
                    ) : (
                      <>
                        <div className="w-2 h-2 bg-red-600 rounded-full"></div>
                        <span className="font-medium">Cache Indisponible</span>
                      </>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Source des données</p>
                </div>

                <div className="text-center">
                  <div className="font-medium text-blue-600">
                    {cacheStatus.is_available ? cacheStatus.performance_gain : 'Performance standard'}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Temps de chargement</p>
                </div>

                <div className="text-center">
                  <div className="font-medium text-gray-700">
                    {cacheStatus.next_update ? new Date(cacheStatus.next_update).toLocaleString('fr-FR', {
                      hour: '2-digit', 
                      minute: '2-digit'
                    }) : 'Automatique'}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Prochaine mise à jour</p>
                </div>
              </div>

              {/* Barre de progression de la fraîcheur du cache */}
              {cacheStatus.is_available && (
                <div className="mt-4">
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>Fraîcheur des données</span>
                    <span>{Math.max(0, 60 - cacheStatus.cache_age_minutes)}min restantes</span>
                  </div>
                  <div className="w-full bg-gray-200 h-2 rounded">
                    <div 
                      className={`h-2 rounded transition-all duration-300 ${
                        cacheStatus.cache_age_minutes < 30 ? 'bg-green-500' :
                        cacheStatus.cache_age_minutes < 45 ? 'bg-yellow-500' :
                        'bg-red-500'
                      }`}
                      style={{ 
                        width: `${Math.max(10, Math.min(100, 100 - (cacheStatus.cache_age_minutes / 60 * 100)))}%` 
                      }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Section d'export complète avec informations cache */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-medium text-gray-900">Export des Statistiques d'Invitations</h3>
            {cacheStatus?.is_available && (
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                Données optimisées
              </span>
            )}
          </div>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Export CSV */}
            <div className="bg-white border border-gray-200 p-4 flex flex-col justify-between h-full">
              <div>
                <h4 className="text-base font-medium text-gray-900 mb-1">Export CSV Complet</h4>
                <p className="text-sm text-gray-600 mb-3">Toutes les statistiques au format CSV</p>
                <div className="text-xs text-gray-500 mb-4">
                  <p>• Top inviteurs et statistiques détaillées</p>
                  <p>• Données {cacheStatus?.is_available ? 'optimisées par cache' : 'en temps réel'}</p>
                  {cacheStatus?.is_available && (
                    <p>• Exporté avec performance optimisée</p>
                  )}
                </div>
              </div>
              <button
                onClick={() => {
                  const csvData = [
                    ['Métrique', 'Valeur', 'Source', 'Timestamp'],
                    ['Total Invitations Envoyées', invitationStats.total_invitations_sent, cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['Total Invitations Acceptées', invitationStats.total_invitations_accepted, cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['Taux d\'Acceptation Global', `${invitationStats.acceptance_rate.toFixed(1)}%`, cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['Nombre d\'Inviteurs Uniques', invitationStats.unique_inviters, cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['Moyenne Invitations par Inviteur', invitationStats.unique_inviters > 0 ? (invitationStats.total_invitations_sent / invitationStats.unique_inviters).toFixed(1) : '0', cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['', '', '', ''],
                    ['Top Inviteurs (Envoyées)', '', '', ''],
                    ['Rang', 'Nom', 'Email', 'Envoyées', 'Acceptées', 'Taux'],
                    ...invitationStats.top_inviters.map((inviter, index) => [
                      index + 1,
                      inviter.inviter_name || 'N/A',
                      inviter.inviter_email,
                      inviter.invitations_sent,
                      inviter.invitations_accepted,
                      `${inviter.acceptance_rate.toFixed(1)}%`
                    ]),
                    ['', '', '', ''],
                    ['Top Inviteurs (Acceptées)', '', '', ''],
                    ['Rang', 'Nom', 'Email', 'Acceptées', 'Total', 'Efficacité'],
                    ...invitationStats.top_accepted.map((inviter, index) => [
                      index + 1,
                      inviter.inviter_name || 'N/A',
                      inviter.inviter_email,
                      inviter.invitations_accepted,
                      inviter.invitations_sent,
                      `${inviter.acceptance_rate.toFixed(1)}%`
                    ])
                  ]
                  
                  const csvContent = csvData
                    .map(row => row.map(field => `"${field}"`).join(','))
                    .join('\n')
                  
                  const bom = '\uFEFF'
                  const blob = new Blob([bom + csvContent], { type: 'text/csv;charset=utf-8' })
                  const url = window.URL.createObjectURL(blob)
                  
                  const link = document.createElement('a')
                  link.href = url
                  link.download = `invitations_stats_${cacheStatus?.is_available ? 'cache' : 'direct'}_${new Date().toISOString().split('T')[0]}.csv`
                  document.body.appendChild(link)
                  link.click()
                  document.body.removeChild(link)
                  window.URL.revokeObjectURL(url)
                }}
                className="w-full bg-blue-600 text-white px-4 py-2 text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                📊 Exporter CSV
              </button>
            </div>

            {/* Export JSON */}
            <div className="bg-white border border-gray-200 p-4 flex flex-col justify-between h-full">
              <div>
                <h4 className="text-base font-medium text-gray-900 mb-1">Export JSON Détaillé</h4>
                <p className="text-sm text-gray-600 mb-3">Format JSON avec métadonnées complètes</p>
                <div className="text-xs text-gray-500 mb-4">
                  <p>• Structure complète pour analyse avancée</p>
                  <p>• Métadonnées de performance incluses</p>
                  {cacheStatus?.is_available && (
                    <p>• Informations de cache détaillées</p>
                  )}
                </div>
              </div>
              <button
                onClick={() => {
                  const exportData = {
                    export_metadata: {
                      timestamp: new Date().toISOString(),
                      data_source: cacheStatus?.is_available ? 'ultra_fast_cache' : 'direct_query',
                      performance_gain: cacheStatus?.performance_gain || 'N/A',
                      cache_age_minutes: cacheStatus?.cache_age_minutes || null,
                      version: '2.0'
                    },
                    invitation_statistics: invitationStats,
                    cache_information: cacheStatus ? {
                      is_cache_enabled: cacheStatus.is_available,
                      last_cache_update: cacheStatus.last_update,
                      next_cache_update: cacheStatus.next_update,
                      cache_performance: cacheStatus.performance_gain
                    } : null,
                    computed_metrics: {
                      pending_invitations: invitationStats.total_invitations_sent - invitationStats.total_invitations_accepted,
                      success_rate: invitationStats.acceptance_rate,
                      average_invitations_per_inviter: invitationStats.unique_inviters > 0 ? 
                        (invitationStats.total_invitations_sent / invitationStats.unique_inviters).toFixed(2) : 0,
                      performance_rating: invitationStats.acceptance_rate >= 75 ? 'excellent' :
                                         invitationStats.acceptance_rate >= 50 ? 'good' : 'needs_improvement'
                    },
                    detailed_analysis: {
                      top_performers: invitationStats.top_accepted.slice(0, 3).map(inviter => ({
                        name: inviter.inviter_name,
                        email: inviter.inviter_email,
                        success_count: inviter.invitations_accepted,
                        efficiency: inviter.acceptance_rate
                      })),
                      most_active: invitationStats.top_inviters.slice(0, 3).map(inviter => ({
                        name: inviter.inviter_name,
                        email: inviter.inviter_email,
                        invitation_count: inviter.invitations_sent,
                        success_rate: inviter.acceptance_rate
                      }))
                    }
                  }
                  
                  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportData, null, 2))
                  const link = document.createElement("a")
                  link.setAttribute("href", dataStr)
                  link.setAttribute("download", `invitations_complete_${cacheStatus?.is_available ? 'cached' : 'direct'}_${new Date().toISOString().split('T')[0]}.json`)
                  document.body.appendChild(link)
                  link.click()
                  document.body.removeChild(link)
                }}
                className="w-full bg-blue-600 text-white px-4 py-2 text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                🔧 Exporter JSON
              </button>
            </div>

          </div>
        </div>
      </div>
    </div>
  )
}