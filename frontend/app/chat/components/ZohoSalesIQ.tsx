import React, { useState, useEffect, useRef } from 'react'

interface ZohoSalesIQProps {
  user: any
  language: string
}

// ==================== COMPOSANT ZOHO SALESIQ - VERSION CORRIGÉE V6 ====================
export const ZohoSalesIQ: React.FC<ZohoSalesIQProps> = ({ user, language }) => {
  const [isZohoReady, setIsZohoReady] = useState(false)
  const [hasError, setHasError] = useState(false)
  const initializationRef = useRef(false)
  const lastLanguageRef = useRef<string>('')
  const isReloadingRef = useRef(false)
  const currentScriptRef = useRef<HTMLScriptElement | null>(null)
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const configureAttemptsRef = useRef(0) // ✅ NOUVEAU : Compteur de tentatives
  
  // Fonction pour mapper les codes de langue vers les codes Zoho
  const getZohoLanguage = (lang: string): string => {
    const languageMap: Record<string, string> = {
      'fr': 'fr',      // Français
      'en': 'en',      // English  
      'es': 'es'       // Español
    }
    return languageMap[lang] || 'en'
  }
  
  // Fonction pour nettoyer complètement Zoho
  const cleanupZoho = () => {
    console.log('🧹 [ZohoSalesIQ] DEBUT nettoyage complet de Zoho')
    
    // Supprimer le script existant avec référence
    if (currentScriptRef.current) {
      currentScriptRef.current.remove()
      currentScriptRef.current = null
      console.log('🗑️ [ZohoSalesIQ] Script référencé supprimé')
    }
    
    // Supprimer tous les scripts Zoho qui pourraient traîner
    document.querySelectorAll('script[src*="salesiq.zohopublic.com"]').forEach(script => {
      script.remove()
    })
    
    // Supprimer tous les widgets Zoho (recherche plus extensive)
    const zohoSelectors = [
      '[id*="zsiq"]', '[class*="zsiq"]', '[id*="siq"]', '[class*="siq"]',
      '[id*="zoho"]', '[class*="zoho"]', '[data-widget*="zoho"]'
    ]
    
    zohoSelectors.forEach(selector => {
      document.querySelectorAll(selector).forEach(el => {
        el.remove()
      })
    })
    console.log('🧹 [ZohoSalesIQ] Tous widgets Zoho supprimés')
    
    // Nettoyer l'objet global complètement (avec protection supplémentaire)
    const globalWindow = window as any
    if (globalWindow.$zoho) {
      delete globalWindow.$zoho
      globalWindow.$zoho = undefined  // Protection supplémentaire contre les fuites
      console.log('🧹 [ZohoSalesIQ] Objet global $zoho supprimé et undefined')
    }
    
    // Réinitialiser les états
    setIsZohoReady(false)
    setHasError(false)
    console.log('🔄 [ZohoSalesIQ] États réinitialisés')
  }
  
  // Fonction pour charger Zoho avec une langue spécifique
  const loadZohoWithLanguage = (targetLanguage: string) => {
    if (isReloadingRef.current) {
      console.log('🔄 [ZohoSalesIQ] Rechargement déjà en cours, ignoré')
      return
    }
    
    isReloadingRef.current = true
    configureAttemptsRef.current = 0 // ✅ RESET : Nouveau chargement = reset compteur
    console.log('🚀 [ZohoSalesIQ] DEBUT loadZohoWithLanguage avec langue:', targetLanguage)
    console.log('👤 [ZohoSalesIQ] User présent:', !!user, user?.email)
    
    const zohoLang = getZohoLanguage(targetLanguage)
    const globalWindow = window as any
    
    // ✅ NOUVELLE APPROCHE : Configurer $zoho APRÈS le chargement du script
    const configureZohoWidget = () => {
      configureAttemptsRef.current++
      console.log(`🔧 [ZohoSalesIQ] Configuration post-chargement du widget... (Tentative ${configureAttemptsRef.current})`)
      
      // ✅ MONITORING : Vérifier le nombre de tentatives
      if (configureAttemptsRef.current > 3) {
        console.error('❌ [ZohoSalesIQ] Impossible d\'initialiser le widget après 3 tentatives.')
        setHasError(true)
        isReloadingRef.current = false
        return
      }
      
      try {
        const zoho = globalWindow.$zoho?.salesiq
        if (zoho) {
          console.log('✅ [ZohoSalesIQ] Objet Zoho disponible, configuration...')
          
          // Configuration des informations utilisateur si disponible
          if (user && zoho.visitor?.info) {
            zoho.visitor.info({
              name: user.name || 'Utilisateur Intelia',
              email: user.email || ''
            })
            console.log('👤 [ZohoSalesIQ] Info utilisateur configurée pour:', user.email)
          }
          
          // Configuration du widget pour éviter l'ouverture automatique
          if (zoho.chat && zoho.chat.window) {
            zoho.chat.window('hide') // S'assurer que la fenêtre est fermée
          }
          
          // Afficher le bouton flotant
          if (zoho.floatbutton?.visible) {
            zoho.floatbutton.visible('show')
            console.log('👁️ [ZohoSalesIQ] Bouton flotant affiché')
          }
          
          // ✅ SUGGESTION 2 : Vérifier si le widget est effectivement visible
          if (document.querySelectorAll('[id*="zsiq"]').length === 0) {
            console.warn('🚫 [ZohoSalesIQ] Aucune trace de widget visible après configuration. Tentative de réaffichage forcée.')
            if (zoho.floatbutton?.visible) {
              zoho.floatbutton.visible('show')
            }
          }
          
          // ✅ SUCCÈS : Réinitialiser le compteur
          configureAttemptsRef.current = 0
          setIsZohoReady(true)
          setHasError(false)
          console.log('✅ [ZohoSalesIQ] Widget complètement initialisé et visible')
        } else {
          console.warn(`⚠️ [ZohoSalesIQ] Objet Zoho pas encore disponible, tentative ${configureAttemptsRef.current}/3 dans 500ms...`)
          // Réessayer si Zoho n'est pas encore prêt
          setTimeout(configureZohoWidget, 500)
        }
      } catch (error) {
        console.error(`❌ [ZohoSalesIQ] Erreur configuration (tentative ${configureAttemptsRef.current}/3):`, error)
        
        // Si c'est la dernière tentative, marquer comme erreur
        if (configureAttemptsRef.current >= 3) {
          setHasError(true)
        } else {
          // Sinon, réessayer
          setTimeout(configureZohoWidget, 1000)
        }
      } finally {
        // Ne réinitialiser isReloadingRef que si on arrête les tentatives
        if (configureAttemptsRef.current >= 3 || isZohoReady) {
          isReloadingRef.current = false
          console.log('🔄 [ZohoSalesIQ] isReloadingRef réinitialisé')
        }
      }
    }
    
    // ✅ Configuration minimale AVANT le chargement du script
    globalWindow.$zoho = {
      salesiq: {
        widgetcode: 'siq31d58179214fbbfbb0a5b5eb16ab9173ba0ee84601e9d7d04840d96541bc7e4f',
        values: {
          showLauncher: true,
          showChat: false,
          autoOpen: false,
          floatbutton: 'show'
        },
        ready: function() {
          console.log('✅ [ZohoSalesIQ] Callback ready déclenché avec langue:', zohoLang)
          // Attendre un peu puis configurer
          setTimeout(configureZohoWidget, 800)
        }
      }
    }
    
    // Créer et charger le script Zoho
    const script = document.createElement('script')
    script.type = 'text/javascript'
    script.async = true
    script.defer = true
    script.src = `https://salesiq.zohopublic.com/widget?wc=${globalWindow.$zoho.salesiq.widgetcode}&locale=${zohoLang}&t=${Date.now()}`
    
    console.log('📡 [ZohoSalesIQ] URL script avec locale:', script.src)
    
    script.onload = () => {
      console.log('✅ [ZohoSalesIQ] Script chargé avec succès pour locale:', zohoLang)
      
      // ✅ FALLBACK : Si ready n'est pas appelé dans les 3 secondes, forcer la configuration
      setTimeout(() => {
        if (!isZohoReady && !hasError) {
          console.warn('⚠️ [ZohoSalesIQ] Ready non déclenché, tentative forcée de configuration')
          if ((window as any).$zoho?.salesiq) {
            configureZohoWidget()
          } else {
            console.error('❌ [ZohoSalesIQ] $zoho.salesiq encore indisponible après script.onload')
          }
        }
      }, 3000)
    }
    
    script.onerror = () => {
      console.error('❌ [ZohoSalesIQ] Erreur chargement script pour locale:', zohoLang)
      setHasError(true)
      isReloadingRef.current = false
    }
    
    // Sauvegarder la référence et ajouter au DOM
    currentScriptRef.current = script
    document.head.appendChild(script)
    console.log('📝 [ZohoSalesIQ] Script ajouté au DOM avec référence')
  }
  
  // Fonction pour recharger Zoho avec une nouvelle langue (avec debounce)
  const reloadZohoWithLanguage = (newLanguage: string) => {
    console.log('🔄 [ZohoSalesIQ] DEBUT reloadZohoWithLanguage avec langue:', newLanguage)
    console.log('👤 [ZohoSalesIQ] User disponible pour rechargement:', !!user, user?.email || 'N/A')
    
    // 1. Nettoyer complètement
    cleanupZoho()
    
    // ✅ NOUVELLE PROTECTION : Vérifier qu'aucun autre rechargement n'est en cours
    if (isReloadingRef.current) {
      console.warn('⚠️ [ZohoSalesIQ] Un autre rechargement est en cours, skip.')
      return
    }
    
    // 2. Attendre puis recharger
    setTimeout(() => {
      console.log('⏰ [ZohoSalesIQ] Démarrage rechargement après nettoyage')
      loadZohoWithLanguage(newLanguage)
    }, 800)
  }
  
  // ✅ CORRECTION PRINCIPALE : UseEffect séparé pour initialisation et changements
  useEffect(() => {
    if (!language) {
      console.log('⏭️ [ZohoSalesIQ] Pas de langue fournie, initialisation reportée')
      return
    }
    
    console.log('🌐 [ZohoSalesIQ] Changement de langue détecté:', language)
    console.log('📊 [ZohoSalesIQ] État actuel - initialisé:', initializationRef.current, 'dernière langue:', lastLanguageRef.current)
    
    // ✅ LOGIQUE CORRIGÉE
    if (!initializationRef.current) {
      // ✅ PREMIÈRE INITIALISATION
      console.log('🎯 [ZohoSalesIQ] PREMIÈRE INITIALISATION avec langue:', language)
      initializationRef.current = true
      lastLanguageRef.current = language
      
      // Debounce pour la première fois aussi
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current)
      }
      
      debounceTimeoutRef.current = setTimeout(() => {
        loadZohoWithLanguage(language)
        debounceTimeoutRef.current = null
      }, 300)
      
    } else if (language !== lastLanguageRef.current) {
      // ✅ CHANGEMENT DE LANGUE
      console.log('🔄 [ZohoSalesIQ] CHANGEMENT DE LANGUE détecté:', lastLanguageRef.current, '→', language)
      
      // Annuler le debounce en cours
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current)
        console.log('🚫 [ZohoSalesIQ] Debounce annulé pour changement de langue')
      }
      
      // Mettre à jour la référence AVANT le rechargement
      lastLanguageRef.current = language
      
      // Programmer le rechargement avec debounce
      debounceTimeoutRef.current = setTimeout(() => {
        console.log('⏰ [ZohoSalesIQ] Exécution rechargement après debounce pour langue:', language)
        reloadZohoWithLanguage(language)
        debounceTimeoutRef.current = null
      }, 300)
      
    } else {
      console.log('✅ [ZohoSalesIQ] Langue inchangée, pas d\'action requise')
    }
    
  }, [language]) // Réagit seulement aux changements de la prop language

  // Cleanup à la destruction du composant
  useEffect(() => {
    return () => {
      console.log('🧹 [ZohoSalesIQ] Nettoyage à la destruction du composant')
      
      // Annuler le debounce en cours
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current)
        debounceTimeoutRef.current = null
      }
      
      cleanupZoho()
      
      // Réinitialiser les refs pour éviter les fuites
      initializationRef.current = false
      lastLanguageRef.current = ''
      isReloadingRef.current = false
    }
  }, [])

  return null
}