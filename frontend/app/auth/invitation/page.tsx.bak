'use client'
// app/auth/invitation/page.tsx - Page pour gérer les invitations avec définition de mot de passe

import React, { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { getSupabaseClient } from '@/lib/supabase/singleton'

// ==================== VALIDATION MOT DE PASSE ====================
const validatePassword = (password: string): string[] => {
  const errors: string[] = []
  
  if (password.length < 8) {
    errors.push('Le mot de passe doit contenir au moins 8 caractères')
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('Le mot de passe doit contenir au moins une majuscule')
  }
  if (!/[a-z]/.test(password)) {
    errors.push('Le mot de passe doit contenir au moins une minuscule')
  }
  if (!/\d/.test(password)) {
    errors.push('Le mot de passe doit contenir au moins un chiffre')
  }
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push('Le mot de passe doit contenir au moins un caractère spécial')
  }
  
  return errors
}

// ==================== LOGO INTELIA ====================
const InteliaLogo = ({ className = "w-12 h-12" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// ==================== ICONES ====================
const EyeIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
  </svg>
)

const EyeSlashIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.34 6.34m6.822 10.565l-3.536-3.536" />
  </svg>
)

// ==================== COMPOSANT CHAMP MOT DE PASSE ====================
interface PasswordFieldProps {
  value: string
  onChange: (value: string) => void
  placeholder: string
  label: string
  disabled?: boolean
  showStrength?: boolean
  showRequirements?: boolean
  confirmValue?: string
  isConfirmField?: boolean
}

