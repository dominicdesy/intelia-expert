'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import Head from 'next/head'

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
    close: 'Fermer'
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
    personalInfo: 'Personal Information',
    firstName: 'First Name',
    lastName: 'Last Name',
    linkedinProfile: 'Personal LinkedIn Profile',
    contact: 'Contact',
    country: 'Country',
    countryCode: 'Country Code',
    areaCode: 'Area Code',
    phoneNumber: 'Phone Number',
    company: 'Company',
    companyName: 'Company Name',
    companyWebsite: 'Company Website',
    companyLinkedin: 'Company LinkedIn Page',
    optional: '(optional)',
    required: '*',
    close: 'Close'
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
    personalInfo: 'Información Personal',
    firstName: 'Nombre',
    lastName: 'Apellido',
    linkedinProfile: 'Perfil Personal de LinkedIn',
    contact: 'Contacto',
    country: 'País',
    countryCode: 'Código de País',
    areaCode: 'Código de Área',
    phoneNumber: 'Número de Teléfono',
    company: 'Empresa',
    companyName: 'Nombre de la Empresa',
    companyWebsite: 'Sitio Web de la Empresa',
    companyLinkedin: 'Página LinkedIn de la Empresa',
    optional: '(opcional)',
    required: '*',
    close: 'Cerrar'
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
    personalInfo: 'Persönliche Informationen',
    firstName: 'Vorname',
    lastName: 'Nachname',
    linkedinProfile: 'Persönliches LinkedIn-Profil',
    contact: 'Kontakt',
    country: 'Land',
    countryCode: 'Ländercode',
    areaCode: 'Vorwahl',
    phoneNumber: 'Telefonnummer',
    company: 'Unternehmen',
    companyName: 'Firmenname',
    companyWebsite: 'Firmen-Website',
    companyLinkedin: 'Unternehmens-LinkedIn-Seite',
    optional: '(optional)',
    required: '*',
    close: 'Schließen'
  }
}

const countries = [
  { value: 'CA', label: 'Canada' },
  { value: 'US', label: 'États-Unis' },
  { value: 'FR', label: 'France' },
  { value: 'BE', label: 'Belgique' },
  { value: 'CH', label: 'Suisse' },
  { value: 'MX', label: 'Mexique' },
  { value: 'BR', label: 'Brésil' }
]

