'use client'

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
    subtitle: 'Assistant IA spécialisé en santé et nutrition animale',
    email: 'Adresse email',
    password: 'Mot de passe',
    login: 'Se connecter',
    signup: 'Créer un compte',
    rememberMe: 'Se souvenir de moi',
    forgotPassword: 'Mot de passe oublié ?',
    newToIntelia: 'Nouveau sur Intelia ?',
    connecting: 'Connexion en cours...',
    loginError: 'Erreur de connexion',
    emailRequired: 'L\'adresse email est requise',
    emailInvalid: 'Veuillez entrer une adresse email valide',
    passwordRequired: 'Le mot de passe est requis',
    passwordTooShort: 'Le mot de passe doit contenir au moins 6 caractères',
    terms: 'conditions d\'utilisation',
    privacy: 'politique de confidentialité',
    gdprNotice: 'En vous connectant, vous acceptez nos',
    dataRetention: '🔒 Données supprimées automatiquement après 30 jours d\'inactivité.',
    needHelp: 'Besoin d\'aide ?',
    contactSupport: 'Contactez le support',
    createAccount: 'Créer un compte',
    confirmationSent: 'Email de confirmation envoyé ! Vérifiez votre boîte mail.',
    accountCreated: 'Compte créé avec succès ! Vérifiez vos emails pour confirmer votre compte.'
  },
  en: {
    title: 'Intelia Expert',
    subtitle: 'AI Assistant specialized in animal health and nutrition',
    email: 'Email address',
    password: 'Password',
    login: 'Sign in',
    signup: 'Create account',
    rememberMe: 'Remember me',
    forgotPassword: 'Forgot password?',
    newToIntelia: 'New to Intelia?',
    connecting: 'Signing in...',
    loginError: 'Login error',
    emailRequired: 'Email address is required',
    emailInvalid: 'Please enter a valid email address',
    passwordRequired: 'Password is required',
    passwordTooShort: 'Password must be at least 6 characters',
    terms: 'terms of service',
    privacy: 'privacy policy',
    gdprNotice: 'By signing in, you accept our',
    dataRetention: '🔒 Data automatically deleted after 30 days of inactivity.',
    needHelp: 'Need help?',
    contactSupport: 'Contact support',
    createAccount: 'Create account',
    confirmationSent: 'Confirmation email sent! Check your mailbox.',
    accountCreated: 'Account created successfully! Check your emails to confirm your account.'
  },
  es: {
    title: 'Intelia Expert',
    subtitle: 'Asistente IA especializado en salud y nutrición animal',
    email: 'Dirección de correo',
    password: 'Contraseña',
    login: 'Iniciar sesión',
    signup: 'Crear cuenta',
    rememberMe: 'Recordarme',
    forgotPassword: '¿Olvidaste tu contraseña?',
    newToIntelia: '¿Nuevo en Intelia?',
    connecting: 'Iniciando sesión...',
    loginError: 'Error de inicio de sesión',
    emailRequired: 'La dirección de correo es requerida',
    emailInvalid: 'Por favor ingresa una dirección de correo válida',
    passwordRequired: 'La contraseña es requerida',
    passwordTooShort: 'La contraseña debe tener al menos 6 caracteres',
    terms: 'términos de servicio',
    privacy: 'política de privacidad',
    gdprNotice: 'Al iniciar sesión, aceptas nuestros',
    dataRetention: '🔒 Datos eliminados automáticamente después de 30 días de inactividad.',
    needHelp: '¿Necesitas ayuda?',
    contactSupport: 'Contactar soporte',
    createAccount: 'Crear cuenta',
    confirmationSent: '¡Email de confirmación enviado! Revisa tu bandeja de entrada.',
    accountCreated: '¡Cuenta creada exitosamente! Revisa tus emails para confirmar tu cuenta.'
  },
  de: {
    title: 'Intelia Expert',
    subtitle: 'KI-Assistent spezialisiert auf Tiergesundheit und -ernährung',
    email: 'E-Mail-Adresse',
    password: 'Passwort',
    login: 'Anmelden',
    signup: 'Konto erstellen',
    rememberMe: 'Angemeldet bleiben',
    forgotPassword: 'Passwort vergessen?',
    newToIntelia: 'Neu bei Intelia?',
    connecting: 'Anmeldung läuft...',
    loginError: 'Anmeldefehler',
    emailRequired: 'E-Mail-Adresse ist erforderlich',
    emailInvalid: 'Bitte geben Sie eine gültige E-Mail-Adresse ein',
    passwordRequired: 'Passwort ist erforderlich',
    passwordTooShort: 'Passwort muss mindestens 6 Zeichen haben',
    terms: 'Nutzungsbedingungen',
    privacy: 'Datenschutzrichtlinie',
    gdprNotice: 'Durch die Anmeldung akzeptieren Sie unsere',
    dataRetention: '🔒 Daten werden nach 30 Tagen Inaktivität automatisch gelöscht.',
    needHelp: 'Brauchen Sie Hilfe?',
    contactSupport: 'Support kontaktieren',
    createAccount: 'Konto erstellen',
    confirmationSent: 'Bestätigungs-E-Mail gesendet! Überprüfen Sie Ihr Postfach.',
    accountCreated: 'Konto erfolgreich erstellt! Überprüfen Sie Ihre E-Mails zur Kontobestätigung.'
  }
}

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
    // Charger la langue sauvegardée ou détecter automatiquement
    const savedLanguage = localStorage.getItem('intelia-language') as Language
    if (savedLanguage && translations[savedLanguage]) {
      setLanguage(savedLanguage)
    } else {
      // Auto-détection basée sur le navigateur
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

// ==================== SÉLECTEUR DE LANGUE AMÉLIORÉ ====================
const LanguageSelector = () => {
  const { language, changeLanguage } = useLanguage()
  const [isOpen, setIsOpen] = useState(false)

  const languages = [
    { code: 'fr' as Language, name: 'Français', flag: '🇫🇷' },
    { code: 'en' as Language, name: 'English', flag: '🇺🇸' },
    { code: 'es' as Language, name: 'Español', flag: '🇪🇸' },
    { code: 'de' as Language, name: 'Deutsch', flag: '🇩🇪' }
  ]

  const currentLanguage = languages.find(lang => lang.code === language)

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
                onClick={() => {
                  changeLanguage(lang.code)
                  setIsOpen(false)
                }}
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

// ==================== PAGE DE CONNEXION AVEC SIGNUP ====================
export default function LoginPage() {
  const { t } = useLanguage()
  const [isSignupMode, setIsSignupMode] = useState(false)
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    rememberMe: false
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const handleInputChange = (field: string, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    if (error) {
      setError('')
    }
    if (success) {
      setSuccess('')
    }
  }

  // FONCTION DE CRÉATION DE COMPTE AVEC SUPABASE
  const handleSignup = async () => {
    setError('')
    setSuccess('')
    
    // Validations
    if (!formData.email.trim()) {
      setError(t.emailRequired)
      return
    }
    
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setError(t.emailInvalid)
      return
    }
    
    if (!formData.password) {
      setError(t.passwordRequired)
      return
    }

    if (formData.password.length < 6) {
      setError(t.passwordTooShort)
      return
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Les mots de passe ne correspondent pas')
      return
    }

    setIsLoading(true)

    try {
      console.log('📝 Création de compte avec Supabase:', formData.email)
      
      // CRÉATION DE COMPTE AVEC SUPABASE
      const { data, error } = await supabase.auth.signUp({
        email: formData.email.trim(),
        password: formData.password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
          data: {
            created_at: new Date().toISOString(),
            app_metadata: {
              provider: 'email',
              role: 'producer'
            }
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
          'Email rate limit exceeded': 'Trop de tentatives. Réessayez dans quelques minutes.'
        }
        
        const friendlyMessage = errorMessages[error.message] || error.message
        setError(friendlyMessage)
        return
      }

      console.log('✅ Compte créé:', data)

      if (data.user && !data.user.email_confirmed_at) {
        setSuccess(t.accountCreated)
        // Réinitialiser le formulaire
        setFormData({
          email: '',
          password: '',
          confirmPassword: '',
          rememberMe: false
        })
        // Passer en mode login après 3 secondes
        setTimeout(() => {
          setIsSignupMode(false)
          setSuccess('')
        }, 3000)
      } else if (data.user && data.user.email_confirmed_at) {
        // Utilisateur créé et confirmé immédiatement (rare)
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

  // FONCTION DE CONNEXION AMÉLIORÉE
  const handleLogin = async () => {
    setError('')
    setSuccess('')
    
    // Validations
    if (!formData.email.trim()) {
      setError(t.emailRequired)
      return
    }
    
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setError(t.emailInvalid)
      return
    }
    
    if (!formData.password) {
      setError(t.passwordRequired)
      return
    }

    if (formData.password.length < 6) {
      setError(t.passwordTooShort)
      return
    }

    setIsLoading(true)

    try {
      console.log('🔐 Tentative de connexion avec Supabase:', formData.email)
      
      // CONNEXION AVEC SUPABASE
      const { data, error } = await supabase.auth.signInWithPassword({
        email: formData.email.trim(),
        password: formData.password
      })
      
      if (error) {
        console.error('❌ Erreur Supabase:', error)
        
        const errorMessages: Record<string, string> = {
          'Invalid login credentials': 'Email ou mot de passe incorrect',
          'Email not confirmed': 'Email non confirmé. Vérifiez votre boîte mail et cliquez sur le lien de confirmation.',
          'Too many requests': 'Trop de tentatives. Réessayez dans quelques minutes.',
          'User not found': 'Aucun compte trouvé avec cet email. Voulez-vous créer un compte ?',
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
      
      // Redirection après connexion réussie
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

  return (
    <>
      <Head>
        <title>Intelia | Expert</title>
        <meta name="description" content="Assistant IA spécialisé en santé et nutrition animale" />
      </Head>
      
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative">
        {/* Sélecteur de langue en haut à droite */}
        <div className="absolute top-4 right-4">
          <LanguageSelector />
        </div>
        
        {/* Header */}
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="flex justify-center">
            <InteliaLogo className="w-16 h-16" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            {t.title}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            {t.subtitle}
          </p>
        </div>

        {/* Formulaire */}
        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
            
            {/* Message d'erreur */}
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
                      {t.loginError}
                    </h3>
                    <div className="mt-1 text-sm text-red-700">
                      {error}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Message de succès */}
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

            <div className="space-y-6">
              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  {t.email}
                </label>
                <div className="mt-1">
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={formData.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
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
                  {t.password}
                </label>
                <div className="mt-1 relative">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete={isSignupMode ? "new-password" : "current-password"}
                    required
                    value={formData.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
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

              {/* Confirmation mot de passe (signup seulement) */}
              {isSignupMode && (
                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                    Confirmer le mot de passe
                  </label>
                  <div className="mt-1 relative">
                    <input
                      id="confirmPassword"
                      name="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      autoComplete="new-password"
                      required
                      value={formData.confirmPassword}
                      onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                      onKeyPress={handleKeyPress}
                      className="block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 pr-10 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm transition-colors"
                      placeholder="••••••••"
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center hover:text-gray-600 transition-colors"
                      disabled={isLoading}
                      tabIndex={-1}
                    >
                      {showConfirmPassword ? (
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
              )}

              {/* Options (login seulement) */}
              {!isSignupMode && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <input
                      id="remember-me"
                      name="remember-me"
                      type="checkbox"
                      checked={formData.rememberMe}
                      onChange={(e) => handleInputChange('rememberMe', e.target.checked)}
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
              )}

              {/* Bouton principal */}
              <div>
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={isLoading || !formData.email || !formData.password || (isSignupMode && !formData.confirmPassword)}
                  className="flex w-full justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? (
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>{t.connecting}</span>
                    </div>
                  ) : (
                    isSignupMode ? t.signup : t.login
                  )}
                </button>
              </div>
            </div>

            {/* Séparateur */}
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

              {/* Toggle Login/Signup */}
              <div className="mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setIsSignupMode(!isSignupMode)
                    setError('')
                    setSuccess('')
                    setFormData({
                      email: '',
                      password: '',
                      confirmPassword: '',
                      rememberMe: false
                    })
                  }}
                  className="flex w-full justify-center rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
                >
                  {isSignupMode ? t.login : t.createAccount}
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
                .{' '}
                <br />
                {t.dataRetention}
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