import React, { useState, useMemo, useEffect, useRef } from 'react'
import { useTranslation } from '@/lib/languages/i18n'
import { useAuthStore } from '@/lib/stores/auth' 
import { getSupabaseClient } from '@/lib/supabase/singleton'

interface InviteFriendModalProps {
  onClose: () => void
}

// Types pour les réponses API
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

// ==================== SERVICE D'INVITATION ====================
const invitationService = {
  async sendInvitation(emails: string[], personalMessage: string, inviterInfo: any) {
    try {
      console.log('📧 [InvitationService] Envoi invitation:', { 
        emails, 
        hasMessage: !!personalMessage,
        inviterEmail: inviterInfo.email 
      })
      
      const supabase = getSupabaseClient()
      const { data, error } = await supabase.auth.getSession()
      
      if (error) {
        console.error('❌ [InvitationService] Erreur session:', error)
        throw new Error('Session expirée - reconnexion nécessaire')
      }
      
      const session = data.session
      if (!session?.access_token) {
        throw new Error('Session expirée - reconnexion nécessaire')
      }

      console.log('✅ [InvitationService] Service initialized')
      
      // URL selon votre configuration
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert.intelia.com/api'
      const cleanBaseUrl = baseUrl.replace(/\/api\/?$/, '')
      const inviteUrl = `${cleanBaseUrl}/api/v1/invitations/send`
      
      console.log('🌐 [InvitationService] URL d\'envoi:', inviteUrl)
      
      const headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json',
        'Authorization': `Bearer ${session.access_token}`
      }
      
      console.log('📦 [InvitationService] Headers préparés:', {
        ...headers,
        Authorization: '[HIDDEN]'
      })
      
      const requestBody = {
        emails,
        personal_message: personalMessage,
        inviter_name: inviterInfo.name,
        inviter_email: inviterInfo.email,
        language: inviterInfo.language || 'fr',
        force_send: false // Toujours false - pas de forçage
      }
      
      console.log('📋 [InvitationService] Corps de la requête:', requestBody)
      
      const response = await fetch(inviteUrl, {		  
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody)
      })

      console.log('📡 [InvitationService] Réponse reçue:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok
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
      console.log('✅ [InvitationService] Invitations traitées:', result)
      return result
      
    } catch (error) {
      console.error('❌ [InvitationService] Erreur envoi:', error)
      throw error
    }
  }
}

