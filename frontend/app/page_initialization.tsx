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

  // ✅ CORRECTION : toggleMode sans dépendances changeantes
  const toggleMode = useCallback(() => {
    console.log('🔄 [UI] Basculement mode')
    setIsSignupMode(prev => {
      console.log('🔄 [UI] Mode:', !prev ? 'login → signup' : 'signup → login')
      return !prev
    })
    setLocalError('')
    setLocalSuccess('')
  }, []) // ✅ Pas de dépendances - fonction stable

  // ✅ CORRECTION : setCurrentLanguage stable sans dépendances changeantes
  const handleSetCurrentLanguage = useCallback((newLanguage: Language) => {
    setCurrentLanguage(prev => {
      if (prev !== newLanguage) {
        console.log('🌐 [Language] Changement de langue:', prev, '→', newLanguage)
        localStorage.setItem('intelia-language', newLanguage)
        return newLanguage
      }
      return prev
    })
  }, []) // ✅ Pas de dépendances - fonction stable

  // ✅ Effects d'initialisation optimisés avec Remember Me
  useEffect(() => {
    if (!isMounted.current) return
    
    setHasHydrated(true)
    
    if (!hasInitialized.current) {
      hasInitialized.current = true
      console.log('🎯 [Init] Initialisation unique')
      
      // Charger les préférences utilisateur de manière synchrone
      const savedLanguage = localStorage.getItem('intelia-language') as Language
      if (savedLanguage && translations[savedLanguage]) {
        setCurrentLanguage(savedLanguage)
      } else {
        // Détection de langue navigateur seulement si pas de langue sauvée
        const browserLanguage = navigator.language.substring(0, 2) as Language
        if (translations[browserLanguage]) {
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

  // ✅ CORRECTION : Retour avec fonctions stables
  return useMemo(() => ({
    currentLanguage,
    setCurrentLanguage: handleSetCurrentLanguage, // ✅ Fonction stable
    t,
    isSignupMode,
    setIsSignupMode,
    localError,
    setLocalError,
    localSuccess,
    setLocalSuccess,
    hasHydrated,
    hasInitialized,
    toggleMode // ✅ Fonction stable
  }), [
    currentLanguage, 
    t, 
    isSignupMode, 
    localError, 
    localSuccess, 
    hasHydrated,
    handleSetCurrentLanguage, // ✅ Stable
    toggleMode // ✅ Stable
  ])
}