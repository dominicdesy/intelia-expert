'use client'

import React, { useState, useEffect, useRef, useCallback, Suspense, useMemo } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'
import type { Language, User } from '@/types'

// Import des hooks et utilitaires
import { 
  useCountries, 
  useCountryCodeMap, 
  translations, 
  validateEmail, 
  validatePassword, 
  validatePhone, 
  rememberMeUtils 
} from './page_hooks'

// Import des composants
import { 
  InteliaLogo, 
  LanguageSelector, 
  CountrySelector, 
  AlertMessage, 
  PasswordInput, 
  PasswordMatchIndicator, 
  LoadingSpinner, 
  AuthFooter 
} from './page_components'

// Contenu principal de la page
function PageContent() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  
  const { user, isAuthenticated, isLoading, hasHydrated } = useAuthStore()
  const { login, register, initializeSession } = useAuthStore()

  // Hook pour charger les pays
  const { countries, loading: countriesLoading, usingFallback } = useCountries()
  
  // Créer le mapping des codes téléphoniques dynamiquement
  const countryCodeMap = useCountryCodeMap(countries)

  // Refs pour éviter les doubles appels
  const hasInitialized = useRef(false)
  const hasCheckedAuth = useRef(false)
  const redirectLock = useRef(false)
  const sessionInitialized = useRef(false)

  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const t = useMemo(() => translations[currentLanguage], [currentLanguage])
  
  const [isSignupMode, setIsSignupMode] = useState(false)
  const [localError, setLocalError] = useState('')
  const [localSuccess, setLocalSuccess] = useState('')
  
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

  const safeRedirectToChat = useCallback(() => {
    if (redirectLock.current) {
      console.log('🔒 [Redirect] Redirection déjà en cours, skip')
      return
    }

    redirectLock.current = true
    console.log('🚀 [Redirect] Redirection vers /chat...')
    
    try {
      router.push('/chat')
    } catch (error) {
      console.error('❌ [Redirect] Erreur redirection:', error)
      redirectLock.current = false
    }
  }, [router])

  // Gestion des changements de formulaires
  const handleLoginChange = (field: keyof typeof loginData, value: string | boolean) => {
    setLoginData(prev => ({ ...prev, [field]: value }))
    setLocalError('')
  }

  const handleSignupChange = (field: keyof typeof signupData, value: string) => {
    setSignupData(prev => {
      const newData = { ...prev, [field]: value }
      
      // Auto-remplir l'indicatif pays quand le pays change
      if (field === 'country' && value && countryCodeMap[value]) {
        console.log('🏳️ [Country] Auto-remplissage code pays:', value, '->', countryCodeMap[value])
        newData.countryCode = countryCodeMap[value]
      }
      
      return newData
    })
    setLocalError('')
  }

  const validateSignupForm = (): string | null => {
    if (!signupData.email) return t.emailRequired
    if (!validateEmail(signupData.email)) return t.emailInvalid
    if (!signupData.password) return t.passwordRequired
    
    const passwordValidation = validatePassword(signupData.password)
    if (!passwordValidation.isValid) {
      return t.passwordTooShort
    }
    
    if (signupData.password !== signupData.confirmPassword) return t.passwordMismatch
    if (!signupData.firstName.trim()) return t.firstNameRequired
    if (!signupData.lastName.trim()) return t.lastNameRequired
    if (!signupData.country) return t.countryRequired
    
    if (!validatePhone(signupData.countryCode, signupData.areaCode, signupData.phoneNumber)) {
      return t.phoneInvalid
    }
    
    return null
  }

  // Gestion de la connexion
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError('')
    setLocalSuccess('')

    if (!loginData.email) {
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

    try {
      console.log('🔄 [Login] Tentative connexion...')
      
      await login(loginData.email, loginData.password)
      
      // Sauvegarder remember me
      rememberMeUtils.save(loginData.email, loginData.rememberMe)
      
      setLocalSuccess(t.authSuccess)
      console.log('✅ [Login] Connexion réussie')
      
      // Redirection automatique après succès
      setTimeout(() => {
        safeRedirectToChat()
      }, 1000)
      
    } catch (error: any) {
      console.error('❌ [Login] Erreur connexion:', error)
      setLocalError(error?.message || t.authError)
    }
  }

  // Gestion de l'inscription
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError('')
    setLocalSuccess('')

    const validationError = validateSignupForm()
    if (validationError) {
      setLocalError(validationError)
      return
    }

    try {
      console.log('🔄 [Signup] Tentative création compte...')
      
      const userData = {
        email: signupData.email,
        firstName: signupData.firstName,
        lastName: signupData.lastName,
        linkedinProfile: signupData.linkedinProfile,
        country: signupData.country,
        countryCode: signupData.countryCode,
        areaCode: signupData.areaCode,
        phoneNumber: signupData.phoneNumber,
        companyName: signupData.companyName,
        companyWebsite: signupData.companyWebsite,
        companyLinkedin: signupData.companyLinkedin
      }
      
      await register(signupData.email, signupData.password, userData)
      
      setLocalSuccess(t.accountCreated)
      console.log('✅ [Signup] Création compte réussie')
      
      // Retour au mode login après création
      setTimeout(() => {
        setIsSignupMode(false)
        setLoginData(prev => ({ ...prev, email: signupData.email }))
      }, 2000)
      
    } catch (error: any) {
      console.error('❌ [Signup] Erreur création compte:', error)
      setLocalError(error?.message || t.signupError)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (isSignupMode) {
        handleSignup(e as any)
      } else {
        handleLogin(e as any)
      }
    }
  }

  const toggleMode = () => {
    setIsSignupMode(!isSignupMode)
    setLocalError('')
    setLocalSuccess('')
  }

  // Effects d'initialisation
  useEffect(() => {
    if (!hasInitialized.current) {
      hasInitialized.current = true
      
      // Charger remember me
      const { rememberMe, lastEmail } = rememberMeUtils.load()
      if (rememberMe && lastEmail) {
        setLoginData(prev => ({
          ...prev,
          email: lastEmail,
          rememberMe: true
        }))
      }
    }
  }, [])

  useEffect(() => {
    if (!hasHydrated) return
    
    if (!sessionInitialized.current) {
      sessionInitialized.current = true
      console.log('🔄 [Session] Initialisation unique de la session')
      initializeSession()
    }
  }, [hasHydrated, initializeSession])

  useEffect(() => {
    if (!hasHydrated) return
    
    if (!hasCheckedAuth.current && !isLoading) {
      hasCheckedAuth.current = true
      console.log('🔍 [Auth] Vérification unique de l\'authentification')
      
      if (isAuthenticated && user) {
        console.log('✅ [Auth] Utilisateur connecté, redirection...')
        safeRedirectToChat()
      } else {
        console.log('❌ [Auth] Utilisateur non connecté')
      }
    }
  }, [hasHydrated, isLoading, isAuthenticated, user, safeRedirectToChat])

  // Affichage loading pendant l'hydratation
  if (!hasHydrated || isLoading) {
    return <LoadingSpinner />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 relative">
      <div className="absolute top-4 right-4">
        <LanguageSelector onLanguageChange={setCurrentLanguage} currentLanguage={currentLanguage} />
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
          
          {/* Statut du chargement des pays */}
          {usingFallback && !countriesLoading && isSignupMode && (
            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center space-x-2">
                <svg className="w-4 h-4 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <span className="text-sm text-yellow-800">
                  {t.limitedCountryList}
                </span>
              </div>
            </div>
          )}

          {/* Messages d'erreur et succès */}
          {localError && (
            <AlertMessage 
              type="error" 
              title={isSignupMode ? t.signupError : t.loginError} 
              message={localError} 
            />
          )}

          {localSuccess && (
            <AlertMessage 
              type="success" 
              title="" 
              message={localSuccess} 
            />
          )}

          {/* FORMULAIRE DE CONNEXION */}
          {!isSignupMode && (
            <form onSubmit={handleLogin} onKeyPress={handleKeyPress}>
              <div className="space-y-6">
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
                      value={loginData.email}
                      onChange={(e) => handleLoginChange('email', e.target.value)}
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                    {t.password}
                  </label>
                  <div className="mt-1">
                    <PasswordInput
                      id="password"
                      name="password"
                      value={loginData.password}
                      onChange={(e) => handleLoginChange('password', e.target.value)}
                      autoComplete="current-password"
                      required
                    />
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
                    />
                    <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-900">
                      {t.rememberMe}
                    </label>
                  </div>

                  <div className="text-sm">
                    <Link href="/forgot-password" className="font-medium text-blue-600 hover:text-blue-500">
                      {t.forgotPassword}
                    </Link>
                  </div>
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="flex w-full justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? t.connecting : t.login}
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* FORMULAIRE D'INSCRIPTION */}
          {isSignupMode && (
            <form onSubmit={handleSignup} onKeyPress={handleKeyPress}>
              <div className="space-y-6">
                {/* Section Informations personnelles */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">{t.personalInfo}</h3>
                  
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        {t.firstName} <span className="text-red-500">{t.required}</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={signupData.firstName}
                        onChange={(e) => handleSignupChange('firstName', e.target.value)}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        {t.lastName} <span className="text-red-500">{t.required}</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={signupData.lastName}
                        onChange={(e) => handleSignupChange('lastName', e.target.value)}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t.linkedinProfile} {t.optional}
                    </label>
                    <input
                      type="url"
                      value={signupData.linkedinProfile}
                      onChange={(e) => handleSignupChange('linkedinProfile', e.target.value)}
                      placeholder="https://linkedin.com/in/votre-profil"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                </div>

                {/* Section Contact */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">{t.contact}</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t.email} <span className="text-red-500">{t.required}</span>
                    </label>
                    <input
                      type="email"
                      required
                      value={signupData.email}
                      onChange={(e) => handleSignupChange('email', e.target.value)}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>

                  {/* Sélection pays améliorée */}
                  <CountrySelector
                    countries={countries}
                    countriesLoading={countriesLoading}
                    usingFallback={usingFallback}
                    value={signupData.country}
                    onChange={(value) => handleSignupChange('country', value)}
                    t={t}
                  />

                  {/* Téléphone optionnel */}
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t.phoneNumber} {t.optional}
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">{t.countryCode}</label>
                        <input
                          type="text"
                          placeholder="+1"
                          value={signupData.countryCode}
                          onChange={(e) => handleSignupChange('countryCode', e.target.value)}
                          className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">{t.areaCode}</label>
                        <input
                          type="text"
                          placeholder="514"
                          value={signupData.areaCode}
                          onChange={(e) => handleSignupChange('areaCode', e.target.value)}
                          className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">{t.phoneNumber}</label>
                        <input
                          type="text"
                          placeholder="1234567"
                          value={signupData.phoneNumber}
                          onChange={(e) => handleSignupChange('phoneNumber', e.target.value)}
                          className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Section Entreprise */}
                <div className="border-b border-gray-200 pb-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">{t.company}</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t.companyName} {t.optional}
                    </label>
                    <input
                      type="text"
                      value={signupData.companyName}
                      onChange={(e) => handleSignupChange('companyName', e.target.value)}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t.companyWebsite} {t.optional}
                    </label>
                    <input
                      type="url"
                      value={signupData.companyWebsite}
                      onChange={(e) => handleSignupChange('companyWebsite', e.target.value)}
                      placeholder="https://votre-entreprise.com"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t.companyLinkedin} {t.optional}
                    </label>
                    <input
                      type="url"
                      value={signupData.companyLinkedin}
                      onChange={(e) => handleSignupChange('companyLinkedin', e.target.value)}
                      placeholder="https://linkedin.com/company/votre-entreprise"
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                </div>

                {/* Section Mot de passe */}
                <div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t.password} <span className="text-red-500">{t.required}</span>
                    </label>
                    <div className="mt-1">
                      <PasswordInput
                        value={signupData.password}
                        onChange={(e) => handleSignupChange('password', e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      {t.confirmPassword} <span className="text-red-500">{t.required}</span>
                    </label>
                    <div className="mt-1">
                      <PasswordInput
                        value={signupData.confirmPassword}
                        onChange={(e) => handleSignupChange('confirmPassword', e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  {/* Indicateur de correspondance des mots de passe */}
                  <PasswordMatchIndicator 
                    password={signupData.password} 
                    confirmPassword={signupData.confirmPassword} 
                  />
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="flex w-full justify-center rounded-md border border-transparent bg-green-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? t.creating : t.createAccount}
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* Boutons de navigation */}
          <div className="mt-6 text-center">
            {!isSignupMode ? (
              <div>
                <p className="text-sm text-gray-600">
                  {t.newToIntelia}{' '}
                  <button
                    onClick={toggleMode}
                    className="font-medium text-blue-600 hover:text-blue-500"
                  >
                    {t.createAccount}
                  </button>
                </p>
              </div>
            ) : (
              <div>
                <p className="text-sm text-gray-600">
                  {t.alreadyHaveAccount}{' '}
                  <button
                    onClick={toggleMode}
                    className="font-medium text-blue-600 hover:text-blue-500"
                  >
                    {t.backToLogin}
                  </button>
                </p>
              </div>
            )}
          </div>

          {/* Footer */}
          <AuthFooter t={t} />
        </div>
      </div>
    </div>
  )
}

// Export principal avec Suspense
export default function Page() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <PageContent />
    </Suspense>
  )
}