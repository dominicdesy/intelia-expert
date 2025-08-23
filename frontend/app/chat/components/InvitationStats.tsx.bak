import React from 'react'

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

interface InvitationStatsProps {
  invitationStats: InvitationStats | null
}

export const InvitationStatsComponent: React.FC<InvitationStatsProps> = ({
  invitationStats
}) => {
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
      {/* KPIs Invitations - Style Compass */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Invitations Envoyées */}
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Invitations Envoyées</p>
            <p className="text-2xl font-semibold text-gray-900">{invitationStats.total_invitations_sent}</p>
          </div>
        </div>

        {/* Total Invitations Acceptées */}
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Invitations Acceptées</p>
            <p className="text-2xl font-semibold text-green-600">{invitationStats.total_invitations_accepted}</p>
          </div>
        </div>

        {/* Utilisateurs Inviteurs */}
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Utilisateurs Inviteurs</p>
            <p className="text-2xl font-semibold text-gray-900">{invitationStats.unique_inviters}</p>
          </div>
        </div>

        {/* Taux d'Acceptation Global */}
        <div className="bg-white border border-gray-200 p-4">
          <div>
            <p className="text-sm text-gray-600 mb-1">Taux d'Acceptation</p>
            <p className="text-2xl font-semibold text-blue-600">{invitationStats.acceptance_rate.toFixed(1)}%</p>
          </div>
        </div>
      </div>

      {/* Tables des Top Inviters */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Top 5 Inviteurs par Nombre d'Invitations */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-base font-medium text-gray-900">Top 5 - Invitations Envoyées</h3>
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
            <h3 className="text-base font-medium text-gray-900">Top 5 - Invitations Acceptées</h3>
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
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Section de Performance Invitations */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-base font-medium text-gray-900">Performance des Invitations</h3>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-white border border-gray-200">
              <p className="text-lg font-semibold text-gray-900">{invitationStats.total_invitations_sent}</p>
              <p className="text-xs text-gray-600">Total Envoyées</p>
            </div>
            <div className="text-center p-3 bg-white border border-gray-200">
              <p className="text-lg font-semibold text-green-600">{invitationStats.total_invitations_accepted}</p>
              <p className="text-xs text-gray-600">Total Acceptées</p>
            </div>
            <div className="text-center p-3 bg-white border border-gray-200">
              <p className="text-lg font-semibold text-gray-900">{invitationStats.total_invitations_sent - invitationStats.total_invitations_accepted}</p>
              <p className="text-xs text-gray-600">En Attente</p>
            </div>
            <div className="text-center p-3 bg-white border border-gray-200">
              <p className="text-lg font-semibold text-blue-600">{invitationStats.acceptance_rate.toFixed(1)}%</p>
              <p className="text-xs text-gray-600">Taux Global</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}