// ==================== MODAL INVITATION SIMPLIFIÉE ====================
export const InviteFriendModal: React.FC<InviteFriendModalProps> = ({ onClose }) => {
  const { t } = useTranslation()
  const { user } = useAuthStore() 
  const [emails, setEmails] = useState('')
  const [personalMessage, setPersonalMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [results, setResults] = useState<InvitationResponse | null>(null)
  const overlayRef = useRef<HTMLDivElement>(null)

  // Forcer les styles au montage pour contourner les problèmes CSS
  useEffect(() => {
    const overlay = overlayRef.current
    
    if (overlay) {
      // Forcer les dimensions de l'overlay
      overlay.style.setProperty('width', '100vw', 'important')
      overlay.style.setProperty('height', '100vh', 'important')
      overlay.style.setProperty('top', '0', 'important')
      overlay.style.setProperty('left', '0', 'important')
      overlay.style.setProperty('right', '0', 'important')
      overlay.style.setProperty('bottom', '0', 'important')
      
      // BACKDROP GRISÉ avec flou + centrage flex
      overlay.style.setProperty('background-color', 'rgba(0, 0, 0, 0.5)', 'important')
      overlay.style.setProperty('backdrop-filter', 'blur(2px)', 'important')
      overlay.style.setProperty('animation', 'fadeIn 0.2s ease-out', 'important')
      overlay.style.setProperty('display', 'flex', 'important')
      overlay.style.setProperty('align-items', 'center', 'important')
      overlay.style.setProperty('justify-content', 'center', 'important')
      overlay.style.setProperty('padding', '16px', 'important')
      
      // Forcer les dimensions du contenu
      const content = overlay.querySelector('.bg-white') as HTMLElement
      if (content) {
        content.style.setProperty('width', '95vw', 'important')
        content.style.setProperty('max-width', '700px', 'important')
        content.style.setProperty('max-height', '85vh', 'important')
        content.style.setProperty('min-width', '320px', 'important')
        content.style.setProperty('animation', 'modalSlideIn 0.3s ease-out', 'important')
      }
    }
  }, [])

  // Calcul de currentUser (votre code original conservé)
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
      console.warn(t('invite.authRetrievalError'), e)
    }
    
    return null
  }, [user, t])

  useEffect(() => {
    if (!currentUser?.email) {
      setErrors([t('invite.loginRequired')])
    } else {
      setErrors([])
    }
  }, [currentUser, t])

  // Validation des emails (votre fonction originale conservée)
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

  const handleSendInvitations = async () => {
    console.log('🖱️ [InviteFriendModal] Bouton "Envoyer" cliqué')
    console.log('📊 [InviteFriendModal] État initial:', {
      isLoading,
      emailsLength: emails.length,
      hasCurrentUser: !!currentUser?.email
    })
    
    setErrors([])
    setResults(null)
    
    if (!currentUser?.email) {
      console.log('❌ [InviteFriendModal] Pas d\'utilisateur connecté')
      setErrors([t('invite.loginRequired')])
      return
    }

    if (!emails.trim()) {
      console.log('❌ [InviteFriendModal] Pas d\'emails fournis')
      setErrors([t('invite.emailRequired')])
      return
    }

    const { valid, invalid } = validateEmails(emails)
    console.log('📧 [InviteFriendModal] Validation emails:', { valid, invalid })
    
    if (invalid.length > 0) {
      console.log('❌ [InviteFriendModal] Emails invalides détectés:', invalid)
      setErrors([
        `${t('invite.invalidEmails')}: ${invalid.join(', ')}`,
        t('invite.emailFormat')
      ])
      return
    }

    if (valid.length === 0) {
      console.log('❌ [InviteFriendModal] Aucun email valide')
      setErrors([t('invite.noValidEmails')])
      return
    }

    if (valid.length > 10) {
      console.log('❌ [InviteFriendModal] Trop d\'emails:', valid.length)
      setErrors([t('invite.maxLimit')])
      return
    }

    setIsLoading(true)
    console.log('🔄 [InviteFriendModal] Début du processus d\'envoi')
    
    try {
      console.log('🚀 [InviteFriendModal] Début envoi invitations:', {
        emails: valid,
        userEmail: currentUser.email,
        userName: currentUser.name
      })
      
      const inviterInfo = {
        name: currentUser.name || currentUser.email?.split('@')[0] || 'Utilisateur Intelia',
        email: currentUser.email,
        language: currentUser.language || 'fr'
      }
      
      console.log('👤 [InviteFriendModal] Informations de l\'inviteur:', inviterInfo)
      
      const result = await invitationService.sendInvitation(
        valid, 
        personalMessage.trim(), 
        inviterInfo
      )
      
      console.log('✅ [InviteFriendModal] Résultat reçu:', result)
      
      // Afficher les résultats
      setResults(result)
      
    } catch (error) {
      console.error('❌ [InviteFriendModal] Erreur envoi:', error)
      
      let errorMessage = t('invite.sendError')
      
      if (error instanceof Error) {
        errorMessage = error.message
      }
      
      console.log('🔍 [InviteFriendModal] Analyse de l\'erreur:', errorMessage)
      
      if (errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
        setErrors([
          t('invite.authError'),
          t('invite.reconnectSuggestion')
        ])
      } else if (errorMessage.includes('401') || errorMessage.includes('Unauthorized')) {
        setErrors([
          t('invite.sessionExpired'),
          t('invite.sessionExpiredDetail')
        ])
      } else {
        setErrors([
          errorMessage,
          t('invite.retryOrContact')
        ])
      }
    } finally {
      setIsLoading(false)
      console.log('🏁 [InviteFriendModal] Fin du processus d\'envoi')
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
        return <span className="text-yellow-600">⭐</span>
      case 'failed': return <span className="text-red-600">❌</span>
      default: return <span className="text-gray-600">⚪</span>
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'sent': return 'bg-green-50 border-green-200 text-green-800'
      case 'skipped': return 'bg-blue-50 border-blue-200 text-blue-800'
      case 'failed': return 'bg-red-50 border-red-200 text-red-800'
      default: return 'bg-gray-50 border-gray-200 text-gray-800'
    }
  }

  // ==================== AJOUT: Fonction pour messages simplifiés ====================
  const getFriendlyMessage = (result: InvitationResult) => {
    if (result.status === 'sent') {
      return t('invite.invitationSent', { email: result.email })
    }
    
    if (result.status === 'skipped') {
      if (result.reason === 'user_exists') {
        if (result.details?.registered_since) {
          const registeredDate = new Date(result.details.registered_since).toLocaleDateString('fr-FR')
          return `${t('invite.userExistsWithDate')}: ${result.email} (${registeredDate})`
        }
        return `${t('invite.userExists')}: ${result.email}`
      }
      
      if (result.reason === 'already_invited_by_you') {
        return `${t('invite.alreadyInvitedByYou')}: ${result.email}`
      }
      
      if (result.reason === 'already_invited_by_other') {
        return `${t('invite.alreadyInvitedByOther')}: ${result.email}`
      }
    }
    
    if (result.status === 'failed') {
      if (result.reason?.includes('Invalid email')) {
        return `${t('invite.invalidEmail')}: ${result.email}`
      }
      if (result.reason?.includes('rate limit')) {
        return t('invite.rateLimit')
      }
      return `${t('invite.sendFailed')}: ${result.email}`
    }
    
    return result.message
  }

  // Affichage conditionnel si pas d'utilisateur (votre code original conservé)
  if (!currentUser?.email) {
    return (
      <>
        {/* Styles CSS pour les animations */}
        <style jsx>{`
          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
          
          @keyframes modalSlideIn {
            from { 
              opacity: 0; 
              transform: translateY(-20px) scale(0.95); 
            }
            to { 
              opacity: 1; 
              transform: translateY(0) scale(1); 
            }
          }
        `}</style>

        <div ref={overlayRef} className="fixed inset-0 z-50" onClick={onClose}>
          <div 
            className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" 
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">{t('nav.inviteFriend')}</h2>
              <button 
                onClick={onClose} 
                className="text-gray-400 hover:text-gray-600 text-2xl transition-colors hover:bg-gray-100 rounded-full w-8 h-8 flex items-center justify-center"
                aria-label={t('modal.close')}
                title={t('modal.close')}
              >
                ×
              </button>
            </div>
            <div className="p-6">
              <div className="text-center">
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">{t('invite.loginRequiredTitle')}</h2>
                <p className="text-sm text-gray-600 mb-4">{t('invite.loginRequired')}</p>
                <button 
                  onClick={onClose} 
                  className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                >
                  {t('modal.close')}
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
      {/* Styles CSS pour les animations */}
      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        @keyframes modalSlideIn {
          from { 
            opacity: 0; 
            transform: translateY(-20px) scale(0.95); 
          }
          to { 
            opacity: 1; 
            transform: translateY(0) scale(1); 
          }
        }
      `}</style>

      <div ref={overlayRef} className="fixed inset-0 z-50" onClick={onClose}>
        <div 
          className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" 
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">{t('nav.inviteFriend')}</h2>
            <button 
              onClick={onClose} 
              className="text-gray-400 hover:text-gray-600 text-2xl transition-colors hover:bg-gray-100 rounded-full w-8 h-8 flex items-center justify-center"
              aria-label={t('modal.close')}
              title={t('modal.close')}
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
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  {t('invite.title')}
                </h2>
                <p className="text-sm text-gray-600">
                  {t('invite.subtitle')}
                </p>
              </div>

              {/* ==================== INTERFACE SIMPLIFIÉE POUR LES RÉSULTATS ==================== */}
              {results && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    {t('invite.sendStatus')}
                  </h3>

                  {/* Messages des résultats - Interface simplifiée */}
                  <div className="space-y-3">
                    {results.results.map((result, index) => (
                      <div
                        key={index}
                        className={`p-4 rounded-lg border-l-4 ${
                          result.success && result.status === 'sent'
                            ? 'bg-green-50 border-green-400'
                            : result.status === 'skipped'
                            ? 'bg-blue-50 border-blue-400'
                            : 'bg-red-50 border-red-400'
                        }`}
                      >
                        <div className="flex items-start space-x-3">
                          <span className="text-2xl mt-1">
                            {result.success && result.status === 'sent' ? '✅' : 
                             result.status === 'skipped' ? '👤' : '❌'}
                          </span>
                          <div className="flex-1">
                            <p className="text-sm text-gray-800 font-medium">
                              {getFriendlyMessage(result)}
                            </p>
                            {result.details?.last_login && (
                              <p className="text-xs text-gray-500 mt-1">
                                {t('invite.lastLogin')}: {new Date(result.details.last_login).toLocaleDateString('fr-FR')}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="flex space-x-3 mt-6">
                    <button
                      onClick={() => {
                        setResults(null)
                        setEmails('')
                        setPersonalMessage('')
                      }}
                      className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-200 transition-colors"
                    >
                      {t('invite.inviteOthers')}
                    </button>
                    <button
                      onClick={onClose}
                      className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                    >
                      {t('modal.close')}
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
                      {t('invite.validationError')}
                    </p>
                    <ul className="list-disc list-inside space-y-1 text-sm">
                      {errors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Formulaire principal (si pas de résultats affichés) */}
              {!results && (
                <div className="space-y-6">
                  {/* Section Email Addresses */}
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-2">
                      {t('invite.emailAddresses')}
                      {getEmailCount() > 0 && (
                        <span className="ml-2 text-blue-600 font-normal">
                          {`${t('invite.recipientCount')}: ${getEmailCount()}`})
                        </span>
                      )}
                    </label>
                    <textarea
                      value={emails}
                      onChange={(e) => setEmails(e.target.value)}
                      placeholder={t('invite.emailPlaceholder')}
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
                      {t('invite.emailHelp')}
                    </p>
                  </div>

                  {/* Section Message Personnel */}
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-2">
                      {t('invite.personalMessage')} 
                      <span className="text-gray-500 font-normal">({t('invite.optional')})</span>
                    </label>
                    <textarea
                      value={personalMessage}
                      onChange={(e) => setPersonalMessage(e.target.value)}
                      placeholder={t('invite.messagePlaceholder')}
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
                        {t('invite.messageHelp')}
                      </p>
                      <span className="text-xs text-gray-400">
                        {personalMessage.length}/500
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Boutons d'action */}
              <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                {/* Bouton d'envoi (seulement si pas de résultats) */}
                {!results && (
                  <button
                    onClick={() => {
                      console.log('🖱️ [InviteFriendModal] Bouton "Envoyer" cliqué depuis onClick')
                      handleSendInvitations()
                    }}
                    disabled={isLoading || getEmailCount() === 0}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center space-x-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  >
                    {isLoading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>{t('invite.sending')}</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                        </svg>
                        <span>
                          {t('invite.send')} {getEmailCount() > 0 ? `(${getEmailCount()})` : ''}
                        </span>
                      </>
                    )}
                  </button>
                )}
              </div>

              {/* Footer avec informations */}
              <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-100">
                {t('invite.footerInfo')}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}