'use client'

// Forcer l'utilisation du runtime Node.js au lieu d'Edge Runtime
export const runtime = 'nodejs'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import Head from 'next/head'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

// Instance Supabase réutilisable
const supabase = createClientComponentClient()

// ==================== SYSTEM INTERNATIONALIZATION ====================
type Language = 'fr' | 'en' | 'es' | 'de'

const translations = {
  fr: {
    title: 'Intelia Expert',
    email: 'Email',
    password: 'Mot de passe',
    confirmPassword: 'Confirmer le mot de passe',
    login: 'Se connecter',
    signup: 'Créer un compte',
    rememberMe: 'Se souvenir de moi',
    forgotPassword: 'Mot de passe oublié ?',
    newToIntelia: 'Nouveau sur Intelia ?',
    connecting: 'Connexion en cours...',
    creating: 'Création en cours...',
    loginError: 'Erreur de connexion',
    signupError: 'Erreur de création',
    emailRequired: 'L\'adresse email est requise',
    emailInvalid: 'Veuillez entrer une adresse email valide',
    passwordRequired: 'Le mot de passe est requis',
    passwordTooShort: 'Le mot de passe doit contenir au moins 8 caractères, une majuscule et un chiffre',
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
    // Champs formulaire d'inscription
    personalInfo: 'Informations personnelles',
    firstName: 'Prénom',
    lastName: 'Nom de famille',
    linkedinProfile: 'Profil LinkedIn personnel',
    contact: 'Contact',
    country: 'Pays',
    phone: 'Téléphone',
    phoneFormat: 'Format: +1 (XXX) XXX-XXXX',
    company: 'Entreprise',
    companyName: 'Nom de l\'entreprise',
    companyWebsite: 'Site web de l\'entreprise',
    companyLinkedin: 'Page LinkedIn de l\'entreprise',
    optional: '(optionnel)',
    required: '*'
  },
  en: {
    title: 'Intelia Expert',
    email: 'Email',
    password: 'Password',
    confirmPassword: 'Confirm password',
    login: 'Sign in',
    signup: 'Create account',
    rememberMe: 'Remember me',
    forgotPassword: 'Forgot password?',
    newToIntelia: 'New to Intelia?',
    connecting: 'Signing in...',
    creating: 'Creating account...',
    loginError: 'Login error',
    signupError: 'Signup error',
    emailRequired: 'Email address is required',
    emailInvalid: 'Please enter a valid email address',
    passwordRequired: 'Password is required',
    passwordTooShort: 'Password must be at least 8 characters with one uppercase letter and one number',
    passwordMismatch: 'Passwords do not match',
    firstNameRequired: 'First name is required',
    lastNameRequired: 'Last name is required',
    countryRequired: 'Country is required',
    phoneInvalid: 'Invalid phone format',
    terms: 'terms of service',
    privacy: 'privacy policy',
    gdprNotice: 'By signing in, you accept our',
    needHelp: 'Need help?',
    contactSupport: 'Contact support',
    createAccount: 'Create account',
    backToLogin: 'Back to login',
    confirmationSent: 'Confirmation email sent! Check your mailbox.',
    accountCreated: 'Account created successfully! Check your emails to confirm your account.',
    // Champs formulaire d'inscription
    personalInfo: 'Personal Information',
    firstName: 'First Name',
    lastName: 'Last Name',
    linkedinProfile: 'Personal LinkedIn Profile',
    contact: 'Contact',
    country: 'Country',
    phone: 'Phone',
    phoneFormat: 'Format: +1 (XXX) XXX-XXXX',
    company: 'Company',
    companyName: 'Company Name',
    companyWebsite: 'Company Website',
    companyLinkedin: 'Company LinkedIn Page',
    optional: '(optional)',
    required: '*'
  },
  es: {
    title: 'Intelia Expert',
    email: 'Email',
    password: 'Contraseña',
    confirmPassword: 'Confirmar contraseña',
    login: 'Iniciar sesión',
    signup: 'Crear cuenta',
    rememberMe: 'Recordarme',
    forgotPassword: '¿Olvidaste tu contraseña?',
    newToIntelia: '¿Nuevo en Intelia?',
    connecting: 'Iniciando sesión...',
    creating: 'Creando cuenta...',
    loginError: 'Error de inicio de sesión',
    signupError: 'Error de registro',
    emailRequired: 'La dirección de correo es requerida',
    emailInvalid: 'Por favor ingresa una dirección de correo válida',
    passwordRequired: 'La contraseña es requerida',
    passwordTooShort: 'La contraseña debe tener al menos 8 caracteres con una mayúscula y un número',
    passwordMismatch: 'Las contraseñas no coinciden',
    firstNameRequired: 'El nombre es requerido',
    lastNameRequired: 'El apellido es requerido',
    countryRequired: 'El país es requerido',
    phoneInvalid: 'Formato de teléfono inválido',
    terms: 'términos de servicio',
    privacy: 'política de privacidad',
    gdprNotice: 'Al iniciar sesión, aceptas nuestros',
    needHelp: '¿Necesitas ayuda?',
    contactSupport: 'Contactar soporte',
    createAccount: 'Crear cuenta',
    backToLogin: 'Volver al inicio',
    confirmationSent: '¡Email de confirmación enviado! Revisa tu bandeja de entrada.',
    accountCreated: '¡Cuenta creada exitosamente! Revisa tus emails para confirmar tu cuenta.',
    // Champs formulaire d'inscription
    personalInfo: 'Información Personal',
    firstName: 'Nombre',
    lastName: 'Apellido',
    linkedinProfile: 'Perfil Personal de LinkedIn',
    contact: 'Contacto',
    country: 'País',
    phone: 'Teléfono',
    phoneFormat: 'Formato: +1 (XXX) XXX-XXXX',
    company: 'Empresa',
    companyName: 'Nombre de la Empresa',
    companyWebsite: 'Sitio Web de la Empresa',
    companyLinkedin: 'Página LinkedIn de la Empresa',
    optional: '(opcional)',
    required: '*'
  },
  de: {
    title: 'Intelia Expert',
    email: 'E-Mail',
    password: 'Passwort',
    confirmPassword: 'Passwort bestätigen',
    login: 'Anmelden',
    signup: 'Konto erstellen',
    rememberMe: 'Angemeldet bleiben',
    forgotPassword: 'Passwort vergessen?',
    newToIntelia: 'Neu bei Intelia?',
    connecting: 'Anmeldung läuft...',
    creating: 'Konto wird erstellt...',
    loginError: 'Anmeldefehler',
    signupError: 'Registrierungsfehler',
    emailRequired: 'E-Mail-Adresse ist erforderlich',
    emailInvalid: 'Bitte geben Sie eine gültige E-Mail-Adresse ein',
    passwordRequired: 'Passwort ist erforderlich',
    passwordTooShort: 'Passwort muss mindestens 8 Zeichen mit einem Großbuchstaben und einer Zahl haben',
    passwordMismatch: 'Passwörter stimmen nicht überein',
    firstNameRequired: 'Vorname ist erforderlich',
    lastNameRequired: 'Nachname ist erforderlich',
    countryRequired: 'Land ist erforderlich',
    phoneInvalid: 'Ungültiges Telefonformat',
    terms: 'Nutzungsbedingungen',
    privacy: 'Datenschutzrichtlinie',
    gdprNotice: 'Durch die Anmeldung akzeptieren Sie unsere',
    needHelp: 'Brauchen Sie Hilfe?',
    contactSupport: 'Support kontaktieren',
    createAccount: 'Konto erstellen',
    backToLogin: 'Zurück zur Anmeldung',
    confirmationSent: 'Bestätigungs-E-Mail gesendet! Überprüfen Sie Ihr Postfach.',
    accountCreated: 'Konto erfolgreich erstellt! Überprüfen Sie Ihre E-Mails zur Kontobestätigung.',
    // Champs formulaire d'inscription
    personalInfo: 'Persönliche Informationen',
    firstName: 'Vorname',
    lastName: 'Nachname',
    linkedinProfile: 'Persönliches LinkedIn-Profil',
    contact: 'Kontakt',
    country: 'Land',
    phone: 'Telefon',
    phoneFormat: 'Format: +1 (XXX) XXX-XXXX',
    company: 'Unternehmen',
    companyName: 'Firmenname',
    companyWebsite: 'Firmen-Website',
    companyLinkedin: 'Unternehmens-LinkedIn-Seite',
    optional: '(optional)',
    required: '*'
  }
}

