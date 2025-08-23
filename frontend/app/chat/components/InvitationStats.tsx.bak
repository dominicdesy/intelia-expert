import React from 'react'

// 🚀 NOUVEAU: Interface pour les réponses cache ultra-rapides
interface CacheInvitationResponse {
  cache_info: {
    is_available: boolean
    last_update: string | null
    cache_age_minutes: number
    performance_gain: string
    next_update: string | null
  }
  invitation_stats: InvitationStats
}

// CONSERVATION INTÉGRALE: Interface existante
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

// 🚀 MODIFIÉE: Props avec support du cache
interface InvitationStatsProps {
  invitationStats: InvitationStats | null
  // 🚀 NOUVEAU: Props optionnelles pour le cache
  cacheStatus?: {
    is_available: boolean
    last_update: string | null
    cache_age_minutes: number
    performance_gain: string
    next_update: string | null
  } | null
  isLoading?: boolean
  useFastEndpoints?: boolean
}

export const InvitationStatsComponent: React.FC<InvitationStatsProps> = ({
  invitationStats,
  // 🚀 NOUVEAU: Propriétés cache avec valeurs par défaut
  cacheStatus = null,
  isLoading = false,
  useFastEndpoints = true
}) => {
  // 🚀 NOUVEAU: Affichage spécial pendant le chargement avec indicateur de mode
  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 p-8 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Chargement des statistiques d'invitations...</p>
        <p className="text-xs text-gray-400 mt-2">
          {useFastEndpoints ? '⚡ Mode cache ultra-rapide' : '📦 Mode classique'}
        </p>
      </div>
    )
  }

  if (!invitationStats) {
    return (
      <div className="bg-white border border-gray-200 p-4">
        <div className="text-center text-gray-500">
          <div className="text-gray-400 text-2xl mb-2">📨</div>
          <p>Statistiques d'invitations non disponibles</p>
          {/* 🚀 NOUVEAU: Information sur la tentative de cache */}
          <p className="text-xs text-gray-400 mt-2">
            Mode {useFastEndpoints ? 'cache ultra-rapide' : 'classique'} - Aucune donnée
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 🚀 NOUVEAU: Header avec indicateur de performance cache */}
      {cacheStatus && cacheStatus.is_available && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></div>
                <h3 className="text-base font-medium text-green-900">📊 Données Ultra-Rapides</h3>
              </div>
              <div className="flex items-center space-x-4 text-sm text-green-700">
                <span>⚡ Chargé en {cacheStatus.performance_gain}</span>
                <span>📅 MàJ: {cacheStatus.last_update ? new Date(cacheStatus.last_update).toLocaleString('fr-FR', { 
                  month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                }) : 'N/A'}</span>
                <span>⏱️ Âge: {cacheStatus.cache_age_minutes}min</span>
              </div>
            </div>
            <div className="text-sm text-green-600 font-medium">
              🚀 Performance optimisée
            </div>
          </div>
        </div>
      )}

      {/* KPIs Invitations - CONSERVATION INTÉGRALE Style Compass */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Invitations Envoyées */}
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Invitations Envoyées</p>
            <p className="text-2xl font-semibold text-gray-900">{invitationStats.total_invitations_sent}</p>
            {/* 🚀 NOUVEAU: Petit indicateur source des données */}
            {cacheStatus && (
              <p className="text-xs text-gray-400 mt-1">
                {cacheStatus.is_available ? '⚡ Cache' : '📦 Direct'}
              </p>
            )}
          </div>
        </div>

        {/* Total Invitations Acceptées */}
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Invitations Acceptées</p>
            <p className="text-2xl font-semibold text-green-600">{invitationStats.total_invitations_accepted}</p>
            {/* 🚀 NOUVEAU: Indicateur de fraîcheur des données */}
            {cacheStatus && cacheStatus.is_available && (
              <p className="text-xs text-green-500 mt-1">
                Données mises en cache
              </p>
            )}
          </div>
        </div>

        {/* Utilisateurs Inviteurs */}
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Utilisateurs Inviteurs</p>
            <p className="text-2xl font-semibold text-gray-900">{invitationStats.unique_inviters}</p>
            {/* 🚀 NOUVEAU: Affichage conditionnel du mode */}
            {!cacheStatus?.is_available && (
              <p className="text-xs text-amber-500 mt-1">
                Mode direct
              </p>
            )}
          </div>
        </div>

        {/* Taux d'Acceptation Global */}
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Taux d'Acceptation</p>
            <p className="text-2xl font-semibold text-blue-600">{invitationStats.acceptance_rate.toFixed(1)}%</p>
            {/* 🚀 NOUVEAU: Performance gain si disponible */}
            {cacheStatus?.is_available && (
              <p className="text-xs text-blue-500 mt-1">
                ⚡ {cacheStatus.performance_gain}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* 🚀 NOUVEAU: Section d'information sur les données (optionnelle) */}
      {cacheStatus && !cacheStatus.is_available && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <div className="flex items-center space-x-2 text-amber-800">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span className="text-sm font-medium">Données chargées en mode direct</span>
            <span className="text-xs bg-amber-200 text-amber-800 px-2 py-1 rounded">
              Performances standard
            </span>
          </div>
        </div>
      )}

      {/* Tables des Top Inviters - CONSERVATION INTÉGRALE */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Top 5 Inviteurs par Nombre d'Invitations - CODE ORIGINAL CONSERVÉ */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-medium text-gray-900">Top 5 - Invitations Envoyées</h3>
              {/* 🚀 NOUVEAU: Badge de source des données */}
              {cacheStatus && (
                <span className={`text-xs px-2 py-1 rounded ${
                  cacheStatus.is_available 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {cacheStatus.is_available ? '⚡ Cache' : '📦 Direct'}
                </span>
              )}
            </div>
          </div>
          <div className="overflow-hidden">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Inviteur</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Envoyées</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Acceptées</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Taux</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {invitationStats.top_inviters.slice(0, 5).map((inviter, index) => (
                  <tr key={inviter.inviter_email || `inviter-${index}`} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm text-gray-900 max-w-48">
                      <div className="truncate" title={inviter.inviter_email}>
                        <div className="font-medium">{inviter.inviter_name || 'Nom non disponible'}</div>
                        <div className="text-xs text-gray-500">{inviter.inviter_email}</div>
                      </div>
                    </td>
                    <td className="px-4 py-2 text-sm font-medium text-gray-900">{inviter.invitations_sent}</td>
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
                    <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                      <div className="text-gray-400 text-2xl mb-2">📨</div>
                      <p>Aucun inviteur trouvé</p>
                      {/* 🚀 NOUVEAU: Information sur le mode de chargement */}
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

        {/* Top 5 Inviteurs par Acceptations - CODE ORIGINAL CONSERVÉ */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-medium text-gray-900">Top 5 - Invitations Acceptées</h3>
              {/* 🚀 NOUVEAU: Indicateur de temps de mise à jour */}
              {cacheStatus && cacheStatus.is_available && (
                <span className="text-xs text-green-600">
                  ⏱️ {cacheStatus.cache_age_minutes}min
                </span>
              )}
            </div>
          </div>
          <div className="overflow-hidden">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Inviteur</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Acceptées</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Taux</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {invitationStats.top_accepted.slice(0, 5).map((inviter, index) => (
                  <tr key={inviter.inviter_email || `accepted-${index}`} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm text-gray-900 max-w-48">
                      <div className="truncate" title={inviter.inviter_email}>
                        <div className="font-medium">{inviter.inviter_name || 'Nom non disponible'}</div>
                        <div className="text-xs text-gray-500">{inviter.inviter_email}</div>
                      </div>
                    </td>
                    <td className="px-4 py-2 text-sm font-bold text-green-600">{inviter.invitations_accepted}</td>
                    <td className="px-4 py-2 text-sm text-gray-600">{inviter.invitations_sent}</td>
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
                {invitationStats.top_accepted.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                      <div className="text-gray-400 text-2xl mb-2">✅</div>
                      <p>Aucune invitation acceptée</p>
                      {/* 🚀 NOUVEAU: Information contextuelle */}
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

      {/* Section de Performance Invitations - CONSERVATION INTÉGRALE avec améliorations cache */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-medium text-gray-900">Performance des Invitations</h3>
            {/* 🚀 NOUVEAU: Horodatage des données */}
            {cacheStatus && cacheStatus.last_update && (
              <div className="text-xs text-gray-500">
                📅 Dernière MàJ: {new Date(cacheStatus.last_update).toLocaleString('fr-FR')}
              </div>
            )}
          </div>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-white border border-gray-200 relative">
              <p className="text-lg font-semibold text-gray-900">{invitationStats.total_invitations_sent}</p>
              <p className="text-xs text-gray-600">Total Envoyées</p>
              {/* 🚀 NOUVEAU: Badge de performance dans les coins */}
              {cacheStatus?.is_available && (
                <div className="absolute top-1 right-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              )}
            </div>
            <div className="text-center p-3 bg-white border border-gray-200 relative">
              <p className="text-lg font-semibold text-green-600">{invitationStats.total_invitations_accepted}</p>
              <p className="text-xs text-gray-600">Total Acceptées</p>
              {cacheStatus?.is_available && (
                <div className="absolute top-1 right-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              )}
            </div>
            <div className="text-center p-3 bg-white border border-gray-200 relative">
              <p className="text-lg font-semibold text-gray-900">{invitationStats.total_invitations_sent - invitationStats.total_invitations_accepted}</p>
              <p className="text-xs text-gray-600">En Attente</p>
              {cacheStatus?.is_available && (
                <div className="absolute top-1 right-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              )}
            </div>
            <div className="text-center p-3 bg-white border border-gray-200 relative">
              <p className="text-lg font-semibold text-blue-600">{invitationStats.acceptance_rate.toFixed(1)}%</p>
              <p className="text-xs text-gray-600">Taux Global</p>
              {cacheStatus?.is_available && (
                <div className="absolute top-1 right-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              )}
            </div>
          </div>

          {/* 🚀 NOUVEAU: Section d'informations sur le cache détaillée */}
          {cacheStatus && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className={`inline-flex items-center space-x-1 ${
                    cacheStatus.is_available ? 'text-green-600' : 'text-amber-600'
                  }`}>
                    {cacheStatus.is_available ? (
                      <>
                        <div className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></div>
                        <span className="font-medium">Cache Actif</span>
                      </>
                    ) : (
                      <>
                        <div className="w-2 h-2 bg-amber-600 rounded-full"></div>
                        <span className="font-medium">Mode Direct</span>
                      </>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Source des données
                  </p>
                </div>

                <div className="text-center">
                  <div className="font-medium text-blue-600">
                    {cacheStatus.is_available ? cacheStatus.performance_gain : 'Performance standard'}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Temps de chargement
                  </p>
                </div>

                <div className="text-center">
                  <div className="font-medium text-gray-700">
                    {cacheStatus.next_update ? new Date(cacheStatus.next_update).toLocaleString('fr-FR', {
                      hour: '2-digit', 
                      minute: '2-digit'
                    }) : 'Automatique'}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Prochaine mise à jour
                  </p>
                </div>
              </div>

              {/* 🚀 NOUVEAU: Barre de progression de la fraîcheur du cache */}
              {cacheStatus.is_available && (
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>Fraîcheur des données</span>
                    <span>{Math.max(0, 60 - cacheStatus.cache_age_minutes)}min restantes</span>
                  </div>
                  <div className="w-full bg-gray-200 h-1 rounded">
                    <div 
                      className={`h-1 rounded transition-all duration-300 ${
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

      {/* 🚀 NOUVEAU: Section d'export améliorée avec informations cache */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-medium text-gray-900">Export des Statistiques d'Invitations</h3>
            {cacheStatus?.is_available && (
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                ⚡ Données ultra-rapides
              </span>
            )}
          </div>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Export CSV - Amélioré avec infos cache */}
            <div className="bg-white border border-gray-200 p-4 flex flex-col justify-between h-full">
              <div>
                <h4 className="text-base font-medium text-gray-900 mb-1">Export CSV Complet</h4>
                <p className="text-sm text-gray-600 mb-3">Toutes les statistiques au format CSV</p>
                <div className="text-xs text-gray-500 mb-4">
                  <p>• Top inviteurs et statistiques détaillées</p>
                  <p>• Données {cacheStatus?.is_available ? 'optimisées par cache' : 'en temps réel'}</p>
                  {cacheStatus?.is_available && (
                    <p>• ⚡ Exporté en {cacheStatus.performance_gain}</p>
                  )}
                </div>
              </div>
              <button
                onClick={() => {
                  // Données détaillées pour l'export CSV
                  const csvData = [
                    ['Métrique', 'Valeur', 'Source', 'Timestamp'],
                    ['Total Invitations Envoyées', invitationStats.total_invitations_sent, cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['Total Invitations Acceptées', invitationStats.total_invitations_accepted, cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['Taux d\'Acceptation Global', `${invitationStats.acceptance_rate.toFixed(1)}%`, cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['Nombre d\'Inviteurs Uniques', invitationStats.unique_inviters, cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['', '', '', ''], // Séparateur
                    ['Top Inviteurs (Envoyées)', '', '', ''],
                    ...invitationStats.top_inviters.map(inviter => [
                      inviter.inviter_name || inviter.inviter_email,
                      inviter.invitations_sent,
                      inviter.invitations_accepted,
                      `${inviter.acceptance_rate.toFixed(1)}%`
                    ]),
                    ['', '', '', ''], // Séparateur
                    ['Top Inviteurs (Acceptées)', '', '', ''],
                    ...invitationStats.top_accepted.map(inviter => [
                      inviter.inviter_name || inviter.inviter_email,
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

            {/* Export JSON - Amélioré avec métadonnées cache */}
            <div className="bg-white border border-gray-200 p-4 flex flex-col justify-between h-full">
              <div>
                <h4 className="text-base font-medium text-gray-900 mb-1">Export JSON Détaillé</h4>
                <p className="text-sm text-gray-600 mb-3">Format JSON avec métadonnées complètes</p>
                <div className="text-xs text-gray-500 mb-4">
                  <p>• Structure complète pour analyse avancée</p>
                  <p>• Métadonnées de performance incluses</p>
                  {cacheStatus?.is_available && (
                    <p>• 🚀 Informations de cache détaillées</p>
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
                        (invitationStats.total_invitations_sent / invitationStats.unique_inviters).toFixed(2) : 0
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