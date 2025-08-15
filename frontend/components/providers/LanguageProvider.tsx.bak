// components/providers/LanguageProvider.tsx
'use client'

import { useEffect } from 'react'
import { useLanguageStore } from '@/lib/stores/language'
import { useAuthStore } from '@/lib/stores/auth'

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const { setLanguage } = useLanguageStore()
  const { user } = useAuthStore()

  useEffect(() => {
    // Définir la langue basée sur l'utilisateur ou le navigateur
    if (user?.language) {
      setLanguage(user.language)
    } else if (typeof window !== 'undefined') {
      const browserLang = navigator.language.split('-')[0] as any
      const supportedLangs = ['fr', 'en', 'es', 'pt', 'de', 'nl', 'pl']
      
      if (supportedLangs.includes(browserLang)) {
        setLanguage(browserLang)
      } else {
        setLanguage('fr') // Français par défaut
      }
    }
  }, [user, setLanguage])

  return <>{children}</>
}