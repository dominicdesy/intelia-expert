import React, { useReducer } from 'react'
import { useTranslation } from '@/lib/languages/i18n'
import { useUser } from '@/lib/hooks/useAuthStore'
import { apiClient } from '@/lib/api/client'

interface InviteFriendModalProps {
  onClose: () => void
}

// Types basés sur votre backend
interface InvitationResult {
  email: string
  success: boolean
  status: 'sent' | 'resent' | 'skipped' | 'failed'
  reason?: string
  message: string
  details?: Record<string, any>
}

interface InvitationResponse {
  success: boolean
  sent_count: number
  resent_count: number
  skipped_count: number
  failed_count: number
  message: string
  results: InvitationResult[]
}

// État du modal avec useReducer
interface ModalState {
  emails: string
  personalMessage: string
  isLoading: boolean
  errors: string[]
  results: InvitationResponse | null
  validationResults: any | null
}

type ModalAction =
  | { type: 'SET_EMAILS'; payload: string }
  | { type: 'SET_MESSAGE'; payload: string }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERRORS'; payload: string[] }
  | { type: 'SET_RESULTS'; payload: InvitationResponse }
  | { type: 'SET_VALIDATION'; payload: any }
  | { type: 'CLEAR_RESULTS' }
  | { type: 'RESET' }

const initialState: ModalState = {
  emails: '',
  personalMessage: '',
  isLoading: false,
  errors: [],
  results: null,
  validationResults: null
}

function modalReducer(state: ModalState, action: ModalAction): ModalState {
  switch (action.type) {
    case 'SET_EMAILS':
      return { ...state, emails: action.payload, errors: [] }
    case 'SET_MESSAGE':
      return { ...state, personalMessage: action.payload }
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload }
    case 'SET_ERRORS':
      return { ...state, errors: action.payload }
    case 'SET_RESULTS':
      return { ...state, results: action.payload, isLoading: false }
    case 'SET_VALIDATION':
      return { ...state, validationResults: action.payload }
    case 'CLEAR_RESULTS':
      return { ...state, results: null, validationResults: null }
    case 'RESET':
      return { ...initialState }
    default:
      return state
  }
}

// Hook personnalisé pour la logique d'invitation
function useInvitations() {
  const { user } = useUser()

  const validateEmails = (emailString: string) => {
    const emailList = emailString
      .split(',')
      .map(email => email.trim())
      .filter(email => email.length > 0)
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    const valid: string[] = []
    const invalid: string[] = []
    
    emailList.forEach(email => {
      if (emailRegex.test(email)) {
        valid.push(email)
      } else {
        invalid.push(email)
      }
    })
    
    return { valid, invalid }
  }

  const validateEmailsOnServer = async (emails: string[]) => {
    try {
      const response = await apiClient.postSecure('/invitations/validate', { emails })
      return response.success ? response.data : null
    } catch (error) {
      console.error('Erreur validation serveur:', error)
      return null
    }
  }

  const sendInvitations = async (emails: string[], personalMessage: string) => {
    if (!user?.email || !user?.name) {
      throw new Error('Utilisateur non connecté')
    }

    const payload = {
      emails,
      personal_message: personalMessage.trim(),
      inviter_name: user.name,
      inviter_email: user.email,
      language: user.language || 'fr',
      force_send: false
    }

    const response = await apiClient.postSecure('/invitations/send', payload)
    
    if (!response.success) {
      throw new Error(response.error?.message || 'Erreur lors de l\'envoi des invitations')
    }

    return response.data
  }

  const getInvitationStats = async () => {
    try {
      const response = await apiClient.getSecure('/invitations/stats/summary')
      return response.success ? response.data : null
    } catch (error) {
      console.error('Erreur récupération stats:', error)
      return null
    }
  }

  return {
    validateEmails,
    validateEmailsOnServer,
    sendInvitations,
    getInvitationStats
  }
}

