'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import type { Language } from '@/types'
import { useTranslation } from '@/lib/languages/i18n'
import { rememberMeUtils } from './page_hooks'

export function usePageInitialization() {
  const searchParams = useSearchParams()
  
  // PATTERN SIMPLE COMME CONTACTMODAL - Pas de refs complexes
  const { t } = useTranslation()
  
  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const [isSignupMode, setIsSignupMode] = useState(false)
  const [localError, setLocalError] = useState('')
  const [localSuccess, setLocalSuccess] = useState('')
  const [hasHydrated, setHasHydrated] = useState(false)

  // Fonction simple comme ContactModal
  const toggleMode = useCallback(() => {
    setIsSignupMode(prev => !prev)
    setLocalError('')
    setLocalSuccess('')
  }, [])

  // Fonction simple pour changer la langue
  const handleSetCurrentLanguage = useCallback((newLanguage: Language) => {
    setCurrentLanguage(newLanguage)
    // CORRECTION: Sauvegarder avec la structure attendue par i18n.ts
    const langData = {
      state: {
        currentLanguage: newLanguage
      }
    }
    localStorage.setItem('intelia-language', JSON.stringify(langData))
  }, [])

  // Hydratation simple
  useEffect(() => {
    setHasHydrated(true)
    
    // Charger la langue sauvegardée
    try {
      const storedLang = localStorage.getItem('intelia-language')
      if (storedLang) {
        const parsed = JSON.parse(storedLang)
        const savedLanguage = parsed?.state?.currentLanguage
        if (savedLanguage && ['fr', 'en', 'es', 'ar'].includes(savedLanguage)) {
          setCurrentLanguage(savedLanguage)
        }
      }
    } catch (error) {
      console.warn('Erreur lecture langue:', error)
    }

    // Charger RememberMe
    const { rememberMe, lastEmail } = rememberMeUtils.load()
    if (rememberMe && lastEmail) {
      setLocalSuccess(`Email restauré : ${lastEmail}`)
      setTimeout(() => setLocalSuccess(''), 4000)
    }
  }, [])

  // Gestion URL callback - VERSION SIMPLE
  useEffect(() => {
    const authStatus = searchParams?.get('auth')
    if (!authStatus) return
    
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
      console.error('Erreur nettoyage URL:', error)
    }
    
    setTimeout(() => {
      setLocalSuccess('')
      setLocalError('')
    }, 3000)
  }, [searchParams, t])

  // Gestion scroll en mode signup
  useEffect(() => {
    if (isSignupMode) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
    
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isSignupMode])

  // Retour simple comme ContactModal
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
    hasInitialized: { current: true }, // Toujours initialisé en mode simple
    toggleMode
  }), [
    currentLanguage,
    t,
    isSignupMode,
    localError,
    localSuccess,
    hasHydrated,
    handleSetCurrentLanguage,
    toggleMode
  ])
}