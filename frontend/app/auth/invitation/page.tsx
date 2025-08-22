'use client'
// app/auth/invitation/page.tsx - Page d'invitation utilisant UNIQUEMENT le backend

import React, { useEffect, useState, useMemo } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

// ==================== CONFIGURATION DES PAYS AVEC FALLBACK ====================
// Pays de fallback (les plus communs) en cas d'échec de l'API
const fallbackCountries = [
  { value: 'CA', label: 'Canada', phoneCode: '+1', flag: '🇨🇦' },
  { value: 'US', label: 'États-Unis', phoneCode: '+1', flag: '🇺🇸' },
  { value: 'FR', label: 'France', phoneCode: '+33', flag: '🇫🇷' },
  { value: 'GB', label: 'Royaume-Uni', phoneCode: '+44', flag: '🇬🇧' },
  { value: 'DE', label: 'Allemagne', phoneCode: '+49', flag: '🇩🇪' },
  { value: 'IT', label: 'Italie', phoneCode: '+39', flag: '🇮🇹' },
  { value: 'ES', label: 'Espagne', phoneCode: '+34', flag: '🇪🇸' },
  { value: 'BE', label: 'Belgique', phoneCode: '+32', flag: '🇧🇪' },
  { value: 'CH', label: 'Suisse', phoneCode: '+41', flag: '🇨🇭' },
  { value: 'MX', label: 'Mexique', phoneCode: '+52', flag: '🇲🇽' },
  { value: 'BR', label: 'Brésil', phoneCode: '+55', flag: '🇧🇷' },
  { value: 'AU', label: 'Australie', phoneCode: '+61', flag: '🇦🇺' },
  { value: 'JP', label: 'Japon', phoneCode: '+81', flag: '🇯🇵' },
  { value: 'CN', label: 'Chine', phoneCode: '+86', flag: '🇨🇳' },
  { value: 'IN', label: 'Inde', phoneCode: '+91', flag: '🇮🇳' },
  { value: 'NL', label: 'Pays-Bas', phoneCode: '+31', flag: '🇳🇱' },
  { value: 'SE', label: 'Suède', phoneCode: '+46', flag: '🇸🇪' },
  { value: 'NO', label: 'Norvège', phoneCode: '+47', flag: '🇳🇴' },
  { value: 'DK', label: 'Danemark', phoneCode: '+45', flag: '🇩🇰' },
  { value: 'FI', label: 'Finlande', phoneCode: '+358', flag: '🇫🇮' }
]

// Interface pour les pays
interface Country {
  value: string
  label: string
  phoneCode: string
  flag?: string
}

// Hook personnalisé pour charger les pays avec fallback
const useCountries = () => {
  const [countries, setCountries] = useState<Country[]>(fallbackCountries)
  const [loading, setLoading] = useState(true)
  const [usingFallback, setUsingFallback] = useState(false)

  useEffect(() => {
    const fetchCountries = async () => {
      try {
        // ✅ OPTION 1: Essayer l'API REST Countries
        // Note: Nécessite que restcountries.com soit autorisé dans la CSP
        console.log('🌍 [Countries] Tentative de chargement via API REST Countries...')
        
        const response = await fetch('https://restcountries.com/v3.1/all?fields=cca2,name,idd,flag,translations', {
          headers: {
            'Accept': 'application/json',
          }
        })
        
        if (!response.ok) {
          throw new Error(`API Error: ${response.status} ${response.statusText}`)
        }
        
        const data = await response.json()
        console.log('🌍 [Countries] Données reçues:', data.length, 'pays')
        
        const formattedCountries = data
          .map((country: any) => {
            const phoneCode = country.idd?.root + (country.idd?.suffixes?.[0] || '')
            return {
              value: country.cca2,
              label: country.translations?.fra?.common || country.name.common,
              phoneCode: phoneCode,
              flag: country.flag
            }
          })
          .filter((country: Country) => {
            // Filtrer les pays sans code téléphone valide
            const hasValidCode = country.phoneCode && 
                                country.phoneCode !== 'undefined' && 
                                country.phoneCode !== 'null' &&
                                country.phoneCode.length > 1 &&
                                country.phoneCode.startsWith('+')
            return hasValidCode && country.value && country.label
          })
          .sort((a: Country, b: Country) => a.label.localeCompare(b.label))
        
        console.log('🌍 [Countries] Pays formatés:', formattedCountries.length, 'pays valides')
        
        if (formattedCountries.length >= 50) { // Au moins 50 pays pour considérer que l'API fonctionne bien
          setCountries(formattedCountries)
          setUsingFallback(false)
          console.log('✅ [Countries] API REST Countries utilisée avec succès')
        } else {
          console.warn('⚠️ [Countries] Peu de pays reçus, utilisation du fallback')
          throw new Error('Données insuffisantes')
        }
        
      } catch (err) {
        console.warn('⚠️ [Countries] API REST Countries bloquée par CSP, utilisation du fallback:', err)
        console.info('💡 [Countries] Pour utiliser l\'API complète, ajoutez https://restcountries.com à votre CSP')
        setCountries(fallbackCountries)
        setUsingFallback(true)
      } finally {
        setLoading(false)
      }
    }

    // Délai pour éviter les appels trop fréquents
    const timer = setTimeout(fetchCountries, 100)
    return () => clearTimeout(timer)
  }, [])

  return { countries, loading, usingFallback }
}

