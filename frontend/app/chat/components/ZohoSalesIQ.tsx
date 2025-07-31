// components/ZohoSalesIQ.tsx - VERSION AVEC BOUTON FLOTTANT UNIQUEMENT

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
    
    const floatButton = document.querySelector('#zsiq_float') as HTMLElement
    if (floatButton && floatButton.classList.contains('zsiq-hide')) {
      console.log('📌 [ZohoSalesIQ] Retrait classe zsiq-hide pour rendre visible')
      floatButton.classList.remove('zsiq-hide')
      console.log('✅ [ZohoSalesIQ] Bouton flottant maintenant visible')
    }
  }, [])

  // ✅ NOUVEAU: Masquer automatiquement la fenêtre de chat si elle s'ouvre
  const hideZohoChatWindow = useCallback(() => {
    console.log('🔧 [ZohoSalesIQ] Vérification et masquage fenêtre chat si ouverte')
    
    // Masquer la fenêtre principale de chat si elle est ouverte
    const chatWindow = document.querySelector('#zsiq_agelif, .zsiq_theme1, .siq-widgetwindow') as HTMLElement
    if (chatWindow && !chatWindow.classList.contains('zsiq-hide')) {
      console.log('📌 [ZohoSalesIQ] Masquage fenêtre de chat automatiquement ouverte')
      
      // Tenter de fermer via l'API Zoho
      if (window.$zoho?.salesiq?.floatwindow) {
        try {
          window.$zoho.salesiq.floatwindow.visible('hide')
          console.log('✅ [ZohoSalesIQ] Fenêtre fermée via API Zoho')
        } catch (error) {
          console.warn('⚠️ [ZohoSalesIQ] Impossible de fermer via API:', error)
        }
      }
      
      // Backup: masquer via CSS
      chatWindow.classList.add('zsiq-hide')
      chatWindow.style.display = 'none'
      console.log('✅ [ZohoSalesIQ] Fenêtre masquée via CSS')
    }
    
    // S'assurer que le bouton flottant reste visible
    ensureFloatButtonVisible()
  }, [ensureFloatButtonVisible])

  // ✅ NOUVEAU: Fix accessibilité Microsoft Edge
  const fixZohoAccessibility = useCallback(() => {
    console.log('🔧 [ZohoSalesIQ] Application fixes accessibilité Microsoft Edge')
    
    // ✅ FIX 1: Interactive controls must not be nested
    const floatButton = document.querySelector('#zsiq_float') as HTMLElement
    if (floatButton) {
      // Supprimer les attributs role imbriqués problématiques
      const nestedControls = floatButton.querySelectorAll('[role="button"]')
      nestedControls.forEach((control, index) => {
        if (index > 0) { // Garder le premier, supprimer les autres
          control.removeAttribute('role')
          control.removeAttribute('tabindex')
          console.log('✅ [ZohoSalesIQ] Contrôle imbriqué corrigé')
        }
      })
      
      // S'assurer d'un seul point d'interaction
      if (!floatButton.getAttribute('aria-label')) {
        floatButton.setAttribute('aria-label', 'Ouvrir le support chat')
        floatButton.setAttribute('title', 'Ouvrir le support chat')
      }
      
      // Supprimer les éléments interactifs redondants
      const redundantButtons = floatButton.querySelectorAll('div[onclick], span[onclick]')
      redundantButtons.forEach(btn => {
        btn.removeAttribute('onclick')
        btn.removeAttribute('role')
        btn.removeAttribute('tabindex')
      })
    }

    // ✅ FIX 2: ARIA commands must have accessible name
    const interactiveElements = document.querySelectorAll('#zsiq_float [role="button"], .siqico-close, [class*="zsiq"][onclick]')
    interactiveElements.forEach(element => {
      if (!element.getAttribute('aria-label') && !element.getAttribute('aria-labelledby')) {
        const className = element.className
        let label = 'Élément interactif du chat'
        
        if (className.includes('close')) {
          label = 'Fermer le chat'
        } else if (className.includes('minimize')) {
          label = 'Réduire le chat'
        } else if (className.includes('maximize')) {
          label = 'Agrandir le chat'
        }
        
        element.setAttribute('aria-label', label)
        element.setAttribute('title', label)
        console.log('✅ [ZohoSalesIQ] aria-label ajouté:', label)
      }
    })

    // ✅ FIX 3: Supprimer les tabindex négatifs qui causent des problèmes
    const negativeTabIndex = document.querySelectorAll('[tabindex="-1"]')
    negativeTabIndex.forEach(element => {
      if (element.closest('#zsiq_float')) {
        element.removeAttribute('tabindex')
      }
    })
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
          
          // ✅ MODIFICATION PRINCIPALE: Ne pas auto-ouvrir le widget
          console.log('👁️ [ZohoSalesIQ] Widget configuré - BOUTON FLOTTANT UNIQUEMENT')
          
          // ✅ S'assurer que seul le bouton flottant est visible
          setTimeout(() => {
            ensureFloatButtonVisible()
            hideZohoChatWindow() // ✅ NOUVEAU: Masquer la fenêtre si elle s'ouvre
            fixZohoAccessibility()
          }, 1000)
          
          // ✅ VÉRIFICATION RÉPÉTÉE pour s'assurer que la fenêtre reste fermée
          setTimeout(() => {
            ensureFloatButtonVisible()
            hideZohoChatWindow() // ✅ NOUVEAU: Masquer à nouveau
            fixZohoAccessibility()
          }, 3000)
          
          // ✅ VÉRIFICATION FINALE
          setTimeout(() => {
            ensureFloatButtonVisible()
            hideZohoChatWindow() // ✅ NOUVEAU: Masquer une dernière fois
            fixZohoAccessibility()
          }, 8000)
          
          console.log('✅ [ZohoSalesIQ] Configuration terminée - Bouton flottant uniquement')
          return
          
        } catch (error) {
          console.error('❌ [ZohoSalesIQ] Erreur configuration:', error)
        }
      } else if (attempts < maxAttempts) {
        console.log('⏳ [ZohoSalesIQ] Widget pas encore prêt, retry...')
        retryTimeoutRef.current = setTimeout(configureAttempt, checkInterval)
      } else {
        console.error('❌ [ZohoSalesIQ] Échec configuration après', maxAttempts, 'tentatives')
      }
    }
    
    configureAttempt()
  }, [user, ensureFloatButtonVisible, hideZohoChatWindow, fixZohoAccessibility])

  const loadZohoWithLanguage = useCallback((lang: string) => {
    console.log('🚀 [ZohoSalesIQ] Chargement widget avec langue de session:', lang)
    
    if (!user?.email) {
      console.warn('⚠️ [ZohoSalesIQ] Pas d\'utilisateur, abandon')
      return
    }

    // ✅ SÉCURISÉ: Variables depuis environnement
    const widgetBaseUrl = process.env.NEXT_PUBLIC_ZOHO_WIDGET_BASE_URL
    const widgetId = process.env.NEXT_PUBLIC_ZOHO_WIDGET_ID
    
    if (!widgetBaseUrl || !widgetId) {
      console.error('❌ [ZohoSalesIQ] Variables Zoho manquantes:', {
        baseUrl: !!widgetBaseUrl,
        widgetId: !!widgetId
      })
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
      
      // ✅ SÉCURISÉ: URL construite depuis variables env
      script.src = `${widgetBaseUrl}?wc=${widgetId}&locale=${lang}`
      
      console.log('📡 [ZohoSalesIQ] Chargement script principal depuis env vars')
      
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

  // ✅ NOUVEAU: Observer DOM pour masquer automatiquement la fenêtre de chat
  useEffect(() => {
    if (!widgetLoadedRef.current) return

    const observer = new MutationObserver((mutations) => {
      let shouldCheck = false
      
      mutations.forEach((mutation) => {
        // Vérifier si des éléments Zoho ont été ajoutés/modifiés
        if (mutation.type === 'childList') {
          const hasZohoElements = Array.from(mutation.addedNodes).some(node => 
            node instanceof Element && (
              node.id?.includes('zsiq') || 
              node.className?.includes('zsiq') ||
              node.className?.includes('siq-')
            )
          )
          if (hasZohoElements) shouldCheck = true
        }
        
        // Vérifier si des classes/styles ont changé sur des éléments Zoho
        if (mutation.type === 'attributes' && mutation.target instanceof Element) {
          if (mutation.target.id?.includes('zsiq') || 
              mutation.target.className?.includes('zsiq') ||
              mutation.target.className?.includes('siq-')) {
            shouldCheck = true
          }
        }
      })
      
      if (shouldCheck) {
        setTimeout(() => {
          hideZohoChatWindow()
          fixZohoAccessibility()
        }, 500)
      }
    })

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'style', 'id']
    })

    return () => observer.disconnect()
  }, [hideZohoChatWindow, fixZohoAccessibility])

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