const InteliaLogo = ({ className = "w-16 h-16" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

const LanguageSelector = ({ onLanguageChange, currentLanguage }: { 
  onLanguageChange: (lang: Language) => void
  currentLanguage: Language 
}) => {
  const [isOpen, setIsOpen] = useState(false)

  const languages = [
    { code: 'fr' as Language, name: 'Français', flag: '🇫🇷' },
    { code: 'en' as Language, name: 'English', flag: '🇺🇸' },
    { code: 'es' as Language, name: 'Español', flag: '🇪🇸' },
    { code: 'de' as Language, name: 'Deutsch', flag: '🇩🇪' }
  ]

  const currentLang = languages.find(lang => lang.code === currentLanguage)

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 transition-colors"
      >
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
        </svg>
        <span>{currentLang?.name}</span>
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
                onClick={() => {
                  onLanguageChange(lang.code)
                  setIsOpen(false)
                }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center space-x-2 ${
                  lang.code === currentLanguage ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
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

const validateLinkedIn = (url: string): boolean => {
  if (!url.trim()) return true
  return /^(https?:\/\/)?(www\.)?linkedin\.com\/(in|company)\/[\w\-]+\/?$/.test(url)
}

const validateWebsite = (url: string): boolean => {
  if (!url.trim()) return true
  return /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/.test(url)
}

export default function LoginPage() {
  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const t = translations[currentLanguage]
  
  const [isSignupMode, setIsSignupMode] = useState(false)
  
  const [loginData, setLoginData] = useState({
    email: '',
    password: '',
    rememberMe: false
  })

  const [signupData, setSignupData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    linkedinProfile: '',
    country: '',
    countryCode: '',      
    areaCode: '',         
    phoneNumber: '',      
    companyName: '',
    companyWebsite: '',
    companyLinkedin: ''
  })

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  useEffect(() => {
    const savedLanguage = localStorage.getItem('intelia-language') as Language
    if (savedLanguage && translations[savedLanguage]) {
      setCurrentLanguage(savedLanguage)
    } else {
      const browserLanguage = navigator.language.substring(0, 2) as Language
      if (translations[browserLanguage]) {
        setCurrentLanguage(browserLanguage)
      }
    }

    const rememberMe = localStorage.getItem('intelia-remember-me') === 'true'
    const lastEmail = localStorage.getItem('intelia-last-email') || ''
    
    if (rememberMe && lastEmail) {
      setLoginData(prev => ({
        ...prev,
        email: lastEmail,
        rememberMe: true
      }))
    }
  }, [])

  const handleLanguageChange = (newLanguage: Language) => {
    setCurrentLanguage(newLanguage)
    localStorage.setItem('intelia-language', newLanguage)
  }

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

  const validateSignupForm = (): string | null => {
    const { 
      email, password, confirmPassword, firstName, lastName, country, 
      countryCode, areaCode, phoneNumber,
      linkedinProfile, companyWebsite, companyLinkedin 
    } = signupData

    if (!email.trim()) return t.emailRequired
    if (!validateEmail(email)) return t.emailInvalid
    if (!password) return t.passwordRequired
    
    const passwordValidation = validatePassword(password)
    if (!passwordValidation.isValid) return t.passwordTooShort
    
    if (password !== confirmPassword) return t.passwordMismatch
    if (!firstName.trim()) return t.firstNameRequired
    if (!lastName.trim()) return t.lastNameRequired
    if (!country) return t.countryRequired
    
    if (!validatePhone(countryCode, areaCode, phoneNumber)) {
      return 'Format de téléphone invalide. Si vous renseignez le téléphone, tous les champs (indicatif pays, indicatif régional, numéro) sont requis.'
    }
    
    if (linkedinProfile && !validateLinkedIn(linkedinProfile)) return 'Format LinkedIn invalide'
    if (companyWebsite && !validateWebsite(companyWebsite)) return 'Format de site web invalide'
    if (companyLinkedin && !validateLinkedIn(companyLinkedin)) return 'Format LinkedIn entreprise invalide'
    
    return null
  }

  const handleSignup = async () => {
    setError('')
    setSuccess('')
    
    const validationError = validateSignupForm()
    if (validationError) {
      setError(validationError)
      return
    }

    setIsLoading(true)

    // Simulation d'appel API
    try {
      await new Promise(resolve => setTimeout(resolve, 2000))
      setSuccess(t.accountCreated)
      setSignupData({
        email: '', password: '', confirmPassword: '',
        firstName: '', lastName: '', linkedinProfile: '',
        country: '', countryCode: '', areaCode: '', phoneNumber: '',
        companyName: '', companyWebsite: '', companyLinkedin: ''
      })
      setTimeout(() => {
        setIsSignupMode(false)
        setSuccess('')
      }, 4000)
    } catch (error: any) {
      setError('Erreur technique inattendue. Veuillez réessayer.')
    } finally {
      setIsLoading(false)
    }
  }

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

    // Simulation d'appel API
    try {
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      if (loginData.rememberMe) {
        localStorage.setItem('intelia-remember-me', 'true')
        localStorage.setItem('intelia-last-email', loginData.email.trim())
      } else {
        localStorage.removeItem('intelia-remember-me')
        localStorage.removeItem('intelia-last-email')
      }
      
      // Simuler redirection
      alert('Connexion réussie ! (En production, redirection vers /chat)')
      
    } catch (error: any) {
      setError('Erreur technique inattendue. Veuillez réessayer.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      if (isSignupMode) {
        handleSignup()
      } else {
        handleLogin()
      }
    }
  }

  const toggleMode = () => {
    setIsSignupMode(!isSignupMode)
    setError('')
    setSuccess('')
    
    if (!isSignupMode) {
      setLoginData({ email: '', password: '', rememberMe: false })
    } else {
      const rememberMe = localStorage.getItem('intelia-remember-me') === 'true'
      const lastEmail = localStorage.getItem('intelia-last-email') || ''
      
      setLoginData({ 
        email: rememberMe ? lastEmail : '', 
        password: '', 
        rememberMe 
      })
    }
    
    setSignupData({
      email: '', password: '', confirmPassword: '',
      firstName: '', lastName: '', linkedinProfile: '',
      country: '', countryCode: '', areaCode: '', phoneNumber: '',
      companyName: '', companyWebsite: '', companyLinkedin: ''
    })
  }

  const handleCloseSignup = () => {
    setIsSignupMode(false)
    setError('')
    setSuccess('')
    
    // Restaurer les données de connexion si remember me était activé
    const rememberMe = localStorage.getItem('intelia-remember-me') === 'true'
    const lastEmail = localStorage.getItem('intelia-last-email') || ''
    
    setLoginData({ 
      email: rememberMe ? lastEmail : '', 
      password: '', 
      rememberMe 
    })
    
    // Réinitialiser le formulaire d'inscription
    setSignupData({
      email: '', password: '', confirmPassword: '',
      firstName: '', lastName: '', linkedinProfile: '',
      country: '', countryCode: '', areaCode: '', phoneNumber: '',
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
        <div className="absolute top-4 right-4">
          <LanguageSelector onLanguageChange={handleLanguageChange} currentLanguage={currentLanguage} />
        </div>
        
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="flex justify-center">
            <InteliaLogo className="w-16 h-16" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            {t.title}
          </h2>
        </div>

        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-2xl">
          <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10 max-h-screen overflow-y-auto relative">
            
            {/* Bouton de fermeture pour le mode inscription */}
            {isSignupMode && (
              <button
                onClick={handleCloseSignup}
                className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors z-10"
                title={t.close}
                disabled={isLoading}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
            
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

            {!isSignupMode && (
              <div className="space-y-6">
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

            {isSignupMode && (
              <div className="space-y-6 pt-2">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 border-b pb-2">
                    {t.personalInfo}
                  </h3>
                  
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label htmlFor="firstName" className="block text-sm font-medium text-gray-700">
                        {t.firstName} <span className="text-red-500">*</span>
                      </label>
                      <input
                        id="firstName"
                        type="text"
                        required
                        value={signupData.firstName}
                        onChange={(e) => handleSignupChange('firstName', e.target.value)}
                        className="mt-1 block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        disabled={isLoading}
                      />
                    </div>

                    <div>
                      <label htmlFor="lastName" className="block text-sm font-medium text-gray-700">
                        {t.lastName} <span className="text-red-500">*</span>
                      </label>
                      <input
                        id="lastName"
                        type="text"
                        required
                        value={signupData.lastName}
                        onChange={(e) => handleSignupChange('lastName', e.target.value)}
                        className="mt-1 block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        disabled={isLoading}
                      />
                    </div>
                  </div>

                  <div className="mt-4">
                    <label htmlFor="linkedinProfile" className="block text-sm font-medium text-gray-700">
                      {t.linkedinProfile} <span className="text-gray-500 text-xs">{t.optional}</span>
                    </label>
                    <input
                      id="linkedinProfile"
                      type="url"
                      value={signupData.linkedinProfile}
                      onChange={(e) => handleSignupChange('linkedinProfile', e.target.value)}
                      placeholder="https://linkedin.com/in/votre-profil"
                      className="mt-1 block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isLoading}
                    />
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 border-b pb-2">
                    {t.contact}
                  </h3>

                  <div className="mb-4">
                    <label htmlFor="signupEmail" className="block text-sm font-medium text-gray-700">
                      {t.email} <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="signupEmail"
                      type="email"
                      required
                      value={signupData.email}
                      onChange={(e) => handleSignupChange('email', e.target.value)}
                      placeholder="votre@email.com"
                      className="mt-1 block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isLoading}
                    />
                  </div>

                  <div className="mb-4">
                    <label htmlFor="country" className="block text-sm font-medium text-gray-700">
                      {t.country} <span className="text-red-500">*</span>
                    </label>
                    <select
                      id="country"
                      required
                      value={signupData.country}
                      onChange={(e) => handleSignupChange('country', e.target.value)}
                      className="mt-1 block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 bg-white shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isLoading}
                    >
                      <option value="">Sélectionner...</option>
                      {countries.map((country) => (
                        <option key={country.value} value={country.value}>
                          {country.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Téléphone <span className="text-gray-500 text-xs">{t.optional}</span>
                    </label>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label htmlFor="countryCode" className="block text-xs font-medium text-gray-600 mb-1">
                          {t.countryCode}
                        </label>
                        <select
                          id="countryCode"
                          value={signupData.countryCode}
                          onChange={(e) => handleSignupChange('countryCode', e.target.value)}
                          className="block w-full appearance-none rounded-md border border-gray-300 px-2 py-2 bg-white shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-sm"
                          disabled={isLoading}
                        >
                          <option value="">+</option>
                          <option value="+1">+1</option>
                          <option value="+33">+33</option>
                          <option value="+32">+32</option>
                          <option value="+41">+41</option>
                          <option value="+52">+52</option>
                          <option value="+55">+55</option>
                        </select>
                      </div>
                      
                      <div>
                        <label htmlFor="areaCode" className="block text-xs font-medium text-gray-600 mb-1">
                          {t.areaCode}
                        </label>
                        <input
                          id="areaCode"
                          type="tel"
                          value={signupData.areaCode}
                          onChange={(e) => handleSignupChange('areaCode', e.target.value)}
                          placeholder="555"
                          maxLength={3}
                          className="block w-full appearance-none rounded-md border border-gray-300 px-2 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-sm"
                          disabled={isLoading}
                        />
                      </div>
                      
                      <div>
                        <label htmlFor="phoneNumber" className="block text-xs font-medium text-gray-600 mb-1">
                          {t.phoneNumber}
                        </label>
                        <input
                          id="phoneNumber"
                          type="tel"
                          value={signupData.phoneNumber}
                          onChange={(e) => handleSignupChange('phoneNumber', e.target.value)}
                          placeholder="1234567"
                          maxLength={7}
                          className="block w-full appearance-none rounded-md border border-gray-300 px-2 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-sm"
                          disabled={isLoading}
                        />
                      </div>
                    </div>
                    
                    {(signupData.countryCode || signupData.areaCode || signupData.phoneNumber) && (
                      <div className="mt-2">
                        {validatePhone(signupData.countryCode, signupData.areaCode, signupData.phoneNumber) ? (
                          <div className="flex items-center text-xs text-green-600">
                            <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            Format téléphone valide
                          </div>
                        ) : (
                          <div className="flex items-center text-xs text-red-600">
                            <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                            </svg>
                            Tous les champs téléphone sont requis
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label htmlFor="signupPassword" className="block text-sm font-medium text-gray-700">
                        {t.password} <span className="text-red-500">*</span>
                      </label>
                      <div className="mt-1 relative">
                        <input
                          id="signupPassword"
                          type={showPassword ? "text" : "password"}
                          required
                          value={signupData.password}
                          onChange={(e) => handleSignupChange('password', e.target.value)}
                          className="block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 pr-10 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          placeholder="••••••••"
                          disabled={isLoading}
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute inset-y-0 right-0 pr-3 flex items-center"
                          tabIndex={-1}
                        >
                          <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        </button>
                      </div>
                      {signupData.password && (
                        <div className="mt-2 space-y-1">
                          {(() => {
                            const validation = validatePassword(signupData.password)
                            return validation.errors.map((error, index) => (
                              <div key={index} className="flex items-center text-xs text-red-600">
                                <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                                {error}
                              </div>
                            ))
                          })()}
                          {validatePassword(signupData.password).isValid && (
                            <div className="flex items-center text-xs text-green-600">
                              <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                              </svg>
                              Mot de passe valide
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <div>
                      <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                        {t.confirmPassword} <span className="text-red-500">*</span>
                      </label>
                      <div className="mt-1 relative">
                        <input
                          id="confirmPassword"
                          type={showConfirmPassword ? "text" : "password"}
                          required
                          value={signupData.confirmPassword}
                          onChange={(e) => handleSignupChange('confirmPassword', e.target.value)}
                          className="block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 pr-10 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          placeholder="••••••••"
                          disabled={isLoading}
                        />
                        <button
                          type="button"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          className="absolute inset-y-0 right-0 pr-3 flex items-center"
                          tabIndex={-1}
                        >
                          <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        </button>
                      </div>
                      {signupData.confirmPassword && (
                        <div className="mt-2">
                          {signupData.password === signupData.confirmPassword ? (
                            <div className="flex items-center text-xs text-green-600">
                              <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                              </svg>
                              Mots de passe identiques
                            </div>
                          ) : (
                            <div className="flex items-center text-xs text-red-600">
                              <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                              </svg>
                              Les mots de passe ne correspondent pas
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 border-b pb-2">
                    {t.company}
                  </h3>

                  <div className="mb-4">
                    <label htmlFor="companyName" className="block text-sm font-medium text-gray-700">
                      {t.companyName} <span className="text-gray-500 text-xs">{t.optional}</span>
                    </label>
                    <input
                      id="companyName"
                      type="text"
                      value={signupData.companyName}
                      onChange={(e) => handleSignupChange('companyName', e.target.value)}
                      className="mt-1 block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isLoading}
                    />
                  </div>

                  <div className="mb-4">
                    <label htmlFor="companyWebsite" className="block text-sm font-medium text-gray-700">
                      {t.companyWebsite} <span className="text-gray-500 text-xs">{t.optional}</span>
                    </label>
                    <input
                      id="companyWebsite"
                      type="url"
                      value={signupData.companyWebsite}
                      onChange={(e) => handleSignupChange('companyWebsite', e.target.value)}
                      placeholder="https://www.entreprise.com"
                      className="mt-1 block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isLoading}
                    />
                  </div>

                  <div>
                    <label htmlFor="companyLinkedin" className="block text-sm font-medium text-gray-700">
                      {t.companyLinkedin} <span className="text-gray-500 text-xs">{t.optional}</span>
                    </label>
                    <input
                      id="companyLinkedin"
                      type="url"
                      value={signupData.companyLinkedin}
                      onChange={(e) => handleSignupChange('companyLinkedin', e.target.value)}
                      placeholder="https://linkedin.com/company/votre-entreprise"
                      className="mt-1 block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isLoading}
                    />
                  </div>
                </div>

                <div className="pt-4">
                  <button
                    type="button"
                    onClick={handleSignup}
                    disabled={isLoading}
                    className="flex w-full justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isLoading ? (
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        <span>{t.creating}</span>
                      </div>
                    ) : (
                      t.signup
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Section des boutons de basculement - seulement visible en mode connexion */}
            {!isSignupMode && (
              <>
                <div className="mt-6">
                  <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-gray-300" />
                    </div>
                    <div className="relative flex justify-center text-sm">
                      <span className="bg-white px-2 text-gray-500">
                        {t.newToIntelia}
                      </span>
                    </div>
                  </div>

                  <div className="mt-6">
                    <button
                      type="button"
                      onClick={toggleMode}
                      className="flex w-full justify-center rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
                    >
                      {t.createAccount}
                    </button>
                  </div>
                </div>
              </>
            )}

            {/* Section RGPD */}
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

        {/* Section d'aide */}
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