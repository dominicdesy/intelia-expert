'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import type { Language } from '@/types'
import { useTranslation } from '@/lib/languages/i18n'
import { rememberMeUtils } from './page_hooks'
import { Suspense } from 'react'

// Composant qui utilise useSearchParams, wrappé dans Suspense
function SearchParamsHandler({ onAuthStatus }: { onAuthStatus: (status: string | null) => void }) {
  const searchParams = useSearchParams()
  
  useEffect(() => {
    const authStatus = searchParams?.get('auth')
    onAuthStatus(authStatus)
  }, [searchParams, onAuthStatus])
  
  return null
}

function usePageInitializationCore() {
  const { t } = useTranslation()
  
  const [currentLanguage, setCurrentLanguage] = useState<Language>('fr')
  const [isSignupMode, setIsSignupMode] = useState(false)
  const [localError, setLocalError] = useState('')
  const [localSuccess, setLocalSuccess] = useState('')
  const [hasHydrated, setHasHydrated] = useState(false)
  const [authStatusFromUrl, setAuthStatusFromUrl] = useState<string | null>(null)

  // Fonction simple comme ContactModal
  const toggleMode = useCallback(() => {
    setIsSignupMode(prev => !prev)
    setLocalError('')
    setLocalSuccess('')
  }, [])

  // Fonction simple pour changer la langue
  const handleSetCurrentLanguage = useCallback((newLanguage: Language) => {
    setCurrentLanguage(newLanguage)
    // Sauvegarder avec la structure attendue par i18n.ts
    const langData = {
      state: {
        currentLanguage: newLanguage
      }
    }
    localStorage.setItem('intelia-language', JSON.stringify(langData))
  }, [])

  // Callback pour recevoir le statut d'auth depuis l'URL
  const handleAuthStatus = useCallback((status: string | null) => {
    setAuthStatusFromUrl(status)
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

  // Gestion du statut d'auth depuis l'URL
  useEffect(() => {
    if (!authStatusFromUrl) return
    
    if (authStatusFromUrl === 'success') {
      setLocalSuccess(t('auth.success'))
    } else if (authStatusFromUrl === 'error') {
      setLocalError(t('auth.error'))
    } else if (authStatusFromUrl === 'incomplete') {
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
  }, [authStatusFromUrl, t])

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

  return {
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
    toggleMode,
    handleAuthStatus
  }
}

export function usePageInitialization() {
  const coreHook = usePageInitializationCore()
  
  return {
    ...coreHook,
    // Wrapper avec Suspense pour useSearchParams
    SearchParamsWrapper: ({ children }: { children: React.ReactNode }) => (
      <Suspense fallback={null}>
        <SearchParamsHandler onAuthStatus={coreHook.handleAuthStatus} />
        {children}
      </Suspense>
    )
  }
}