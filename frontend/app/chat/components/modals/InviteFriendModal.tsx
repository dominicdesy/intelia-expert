import React, { useState, useMemo, useEffect } from 'react'
import { useTranslation } from '../../hooks/useTranslation'
import { useAuthStore } from '@/lib/stores/auth' 
import { getSupabaseClient } from '@/lib/supabase/singleton'

interface InviteFriendModalProps {
  onClose: () => void
}

// Types pour les nouvelles fonctionnalités
interface InvitationResult {
  email: string;
  success: boolean;
  status: 'sent' | 'skipped' | 'failed';
  reason?: string;
  message: string;
  details?: {
    registered_since?: string;
    last_login?: string;
    invited_by?: string;
    invited_at?: string;
  };
}

interface InvitationResponse {
  success: boolean;
  sent_count: number;
  skipped_count: number;
  failed_count: number;
  message: string;
  results: InvitationResult[];
}

// ==================== SERVICE D'INVITATION AMÉLIORÉ ====================
const invitationService = {
  // Nouvelle fonction : Pré-validation des emails
  async validateEmails(emails: string[]): Promise<any> {
    try {
      const supabase = getSupabaseClient()
      const { data, error } = await supabase.auth.getSession()
      if (error || !data.session?.access_token) {
        throw new Error('Session expirée - reconnexion nécessaire')
      }

      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert.intelia.com/api'
      const cleanBaseUrl = baseUrl.replace(/\/api\/?$/, '')
      const validateUrl = `${cleanBaseUrl}/api/v1/invitations/validate`
      
      const response = await fetch(validateUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
          'Accept': 'application/json',
          'Authorization': `Bearer ${data.session.access_token}`
        },
        body: JSON.stringify(emails)
      })

      if (!response.ok) {
        throw new Error('Erreur lors de la validation')
      }

      return await response.json()
    } catch (error) {
      console.error('❌ Erreur validation emails:', error)
      throw error
    }
  },

  // Fonction d'envoi améliorée (votre fonction existante + nouvelles options)
  async sendInvitation(emails: string[], personalMessage: string, inviterInfo: any, forceSend: boolean = false) {
    try {
      console.log('📧 [InvitationService] Envoi invitation avec détection:', { 
        emails, 
        hasMessage: !!personalMessage,
        inviterEmail: inviterInfo.email,
        forceSend
      })
      
      const supabase = getSupabaseClient()
      const { data, error } = await supabase.auth.getSession()
      if (error) {
        console.error('❌ [InvitationService] Erreur session Supabase:', error)
        throw new Error('Session expirée - reconnexion nécessaire')
      }
      
      const session = data.session
      if (!session?.access_token) {
        throw new Error('Session expirée - reconnexion nécessaire')
      }

      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert.intelia.com/api'
      const cleanBaseUrl = baseUrl.replace(/\/api\/?$/, '')
      const inviteUrl = `${cleanBaseUrl}/api/v1/invitations/send`
      
      const headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json',
        'Authorization': `Bearer ${session.access_token}`
      }
      
      const response = await fetch(inviteUrl, {		  
        method: 'POST',
        headers,
        body: JSON.stringify({
          emails,
          personal_message: personalMessage,
          inviter_name: inviterInfo.name,
          inviter_email: inviterInfo.email,
          language: inviterInfo.language || 'fr',
          force_send: forceSend // 🆕 Nouvelle option
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ [InvitationService] Erreur HTTP:', response.status, errorText)
        
        if (response.status === 401) {
          await supabase.auth.signOut()
          window.location.href = '/'
          throw new Error('Session expirée. Redirection vers la connexion...')
        }
        
        let errorMessage = 'Erreur lors de l\'envoi des invitations'
        try {
          const errorJson = JSON.parse(errorText)
          errorMessage = errorJson.detail || errorJson.message || errorMessage
        } catch {
          // Si ce n'est pas du JSON, garder le message par défaut
        }
        
        throw new Error(errorMessage)
      }

      const result = await response.json()
      console.log('✅ [InvitationService] Invitations envoyées:', result)
      return result
      
    } catch (error) {
      console.error('❌ [InvitationService] Erreur envoi:', error)
      throw error
    }
  }
}

// ==================== MODAL INVITATION AMI AMÉLIORÉE ====================
export const InviteFriendModal: React.FC<InviteFriendModalProps> = ({ onClose }) => {
  const { t } = useTranslation()
  const { user } = useAuthStore() 
  const [emails, setEmails] = useState('')
  const [personalMessage, setPersonalMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [successMessage, setSuccessMessage] = useState('')
  
  // 🆕 Nouveaux états pour les fonctionnalités avancées
  const [showPreValidation, setShowPreValidation] = useState(false)
  const [preValidationResults, setPreValidationResults] = useState<any>(null)
  const [detailedResults, setDetailedResults] = useState<InvitationResponse | null>(null)
  const [forceSend, setForceSend] = useState(false)

  // Calcul de currentUser (votre code existant)
  const currentUser = useMemo(() => {
    if (user?.email) {
      return user
    }
    
    try {
      const supabaseAuth = localStorage.getItem('supabase.auth.token') || sessionStorage.getItem('supabase.auth.token')
      if (supabaseAuth) {
        const authData = JSON.parse(supabaseAuth)
        if (authData.user?.email) {
          const userLanguage = 
            authData.user.user_metadata?.language ||
            authData.user.language ||
            localStorage.getItem('intelia_language') ||
            localStorage.getItem('preferred_language') ||
            (navigator.language.startsWith('en') ? 'en' : 
             navigator.language.startsWith('es') ? 'es' : 'fr')

          return {
            email: authData.user.email,
            name: authData.user.user_metadata?.name || authData.user.name || authData.user.email.split('@')[0],
            id: authData.user.id,
            language: userLanguage
          }
        }
      }
    } catch (e) {
      console.warn('Erreur récupération auth depuis storage:', e)
    }
    
    return null
  }, [user])

  useEffect(() => {
    if (!currentUser?.email) {
      setErrors(['Vous devez être connecté pour envoyer des invitations'])
    } else {
      setErrors([])
    }
  }, [currentUser])

  // Validation des emails (votre fonction existante)
  const validateEmails = (emailString: string): { valid: string[], invalid: string[] } => {
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

  // 🆕 Nouvelle fonction : Pré-validation
  const handlePreValidation = async () => {
    if (!currentUser?.email) {
      setErrors(['Vous devez être connecté pour valider les emails'])
      return
    }

    const { valid, invalid } = validateEmails(emails)
    
    if (invalid.length > 0) {
      setErrors([`Adresses email invalides : ${invalid.join(', ')}`])
      return
    }

    if (valid.length === 0) {
      setErrors(['Aucune adresse email valide trouvée'])
      return
    }

    setIsLoading(true)
    setErrors([])
    
    try {
      const results = await invitationService.validateEmails(valid)
      setPreValidationResults(results)
      setShowPreValidation(true)
    } catch (error) {
      console.error('Erreur pré-validation:', error)
      setErrors(['Erreur lors de la validation des emails'])
    } finally {
      setIsLoading(false)
    }
  }

  // Fonction d'envoi améliorée (basée sur votre fonction existante)
  const handleSendInvitations = async () => {
    setErrors([])
    setSuccessMessage('')
    setDetailedResults(null)
    
    if (!currentUser?.email) {
      setErrors(['Vous devez être connecté pour envoyer des invitations'])
      return
    }

    if (!emails.trim()) {
      setErrors(['Veuillez saisir au moins une adresse email'])
      return
    }

    const { valid, invalid } = validateEmails(emails)
    
    if (invalid.length > 0) {
      setErrors([
        `Adresses email invalides : ${invalid.join(', ')}`,
        'Format attendu : nom@exemple.com'
      ])
      return
    }

    if (valid.length === 0) {
      setErrors(['Aucune adresse email valide trouvée'])
      return
    }

    if (valid.length > 10) {
      setErrors(['Maximum 10 invitations à la fois'])
      return
    }

    setIsLoading(true)
    setShowPreValidation(false)
    
    try {
      console.log('🚀 [InviteFriendModal] Début envoi invitations amélioré:', {
        emails: valid,
        userEmail: currentUser.email,
        userName: currentUser.name,
        userLanguage: currentUser.language,
        forceSend
      })
      
      const result = await invitationService.sendInvitation(
        valid, 
        personalMessage.trim(), 
        {
          name: currentUser.name || currentUser.email?.split('@')[0] || 'Utilisateur Intelia',
          email: currentUser.email,
          language: currentUser.language || 'fr'
        },
        forceSend
      )
      
      // 🆕 Gestion des résultats détaillés
      if (result.results && result.results.length > 0) {
        setDetailedResults(result)
        
        // Message de succès personnalisé
        const messages = []
        if (result.sent_count > 0) {
          messages.push(`✅ ${result.sent_count} invitation${result.sent_count > 1 ? 's' : ''} envoyée${result.sent_count > 1 ? 's' : ''}`)
        }
        if (result.skipped_count > 0) {
          messages.push(`⏭️ ${result.skipped_count} ignorée${result.skipped_count > 1 ? 's' : ''} (utilisateur${result.skipped_count > 1 ? 's' : ''} existant${result.skipped_count > 1 ? 's' : ''})`)
        }
        if (result.failed_count > 0) {
          messages.push(`❌ ${result.failed_count} échec${result.failed_count > 1 ? 's' : ''}`)
        }
        
        setSuccessMessage(messages.join(' • '))
      } else {
        // Fallback vers votre logique existante
        setSuccessMessage(
          `✅ ${result.sent_count} invitation${result.sent_count > 1 ? 's' : ''} envoyée${result.sent_count > 1 ? 's' : ''} avec succès !`
        )
        
        if (result.failed_emails && result.failed_emails.length > 0) {
          setErrors([
            `Certaines invitations ont échoué : ${result.failed_emails.join(', ')}`
          ])
        }
        
        // Réinitialiser le formulaire après 3 secondes si tout est OK
        if (result.failed_emails.length === 0) {
          setTimeout(() => {
            setEmails('')
            setPersonalMessage('')
            setSuccessMessage('')
            onClose()
          }, 3000)
        }
      }
      
    } catch (error) {
      console.error('❌ [InviteFriendModal] Erreur envoi:', error)
      
      let errorMessage = 'Erreur lors de l\'envoi des invitations'
      
      if (error instanceof Error) {
        errorMessage = error.message
      }
      
      if (errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
        setErrors([
          'Erreur d\'autorisation - Vérifiez que vous êtes bien connecté',
          'Si le problème persiste, déconnectez-vous et reconnectez-vous'
        ])
      } else if (errorMessage.includes('401') || errorMessage.includes('Unauthorized')) {
        setErrors([
          'Session expirée - Veuillez vous reconnecter',
          'Votre session a expiré, reconnectez-vous pour continuer'
        ])
      } else {
        setErrors([
          errorMessage,
          'Veuillez réessayer ou contacter le support si le problème persiste.'
        ])
      }
    } finally {
      setIsLoading(false)
    }
  }

  const getEmailCount = () => {
    const { valid } = validateEmails(emails)
    return valid.length
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const getStatusIcon = (status: string, reason?: string) => {
    switch (status) {
      case 'sent': return <span className="text-green-600">✅</span>
      case 'skipped': 
        if (reason === 'user_exists') return <span className="text-blue-600">👤</span>
        return <span className="text-yellow-600">⏭️</span>
      case 'failed': return <span className="text-red-600">❌</span>
      default: return <span className="text-gray-600">⚪</span>
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'sent': return 'bg-green-50 border-green-200 text-green-800'
      case 'skipped': return 'bg-yellow-50 border-yellow-200 text-yellow-800'
      case 'failed': return 'bg-red-50 border-red-200 text-red-800'
      default: return 'bg-gray-50 border-gray-200 text-gray-800'
    }
  }

  // Fonction pour retry les emails ignorés
  const handleRetrySkipped = () => {
    if (detailedResults) {
      const skippedEmails = detailedResults.results
        .filter(r => r.status === 'skipped' || r.status === 'failed')
        .map(r => r.email)
      setEmails(skippedEmails.join(', '))
      setForceSend(true)
      setDetailedResults(null)
      setSuccessMessage('')
    }
  }

  // Affichage conditionnel si pas d'utilisateur (votre code existant)
  if (!currentUser?.email) {
    return (
      <>
        {/* Votre code existant pour l'erreur de connexion */}
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50" onClick={onClose} />
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Inviter des amis</h2>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl">×</button>
            </div>
            <div className="p-6">
              <div className="text-center">
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">Connexion requise</h2>
                <p className="text-sm text-gray-600 mb-4">Vous devez être connecté pour envoyer des invitations</p>
                <button onClick={onClose} className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700">
                  Fermer
                </button>
              </div>
            </div>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50" onClick={onClose} />
      
      {/* Modal Container */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Inviter des amis</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl">×</button>
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
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  Invitez vos collègues à découvrir Intelia Expert
                </h2>
                <p className="text-sm text-gray-600">
                  Partagez la puissance d'Intelia Expert avec votre équipe
                </p>
              </div>

              {/* Messages de succès avec résultats détaillés */}
              {successMessage && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-center">
                    <svg className="w-5 h-5 text-green-600 mr-2" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-green-800 font-medium">{successMessage}</span>
                  </div>
                </div>
              )}

              {/* 🆕 Résultats détaillés */}
              {detailedResults && (
                <div className="space-y-3">
                  <h4 className="font-medium text-gray-900">📋 Détails par email :</h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {detailedResults.results.map((result, index) => (
                      <div key={index} className={`p-3 rounded-lg border ${getStatusColor(result.status)}`}>
                        <div className="flex items-center space-x-2">
                          {getStatusIcon(result.status, result.reason)}
                          <span className="font-medium">{result.email}</span>
                        </div>
                        <p className="text-sm mt-1 opacity-75">{result.message}</p>
                        
                        {/* Détails pour utilisateurs existants */}
                        {result.details && result.reason === 'user_exists' && (
                          <div className="mt-2 p-2 bg-white bg-opacity-50 rounded text-xs">
                            <p>👤 <strong>Inscrit le :</strong> {formatDate(result.details.registered_since)}</p>
                            {result.details.last_login && (
                              <p>🔄 <strong>Dernière connexion :</strong> {formatDate(result.details.last_login)}</p>
                            )}
                          </div>
                        )}

                        {/* Détails pour invitations en double */}
                        {result.details && (result.reason === 'already_invited_by_you' || result.reason === 'already_invited_by_other') && (
                          <div className="mt-2 p-2 bg-white bg-opacity-50 rounded text-xs">
                            <p>📧 <strong>Invité le :</strong> {formatDate(result.details.invited_at)}</p>
                            {result.details.invited_by && (
                              <p>👨‍💼 <strong>Par :</strong> {result.details.invited_by}</p>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Bouton retry pour les ignorés */}
                  {detailedResults.skipped_count > 0 && (
                    <button
                      onClick={handleRetrySkipped}
                      className="w-full px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
                    >
                      🔄 Forcer l'envoi pour les {detailedResults.skipped_count} email{detailedResults.skipped_count > 1 ? 's' : ''} ignoré{detailedResults.skipped_count > 1 ? 's' : ''}
                    </button>
                  )}
                </div>
              )}

              {/* 🆕 Résultats de pré-validation */}
              {showPreValidation && preValidationResults && (
                <div className="space-y-4">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h3 className="font-semibold text-blue-900 mb-2">🔍 Résultats de la pré-validation</h3>
                    <div className="text-sm text-blue-800">
                      <p>📊 {preValidationResults.total_emails} emails analysés</p>
                      <p>✅ {preValidationResults.can_invite} peuvent être invités</p>
                      <p>⏭️ {preValidationResults.cannot_invite} ne peuvent pas être invités</p>
                    </div>
                  </div>

                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {preValidationResults.validations.map((validation: any, index: number) => (
                      <div key={index} className={`p-3 rounded-lg border ${validation.can_invite ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'}`}>
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{validation.email}</span>
                          {validation.can_invite ? (
                            <span className="text-green-600">✅ Peut être invité</span>
                          ) : (
                            <span className="text-yellow-600">⏭️ {validation.reason === 'user_exists' ? 'Déjà inscrit' : 'Déjà invité'}</span>
                          )}
                        </div>
                        {!validation.can_invite && (
                          <p className="text-sm mt-1 opacity-75">{validation.message}</p>
                        )}
                      </div>
                    ))}
                  </div>

                  <div className="flex space-x-3">
                    <button
                      onClick={() => setShowPreValidation(false)}
                      className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                    >
                      Modifier la liste
                    </button>
                    <button
                      onClick={handleSendInvitations}
                      disabled={preValidationResults.can_invite === 0 && !forceSend}
                      className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                    >
                      {forceSend ? 
                        `Forcer l'envoi (${preValidationResults.total_emails})` : 
                        `Envoyer (${preValidationResults.can_invite})`
                      }
                    </button>
                  </div>
                </div>
              )}

              {/* Messages d'erreur */}
              {errors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="text-red-800">
                    <p className="font-medium mb-2 flex items-center">
                      <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                      </svg>
                      Erreur de validation
                    </p>
                    <ul className="list-disc list-inside space-y-1 text-sm">
                      {errors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Formulaire principal (si pas de résultats détaillés affichés) */}
              {!detailedResults && !showPreValidation && (
                <div className="space-y-6">
                  {/* Section Email Addresses */}
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-2">
                      Adresses Email
                      {getEmailCount() > 0 && (
                        <span className="ml-2 text-blue-600 font-normal">
                          ({getEmailCount()} destinataire{getEmailCount() > 1 ? 's' : ''})
                        </span>
                      )}
                    </label>
                    <textarea
                      value={emails}
                      onChange={(e) => setEmails(e.target.value)}
                      placeholder="nom1@exemple.com, nom2@exemple.com, nom3@exemple.com"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                      style={{
                        fontSize: '16px',
                        backgroundColor: 'white',
                        color: '#111827',
                        lineHeight: '1.5'
                      }}
                      rows={3}
                      disabled={isLoading}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      💡 Séparez les adresses par des virgules. Maximum 10 invitations à la fois.
                    </p>
                  </div>

                  {/* Section Message Personnel */}
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-2">
                      Ajouter un message personnel 
                      <span className="text-gray-500 font-normal">(optionnel)</span>
                    </label>
                    <textarea
                      value={personalMessage}
                      onChange={(e) => setPersonalMessage(e.target.value)}
                      placeholder="Expliquez à vos collègues pourquoi vous les invitez à découvrir Intelia Expert..."
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                      style={{
                        fontSize: '16px',
                        backgroundColor: 'white',
                        color: '#111827',
                        lineHeight: '1.5'
                      }}
                      rows={4}
                      maxLength={500}
                      disabled={isLoading}
                    />
                    <div className="flex justify-between items-center mt-1">
                      <p className="text-xs text-gray-500">
                        💬 Votre message sera inclus dans l'email d'invitation
                      </p>
                      <span className="text-xs text-gray-400">
                        {personalMessage.length}/500
                      </span>
                    </div>
                  </div>

                  {/* 🆕 Option force send */}
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="forceSend"
                      checked={forceSend}
                      onChange={(e) => setForceSend(e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <label htmlFor="forceSend" className="text-sm text-gray-700">
                      Forcer l'envoi même pour les utilisateurs existants
                    </label>
                  </div>
                </div>
              )}

              {/* Boutons d'action */}
              <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                <button
                  onClick={onClose}
                  className="px-6 py-2 text-gray-600 hover:text-gray-800 font-medium"
                  disabled={isLoading}
                >
                  {detailedResults ? 'Fermer' : 'Annuler'}
                </button>

                {/* 🆕 Bouton pré-validation */}
                {!detailedResults && !showPreValidation && (
                  <button
                    onClick={handlePreValidation}
                    disabled={isLoading || getEmailCount() === 0}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    🔍 Pré-vérifier
                  </button>
                )}

                {/* Bouton d'envoi */}
                {!detailedResults && (
                  <button
                    onClick={handleSendInvitations}
                    disabled={isLoading || getEmailCount() === 0}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center space-x-2"
                  >
                    {isLoading ? (
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

                {/* Bouton nouvelle invitation après résultats */}
                {detailedResults && (
                  <button
                    onClick={() => {
                      setDetailedResults(null)
                      setEmails('')
                      setPersonalMessage('')
                      setSuccessMessage('')
                      setForceSend(false)
                    }}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    ↩️ Nouvelle invitation
                  </button>
                )}
              </div>

              {/* Footer avec informations */}
              <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-100">
                🔒 Les invitations sont envoyées depuis support@intelia.com avec votre nom comme expéditeur.
                <br />
                Vos contacts recevront un lien pour créer leur compte Intelia Expert gratuitement.
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}