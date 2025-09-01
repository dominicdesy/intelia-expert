// lib/hooks/useLanguageStore.ts - Hook de compatibilité
import { useTranslation } from '@/lib/languages/i18n'

// Hook qui imite l'interface de l'ancien Zustand store
export const useLanguageStore = () => {
  const { t, currentLanguage, changeLanguage } = useTranslation()

  return {
    t,
    currentLanguage,
    setLanguage: changeLanguage, // Alias pour compatibilité
    changeLanguage
  }
}

// Export pour les options de langue (basé sur config.ts)
import { availableLanguages } from '@/lib/languages/config'

export const languageOptions = availableLanguages.map(lang => ({
  code: lang.code,
  name: lang.nativeName,
  flag: lang.flag
}))