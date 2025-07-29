import React, { useState } from 'react'
import { useTranslation } from '../../hooks/useTranslation'
import { useAuthStore } from '../../hooks/useAuthStore'

interface InviteFriendModalProps {
  onClose: () => void
}

// ==================== SERVICE D'INVITATION ====================
const invitationService = {
  async sendInvitation(emails: string[], personalMessage: string, inviterInfo: any) {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    try {
      console.log('📧 [InvitationService] Envoi invitation:', { emails, hasMessage: !!personalMessage })
      
      const response = await fetch(`${API_BASE_URL}/api/v1/invitations/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('supabase_token')}`
        },
        body: JSON.stringify({
          emails,
          personal_message: personalMessage,
          inviter_name: inviterInfo.name,
          inviter_email: inviterInfo.email,
          language: inviterInfo.language || 'fr'
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Erreur lors de l\'envoi des invitations')
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

// ==================== MODAL INVITATION AMI ====================
export const InviteFriendModal: React.FC<InviteFriendModalProps> = ({ onClose }) => {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const [emails, setEmails] = useState('')
  const [personalMessage, setPersonalMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [successMessage, setSuccessMessage] = useState('')

  // Validation des emails
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
    setErrors([])
    setSuccessMessage('')
    
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
    
    try {
      console.log('🚀 [InviteFriendModal] Début envoi invitations:', valid)
      
      const result = await invitationService.sendInvitation(
        valid, 
        personalMessage.trim(), 
        {
          name: user?.name || 'Utilisateur Intelia',
          email: user?.email || '',
          language: user?.language || 'fr'
        }
      )
      
      setSuccessMessage(
        `✅ ${result.sent_count} invitation${result.sent_count > 1 ? 's' : ''} envoyée${result.sent_count > 1 ? 's' : ''} avec succès !`
      )
      
      // Réinitialiser le formulaire après 2 secondes
      setTimeout(() => {
        setEmails('')
        setPersonalMessage('')
        setSuccessMessage('')
        onClose()
      }, 2000)
      
    } catch (error) {
      console.error('❌ [InviteFriendModal] Erreur envoi:', error)
      setErrors([
        error instanceof Error ? error.message : 'Erreur lors de l\'envoi des invitations',
        'Veuillez réessayer ou contacter le support si le problème persiste.'
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const getEmailCount = () => {
    const { valid } = validateEmails(emails)
    return valid.length
  }

  return (
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
          Partagez l'intelligence artificielle spécialisée en santé animale avec votre équipe
        </p>
      </div>

      {/* Messages de succès */}
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

        {/* Aperçu de l'invitation */}
        {getEmailCount() > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">📧 Aperçu de l'invitation :</h4>
            <div className="text-sm text-blue-800 space-y-1">
              <p><strong>De :</strong> {user?.name || 'Vous'} via support@intelia.com</p>
              <p><strong>À :</strong> {getEmailCount()} destinataire{getEmailCount() > 1 ? 's' : ''}</p>
              <p><strong>Sujet :</strong> {user?.name || 'Votre collègue'} vous invite à découvrir Intelia Expert</p>
              {personalMessage.trim() && (
                <p><strong>Message personnel :</strong> Inclus ✓</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Boutons d'action */}
      <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
        <button
          onClick={onClose}
          className="px-6 py-2 text-gray-600 hover:text-gray-800 font-medium"
          disabled={isLoading}
        >
          Annuler
        </button>
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
      </div>

      {/* Footer avec informations */}
      <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-100">
        🔒 Les invitations sont envoyées depuis support@intelia.com avec votre nom comme expéditeur.
        <br />
        Vos contacts recevront un lien pour créer leur compte Intelia Expert gratuitement.
      </div>
    </div>
  )
}