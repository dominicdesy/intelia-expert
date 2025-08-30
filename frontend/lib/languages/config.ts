// ==================== CONFIGURATION DES LANGUES DISPONIBLES ====================

export interface LanguageConfig {
  code: string
  name: string
  nativeName: string
  region: string
  flag: string
  rtl?: boolean
  dateFormat: string
}

export const availableLanguages: LanguageConfig[] = [
  {
    code: 'fr',
    name: 'French',
    nativeName: 'Français',
    region: 'France',
    flag: '🇫🇷',
    dateFormat: 'fr-FR'
  },
  {
    code: 'en',
    name: 'English',
    nativeName: 'English',
    region: 'United States',
    flag: '🇺🇸',
    dateFormat: 'en-US'
  },
  {
    code: 'es',
    name: 'Spanish',
    nativeName: 'Español',
    region: 'España',
    flag: '🇪🇸',
    dateFormat: 'es-ES'
  },
  {
    code: 'pt',
    name: 'Portuguese',
    nativeName: 'Português',
    region: 'Brasil',
    flag: '🇧🇷',
    dateFormat: 'pt-BR'
  },
  {
    code: 'de',
    name: 'German',
    nativeName: 'Deutsch',
    region: 'Deutschland',
    flag: '🇩🇪',
    dateFormat: 'de-DE'
  },
  {
    code: 'nl',
    name: 'Dutch',
    nativeName: 'Nederlands',
    region: 'Nederland',
    flag: '🇳🇱',
    dateFormat: 'nl-NL'
  },
  {
    code: 'pl',
    name: 'Polish',
    nativeName: 'Polski',
    region: 'Polska',
    flag: '🇵🇱',
    dateFormat: 'pl-PL'
  },
  {
    code: 'th',
    name: 'Thai',
    nativeName: 'ไทย',
    region: 'ประเทศไทย',
    flag: '🇹🇭',
    dateFormat: 'th-TH'
  },
  {
    code: 'hi',
    name: 'Hindi',
    nativeName: 'हिन्दी',
    region: 'भारत',
    flag: '🇮🇳',
    dateFormat: 'hi-IN'
  },
  {
    code: 'zh',
    name: 'Chinese',
    nativeName: '中文',
    region: '中国',
    flag: '🇨🇳',
    dateFormat: 'zh-CN'
  }
]

// Langue par défaut
export const DEFAULT_LANGUAGE = 'fr'

// Fonction utilitaire pour obtenir une langue par son code
export const getLanguageByCode = (code: string): LanguageConfig | undefined => {
  return availableLanguages.find(lang => lang.code === code)
}

// Fonction utilitaire pour valider un code de langue
export const isValidLanguageCode = (code: string): boolean => {
  return availableLanguages.some(lang => lang.code === code)
}

// Fonction pour obtenir la langue par défaut si le code n'est pas valide
export const getLanguageOrDefault = (code: string): LanguageConfig => {
  return getLanguageByCode(code) || getLanguageByCode(DEFAULT_LANGUAGE)!
}

// Export pour compatibilité avec l'ancien système
export const getAvailableLanguages = () => availableLanguages.map(lang => ({
  code: lang.code,
  name: lang.nativeName,
  region: lang.region
}))

// Fonction pour détecter la langue du navigateur
export const detectBrowserLanguage = (): string => {
  if (typeof window === 'undefined') return DEFAULT_LANGUAGE
  
  const browserLang = navigator.language || navigator.languages?.[0]
  if (!browserLang) return DEFAULT_LANGUAGE
  
  // Extraire le code de langue (ex: 'en-US' -> 'en')
  const langCode = browserLang.split('-')[0].toLowerCase()
  
  // Vérifier si cette langue est supportée
  return isValidLanguageCode(langCode) ? langCode : DEFAULT_LANGUAGE
}