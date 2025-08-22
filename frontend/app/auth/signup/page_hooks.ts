// page_hooks.ts - Hooks et utilitaires pour la page d'authentification
'use client'

import { useState, useEffect, useMemo } from 'react'
import type { Language } from '@/types'

// ==================== GESTION DES PAYS AVEC FALLBACK ====================
export const fallbackCountries = [
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
export interface Country {
  value: string
  label: string
  phoneCode: string
  flag?: string
}

// Hook personnalisé pour charger les pays avec fallback amélioré
export const useCountries = () => {
  const [countries, setCountries] = useState<Country[]>(fallbackCountries)
  const [loading, setLoading] = useState(true)
  const [usingFallback, setUsingFallback] = useState(true)

  useEffect(() => {
    const fetchCountries = async () => {
      try {
        console.log('🌍 [Countries] Tentative de chargement depuis l\'API REST Countries...')
        
        // Timeout pour éviter les appels trop longs
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 secondes max
        
        const response = await fetch('https://restcountries.com/v3.1/all?fields=cca2,name,idd,flag,translations', {
          headers: {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (compatible; Intelia/1.0)'
          },
          signal: controller.signal
        })
        
        clearTimeout(timeoutId)
        
        if (!response.ok) {
          throw new Error(`API indisponible: ${response.status}`)
        }
        
        const data = await response.json()
        console.log(`📊 [Countries] Données reçues: ${data.length} pays bruts`)
        
        // Vérification que data est bien un array
        if (!Array.isArray(data)) {
          throw new Error('Format de données invalide')
        }
        
        const formattedCountries = data
          .map((country: any) => {
            // Construction du code téléphonique plus robuste
            let phoneCode = ''
            if (country.idd?.root) {
              phoneCode = country.idd.root
              if (country.idd.suffixes && country.idd.suffixes[0]) {
                phoneCode += country.idd.suffixes[0]
              }
            }
            
            return {
              value: country.cca2,
              label: country.translations?.fra?.common || country.name?.common || country.cca2,
              phoneCode: phoneCode,
              flag: country.flag || ''
            }
          })
          .filter((country: Country) => {
            // ✅ VALIDATION ROBUSTE améliorée
            const hasValidCode = country.phoneCode && 
                                country.phoneCode !== 'undefined' && 
                                country.phoneCode !== 'null' &&
                                country.phoneCode.length > 1 &&
                                country.phoneCode.startsWith('+') &&
                                /^\+\d+$/.test(country.phoneCode) // Vérifie que c'est bien +suivi de chiffres
            
            const hasValidInfo = country.value && 
                                country.value.length === 2 && // Code pays ISO valide
                                country.label && 
                                country.label.length > 1
            
            return hasValidCode && hasValidInfo
          })
          .sort((a: Country, b: Country) => a.label.localeCompare(b.label, 'fr', { numeric: true }))
        
        console.log(`✅ [Countries] Pays valides après filtrage: ${formattedCountries.length}`)
        console.log('📋 [Countries] Échantillon:', formattedCountries.slice(0, 3))
        
        // ✅ SEUIL DE QUALITÉ : Au moins 50 pays pour considérer l'API comme valide
        if (formattedCountries.length >= 50) {
          console.log('🌍 [Countries] API validée, utilisation des données')
          setCountries(formattedCountries)
          setUsingFallback(false)
        } else {
          throw new Error(`Pas assez de pays valides: ${formattedCountries.length}/50 minimum`)
        }
        
      } catch (err: any) {
        console.warn('⚠️ [Countries] Échec API, utilisation de la liste de fallback:', err.message)
        
        // Si c'est une erreur d'abort (timeout), on le mentionne spécifiquement
        if (err.name === 'AbortError') {
          console.warn('⏱️ [Countries] Timeout de l\'API (10s)')
        }
        
        setCountries(fallbackCountries)
        setUsingFallback(true)
      } finally {
        setLoading(false)
      }
    }

    // Petit délai pour éviter les appels trop rapides
    const timer = setTimeout(fetchCountries, 100)
    return () => clearTimeout(timer)
  }, [])

  return { countries, loading, usingFallback }
}

// Hook pour créer le mapping des codes téléphoniques
export const useCountryCodeMap = (countries: Country[]) => {
  return useMemo(() => {
    return countries.reduce((acc, country) => {
      acc[country.value] = country.phoneCode
      return acc
    }, {} as Record<string, string>)
  }, [countries])
}

// Traductions
export const translations = {
  fr: {
    title: 'Intelia Expert',
    email: 'Email',
    password: 'Mot de passe',
    confirmPassword: 'Confirmer le mot de passe',
    login: 'Se connecter',
    signup: 'Créer un compte',
    rememberMe: 'Se souvenir de mon email',
    forgotPassword: 'Mot de passe oublié ?',
    newToIntelia: 'Nouveau sur Intelia ?',
    connecting: 'Connexion en cours...',
    creating: 'Création en cours...',
    loginError: 'Erreur de connexion',
    signupError: 'Erreur de création',
    emailRequired: 'L\'adresse email est requise',
    emailInvalid: 'Veuillez entrer une adresse email valide',
    passwordRequired: 'Le mot de passe est requis',
    passwordTooShort: 'Le mot de passe doit contenir au moins 8 caractères, une majuscule, une minuscule, un chiffre et un caractère spécial',
    passwordMismatch: 'Les mots de passe ne correspondent pas',
    firstNameRequired: 'Le prénom est requis',
    lastNameRequired: 'Le nom de famille est requis',
    countryRequired: 'Le pays est requis',
    phoneInvalid: 'Format de téléphone invalide',
    terms: 'conditions d\'utilisation',
    privacy: 'politique de confidentialité',
    gdprNotice: 'En vous connectant, vous acceptez nos',
    needHelp: 'Besoin d\'aide ?',
    contactSupport: 'Contactez le support',
    createAccount: 'Créer un compte',
    backToLogin: 'Retour à la connexion',
    confirmationSent: 'Email de confirmation envoyé ! Vérifiez votre boîte mail.',
    accountCreated: 'Compte créé avec succès ! Vérifiez vos emails pour confirmer votre compte.',
    personalInfo: 'Informations personnelles',
    firstName: 'Prénom',
    lastName: 'Nom de famille',
    linkedinProfile: 'Profil LinkedIn personnel',
    contact: 'Contact',
    country: 'Pays',
    countryCode: 'Indicatif pays',
    areaCode: 'Indicatif régional',
    phoneNumber: 'Numéro de téléphone',
    company: 'Entreprise',
    companyName: 'Nom de l\'entreprise',
    companyWebsite: 'Site web de l\'entreprise',
    companyLinkedin: 'Page LinkedIn de l\'entreprise',
    optional: '(optionnel)',
    required: '*',
    close: 'Fermer',
    alreadyHaveAccount: 'Déjà un compte ?',
    authSuccess: 'Connexion réussie !',
    authError: 'Erreur de connexion, veuillez réessayer.',
    authIncomplete: 'Connexion incomplète, veuillez réessayer.',
    sessionCleared: 'Session précédente effacée',
    forceLogout: 'Déconnexion automatique',
    loadingCountries: 'Chargement des pays...',
    limitedCountryList: 'Liste de pays limitée (connexion internet limitée)',
    selectCountry: 'Sélectionner un pays...'
  },
  en: {
    title: 'Intelia Expert',
    email: 'Email',
    password: 'Password',
    confirmPassword: 'Confirm password',
    login: 'Sign in',
    signup: 'Create account',
    rememberMe: 'Remember my email',
    forgotPassword: 'Forgot password?',
    newToIntelia: 'New to Intelia?',
    connecting: 'Connecting...',
    creating: 'Creating...',
    loginError: 'Login error',
    signupError: 'Signup error',
    emailRequired: 'Email address is required',
    emailInvalid: 'Please enter a valid email address',
    passwordRequired: 'Password is required',
    passwordTooShort: 'Password must contain at least 8 characters, one uppercase, one lowercase, one number and one special character',
    passwordMismatch: 'Passwords do not match',
    firstNameRequired: 'First name is required',
    lastNameRequired: 'Last name is required',
    countryRequired: 'Country is required',
    phoneInvalid: 'Invalid phone format',
    terms: 'terms of service',
    privacy: 'privacy policy',
    gdprNotice: 'By signing in, you agree to our',
    needHelp: 'Need help?',
    contactSupport: 'Contact support',
    createAccount: 'Create account',
    backToLogin: 'Back to login',
    confirmationSent: 'Confirmation email sent! Check your mailbox.',
    accountCreated: 'Account created successfully! Check your emails to confirm your account.',
    personalInfo: 'Personal information',
    firstName: 'First name',
    lastName: 'Last name',
    linkedinProfile: 'Personal LinkedIn profile',
    contact: 'Contact',
    country: 'Country',
    countryCode: 'Country code',
    areaCode: 'Area code',
    phoneNumber: 'Phone number',
    company: 'Company',
    companyName: 'Company name',
    companyWebsite: 'Company website',
    companyLinkedin: 'Company LinkedIn page',
    optional: '(optional)',
    required: '*',
    close: 'Close',
    alreadyHaveAccount: 'Already have an account?',
    authSuccess: 'Login successful!',
    authError: 'Login error, please try again.',
    authIncomplete: 'Incomplete login, please try again.',
    sessionCleared: 'Previous session cleared',
    forceLogout: 'Automatic logout',
    loadingCountries: 'Loading countries...',
    limitedCountryList: 'Limited country list (limited internet connection)',
    selectCountry: 'Select a country...'
  }
}

// Fonctions de validation
export const validateEmail = (email: string): boolean => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

// Validation mot de passe
export const validatePassword = (password: string): { isValid: boolean; errors: string[] } => {
  const errors: string[] = []
  
  if (password.length < 8) {
    errors.push('Au moins 8 caractères')
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('Une majuscule')
  }
  if (!/[a-z]/.test(password)) {
    errors.push('Une minuscule')
  }
  if (!/[0-9]/.test(password)) {
    errors.push('Un chiffre')
  }
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push('Un caractère spécial')
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}

// Validation téléphone
export const validatePhone = (countryCode: string, areaCode: string, phoneNumber: string): boolean => {
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

// Utilitaires Remember Me
export const rememberMeUtils = {
  save: (email: string, remember: boolean) => {
    try {
      if (remember && email) {
        localStorage.setItem('intelia_remember_email', email)
        localStorage.setItem('intelia_remember_flag', 'true')
        console.log('🔄 [Init] Remember me sauvegardé:', { email, remember })
      } else {
        localStorage.removeItem('intelia_remember_email')
        localStorage.removeItem('intelia_remember_flag')
        console.log('🔄 [Init] Remember me effacé')
      }
    } catch (error) {
      console.warn('⚠️ [Init] Erreur sauvegarde remember me:', error)
    }
  },

  load: () => {
    try {
      const savedEmail = localStorage.getItem('intelia_remember_email') || ''
      const rememberFlag = localStorage.getItem('intelia_remember_flag') === 'true'
      const hasRememberedEmail = !!(savedEmail && rememberFlag)
      
      const result = {
        rememberMe: rememberFlag,
        lastEmail: savedEmail,
        hasRememberedEmail
      }
      
      console.log('🔄 [Init] Chargement remember me:', result)
      return result
    } catch (error) {
      console.warn('⚠️ [Init] Erreur chargement remember me:', error)
      return { rememberMe: false, lastEmail: '', hasRememberedEmail: false }
    }
  }
}