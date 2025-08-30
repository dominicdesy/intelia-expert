import { useState, useEffect } from 'react'
import { translations } from '../utils/translations'
import { Translation } from '../../../types'

// Hook de traduction avec support force_language atomique
export const useTranslation = (): Translation => {
  const [currentLanguage, setCurrentLanguage] = useState('fr')
  
  const t = (key: string): string => {
    return translations[currentLanguage as keyof typeof translations]?.[key as keyof typeof translations['fr']] || key
  }
  
  const changeLanguage = (lang: string) => {
    console.log('🌐 [useTranslation] changeLanguage appelée:', currentLanguage, '→', lang)
    setCurrentLanguage(lang)
    localStorage.setItem('intelia_language', lang)
    console.log('✅ [useTranslation] État langue mis à jour:', lang)
    
    // Force un re-render de tous les composants qui utilisent ce hook
    window.dispatchEvent(new Event('languageChanged'))
  }
  
  // 🔒 EFFET DE BOOT - Priorité au flag force_language
  useEffect(() => {
    console.log('🚀 [useTranslation] Initialisation du hook...')
    
    // 1. 🎯 PRIORITÉ ABSOLUE : Vérifier le flag force au boot
    const forcedLang = sessionStorage.getItem('force_language')
    if (forcedLang) {
      console.log('🔒 [useTranslation] FORCE LANGUAGE détecté:', forcedLang)
      
      // Valider que la langue forcée existe
      if (translations[forcedLang as keyof typeof translations]) {
        console.log('✅ [useTranslation] Application langue forcée:', forcedLang)
        setCurrentLanguage(forcedLang)
        
        // Synchroniser localStorage avec la langue forcée
        localStorage.setItem('intelia_language', forcedLang)
        
        // Nettoyer le flag après usage
        sessionStorage.removeItem('force_language')
        console.log('🧹 [useTranslation] Flag force_language nettoyé')
        
        // Notifier le changement
        window.dispatchEvent(new Event('languageChanged'))
        
        // ⛔ EARLY RETURN - Ne pas vérifier localStorage après
        return
      } else {
        console.warn('⚠️ [useTranslation] Langue forcée invalide:', forcedLang)
        sessionStorage.removeItem('force_language') // Nettoyer le flag invalide
      }
    }
    
    // 2. 📦 FALLBACK : Charger depuis localStorage (comportement normal)
    const savedLang = localStorage.getItem('intelia_language')
    if (savedLang && translations[savedLang as keyof typeof translations]) {
      console.log('📄 [useTranslation] Chargement langue sauvegardée:', savedLang)
      setCurrentLanguage(savedLang)
    } else {
      console.log('🔤 [useTranslation] Utilisation langue par défaut: fr')
      // Pas besoin de setState, déjà à 'fr' par défaut
    }
  }, []) // ⚠️ DÉPENDANCES VIDES - Ne s'exécute qu'au mount !

  // 🌐 ÉCOUTER les changements de langue globaux (garde le comportement existant)
  useEffect(() => {
    const handleLanguageChange = () => {
      // ⚠️ IGNORER si on a un flag force en cours de traitement
      const forcedLang = sessionStorage.getItem('force_language')
      if (forcedLang) {
        console.log('⏭️ [useTranslation] Event ignoré - flag force en cours:', forcedLang)
        return
      }
      
      const savedLang = localStorage.getItem('intelia_language')
      if (savedLang && savedLang !== currentLanguage) {
        console.log('📡 [useTranslation] Mise à jour depuis événement global:', savedLang)
        setCurrentLanguage(savedLang)
      }
    }

    window.addEventListener('languageChanged', handleLanguageChange)
    return () => window.removeEventListener('languageChanged', handleLanguageChange)
  }, [currentLanguage])
  
  return { t, changeLanguage, currentLanguage }
}