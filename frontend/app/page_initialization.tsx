'use client'

import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import type { Language } from '@/types'
import { useTranslation } from '@/lib/languages/i18n'
import { rememberMeUtils } from './page_hooks'

// 🎯 NOUVEAU: Traductions critiques par défaut pour éviter le FOUC
const criticalTranslations = {
  fr: {
    'page.title': 'Connexion à Intelia Expert',
    'auth.success': 'Connexion réussie',
    'auth.error': 'Erreur de connexion',
    'auth.incomplete': 'Connexion incomplète',
    'email': 'Email',
    'password': 'Mot de passe',
    'loading': 'Chargement...'
  },
  en: {
    'page.title': 'Login to Intelia Expert',
    'auth.success': 'Login successful',
    'auth.error': 'Connection error',
    'auth.incomplete': 'Incomplete connection',
    'email': 'Email',
    'password': 'Password',
    'loading': 'Loading...'
  },
  es: {
    'page.title': 'Iniciar sesión en Intelia Expert',
    'auth.success': 'Inicio de sesión exitoso',
    'auth.error': 'Error de conexión',
    'auth.incomplete': 'Conexión incompleta',
    'email': 'Correo electrónico',
    'password': 'Contraseña',
    'loading': 'Cargando...'
  },
  ar: {
    'page.title': 'تسجيل الدخول إلى Intelia Expert',
    'auth.success': 'تم تسجيل الدخول بنجاح',
    'auth.error': 'خطأ في الاتصال',
    'auth.incomplete': 'اتصال غير مكتمل',
    'email': 'البريد الإلكتروني',
    'password': 'كلمة المرور',
    'loading': 'جاري التحميل...'
  }
}

// 🎯 NOUVEAU: États de chargement pour le skeleton
type LoadingState = 'initial' | 'hydrating' | 'loading-translations' | 'ready'

