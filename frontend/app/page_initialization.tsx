'use client'

import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import type { Language } from '@/types'
import { translations } from './page_translations'
import { rememberMeUtils } from './page_hooks'

export function usePageInitialization() {
  const searchParams = useSearchParams()
  
  // Refs pour éviter les doubles appels
  const hasInitialized = useRef(false)
  const isMounted = useRef(true)
  
  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const [isSignupMode, setIsSignupMode] = useState(false)
  const [localError, setLocalError] = useState('')
  const [localSuccess, setLocalSuccess] = useState('')
  const [hasHydrated, setHasHydrated] = useState(false)

  // ✅ Mémorisation stable des traductions
  const t = useMemo(() => translations[currentLanguage], [currentLanguage])

  // ✅ Fonction toggleMode mémorisée pour éviter les re-renders
  const toggleMode = useCallback(() => {
    console.log('🔄 [UI] Basculement mode:', isSignupMode ? 'signup → login' : 'login → signup')
    setIsSignupMode(prev => !prev)
    setLocalError('')
    setLocalSuccess('')
  }, [isSignupMode])

  // ✅ Fonction setCurrentLanguage stable avec mémorisation
  const handleSetCurrentLanguage = useCallback((newLanguage: Language) => {
    if (currentLanguage !== newLanguage) {
      console.log('🌐 [Language] Changement de langue:', currentLanguage, '→', newLanguage)
      setCurrentLanguage(newLanguage)
      localStorage.setItem('intelia-language', newLanguage)
    }
  }, [currentLanguage])

  // ✅ Effects d'initialisation optimisés avec Remember Me
  useEffect(() => {
    if (!isMounted.current) return
    
    setHasHydrated(true)
    
    if (!hasInitialized.current) {
      hasInitialized.current = true
      console.log('🎯 [Init] Initialisation unique')
      
      // Charger les préférences utilisateur de manière synchrone
      const savedLanguage = localStorage.getItem('intelia-language') as Language
      if (savedLanguage && translations[savedLanguage] && savedLanguage !== currentLanguage) {
        setCurrentLanguage(savedLanguage)
      } else if (!savedLanguage) {
        // Détection de langue navigateur seulement si pas de langue sauvée
        const browserLanguage = navigator.language.substring(0, 2) as Language
        if (translations[browserLanguage] && browserLanguage !== currentLanguage) {
          setCurrentLanguage(browserLanguage)
        }
      }

      // Restaurer EMAIL avec fonction utilitaire - Une seule fois
      const { hasRememberedEmail, lastEmail } = rememberMeUtils.load()
      
      if (hasRememberedEmail && isMounted.current) {
        setLocalSuccess(`Email restauré : ${lastEmail}. Entrez votre mot de passe.`)
        const timer = setTimeout(() => {
          if (isMounted.current) {
            setLocalSuccess('')
          }
        }, 4000)
        
        // Cleanup timer si démontage
        return () => clearTimeout(timer)
      }
    }
  }, []) // ✅ Dépendances vides - ne s'exécute qu'une fois

  // ✅ Gestion URL callback optimisée
  useEffect(() => {
    if (!hasInitialized.current || !isMounted.current) return

    const authStatus = searchParams?.get('auth')
    if (!authStatus) return
    
    console.log('🔗 [URL] Traitement callback auth:', authStatus)
    
    if (authStatus === 'success') {
      setLocalSuccess(t.authSuccess)
    } else if (authStatus === 'error') {
      setLocalError(t.authError)
    } else if (authStatus === 'incomplete') {
      setLocalError(t.authIncomplete)
    }
    
    // Nettoyer l'URL de manière optimisée
    try {
      const url = new URL(window.location.href)
      url.searchParams.delete('auth')
      window.history.replaceState({}, '', url.pathname)
    } catch (error) {
      console.error('❌ [URL] Erreur nettoyage URL:', error)
    }
    
    // Masquer les messages après 3 secondes
    const timer = setTimeout(() => {
      if (isMounted.current) {
        setLocalSuccess('')
        setLocalError('')
      }
    }, 3000)
    
    return () => clearTimeout(timer)
  }, [searchParams, t.authSuccess, t.authError, t.authIncomplete]) // ✅ Dépendances stables

  // ✅ Effet pour bloquer le scroll en mode signup - Optimisé
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
    
    // ✅ Cleanup optimisé au démontage
    return () => {
      document.body.style.overflow = originalBodyOverflow || 'unset'
      document.documentElement.style.overflow = originalDocumentOverflow || 'unset'
    }
  }, [isSignupMode])

  // ✅ Cleanup général au démontage
  useEffect(() => {
    return () => {
      isMounted.current = false
    }
  }, [])

  // ✅ Retour mémorisé pour éviter les re-renders des composants parents
  return useMemo(() => ({
    currentLanguage,
    setCurrentLanguage: handleSetCurrentLanguage,
    t,
    isSignupMode,
    setIsSignupMode,
    localError,
    setLocalError,
    localSuccess,
    setLocalSuccess,
    hasHydrated,
    hasInitialized,
    toggleMode
  }), [
    currentLanguage, 
    handleSetCurrentLanguage,
    t, 
    isSignupMode, 
    localError, 
    localSuccess, 
    hasHydrated, 
    toggleMode
  ])
}