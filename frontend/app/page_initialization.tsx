'use client'

import { useState, useEffect, useRef, useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import type { Language } from '@/types'
import { translations } from './page_translations'
import { rememberMeUtils } from './page_hooks'

export function usePageInitialization() {
  const searchParams = useSearchParams()
  
  // Refs pour éviter les doubles appels
  const hasInitialized = useRef(false)
  
  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const t = useMemo(() => translations[currentLanguage], [currentLanguage])
  
  const [isSignupMode, setIsSignupMode] = useState(false)
  const [localError, setLocalError] = useState('')
  const [localSuccess, setLocalSuccess] = useState('')
  const [hasHydrated, setHasHydrated] = useState(false)

  const toggleMode = () => {
    console.log('🔄 [UI] Basculement mode:', isSignupMode ? 'signup → login' : 'login → signup')
    setIsSignupMode(!isSignupMode)
    setLocalError('')
    setLocalSuccess('')
  }

  // Effects d'initialisation avec Remember Me
  useEffect(() => {
    setHasHydrated(true)
    
    if (!hasInitialized.current) {
      hasInitialized.current = true
      console.log('🎯 [Init] Initialisation unique')
      
      // Charger les préférences utilisateur
      const savedLanguage = localStorage.getItem('intelia-language') as Language
      if (savedLanguage && translations[savedLanguage]) {
        setCurrentLanguage(savedLanguage)
      } else {
        const browserLanguage = navigator.language.substring(0, 2) as Language
        if (translations[browserLanguage]) {
          setCurrentLanguage(browserLanguage)
        }
      }

      // Restaurer EMAIL avec fonction utilitaire
      const { hasRememberedEmail, lastEmail } = rememberMeUtils.load()
      
      if (hasRememberedEmail) {
        setLocalSuccess(`Email restauré : ${lastEmail}. Entrez votre mot de passe.`)
        setTimeout(() => setLocalSuccess(''), 4000)
      }
    }
  }, [])

  // Gestion URL callback
  useEffect(() => {
    if (!hasInitialized.current) return

    const authStatus = searchParams.get('auth')
    if (!authStatus) return
    
    if (authStatus === 'success') {
      setLocalSuccess(t.authSuccess)
    } else if (authStatus === 'error') {
      setLocalError(t.authError)
    } else if (authStatus === 'incomplete') {
      setLocalError(t.authIncomplete)
    }
    
    // Nettoyer l'URL
    const url = new URL(window.location.href)
    url.searchParams.delete('auth')
    window.history.replaceState({}, '', url.pathname)
    
    // Masquer les messages après 3 secondes
    const timer = setTimeout(() => {
      setLocalSuccess('')
      setLocalError('')
    }, 3000)
    
    return () => clearTimeout(timer)
  }, [searchParams, t])

  // Effet pour bloquer le scroll en mode signup
  useEffect(() => {
    if (isSignupMode) {
      document.body.style.overflow = 'hidden'
      document.documentElement.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
      document.documentElement.style.overflow = 'unset'
    }
    
    // Cleanup au démontage
    return () => {
      document.body.style.overflow = 'unset'
      document.documentElement.style.overflow = 'unset'
    }
  }, [isSignupMode])

  return {
    currentLanguage,
    setCurrentLanguage,
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
  }
}