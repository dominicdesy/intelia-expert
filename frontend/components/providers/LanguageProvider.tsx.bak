// components/providers/LanguageProvider.tsx - VERSION AVEC ANTI-FLASH INTÉGRÉ
'use client'

import { useEffect, useRef } from 'react'
import { useTranslation } from '@/lib/languages/i18n'
import { isValidLanguageCode } from '@/lib/languages/config'

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const { changeLanguage } = useTranslation()
  const hasInitializedRef = useRef(false)
  const isInitializingRef = useRef(false)

  useEffect(() => {
    // Initialisation UNE SEULE FOIS avec protection anti-flash
    if (hasInitializedRef.current || isInitializingRef.current) return
    isInitializingRef.current = true

    const initializeLanguage = async () => {
      if (typeof window !== 'undefined') {
        try {
          // 1. PRIORITÉ ABSOLUE : localStorage Zustand
          const zustandData = localStorage.getItem('intelia-language')
          let selectedLang = 'fr' // Default fallback

          if (zustandData) {
            try {
              const parsed = JSON.parse(zustandData)
              const storedLang = parsed?.state?.currentLanguage
              
              if (storedLang && isValidLanguageCode(storedLang)) {
                selectedLang = storedLang
                console.log('[LanguageProvider] ✅ Langue trouvée dans localStorage:', storedLang)
              }
            } catch (error) {
              console.warn('[LanguageProvider] Erreur parsing localStorage:', error)
            }
          } else {
            // 2. FALLBACK : navigateur (seulement si aucune préférence sauvée)
            const browserLang = navigator.language.split('-')[0]
            selectedLang = isValidLanguageCode(browserLang) ? browserLang : 'fr'
            console.log('[LanguageProvider] Langue depuis navigateur/défaut:', selectedLang)
          }

          // 3. FORCER la synchronisation immédiate
          await changeLanguage(selectedLang)
          
          // 4. Émettre l'événement pour tous les composants
          window.dispatchEvent(new CustomEvent('languageChanged', { 
            detail: { language: selectedLang } 
          }))
          
          // 5. MARQUER COMME PRÊT pour éviter le flash
          // Petit délai pour s'assurer que tous les composants sont synchronisés
          setTimeout(() => {
            document.documentElement.classList.add('language-ready')
            console.log('[LanguageProvider] 🎯 Interface prête - Flash évité')
          }, 100) // 100ms suffisant pour la plupart des cas

        } catch (error) {
          console.error('[LanguageProvider] Erreur initialisation:', error)
          // En cas d'erreur, forcer l'affichage pour éviter un écran noir
          document.documentElement.classList.add('language-ready')
        } finally {
          hasInitializedRef.current = true
          isInitializingRef.current = false
        }
      }
    }

    initializeLanguage()
  }, [changeLanguage])

  // ÉCOUTER les changements de langue et les propager
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'intelia-language' && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue)
          const newLang = parsed?.state?.currentLanguage
          
          if (newLang && isValidLanguageCode(newLang)) {
            // Pas de flash lors des changements manuels
            document.documentElement.classList.remove('language-ready')
            
            changeLanguage(newLang).then(() => {
              // Remettre la classe après le changement
              setTimeout(() => {
                document.documentElement.classList.add('language-ready')
              }, 50)
            })
            
            console.log('[LanguageProvider] 🔄 Changement détecté:', newLang)
          }
        } catch (error) {
          console.warn('[LanguageProvider] Erreur storage change:', error)
        }
      }
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [changeLanguage])

  // Timeout de sécurité pour éviter un écran noir permanent
  useEffect(() => {
    const safetyTimer = setTimeout(() => {
      if (!document.documentElement.classList.contains('language-ready')) {
        console.warn('[LanguageProvider] ⚠️ Timeout sécurité atteint - Affichage forcé')
        document.documentElement.classList.add('language-ready')
      }
    }, 2000) // 2 secondes max

    return () => clearTimeout(safetyTimer)
  }, [])

  return <>{children}</>
}