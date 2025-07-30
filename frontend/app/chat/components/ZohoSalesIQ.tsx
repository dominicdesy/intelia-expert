import React, { useEffect, useRef } from 'react'

interface ZohoSalesIQProps {
  user: any
  language: string
}

// ==================== FIX IMMÉDIAT - WIDGET STABLE ====================
export const ZohoSalesIQ: React.FC<ZohoSalesIQProps> = ({ user, language }) => {
  const initializationRef = useRef(false)
  const currentLanguageRef = useRef<string>('')
  
  // ✅ SOLUTION IMMÉDIATE : Widget fixe sans rechargement
  const initializeZohoOnce = () => {
    if (initializationRef.current) {
      console.log('✅ [ZohoFix] Widget déjà initialisé, pas de rechargement')
      return
    }
    
    initializationRef.current = true
    console.log('🚀 [ZohoFix] Initialisation unique du widget')
    
    const globalWindow = window as any
    
    // Déterminer la langue basée sur la langue actuelle
    const widgetLanguage = getWidgetLanguage(language)
    currentLanguageRef.current = widgetLanguage
    
    // Configuration unique et stable - JAMAIS supprimée
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
          console.log('✅ [ZohoFix] Widget prêt en langue:', widgetLanguage)
          
          setTimeout(() => {
            try {
              const zoho = globalWindow.$zoho?.salesiq
              if (zoho) {
                // Configuration utilisateur avec langue info
                updateUserInfo(zoho, user, language)
                
                // Afficher le widget
                if (zoho.floatbutton?.visible) {
                  zoho.floatbutton.visible('show')
                  console.log('✅ [ZohoFix] Widget visible et stable')
                }
                
              } else {
                console.error('❌ [ZohoFix] Objet Zoho indisponible')
              }
            } catch (error) {
              console.error('❌ [ZohoFix] Erreur configuration:', error)
            }
          }, 1000)
        }
      }
    }
    
    // Charger le script UNE SEULE FOIS
    const script = document.createElement('script')
    script.type = 'text/javascript'
    script.async = true
    script.defer = true
    script.src = `https://salesiq.zohopublic.com/widget?wc=${globalWindow.$zoho.salesiq.widgetcode}&locale=${widgetLanguage}`
    
    console.log('📡 [ZohoFix] Chargement widget stable avec locale:', widgetLanguage)
    
    script.onload = () => {
      console.log('✅ [ZohoFix] Script chargé avec succès - STABLE')
    }
    
    script.onerror = () => {
      console.error('❌ [ZohoFix] Erreur chargement script')
      initializationRef.current = false // Permettre retry
    }
    
    document.head.appendChild(script)
  }
  
  // ✅ LOGIQUE LANGUE : Prioriser selon usage
  const getWidgetLanguage = (currentLang: string): string => {
    // Option 1: Toujours français (plus stable)
    // return 'fr'
    
    // Option 2: Langue dynamique mais SANS rechargement
    const languageMap = {
      'fr': 'fr',
      'en': 'en',  
      'es': 'fr'  // Fallback vers français si espagnol pas supporté
    }
    
    return languageMap[currentLang as keyof typeof languageMap] || 'fr'
  }
  
  // ✅ MISE À JOUR INFO UTILISATEUR (sans rechargement widget)
  const updateUserInfo = (zoho: any, userData: any, currentLanguage: string) => {
    if (!userData || !zoho.visitor?.info) return
    
    try {
      zoho.visitor.info({
        name: userData.name || 'Utilisateur Intelia',
        email: userData.email || '',
        // Informations importantes pour le support
        app_language: currentLanguage,
        widget_language: currentLanguageRef.current,
        user_type: userData.user_type || 'standard',
        timestamp: new Date().toISOString()
      })
      
      console.log('👤 [ZohoFix] Info utilisateur mise à jour:', {
        email: userData.email,
        app_language: currentLanguage,
        widget_language: currentLanguageRef.current
      })
    } catch (error) {
      console.error('❌ [ZohoFix] Erreur mise à jour utilisateur:', error)
    }
  }
  
  // ✅ EFFET PRINCIPAL : Initialiser UNE SEULE FOIS
  useEffect(() => {
    initializeZohoOnce()
  }, []) // AUCUNE dépendance = jamais de rechargement
  
  // ✅ EFFET SÉPARÉ : Mise à jour info utilisateur/langue
  useEffect(() => {
    if (!initializationRef.current) return
    
    // Attendre que Zoho soit prêt puis mettre à jour les infos
    const updateInfo = () => {
      const globalWindow = window as any
      const zoho = globalWindow.$zoho?.salesiq
      
      if (zoho && zoho.visitor?.info) {
        updateUserInfo(zoho, user, language)
      } else {
        console.log('⏳ [ZohoFix] Zoho pas encore prêt pour mise à jour info')
      }
    }
    
    // Délai pour s'assurer que Zoho est prêt
    const timer = setTimeout(updateInfo, 2000)
    
    return () => clearTimeout(timer)
  }, [user, language]) // Réagit aux changements pour mise à jour info seulement
  
  // ✅ PAS DE CLEANUP AGRESSIF
  useEffect(() => {
    return () => {
      console.log('🧹 [ZohoFix] Cleanup minimal - widget reste stable')
      // Volontairement minimal pour éviter les conflits
      // Ne pas supprimer $zoho pour éviter les erreurs WebSocket
    }
  }, [])

  return null
}

// ==================== INSTRUCTIONS D'UTILISATION ====================
/*
REMPLACEMENT IMMÉDIAT :

1. Remplacer l'import existant :
   import { ZohoSalesIQ } from './components/ZohoSalesIQ'

2. Usage identique - aucun changement requis :
   <ZohoSalesIQ user={user} language={currentLanguage} />

3. Comportement :
   - Widget se charge UNE FOIS dans la langue appropriée
   - Info utilisateur mise à jour quand langue/user change
   - Équipe support voit la langue actuelle de l'app
   - AUCUN rechargement = AUCUNE erreur WebSocket

4. Support multilingue :
   - Widget affiché dans langue appropriée (fr/en)
   - Info utilisateur contient app_language pour le support
   - Équipe peut répondre dans la bonne langue

RÉSULTAT :
✅ Erreur "Cannot read properties of undefined" ÉLIMINÉE
✅ Widget stable et fonctionnel
✅ Pas de rechargement = pas de problème
✅ Support multilingue via info utilisateur
*/