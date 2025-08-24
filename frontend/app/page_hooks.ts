// page_hooks.ts
import { useState, useEffect, useMemo } from 'react'
import type { Country } from './page_types'

// Fallback countries
const fallbackCountries: Country[] = [
  { value: 'CA', label: 'Canada', phoneCode: '+1', flag: '🇨🇦' },
  { value: 'US', label: 'États-Unis', phoneCode: '+1', flag: '🇺🇸' },
  { value: 'FR', label: 'France', phoneCode: '+33', flag: '🇫🇷' },
  { value: 'GB', label: 'Royaume-Uni', phoneCode: '+44', flag: '🇬🇧' },
  { value: 'DE', label: 'Allemagne', phoneCode: '+49', flag: '🇩🇪' },
  { value: 'IT', label: 'Italie', phoneCode: '+39', flag: '🇮🇹' },
  { value: 'ES', label: 'Espagne', phoneCode: '+34', flag: '🇪🇸' },
  { value: 'BE', label: 'Belgique', phoneCode: '+32', flag: '🇧🇪' },
  { value: 'CH', label: 'Suisse', phoneCode: '+41', flag: '🇨🇭' },
  { value: 'MX', label: 'Mexique', phoneCode: '+52', flag: '🇲🇽' },
  { value: 'BR', label: 'Brésil', phoneCode: '+55', flag: '🇧🇷' },
  { value: 'AU', label: 'Australie', phoneCode: '+61', flag: '🇦🇺' },
  { value: 'JP', label: 'Japon', phoneCode: '+81', flag: '🇯🇵' },
  { value: 'CN', label: 'Chine', phoneCode: '+86', flag: '🇨🇳' },
  { value: 'IN', label: 'Inde', phoneCode: '+91', flag: '🇮🇳' },
  { value: 'NL', label: 'Pays-Bas', phoneCode: '+31', flag: '🇳🇱' },
  { value: 'SE', label: 'Suède', phoneCode: '+46', flag: '🇸🇪' },
  { value: 'NO', label: 'Norvège', phoneCode: '+47', flag: '🇳🇴' },
  { value: 'DK', label: 'Danemark', phoneCode: '+45', flag: '🇩🇰' },
  { value: 'FI', label: 'Finlande', phoneCode: '+358', flag: '🇫🇮' }
]

// Hook pour charger les pays depuis l'API REST Countries avec debug complet
export const useCountries = () => {
  console.log('🎯 [Countries] Hook useCountries appelé!')
  
  const [countries, setCountries] = useState<Country[]>(fallbackCountries)
  const [loading, setLoading] = useState(true)
  const [usingFallback, setUsingFallback] = useState(true)

  useEffect(() => {
    console.log('🚀 [Countries] DÉMARRAGE du processus de chargement des pays')
    
    const fetchCountries = async () => {
      try {
        console.log('🌍 [Countries] Début du chargement depuis l\'API REST Countries...')
        console.log('📡 [Countries] URL: https://restcountries.com/v3.1/all?fields=cca2,name,idd,flag,translations')
        
        const controller = new AbortController()
        const timeoutId = setTimeout(() => {
          console.log('⏱️ [Countries] Timeout atteint (10s)')
          controller.abort()
        }, 10000)
        
        const response = await fetch('https://restcountries.com/v3.1/all?fields=cca2,name,idd,flag,translations', {
          headers: {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (compatible; Intelia/1.0)',
            'Cache-Control': 'no-cache'
          },
          signal: controller.signal
        })
        
        clearTimeout(timeoutId)
        console.log(`📡 [Countries] Statut HTTP: ${response.status} ${response.statusText}`)
        
        if (!response.ok) {
          throw new Error(`API indisponible: ${response.status}`)
        }
        
        const data = await response.json()
        console.log(`📊 [Countries] Données reçues: ${data.length} pays bruts`)
        console.log('🔍 [Countries] Échantillon brut:', data.slice(0, 2))
        
        if (!Array.isArray(data)) {
          console.error('❌ [Countries] Format invalide - pas un array')
          throw new Error('Format de données invalide')
        }
        
        const formattedCountries = data
          .map((country: any, index: number) => {
            let phoneCode = ''
            if (country.idd?.root) {
              phoneCode = country.idd.root
              if (country.idd.suffixes && country.idd.suffixes[0]) {
                phoneCode += country.idd.suffixes[0]
              }
            }
            
            const formatted = {
              value: country.cca2,
              label: country.translations?.fra?.common || country.name?.common || country.cca2,
              phoneCode: phoneCode,
              flag: country.flag || ''
            }
            
            if (index < 3) {
              console.log(`🏳️ [Countries] Pays ${index + 1}:`, formatted)
            }
            
            return formatted
          })
          .filter((country: Country, index: number) => {
            const hasValidCode = country.phoneCode && 
                                country.phoneCode !== 'undefined' && 
                                country.phoneCode !== 'null' &&
                                country.phoneCode.length > 1 &&
                                country.phoneCode.startsWith('+') &&
                                /^\+\d+$/.test(country.phoneCode)
            
            const hasValidInfo = country.value && 
                                country.value.length === 2 &&
                                country.label && 
                                country.label.length > 1
            
            const isValid = hasValidCode && hasValidInfo
            
            if (!isValid && index < 5) {
              console.log(`❌ [Countries] Pays rejeté:`, {
                country: country.label,
                code: country.value,
                phoneCode: country.phoneCode,
                hasValidCode,
                hasValidInfo
              })
            }
            
            return isValid
          })
          .sort((a: Country, b: Country) => a.label.localeCompare(b.label, 'fr', { numeric: true }))
        
        console.log(`✅ [Countries] Pays valides après filtrage: ${formattedCountries.length}`)
        console.log('📋 [Countries] Échantillon final:', formattedCountries.slice(0, 5))
        
        if (formattedCountries.length >= 50) {
          console.log('🎉 [Countries] API validée! Utilisation des données complètes')
          console.log(`📈 [Countries] Transition: fallback(${fallbackCountries.length}) → API(${formattedCountries.length})`)
          setCountries(formattedCountries)
          setUsingFallback(false)
        } else {
          console.warn(`⚠️ [Countries] Pas assez de pays valides: ${formattedCountries.length}/50`)
          throw new Error(`Qualité insuffisante: ${formattedCountries.length}/50 pays`)
        }
        
      } catch (err: any) {
        console.error('💥 [Countries] ERREUR:', err)
        console.warn('🔄 [Countries] Passage en mode fallback')
        
        if (err.name === 'AbortError') {
          console.warn('⏱️ [Countries] Cause: Timeout de l\'API (10s)')
        } else if (err.name === 'TypeError' && err.message.includes('fetch')) {
          console.warn('🌍 [Countries] Cause: Problème de connexion réseau')
        } else {
          console.warn('🐛 [Countries] Cause:', err.message)
        }
        
        setCountries(fallbackCountries)
        setUsingFallback(true)
      } finally {
        console.log('🏁 [Countries] Chargement terminé')
        setLoading(false)
      }
    }

    const timer = setTimeout(() => {
      console.log('⏰ [Countries] Démarrage après délai de 100ms')
      fetchCountries()
    }, 100)
    
    return () => clearTimeout(timer)
  }, [])

  console.log(`🔄 [Countries] Render - ${countries.length} pays, loading:${loading}, fallback:${usingFallback}`)
  return { countries, loading, usingFallback }
}

