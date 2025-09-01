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
    region: 'Spain',
    flag: '🇪🇸',
    dateFormat: 'es-ES'
  },
  {
    code: 'pt',
    name: 'Portuguese',
    nativeName: 'Português',
    region: 'Portugal',
    flag: '🇵🇹',
    dateFormat: 'pt-PT'
  },
  {
    code: 'de',
    name: 'German',
    nativeName: 'Deutsch',
    region: 'Germany',
    flag: '🇩🇪',
    dateFormat: 'de-DE'
  },
  {
    code: 'nl',
    name: 'Dutch',
    nativeName: 'Nederlands',
    region: 'Netherlands',
    flag: '🇳🇱',
    dateFormat: 'nl-NL'
  },
  {
    code: 'pl',
    name: 'Polish',
    nativeName: 'Polski',
    region: 'Poland',
    flag: '🇵🇱',
    dateFormat: 'pl-PL'
  },
  {
    code: 'th',
    name: 'Thai',
    nativeName: 'ไทย',
    region: 'Thailand',
    flag: '🇹🇭',
    dateFormat: 'th-TH'
  },
  {
    code: 'hi',
    name: 'Hindi',
    nativeName: 'हिंदी',
    region: 'India',
    flag: '🇮🇳',
    dateFormat: 'hi-IN'
  },
  {
    code: 'zh',
    name: 'Chinese (Mandarin)',
    nativeName: '中文',
    region: 'China',
    flag: '🇨🇳',
    dateFormat: 'zh-CN'
  }
]

// Langue par défaut
export const DEFAULT_LANGUAGE = 'en'

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

// Langues avec support RTL (Right-to-Left)
export const RTL_LANGUAGES = new Set(['ar', 'he', 'fa', 'ur'])

// Fonction pour vérifier si une langue utilise RTL
export const isRTLLanguage = (code: string): boolean => {
  return RTL_LANGUAGES.has(code)
}

// Groupement des langues par région (optionnel pour l'interface)
export const LANGUAGE_REGIONS = {
  europe: ['fr', 'en', 'es', 'pt', 'de', 'nl', 'pl'],
  asia: ['th', 'hi', 'zh'],
  americas: [], // Si vous ajoutez plus tard pt-BR, en-CA, etc.
  africa: [],
  oceania: []
} as const

// Export des langues disponibles par région
export const getLanguagesByRegion = (region: keyof typeof LANGUAGE_REGIONS) => {
  return availableLanguages.filter(lang => 
    LANGUAGE_REGIONS[region].includes(lang.code)
  )
}