// components/providers/LanguageProvider.tsx
'use client'

import { useEffect, useRef } from 'react'
import { useTranslation } from '@/lib/languages/i18n'

// Import de la configuration officielle
import { isValidLanguageCode } from '@/lib/languages/config'

// Types supportés par le système i18n (basé sur config.ts)
type Language = 'fr' | 'en' | 'es' | 'pt' | 'de' | 'nl' | 'pl' | 'th' | 'hi' | 'zh'

// Helper function pour valider le type Language (utilise la config officielle)
function isValidLanguage(lang: string): lang is Language {
  return isValidLanguageCode(lang)
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const { changeLanguage } = useTranslation()
  const hasInitializedRef = useRef(false)

  useEffect(() => {
    // Initialisation UNE SEULE FOIS
    if (hasInitializedRef.current) return
    hasInitializedRef.current = true

    // Définir la langue basée sur le navigateur
    if (typeof window !== 'undefined') {
      const browserLang = navigator.language.split('-')[0]
      
      // Validation et application de la langue
      if (isValidLanguage(browserLang)) {
        changeLanguage(browserLang)
        console.log('[LanguageProvider] Langue initialisée depuis navigateur:', browserLang)
      } else {
        changeLanguage('fr') // Français par défaut
        console.log('[LanguageProvider] Langue par défaut appliquée: fr')
      }
    }
  }, [changeLanguage])

  return <>{children}</>
}