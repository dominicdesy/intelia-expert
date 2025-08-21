'use client'

import { useEffect, useRef, useCallback } from 'react'

interface ZohoSalesIQProps {
  user: any
  language: string
}

// Interface pour l'état du widget optimisé
interface WidgetState {
  isInitialized: boolean
  isConfigured: boolean
  isVisible: boolean
  sessionLanguage: string | null
  lastVerification: number
  verificationCount: number
  scriptLoaded: boolean
}

// Configuration des constantes optimisées
const CONFIG = {
  MAX_CONFIG_ATTEMPTS: 5,
  CONFIG_RETRY_DELAY: 1000,
  VERIFICATION_DEBOUNCE: 500,
  VERIFICATION_INTERVAL: 3000,
  MAX_VERIFICATION_ATTEMPTS: 10,
  SCRIPT_TIMEOUT: 15000,
  CIRCUIT_BREAKER_THRESHOLD: 3,
  BACKOFF_MULTIPLIER: 1.5,
  DOM_OBSERVER_DELAY: 500
} as const

// 🛡️ NOUVELLE FONCTION UTILITAIRE SÉCURISÉE pour éviter l'erreur includes
const hasZohoClass = (element: Element): boolean => {
  try {
    // Vérification sécurisée avec gestion d'erreurs
    const classString = typeof element.className === 'string' 
      ? element.className 
      : element.className?.toString() || ''
    
    return classString.includes('zsiq') || classString.includes('siq-')
  } catch (error) {
    console.warn('⚠️ [ZohoSalesIQ] Erreur vérification classe:', error)
    return false
  }
}

// 🛡️ FONCTION UTILITAIRE pour vérifier les IDs Zoho
const hasZohoId = (element: Element): boolean => {
  try {
    return element.id?.includes('zsiq') || false
  } catch (error) {
    console.warn('⚠️ [ZohoSalesIQ] Erreur vérification ID:', error)
    return false
  }
}