const PasswordField: React.FC<PasswordFieldProps> = ({
  value,
  onChange,
  placeholder,
  label,
  disabled = false,
  showStrength = false,
  showRequirements = false,
  confirmValue,
  isConfirmField = false
}) => {
  const [showPassword, setShowPassword] = useState(false)
  
  const passwordErrors = validatePassword(value)
  const strength = value ? 5 - passwordErrors.length : 0
  
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </label>
      <div className="relative">
        <input
          type={showPassword ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 pr-10 transition-colors"
          placeholder={placeholder}
          disabled={disabled}
          autoComplete={isConfirmField ? "new-password" : "new-password"}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute inset-y-0 right-0 pr-3 flex items-center hover:text-gray-600 transition-colors"
          disabled={disabled}
        >
          {showPassword ? (
            <EyeSlashIcon className="h-5 w-5 text-gray-400" />
          ) : (
            <EyeIcon className="h-5 w-5 text-gray-400" />
          )}
        </button>
      </div>
      
      {/* Indicateur de force du mot de passe */}
      {showStrength && value && (
        <div className="mt-2">
          <div className="text-xs text-gray-600 mb-1">Force du mot de passe :</div>
          <div className="flex space-x-1">
            {[1, 2, 3, 4, 5].map((level) => (
              <div
                key={level}
                className={`h-1 flex-1 rounded ${
                  level <= strength
                    ? strength <= 1
                      ? 'bg-red-500'
                      : strength <= 2
                      ? 'bg-orange-500'
                      : strength <= 3
                      ? 'bg-yellow-500'
                      : strength <= 4
                      ? 'bg-blue-500'
                      : 'bg-green-500'
                    : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
          <div className="text-xs mt-1 text-gray-600">
            {strength <= 1 && 'Très faible'}
            {strength === 2 && 'Faible'}
            {strength === 3 && 'Moyen'}
            {strength === 4 && 'Fort'}
            {strength === 5 && 'Très fort'}
          </div>
        </div>
      )}
      
      {/* Indicateur de correspondance pour confirmation */}
      {isConfirmField && value && confirmValue && (
        <div className="mt-1 text-xs">
          {confirmValue === value ? (
            <span className="text-green-600 flex items-center">
              <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Les mots de passe correspondent
            </span>
          ) : (
            <span className="text-red-600 flex items-center">
              <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Les mots de passe ne correspondent pas
            </span>
          )}
        </div>
      )}
      
      {/* Exigences du mot de passe */}
      {showRequirements && (
        <div className="mt-3 bg-gray-50 rounded-lg p-3">
          <h5 className="text-sm font-medium text-gray-900 mb-2">Exigences du mot de passe :</h5>
          <ul className="text-xs text-gray-600 space-y-1">
            <li className="flex items-center space-x-2">
              <span className={value.length >= 8 ? 'text-green-600' : 'text-gray-400'}>
                {value.length >= 8 ? '✓' : '○'}
              </span>
              <span>Au moins 8 caractères</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className={/[A-Z]/.test(value) ? 'text-green-600' : 'text-gray-400'}>
                {/[A-Z]/.test(value) ? '✓' : '○'}
              </span>
              <span>Au moins une majuscule</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className={/[a-z]/.test(value) ? 'text-green-600' : 'text-gray-400'}>
                {/[a-z]/.test(value) ? '✓' : '○'}
              </span>
              <span>Au moins une minuscule</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className={/\d/.test(value) ? 'text-green-600' : 'text-gray-400'}>
                {/\d/.test(value) ? '✓' : '○'}
              </span>
              <span>Au moins un chiffre</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className={/[!@#$%^&*(),.?":{}|<>]/.test(value) ? 'text-green-600' : 'text-gray-400'}>
                {/[!@#$%^&*(),.?":{}|<>]/.test(value) ? '✓' : '○'}
              </span>
              <span>Au moins un caractère spécial</span>
            </li>
          </ul>
        </div>
      )}
    </div>
  )
}

// ==================== COMPOSANT PRINCIPAL CORRIGÉ ====================
function InvitationAcceptPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'set-password' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')
  const [userInfo, setUserInfo] = useState<any>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  
  // États pour le formulaire de mot de passe
  const [formData, setFormData] = useState({
    password: '',
    confirmPassword: ''
  })
  const [errors, setErrors] = useState<string[]>([])

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        console.log('🔍 [InvitationAccept] Début traitement invitation')
        
        const supabase = getSupabaseClient()
        
        // 🔧 CORRECTION MAJEURE : Vérifier AUSSI les query parameters
        const hash = window.location.hash
        const token = searchParams.get('token')
        const type = searchParams.get('type')
        
        console.log('🔍 [InvitationAccept] Hash URL:', hash ? 'présent' : 'absent')
        console.log('🔍 [InvitationAccept] Query token:', token ? 'présent' : 'absent')
        console.log('🔍 [InvitationAccept] Query type:', type)
        console.log('🔍 [InvitationAccept] URL complète:', window.location.href)
        
        // Détecter l'invitation dans hash OU query parameters
        const hasInvitationInHash = hash && (hash.includes('access_token') || hash.includes('type=invite'))
        const hasInvitationInQuery = token && type === 'invite'
        
        if (hasInvitationInHash || hasInvitationInQuery) {
          console.log('📧 [InvitationAccept] Invitation détectée dans URL')
          setMessage('Validation de votre invitation...')
          
          // 🔧 CORRECTION : Laisser plus de temps à Supabase pour traiter
          await new Promise(resolve => setTimeout(resolve, 2000))
          
          // Supabase va automatiquement traiter les tokens
          const { data: sessionData, error: sessionError } = await supabase.auth.getSession()
          
          console.log('📊 [InvitationAccept] Session data:', sessionData)
          console.log('📊 [InvitationAccept] Session error:', sessionError)
          
          if (sessionError) {
            console.error('❌ [InvitationAccept] Erreur session:', sessionError)
            throw new Error(`Erreur d'authentification: ${sessionError.message}`)
          }
          
          if (sessionData.session) {
            console.log('✅ [InvitationAccept] Session créée:', sessionData.session.user.email)
            
            // Extraire les métadonnées d'invitation
            const userMetadata = sessionData.session.user.user_metadata
            console.log('📋 [InvitationAccept] Métadonnées utilisateur:', userMetadata)
            
            const user = sessionData.session.user
            setUserInfo({
              email: user.email,
              invitedBy: userMetadata?.inviter_name || userMetadata?.invited_by,
              invitationDate: userMetadata?.invitation_date,
              personalMessage: userMetadata?.personal_message,
              language: userMetadata?.language || 'fr'
            })
            
            // Vérifier si l'utilisateur a déjà un mot de passe
            console.log('🔐 [InvitationAccept] Utilisateur créé récemment, demande de mot de passe')
            setStatus('set-password')
            setMessage('Définissez votre mot de passe')
            
            // Nettoyer l'URL
            window.history.replaceState({}, document.title, window.location.pathname)
            
          } else {
            // 🔧 CORRECTION : Réessayer avec un délai plus long
            console.log('⏳ [InvitationAccept] Pas de session immédiate, attente supplémentaire...')
            setMessage('Finalisation de votre invitation...')
            
            await new Promise(resolve => setTimeout(resolve, 3000))
            
            const { data: retrySessionData } = await supabase.auth.getSession()
            
            if (retrySessionData.session) {
              console.log('✅ [InvitationAccept] Session créée après retry')
              const user = retrySessionData.session.user
              const userMetadata = user.user_metadata
              
              setUserInfo({
                email: user.email,
                invitedBy: userMetadata?.inviter_name || userMetadata?.invited_by,
                invitationDate: userMetadata?.invitation_date,
                personalMessage: userMetadata?.personal_message,
                language: userMetadata?.language || 'fr'
              })
              
              setStatus('set-password')
              setMessage('Définissez votre mot de passe')
              window.history.replaceState({}, document.title, window.location.pathname)
            } else {
              throw new Error('Aucune session créée après traitement de l\'invitation')
            }
          }
          
        } else {
          // Pas de fragments d'auth, vérifier s'il y a une session existante
          console.log('🔍 [InvitationAccept] Pas d\'invitation, vérification session existante')
          
          const { data: existingSession } = await supabase.auth.getSession()
          
          if (existingSession.session) {
            console.log('✅ [InvitationAccept] Session existante trouvée')
            setStatus('success')
            setMessage('Vous êtes déjà connecté !')
            setTimeout(() => router.push('/chat'), 1500)
          } else {
            console.log('ℹ️ [InvitationAccept] Aucune session, redirection vers login')
            setStatus('error')
            setMessage('Aucune invitation trouvée')
            setTimeout(() => router.push('/auth/login'), 2000)
          }
        }
        
      } catch (error) {
        console.error('❌ [InvitationAccept] Erreur traitement:', error)
        setStatus('error')
        
        if (error instanceof Error) {
          setMessage(error.message)
        } else {
          setMessage('Erreur lors du traitement de votre invitation')
        }
        
        // Redirection vers login après erreur
        setTimeout(() => {
          router.push('/auth/login?error=' + encodeURIComponent(
            error instanceof Error ? error.message : 'Erreur d\'invitation'
          ))
        }, 4000)
      }
    }

    // 🔧 CORRECTION : Délai réduit mais traitement plus robuste
    const timer = setTimeout(handleAuthCallback, 1000)
    return () => clearTimeout(timer)
  }, [router, searchParams])

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    if (errors.length > 0) {
      setErrors([])
    }
  }

  const handlePasswordSubmit = async () => {
    const validationErrors: string[] = []
    
    // Validations
    if (!formData.password) {
      validationErrors.push('Le mot de passe est requis')
    }
    if (!formData.confirmPassword) {
      validationErrors.push('La confirmation du mot de passe est requise')
    }
    if (formData.password !== formData.confirmPassword) {
      validationErrors.push('Les mots de passe ne correspondent pas')
    }
    
    // Validation de la force du mot de passe
    const passwordValidationErrors = validatePassword(formData.password)
    validationErrors.push(...passwordValidationErrors)
    
    if (validationErrors.length > 0) {
      setErrors(validationErrors)
      return
    }
    
    setIsProcessing(true)
    setErrors([])
    
    try {
      console.log('🔐 [InvitationAccept] Définition du mot de passe...')
      
      const supabase = getSupabaseClient()
      
      // Mettre à jour le mot de passe de l'utilisateur
      const { data, error } = await supabase.auth.updateUser({
        password: formData.password
      })
      
      if (error) {
        throw error
      }
      
      console.log('✅ [InvitationAccept] Mot de passe défini avec succès')
      setStatus('success')
      setMessage('Compte créé avec succès !')
      
      // Redirection vers le chat après 2 secondes
      setTimeout(() => {
        console.log('🚀 [InvitationAccept] Redirection vers chat')
        router.push('/chat')
      }, 2000)
      
    } catch (error: any) {
      console.error('❌ [InvitationAccept] Erreur définition mot de passe:', error)
      setErrors([error.message || 'Erreur lors de la définition du mot de passe'])
    } finally {
      setIsProcessing(false)
    }
  }

  const isFormValid = () => {
    return (
      formData.password &&
      formData.confirmPassword &&
      formData.password === formData.confirmPassword &&
      validatePassword(formData.password).length === 0
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Logo Intelia */}
        <div className="flex justify-center mb-8">
          <InteliaLogo className="w-16 h-16" />
        </div>
        
        <h1 className="text-center text-3xl font-bold text-gray-900 mb-2">
          Intelia Expert
        </h1>
        <p className="text-center text-sm text-gray-600 mb-8">
          {status === 'set-password' ? 'Définissez votre mot de passe' : 'Finalisation de votre invitation'}
        </p>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
          
          {/* Statut Loading */}
          {status === 'loading' && (
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Traitement en cours...
              </h2>
              <p className="text-sm text-gray-600">
                {message || 'Finalisation de votre invitation'}
              </p>
              
              {/* 🆕 Indicateur de debug */}
              <div className="mt-4 text-xs text-gray-400">
                <p>🔄 Vérification des tokens d'invitation...</p>
                <p>⏳ Cela peut prendre quelques secondes</p>
              </div>
            </div>
          )}

          {/* Formulaire de définition du mot de passe */}
          {status === 'set-password' && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4 text-center">
                Bienvenue ! Définissez votre mot de passe
              </h2>
              
              {userInfo && (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h3 className="font-medium text-blue-900 mb-2">Informations de votre invitation</h3>
                  <div className="text-sm text-blue-800 space-y-1">
                    <p><strong>Email :</strong> {userInfo.email}</p>
                    {userInfo.invitedBy && (
                      <p><strong>Invité par :</strong> {userInfo.invitedBy}</p>
                    )}
                    {userInfo.personalMessage && (
                      <div className="mt-2 p-2 bg-white rounded border">
                        <p className="text-xs text-gray-600 mb-1">Message personnel :</p>
                        <p className="text-sm italic">"{userInfo.personalMessage}"</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Messages d'erreur */}
              {errors.length > 0 && (
                <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-3">
                  <div className="text-sm text-red-800">
                    {errors.map((error, index) => (
                      <div key={index} className="flex items-start space-x-2">
                        <span className="text-red-500 font-bold">•</span>
                        <span>{error}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="space-y-6">
                {/* Nouveau mot de passe */}
                <PasswordField
                  value={formData.password}
                  onChange={(value) => handleInputChange('password', value)}
                  label="Votre mot de passe"
                  placeholder="Créez un mot de passe sécurisé"
                  showStrength={true}
                  showRequirements={true}
                  disabled={isProcessing}
                />

                {/* Confirmation */}
                <PasswordField
                  value={formData.confirmPassword}
                  onChange={(value) => handleInputChange('confirmPassword', value)}
                  label="Confirmer le mot de passe"
                  placeholder="Retapez votre mot de passe"
                  confirmValue={formData.password}
                  isConfirmField={true}
                  disabled={isProcessing}
                />

                <button
                  type="button"
                  onClick={handlePasswordSubmit}
                  disabled={isProcessing || !isFormValid()}
                  className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isProcessing ? (
                    <div className="flex items-center justify-center space-x-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Création du compte...</span>
                    </div>
                  ) : (
                    'Créer mon compte'
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Statut Success */}
          {status === 'success' && (
            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              
              <h2 className="text-lg font-semibold text-green-900 mb-4">
                {message}
              </h2>
              
              <div className="text-sm text-gray-600">
                <p>Redirection vers votre tableau de bord...</p>
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-green-600 h-2 rounded-full animate-pulse" style={{width: '100%'}}></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Statut Error */}
          {status === 'error' && (
            <div className="text-center">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
              </div>
              
              <h2 className="text-lg font-semibold text-red-900 mb-2">
                Erreur de traitement
              </h2>
              <p className="text-sm text-red-700 mb-4">
                {message}
              </p>
              
              <div className="text-xs text-gray-600">
                Redirection vers la page de connexion...
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="mt-8 pt-4 border-t border-gray-200">
            <p className="text-xs text-gray-500 text-center">
              Besoin d'aide ? Contactez-nous à support@intelia.com
            </p>
          </div>
          
        </div>
      </div>
    </div>
  )
}

// ==================== EXPORT AVEC SUSPENSE ====================
export default function InvitationAcceptPage() {
  return (
    <React.Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement de l'invitation...</p>
        </div>
      </div>
    }>
      <InvitationAcceptPageContent />
    </React.Suspense>
  )
}