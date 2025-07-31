'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import type { Language } from '@/types'

const translations = {
  fr: {
    title: 'Intelia Expert',
    email: 'Email',
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
    needHelp: 'Besoin d\'aide ?',
    contactSupport: 'Contactez le support',
    createAccount: 'Créer un compte',
    authSuccess: 'Connexion réussie ! Bienvenue.',
    authError: 'Erreur de connexion, veuillez réessayer.',
    authIncomplete: 'Connexion incomplète, veuillez réessayer.'
  },
  en: {
    title: 'Intelia Expert',
    email: 'Email',
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
    needHelp: 'Need help?',
    contactSupport: 'Contact support',
    createAccount: 'Create account',
    authSuccess: 'Successfully logged in! Welcome.',
    authError: 'Login error, please try again.',
    authIncomplete: 'Incomplete login, please try again.'
  }
}

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
    { code: 'en' as Language, name: 'English', flag: '🇺🇸' }
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

export default function LoginPage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // 🚨 ÉTAT LOCAL SIMPLE - PAS DE ZUSTAND
  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const [isLoading, setIsLoading] = useState(false)
  const [localError, setLocalError] = useState('')
  const [localSuccess, setLocalSuccess] = useState('')
  
  const [loginData, setLoginData] = useState({
    email: '',
    password: '',
    rememberMe: false
  })

  const [showPassword, setShowPassword] = useState(false)
  const t = translations[currentLanguage]

  // 🚨 INITIALISATION ULTRA-SIMPLE
  useEffect(() => {
    console.log('🔧 [Minimal] Initialisation ultra-simple')
    
    // Charger préférences de base
    const savedLanguage = localStorage.getItem('intelia-language') as Language
    if (savedLanguage && translations[savedLanguage]) {
      setCurrentLanguage(savedLanguage)
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

  // 🚨 GESTION URL CALLBACK SIMPLE
  useEffect(() => {
    const authStatus = searchParams.get('auth')
    if (!authStatus) return
    
    if (authStatus === 'success') {
      setLocalSuccess(t.authSuccess)
      router.push('/chat')
    } else if (authStatus === 'error') {
      setLocalError(t.authError)  
    } else if (authStatus === 'incomplete') {
      setLocalError(t.authIncomplete)
    }
    
    // Nettoyer URL
    const url = new URL(window.location.href)
    url.searchParams.delete('auth')
    window.history.replaceState({}, '', url.pathname)
  }, [searchParams, t, router])

  const handleLanguageChange = (newLanguage: Language) => {
    setCurrentLanguage(newLanguage)
    localStorage.setItem('intelia-language', newLanguage)
  }

  const handleLoginChange = (field: string, value: string | boolean) => {
    setLoginData(prev => ({ ...prev, [field]: value }))
    if (localError) setLocalError('')
    if (localSuccess) setLocalSuccess('')
  }

  // 🚨 LOGIN SIMPLIFIÉ - DIRECT VERS SUPABASE
  const handleLogin = async () => {
    setLocalError('')
    setLocalSuccess('')
    setIsLoading(true)
    
    try {
      if (!loginData.email.trim()) {
        setLocalError(t.emailRequired)
        return
      }
      
      if (!validateEmail(loginData.email)) {
        setLocalError(t.emailInvalid)
        return
      }
      
      if (!loginData.password) {
        setLocalError(t.passwordRequired)
        return
      }

      if (loginData.password.length < 6) {
        setLocalError(t.passwordTooShort)
        return
      }

      console.log('🔐 [Minimal] Tentative connexion directe:', loginData.email)
      
      // 🚨 IMPORT DYNAMIQUE POUR ÉVITER LA BOUCLE
      const { createClient } = await import('@supabase/supabase-js')
      
      const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
      )

      const { data, error } = await supabase.auth.signInWithPassword({
        email: loginData.email.trim(),
        password: loginData.password,
      })

      if (error) {
        console.error('❌ [Minimal] Erreur Supabase:', error)
        setLocalError(error.message || 'Erreur de connexion')
        return
      }

      if (data.user) {
        console.log('✅ [Minimal] Connexion réussie:', data.user.email)
        
        // Gestion "Se souvenir de moi"
        if (loginData.rememberMe) {
          localStorage.setItem('intelia-remember-me', 'true')
          localStorage.setItem('intelia-last-email', loginData.email.trim())
        } else {
          localStorage.removeItem('intelia-remember-me')
          localStorage.removeItem('intelia-last-email')
        }
        
        // 🚨 REDIRECTION SIMPLE ET SÉCURISÉE
        setLocalSuccess('Connexion réussie ! Redirection...')
        
        // Attendre un peu avant redirection pour éviter les conflits
        setTimeout(() => {
          console.log('🚀 [Minimal] Redirection vers /chat')
          
          try {
            // UNE SEULE redirection, pas de setTimeout multiples
            window.location.href = '/chat'
          } catch (error) {
            console.error('❌ [Minimal] Erreur redirection:', error)
            setLocalError('Erreur de redirection. Essayez de naviguer manuellement vers /chat')
          }
        }, 1000)
        
        return
      }

      setLocalError('Connexion échouée')
      
    } catch (error: any) {
      console.error('❌ [Minimal] Erreur connexion:', error)
      setLocalError(error.message || 'Erreur de connexion')
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      handleLogin()
    }
  }

  // 🚨 AFFICHAGE DIRECT - PAS DE CONDITIONS COMPLEXES
  return (
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

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
          
          {/* Messages d'erreur et succès */}
          {localError && (
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
                    {localError}
                  </div>
                </div>
              </div>
            </div>
          )}

          {localSuccess && (
            <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <div className="text-sm text-green-700">
                    {localSuccess}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Formulaire de connexion SIMPLIFIÉ */}
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

          {/* Section de création de compte */}
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
              <Link
                href="/auth/signup"
                className="flex w-full justify-center rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
              >
                {t.createAccount}
              </Link>
            </div>
          </div>

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
  )
}