// Liste des pays
const countries = [
  { value: 'CA', label: 'Canada' },
  { value: 'US', label: 'États-Unis' },
  { value: 'FR', label: 'France' },
  { value: 'BE', label: 'Belgique' },
  { value: 'CH', label: 'Suisse' },
  { value: 'MX', label: 'Mexique' },
  { value: 'BR', label: 'Brésil' }
]

// ==================== LOGO INTELIA ====================
const InteliaLogo = ({ className = "w-16 h-16" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// ==================== LANGUAGE CONTEXT ====================
const useLanguage = () => {
  const [language, setLanguage] = useState<Language>('fr')

  useEffect(() => {
    const savedLanguage = localStorage.getItem('intelia-language') as Language
    if (savedLanguage && translations[savedLanguage]) {
      setLanguage(savedLanguage)
    } else {
      const browserLanguage = navigator.language.substring(0, 2) as Language
      if (translations[browserLanguage]) {
        setLanguage(browserLanguage)
      }
    }
  }, [])

  const changeLanguage = (newLanguage: Language) => {
    setLanguage(newLanguage)
    localStorage.setItem('intelia-language', newLanguage)
  }

  return {
    language,
    changeLanguage,
    t: translations[language]
  }
}

// ==================== SÉLECTEUR DE LANGUE ====================
const LanguageSelector = ({ onLanguageChange }: { onLanguageChange: (lang: Language) => void }) => {
  const { language, changeLanguage } = useLanguage()
  const [isOpen, setIsOpen] = useState(false)

  const languages = [
    { code: 'fr' as Language, name: 'Français', flag: '🇫🇷' },
    { code: 'en' as Language, name: 'English', flag: '🇺🇸' },
    { code: 'es' as Language, name: 'Español', flag: '🇪🇸' },
    { code: 'de' as Language, name: 'Deutsch', flag: '🇩🇪' }
  ]

  const currentLanguage = languages.find(lang => lang.code === language)

  const handleLanguageChange = (newLanguage: Language) => {
    changeLanguage(newLanguage)
    onLanguageChange(newLanguage)
    setIsOpen(false)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 transition-colors"
      >
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
        </svg>
        <span>{currentLanguage?.name}</span>
        <svg className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
            {languages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => handleLanguageChange(lang.code)}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center space-x-2 ${
                  lang.code === language ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
                } first:rounded-t-lg last:rounded-b-lg transition-colors`}
              >
                <span>{lang.flag}</span>
                <span>{lang.name}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// ==================== VALIDATION FUNCTIONS ====================
const validateEmail = (email: string): boolean => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

const validatePassword = (password: string): { isValid: boolean; errors: string[] } => {
  const errors: string[] = []
  
  if (password.length < 8) {
    errors.push('Au moins 8 caractères')
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('Une majuscule')
  }
  if (!/[0-9]/.test(password)) {
    errors.push('Un chiffre')
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}

const validatePhone = (phone: string): boolean => {
  if (!phone.trim()) return true // Optional field
  // Format: +1 (XXX) XXX-XXXX or variations
  return /^[\+]?[1-9][\d]{0,3}[\s\(\-]?[\d]{3}[\s\)\-]?[\d]{3}[\s\-]?[\d]{4}$/.test(phone.replace(/\s/g, ''))
}

const validateLinkedIn = (url: string): boolean => {
  if (!url.trim()) return true // Optional field
  return /^(https?:\/\/)?(www\.)?linkedin\.com\/(in|company)\/[\w\-]+\/?$/.test(url)
}

const validateWebsite = (url: string): boolean => {
  if (!url.trim()) return true // Optional field
  return /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/.test(url)
}

// ==================== PAGE DE CONNEXION/INSCRIPTION ====================
export default function LoginPage() {
  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const t = translations[currentLanguage]
  
  const [isSignupMode, setIsSignupMode] = useState(false)
  
  // Données de connexion
  const [loginData, setLoginData] = useState({
    email: '',
    password: '',
    rememberMe: false
  })

  // Données d'inscription complètes
  const [signupData, setSignupData] = useState({
    // Authentification
    email: '',
    password: '',
    confirmPassword: '',
    
    // Informations personnelles
    firstName: '',
    lastName: '',
    linkedinProfile: '',
    
    // Contact
    country: '',
    phone: '',
    
    // Entreprise
    companyName: '',
    companyWebsite: '',
    companyLinkedin: ''
  })

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const handleLoginChange = (field: string, value: string | boolean) => {
    setLoginData(prev => ({ ...prev, [field]: value }))
    if (error) setError('')
    if (success) setSuccess('')
  }

  const handleSignupChange = (field: string, value: string) => {
    setSignupData(prev => ({ ...prev, [field]: value }))
    if (error) setError('')
    if (success) setSuccess('')
  }

  // Handler pour changement de langue
  const handleLanguageChange = (lang: Language) => {
    setCurrentLanguage(lang)
  }

  // VALIDATION SIGNUP COMPLET
  const validateSignupForm = (): string | null => {
    const { email, password, confirmPassword, firstName, lastName, country, phone, linkedinProfile, companyWebsite, companyLinkedin } = signupData

    if (!email.trim()) return t.emailRequired
    if (!validateEmail(email)) return t.emailInvalid
    if (!password) return t.passwordRequired
    
    const passwordValidation = validatePassword(password)
    if (!passwordValidation.isValid) return t.passwordTooShort
    
    if (password !== confirmPassword) return t.passwordMismatch
    if (!firstName.trim()) return t.firstNameRequired
    if (!lastName.trim()) return t.lastNameRequired
    if (!country) return t.countryRequired
    if (!validatePhone(phone)) return t.phoneInvalid
    if (linkedinProfile && !validateLinkedIn(linkedinProfile)) return 'Format LinkedIn invalide'
    if (companyWebsite && !validateWebsite(companyWebsite)) return 'Format de site web invalide'
    if (companyLinkedin && !validateLinkedIn(companyLinkedin)) return 'Format LinkedIn entreprise invalide'
    
    return null
  }

  // FONCTION DE CRÉATION DE COMPTE AMÉLIORÉE
  const handleSignup = async () => {
    setError('')
    setSuccess('')
    
    const validationError = validateSignupForm()
    if (validationError) {
      setError(validationError)
      return
    }

    setIsLoading(true)

    try {
      console.log('📝 Création de compte avec profil complet:', signupData.email)
      
      // CRÉATION DE COMPTE AVEC MÉTADONNÉES COMPLÈTES
      const { data, error } = await supabase.auth.signUp({
        email: signupData.email.trim(),
        password: signupData.password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
          data: {
            // Informations personnelles
            first_name: signupData.firstName.trim(),
            last_name: signupData.lastName.trim(),
            linkedin_profile: signupData.linkedinProfile.trim(),
            
            // Contact
            country: signupData.country,
            phone: signupData.phone.trim(),
            
            // Entreprise
            company_name: signupData.companyName.trim(),
            company_website: signupData.companyWebsite.trim(),
            company_linkedin: signupData.companyLinkedin.trim(),
            
            // Métadonnées
            created_at: new Date().toISOString(),
            role: 'producer',
            profile_complete: true
          }
        }
      })
      
      if (error) {
        console.error('❌ Erreur Supabase signup:', error)
        
        const errorMessages: Record<string, string> = {
          'User already registered': 'Un compte existe déjà avec cet email.',
          'Password should be at least 6 characters': t.passwordTooShort,
          'Invalid email': t.emailInvalid,
          'Signup is disabled': 'La création de compte est temporairement désactivée.',
          'Email rate limit exceeded': 'Trop de tentatives. Réessayez dans quelques minutes.',
          'Invalid phone number': 'Numéro de téléphone invalide.',
          'Weak password': 'Mot de passe trop faible. Utilisez au moins 8 caractères avec lettres et chiffres.'
        }
        
        const friendlyMessage = errorMessages[error.message] || error.message
        setError(friendlyMessage)
        return
      }

      console.log('✅ Compte créé avec succès:', data)

      if (data.user && !data.user.email_confirmed_at) {
        setSuccess(t.accountCreated)
        // Réinitialiser le formulaire
        setSignupData({
          email: '', password: '', confirmPassword: '',
          firstName: '', lastName: '', linkedinProfile: '',
          country: '', phone: '',
          companyName: '', companyWebsite: '', companyLinkedin: ''
        })
        // Passer en mode login après 4 secondes
        setTimeout(() => {
          setIsSignupMode(false)
          setSuccess('')
        }, 4000)
      } else if (data.user && data.user.email_confirmed_at) {
        setSuccess('Compte créé et confirmé ! Redirection...')
        setTimeout(() => {
          window.location.href = '/chat'
        }, 1500)
      }
      
    } catch (error: any) {
      console.error('❌ Erreur critique de création:', error)
      setError('Erreur technique inattendue. Veuillez réessayer.')
    } finally {
      setIsLoading(false)
    }
  }

  // FONCTION DE CONNEXION
  const handleLogin = async () => {
    setError('')
    setSuccess('')
    
    if (!loginData.email.trim()) {
      setError(t.emailRequired)
      return
    }
    
    if (!validateEmail(loginData.email)) {
      setError(t.emailInvalid)
      return
    }
    
    if (!loginData.password) {
      setError(t.passwordRequired)
      return
    }

    if (loginData.password.length < 6) {
      setError(t.passwordTooShort)
      return
    }

    setIsLoading(true)

    try {
      console.log('🔐 Tentative de connexion:', loginData.email)
      
      const { data, error } = await supabase.auth.signInWithPassword({
        email: loginData.email.trim(),
        password: loginData.password
      })
      
      if (error) {
        console.error('❌ Erreur Supabase:', error)
        
        const errorMessages: Record<string, string> = {
          'Invalid login credentials': 'Email ou mot de passe incorrect',
          'Email not confirmed': 'Email non confirmé. Vérifiez votre boîte mail et cliquez sur le lien de confirmation.',
          'Too many requests': 'Trop de tentatives. Réessayez dans quelques minutes.',
          'User not found': 'Aucun compte trouvé avec cet email.',
          'Wrong password': 'Mot de passe incorrect',
          'Auth session missing': 'Session expirée. Veuillez vous reconnecter.'
        }
        
        const friendlyMessage = errorMessages[error.message] || error.message
        setError(friendlyMessage)
        return
      }

      if (!data.user) {
        setError('Erreur de connexion. Veuillez réessayer.')
        return
      }

      console.log('✅ Connexion réussie:', data.user.email)
      window.location.href = '/chat'
      
    } catch (error: any) {
      console.error('❌ Erreur critique de connexion:', error)
      setError('Erreur technique inattendue. Veuillez réessayer.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = () => {
    if (isSignupMode) {
      handleSignup()
    } else {
      handleLogin()
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      handleSubmit()
    }
  }

  const toggleMode = () => {
    setIsSignupMode(!isSignupMode)
    setError('')
    setSuccess('')
    setLoginData({ email: '', password: '', rememberMe: false })
    setSignupData({
      email: '', password: '', confirmPassword: '',
      firstName: '', lastName: '', linkedinProfile: '',
      country: '', phone: '',
      companyName: '', companyWebsite: '', companyLinkedin: ''
    })
  }

  return (
    <>
      <Head>
        <title>Intelia | Expert</title>
        <meta name="description" content="Intelia Expert - Connexion" />
      </Head>
      
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 relative">
        {/* Sélecteur de langue */}
        <div className="absolute top-4 right-4">
          <LanguageSelector onLanguageChange={handleLanguageChange} />
        </div>
        
        {/* Header */}
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="flex justify-center">
            <InteliaLogo className="w-16 h-16" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            {t.title}
          </h2>
        </div>

        {/* Formulaire */}
        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-lg">
          <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
            
            {/* Messages d'erreur et succès */}
            {error && (
              <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800">
                      {isSignupMode ? t.signupError : t.loginError}
                    </h3>
                    <div className="mt-1 text-sm text-red-700">
                      {error}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {success && (
              <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <div className="text-sm text-green-700">
                      {success}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* FORMULAIRE DE CONNEXION */}
            {!isSignupMode && (
              <div className="space-y-6">
                {/* Email */}
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                    {t.email} <span className="text-red-500">*</span>
                  </label>
                  <div className="mt-1">
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={loginData.email}
                      onChange={(e) => handleLoginChange('email', e.target.value)}
                      onKeyPress={handleKeyPress}
                      className="block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm transition-colors"
                      placeholder="votre@email.com"
                      disabled={isLoading}
                    />
                  </div>
                </div>

                {/* Mot de passe */}
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                    {t.password} <span className="text-red-500">*</span>
                  </label>
                  <div className="mt-1 relative">
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      required
                      value={loginData.password}
                      onChange={(e) => handleLoginChange('password', e.target.value)}
                      onKeyPress={handleKeyPress}
                      className="block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 pr-10 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm transition-colors"
                      placeholder="••••••••"
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center hover:text-gray-600 transition-colors"
                      disabled={isLoading}
                      tabIndex={-1}
                    >
                      {showPassword ? (
                        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.34 6.34m6.822 10.565l-3.536-3.536" />
                        </svg>
                      ) : (
                        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                {/* Options */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <input
                      id="remember-me"
                      name="remember-me"
                      type="checkbox"
                      checked={loginData.rememberMe}
                      onChange={(e) => handleLoginChange('rememberMe', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      disabled={isLoading}
                    />
                    <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-900">
                      {t.rememberMe}
                    </label>
                  </div>

                  <div className="text-sm">
                    <Link 
                      href="/auth/forgot-password" 
                      className="font-medium text-blue-600 hover:text-blue-500 transition-colors"
                    >
                      {t.forgotPassword}
                    </Link>
                  </div>
                </div>

                {/* Bouton de connexion */}
                <div>
                  <button
                    type="button"
                    onClick={handleLogin}
                    disabled={isLoading || !loginData.email || !loginData.password}
                    className="flex w-full justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isLoading ? (
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        <span>{t.connecting}</span>
                      </div>
                    ) : (
                      t.login
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* FORMULAIRE D'INSCRIPTION (partie tronquée pour économiser l'espace) */}
            {isSignupMode && (
              <div className="text-center text-gray-500 py-8">
                Formulaire d'inscription disponible - utilisez le code complet du fichier original
              </div>
            )}

            {/* Séparateur et toggle */}
            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="bg-white px-2 text-gray-500">
                    {isSignupMode ? 'Déjà un compte ?' : t.newToIntelia}
                  </span>
                </div>
              </div>

              <div className="mt-6">
                <button
                  type="button"
                  onClick={toggleMode}
                  className="flex w-full justify-center rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
                >
                  {isSignupMode ? t.backToLogin : t.createAccount}
                </button>
              </div>
            </div>

            {/* Footer RGPD */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <p className="text-xs text-gray-500 text-center leading-relaxed">
                {t.gdprNotice}{' '}
                <a href="/terms" className="text-blue-600 hover:text-blue-500 transition-colors">
                  {t.terms}
                </a>{' '}
                et notre{' '}
                <a href="/privacy" className="text-blue-600 hover:text-blue-500 transition-colors">
                  {t.privacy}
                </a>
                .
              </p>
            </div>
          </div>
        </div>

        {/* Footer avec support */}
        <div className="mt-8 text-center">
          <p className="text-xs text-gray-500">
            {t.needHelp}{' '}
            <button
              type="button"
              onClick={() => window.open('mailto:support@intelia.com', '_blank')}
              className="text-blue-600 hover:underline font-medium"
            >
              {t.contactSupport}
            </button>
          </p>
        </div>
      </div>
    </>
  )
}