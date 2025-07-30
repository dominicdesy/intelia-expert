// components/ZohoSalesIQ.tsx - VERSION ROBUSTE avec gestion d'erreurs

import { useEffect, useRef } from 'react'

interface ZohoSalesIQProps {
  user: any
  language: string
}

export const ZohoSalesIQ: React.FC<ZohoSalesIQProps> = ({ user, language }) => {
  const isInitializedRef = useRef(false)
  const currentLanguageRef = useRef(language)
  const widgetLoadedRef = useRef(false)
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // ✅ CORRECTION: Effet pour gérer le changement de langue
  useEffect(() => {
    console.log('🌐 [ZohoSalesIQ] Changement de langue détecté:', currentLanguageRef.current, '→', language)
    
    // Si la langue a changé et le widget était déjà chargé, on le recharge
    if (widgetLoadedRef.current && currentLanguageRef.current !== language) {
      console.log('🔄 [ZohoSalesIQ] Rechargement du widget pour nouvelle langue:', language)
      
      // Nettoyer timeouts en cours
      clearRetryTimeout()
      
      // Nettoyer l'ancien widget
      cleanupZoho()
      
      // Petite pause pour s'assurer que le nettoyage est terminé
      setTimeout(() => {
        currentLanguageRef.current = language
        loadZohoWithLanguage(language)
      }, 1000) // Augmenté à 1s pour plus de sécurité
      
      return
    }
    
    // Première initialisation
    if (!isInitializedRef.current && user?.email) {
      console.log('🎯 [ZohoSalesIQ] PREMIÈRE INITIALISATION avec langue:', language)
      isInitializedRef.current = true
      currentLanguageRef.current = language
      loadZohoWithLanguage(language)
    }
    
  }, [language, user])

  const clearRetryTimeout = () => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
  }

  const cleanupZoho = () => {
    console.log('🧹 [ZohoSalesIQ] NETTOYAGE pour changement de langue')
    
    try {
      // Nettoyer les timeouts
      clearRetryTimeout()
      
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
      
      // Supprimer les éléments DOM du widget (plus complet)
      const selectors = [
        '[id*="zsiq"]', '[class*="zsiq"]', '[id*="siq"]', '[class*="siq"]',
        '#salesiq-chat', '.salesiq-widget', '.zoho-salesiq'
      ]
      
      selectors.forEach(selector => {
        const elements = document.querySelectorAll(selector)
        elements.forEach(element => {
          element.remove()
        })
      })
      
      // Nettoyer l'objet global plus en profondeur
      if (window.$zoho) {
        try {
          delete window.$zoho
        } catch (e) {
          // Fallback si delete échoue
          window.$zoho = undefined
        }
      }
      
      // Nettoyer les variables globales Zoho potentielles
      if (window.zsiqd) {
        delete window.zsiqd
      }
      
      // Réinitialiser les refs
      widgetLoadedRef.current = false
      
      console.log('✅ [ZohoSalesIQ] Nettoyage terminé')
      
    } catch (error) {
      console.error('❌ [ZohoSalesIQ] Erreur lors du nettoyage:', error)
    }
  }

  const loadZohoWithLanguage = (lang: string) => {
    console.log('🚀 [ZohoSalesIQ] Chargement du widget avec langue:', lang)
    
    if (!user?.email) {
      console.warn('⚠️ [ZohoSalesIQ] Pas d\'utilisateur, chargement annulé')
      return
    }

    try {
      // Mapper les langues vers les locales Zoho
      const localeMap: { [key: string]: string } = {
        'fr': 'fr',
        'en': 'en', 
        'es': 'es'
      }
      
      const zohoLocale = localeMap[lang] || 'en'
      
      console.log('🌍 [ZohoSalesIQ] Locale Zoho sélectionnée:', zohoLocale)
      
      // Créer le script avec la bonne locale
      const script = document.createElement('script')
      script.type = 'text/javascript'
      script.async = true
      script.defer = true
      
      const timestamp = Date.now()
      script.src = `https://salesiq.zohopublic.com/widget?wc=siq31d58179214fbbfbb0a5b5eb16ab9173ba0ee84601e9d7d04840d96541bc7e4f&locale=${zohoLocale}&t=${timestamp}`
      
      console.log('📡 [ZohoSalesIQ] URL script avec locale:', script.src)
      
      // Callback quand le script est chargé
      script.onload = () => {
        console.log('✅ [ZohoSalesIQ] Script chargé avec succès pour locale:', zohoLocale)
        widgetLoadedRef.current = true
        
        // ✅ CORRECTION: Attendre plus longtemps pour que Zoho s'initialise
        setTimeout(() => {
          configureWidget(lang)
        }, 2000) // Augmenté à 2 secondes
      }
      
      script.onerror = (error) => {
        console.error('❌ [ZohoSalesIQ] Erreur chargement script:', error)
        
        // ✅ NOUVEAU: Retry après erreur
        retryTimeoutRef.current = setTimeout(() => {
          console.log('🔄 [ZohoSalesIQ] Retry après erreur de chargement')
          loadZohoWithLanguage(lang)
        }, 5000)
      }
      
      // Ajouter le script au DOM
      document.head.appendChild(script)
      console.log('📝 [ZohoSalesIQ] Script ajouté au DOM')
      
    } catch (error) {
      console.error('❌ [ZohoSalesIQ] Erreur lors du chargement:', error)
    }
  }

  const configureWidget = (lang: string) => {
    console.log('🔧 [ZohoSalesIQ] Configuration du widget pour langue:', lang)
    
    let attempts = 0
    const maxAttempts = 20 // ✅ CORRECTION: Plus de tentatives
    const checkInterval = 1000 // ✅ CORRECTION: Intervalle plus long
    
    const configureAttempt = () => {
      attempts++
      console.log(`🔧 [ZohoSalesIQ] Tentative de configuration ${attempts}/${maxAttempts}`)
      
      // ✅ CORRECTION: Vérification plus robuste
      if (window.$zoho && 
          window.$zoho.salesiq && 
          typeof window.$zoho.salesiq.visitor !== 'undefined' &&
          typeof window.$zoho.salesiq.floatwindow !== 'undefined') {
        
        try {
          console.log('✅ [ZohoSalesIQ] Objet Zoho disponible, configuration...')
          
          // ✅ CORRECTION: Configuration utilisateur plus défensive
          if (user?.email) {
            const visitorInfo = {
              'Email': user.email,
              'Name': user.name || user.email.split('@')[0],
              'App Language': lang,
              'Widget Language': lang,
              'User ID': user.id || 'unknown'
            }
            
            console.log('👤 [ZohoSalesIQ] Configuration visiteur:', visitorInfo)
            window.$zoho.salesiq.visitor.info(visitorInfo)
            console.log('👤 [ZohoSalesIQ] Info utilisateur configurée avec langue:', lang)
          }
          
          // ✅ CORRECTION: Attendre un peu avant d'afficher
          setTimeout(() => {
            try {
              if (window.$zoho?.salesiq?.floatwindow) {
                window.$zoho.salesiq.floatwindow.visible('show')
                console.log('👁️ [ZohoSalesIQ] Widget affiché')
              }
            } catch (showError) {
              console.error('❌ [ZohoSalesIQ] Erreur affichage widget:', showError)
            }
          }, 500)
          
          console.log('✅ [ZohoSalesIQ] Configuration terminée avec succès')
          return // ✅ Sortir de la fonction
          
        } catch (error) {
          console.error('❌ [ZohoSalesIQ] Erreur configuration:', error)
          
          // ✅ NOUVEAU: Continuer les tentatives même après erreur
          if (attempts < maxAttempts) {
            retryTimeoutRef.current = setTimeout(configureAttempt, checkInterval)
          }
        }
      } else if (attempts < maxAttempts) {
        console.log('⏳ [ZohoSalesIQ] Objet Zoho pas encore disponible, nouvelle tentative...')
        
        // ✅ CORRECTION: Debug plus détaillé
        console.log('🔍 [ZohoSalesIQ] État Zoho:', {
          windowZoho: !!window.$zoho,
          salesiq: !!window.$zoho?.salesiq,
          visitor: typeof window.$zoho?.salesiq?.visitor,
          floatwindow: typeof window.$zoho?.salesiq?.floatwindow
        })
        
        retryTimeoutRef.current = setTimeout(configureAttempt, checkInterval)
        
      } else {
        console.error('❌ [ZohoSalesIQ] Échec configuration après', maxAttempts, 'tentatives')
        
        // ✅ NOUVEAU: Tentative de rechargement complet après échec
        console.log('🔄 [ZohoSalesIQ] Tentative de rechargement complet...')
        setTimeout(() => {
          cleanupZoho()
          setTimeout(() => loadZohoWithLanguage(lang), 2000)
        }, 3000)
      }
    }
    
    configureAttempt()
  }

  // Nettoyage à la destruction du composant
  useEffect(() => {
    return () => {
      console.log('🧹 [ZohoSalesIQ] Nettoyage à la destruction du composant')
      clearRetryTimeout()
      cleanupZoho()
    }
  }, [])

  return null
}

// ✅ CORRECTION: Types TypeScript plus complets
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