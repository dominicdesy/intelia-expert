import { useState, useEffect, useCallback, useRef } from 'react'
import { translations } from '../utils/translations'
import { Translation } from '../../../types'

// ==================== BOOT PICKUP ATOMIQUE ====================
let bootApplied = false

// Application synchrone AVANT tout rendu
if (typeof window !== 'undefined' && !bootApplied) {
  const forced = sessionStorage.getItem('force_language')
  if (forced && translations[forced as keyof typeof translations]) {
    try {
      console.log('[useTranslation] Boot pickup applied:', forced)
      
      // Application immédiate dans localStorage (source de vérité)
      localStorage.setItem('intelia_language', forced)
      
      // Nettoyage du flag
      sessionStorage.removeItem('force_language')
      
    } finally {
      bootApplied = true
    }
  } else {
    bootApplied = true
  }
}

// ==================== HOOK PRINCIPAL ====================
export const useTranslation = (): Translation => {
  // État initial : priorité au localStorage
  const [currentLanguage, setCurrentLanguage] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('intelia_language')
      if (saved && translations[saved as keyof typeof translations]) {
        console.log('[useTranslation] État initial depuis localStorage:', saved)
        return saved
      }
    }
    console.log('[useTranslation] État initial par défaut: fr')
    return 'fr'
  })
  
  // Protection contre setState après unmount
  const mountedRef = useRef(true)
  
  useEffect(() => {
    return () => {
      mountedRef.current = false
    }
  }, [])
  
  // Fonction de traduction mémorisée
  const t = useCallback((key: string): string => {
    const translated = translations[currentLanguage as keyof typeof translations]?.[key as keyof typeof translations['fr']]
    return translated || key
  }, [currentLanguage])
  
  // Fonction changeLanguage référentiellement stable
  const changeLanguage = useCallback((lang: string) => {
    // Vérifier si le composant est encore monté
    if (!mountedRef.current) {
      console.log('[useTranslation] setState évité - composant démonté')
      return
    }
    
    // Éviter les changements inutiles
    if (lang === currentLanguage) {
      console.log('[useTranslation] Changement ignoré (identique):', lang)
      return
    }
    
    console.log('[useTranslation] changeLanguage:', currentLanguage, '→', lang)
    
    // Mise à jour immédiate state + localStorage
    setCurrentLanguage(lang)
    if (typeof window !== 'undefined') {
      localStorage.setItem('intelia_language', lang)
    }
    
    // Notifier les autres composants
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('languageChanged'))
    }
    
    console.log('[useTranslation] Changement appliqué:', lang)
  }, [currentLanguage])
  
  // Synchronisation initiale
  useEffect(() => {
    if (typeof window === 'undefined') return
    
    // Vérifier si on a une langue sauvegardée différente de l'état
    const savedLang = localStorage.getItem('intelia_language')
    if (savedLang && 
        savedLang !== currentLanguage && 
        translations[savedLang as keyof typeof translations]) {
      
      console.log('[useTranslation] Synchronisation initiale:', currentLanguage, '→', savedLang)
      setCurrentLanguage(savedLang)
    }
  }, [])
  
  // Écouter les changements de langue globaux
  useEffect(() => {
    if (typeof window === 'undefined') return
    
    const handleLanguageChange = () => {
      const savedLang = localStorage.getItem('intelia_language')
      if (savedLang && savedLang !== currentLanguage && translations[savedLang as keyof typeof translations]) {
        console.log('[useTranslation] Mise à jour depuis événement global:', savedLang)
        if (mountedRef.current) {
          setCurrentLanguage(savedLang)
        }
      }
    }

    window.addEventListener('languageChanged', handleLanguageChange)
    return () => window.removeEventListener('languageChanged', handleLanguageChange)
  }, [currentLanguage])
  
  return { 
    t, 
    changeLanguage, 
    currentLanguage 
  }
}