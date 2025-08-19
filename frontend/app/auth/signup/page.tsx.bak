// page.tsx - Version Backend API (changements minimaux)

'use client'

import React, { useState, useEffect, useRef, useCallback, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
// 🔄 CHANGEMENT PRINCIPAL: Utiliser le store backend au lieu de Supabase
import { useAuthStore } from '@/lib/stores/auth' // ← Maintenant c'est le store backend
import type { Language, User } from '@/types'

// 🆕 BANNIÈRE TEMPORAIRE pour informer du changement
const BackendMigrationBanner = () => (
  <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
    <div className="flex items-center space-x-2">
      <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span className="text-sm text-green-800 font-medium">
        Service optimisé : Création de compte maintenant plus rapide et fiable
      </span>
    </div>
  </div>
)

const translations = {
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
    close: 'Fermer',
    alreadyHaveAccount: 'Déjà un compte ?',
    authSuccess: 'Connexion réussie !',
    authError: 'Erreur de connexion, veuillez réessayer.',
    authIncomplete: 'Connexion incomplète, veuillez réessayer.',
    sessionCleared: 'Session précédente effacée',
    forceLogout: 'Déconnexion automatique'
  },
  // ... autres langues (en, es, de) - gardez votre code existant
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

// Fonctions de validation (gardez votre code existant)
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

// 🔧 Votre contenu existant devient PageContent (AUCUN CHANGEMENT dans la logique)
function PageContent() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  
  // 🔄 MÊME API - mais maintenant utilise le backend
  const { user, isAuthenticated, isLoading, hasHydrated } = useAuthStore()
  const { login, register, initializeSession } = useAuthStore()

  // 🔧 TOUT LE RESTE DE VOTRE CODE EXISTANT RESTE IDENTIQUE
  // Protection + Remember Me + État local, etc.
  const hasInitialized = useRef(false)
  const hasCheckedAuth = useRef(false)
  const redirectLock = useRef(false)
  const sessionInitialized = useRef(false)

  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const t = translations[currentLanguage]
  
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

  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const passwordInputRef = useRef<HTMLInputElement>(null)

  // 🔧 TOUTES VOS FONCTIONS EXISTANTES RESTENT IDENTIQUES
  // (rememberMeUtils, safeRedirectToChat, handleLogin, handleSignup, etc.)

  // Just for brevity - gardez tout votre code existant pour :
  // - rememberMeUtils
  // - safeRedirectToChat  
  // - useEffect hooks
  // - handleLoginChange
  // - handleSignupChange
  // - validateSignupForm
  // - handleLogin (fonctionne avec backend automatiquement)
  // - handleSignup (fonctionne avec backend automatiquement)
  // - handleKeyPress
  // - handleCloseSignup
  // - toggleMode

  // Le code principal reste exactement le même car l'API du store est identique

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
          
          {/* 🆕 BANNIÈRE INFORMATION BACKEND */}
          <BackendMigrationBanner />
          
          {/* 🔧 RESTE IDENTIQUE - vos boutons, formulaires, etc. */}
          {/* Gardez tout votre JSX existant */}
          
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
                    {isSignupMode ? t.signupError : t.loginError}
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

          {/* 🔧 GARDEZ TOUT VOTRE JSX EXISTANT POUR LES FORMULAIRES */}
          {/* Login form, signup form, etc. - rien ne change */}
          
          <div className="text-center mt-4 p-3 bg-blue-50 rounded-lg">
            <p className="text-xs text-blue-700">
              💡 Nouveau : Service optimisé via notre backend sécurisé pour une meilleure fiabilité
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// 🔧 Export principal reste identique
export default function Page() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <img 
            src="/images/favicon.png" 
            alt="Intelia Logo" 
            className="w-16 h-16 mx-auto mb-4"
          />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement...</p>
        </div>
      </div>
    }>
      <PageContent />
    </Suspense>
  )
}