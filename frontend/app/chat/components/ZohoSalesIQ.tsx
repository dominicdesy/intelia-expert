// components/ZohoSalesIQ.tsx - VERSION CORRIGÉE avec initialisation appropriée

import { useEffect, useRef, useCallback } from 'react'

interface ZohoSalesIQProps {
  user: any
  language: string
}

export const ZohoSalesIQ: React.FC<ZohoSalesIQProps> = ({ user, language }) => {
  const isInitializedRef = useRef(false)
  const currentLanguageRef = useRef<string | null>(null)
  const widgetLoadedRef = useRef(false)
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const clearRetryTimeout = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
  }, [])

  const cleanupZoho = useCallback(() => {
    console.log('🧹 [ZohoSalesIQ] NETTOYAGE complet')
    
    try {
      clearRetryTimeout()
      
      // Cacher le widget si disponible
      if (window.$zoho?.salesiq?.floatwindow) {
        try {
          window.$zoho.salesiq.floatwindow.visible('hide')
        } catch (e) {
          console.warn('⚠️ [ZohoSalesIQ] Erreur hide widget:', e)
        }
      }
      
      // Supprimer les scripts Zoho existants
      const existingScripts = document.querySelectorAll('script[src*="salesiq.zohopublic.com"], script#zsiqscript')
      existingScripts.forEach(script => {
        console.log('🗑️ [ZohoSalesIQ] Suppression script:', script.id || script.src)
        script.remove()
      })
      
      // Supprimer le script d'initialisation personnalisé
      const initScript = document.querySelector('#zoho-init-script')
      if (initScript) {
        initScript.remove()
      }
      
      // Supprimer les éléments DOM du widget
      const selectors = [
        '[id*="zsiq"]', '[class*="zsiq"]', '[id*="siq"]', '[class*="siq"]',
        '#salesiq-chat', '.salesiq-widget', '.zoho-salesiq'
      ]
      
      selectors.forEach(selector => {
        const elements = document.querySelectorAll(selector)
        elements.forEach(element => element.remove())
      })
      
      // ✅ CORRECTION: NE PAS supprimer $zoho complètement, juste le réinitialiser
      if (window.$zoho) {
        window.$zoho.salesiq = { ready: function(){} }
      }
      
      widgetLoadedRef.current = false
      
      console.log('✅ [ZohoSalesIQ] Nettoyage terminé')
      
    } catch (error) {
      console.error('❌ [ZohoSalesIQ] Erreur lors du nettoyage:', error)
    }
  }, [clearRetryTimeout])

  const initializeZohoObject = useCallback(() => {
    console.log('🔧 [ZohoSalesIQ] Initialisation objet $zoho')
    
    // ✅ CORRECTION: Initialiser $zoho EXACTEMENT comme Zoho le fait
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

  const configureWidget = useCallback((lang: string) => {
    console.log('🔧 [ZohoSalesIQ] Configuration du widget pour langue:', lang)
    
    let attempts = 0
    const maxAttempts = 10
    const checkInterval = 1000
    
    const configureAttempt = () => {
      attempts++
      console.log(`🔧 [ZohoSalesIQ] Tentative de configuration ${attempts}/${maxAttempts}`)
      
      // ✅ CORRECTION: Vérification plus appropriée après initialisation
      if (window.$zoho && 
          window.$zoho.salesiq && 
          typeof window.$zoho.salesiq.visitor?.info === 'function' &&
          typeof window.$zoho.salesiq.floatwindow?.visible === 'function') {
        
        try {
          console.log('✅ [ZohoSalesIQ] Objet Zoho complet disponible, configuration...')
          
          // Configuration utilisateur
          if (user?.email) {
            const visitorInfo = {
              'Email': user.email,
              'Name': user.name || user.email.split('@')[0],
              'App Language': lang,
              'Widget Language': lang,
              'User ID': user.id || 'unknown'
            }
            
            window.$zoho.salesiq.visitor.info(visitorInfo)
            console.log('👤 [ZohoSalesIQ] Info utilisateur configurée avec langue:', lang)
          }
          
          // Afficher le widget
          setTimeout(() => {
            try {
              if (window.$zoho?.salesiq?.floatwindow) {
                window.$zoho.salesiq.floatwindow.visible('show')
                console.log('👁️ [ZohoSalesIQ] Widget affiché')
              }
            } catch (showError) {
              console.error('❌ [ZohoSalesIQ] Erreur affichage:', showError)
            }
          }, 500)
          
          console.log('✅ [ZohoSalesIQ] Configuration terminée avec succès')
          return
          
        } catch (error) {
          console.error('❌ [ZohoSalesIQ] Erreur configuration:', error)
        }
      } else if (attempts < maxAttempts) {
        console.log('⏳ [ZohoSalesIQ] Widget pas encore prêt, retry...')
        console.log('🔍 [ZohoSalesIQ] État:', {
          zoho: !!window.$zoho,
          salesiq: !!window.$zoho?.salesiq,
          visitor: typeof window.$zoho?.salesiq?.visitor,
          floatwindow: typeof window.$zoho?.salesiq?.floatwindow
        })
        
        retryTimeoutRef.current = setTimeout(configureAttempt, checkInterval)
        
      } else {
        console.error('❌ [ZohoSalesIQ] Échec configuration après', maxAttempts, 'tentatives')
      }
    }
    
    configureAttempt()
  }, [user])

  const loadZohoWithLanguage = useCallback((lang: string) => {
    console.log('🚀 [ZohoSalesIQ] Chargement widget avec langue:', lang)
    
    if (!user?.email) {
      console.warn('⚠️ [ZohoSalesIQ] Pas d\'utilisateur, abandon')
      return
    }

    try {
      // ✅ ÉTAPE 1: Initialiser l'objet $zoho AVANT le script
      initializeZohoObject()
      
      // ✅ ÉTAPE 2: Créer le script principal avec la structure Zoho
      const script = document.createElement('script')
      script.id = 'zsiqscript'
      script.async = true
      script.defer = true
      
      // ✅ CORRECTION: Utiliser l'URL de base sans locale d'abord
      script.src = `https://salesiq.zohopublic.com/widget?wc=siq31d58179214fbbfbb0a5b5eb16ab9173ba0ee84601e9d7d04840d96541bc7e4f`
      
      console.log('📡 [ZohoSalesIQ] Chargement script principal:', script.src)
      
      let loadTimeout: NodeJS.Timeout
      
      script.onload = () => {
        console.log('✅ [ZohoSalesIQ] Script principal chargé avec succès')
        clearTimeout(loadTimeout)
        widgetLoadedRef.current = true
        
        // Attendre que le widget soit complètement initialisé
        setTimeout(() => {
          configureWidget(lang)
        }, 2000)
      }
      
      script.onerror = (error) => {
        console.error('❌ [ZohoSalesIQ] Erreur chargement script principal:', error)
        clearTimeout(loadTimeout)
        
        // Retry après erreur
        setTimeout(() => {
          console.log('🔄 [ZohoSalesIQ] Retry après erreur')
          cleanupZoho()
          setTimeout(() => loadZohoWithLanguage(lang), 2000)
        }, 5000)
      }
      
      // Timeout de sécurité
      loadTimeout = setTimeout(() => {
        console.error('❌ [ZohoSalesIQ] Timeout chargement script')
        script.remove()
      }, 15000)
      
      document.head.appendChild(script)
      
    } catch (error) {
      console.error('❌ [ZohoSalesIQ] Erreur création script:', error)
    }
  }, [user, initializeZohoObject, configureWidget, cleanupZoho])

  // Effet principal avec protection boucle infinie
  useEffect(() => {
    console.log('🌐 [ZohoSalesIQ] Effet déclenché - Langue:', language, 'User:', !!user?.email)
    
    // Protection contre les changements inutiles
    if (currentLanguageRef.current === language && isInitializedRef.current) {
      console.log('👍 [ZohoSalesIQ] Pas de changement nécessaire')
      return
    }
    
    // Si changement de langue sur widget déjà chargé
    if (widgetLoadedRef.current && currentLanguageRef.current && currentLanguageRef.current !== language) {
      console.log('🔄 [ZohoSalesIQ] Rechargement pour nouvelle langue:', currentLanguageRef.current, '→', language)
      
      currentLanguageRef.current = language
      clearRetryTimeout()
      cleanupZoho()
      
      setTimeout(() => {
        loadZohoWithLanguage(language)
      }, 1000)
      
      return
    }
    
    // Première initialisation
    if (!isInitializedRef.current && user?.email) {
      console.log('🎯 [ZohoSalesIQ] PREMIÈRE INITIALISATION avec langue:', language)
      isInitializedRef.current = true
      currentLanguageRef.current = language
      loadZohoWithLanguage(language)
    }
    
  }, [language, user?.email, loadZohoWithLanguage, cleanupZoho, clearRetryTimeout])

  // Nettoyage à la destruction
  useEffect(() => {
    return () => {
      console.log('🧹 [ZohoSalesIQ] Destruction composant')
      clearRetryTimeout()
      cleanupZoho()
    }
  }, [cleanupZoho, clearRetryTimeout])

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