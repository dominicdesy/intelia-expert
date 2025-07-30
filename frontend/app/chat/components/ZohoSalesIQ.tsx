// components/ZohoSalesIQ.tsx - VERSION STABLE avec protection boucle infinie

import { useEffect, useRef, useCallback } from 'react'

interface ZohoSalesIQProps {
  user: any
  language: string
}

export const ZohoSalesIQ: React.FC<ZohoSalesIQProps> = ({ user, language }) => {
  const isInitializedRef = useRef(false)
  const currentLanguageRef = useRef<string | null>(null)
  const widgetLoadedRef = useRef(false)
  const configurationAttemptsRef = useRef(0)
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isConfiguring = useRef(false)

  // ✅ CORRECTION: Mémoisation de la fonction de nettoyage
  const clearRetryTimeout = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
  }, [])

  const cleanupZoho = useCallback(() => {
    console.log('🧹 [ZohoSalesIQ] NETTOYAGE complet')
    
    try {
      // Nettoyer les timeouts
      clearRetryTimeout()
      isConfiguring.current = false
      configurationAttemptsRef.current = 0
      
      // Cacher le widget si disponible
      if (window.$zoho?.salesiq?.floatwindow) {
        try {
          window.$zoho.salesiq.floatwindow.visible('hide')
        } catch (e) {
          console.warn('⚠️ [ZohoSalesIQ] Erreur hide widget:', e)
        }
      }
      
      // Supprimer les scripts existants
      const existingScripts = document.querySelectorAll('script[src*="salesiq.zohopublic.com"]')
      existingScripts.forEach(script => {
        console.log('🗑️ [ZohoSalesIQ] Suppression script existant')
        script.remove()
      })
      
      // Supprimer les éléments DOM du widget
      const selectors = [
        '[id*="zsiq"]', '[class*="zsiq"]', '[id*="siq"]', '[class*="siq"]',
        '#salesiq-chat', '.salesiq-widget', '.zoho-salesiq'
      ]
      
      selectors.forEach(selector => {
        const elements = document.querySelectorAll(selector)
        elements.forEach(element => element.remove())
      })
      
      // Nettoyer les objets globaux
      if (window.$zoho) {
        try {
          delete window.$zoho
        } catch (e) {
          window.$zoho = undefined
        }
      }
      
      if (window.zsiqd) {
        delete window.zsiqd
      }
      
      // Réinitialiser les refs
      widgetLoadedRef.current = false
      
      console.log('✅ [ZohoSalesIQ] Nettoyage terminé')
      
    } catch (error) {
      console.error('❌ [ZohoSalesIQ] Erreur lors du nettoyage:', error)
    }
  }, [clearRetryTimeout])

  const configureWidget = useCallback((lang: string) => {
    if (isConfiguring.current) {
      console.log('⚠️ [ZohoSalesIQ] Configuration déjà en cours, ignoré')
      return
    }
    
    console.log('🔧 [ZohoSalesIQ] Configuration du widget pour langue:', lang)
    isConfiguring.current = true
    configurationAttemptsRef.current = 0
    
    const maxAttempts = 15
    const checkInterval = 1500
    
    const configureAttempt = () => {
      configurationAttemptsRef.current++
      console.log(`🔧 [ZohoSalesIQ] Tentative ${configurationAttemptsRef.current}/${maxAttempts}`)
      
      // ✅ CORRECTION: Vérification plus stricte
      if (window.$zoho && 
          window.$zoho.salesiq && 
          typeof window.$zoho.salesiq.visitor?.info === 'function' &&
          typeof window.$zoho.salesiq.floatwindow?.visible === 'function') {
        
        try {
          console.log('✅ [ZohoSalesIQ] Objet Zoho disponible, configuration...')
          
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
            console.log('👤 [ZohoSalesIQ] Info utilisateur configurée')
          }
          
          // Afficher le widget après un délai
          setTimeout(() => {
            try {
              if (window.$zoho?.salesiq?.floatwindow) {
                window.$zoho.salesiq.floatwindow.visible('show')
                console.log('👁️ [ZohoSalesIQ] Widget affiché')
              }
            } catch (showError) {
              console.error('❌ [ZohoSalesIQ] Erreur affichage:', showError)
            }
          }, 1000)
          
          console.log('✅ [ZohoSalesIQ] Configuration terminée avec succès')
          isConfiguring.current = false
          return
          
        } catch (error) {
          console.error('❌ [ZohoSalesIQ] Erreur configuration:', error)
        }
      }
      
      // Continuer les tentatives ou abandonner
      if (configurationAttemptsRef.current < maxAttempts) {
        console.log('⏳ [ZohoSalesIQ] Objet Zoho indisponible, retry...')
        
        retryTimeoutRef.current = setTimeout(configureAttempt, checkInterval)
        
      } else {
        console.error('❌ [ZohoSalesIQ] Échec configuration après', maxAttempts, 'tentatives')
        isConfiguring.current = false
        
        // ✅ NOUVEAU: Vérifier s'il y a un problème avec le script Zoho
        const zohoScript = document.querySelector('script[src*="salesiq.zohopublic.com"]')
        if (zohoScript) {
          console.log('⚠️ [ZohoSalesIQ] Script présent mais $zoho indisponible - problème Zoho')
          console.log('🔄 [ZohoSalesIQ] Tentative de rechargement complet dans 10s...')
          
          setTimeout(() => {
            if (!isConfiguring.current) {
              cleanupZoho()
              setTimeout(() => loadZohoWithLanguage(lang), 2000)
            }
          }, 10000)
        }
      }
    }
    
    configureAttempt()
  }, [user, cleanupZoho])

  const loadZohoWithLanguage = useCallback((lang: string) => {
    console.log('🚀 [ZohoSalesIQ] Chargement widget langue:', lang)
    
    if (!user?.email) {
      console.warn('⚠️ [ZohoSalesIQ] Pas d\'utilisateur, abandon')
      return
    }

    // ✅ CORRECTION: Vérifier si un script est déjà en cours de chargement
    const existingScript = document.querySelector('script[src*="salesiq.zohopublic.com"]')
    if (existingScript && !widgetLoadedRef.current) {
      console.log('⚠️ [ZohoSalesIQ] Script déjà en cours de chargement, attente...')
      return
    }

    try {
      const localeMap: { [key: string]: string } = {
        'fr': 'fr',
        'en': 'en', 
        'es': 'es'
      }
      
      const zohoLocale = localeMap[lang] || 'en'
      
      const script = document.createElement('script')
      script.type = 'text/javascript'
      script.async = true
      script.defer = true
      
      const timestamp = Date.now()
      script.src = `https://salesiq.zohopublic.com/widget?wc=siq31d58179214fbbfbb0a5b5eb16ab9173ba0ee84601e9d7d04840d96541bc7e4f&locale=${zohoLocale}&t=${timestamp}`
      
      console.log('📡 [ZohoSalesIQ] Chargement:', script.src)
      
      let loadTimeout: NodeJS.Timeout
      
      script.onload = () => {
        console.log('✅ [ZohoSalesIQ] Script chargé - locale:', zohoLocale)
        clearTimeout(loadTimeout)
        widgetLoadedRef.current = true
        
        // Attendre que Zoho s'initialise
        setTimeout(() => {
          if (!isConfiguring.current) {
            configureWidget(lang)
          }
        }, 3000)
      }
      
      script.onerror = (error) => {
        console.error('❌ [ZohoSalesIQ] Erreur chargement script:', error)
        clearTimeout(loadTimeout)
        
        // Retry après erreur
        setTimeout(() => {
          if (!isConfiguring.current) {
            console.log('🔄 [ZohoSalesIQ] Retry après erreur')
            loadZohoWithLanguage(lang)
          }
        }, 10000)
      }
      
      // Timeout si le script ne se charge pas
      loadTimeout = setTimeout(() => {
        console.error('❌ [ZohoSalesIQ] Timeout chargement script')
        script.remove()
      }, 30000)
      
      document.head.appendChild(script)
      
    } catch (error) {
      console.error('❌ [ZohoSalesIQ] Erreur création script:', error)
    }
  }, [user, configureWidget])

  // ✅ CORRECTION: Effet principal avec protection boucle infinie
  useEffect(() => {
    console.log('🌐 [ZohoSalesIQ] Effet déclenché - Langue:', language, 'User:', !!user?.email)
    
    // Protection contre les changements inutiles
    if (currentLanguageRef.current === language && isInitializedRef.current) {
      console.log('👍 [ZohoSalesIQ] Pas de changement nécessaire')
      return
    }
    
    // Si changement de langue sur widget déjà chargé
    if (widgetLoadedRef.current && currentLanguageRef.current !== language) {
      console.log('🔄 [ZohoSalesIQ] Rechargement pour nouvelle langue:', language)
      
      currentLanguageRef.current = language
      clearRetryTimeout()
      isConfiguring.current = false
      cleanupZoho()
      
      setTimeout(() => {
        loadZohoWithLanguage(language)
      }, 2000)
      
      return
    }
    
    // Première initialisation
    if (!isInitializedRef.current && user?.email) {
      console.log('🎯 [ZohoSalesIQ] PREMIÈRE INITIALISATION')
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
      isConfiguring.current = false
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
        visitor?: {
          info: (data: any) => void
        }
        floatwindow?: {
          visible: (action: 'show' | 'hide') => void
        }
      }
    }
    zsiqd?: any
  }
}