export const ZohoSalesIQ: React.FC<ZohoSalesIQProps> = ({ user, language }) => {
  // État centralisé du widget
  const widgetStateRef = useRef<WidgetState>({
    isInitialized: false,
    isConfigured: false,
    isVisible: false,
    sessionLanguage: null,
    lastVerification: 0,
    verificationCount: 0,
    scriptLoaded: false
  })

  // Refs pour la gestion des timers et contrôles
  const timeoutsRef = useRef<Set<NodeJS.Timeout>>(new Set())
  const intervalsRef = useRef<Set<NodeJS.Timeout>>(new Set())
  const isMountedRef = useRef(true)
  const verificationTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const configurationLockRef = useRef(false)
  const domObserverRef = useRef<MutationObserver | null>(null)

  // Circuit breaker pour éviter les boucles infinies
  const circuitBreaker = useRef({
    failures: 0,
    lastFailure: 0,
    isOpen: false,
    
    canAttempt(): boolean {
      const now = Date.now()
      
      // Reset après 30 secondes
      if (now - this.lastFailure > 30000) {
        this.failures = 0
        this.isOpen = false
      }
      
      if (this.isOpen) {
        console.warn('🚫 [ZohoSalesIQ] Circuit breaker ouvert - opération bloquée')
        return false
      }
      
      return this.failures < CONFIG.CIRCUIT_BREAKER_THRESHOLD
    },
    
    recordFailure(): void {
      this.failures++
      this.lastFailure = Date.now()
      
      if (this.failures >= CONFIG.CIRCUIT_BREAKER_THRESHOLD) {
        this.isOpen = true
        console.error('🚫 [ZohoSalesIQ] Circuit breaker activé après', this.failures, 'échecs')
      }
    },
    
    recordSuccess(): void {
      this.failures = 0
      this.isOpen = false
    }
  })

  // Fonction utilitaire pour gérer les timeouts avec tracking
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

  // Fonction utilitaire pour gérer les intervals avec tracking
  const createInterval = useCallback((callback: () => void, delay: number): NodeJS.Timeout => {
    const interval = setInterval(() => {
      if (isMountedRef.current) {
        callback()
      }
    }, delay)
    intervalsRef.current.add(interval)
    return interval
  }, [])

  // Nettoyage optimisé de tous les timers
  const clearAllTimers = useCallback(() => {
    timeoutsRef.current.forEach(clearTimeout)
    intervalsRef.current.forEach(clearInterval)
    timeoutsRef.current.clear()
    intervalsRef.current.clear()
    
    if (verificationTimeoutRef.current) {
      clearTimeout(verificationTimeoutRef.current)
      verificationTimeoutRef.current = null
    }

    if (domObserverRef.current) {
      domObserverRef.current.disconnect()
      domObserverRef.current = null
    }
  }, [])

  // Stockage global optimisé de la langue de session
  const setGlobalSessionLanguage = useCallback((lang: string) => {
    if (typeof window !== 'undefined') {
      ;(window as any).ZOHO_SESSION_LANGUAGE = lang
      console.log('🌐 [ZohoSalesIQ] Variable globale stockée:', lang)
    }
  }, [])

  // Vérification optimisée de la visibilité du bouton flottant
  const ensureFloatButtonVisible = useCallback((): boolean => {
    if (!circuitBreaker.current.canAttempt()) return false

    try {
      const floatButton = document.querySelector('#zsiq_float') as HTMLElement
      if (floatButton && floatButton.classList.contains('zsiq-hide')) {
        console.log('🔌 [ZohoSalesIQ] Retrait classe zsiq-hide pour rendre visible')
        floatButton.classList.remove('zsiq-hide')
        console.log('✅ [ZohoSalesIQ] Bouton flottant maintenant visible')
        return true
      }
      return false
    } catch (error) {
      console.error('🔧 [ZohoSalesIQ] Erreur visibilité bouton:', error)
      circuitBreaker.current.recordFailure()
      return false
    }
  }, [])

  // Masquage optimisé de la fenêtre de chat
  const hideZohoChatWindow = useCallback((): boolean => {
    if (!circuitBreaker.current.canAttempt()) return false

    try {
      let hasChanges = false
      
      // Masquer la fenêtre principale de chat
      const chatSelectors = ['#zsiq_agelif', '.zsiq_theme1', '.siq-widgetwindow', '.zsiq-chat']
      
      chatSelectors.forEach(selector => {
        const chatWindow = document.querySelector(selector) as HTMLElement
        if (chatWindow && !chatWindow.classList.contains('zsiq-hide')) {
          // Tenter via API Zoho d'abord
          if ((window as any).$zoho?.salesiq?.floatwindow) {
            try {
              ;(window as any).$zoho.salesiq.floatwindow.visible('hide')
              console.log('✅ [ZohoSalesIQ] Fenêtre fermée via API Zoho')
            } catch (error) {
              console.warn('⚠️ [ZohoSalesIQ] Impossible de fermer via API:', error)
            }
          }
          
          // Backup: masquer via CSS
          chatWindow.classList.add('zsiq-hide')
          chatWindow.style.display = 'none'
          hasChanges = true
        }
      })

      if (hasChanges) {
        console.log('✅ [ZohoSalesIQ] Fenêtre chat masquée')
      }

      return hasChanges
    } catch (error) {
      console.error('🔧 [ZohoSalesIQ] Erreur masquage chat:', error)
      circuitBreaker.current.recordFailure()
      return false
    }
  }, [])

  // Fixes d'accessibilité consolidés et optimisés
  const fixZohoAccessibility = useCallback((): boolean => {
    if (!circuitBreaker.current.canAttempt()) return false

    try {
      let hasChanges = false

      // Fix 1: Interactive controls must not be nested
      const floatButton = document.querySelector('#zsiq_float') as HTMLElement
      if (floatButton) {
        const nestedControls = floatButton.querySelectorAll('[role="button"]')
        if (nestedControls.length > 1) {
          nestedControls.forEach((control, index) => {
            if (index > 0) {
              control.removeAttribute('role')
              control.removeAttribute('tabindex')
              hasChanges = true
            }
          })
          
          if (hasChanges) {
            console.log('✅ [ZohoSalesIQ] Contrôle imbriqué corrigé')
          }
        }

        // Ajouter aria-label principal si manquant
        if (!floatButton.getAttribute('aria-label')) {
          floatButton.setAttribute('aria-label', 'Ouvrir le support chat')
          floatButton.setAttribute('title', 'Ouvrir le support chat')
          hasChanges = true
        }

        // Supprimer les éléments interactifs redondants
        const redundantButtons = floatButton.querySelectorAll('div[onclick], span[onclick]')
        redundantButtons.forEach(btn => {
          if (btn.getAttribute('onclick')) {
            btn.removeAttribute('onclick')
            btn.removeAttribute('role')
            btn.removeAttribute('tabindex')
            hasChanges = true
          }
        })
      }

      // Fix 2: ARIA commands must have accessible name
      const interactiveElements = document.querySelectorAll('#zsiq_float [role="button"], .siqico-close, [class*="zsiq"][onclick]')
      interactiveElements.forEach(element => {
        if (!element.getAttribute('aria-label') && !element.getAttribute('aria-labelledby')) {
          // 🛡️ CORRECTION : Utiliser la fonction sécurisée pour className
          let label = 'Élément interactif du chat'
          
          try {
            const classString = typeof element.className === 'string' 
              ? element.className 
              : element.className?.toString() || ''
            
            if (classString.includes('close')) {
              label = 'Fermer le chat'
            } else if (classString.includes('minimize')) {
              label = 'Réduire le chat'
            } else if (classString.includes('maximize')) {
              label = 'Agrandir le chat'
            }
          } catch (error) {
            console.warn('⚠️ [ZohoSalesIQ] Erreur détection classe bouton:', error)
          }
          
          element.setAttribute('aria-label', label)
          element.setAttribute('title', label)
          hasChanges = true
        }
      })

      // Fix 3: Supprimer tabindex négatifs problématiques
      const negativeTabIndex = document.querySelectorAll('[tabindex="-1"]')
      negativeTabIndex.forEach(element => {
        if (element.closest('#zsiq_float')) {
          element.removeAttribute('tabindex')
          hasChanges = true
        }
      })

      if (hasChanges) {
        console.log('✅ [ZohoSalesIQ] Fixes accessibilité appliqués')
      }

      return hasChanges
    } catch (error) {
      console.error('🔧 [ZohoSalesIQ] Erreur fixes accessibilité:', error)
      circuitBreaker.current.recordFailure()
      return false
    }
  }, [])

  // Vérification consolidée avec debouncing intelligent
  const performConsolidatedVerification = useCallback(() => {
    if (!isMountedRef.current || !circuitBreaker.current.canAttempt()) return

    const state = widgetStateRef.current
    const now = Date.now()

    // Éviter les vérifications trop fréquentes
    if (now - state.lastVerification < CONFIG.VERIFICATION_DEBOUNCE) return

    // Limiter le nombre de vérifications
    if (state.verificationCount >= CONFIG.MAX_VERIFICATION_ATTEMPTS) {
      console.log('🛑 [ZohoSalesIQ] Limite vérifications atteinte')
      return
    }

    state.lastVerification = now
    state.verificationCount++

    try {
      let hasChanges = false

      // Exécuter toutes les vérifications en une fois
      if (ensureFloatButtonVisible()) hasChanges = true
      if (hideZohoChatWindow()) hasChanges = true
      if (fixZohoAccessibility()) hasChanges = true

      if (hasChanges) {
        console.log('✅ [ZohoSalesIQ] Vérification consolidée terminée avec modifications')
        circuitBreaker.current.recordSuccess()
        
        // Reset du compteur de vérifications après succès
        state.verificationCount = Math.max(0, state.verificationCount - 2)
      }

    } catch (error) {
      console.error('🔧 [ZohoSalesIQ] Erreur vérification consolidée:', error)
      circuitBreaker.current.recordFailure()
    }
  }, [ensureFloatButtonVisible, hideZohoChatWindow, fixZohoAccessibility])

  // Vérification avec debouncing optimisé
  const debouncedVerification = useCallback(() => {
    if (!isMountedRef.current) return

    // Annuler la vérification précédente
    if (verificationTimeoutRef.current) {
      clearTimeout(verificationTimeoutRef.current)
    }

    verificationTimeoutRef.current = createTimeout(() => {
      performConsolidatedVerification()
    }, CONFIG.VERIFICATION_DEBOUNCE)
  }, [performConsolidatedVerification, createTimeout])

  // Initialisation optimisée de l'objet Zoho
  const initializeZohoObject = useCallback(() => {
    if (typeof window === 'undefined') return

    console.log('🔧 [ZohoSalesIQ] Initialisation objet $zoho')

    if (!document.querySelector('#zoho-init-script')) {
      const initScript = document.createElement('script')
      initScript.id = 'zoho-init-script'
      initScript.innerHTML = `
        window.$zoho = window.$zoho || {};
        $zoho.salesiq = $zoho.salesiq || {ready: function(){}};
        console.log('✅ [ZohoSalesIQ] Objet $zoho initialisé');
      `
      document.head.appendChild(initScript)
    }
  }, [])

  // Configuration du widget avec retry intelligent et backoff
  const configureWidget = useCallback(async (lang: string, attempt: number = 1): Promise<boolean> => {
    if (!isMountedRef.current || configurationLockRef.current) return false

    // Lock pour éviter les configurations parallèles
    configurationLockRef.current = true

    try {
      console.log(`🔧 [ZohoSalesIQ] Tentative de configuration ${attempt}/${CONFIG.MAX_CONFIG_ATTEMPTS}`)

      const $zoho = (window as any).$zoho
      if (!$zoho?.salesiq?.visitor?.info || !$zoho?.salesiq?.floatwindow?.visible) {
        throw new Error('API Zoho incomplète')
      }

      console.log('✅ [ZohoSalesIQ] Objet Zoho complet disponible, configuration...')

      // Configuration des informations utilisateur
      if (user?.email) {
        const visitorInfo = {
          'Email': user.email,
          'Name': user.name || user.email.split('@')[0],
          'App Language': lang,
          'Widget Language': lang,
          'User ID': user.id || 'unknown'
        }
        
        $zoho.salesiq.visitor.info(visitorInfo)
        console.log('👤 [ZohoSalesIQ] Info utilisateur configurée avec langue:', lang)
      }

      console.log('👁️ [ZohoSalesIQ] Widget configuré - BOUTON FLOTTANT UNIQUEMENT')

      // Planifier les vérifications avec des délais optimisés
      const verificationDelays = [1000, 3000, 8000]
      verificationDelays.forEach(delay => {
        createTimeout(() => {
          debouncedVerification()
        }, delay)
      })

      // Mettre à jour l'état
      const state = widgetStateRef.current
      state.isConfigured = true
      state.sessionLanguage = lang
      state.verificationCount = 0

      console.log('✅ [ZohoSalesIQ] Configuration terminée - Bouton flottant uniquement')

      return true

    } catch (error) {
      console.error(`🔧 [ZohoSalesIQ] Erreur configuration tentative ${attempt}:`, error)

      if (attempt < CONFIG.MAX_CONFIG_ATTEMPTS && isMountedRef.current) {
        // Retry avec backoff exponentiel
        const delay = CONFIG.CONFIG_RETRY_DELAY * Math.pow(CONFIG.BACKOFF_MULTIPLIER, attempt - 1)
        console.log(`🔄 [ZohoSalesIQ] Nouvelle tentative dans ${delay}ms`)
        
        createTimeout(() => {
          configureWidget(lang, attempt + 1)
        }, delay)
      } else {
        console.error('🚫 [ZohoSalesIQ] Échec configuration après', CONFIG.MAX_CONFIG_ATTEMPTS, 'tentatives')
        circuitBreaker.current.recordFailure()
      }

      return false

    } finally {
      configurationLockRef.current = false
    }
  }, [user, createTimeout, debouncedVerification])

  // Chargement optimisé du script avec gestion d'erreurs robuste
  const loadZohoScript = useCallback(async (lang: string): Promise<void> => {
    if (!isMountedRef.current || typeof window === 'undefined') return

    console.log('🚀 [ZohoSalesIQ] Chargement widget avec langue de session:', lang)

    // Vérification des variables d'environnement
    const widgetBaseUrl = process.env.NEXT_PUBLIC_ZOHO_WIDGET_BASE_URL
    const widgetId = process.env.NEXT_PUBLIC_ZOHO_WIDGET_ID
    
    if (!widgetBaseUrl || !widgetId) {
      console.error('❌ [ZohoSalesIQ] Variables Zoho manquantes:', {
        baseUrl: !!widgetBaseUrl,
        widgetId: !!widgetId
      })
      throw new Error('Configuration Zoho manquante')
    }

    return new Promise((resolve, reject) => {
      // Initialiser l'objet $zoho AVANT le script
      initializeZohoObject()

      const script = document.createElement('script')
      script.id = 'zsiqscript'
      script.async = true
      script.defer = true
      script.src = `${widgetBaseUrl}?wc=${widgetId}&locale=${lang}`

      console.log('📡 [ZohoSalesIQ] Chargement script principal depuis env vars')

      const timeout = createTimeout(() => {
        console.error('⏰ [ZohoSalesIQ] Timeout chargement script')
        script.remove()
        reject(new Error('Timeout chargement script'))
      }, CONFIG.SCRIPT_TIMEOUT)

      script.onload = () => {
        clearTimeout(timeout)
        console.log('✅ [ZohoSalesIQ] Script principal chargé avec succès')
        widgetStateRef.current.scriptLoaded = true
        
        // Attendre l'initialisation complète avant configuration
        createTimeout(() => {
          configureWidget(lang)
        }, 2000)
        
        resolve()
      }

      script.onerror = () => {
        clearTimeout(timeout)
        console.error('❌ [ZohoSalesIQ] Erreur chargement script principal')
        script.remove()
        reject(new Error('Erreur chargement script'))
      }

      document.head.appendChild(script)
    })
  }, [initializeZohoObject, createTimeout, configureWidget])

  // 🛡️ Observer DOM CORRIGÉ avec gestion sécurisée des className
  const setupDOMObserver = useCallback(() => {
    if (!isMountedRef.current || domObserverRef.current) return

    const observer = new MutationObserver((mutations) => {
      let shouldCheck = false
      
      try {
        mutations.forEach((mutation) => {
          // Vérifier si des éléments Zoho ont été ajoutés/modifiés
          if (mutation.type === 'childList') {
            const hasZohoElements = Array.from(mutation.addedNodes).some(node => {
              if (!(node instanceof Element)) return false
              
              // ✅ CORRECTION : Utiliser les fonctions sécurisées
              return hasZohoId(node) || hasZohoClass(node)
            })
            
            if (hasZohoElements) shouldCheck = true
          }
          
          // Vérifier si des attributs ont changé sur des éléments Zoho
          if (mutation.type === 'attributes' && mutation.target instanceof Element) {
            // ✅ CORRECTION : Utiliser les fonctions sécurisées
            if (hasZohoId(mutation.target) || hasZohoClass(mutation.target)) {
              shouldCheck = true
            }
          }
        })
        
        if (shouldCheck && isMountedRef.current) {
          // Utiliser le debouncing pour éviter les appels trop fréquents
          debouncedVerification()
        }
      } catch (error) {
        console.error('🚨 [ZohoSalesIQ] Erreur dans MutationObserver:', error)
        // Ne pas faire planter l'observateur, juste logger l'erreur
      }
    })

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'style', 'id']
    })

    domObserverRef.current = observer
    console.log('👁️ [ZohoSalesIQ] Observer DOM configuré avec protection d\'erreurs')
  }, [debouncedVerification])

  // Processus d'initialisation principal optimisé
  const initializeWidget = useCallback(async (lang: string): Promise<void> => {
    if (!isMountedRef.current || !user?.email) return

    const state = widgetStateRef.current

    console.log('🎯 [ZohoSalesIQ] PREMIÈRE INITIALISATION - Fixation langue session à:', lang)

    try {
      // 1. Fixer la langue de session
      state.sessionLanguage = lang
      setGlobalSessionLanguage(lang)
      console.log('🔌 [ZohoSalesIQ] Langue de session fixée:', lang)

      // 2. Charger le script Zoho
      await loadZohoScript(lang)

      // 3. Configurer l'observer DOM
      setupDOMObserver()

      // Marquer comme initialisé
      state.isInitialized = true
      console.log('✅ [ZohoSalesIQ] Initialisation complète')

    } catch (error) {
      console.error('🔧 [ZohoSalesIQ] Erreur initialisation:', error)
      circuitBreaker.current.recordFailure()
    }
  }, [user, setGlobalSessionLanguage, loadZohoScript, setupDOMObserver])

  // Gestion optimisée du changement de langue
  const handleLanguageChange = useCallback((newLang: string) => {
    const state = widgetStateRef.current

    if (state.sessionLanguage === newLang) {
      console.log('👍 [ZohoSalesIQ] Langue inchangée, widget stable')
      return
    }

    if (state.sessionLanguage) {
      console.log('🚫 [ZohoSalesIQ] CHANGEMENT DE LANGUE IGNORÉ:', state.sessionLanguage, '→', newLang)
      console.log('🔌 [ZohoSalesIQ] Widget reste en:', state.sessionLanguage)
      console.log('💡 [ZohoSalesIQ] Nouvelle langue sera effective à la prochaine session')
    }
  }, [])

  // Effect principal optimisé
  useEffect(() => {
    if (!user?.email || !language) return

    console.log('🌐 [ZohoSalesIQ] Effet déclenché - Langue courante:', language, 'User:', !!user.email)

    const state = widgetStateRef.current

    if (!state.isInitialized) {
      // Première initialisation avec langue fixe
      initializeWidget(language)
    } else {
      // Gestion des changements de langue ultérieurs
      handleLanguageChange(language)
    }

  }, [user?.email, language, initializeWidget, handleLanguageChange])

  // Cleanup optimisé au unmount
  useEffect(() => {
    isMountedRef.current = true

    return () => {
      console.log('🧹 [ZohoSalesIQ] Destruction composant - nettoyage session')
      isMountedRef.current = false
      clearAllTimers()
      configurationLockRef.current = false
      
      // Reset de l'état
      widgetStateRef.current = {
        isInitialized: false,
        isConfigured: false,
        isVisible: false,
        sessionLanguage: null,
        lastVerification: 0,
        verificationCount: 0,
        scriptLoaded: false
      }

      // Nettoyer les variables globales
      if (typeof window !== 'undefined' && (window as any).ZOHO_SESSION_LANGUAGE) {
        delete (window as any).ZOHO_SESSION_LANGUAGE
      }
    }
  }, [clearAllTimers])

  return null
}

// Types TypeScript optimisés
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
    ZOHO_SESSION_LANGUAGE?: string
  }
}