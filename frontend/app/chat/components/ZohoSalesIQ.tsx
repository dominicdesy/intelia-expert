// components/ZohoSalesIQ.tsx - CORRECTION pour changement de langue

import { useEffect, useRef } from 'react'

interface ZohoSalesIQProps {
  user: any
  language: string
}

export const ZohoSalesIQ: React.FC<ZohoSalesIQProps> = ({ user, language }) => {
  const isInitializedRef = useRef(false)
  const currentLanguageRef = useRef(language)
  const widgetLoadedRef = useRef(false)

  // ✅ CORRECTION: Effet pour gérer le changement de langue
  useEffect(() => {
    console.log('🌐 [ZohoSalesIQ] Changement de langue détecté:', currentLanguageRef.current, '→', language)
    
    // Si la langue a changé et le widget était déjà chargé, on le recharge
    if (widgetLoadedRef.current && currentLanguageRef.current !== language) {
      console.log('🔄 [ZohoSalesIQ] Rechargement du widget pour nouvelle langue:', language)
      
      // Nettoyer l'ancien widget
      cleanupZoho()
      
      // Petite pause pour s'assurer que le nettoyage est terminé
      setTimeout(() => {
        currentLanguageRef.current = language
        loadZohoWithLanguage(language)
      }, 500)
      
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

  const cleanupZoho = () => {
    console.log('🧹 [ZohoSalesIQ] NETTOYAGE pour changement de langue')
    
    try {
      // Cacher le widget
      if (window.$zoho && window.$zoho.salesiq && window.$zoho.salesiq.floatwindow) {
        window.$zoho.salesiq.floatwindow.visible('hide')
      }
      
      // Supprimer les scripts existants
      const existingScripts = document.querySelectorAll('script[src*="salesiq.zohopublic.com"]')
      existingScripts.forEach(script => {
        console.log('🗑️ [ZohoSalesIQ] Suppression script existant')
        script.remove()
      })
      
      // Supprimer les éléments DOM du widget
      const widgetElements = document.querySelectorAll('[id*="zsiq"], [class*="zsiq"], [id*="siq"]')
      widgetElements.forEach(element => {
        element.remove()
      })
      
      // Nettoyer l'objet global
      if (window.$zoho) {
        delete window.$zoho
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
        
        // Configuration du widget après chargement
        setTimeout(() => {
          configureWidget(lang)
        }, 1000)
      }
      
      script.onerror = (error) => {
        console.error('❌ [ZohoSalesIQ] Erreur chargement script:', error)
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
    const maxAttempts = 10
    
    const configureAttempt = () => {
      attempts++
      console.log(`🔧 [ZohoSalesIQ] Tentative de configuration ${attempts}/${maxAttempts}`)
      
      if (window.$zoho && window.$zoho.salesiq) {
        try {
          console.log('✅ [ZohoSalesIQ] Objet Zoho disponible, configuration...')
          
          // Configuration utilisateur
          if (user?.email) {
            window.$zoho.salesiq.visitor.info({
              'Email': user.email,
              'Name': user.name || user.email,
              'App Language': lang,
              'Widget Language': lang
            })
            console.log('👤 [ZohoSalesIQ] Info utilisateur configurée avec langue:', lang)
          }
          
          // Afficher le widget
          window.$zoho.salesiq.floatwindow.visible('show')
          console.log('👁️ [ZohoSalesIQ] Widget affiché')
          
          console.log('✅ [ZohoSalesIQ] Configuration terminée avec succès')
          
        } catch (error) {
          console.error('❌ [ZohoSalesIQ] Erreur configuration:', error)
        }
      } else if (attempts < maxAttempts) {
        console.log('⏳ [ZohoSalesIQ] Objet Zoho pas encore disponible, nouvelle tentative...')
        setTimeout(configureAttempt, 500)
      } else {
        console.error('❌ [ZohoSalesIQ] Échec configuration après', maxAttempts, 'tentatives')
      }
    }
    
    configureAttempt()
  }

  // Nettoyage à la destruction du composant
  useEffect(() => {
    return () => {
      console.log('🧹 [ZohoSalesIQ] Nettoyage à la destruction du composant')
      cleanupZoho()
    }
  }, [])

  return null
}

// Types pour TypeScript
declare global {
  interface Window {
    $zoho: any
  }
}