export function usePageInitialization() {
  const searchParams = useSearchParams()
  
  // Refs pour éviter les doubles appels
  const hasInitialized = useRef(false)
  const isMounted = useRef(true)
  const translationsReady = useRef(false)
  
  // 🎯 NOUVEAU: État de chargement unifié
  const [loadingState, setLoadingState] = useState<LoadingState>('initial')
  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const [isSignupMode, setIsSignupMode] = useState(false)
  const [localError, setLocalError] = useState('')
  const [localSuccess, setLocalSuccess] = useState('')

  // Hook de traductions avec fallback
  const { t: originalT } = useTranslation()

  // 🎯 NOUVEAU: Fonction t avec fallback anti-FOUC
  const t = useCallback((key: string): string => {
    // Si les traductions ne sont pas prêtes, utiliser les traductions critiques
    if (!translationsReady.current && criticalTranslations[currentLanguage]?.[key]) {
      return criticalTranslations[currentLanguage][key]
    }
    // Sinon, utiliser les vraies traductions avec fallback
    return originalT(key) || criticalTranslations[currentLanguage]?.[key] || key
  }, [originalT, currentLanguage])

  // Fonction toggleMode stable
  const toggleMode = useCallback(() => {
    console.log('🔄 [UI] Basculement mode')
    setIsSignupMode(prev => {
      console.log('🔄 [UI] Mode:', !prev ? 'login → signup' : 'signup → login')
      return !prev
    })
    setLocalError('')
    setLocalSuccess('')
  }, [])

  // Fonction setCurrentLanguage stable avec transition de state
  const handleSetCurrentLanguage = useCallback((newLanguage: Language) => {
    setCurrentLanguage(prev => {
      if (prev !== newLanguage) {
        console.log('🌐 [Language] Changement:', prev, '→', newLanguage)
        localStorage.setItem('intelia-language', newLanguage)
        // 🎯 NOUVEAU: Déclencher un re-render pour mettre à jour les traductions critiques
        setLoadingState(current => current === 'ready' ? 'loading-translations' : current)
        return newLanguage
      }
      return prev
    })
  }, [])

  // 🎯 NOUVEAU: Effect pour gérer les états de chargement
  useEffect(() => {
    if (!isMounted.current) return

    const initializeApp = async () => {
      console.log('🎯 [Init] Début initialisation')
      setLoadingState('hydrating')

      if (!hasInitialized.current) {
        hasInitialized.current = true
        
        // Charger les préférences de manière synchrone
        const supportedLanguages = ['fr', 'en', 'es', 'ar']
        const savedLanguage = localStorage.getItem('intelia-language') as Language
        
        if (savedLanguage && supportedLanguages.includes(savedLanguage)) {
          setCurrentLanguage(savedLanguage)
        } else {
          const browserLanguage = navigator.language.substring(0, 2) as Language
          if (supportedLanguages.includes(browserLanguage)) {
            setCurrentLanguage(browserLanguage)
          }
        }

        // Gérer Remember Me
        const { rememberMe, lastEmail } = rememberMeUtils.load()
        if (rememberMe && lastEmail && isMounted.current) {
          setLocalSuccess(`Email restauré : ${lastEmail}. Entrez votre mot de passe.`)
          setTimeout(() => {
            if (isMounted.current) setLocalSuccess('')
          }, 4000)
        }

        setLoadingState('loading-translations')
        
        // 🎯 NOUVEAU: Simuler un petit délai pour que les vraies traductions se chargent
        setTimeout(() => {
          if (isMounted.current) {
            translationsReady.current = true
            setLoadingState('ready')
            console.log('✅ [Init] Application prête')
          }
        }, 100) // Délai minimal pour éviter le flash
      }
    }

    initializeApp()
  }, [])

  // Gestion URL callback optimisée
  useEffect(() => {
    if (loadingState !== 'ready' || !isMounted.current) return

    const authStatus = searchParams?.get('auth')
    if (!authStatus) return
    
    console.log('🔗 [URL] Traitement callback auth:', authStatus)
    
    // Utiliser les traductions avec fallback
    if (authStatus === 'success') {
      setLocalSuccess(t('auth.success'))
    } else if (authStatus === 'error') {
      setLocalError(t('auth.error'))
    } else if (authStatus === 'incomplete') {
      setLocalError(t('auth.incomplete'))
    }
    
    // Nettoyer l'URL
    try {
      const url = new URL(window.location.href)
      url.searchParams.delete('auth')
      window.history.replaceState({}, '', url.pathname)
    } catch (error) {
      console.error('❌ [URL] Erreur nettoyage URL:', error)
    }
    
    const timer = setTimeout(() => {
      if (isMounted.current) {
        setLocalSuccess('')
        setLocalError('')
      }
    }, 3000)
    
    return () => clearTimeout(timer)
  }, [searchParams, t, loadingState])

  // 🎯 NOUVEAU: Effect pour gérer les changements de langue après l'initialisation
  useEffect(() => {
    if (loadingState === 'loading-translations') {
      const timer = setTimeout(() => {
        if (isMounted.current) {
          translationsReady.current = true
          setLoadingState('ready')
        }
      }, 50) // Délai minimal pour la transition
      
      return () => clearTimeout(timer)
    }
  }, [loadingState])

  // Effet pour bloquer le scroll en mode signup
  useEffect(() => {
    const originalBodyOverflow = document.body.style.overflow
    const originalDocumentOverflow = document.documentElement.style.overflow
    
    if (isSignupMode) {
      document.body.style.overflow = 'hidden'
      document.documentElement.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = originalBodyOverflow || 'unset'
      document.documentElement.style.overflow = originalDocumentOverflow || 'unset'
    }
    
    return () => {
      document.body.style.overflow = originalBodyOverflow || 'unset'
      document.documentElement.style.overflow = originalDocumentOverflow || 'unset'
    }
  }, [isSignupMode])

  // Cleanup général
  useEffect(() => {
    return () => {
      isMounted.current = false
    }
  }, [])

  // 🎯 NOUVEAU: Computed values pour les états de chargement
  const computedStates = useMemo(() => {
    return {
      hasHydrated: loadingState !== 'initial',
      hasInitialized: { current: loadingState === 'ready' },
      isLoadingTranslations: loadingState === 'loading-translations',
      showSkeleton: loadingState === 'hydrating' || loadingState === 'loading-translations'
    }
  }, [loadingState])

  return useMemo(() => ({
    currentLanguage,
    setCurrentLanguage: handleSetCurrentLanguage,
    t, // 🎯 NOUVEAU: Fonction t avec fallback anti-FOUC
    isSignupMode,
    setIsSignupMode,
    localError,
    setLocalError,
    localSuccess,
    setLocalSuccess,
    toggleMode,
    loadingState, // 🎯 NOUVEAU: État de chargement unifié
    ...computedStates // 🎯 NOUVEAU: États calculés
  }), [
    currentLanguage,
    t, // Inclure t car il dépend de currentLanguage et translationsReady
    isSignupMode,
    localError,
    localSuccess,
    handleSetCurrentLanguage,
    toggleMode,
    loadingState,
    computedStates
  ])
}