// Hook pour créer le mapping des codes téléphoniques
export const useCountryCodeMap = (countries: Country[]) => {
  return useMemo(() => {
    const mapping = countries.reduce((acc, country) => {
      acc[country.value] = country.phoneCode
      return acc
    }, {} as Record<string, string>)
    
    console.log(`🗺️ [CountryCodeMap] Mapping créé avec ${Object.keys(mapping).length} entrées`)
    if (Object.keys(mapping).length > 0) {
      console.log('📋 [CountryCodeMap] Échantillon:', Object.entries(mapping).slice(0, 3))
    }
    
    return mapping
  }, [countries])
}

// Fonctions de validation
export const validateEmail = (email: string): boolean => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

export const validatePassword = (password: string): { isValid: boolean; errors: string[] } => {
  const errors: string[] = []
  
  if (password.length < 8) {
    errors.push('Au moins 8 caractères')
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('Une majuscule')
  }
  if (!/[0-9]/.test(password)) {
    errors.push('Un chiffre')
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}

export const validatePhone = (countryCode: string, areaCode: string, phoneNumber: string): boolean => {
  if (!countryCode.trim() && !areaCode.trim() && !phoneNumber.trim()) {
    return true
  }
  
  if (countryCode.trim() || areaCode.trim() || phoneNumber.trim()) {
    if (!countryCode.trim() || !/^\+[1-9]\d{0,3}$/.test(countryCode.trim())) {
      return false
    }
    
    if (!areaCode.trim() || !/^\d{3}$/.test(areaCode.trim())) {
      return false
    }
    
    if (!phoneNumber.trim() || !/^\d{7}$/.test(phoneNumber.trim())) {
      return false
    }
  }
  
  return true
}

// Nouvelles fonctions de validation ajoutées du backup
export const validateLinkedIn = (url: string): boolean => {
  if (!url.trim()) return true
  return /^(https?:\/\/)?(www\.)?linkedin\.com\/(in|company)\/[\w\-]+\/?$/.test(url)
}

export const validateWebsite = (url: string): boolean => {
  if (!url.trim()) return true
  return /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/.test(url)
}

// Utilitaires pour Remember Me
export const rememberMeUtils = {
  save: (email: string, remember = true) => {
    try {
      if (remember && email?.trim()) {
        localStorage.setItem('intelia-remember-me', 'true')
        localStorage.setItem('intelia-last-email', email.trim())
        console.log('✅ [RememberMe] Email sauvegardé:', email.trim())
      } else {
        localStorage.removeItem('intelia-remember-me')
        localStorage.removeItem('intelia-last-email')
        console.log('🗑️ [RememberMe] Préférences effacées')
      }
    } catch (error) {
      console.error('❌ [RememberMe] Erreur sauvegarde:', error)
    }
  },
  
  load: () => {
    try {
      const rememberMe = localStorage.getItem('intelia-remember-me') === 'true'
      const lastEmail = localStorage.getItem('intelia-last-email') || ''
      
      return {
        rememberMe,
        lastEmail: rememberMe ? lastEmail : '',
        hasRememberedEmail: rememberMe && lastEmail.length > 0
      }
    } catch (error) {
      console.error('❌ [RememberMe] Erreur chargement:', error)
      return { rememberMe: false, lastEmail: '', hasRememberedEmail: false }
    }
  }
}