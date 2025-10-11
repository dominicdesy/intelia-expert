/**
 * Messages de chargement animés pour le chat
 * Utilisés pendant que l'IA génère une réponse
 */

export const loadingMessages = {
  incubating: {
    en: "Incubating",
    fr: "En incubation",
    es: "En incubación",
    pt: "Em incubação",
    de: "Beim Inkubieren",
    it: "In incubazione",
    nl: "Bezig met incuberen",
    pl: "W trakcie inkubacji",
    hi: "अंडे सेने की प्रक्रिया में",
    id: "Sedang menginkubasi",
    th: "กำลังกกไข่",
    zh: "正在孵化中",
    ru: "Инкубация",
  },
  hatching: {
    en: "Hatching",
    fr: "En éclosion",
    es: "En eclosión",
    pt: "Em eclosão",
    de: "Beim Schlüpfen",
    it: "In schiusa",
    nl: "Bezig met uitkomen",
    pl: "W trakcie wylęgania",
    hi: "फूटने की प्रक्रिया में",
    id: "Sedang menetas",
    th: "กำลังฟักไข่",
    zh: "正在破壳中",
    ru: "Вылупление",
  },
  feeding: {
    en: "Feeding",
    fr: "Alimentation en cours",
    es: "En alimentación",
    pt: "Em alimentação",
    de: "Beim Füttern",
    it: "In alimentazione",
    nl: "Bezig met voeren",
    pl: "W trakcie karmienia",
    hi: "खिलाने की प्रक्रिया में",
    id: "Sedang memberi pakan",
    th: "กำลังให้อาหาร",
    zh: "正在投喂中",
    ru: "Кормление",
  },
  watering: {
    en: "Watering",
    fr: "Abreuvement en cours",
    es: "En suministro de agua",
    pt: "Em fornecimento de água",
    de: "Beim Tränken",
    it: "In abbeveraggio",
    nl: "Bezig met water geven",
    pl: "W trakcie pojenia",
    hi: "पानी देने की प्रक्रिया में",
    id: "Sedang memberi air",
    th: "กำลังให้น้ำ",
    zh: "正在供水中",
    ru: "Поение",
  },
  ventilating: {
    en: "Ventilating",
    fr: "Ventilation en cours",
    es: "En ventilación",
    pt: "Em ventilação",
    de: "Beim Lüften",
    it: "In ventilazione",
    nl: "Bezig met ventileren",
    pl: "W trakcie wentylacji",
    hi: "हवा देने की प्रक्रिया में",
    id: "Sedang ventilasi",
    th: "กำลังระบายอากาศ",
    zh: "正在通风中",
    ru: "Вентиляция",
  },
  weighing: {
    en: "Weighing",
    fr: "Pesée en cours",
    es: "En pesaje",
    pt: "Em pesagem",
    de: "Beim Wiegen",
    it: "In pesatura",
    nl: "Bezig met wegen",
    pl: "W trakcie ważenia",
    hi: "वजन करने की प्रक्रिया में",
    id: "Sedang menimbang",
    th: "กำลังชั่งน้ำหนัก",
    zh: "正在称重中",
    ru: "Взвешивание",
  },
  analyzing: {
    en: "Analyzing",
    fr: "Analyse en cours",
    es: "En análisis",
    pt: "Em análise",
    de: "Beim Analysieren",
    it: "In analisi",
    nl: "Bezig met analyseren",
    pl: "W trakcie analizy",
    hi: "विश्लेषण की प्रक्रिया में",
    id: "Sedang menganalisis",
    th: "กำลังวิเคราะห์",
    zh: "正在分析中",
    ru: "Анализ",
  },
  vaccinating: {
    en: "Vaccinating",
    fr: "Vaccination en cours",
    es: "En vacunación",
    pt: "Em vacinação",
    de: "Beim Impfen",
    it: "In vaccinazione",
    nl: "Bezig met vaccineren",
    pl: "W trakcie szczepienia",
    hi: "टीकाकरण की प्रक्रिया में",
    id: "Sedang memvaksinasi",
    th: "กำลังฉีดวัคซีน",
    zh: "正在接种中",
    ru: "Вакцинация",
  },
} as const;

export type LoadingMessageKey = keyof typeof loadingMessages;
export type LanguageCode = keyof (typeof loadingMessages)[LoadingMessageKey];

/**
 * Sélectionne un message de chargement aléatoire dans la langue spécifiée
 * @param language Code de langue (en, fr, es, etc.)
 * @returns Message de chargement traduit
 */
export function getRandomLoadingMessage(language: string = "en"): string {
  const keys = Object.keys(loadingMessages) as LoadingMessageKey[];
  const randomKey = keys[Math.floor(Math.random() * keys.length)];

  // Normaliser le code de langue
  const normalizedLang = language.toLowerCase().split("-")[0] as LanguageCode;

  // Fallback sur l'anglais si la langue n'est pas supportée
  const message = loadingMessages[randomKey];
  return message[normalizedLang] || message.en;
}

/**
 * Hook React pour obtenir un message de chargement qui change à chaque appel
 */
export function useRandomLoadingMessage(language: string = "en"): string {
  return getRandomLoadingMessage(language);
}
