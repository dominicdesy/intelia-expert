// components/providers/LanguageProvider.tsx - VERSION SYNCHRONISÉE
'use client'

import { useEffect, useRef } from 'react'
import { useTranslation } from '@/lib/languages/i18n'
import { isValidLanguageCode } from '@/lib/languages/config'

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const { changeLanguage } = useTranslation()
  const hasInitializedRef = useRef(false)

  useEffect(() => {
    // Initialisation UNE SEULE FOIS
    if (hasInitializedRef.current) return
    hasInitializedRef.current = true

    if (typeof window !== 'undefined') {
      // 1. PRIORITÉ ABSOLUE : localStorage Zustand
      try {
        const zustandData = localStorage.getItem('intelia-language')
        if (zustandData) {
          const parsed = JSON.parse(zustandData)
          const storedLang = parsed?.state?.currentLanguage
          
          if (storedLang && isValidLanguageCode(storedLang)) {
            // FORCER la synchronisation immédiate
            changeLanguage(storedLang)
            
            // Émettre l'événement pour tous les composants
            window.dispatchEvent(new CustomEvent('languageChanged', { 
              detail: { language: storedLang } 
            }))
            
            console.log('[LanguageProvider] ✅ Langue FORCÉE depuis localStorage:', storedLang)
            return
          }
        }
      } catch (error) {
        console.warn('[LanguageProvider] Erreur lecture localStorage:', error)
      }

      // 2. FALLBACK : navigateur (seulement si aucune préférence sauvée)
      const browserLang = navigator.language.split('-')[0]
      const finalLang = isValidLanguageCode(browserLang) ? browserLang : 'fr'
      
      changeLanguage(finalLang)
      console.log('[LanguageProvider] Langue initialisée depuis navigateur/défaut:', finalLang)
    }
  }, [changeLanguage])

  // ÉCOUTER les changements de langue et les propager
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'intelia-language' && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue)
          const newLang = parsed?.state?.currentLanguage
          
          if (newLang && isValidLanguageCode(newLang)) {
            changeLanguage(newLang)
            console.log('[LanguageProvider] 📢 Changement détecté:', newLang)
          }
        } catch (error) {
          console.warn('[LanguageProvider] Erreur storage change:', error)
        }
      }
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [changeLanguage])

  return <>{children}</>
}