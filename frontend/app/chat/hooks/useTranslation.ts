import { useState, useEffect, useCallback } from 'react'
import { translations } from '../utils/translations'
import { Translation } from '../../../types'

// ==================== 🔒 BOOT PICKUP ATOMIQUE ====================
let bootApplied = false

// 1. ✅ BOOT PICKUP (priorité absolue) - Application synchrone AVANT tout rendu
if (typeof window !== 'undefined' && !bootApplied) {
  const forced = sessionStorage.getItem('force_language')
  if (forced && translations[forced as keyof typeof translations]) {
    try {
      console.log('[useTranslation] 🔒 Boot pickup applied:', forced)
      
      // Marque globale pour bypasser toute "garde" pendant ce switch
      ;(window as any).__INTELIA_FORCED_BOOT_LANG__ = forced
      
      // Application immédiate dans localStorage (source de vérité)
      localStorage.setItem('intelia_language', forced)
      
      // Nettoyage du flag
      sessionStorage.removeItem('force_language')
      
    } finally {
      bootApplied = true
    }
  } else {
    bootApplied = true // Marquer comme traité même si pas de flag
  }
}

// ==================== 🎯 HOOK PRINCIPAL ====================
export const useTranslation = (): Translation => {
  // État initial : priorité au localStorage (déjà mis à jour par boot pickup si nécessaire)
  const [currentLanguage, setCurrentLanguage] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('intelia_language')
      if (saved && translations[saved as keyof typeof translations]) {
        console.log('[useTranslation] 🚀 État initial depuis localStorage:', saved)
        return saved
      }
    }
    console.log('[useTranslation] 🔤 État initial par défaut: fr')
    return 'fr'
  })
  
  // 3. ✅ API STABLE - Fonction de traduction mémorisée
  const t = useCallback((key: string): string => {
    const translated = translations[currentLanguage as keyof typeof translations]?.[key as keyof typeof translations['fr']]
    return translated || key
  }, [currentLanguage])
  
  // 3. ✅ API STABLE - Fonction changeLanguage référentiellement stable
  const changeLanguage = useCallback((lang: string) => {
    // 5. ✅ IDEMPOTENCE - Éviter les changements inutiles
    if (lang === currentLanguage) {
      console.log('[useTranslation] ⏭️ Changement ignoré (identique):', lang)
      return
    }
    
    // 2. ✅ PAS DE GARDE qui ignore un switch forcé
    const isForcedBoot = typeof window !== 'undefined' && 
                        (window as any).__INTELIA_FORCED_BOOT_LANG__ === lang
    
    if (isForcedBoot) {
      console.log('[useTranslation] 🔓 Switch forcé autorisé (bypass garde):', lang)
      // Nettoyer la marque après usage
      delete (window as any).__INTELIA_FORCED_BOOT_LANG__
    }
    
    console.log('[useTranslation] 🌐 changeLanguage:', currentLanguage, '→', lang)
    
    // Mise à jour immédiate state + localStorage
    setCurrentLanguage(lang)
    if (typeof window !== 'undefined') {
      localStorage.setItem('intelia_language', lang)
    }
    
    // Notifier les autres composants
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('languageChanged'))
    }
    
    console.log('[useTranslation] ✅ Changement appliqué:', lang)
  }, [currentLanguage])
  
  // 4. ✅ DÉPENDANCES SSR-SAFE - Effet pour synchronisation initiale
  useEffect(() => {
    // 4. ✅ Ne rien faire côté SSR
    if (typeof window === 'undefined') return
    
    // Vérifier si on a une langue sauvegardée différente de l'état
    const savedLang = localStorage.getItem('intelia_language')
    if (savedLang && 
        savedLang !== currentLanguage && 
        translations[savedLang as keyof typeof translations]) {
      
      console.log('[useTranslation] 🔄 Synchronisation initiale:', currentLanguage, '→', savedLang)
      setCurrentLanguage(savedLang)
    }
  }, []) // ⚠️ DÉPENDANCES VIDES - Une seule fois au mount
  
  // 🌐 ÉCOUTER les changements de langue globaux (garde le comportement existant)
  useEffect(() => {
    if (typeof window === 'undefined') return
    
    const handleLanguageChange = () => {
      // 2. ✅ PAS DE GARDE - Ne pas ignorer si c'est un boot forcé
      const isForcedBoot = (window as any).__INTELIA_FORCED_BOOT_LANG__
      if (isForcedBoot) {
        console.log('[useTranslation] 🔓 Event autorisé (boot forcé en cours)')
      }
      
      const savedLang = localStorage.getItem('intelia_language')
      if (savedLang && savedLang !== currentLanguage && translations[savedLang as keyof typeof translations]) {
        console.log('[useTranslation] 📡 Mise à jour depuis événement global:', savedLang)
        setCurrentLanguage(savedLang)
      }
    }

    window.addEventListener('languageChanged', handleLanguageChange)
    return () => window.removeEventListener('languageChanged', handleLanguageChange)
  }, [currentLanguage])
  
  // 7. ✅ LOGS - Confirmation du boot pickup
  useEffect(() => {
    if (typeof window !== 'undefined' && bootApplied) {
      const isFromBoot = (window as any).__INTELIA_FORCED_BOOT_LANG__
      if (isFromBoot) {
        console.log('[useTranslation] 🎯 Boot pickup confirmé - langue active:', currentLanguage)
      }
    }
  }, [currentLanguage])
  
  // 3. ✅ API STABLE - Interface publique stable
  return { 
    t, 
    changeLanguage, 
    currentLanguage 
  }
}