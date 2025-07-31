// components/ZohoSalesIQ.tsx - VERSION STABLE: Langue fixe pour la session

import { useEffect, useRef, useCallback } from 'react'

interface ZohoSalesIQProps {
  user: any
  language: string
}

export const ZohoSalesIQ: React.FC<ZohoSalesIQProps> = ({ user, language }) => {
  const isInitializedRef = useRef(false)
  const sessionLanguageRef = useRef<string | null>(null)
  const widgetLoadedRef = useRef(false)
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const clearRetryTimeout = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
  }, [])

  const ensureFloatButtonVisible = useCallback(() => {
    console.log('🔧 [ZohoSalesIQ] Vérification visibilité bouton flottant')
    
    const floatButton = document.querySelector('#zsiq_float')
    if (floatButton && floatButton.classList.contains('zsiq-hide')) {
      console.log('📌 [ZohoSalesIQ] Retrait classe zsiq-hide pour rendre visible')
      floatButton.classList.remove('zsiq-hide')
      console.log('✅ [ZohoSalesIQ] Bouton flottant maintenant visible')
    }
  }, [])

  const initializeZohoObject = useCallback(() => {
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

  const configureWidget = useCallback((lang: string) => {
    console.log('🔧 [ZohoSalesIQ] Configuration du widget pour langue:', lang)
    
    let attempts = 0
    const maxAttempts = 10
    const checkInterval = 1000
    
    const configureAttempt = () => {
      attempts++
      console.log(`🔧 [ZohoSalesIQ] Tentative de configuration ${attempts}/${maxAttempts}`)
      
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
                
                // ✅ CORRECTION: S'assurer que le bouton flottant reste visible
                setTimeout(() => {
                  ensureFloatButtonVisible()
                }, 1000)
                
                // ✅ CORRECTION: Vérification supplémentaire après 5 secondes
                setTimeout(() => {
                  ensureFloatButtonVisible()
                }, 5000)
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
  }, [user, ensureFloatButtonVisible])

  const loadZohoWithLanguage = useCallback((lang: string) => {
    console.log('🚀 [ZohoSalesIQ] Chargement widget avec langue de session:', lang)
    
    if (!user?.email) {
      console.warn('⚠️ [ZohoSalesIQ] Pas d\'utilisateur, abandon')
      return
    }

    try {
      // Initialiser l'objet $zoho AVANT le script
      initializeZohoObject()
      
      // Créer le script principal
      const script = document.createElement('script')
      script.id = 'zsiqscript'
      script.async = true
      script.defer = true
      
      // ✅ CORRECTION: URL avec locale pour forcer la langue
      script.src = `https://salesiq.zohopublic.com/widget?wc=siq31d58179214fbbfbb0a5b5eb16ab9173ba0ee84601e9d7d04840d96541bc7e4f&locale=${lang}`
      
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
  }, [user, initializeZohoObject, configureWidget])

  // ✅ EFFET PRINCIPAL: Langue fixe pour la session
  useEffect(() => {
    console.log('🌐 [ZohoSalesIQ] Effet déclenché - Langue courante:', language, 'User:', !!user?.email)
    
    // ✅ CAPTURE de la langue à la première initialisation
    if (!isInitializedRef.current && user?.email) {
      console.log('🎯 [ZohoSalesIQ] PREMIÈRE INITIALISATION - Fixation langue session à:', language)
      
      isInitializedRef.current = true
      sessionLanguageRef.current = language
      
      console.log('📌 [ZohoSalesIQ] Langue de session fixée:', sessionLanguageRef.current)
      
      // ✅ CORRECTION: Stocker dans window pour debug
      window.ZOHO_SESSION_LANGUAGE = language
      console.log('🌍 [ZohoSalesIQ] Variable globale stockée:', window.ZOHO_SESSION_LANGUAGE)
      
      loadZohoWithLanguage(language)
      
      return
    }
    
    // ✅ IGNORER tous les changements de langue ultérieurs
    if (isInitializedRef.current && sessionLanguageRef.current) {
      if (language !== sessionLanguageRef.current) {
        console.log('🚫 [ZohoSalesIQ] CHANGEMENT DE LANGUE IGNORÉ:', sessionLanguageRef.current, '→', language)
        console.log('📌 [ZohoSalesIQ] Widget reste en:', sessionLanguageRef.current)
        console.log('💡 [ZohoSalesIQ] Nouvelle langue sera effective à la prochaine session')
      } else {
        console.log('👍 [ZohoSalesIQ] Langue inchangée, widget stable')
      }
      
      return
    }
    
  }, [language, user?.email, loadZohoWithLanguage])

  // Nettoyage à la destruction du composant
  useEffect(() => {
    return () => {
      console.log('🧹 [ZohoSalesIQ] Destruction composant - nettoyage session')
      clearRetryTimeout()
      
      // Réinitialiser les refs pour la prochaine session
      isInitializedRef.current = false
      sessionLanguageRef.current = null
      widgetLoadedRef.current = false
      
      if (window.ZOHO_SESSION_LANGUAGE) {
        delete window.ZOHO_SESSION_LANGUAGE
      }
    }
  }, [clearRetryTimeout])

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
    ZOHO_SESSION_LANGUAGE?: string
  }
}