export const InviteFriendModal: React.FC<InviteFriendModalProps> = ({ onClose }) => {
  const { t } = useTranslation()
  const { user, isAuthenticated, hasHydrated } = useUser()
  const [state, dispatch] = useReducer(modalReducer, initialState)
  const { validateEmails, validateEmailsOnServer, sendInvitations } = useInvitations()

  // Vérification d'authentification
  if (!hasHydrated) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600">Vérification de la session...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!isAuthenticated || !user?.email) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
          <div className="text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Connexion requise</h2>
            <p className="text-sm text-gray-600 mb-4">Vous devez être connecté pour envoyer des invitations.</p>
            <button 
              onClick={onClose} 
              className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              Fermer
            </button>
          </div>
        </div>
      </div>
    )
  }

  const handleSendInvitations = async () => {
    dispatch({ type: 'SET_ERRORS', payload: [] })
    dispatch({ type: 'CLEAR_RESULTS' })
    
    if (!state.emails.trim()) {
      dispatch({ type: 'SET_ERRORS', payload: ['Au moins une adresse email est requise'] })
      return
    }

    const { valid, invalid } = validateEmails(state.emails)
    
    if (invalid.length > 0) {
      dispatch({ type: 'SET_ERRORS', payload: [
        `Adresses email invalides : ${invalid.join(', ')}`,
        'Format attendu : email@exemple.com'
      ]})
      return
    }

    if (valid.length === 0) {
      dispatch({ type: 'SET_ERRORS', payload: ['Aucune adresse email valide trouvée'] })
      return
    }

    if (valid.length > 10) {
      dispatch({ type: 'SET_ERRORS', payload: ['Maximum 10 invitations à la fois'] })
      return
    }

    dispatch({ type: 'SET_LOADING', payload: true })
    
    try {
      const result = await sendInvitations(valid, state.personalMessage)
      dispatch({ type: 'SET_RESULTS', payload: result })
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur lors de l\'envoi des invitations'
      dispatch({ type: 'SET_ERRORS', payload: [errorMessage] })
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false })
    }
  }

  const getEmailCount = () => {
    const { valid } = validateEmails(state.emails)
    return valid.length
  }

  const getFriendlyMessage = (result: InvitationResult) => {
    switch (result.status) {
      case 'sent':
        return `Invitation envoyée : ${result.email}`
      case 'resent':
        return `Invitation renvoyée : ${result.email}`
      case 'skipped':
        return result.message || `Invitation ignorée : ${result.email}`
      case 'failed':
        return `Échec d'envoi : ${result.email}`
      default:
        return result.message
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'sent':
      case 'resent':
        return '✅'
      case 'skipped':
        return '💤'
      case 'failed':
        return '❌'
      default:
        return '❓'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'sent':
      case 'resent':
        return 'bg-green-50 border-green-400'
      case 'skipped':
        return 'bg-blue-50 border-blue-400'
      case 'failed':
        return 'bg-red-50 border-red-400'
      default:
        return 'bg-gray-50 border-gray-400'
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Inviter des amis</h2>
          <button 
            onClick={onClose} 
            className="text-gray-400 hover:text-gray-600 text-2xl transition-colors hover:bg-gray-100 rounded-full w-8 h-8 flex items-center justify-center"
          >
            ×
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6">
          <div className="space-y-6">
            {/* Header avec icône */}
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M18 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zM3 19.235v-.11a6.375 6.375 0 0112.75 0v.109A12.318 12.318 0 019.374 21c-2.331 0-4.512-.645-6.374-1.766z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Partagez Intelia Expert
              </h3>
              <p className="text-sm text-gray-600">
                Invitez vos collègues à découvrir l'assistant IA spécialisé en agriculture
              </p>
            </div>

            {/* Résultats */}
            {state.results && (
              <div className="space-y-4">
                <h4 className="text-lg font-semibold text-gray-900">Résultats d'envoi</h4>

                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm font-medium text-gray-900 mb-2">{state.results.message}</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div className="text-center">
                      <div className="text-xl font-semibold text-green-600">{state.results.sent_count}</div>
                      <div className="text-gray-600">Envoyées</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-semibold text-blue-600">{state.results.resent_count}</div>
                      <div className="text-gray-600">Renvoyées</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-semibold text-yellow-600">{state.results.skipped_count}</div>
                      <div className="text-gray-600">Ignorées</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-semibold text-red-600">{state.results.failed_count}</div>
                      <div className="text-gray-600">Échecs</div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3 max-h-48 overflow-y-auto">
                  {state.results.results.map((result, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded-lg border-l-4 ${getStatusColor(result.status)}`}
                    >
                      <div className="flex items-start space-x-3">
                        <span className="text-lg">{getStatusIcon(result.status)}</span>
                        <div className="flex-1">
                          <p className="text-sm text-gray-800 font-medium">
                            {getFriendlyMessage(result)}
                          </p>
                          {result.details && Object.keys(result.details).length > 0 && (
                            <div className="mt-1 text-xs text-gray-500">
                              {result.details.registered_since && (
                                <p>Inscrit depuis : {new Date(result.details.registered_since).toLocaleDateString('fr-FR')}</p>
                              )}
                              {result.details.hours_remaining && (
                                <p>Prochain renvoi possible dans : {result.details.hours_remaining}h</p>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex space-x-3">
                  <button
                    onClick={() => dispatch({ type: 'RESET' })}
                    className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-200 transition-colors"
                  >
                    Inviter d'autres personnes
                  </button>
                  <button
                    onClick={onClose}
                    className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors"
                  >
                    Fermer
                  </button>
                </div>
              </div>
            )}

            {/* Messages d'erreur */}
            {state.errors.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="text-red-800">
                  <p className="font-medium mb-2 flex items-center">
                    <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                    </svg>
                    Erreur de validation
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-sm">
                    {state.errors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Formulaire principal */}
            {!state.results && (
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Adresses email
                    {getEmailCount() > 0 && (
                      <span className="ml-2 text-blue-600 font-normal">
                        ({getEmailCount()} destinataire{getEmailCount() > 1 ? 's' : ''})
                      </span>
                    )}
                  </label>
                  <textarea
                    value={state.emails}
                    onChange={(e) => dispatch({ type: 'SET_EMAILS', payload: e.target.value })}
                    placeholder="email1@exemple.com, email2@exemple.com, ..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                    rows={3}
                    disabled={state.isLoading}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Séparez les adresses par des virgules. Maximum 10 invitations.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Message personnel 
                    <span className="text-gray-500 font-normal">(optionnel)</span>
                  </label>
                  <textarea
                    value={state.personalMessage}
                    onChange={(e) => dispatch({ type: 'SET_MESSAGE', payload: e.target.value })}
                    placeholder="Ajouter un message personnel à votre invitation..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                    rows={4}
                    maxLength={500}
                    disabled={state.isLoading}
                  />
                  <div className="flex justify-between items-center mt-1">
                    <p className="text-xs text-gray-500">
                      Ce message sera inclus dans l'email d'invitation
                    </p>
                    <span className="text-xs text-gray-400">
                      {state.personalMessage.length}/500
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Boutons d'action */}
            <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
              {!state.results && (
                <button
                  onClick={handleSendInvitations}
                  disabled={state.isLoading || getEmailCount() === 0}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center space-x-2"
                >
                  {state.isLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Envoi en cours...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                      </svg>
                      <span>
                        Envoyer {getEmailCount() > 0 ? `(${getEmailCount()})` : ''}
                      </span>
                    </>
                  )}
                </button>
              )}
            </div>

            {/* Footer */}
            <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-100">
              Les invitations sont gérées de manière sécurisée. Vos contacts ne recevront qu'un seul email d'invitation.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}