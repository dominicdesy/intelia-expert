// lib/stores/language.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { Language, LanguageOption } from '@/types'

// Traductions de base
const translations: Record<Language, Record<string, string>> = {
  fr: {
    'welcome': 'Bienvenue sur Intelia Expert',
    'ask_question': 'Posez votre question à l\'expert...',
    'send': 'Envoyer',
    'login': 'Se connecter',
    'logout': 'Se déconnecter',
    'profile': 'Profil'
  },
  en: {
    'welcome': 'Welcome to Intelia Expert',
    'ask_question': 'Ask your question to the expert...',
    'send': 'Send',
    'login': 'Login',
    'logout': 'Logout',
    'profile': 'Profile'
  },
  es: {
    'welcome': 'Bienvenido a Intelia Expert',
    'ask_question': 'Haga su pregunta al experto...',
    'send': 'Enviar',
    'login': 'Iniciar sesión',
    'logout': 'Cerrar sesión',
    'profile': 'Perfil'
  },
  pt: {
    'welcome': 'Bem-vindo ao Intelia Expert',
    'ask_question': 'Faça sua pergunta ao especialista...',
    'send': 'Enviar',
    'login': 'Entrar',
    'logout': 'Sair',
    'profile': 'Perfil'
  },
  de: {
    'welcome': 'Willkommen bei Intelia Expert',
    'ask_question': 'Stellen Sie Ihre Frage an den Experten...',
    'send': 'Senden',
    'login': 'Anmelden',
    'logout': 'Abmelden',
    'profile': 'Profil'
  },
  nl: {
    'welcome': 'Welkom bij Intelia Expert',
    'ask_question': 'Stel uw vraag aan de expert...',
    'send': 'Verzenden',
    'login': 'Inloggen',
    'logout': 'Uitloggen',
    'profile': 'Profiel'
  },
  pl: {
    'welcome': 'Witamy w Intelia Expert',
    'ask_question': 'Zadaj pytanie ekspertowi...',
    'send': 'Wyślij',
    'login': 'Zaloguj się',
    'logout': 'Wyloguj się',
    'profile': 'Profil'
  }
}

export const languageOptions: LanguageOption[] = [
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'pt', name: 'Português', flag: '🇵🇹' },
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'nl', name: 'Nederlands', flag: '🇳🇱' },
  { code: 'pl', name: 'Polski', flag: '🇵🇱' }
]

interface LanguageStore {
  currentLanguage: Language
  setLanguage: (language: Language) => void
  t: (key: string, params?: Record<string, string>) => string
}

export const useLanguageStore = create<LanguageStore>()(
  persist(
    (set, get) => ({
      currentLanguage: 'fr',

      setLanguage: (language: Language) => {
        set({ currentLanguage: language })
      },

      t: (key: string, params?: Record<string, string>) => {
        const { currentLanguage } = get()
        let translation = translations[currentLanguage]?.[key] || key

        // Remplacer les paramètres si fournis
        if (params) {
          Object.entries(params).forEach(([param, value]) => {
            translation = translation.replace(`{{${param}}}`, value)
          })
        }

        return translation
      }
    }),
    {
      name: 'intelia-language'
    }
  )
)