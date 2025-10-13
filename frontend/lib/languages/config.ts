// ==================== CONFIGURATION DES LANGUES DISPONIBLES ====================

export interface LanguageConfig {
  code: string;
  name: string;
  nativeName: string;
  region: string;
  flag: string;
  rtl?: boolean;
  dateFormat: string;
}

// Fonction pour détecter la langue du navigateur - DÉPLACÉE AU DÉBUT
export const detectBrowserLanguage = (): string => {
  if (typeof window === "undefined") return "en";

  const browserLang = navigator.language || navigator.languages?.[0];
  if (!browserLang) return "en";

  // Extraire le code de langue (ex: 'en-US' -> 'en')
  const langCode = browserLang.split("-")[0].toLowerCase();

  // Vérifier si cette langue est supportée
  return isValidLanguageCode(langCode) ? langCode : "en";
};

// Langues triées par ordre alphabétique du code
export const availableLanguages: LanguageConfig[] = [
  {
    code: "de",
    name: "German",
    nativeName: "Deutsch",
    region: "Germany",
    flag: "🇩🇪",
    dateFormat: "de-DE",
  },
  {
    code: "en",
    name: "English",
    nativeName: "English",
    region: "United States",
    flag: "🇺🇸",
    dateFormat: "en-US",
  },
  {
    code: "es",
    name: "Spanish",
    nativeName: "Español",
    region: "Spain",
    flag: "🇪🇸",
    dateFormat: "es-ES",
  },
  {
    code: "fr",
    name: "French",
    nativeName: "Français",
    region: "France",
    flag: "🇫🇷",
    dateFormat: "fr-FR",
  },
  {
    code: "hi",
    name: "Hindi",
    nativeName: "हिन्दी",
    region: "India",
    flag: "🇮🇳",
    dateFormat: "hi-IN",
  },
  {
    code: "id",
    name: "Indonesian",
    nativeName: "Bahasa Indonesia",
    region: "Indonesia",
    flag: "🇮🇩",
    dateFormat: "id-ID",
  },
  {
    code: "it",
    name: "Italian",
    nativeName: "Italiano",
    region: "Italy",
    flag: "🇮🇹",
    dateFormat: "it-IT",
  },
  {
    code: "ja",
    name: "Japanese",
    nativeName: "日本語",
    region: "Japan",
    flag: "🇯🇵",
    dateFormat: "ja-JP",
  },
  {
    code: "nl",
    name: "Dutch",
    nativeName: "Nederlands",
    region: "Netherlands",
    flag: "🇳🇱",
    dateFormat: "nl-NL",
  },
  {
    code: "pl",
    name: "Polish",
    nativeName: "Polski",
    region: "Poland",
    flag: "🇵🇱",
    dateFormat: "pl-PL",
  },
  {
    code: "pt",
    name: "Portuguese",
    nativeName: "Português",
    region: "Portugal",
    flag: "🇵🇹",
    dateFormat: "pt-PT",
  },
  {
    code: "th",
    name: "Thai",
    nativeName: "ไทย",
    region: "Thailand",
    flag: "🇹🇭",
    dateFormat: "th-TH",
  },
  {
    code: "tr",
    name: "Turkish",
    nativeName: "Türkçe",
    region: "Turkey",
    flag: "🇹🇷",
    dateFormat: "tr-TR",
  },
  {
    code: "vi",
    name: "Vietnamese",
    nativeName: "Tiếng Việt",
    region: "Vietnam",
    flag: "🇻🇳",
    dateFormat: "vi-VN",
  },
  {
    code: "zh",
    name: "Chinese (Mandarin)",
    nativeName: "中文",
    region: "China",
    flag: "🇨🇳",
    dateFormat: "zh-CN",
  },
];

// Fonction utilitaire pour valider un code de langue - DÉPLACÉE AVANT DEFAULT_LANGUAGE
export const isValidLanguageCode = (code: string): boolean => {
  return availableLanguages.some((lang) => lang.code === code);
};

// Langue par défaut - CORRECTION: constante statique
export const DEFAULT_LANGUAGE = "en";

// Fonction utilitaire pour obtenir une langue par son code
export const getLanguageByCode = (code: string): LanguageConfig | undefined => {
  return availableLanguages.find((lang) => lang.code === code);
};

// Fonction pour obtenir la langue par défaut si le code n'est pas valide
export const getLanguageOrDefault = (code: string): LanguageConfig => {
  return getLanguageByCode(code) || getLanguageByCode(DEFAULT_LANGUAGE)!;
};

// Export pour compatibilité avec l'ancien système
export const getAvailableLanguages = () =>
  availableLanguages.map((lang) => ({
    code: lang.code,
    name: lang.nativeName,
    region: lang.region,
  }));

// Langues avec support RTL (Right-to-Left)
export const RTL_LANGUAGES = new Set(["ar", "he", "fa", "ur"]);

// Fonction pour vérifier si une langue utilise RTL
export const isRTLLanguage = (code: string): boolean => {
  return RTL_LANGUAGES.has(code);
};

// Groupement des langues par région (mis à jour par ordre alphabétique des noms)
export const LANGUAGE_REGIONS = {
  europe: ["en", "fr", "de", "it", "nl", "pl", "pt", "es"] as const,
  asia: ["zh", "hi", "id", "ja", "th", "tr", "vi"] as const,
  americas: [] as const, // Si vous ajoutez plus tard pt-BR, en-CA, etc.
  africa: [] as const,
  oceania: [] as const,
};

// Export des langues disponibles par région
export const getLanguagesByRegion = (region: keyof typeof LANGUAGE_REGIONS) => {
  const regionCodes = LANGUAGE_REGIONS[region] as readonly string[];
  return availableLanguages.filter((lang) => regionCodes.includes(lang.code));
};
