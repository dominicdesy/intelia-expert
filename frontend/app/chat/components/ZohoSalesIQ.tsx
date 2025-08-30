'use client'

import { useEffect, useRef, useCallback } from 'react'

interface ZohoSalesIQProps {
  user: any
}

// Configuration simplifiée
const CONFIG = {
  MAX_CONFIG_ATTEMPTS: 3,
  CONFIG_RETRY_DELAY: 2000,
  VERIFICATION_DELAY: 3000,
  SCRIPT_TIMEOUT: 15000
} as const

export const ZohoSalesIQ: React.FC<ZohoSalesIQProps> = ({ user }) => {
  const isMountedRef = useRef(true)
  const isInitializedRef = useRef(false)
  const timeoutsRef = useRef<Set<NodeJS.Timeout>>(new Set())

  // Détection de la langue du navigateur
  const getBrowserLanguage = useCallback((): string => {
    if (typeof window === 'undefined') return 'en'
    
    const browserLang = navigator.language || navigator.languages?.[0] || 'en'
    const langCode = browserLang.split('-')[0].toLowerCase()
    
    // Supporter seulement les langues disponibles dans Zoho
    const supportedLanguages = ['en', 'fr', 'es', 'de', 'it']
    return supportedLanguages.includes(langCode) ? langCode : 'en'
  }, [])

  // Utilitaire pour créer des timeouts trackés
  const createTimeout = useCallback((callback: () => void, delay: number): NodeJS.Timeout => {
    const timeout = setTimeout(() => {
      timeoutsRef.current.delete(timeout)
      if (isMountedRef.current) {
        callback()
      }
    }, delay)
    
    timeoutsRef.current.add(timeout)
    return timeout
  }, [])

  // Nettoyage des timers
  const clearAllTimers = useCallback(() => {
    timeoutsRef.current.forEach(clearTimeout)
    timeoutsRef.current.clear()
  }, [])

  // Initialisation de l'objet Zoho
  const initializeZohoObject = useCallback(() => {
    if (typeof window === 'undefined') return

    if (!document.querySelector('#zoho-init-script')) {
      const initScript = document.createElement('script')
      initScript.id = 'zoho-init-script'
      initScript.innerHTML = `
        window.$zoho = window.$zoho || {};
        $zoho.salesiq = $zoho.salesiq || {ready: function(){}};
      `
      document.head.appendChild(initScript)
    }
  }, [])

  // Configuration du widget
  const configureWidget = useCallback((lang: string, attempt: number = 1): void => {
    if (!isMountedRef.current) return

    try {
      const $zoho = (window as any).$zoho
      if (!$zoho?.salesiq?.visitor?.info) {
        throw new Error('API Zoho non disponible')
      }

      // Configuration utilisateur basique
      if (user?.email) {
        const visitorInfo = {
          'Email': user.email,
          'Name': user.name || user.email.split('@')[0],
          'User ID': user.id || 'unknown'
        }
        
        $zoho.salesiq.visitor.info(visitorInfo)
        console.log('Zoho configuré pour:', user.email, 'langue:', lang)
      }

      // Masquer la fenêtre de chat par défaut (bouton flottant seulement)
      createTimeout(() => {
        if (isMountedRef.current) {
          try {
            const chatWindow = document.querySelector('#zsiq_agelif') as HTMLElement
            if (chatWindow) {
              chatWindow.style.display = 'none'
            }
          } catch (error) {
            console.warn('Erreur masquage chat:', error)
          }
        }
      }, CONFIG.VERIFICATION_DELAY)

    } catch (error) {
      console.error(`Erreur configuration Zoho (tentative ${attempt}):`, error)

      if (attempt < CONFIG.MAX_CONFIG_ATTEMPTS && isMountedRef.current) {
        createTimeout(() => {
          if (isMountedRef.current) {
            configureWidget(lang, attempt + 1)
          }
        }, CONFIG.CONFIG_RETRY_DELAY)
      }
    }
  }, [user, createTimeout])

  // Chargement du script Zoho
  const loadZohoScript = useCallback(async (lang: string): Promise<void> => {
    if (!isMountedRef.current || typeof window === 'undefined') return

    const widgetBaseUrl = process.env.NEXT_PUBLIC_ZOHO_WIDGET_BASE_URL
    const widgetId = process.env.NEXT_PUBLIC_ZOHO_WIDGET_ID
    
    if (!widgetBaseUrl || !widgetId) {
      console.error('Variables Zoho manquantes')
      return
    }

    return new Promise((resolve, reject) => {
      // Initialiser l'objet $zoho avant le script
      initializeZohoObject()

      const script = document.createElement('script')
      script.id = 'zsiqscript'
      script.async = true
      script.defer = true
      script.src = `${widgetBaseUrl}?wc=${widgetId}&locale=${lang}`

      const timeout = createTimeout(() => {
        if (isMountedRef.current) {
          script.remove()
          reject(new Error('Timeout chargement script Zoho'))
        }
      }, CONFIG.SCRIPT_TIMEOUT)

      script.onload = () => {
        clearTimeout(timeout)
        console.log('Script Zoho chargé avec succès')
        
        // Configurer après chargement
        createTimeout(() => {
          if (isMountedRef.current) {
            configureWidget(lang)
          }
        }, 1000)
        
        resolve()
      }

      script.onerror = () => {
        clearTimeout(timeout)
        script.remove()
        reject(new Error('Erreur chargement script Zoho'))
      }

      document.head.appendChild(script)
    })
  }, [initializeZohoObject, createTimeout, configureWidget])

  // Initialisation principale
  const initializeWidget = useCallback(async (): Promise<void> => {
    if (!isMountedRef.current || !user?.email || isInitializedRef.current) return

    isInitializedRef.current = true
    const browserLang = getBrowserLanguage()

    console.log('Initialisation Zoho avec langue navigateur:', browserLang)

    try {
      await loadZohoScript(browserLang)
    } catch (error) {
      console.error('Erreur initialisation Zoho:', error)
      isInitializedRef.current = false
    }
  }, [user, getBrowserLanguage, loadZohoScript])

  // Effect principal - se déclenche seulement une fois
  useEffect(() => {
    if (!user?.email) return

    initializeWidget()
  }, [user?.email, initializeWidget])

  // Cleanup au unmount
  useEffect(() => {
    isMountedRef.current = true

    return () => {
      isMountedRef.current = false
      isInitializedRef.current = false
      clearAllTimers()
      
      // Nettoyer le script si présent
      const script = document.querySelector('#zsiqscript')
      if (script) {
        script.remove()
      }
    }
  }, [clearAllTimers])

  return null
}

// Types TypeScript
declare global {
  interface Window {
    $zoho?: {
      salesiq?: {
        ready?: () => void
        visitor?: {
          info: (data: any) => void
        }
        floatwindow?: {
          visible: (action: 'show' | 'hide') => void
        }
      }
    }
  }
}