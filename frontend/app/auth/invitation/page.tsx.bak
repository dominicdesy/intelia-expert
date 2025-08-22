'use client'
// app/auth/invitation/page.tsx - Page d'invitation utilisant UNIQUEMENT le backend

import React, { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

// ==================== VALIDATION ====================
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

const validatePhone = (countryCode: string, areaCode: string, phoneNumber: string): boolean => {
  if (!countryCode.trim() && !areaCode.trim() && !phoneNumber.trim()) {
    return true
  }
  
  if (countryCode.trim() || areaCode.trim() || phoneNumber.trim()) {
    if (!countryCode.trim() || !/^\+[1-9]\d{0,3}$/.test(countryCode.trim())) {
      return false
    }
    
    if (!areaCode.trim() || !/^\d{3}$/.test(areaCode.trim())) {
      return false
    }
    
    if (!phoneNumber.trim() || !/^\d{7}$/.test(phoneNumber.trim())) {
      return false
    }
  }
  
  return true
}

// ==================== COMPOSANTS ====================
const InteliaLogo = ({ className = "w-12 h-12" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// ==================== COMPOSANT PRINCIPAL ====================
function InvitationAcceptPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'set-password' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')
  const [userInfo, setUserInfo] = useState<any>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [hasProcessedToken, setHasProcessedToken] = useState(false)
  
  // États pour le formulaire complet
  const [formData, setFormData] = useState({
    // Mot de passe
    password: '',
    confirmPassword: '',
    
    // Informations personnelles (✅ CORRIGÉ: aligné avec le backend)
    fullName: '',
    company: '',
    jobTitle: '',
    
    // Contact
    phone: '',
    
    // Entreprise
    companyWebsite: '',
    companyLinkedin: ''
  })
  
  const [errors, setErrors] = useState<string[]>([])
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        // ✅ CORRECTION: Éviter le double traitement
        if (hasProcessedToken) {
          console.log('🔍 [InvitationAccept] Token déjà traité, ignorer')
          return
        }

        console.log('🔍 [InvitationAccept] Début traitement invitation')
        
        // Vérifier les paramètres d'URL
        const hash = window.location.hash
        const token = searchParams.get('token')
        const type = searchParams.get('type')
        
        console.log('🔍 [InvitationAccept] Hash URL:', hash ? 'présent' : 'absent')
        console.log('🔍 [InvitationAccept] Query token:', token ? 'présent' : 'absent')
        console.log('🔍 [InvitationAccept] Query type:', type)
        console.log('🔍 [InvitationAccept] URL complète:', window.location.href)
        
        // Détecter l'invitation
        const hasInvitationInHash = hash && (hash.includes('access_token') || hash.includes('type=invite'))
        const hasInvitationInQuery = token && type === 'invite'
        
        if (hasInvitationInHash || hasInvitationInQuery) {
          console.log('📧 [InvitationAccept] Invitation détectée dans URL')
          setMessage('Validation de votre invitation...')
          
          // ✅ CORRECTION: Marquer comme traité AVANT le traitement
          setHasProcessedToken(true)
          
          // 🔧 NOUVELLE APPROCHE : Extraire le token et valider via le backend
          let accessToken = ''
          
          if (hasInvitationInHash) {
            // Extraire les tokens du hash
            const urlParams = new URLSearchParams(hash.substring(1))
            accessToken = urlParams.get('access_token') || ''
          } else if (hasInvitationInQuery) {
            accessToken = token || ''
          }
          
          if (!accessToken) {
            throw new Error('Token d\'accès manquant dans l\'URL')
          }
          
          console.log('🔍 [InvitationAccept] Token extrait, validation via backend...')
          
          // ✅ CORRIGÉ: Utiliser les variables d'environnement
          const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL
          const validateResponse = await fetch(`${API_BASE_URL}/v1/auth/invitations/validate-token`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              access_token: accessToken
            })
          })
          
          if (!validateResponse.ok) {
            const errorData = await validateResponse.json()
            throw new Error(errorData.detail || 'Erreur de validation du token')
          }
          
          const validationResult = await validateResponse.json()
          console.log('✅ [InvitationAccept] Token validé:', validationResult.user_email)
          
          // ✅ CORRIGÉ: Structure de réponse alignée avec le backend
          setUserInfo({
            email: validationResult.user_email,
            inviterName: validationResult.inviter_name,
            personalMessage: validationResult.invitation_data?.personal_message,
            language: validationResult.invitation_data?.language,
            invitationDate: validationResult.invitation_data?.invitation_date,
            accessToken: accessToken // Stocker pour la finalisation
          })
          
          console.log('🔧 [InvitationAccept] Passage au mode set-password')
          setStatus('set-password')
          setMessage('Complétez votre profil')
          
          // ✅ CORRECTION: Nettoyer l'URL APRÈS avoir défini le statut
          setTimeout(() => {
            window.history.replaceState({}, document.title, window.location.pathname)
          }, 100)
          
        } else {
          // ✅ CORRECTION: Ne rediriger que si on n'a pas déjà traité un token
          if (!hasProcessedToken) {
            console.log('🔍 [InvitationAccept] Pas d\'invitation trouvée')
            setStatus('error')
            setMessage('Aucune invitation trouvée dans cette URL')
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
        
        setTimeout(() => {
          router.push('/auth/login?error=' + encodeURIComponent(
            error instanceof Error ? error.message : 'Erreur d\'invitation'
          ))
        }, 4000)
      }
    }

    // Démarrer le traitement après un délai court
    const timer = setTimeout(handleAuthCallback, 500)
    return () => clearTimeout(timer)
  }, [router, searchParams, hasProcessedToken])

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    if (errors.length > 0) {
      setErrors([])
    }
  }

  const validateForm = (): string[] => {
    const validationErrors: string[] = []
    
    // Validation mot de passe
    if (!formData.password) {
      validationErrors.push('Le mot de passe est requis')
    } else {
      const passwordErrors = validatePassword(formData.password)
      validationErrors.push(...passwordErrors)
    }
    
    if (!formData.confirmPassword) {
      validationErrors.push('La confirmation du mot de passe est requise')
    }
    
    if (formData.password !== formData.confirmPassword) {
      validationErrors.push('Les mots de passe ne correspondent pas')
    }
    
    // ✅ CORRIGÉ: Validation alignée avec les champs backend
    if (!formData.fullName.trim()) {
      validationErrors.push('Le nom complet est requis')
    }
    
    if (!formData.company.trim()) {
      validationErrors.push('L\'entreprise est requise')
    }
    
    if (!formData.jobTitle.trim()) {
      validationErrors.push('Le titre du poste est requis')
    }
    
    return validationErrors
  }

  const handleFormSubmit = async () => {
    const validationErrors = validateForm()
    
    if (validationErrors.length > 0) {
      setErrors(validationErrors)
      return
    }
    
    setIsProcessing(true)
    setErrors([])
    
    try {
      console.log('🔧 [InvitationAccept] Finalisation du compte via backend...')
      
      if (!userInfo?.accessToken) {
        throw new Error('Token d\'accès manquant')
      }
      
      // ✅ CORRIGÉ: Structure de données alignée avec le backend
      const requestBody = {
        access_token: userInfo.accessToken,
        fullName: formData.fullName,
        company: formData.company,
        jobTitle: formData.jobTitle,
        phone: formData.phone || null,
        companyWebsite: formData.companyWebsite || null,
        companyLinkedin: formData.companyLinkedin || null,
        password: formData.password
      }
      
      console.log('🔧 [InvitationAccept] Envoi des données:', {
        ...requestBody,
        password: '[HIDDEN]',
        access_token: '[HIDDEN]'
      })
      
      // ✅ CORRIGÉ: Utiliser les variables d'environnement
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL
      const completeResponse = await fetch(`${API_BASE_URL}/v1/auth/invitations/complete-profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      })
      
      if (!completeResponse.ok) {
        const errorData = await completeResponse.json()
        throw new Error(errorData.detail || 'Erreur lors de la finalisation du profil')
      }
      
      const completionResult = await completeResponse.json()
      console.log('✅ [InvitationAccept] Profil finalisé avec succès')
      
      setStatus('success')
      setMessage('Compte créé avec succès !')
      
      // Redirection vers le chat après 2 secondes
      setTimeout(() => {
        console.log('🚀 [InvitationAccept] Redirection vers chat')
        router.push(completionResult.redirect_url || '/chat')
      }, 2000)
      
    } catch (error: any) {
      console.error('❌ [InvitationAccept] Erreur finalisation compte:', error)
      setErrors([error.message || 'Erreur lors de la finalisation du compte'])
    } finally {
      setIsProcessing(false)
    }
  }

  const isFormValid = () => {
    return (
      formData.password &&
      formData.confirmPassword &&
      formData.password === formData.confirmPassword &&
      validatePassword(formData.password).length === 0 &&
      formData.fullName.trim() &&
      formData.company.trim() &&
      formData.jobTitle.trim()
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
          {status === 'set-password' ? 'Complétez votre profil' : 'Finalisation de votre invitation'}
        </p>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-2xl">
        <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
          
          {/* Statut Loading */}
          {status === 'loading' && (
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Traitement en cours...
              </h2>
              <p className="text-sm text-gray-600">
                {message || 'Validation de votre invitation...'}
              </p>
              
              <div className="mt-4 text-xs text-gray-400">
                <p>🔄 Validation via le backend...</p>
                <p>⏳ Cela peut prendre quelques secondes</p>
              </div>
            </div>
          )}

          {/* Formulaire de création de profil complet */}
          {status === 'set-password' && (
            <div className="max-h-screen overflow-y-auto">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 text-center">
                Bienvenue ! Complétez votre profil
              </h2>
              
              {userInfo && (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h3 className="font-medium text-blue-900 mb-2">Informations de votre invitation</h3>
                  <div className="text-sm text-blue-800 space-y-1">
                    <p><strong>Email :</strong> {userInfo.email}</p>
                    {userInfo.inviterName && (
                      <p><strong>Invité par :</strong> {userInfo.inviterName}</p>
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
                
                {/* Section Informations personnelles - ✅ CORRIGÉ */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Informations personnelles</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Nom complet <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.fullName}
                      onChange={(e) => handleInputChange('fullName', e.target.value)}
                      placeholder="Prénom Nom"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      Entreprise <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.company}
                      onChange={(e) => handleInputChange('company', e.target.value)}
                      placeholder="Nom de votre entreprise"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      Titre du poste <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.jobTitle}
                      onChange={(e) => handleInputChange('jobTitle', e.target.value)}
                      placeholder="Votre titre ou fonction"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>
                </div>

                {/* Section Contact - ✅ SIMPLIFIÉ */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Contact</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Numéro de téléphone (optionnel)
                    </label>
                    <input
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => handleInputChange('phone', e.target.value)}
                      placeholder="+1 514 123-4567"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>
                </div>

                {/* Section Entreprise - ✅ CORRIGÉ */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Entreprise (optionnel)</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Site web de l'entreprise
                    </label>
                    <input
                      type="url"
                      value={formData.companyWebsite}
                      onChange={(e) => handleInputChange('companyWebsite', e.target.value)}
                      placeholder="https://votre-entreprise.com"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      Page LinkedIn de l'entreprise
                    </label>
                    <input
                      type="url"
                      value={formData.companyLinkedin}
                      onChange={(e) => handleInputChange('companyLinkedin', e.target.value)}
                      placeholder="https://linkedin.com/company/votre-entreprise"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>
                </div>

                {/* Section Mot de passe */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Sécurité</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Mot de passe <span className="text-red-500">*</span>
                    </label>
                    <div className="mt-1 relative">
                      <input
                        type={showPassword ? "text" : "password"}
                        required
                        value={formData.password}
                        onChange={(e) => handleInputChange('password', e.target.value)}
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        disabled={isProcessing}
                      />
                      <button
                        type="button"
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                        onClick={() => setShowPassword(!showPassword)}
                        disabled={isProcessing}
                      >
                        {showPassword ? (
                          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                          </svg>
                        ) : (
                          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      Confirmer le mot de passe <span className="text-red-500">*</span>
                    </label>
                    <div className="mt-1 relative">
                      <input
                        type={showConfirmPassword ? "text" : "password"}
                        required
                        value={formData.confirmPassword}
                        onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        disabled={isProcessing}
                      />
                      <button
                        type="button"
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        disabled={isProcessing}
                      >
                        {showConfirmPassword ? (
                          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                          </svg>
                        ) : (
                          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Indicateur de correspondance des mots de passe */}
                  {formData.password && formData.confirmPassword && (
                    <div className="mt-2 text-xs">
                      {formData.confirmPassword === formData.password ? (
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
                </div>

                <button
                  type="button"
                  onClick={handleFormSubmit}
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