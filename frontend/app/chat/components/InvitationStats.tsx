import React from 'react'

// Interface pour les statistiques d'invitations - COMPLÃˆTE
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
          <div className="text-gray-400 text-2xl mb-2">ðŸ"¨</div>
          <p>Statistiques d'invitations non disponibles</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header Ã©purÃ© - sans informations de debug */}



      {/* KPIs Invitations - Version complÃ¨te */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Invitations EnvoyÃ©es</p>
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
            <p className="text-sm text-gray-600 mb-1">Invitations AcceptÃ©es</p>
            <p className="text-2xl font-semibold text-green-600">{invitationStats.total_invitations_accepted}</p>
            {cacheStatus && cacheStatus.is_available && (
              <p className="text-xs text-green-500 mt-1">DonnÃ©es mises en cache</p>
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
              <p className="text-xs text-blue-500 mt-1">OptimisÃ©</p>
            )}
          </div>
        </div>
      </div>

      {/* Tables des Top Inviters - Version complÃ¨te avec toutes les donnÃ©es */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Top 5 Inviteurs par Nombre d'Invitations */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-medium text-gray-900">Top 5 - Invitations EnvoyÃ©es</h3>
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
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">EnvoyÃ©es</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">AcceptÃ©es</th>
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
                      <div className="text-gray-400 text-2xl mb-2">ðŸ"¨</div>
                      <p>Aucun inviteur trouvÃ©</p>
                      {cacheStatus && (
                        <p className="text-xs text-gray-400 mt-1">
                          Mode {cacheStatus.is_available ? 'cache' : 'direct'} - Aucune donnÃ©e
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
              <h3 className="text-base font-medium text-gray-900">Top 5 - Invitations AcceptÃ©es</h3>
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
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">AcceptÃ©es</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">EfficacitÃ©</th>
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
                          <span className="text-green-600 text-sm">ðŸ†</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {invitationStats.top_accepted.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                      <div className="text-gray-400 text-2xl mb-2">âœ…</div>
                      <p>Aucune invitation acceptÃ©e</p>
                      {cacheStatus && (
                        <p className="text-xs text-gray-400 mt-1">
                          DonnÃ©es {cacheStatus.is_available ? 'en cache' : 'directes'} - Aucun rÃ©sultat
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

      {/* Section de Performance Invitations dÃ©taillÃ©e */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-medium text-gray-900">Performance des Invitations</h3>
            {cacheStatus && cacheStatus.last_update && (
              <div className="text-xs text-gray-500">
                DerniÃ¨re MAJ: {new Date(cacheStatus.last_update).toLocaleString('fr-FR')}
              </div>
            )}
          </div>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="text-center p-4 bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 rounded-lg relative">
              <p className="text-2xl font-bold text-blue-900">{invitationStats.total_invitations_sent}</p>
              <p className="text-sm text-blue-700">Total EnvoyÃ©es</p>
              {cacheStatus?.is_available && (
                <div className="absolute top-2 right-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              )}
            </div>
            <div className="text-center p-4 bg-gradient-to-br from-green-50 to-green-100 border border-green-200 rounded-lg relative">
              <p className="text-2xl font-bold text-green-900">{invitationStats.total_invitations_accepted}</p>
              <p className="text-sm text-green-700">Total AcceptÃ©es</p>
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
        </div>
      </div>

      {/* Section d'export complÃ¨te avec informations cache */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-medium text-gray-900">Export des Statistiques d'Invitations</h3>
            {cacheStatus?.is_available && (
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                DonnÃ©es optimisÃ©es
              </span>
            )}
          </div>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 gap-4">
            
            {/* Export CSV */}
            <div className="bg-white border border-gray-200 p-4 flex flex-col justify-between h-full">
              <div>
                <h4 className="text-base font-medium text-gray-900 mb-1">Export CSV Complet</h4>
                <p className="text-sm text-gray-600 mb-3">Toutes les statistiques au format CSV</p>
                <div className="text-xs text-gray-500 mb-4">
                  <p>â€¢ Top inviteurs et statistiques dÃ©taillÃ©es</p>
                  <p>â€¢ DonnÃ©es {cacheStatus?.is_available ? 'optimisÃ©es par cache' : 'en temps rÃ©el'}</p>
                  {cacheStatus?.is_available && (
                    <p>â€¢ ExportÃ© avec performance optimisÃ©e</p>
                  )}
                </div>
              </div>
              <button
                onClick={() => {
                  const csvData = [
                    ['MÃ©trique', 'Valeur', 'Source', 'Timestamp'],
                    ['Total Invitations EnvoyÃ©es', invitationStats.total_invitations_sent, cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['Total Invitations AcceptÃ©es', invitationStats.total_invitations_accepted, cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['Taux d\'Acceptation Global', `${invitationStats.acceptance_rate.toFixed(1)}%`, cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['Nombre d\'Inviteurs Uniques', invitationStats.unique_inviters, cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['Moyenne Invitations par Inviteur', invitationStats.unique_inviters > 0 ? (invitationStats.total_invitations_sent / invitationStats.unique_inviters).toFixed(1) : '0', cacheStatus?.is_available ? 'Cache' : 'Direct', new Date().toISOString()],
                    ['', '', '', ''],
                    ['Top Inviteurs (EnvoyÃ©es)', '', '', ''],
                    ['Rang', 'Nom', 'Email', 'EnvoyÃ©es', 'AcceptÃ©es', 'Taux'],
                    ...invitationStats.top_inviters.map((inviter, index) => [
                      index + 1,
                      inviter.inviter_name || 'N/A',
                      inviter.inviter_email,
                      inviter.invitations_sent,
                      inviter.invitations_accepted,
                      `${inviter.acceptance_rate.toFixed(1)}%`
                    ]),
                    ['', '', '', ''],
                    ['Top Inviteurs (AcceptÃ©es)', '', '', ''],
                    ['Rang', 'Nom', 'Email', 'AcceptÃ©es', 'Total', 'EfficacitÃ©'],
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
                className="bg-blue-600 text-white px-4 py-2 text-sm font-medium hover:bg-blue-700 transition-colors inline-flex items-center space-x-2 w-fit"
              >
                <span>ðŸ"Š</span>
                <span>Exporter CSV</span>
              </button>
            </div>

          </div>
        </div>
      </div>
    </div>
  )
}