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

// Fonction utilitaire sécurisée pour éviter l'erreur includes
const hasZohoClass = (element: Element): boolean => {
  try {
    // Approche plus simple et robuste pour TypeScript
    let classString = ''
    
    if (element.className) {
      // Cast en any pour éviter les problèmes TypeScript, puis String() pour sécurité
      classString = String((element.className as any) || '')
    }
    
    return classString.includes('zsiq') || classString.includes('siq-')
  } catch (error) {
    console.warn('Erreur vérification classe:', error)
    return false
  }
}

// Fonction utilitaire pour vérifier les IDs Zoho
const hasZohoId = (element: Element): boolean => {
  try {
    return element.id?.includes('zsiq') || false
  } catch (error) {
    console.warn('Erreur vérification ID:', error)
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
        console.warn('Circuit breaker ouvert - opération bloquée')
        return false
      }
      
      return this.failures < CONFIG.CIRCUIT_BREAKER_THRESHOLD
    },
    
    recordFailure(): void {
      this.failures++
      this.lastFailure = Date.now()
      
      if (this.failures >= CONFIG.CIRCUIT_BREAKER_THRESHOLD) {
        this.isOpen = true
        console.error('Circuit breaker activé après', this.failures, 'échecs')
      }
    },
    
    recordSuccess(): void {
      this.failures = 0
      this.isOpen = false
    }
  })

  // CORRECTION B: Fonction utilitaire pour vérifier si on doit créer des timers
  const shouldCreateTimers = useCallback((): boolean => {
    // Ne pas créer de timers si le document n'est pas visible
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
      console.log('⏸️ [DEBUG-TIMERS-ZOHO] Timers bloqués - document caché')
      return false
    }

    // Ne pas créer de timers si le composant n'est pas monté
    if (!isMountedRef.current) {
      console.log('⏸️ [DEBUG-TIMERS-ZOHO] Timers bloqués - composant démonté')
      return false
    }

    // Ne pas créer de timers si on est en cours de redirection
    // (détection basique via window.location en cours de changement)
    if (typeof window !== 'undefined') {
      try {
        // Vérifier si on est en cours de navigation
        const isNavigating = document.readyState === 'loading'
        if (isNavigating) {
          console.log('⏸️ [DEBUG-TIMERS-ZOHO] Timers bloqués - navigation en cours')
          return false
        }
      } catch (error) {
        console.warn('Erreur vérification navigation:', error)
      }
    }

    return true
  }, [])

  // CORRECTION B: Fonction utilitaire sécurisée pour gérer les timeouts avec tracking et logs debug
  const createTimeout = useCallback((callback: () => void, delay: number): NodeJS.Timeout => {
    // Vérification préalable avant création du timeout
    if (!shouldCreateTimers()) {
      console.log('❌ [DEBUG-TIMEOUT-ZOHO] createTimeout bloqué - conditions non remplies')
      // Retourner un timeout factice qui ne fait rien
      return setTimeout(() => {}, 0)
    }

    const timeout = setTimeout(() => {
      console.log('🕒 [DEBUG-TIMEOUT-ZOHO] Execution createTimeout - isMounted:', isMountedRef.current, 'visible:', document.visibilityState)
      
      timeoutsRef.current.delete(timeout)
      
      // Double vérification au moment d'exécution
      if (isMountedRef.current && shouldCreateTimers()) {
        callback()
      } else {
        console.log('⚠️ [DEBUG-TIMEOUT-ZOHO] createTimeout ignoré - composant démonté ou navigation')
      }
    }, delay)
    
    timeoutsRef.current.add(timeout)
    return timeout
  }, [shouldCreateTimers])

  // CORRECTION B: Fonction utilitaire pour gérer les intervals avec tracking
  const createInterval = useCallback((callback: () => void, delay: number): NodeJS.Timeout => {
    // Vérification préalable avant création de l'interval
    if (!shouldCreateTimers()) {
      console.log('❌ [DEBUG-INTERVAL-ZOHO] createInterval bloqué - conditions non remplies')
      // Retourner un interval factice qui ne fait rien
      return setInterval(() => {}, delay)
    }

    const interval = setInterval(() => {
      console.log('🕒 [DEBUG-INTERVAL-ZOHO] Execution createInterval - isMounted:', isMountedRef.current, 'visible:', document.visibilityState)
      
      // Vérification à chaque exécution
      if (isMountedRef.current && shouldCreateTimers()) {
        callback()
      } else {
        console.log('⚠️ [DEBUG-INTERVAL-ZOHO] createInterval ignoré - composant démonté ou navigation')
        // Auto-nettoyage si conditions plus remplies
        clearInterval(interval)
        intervalsRef.current.delete(interval)
      }
    }, delay)
    
    intervalsRef.current.add(interval)
    return interval
  }, [shouldCreateTimers])

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
      console.log('Variable globale stockée:', lang)
    }
  }, [])

  // Vérification optimisée de la visibilité du bouton flottant
  const ensureFloatButtonVisible = useCallback((): boolean => {
    if (!circuitBreaker.current.canAttempt()) return false

    try {
      const floatButton = document.querySelector('#zsiq_float') as HTMLElement
      if (floatButton && floatButton.classList.contains('zsiq-hide')) {
        console.log('Retrait classe zsiq-hide pour rendre visible')
        floatButton.classList.remove('zsiq-hide')
        console.log('Bouton flottant maintenant visible')
        return true
      }
      return false
    } catch (error) {
      console.error('Erreur visibilité bouton:', error)
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
              console.log('Fenêtre fermée via API Zoho')
            } catch (error) {
              console.warn('Impossible de fermer via API:', error)
            }
          }
          
          // Backup: masquer via CSS
          chatWindow.classList.add('zsiq-hide')
          chatWindow.style.display = 'none'
          hasChanges = true
        }
      })

      if (hasChanges) {
        console.log('Fenêtre chat masquée')
      }

      return hasChanges
    } catch (error) {
      console.error('Erreur masquage chat:', error)
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
            console.log('Contrôle imbriqué corrigé')
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
          // Utiliser la fonction sécurisée pour className
          let label = 'Élément interactif du chat'
          
          try {
            // Approche simple et robuste pour TypeScript
            const classString = element.className ? String((element.className as any) || '') : ''
            
            if (classString.includes('close')) {
              label = 'Fermer le chat'
            } else if (classString.includes('minimize')) {
              label = 'Réduire le chat'
            } else if (classString.includes('maximize')) {
              label = 'Agrandir le chat'
            }
          } catch (error) {
            console.warn('Erreur détection classe bouton:', error)
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
        console.log('Fixes accessibilité appliqués')
      }

      return hasChanges
    } catch (error) {
      console.error('Erreur fixes accessibilité:', error)
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
      console.log('Limite vérifications atteinte')
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
        console.log('Vérification consolidée terminée avec modifications')
        circuitBreaker.current.recordSuccess()
        
        // Reset du compteur de vérifications après succès
        state.verificationCount = Math.max(0, state.verificationCount - 2)
      }

    } catch (error) {
      console.error('Erreur vérification consolidée:', error)
      circuitBreaker.current.recordFailure()
    }
  }, [ensureFloatButtonVisible, hideZohoChatWindow, fixZohoAccessibility])

  // Vérification avec debouncing optimisé et logs debug
  const debouncedVerification = useCallback(() => {
    if (!isMountedRef.current) return

    // Annuler la vérification précédente
    if (verificationTimeoutRef.current) {
      clearTimeout(verificationTimeoutRef.current)
    }

    // CORRECTION B: setTimeout avec logs debug pour identifier le timeout coupable
    verificationTimeoutRef.current = setTimeout(() => {
      console.log('🕒 [DEBUG-TIMEOUT-ZOHO-VERIFICATION] Execution debouncedVerification - isMounted:', isMountedRef.current)
      if (isMountedRef.current) {
        performConsolidatedVerification()
      } else {
        console.log('⚠️ [DEBUG-TIMEOUT-ZOHO-VERIFICATION] debouncedVerification ignoré - composant démonté')
      }
    }, CONFIG.VERIFICATION_DEBOUNCE)
  }, [performConsolidatedVerification])

  // Initialisation optimisée de l'objet Zoho
  const initializeZohoObject = useCallback(() => {
    if (typeof window === 'undefined') return

    console.log('Initialisation objet $zoho')

    if (!document.querySelector('#zoho-init-script')) {
      const initScript = document.createElement('script')
      initScript.id = 'zoho-init-script'
      initScript.innerHTML = `
        window.$zoho = window.$zoho || {};
        $zoho.salesiq = $zoho.salesiq || {ready: function(){}};
        console.log('Objet $zoho initialisé');
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
      console.log(`Tentative de configuration ${attempt}/${CONFIG.MAX_CONFIG_ATTEMPTS}`)

      const $zoho = (window as any).$zoho
      if (!$zoho?.salesiq?.visitor?.info || !$zoho?.salesiq?.floatwindow?.visible) {
        throw new Error('API Zoho incomplète')
      }

      console.log('Objet Zoho complet disponible, configuration...')

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
        console.log('Info utilisateur configurée avec langue:', lang)
      }

      console.log('Widget configuré - BOUTON FLOTTANT UNIQUEMENT')

      // CORRECTION B: Planifier les vérifications avec des délais optimisés et logs debug
      const verificationDelays = [1000, 3000, 8000]
      verificationDelays.forEach((delay, index) => {
        createTimeout(() => {
          console.log(`🕒 [DEBUG-TIMEOUT-ZOHO-CONFIG-${index}] Execution verification delay ${delay}ms - isMounted:`, isMountedRef.current)
          if (isMountedRef.current) {
            debouncedVerification()
          } else {
            console.log(`⚠️ [DEBUG-TIMEOUT-ZOHO-CONFIG-${index}] Verification delay ignorée - composant démonté`)
          }
        }, delay)
      })

      // Mettre à jour l'état
      const state = widgetStateRef.current
      state.isConfigured = true
      state.sessionLanguage = lang
      state.verificationCount = 0

      console.log('Configuration terminée - Bouton flottant uniquement')

      return true

    } catch (error) {
      console.error(`Erreur configuration tentative ${attempt}:`, error)

      if (attempt < CONFIG.MAX_CONFIG_ATTEMPTS && isMountedRef.current) {
        // CORRECTION B: Retry avec backoff exponentiel et logs debug
        const delay = CONFIG.CONFIG_RETRY_DELAY * Math.pow(CONFIG.BACKOFF_MULTIPLIER, attempt - 1)
        console.log(`Nouvelle tentative dans ${delay}ms`)
        
        createTimeout(() => {
          console.log(`🕒 [DEBUG-TIMEOUT-ZOHO-RETRY-${attempt}] Execution retry config - isMounted:`, isMountedRef.current)
          if (isMountedRef.current) {
            configureWidget(lang, attempt + 1)
          } else {
            console.log(`⚠️ [DEBUG-TIMEOUT-ZOHO-RETRY-${attempt}] Retry config ignoré - composant démonté`)
          }
        }, delay)
      } else {
        console.error('Échec configuration après', CONFIG.MAX_CONFIG_ATTEMPTS, 'tentatives')
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

    console.log('Chargement widget avec langue de session:', lang)

    // Vérification des variables d'environnement
    const widgetBaseUrl = process.env.NEXT_PUBLIC_ZOHO_WIDGET_BASE_URL
    const widgetId = process.env.NEXT_PUBLIC_ZOHO_WIDGET_ID
    
    if (!widgetBaseUrl || !widgetId) {
      console.error('Variables Zoho manquantes:', {
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

      console.log('Chargement script principal depuis env vars')

      // CORRECTION B: Timeout avec logs debug
      const timeout = createTimeout(() => {
        console.log('🕒 [DEBUG-TIMEOUT-ZOHO-SCRIPT] Execution script timeout - isMounted:', isMountedRef.current)
        if (isMountedRef.current) {
          console.error('Timeout chargement script')
          script.remove()
          reject(new Error('Timeout chargement script'))
        } else {
          console.log('⚠️ [DEBUG-TIMEOUT-ZOHO-SCRIPT] Script timeout ignoré - composant démonté')
        }
      }, CONFIG.SCRIPT_TIMEOUT)

      script.onload = () => {
        clearTimeout(timeout)
        console.log('Script principal chargé avec succès')
        widgetStateRef.current.scriptLoaded = true
        
        // CORRECTION B: Attendre l'initialisation complète avant configuration avec logs debug
        createTimeout(() => {
          console.log('🕒 [DEBUG-TIMEOUT-ZOHO-INIT] Execution script onload config - isMounted:', isMountedRef.current)
          if (isMountedRef.current) {
            configureWidget(lang)
          } else {
            console.log('⚠️ [DEBUG-TIMEOUT-ZOHO-INIT] Script onload config ignoré - composant démonté')
          }
        }, 2000)
        
        resolve()
      }

      script.onerror = () => {
        clearTimeout(timeout)
        console.error('Erreur chargement script principal')
        script.remove()
        reject(new Error('Erreur chargement script'))
      }

      document.head.appendChild(script)
    })
  }, [initializeZohoObject, createTimeout, configureWidget])

  // Observer DOM CORRIGÉ avec gestion sécurisée des className
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
              
              // Utiliser les fonctions sécurisées
              return hasZohoId(node) || hasZohoClass(node)
            })
            
            if (hasZohoElements) shouldCheck = true
          }
          
          // Vérifier si des attributs ont changé sur des éléments Zoho
          if (mutation.type === 'attributes' && mutation.target instanceof Element) {
            // Utiliser les fonctions sécurisées
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
        console.error('Erreur dans MutationObserver:', error)
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
    console.log('Observer DOM configuré avec protection d\'erreurs')
  }, [debouncedVerification])

  // Processus d'initialisation principal optimisé
  const initializeWidget = useCallback(async (lang: string): Promise<void> => {
    if (!isMountedRef.current || !user?.email) return

    const state = widgetStateRef.current

    console.log('PREMIÈRE INITIALISATION - Fixation langue session à :', lang)

    try {
      // 1. Fixer la langue de session
      state.sessionLanguage = lang
      setGlobalSessionLanguage(lang)
      console.log('Langue de session fixée:', lang)

      // 2. Charger le script Zoho
      await loadZohoScript(lang)

      // 3. Configurer l'observer DOM
      setupDOMObserver()

      // Marquer comme initialisé
      state.isInitialized = true
      console.log('Initialisation complète')

    } catch (error) {
      console.error('Erreur initialisation:', error)
      circuitBreaker.current.recordFailure()
    }
  }, [user, setGlobalSessionLanguage, loadZohoScript, setupDOMObserver])

  // Gestion optimisée du changement de langue
  const handleLanguageChange = useCallback((newLang: string) => {
    const state = widgetStateRef.current

    if (state.sessionLanguage === newLang) {
      console.log('Langue inchangée, widget stable')
      return
    }

    if (state.sessionLanguage) {
      console.log('CHANGEMENT DE LANGUE IGNORÉ:', state.sessionLanguage, '→', newLang)
      console.log('Widget reste en:', state.sessionLanguage)
      console.log('Nouvelle langue sera effective à la prochaine session')
    }
  }, [])

  // CORRECTION B: Gestionnaire d'événements pour détecter les changements de visibilité
  useEffect(() => {
    const handleVisibilityChange = () => {
      console.log('👁️ [DEBUG-VISIBILITY] Document visibility:', document.visibilityState)
      
      if (document.visibilityState === 'hidden') {
        console.log('🛑 [DEBUG-VISIBILITY] Page cachée - pause des opérations Zoho')
        // Optionnel : mettre en pause les vérifications actives
        if (verificationTimeoutRef.current) {
          clearTimeout(verificationTimeoutRef.current)
          verificationTimeoutRef.current = null
        }
      } else if (document.visibilityState === 'visible' && isMountedRef.current) {
        console.log('▶️ [DEBUG-VISIBILITY] Page visible - reprise des opérations Zoho')
        // Optionnel : reprendre les vérifications si nécessaire
        debouncedVerification()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [debouncedVerification])

  // Effect principal optimisé
  useEffect(() => {
    if (!user?.email || !language) return

    console.log('Effet déclenché - Langue courante:', language, 'User:', !!user.email)

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