// ==================== VALIDATION CORRIGÉE ====================
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

// ✅ VALIDATION TÉLÉPHONE CORRIGÉE
const validatePhone = (countryCode: string, areaCode: string, phoneNumber: string): boolean => {
  // Si tous les champs sont vides, c'est valide (optionnel)
  if (!countryCode.trim() && !areaCode.trim() && !phoneNumber.trim()) {
    return true
  }
  
  // Si au moins un champ est rempli, tous doivent être remplis et valides
  if (countryCode.trim() || areaCode.trim() || phoneNumber.trim()) {
    // Vérifier que tous les champs sont remplis
    if (!countryCode.trim() || !areaCode.trim() || !phoneNumber.trim()) {
      return false
    }
    
    // Vérifier le format de chaque champ
    if (!/^\+[1-9]\d{0,3}$/.test(countryCode.trim())) {
      return false
    }
    
    if (!/^\d{3}$/.test(areaCode.trim())) {
      return false
    }
    
    if (!/^\d{7}$/.test(phoneNumber.trim())) {
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

// Interface pour les résultats de traitement
interface ProcessingResult {
  success: boolean
  step: 'validation' | 'completion'
  message: string
  details?: any
}

const ProcessingStatus = ({ result }: { result: ProcessingResult }) => {
  const getIcon = () => {
    if (result.success) {
      return (
        <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
      )
    } else {
      return (
        <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
        </div>
      )
    }
  }

  const getStepText = () => {
    switch (result.step) {
      case 'validation':
        return result.success ? 'Token d\'invitation validé' : 'Erreur de validation du token'
      case 'completion':
        return result.success ? 'Compte créé avec succès' : 'Erreur de création du compte'
      default:
        return 'Traitement en cours'
    }
  }

  return (
    <div className="text-center">
      {getIcon()}
      <h2 className={`text-lg font-semibold mb-4 ${result.success ? 'text-green-900' : 'text-red-900'}`}>
        {getStepText()}
      </h2>
      
      <div className={`text-sm mb-4 ${result.success ? 'text-green-700' : 'text-red-700'}`}>
        {result.message}
      </div>

      {result.success && result.step === 'completion' && (
        <div className="text-sm text-gray-600">
          <p>Redirection vers votre tableau de bord...</p>
          <div className="mt-2">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-green-600 h-2 rounded-full animate-pulse" style={{width: '100%'}}></div>
            </div>
          </div>
        </div>
      )}

      {!result.success && (
        <div className="text-xs text-gray-600">
          Redirection vers la page de connexion...
        </div>
      )}
    </div>
  )
}

// ==================== COMPOSANT PRINCIPAL ====================
function InvitationAcceptPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'set-password' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')
  const [userInfo, setUserInfo] = useState<any>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [hasProcessedToken, setHasProcessedToken] = useState(false)
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null)
  
  // ✅ Hook pour charger les pays
  const { countries, loading: countriesLoading, usingFallback } = useCountries()
  
  // ✅ Créer le mapping des codes téléphoniques dynamiquement
  const countryCodeMap = useMemo(() => {
    return countries.reduce((acc, country) => {
      acc[country.value] = country.phoneCode
      return acc
    }, {} as Record<string, string>)
  }, [countries])
  
  // États pour le formulaire complet
  const [formData, setFormData] = useState({
    // Mot de passe
    password: '',
    confirmPassword: '',
    
    // Informations personnelles
    firstName: '',
    lastName: '',
    linkedinProfile: '',
    
    // Contact
    email: '',
    country: '',
    countryCode: '',
    areaCode: '',
    phoneNumber: '',
    
    // Entreprise
    companyName: '',
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
          console.log('🔧 [InvitationAccept] Invitation détectée dans URL')
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
            setProcessingResult({
              success: false,
              step: 'validation',
              message: errorData.detail || 'Erreur de validation du token',
              details: errorData
            })
            throw new Error(errorData.detail || 'Erreur de validation du token')
          }
          
          const validationResult = await validateResponse.json()
          console.log('✅ [InvitationAccept] Token validé:', validationResult.user_email)
          
          // Marquer la validation comme réussie
          setProcessingResult({
            success: true,
            step: 'validation',
            message: `Token d'invitation validé pour ${validationResult.user_email}`,
            details: validationResult
          })
          
          // ✅ CORRIGÉ: Structure de réponse alignée avec le backend
          setUserInfo({
            email: validationResult.user_email,
            inviterName: validationResult.inviter_name,
            personalMessage: validationResult.invitation_data?.personal_message,
            language: validationResult.invitation_data?.language,
            invitationDate: validationResult.invitation_data?.invitation_date,
            accessToken: accessToken // Stocker pour la finalisation
          })
          
          // Pré-remplir l'email depuis le token
          setFormData(prev => ({ ...prev, email: validationResult.user_email }))
          
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
            setProcessingResult({
              success: false,
              step: 'validation',
              message: 'Aucune invitation trouvée dans cette URL'
            })
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
    setFormData(prev => {
      const newData = { ...prev, [field]: value }
      
      // Auto-remplir l'indicatif pays quand le pays change
      if (field === 'country' && value && countryCodeMap[value]) {
        newData.countryCode = countryCodeMap[value]
      }
      
      return newData
    })
    
    if (errors.length > 0) {
      setErrors([])
    }
  }

// ✅ VALIDATION FORMULAIRE AVEC TÉLÉPHONE OPTIONNEL ET MOT DE PASSE CONFORME
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
    
    // Validation des informations personnelles
    if (!formData.firstName.trim()) {
      validationErrors.push('Le prénom est requis')
    }
    
    if (!formData.lastName.trim()) {
      validationErrors.push('Le nom de famille est requis')
    }
    
    // Validation contact
    if (!formData.email.trim()) {
      validationErrors.push('L\'email est requis')
    }
    
    if (!formData.country) {
      validationErrors.push('Le pays est requis')
    }
    
    // ✅ VALIDATION TÉLÉPHONE CORRIGÉE - Messages d'erreur spécifiques
    if (!validatePhone(formData.countryCode, formData.areaCode, formData.phoneNumber)) {
      const hasAnyPhoneField = formData.countryCode.trim() || formData.areaCode.trim() || formData.phoneNumber.trim()
      
      if (hasAnyPhoneField) {
        const missingFields = []
        if (!formData.countryCode.trim()) missingFields.push('indicatif pays')
        if (!formData.areaCode.trim()) missingFields.push('indicatif régional')
        if (!formData.phoneNumber.trim()) missingFields.push('numéro')
        
        if (missingFields.length > 0) {
          validationErrors.push(`Téléphone incomplet: veuillez remplir ${missingFields.join(', ')} ou laisser tous les champs téléphone vides`)
        } else {
          validationErrors.push('Format de téléphone invalide')
        }
      }
    }
    
    return validationErrors
  }

  const handleFormSubmit = async () => {
    console.log('🔧 [InvitationAccept] Début handleFormSubmit')
    
    const validationErrors = validateForm()
    
    if (validationErrors.length > 0) {
      console.log('❌ [InvitationAccept] Erreurs de validation:', validationErrors)
      setErrors(validationErrors)
      return
    }
    
    console.log('✅ [InvitationAccept] Validation formulaire passée')
    setIsProcessing(true)
    setErrors([])
    
    try {
      console.log('🔧 [InvitationAccept] Finalisation du compte via backend...')
      
      if (!userInfo?.accessToken) {
        throw new Error('Token d\'accès manquant')
      }
      
      console.log('🔍 [InvitationAccept] UserInfo présent:', !!userInfo)
      console.log('🔍 [InvitationAccept] AccessToken présent:', !!userInfo.accessToken)
      
      // ✅ CORRIGÉ: Structure de données alignée avec le backend
      const requestBody = {
        access_token: userInfo.accessToken,
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email,
        linkedinProfile: formData.linkedinProfile || null,
        country: formData.country,
        phone: formData.countryCode && formData.areaCode && formData.phoneNumber 
          ? `${formData.countryCode} ${formData.areaCode}-${formData.phoneNumber}`
          : null,
        companyName: formData.companyName || null,
        companyWebsite: formData.companyWebsite || null,
        companyLinkedin: formData.companyLinkedin || null,
        password: formData.password
      }
      
      console.log('🔧 [InvitationAccept] Données à envoyer:', {
        ...requestBody,
        password: '[HIDDEN]',
        access_token: '[HIDDEN]'
      })
      
      // ✅ CORRIGÉ: Utiliser les variables d'environnement
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL
      console.log('🌐 [InvitationAccept] API_BASE_URL:', API_BASE_URL)
      
      const completeResponse = await fetch(`${API_BASE_URL}/v1/auth/invitations/complete-profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      })
      
      console.log('📡 [InvitationAccept] Réponse reçue:', completeResponse.status, completeResponse.statusText)
      
      if (!completeResponse.ok) {
        const errorData = await completeResponse.json()
        console.error('❌ [InvitationAccept] Erreur de réponse:', errorData)
        setProcessingResult({
          success: false,
          step: 'completion',
          message: errorData.detail || 'Erreur lors de la finalisation du profil',
          details: errorData
        })
        throw new Error(errorData.detail || 'Erreur lors de la finalisation du profil')
      }
      
      const completionResult = await completeResponse.json()
      console.log('✅ [InvitationAccept] Profil finalisé avec succès:', completionResult)
      
      setStatus('success')
      setMessage('Compte créé avec succès !')
      setProcessingResult({
        success: true,
        step: 'completion',
        message: `Bienvenue ${formData.firstName} ! Votre compte Intelia Expert a été créé avec succès.`
      })
      
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
      formData.firstName.trim() &&
      formData.lastName.trim() &&
      formData.email.trim() &&
      formData.country
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

              {/* Affichage du résultat de validation si disponible */}
              {processingResult && processingResult.step === 'validation' && (
                <div className="mt-6">
                  <ProcessingStatus result={processingResult} />
                </div>
              )}
            </div>
          )}

          {/* Formulaire de création de profil complet */}
          {status === 'set-password' && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4 text-center">
                Bienvenue ! Complétez votre profil
              </h2>
              
              {userInfo && (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h3 className="font-medium text-blue-900 mb-2">✅ Invitation validée avec succès</h3>
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

              {/* ✅ STATUT DU CHARGEMENT DES PAYS - Seulement si vraiment en fallback */}
              {usingFallback && !countriesLoading && (
                <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <svg className="w-4 h-4 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    <span className="text-sm text-yellow-800">
                      Liste de pays limitée (service externe temporairement indisponible)
                    </span>
                  </div>
                </div>
              )}
              
              {/* Messages d'erreur */}
              {errors.length > 0 && (
                <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-3">
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800">
                        Veuillez corriger les erreurs suivantes :
                      </h3>
                      <div className="mt-1 text-sm text-red-700">
                        {errors.map((error, index) => (
                          <div key={index} className="flex items-start space-x-2">
                            <span className="text-red-500 font-bold">•</span>
                            <span>{error}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="space-y-6">
                
                {/* Section Informations personnelles */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Informations personnelles</h3>
                  
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Prénom <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.firstName}
                        onChange={(e) => handleInputChange('firstName', e.target.value)}
                        placeholder="Prénom"
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        disabled={isProcessing}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Nom de famille <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.lastName}
                        onChange={(e) => handleInputChange('lastName', e.target.value)}
                        placeholder="Nom de famille"
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        disabled={isProcessing}
                      />
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      Profil LinkedIn personnel (optionnel)
                    </label>
                    <input
                      type="url"
                      value={formData.linkedinProfile}
                      onChange={(e) => handleInputChange('linkedinProfile', e.target.value)}
                      placeholder="https://linkedin.com/in/votre-profil"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>
                </div>

                {/* Section Contact */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Contact</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Email <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="email"
                      required
                      value={formData.email}
                      onChange={(e) => handleInputChange('email', e.target.value)}
                      placeholder="votre@email.com"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm bg-gray-50"
                      disabled={true}
                      readOnly
                    />
                    <p className="mt-1 text-xs text-gray-500">Email provenant de votre invitation</p>
                  </div>

                  {/* ✅ SÉLECTION PAYS AMÉLIORÉE */}
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      Pays <span className="text-red-500">*</span>
                    </label>
                    {countriesLoading ? (
                      <div className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 bg-gray-50">
                        <div className="flex items-center space-x-2">
                          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                          <span className="text-sm text-gray-600">Chargement des pays...</span>
                        </div>
                      </div>
                    ) : (
                      <select
                        required
                        value={formData.country}
                        onChange={(e) => handleInputChange('country', e.target.value)}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        disabled={isProcessing}
                      >
                        <option value="">Sélectionner un pays...</option>
                        {countries.map(country => (
                          <option key={country.value} value={country.value}>
                            {country.flag} {country.label}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Téléphone (optionnel)
                    </label>
                    <p className="text-xs text-gray-500 mb-2">
                      💡 Si vous remplissez le téléphone, tous les champs sont requis. Sinon, laissez tous les champs vides.
                    </p>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Indicatif pays</label>
                        <input
                          type="text"
                          placeholder="+1"
                          value={formData.countryCode}
                          onChange={(e) => handleInputChange('countryCode', e.target.value)}
                          className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          disabled={isProcessing}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Indicatif régional</label>
                        <input
                          type="text"
                          placeholder="514"
                          value={formData.areaCode}
                          onChange={(e) => handleInputChange('areaCode', e.target.value)}
                          className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          disabled={isProcessing}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Numéro de téléphone</label>
                        <input
                          type="text"
                          placeholder="1234567"
                          value={formData.phoneNumber}
                          onChange={(e) => handleInputChange('phoneNumber', e.target.value)}
                          className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          disabled={isProcessing}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Section Entreprise */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Entreprise</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Nom de l'entreprise (optionnel)
                    </label>
                    <input
                      type="text"
                      value={formData.companyName}
                      onChange={(e) => handleInputChange('companyName', e.target.value)}
                      placeholder="Nom de votre entreprise"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isProcessing}
                    />
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      Site web de l'entreprise (optionnel)
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
                      Page LinkedIn de l'entreprise (optionnel)
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
                    
                    {/* ✅ AJOUT: Exigences du mot de passe */}
                    {formData.password && (
                      <div className="mt-3 bg-gray-50 rounded-lg p-3">
                        <h5 className="text-sm font-medium text-gray-900 mb-2">Exigences du mot de passe :</h5>
                        <ul className="text-xs text-gray-600 space-y-1">
                          <li className="flex items-center space-x-2">
                            <span className={formData.password.length >= 8 ? 'text-green-600' : 'text-gray-400'}>
                              {formData.password.length >= 8 ? '✓' : '○'}
                            </span>
                            <span>Au moins 8 caractères</span>
                          </li>
                          <li className="flex items-center space-x-2">
                            <span className={/[A-Z]/.test(formData.password) ? 'text-green-600' : 'text-gray-400'}>
                              {/[A-Z]/.test(formData.password) ? '✓' : '○'}
                            </span>
                            <span>Au moins une majuscule</span>
                          </li>
                          <li className="flex items-center space-x-2">
                            <span className={/[a-z]/.test(formData.password) ? 'text-green-600' : 'text-gray-400'}>
                              {/[a-z]/.test(formData.password) ? '✓' : '○'}
                            </span>
                            <span>Au moins une minuscule</span>
                          </li>
                          <li className="flex items-center space-x-2">
                            <span className={/\d/.test(formData.password) ? 'text-green-600' : 'text-gray-400'}>
                              {/\d/.test(formData.password) ? '✓' : '○'}
                            </span>
                            <span>Au moins un chiffre</span>
                          </li>
                          <li className="flex items-center space-x-2">
                            <span className={/[!@#$%^&*(),.?":{}|<>]/.test(formData.password) ? 'text-green-600' : 'text-gray-400'}>
                              {/[!@#$%^&*(),.?":{}|<>]/.test(formData.password) ? '✓' : '○'}
                            </span>
                            <span>Au moins un caractère spécial</span>
                          </li>
                        </ul>
                      </div>
                    )}
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
                  onClick={() => {
                    console.log('🖱️ [InvitationAccept] Bouton "Créer mon compte" cliqué')
                    console.log('🔍 [InvitationAccept] isProcessing:', isProcessing)
                    console.log('🔍 [InvitationAccept] isFormValid():', isFormValid())
                    handleFormSubmit()
                  }}
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

          {/* Statut Success et Error avec interface améliorée */}
          {(status === 'success' || status === 'error') && processingResult && (
            <ProcessingStatus result={processingResult} />
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