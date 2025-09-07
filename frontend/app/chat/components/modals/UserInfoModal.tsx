import React, { useState, useEffect, useMemo, useCallback, useRef, startTransition } from 'react'
import { useTranslation } from '@/lib/languages/i18n'
import { useAuthStore } from '@/lib/stores/auth' // ✅ Store unifié uniquement
import { UserInfoModalProps } from '@/types'
import { PhoneInput, usePhoneValidation } from '../PhoneInput'
import { CountrySelect } from '../CountrySelect'
import { apiClient } from '@/lib/api/client'

// Debug utility - TEMPORAIREMENT DÉSACTIVÉ
const debugLog = (category: string, message: string, data?: any) => {
  // Désactivé pour réduire le bruit console
  return
}

interface Country {
  value: string
  label: string
  phoneCode: string
  flag?: string
}

// Mapping des codes de langue vers les codes utilisés par REST Countries
const getLanguageCode = (currentLanguage: string): string => {
  const mapping: Record<string, string> = {
    'fr': 'fra',   // Français
    'es': 'spa',   // Espagnol
    'de': 'deu',   // Allemand
    'pt': 'por',   // Portugais
    'nl': 'nld',   // Néerlandais
    'pl': 'pol',   // Polonais
    'zh': 'zho',   // Chinois
    'hi': 'hin',   // Hindi
    'th': 'tha',   // Thaï
    'en': 'eng'    // Anglais (fallback)
  }
  return mapping[currentLanguage] || 'eng'
}

// Fallback countries avec traductions multilingues (conservé)
const getFallbackCountries = (currentLanguage: string): Country[] => {
  const translations: Record<string, Record<string, string>> = {
    en: {
      'CA': 'Canada',
      'US': 'United States',
      'FR': 'France',
      'GB': 'United Kingdom',
      'DE': 'Germany',
      'IT': 'Italy',
      'ES': 'Spain',
      'BE': 'Belgium',
      'CH': 'Switzerland',
      'MX': 'Mexico',
      'BR': 'Brazil',
      'AU': 'Australia',
      'JP': 'Japan',
      'CN': 'China',
      'IN': 'India',
      'NL': 'Netherlands',
      'SE': 'Sweden',
      'NO': 'Norway',
      'DK': 'Denmark',
      'FI': 'Finland'
    },
    fr: {
      'CA': 'Canada',
      'US': 'États-Unis',
      'FR': 'France',
      'GB': 'Royaume-Uni',
      'DE': 'Allemagne',
      'IT': 'Italie',
      'ES': 'Espagne',
      'BE': 'Belgique',
      'CH': 'Suisse',
      'MX': 'Mexique',
      'BR': 'Brésil',
      'AU': 'Australie',
      'JP': 'Japon',
      'CN': 'Chine',
      'IN': 'Inde',
      'NL': 'Pays-Bas',
      'SE': 'Suède',
      'NO': 'Norvège',
      'DK': 'Danemark',
      'FI': 'Finlande'
    }
  }

  const phoneCodesMap: Record<string, string> = {
    'CA': '+1', 'US': '+1', 'FR': '+33', 'GB': '+44', 'DE': '+49',
    'IT': '+39', 'ES': '+34', 'BE': '+32', 'CH': '+41', 'MX': '+52',
    'BR': '+55', 'AU': '+61', 'JP': '+81', 'CN': '+86', 'IN': '+91',
    'NL': '+31', 'SE': '+46', 'NO': '+47', 'DK': '+45', 'FI': '+358'
  }

  const flagsMap: Record<string, string> = {
    'CA': '🇨🇦', 'US': '🇺🇸', 'FR': '🇫🇷', 'GB': '🇬🇧', 'DE': '🇩🇪',
    'IT': '🇮🇹', 'ES': '🇪🇸', 'BE': '🇧🇪', 'CH': '🇨🇭', 'MX': '🇲🇽',
    'BR': '🇧🇷', 'AU': '🇦🇺', 'JP': '🇯🇵', 'CN': '🇨🇳', 'IN': '🇮🇳',
    'NL': '🇳🇱', 'SE': '🇸🇪', 'NO': '🇳🇴', 'DK': '🇩🇰', 'FI': '🇫🇮'
  }

  const langTranslations = translations[currentLanguage] || translations.en
  
  return Object.keys(langTranslations).map(code => ({
    value: code,
    label: langTranslations[code],
    phoneCode: phoneCodesMap[code],
    flag: flagsMap[code]
  })).sort((a, b) => {
    const locale = currentLanguage === 'fr' ? 'fr' : 'en'
    return a.label.localeCompare(b.label, locale, { numeric: true })
  })
}

// Interface TypeScript pour les données utilisateur API (conservée)
interface UserProfileUpdate {
  first_name?: string
  last_name?: string
  full_name?: string
  country_code?: string
  area_code?: string
  phone_number?: string
  country?: string
  linkedin_profile?: string
  company_name?: string
  company_website?: string
  linkedin_corporate?: string
  user_type?: string
  language?: string
}

const useCountries = () => {
  const { currentLanguage } = useTranslation()
  const languageCode = getLanguageCode(currentLanguage)
  
  const [countries, setCountries] = useState<Country[]>(() => getFallbackCountries(currentLanguage))
  const [loading, setLoading] = useState(false)
  const [usingFallback, setUsingFallback] = useState(true)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    debugLog('COUNTRIES', 'Hook initialized with language', currentLanguage)
    
    const fetchCountries = async () => {
      if (abortControllerRef.current) {
        debugLog('COUNTRIES', 'Aborting previous request')
        abortControllerRef.current.abort()
      }
      
      abortControllerRef.current = new AbortController()
      const signal = abortControllerRef.current.signal

      try {
        debugLog('COUNTRIES', `Starting fetch for language: ${currentLanguage} (${languageCode})`)
        setLoading(true)
        
        const response = await fetch(
          'https://restcountries.com/v3.1/all?fields=cca2,name,idd,flag,translations',
          { 
            signal,
            headers: {
              'Accept': 'application/json',
              'User-Agent': 'Mozilla/5.0 (compatible; Intelia/1.0)',
              'Cache-Control': 'no-cache'
            }
          }
        )
        
        debugLog('COUNTRIES', 'Fetch response', { ok: response.ok, status: response.status })
        
        if (!response.ok || signal.aborted) return
        
        const data = await response.json()
        debugLog('COUNTRIES', 'Data received', { count: data?.length })
        
        if (signal.aborted) return
        
        const formattedCountries = data
          .map((country: any) => {
            let phoneCode = ''
            if (country.idd?.root) {
              phoneCode = country.idd.root
              if (country.idd.suffixes && country.idd.suffixes[0]) {
                phoneCode += country.idd.suffixes[0]
              }
            }
            
            // Récupération du nom selon la langue
            let countryName = country.name?.common || country.cca2
            
            // Essayer d'abord la traduction dans la langue demandée
            if (country.translations && country.translations[languageCode]) {
              countryName = country.translations[languageCode].common || country.translations[languageCode].official
            }
            // Si pas de traduction dans la langue demandée, utiliser l'anglais
            else if (country.name?.common) {
              countryName = country.name.common
            }
            
            return {
              value: country.cca2,
              label: countryName,
              phoneCode: phoneCode,
              flag: country.flag || ''
            }
          })
          .filter((country: Country) => {
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
            
            return hasValidCode && hasValidInfo
          })
          .sort((a: Country, b: Country) => {
            // Tri selon la langue actuelle
            const locale = languageCode === 'fra' ? 'fr' : 
                          languageCode === 'spa' ? 'es' :
                          languageCode === 'deu' ? 'de' :
                          languageCode === 'por' ? 'pt' :
                          languageCode === 'nld' ? 'nl' :
                          languageCode === 'pol' ? 'pl' :
                          languageCode === 'zho' ? 'zh' :
                          'en'
            
            return a.label.localeCompare(b.label, locale, { numeric: true })
          })
        
        debugLog('COUNTRIES', 'Countries processed', { count: formattedCountries.length })
        
        if (formattedCountries.length >= 50 && !signal.aborted) {
          setCountries(formattedCountries)
          setUsingFallback(false)
          debugLog('COUNTRIES', `Using API countries in ${currentLanguage}`)
          
          // Logs de debug pour vérifier les traductions
          const france = formattedCountries.find(c => c.value === 'FR')
          const usa = formattedCountries.find(c => c.value === 'US')
          const germany = formattedCountries.find(c => c.value === 'DE')
          
          console.log(`[UserInfoModal-Countries] Exemples en ${currentLanguage}:`)
          console.log('  France:', france?.label)
          console.log('  USA:', usa?.label)
          console.log('  Germany:', germany?.label)
        }
        
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError' && !signal.aborted) {
          debugLog('COUNTRIES', 'Fetch error, using fallback', error.message)
          // En cas d'erreur, utiliser le fallback dans la bonne langue
          setCountries(getFallbackCountries(currentLanguage))
          setUsingFallback(true)
        }
      } finally {
        if (!signal.aborted) {
          setLoading(false)
          debugLog('COUNTRIES', 'Loading finished')
        }
      }
    }

    // Toujours commencer par mettre à jour le fallback dans la bonne langue
    setCountries(getFallbackCountries(currentLanguage))
    
    fetchCountries()
    
    return () => {
      debugLog('COUNTRIES', 'Cleanup')
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [currentLanguage, languageCode]) // Se redéclenche quand la langue change

  return { countries, loading, usingFallback }
}

// Nouvelle fonction de validation de mot de passe moderne (conservée)
const validatePassword = (password: string): string[] => {
  const errors: string[] = []
  
  // Vérifier que le mot de passe n'est pas vide ou seulement des espaces
  if (!password || password.trim().length === 0) {
    errors.push('Le mot de passe est requis')
    return errors
  }
  
  // Minimum 8 caractères
  if (password.length < 8) {
    errors.push('Au moins 8 caractères requis')
  }
  
  // Maximum 128 caractères (sécurité contre les attaques DoS)
  if (password.length > 128) {
    errors.push('Maximum 128 caractères autorisés')
  }
  
  // Au moins une lettre (majuscule ou minuscule)
  if (!/[a-zA-Z]/.test(password)) {
    errors.push('Au moins une lettre requise')
  }
  
  // Au moins un chiffre
  if (!/\d/.test(password)) {
    errors.push('Au moins un chiffre requis')
  }
  
  // Vérifier les mots de passe faibles courants
  const commonPasswords = [
    'password', '12345678', 'qwerty123', 'abc123456', 
    'password1', 'password123', '123456789', 'motdepasse',
    'azerty123', '11111111', '00000000'
  ]
  if (commonPasswords.some(common => 
    password.toLowerCase().includes(common.toLowerCase())
  )) {
    errors.push('Mot de passe trop commun')
  }
  
  // Vérifier la répétition excessive (plus de 3 caractères identiques consécutifs)
  if (/(.)\1{3,}/.test(password)) {
    errors.push('Trop de caractères identiques consécutifs')
  }
  
  // Bonus: Vérifier que ce n'est pas que des caractères séquentiels
  const sequentialPatterns = [
    '12345678', '87654321', 'abcdefgh', 'zyxwvuts',
    'qwertyui', 'asdfghjk', 'zxcvbnm'
  ]
  if (sequentialPatterns.some(pattern => 
    password.toLowerCase().includes(pattern)
  )) {
    errors.push('Évitez les séquences de caractères')
  }
  
  return errors
}

// Composant d'indicateur de force du mot de passe moderne (conservé)
const PasswordStrengthIndicator: React.FC<{ password: string }> = ({ password }) => {
  const validation = { errors: validatePassword(password) }
  
  const requirements = [
    { test: password.length >= 8, label: 'Au moins 8 caractères' },
    { test: /[a-zA-Z]/.test(password), label: 'Au moins une lettre' },
    { test: /\d/.test(password), label: 'Au moins un chiffre' },
    { test: !/(.)\\1{3,}/.test(password), label: 'Pas de répétitions excessives' },
    { test: password.length <= 128, label: 'Longueur raisonnable' }
  ]

  // Calculer le score de force
  const passedRequirements = requirements.filter(req => req.test).length
  const strength = passedRequirements / requirements.length
  
  const getStrengthColor = () => {
    if (strength < 0.4) return 'bg-red-500'
    if (strength < 0.7) return 'bg-yellow-500'
    if (strength < 0.9) return 'bg-blue-500'
    return 'bg-green-500'
  }
  
  const getStrengthLabel = () => {
    if (strength < 0.4) return 'Faible'
    if (strength < 0.7) return 'Moyen'
    if (strength < 0.9) return 'Bon'
    return 'Excellent'
  }

  return (
    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-gray-700">
          Force du mot de passe
        </p>
        <span className={`text-xs font-medium ${
          strength < 0.4 ? 'text-red-600' :
          strength < 0.7 ? 'text-yellow-600' :
          strength < 0.9 ? 'text-blue-600' : 'text-green-600'
        }`}>
          {getStrengthLabel()}
        </span>
      </div>
      
      {/* Barre de progression */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
        <div 
          className={`h-2 rounded-full transition-all duration-300 ${getStrengthColor()}`}
          style={{ width: `${strength * 100}%` }}
        ></div>
      </div>
      
      {/* Liste des exigences */}
      <div className="grid grid-cols-1 gap-1 text-xs">
        {requirements.map((req, index) => (
          <div
            key={index}
            className={`flex items-center ${req.test ? 'text-green-600' : 'text-gray-400'}`}
          >
            <span className="mr-2 text-sm">{req.test ? '✅' : '⭕'}</span>
            <span>{req.label}</span>
          </div>
        ))}
        
        {/* Afficher les erreurs spécifiques */}
        {validation.errors.map((error, index) => (
          <div key={`error-${index}`} className="flex items-center text-red-600">
            <span className="mr-2 text-sm">❌</span>
            <span>{error}</span>
          </div>
        ))}
      </div>
      
      {/* Conseils pour améliorer le mot de passe */}
      {strength < 1 && (
        <div className="mt-3 pt-2 border-t border-gray-200">
          <p className="text-xs text-gray-600 font-medium mb-1">Conseils :</p>
          <ul className="text-xs text-gray-600 space-y-1">
            {password.length < 12 && (
              <li>• Utilisez 12+ caractères pour plus de sécurité</li>
            )}
            {!/[A-Z]/.test(password) && !/[a-z]/.test(password) && (
              <li>• Mélangez majuscules et minuscules</li>
            )}
            {!/[!@#$%^&*()_+=\[\]{};':"|,.<>?-]/.test(password) && (
              <li>• Les caractères spéciaux renforcent la sécurité (optionnel)</li>
            )}
          </ul>
        </div>
      )}
    </div>
  )
}

// Password input component (conservé)
const PasswordInput: React.FC<{
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  placeholder: string
  autoComplete: string
  required?: boolean
  showStrength?: boolean
  showPassword: boolean
  onToggleShow: () => void
}> = ({ id, label, value, onChange, placeholder, autoComplete, required, showStrength, showPassword, onToggleShow }) => {
  debugLog('COMPONENT', `PasswordInput rendered for ${id}`)
  
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <div className="relative">
        <input
          id={id}
          type={showPassword ? "text" : "password"}
          name={id}
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => {
            debugLog('INPUT', `Password ${id} changed`, { length: e.target.value.length })
            onChange(e.target.value)
          }}
          className="input-primary pr-10"
          placeholder={placeholder}
          required={required}
        />
        <button
          type="button"
          onClick={() => {
            debugLog('INTERACTION', `Toggle password visibility for ${id}`)
            onToggleShow()
          }}
          className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 transition-colors"
        >
          {showPassword ? (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 11-4.243-4.243m4.242 4.242L9.88 9.88" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          )}
        </button>
      </div>
      {showStrength && <PasswordStrengthIndicator password={value} />}
    </div>
  )
}

// Error display component (conservé)
const ErrorDisplay: React.FC<{ errors: string[]; title: string }> = ({ errors, title }) => {
  if (errors.length === 0) return null

  debugLog('ERROR', `Displaying ${errors.length} errors`, errors)

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <div className="text-sm text-red-800">
        <p className="font-medium mb-2">{title} :</p>
        <ul className="list-disc list-inside space-y-1">
          {errors.map((error, index) => (
            <li key={index}>{error}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}

// Main component
export const UserInfoModal: React.FC<UserInfoModalProps> = ({ user, onClose }) => {
  debugLog('LIFECYCLE', 'Component mounting', { 
    hasUser: !!user, 
    userEmail: user?.email,
    timestamp: Date.now()
  })
  
  if (!user) {
    debugLog('LIFECYCLE', 'No user provided - returning null')
    return null
  }

  // ✅ UTILISE LE STORE UNIFIÉ au lieu de updateProfile
  const { updateProfile } = useAuthStore()

  // Protection unmount-safe
  const isMountedRef = useRef(true)
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  // Hook de traduction avec gestion des changements de langue
  const { t, changeLanguage, getCurrentLanguage } = useTranslation()

  const { validatePhoneFields } = usePhoneValidation()
  const overlayRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  
  // Forcer les styles au montage - IDENTIQUE À LanguageModal
  useEffect(() => {
    const overlay = overlayRef.current
    
    if (overlay) {
      overlay.style.setProperty('width', '100vw', 'important')
      overlay.style.setProperty('height', '100vh', 'important')
      overlay.style.setProperty('top', '0', 'important')
      overlay.style.setProperty('left', '0', 'important')
      overlay.style.setProperty('right', '0', 'important')
      overlay.style.setProperty('bottom', '0', 'important')
      overlay.style.setProperty('background-color', 'rgba(0, 0, 0, 0.5)', 'important')
      overlay.style.setProperty('backdrop-filter', 'blur(2px)', 'important')
      overlay.style.setProperty('display', 'flex', 'important')
      overlay.style.setProperty('align-items', 'center', 'important')
      overlay.style.setProperty('justify-content', 'center', 'important')
      overlay.style.setProperty('padding', '16px', 'important')
      
      const content = overlay.querySelector('[data-modal="user-info"]') as HTMLElement
      if (content) {
        content.style.setProperty('width', '95vw', 'important')
        content.style.setProperty('max-width', '700px', 'important')
        content.style.setProperty('max-height', '85vh', 'important')
        content.style.setProperty('min-width', '320px', 'important')
        content.style.setProperty('background-color', 'white', 'important')
      }
    }
  }, [])
  
  // userDataMemo avec dépendance stable
  const userDataMemo = useMemo(() => {
    if (!user?.id) {
      return {
        firstName: '',
        lastName: '',
        email: '',
        country_code: '',
        area_code: '',
        phone_number: '',
        country: '',
        linkedinProfile: '',
        companyName: '',
        companyWebsite: '',
        linkedinCorporate: ''
      }
    }
    
    const memo = {
      firstName: user.firstName || '',
      lastName: user.lastName || '',
      email: user.email || '',
      country_code: user.country_code || '',
      area_code: user.area_code || '',
      phone_number: user.phone_number || '',
      country: user.country || '',
      linkedinProfile: user.linkedinProfile || '',
      companyName: user.companyName || '',
      companyWebsite: user.companyWebsite || '',
      linkedinCorporate: user.linkedinCorporate || ''
    }
    
    debugLog('DATA', 'User data memo updated', memo)
    return memo
  }, [user?.id])
  
  // States - Initialize with stable data
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('profile')
  const [formErrors, setFormErrors] = useState<string[]>([])
  const [passwordErrors, setPasswordErrors] = useState<string[]>([])
  
  // Initialize formData sans dépendre de userDataMemo
  const [formData, setFormData] = useState(() => {
    if (!user?.id) {
      return {
        firstName: '',
        lastName: '',
        email: '',
        country_code: '',
        area_code: '',
        phone_number: '',
        country: '',
        linkedinProfile: '',
        companyName: '',
        companyWebsite: '',
        linkedinCorporate: ''
      }
    }
    
    debugLog('STATE', 'Initializing formData with user data')
    return {
      firstName: user.firstName || '',
      lastName: user.lastName || '',
      email: user.email || '',
      country_code: user.country_code || '',
      area_code: user.area_code || '',
      phone_number: user.phone_number || '',
      country: user.country || '',
      linkedinProfile: user.linkedinProfile || '',
      companyName: user.companyName || '',
      companyWebsite: user.companyWebsite || '',
      linkedinCorporate: user.linkedinCorporate || ''
    }
  })
  
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })
  const [showPasswords, setShowPasswords] = useState({
    currentPassword: false,
    newPassword: false,
    confirmPassword: false
  })

  debugLog('STATE', 'Component states initialized', {
    isLoading,
    activeTab,
    formErrorsCount: formErrors.length,
    passwordErrorsCount: passwordErrors.length
  })

  const { countries, loading: countriesLoading, usingFallback } = useCountries()

  // Validation functions - MISE À JOUR AVEC LA NOUVELLE LOGIQUE
  const validatePasswordField = useCallback((password: string): string[] => {
    return validatePassword(password)
  }, [])

  const validateEmail = useCallback((email: string): string[] => {
    const errors: string[] = []
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    
    if (!email.trim()) {
      errors.push(t('error.emailRequired'))
    } else if (!emailRegex.test(email)) {
      errors.push(t('error.emailInvalid'))
    } else if (email.length > 254) {
      errors.push(t('error.emailTooLong'))
    }
    
    debugLog('VALIDATION', 'Email validation', { email, errors })
    return errors
  }, [t])

  const validateUrl = useCallback((url: string, fieldName: string): string[] => {
    const errors: string[] = []
    
    if (url.trim()) {
      try {
        new URL(url)
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
          errors.push(`${fieldName} ${t('error.urlProtocol')}`)
        }
      } catch {
        errors.push(`${fieldName} ${t('error.urlInvalid')}`)
      }
    }
    
    debugLog('VALIDATION', 'URL validation', { url, fieldName, errors })
    return errors
  }, [t])

  const validateLinkedInUrl = useCallback((url: string, fieldName: string): string[] => {
    const errors: string[] = []
    
    if (url.trim()) {
      const urlErrors = validateUrl(url, fieldName)
      if (urlErrors.length === 0) {
        const isValidLinkedIn = url.includes('linkedin.com/') && 
          (url.includes('/in/') || url.includes('/company/'))
        
        if (!isValidLinkedIn) {
          errors.push(`${fieldName} ${t('error.linkedinInvalid')}`)
        }
      } else {
        errors.push(...urlErrors)
      }
    }
    
    debugLog('VALIDATION', 'LinkedIn URL validation', { url, fieldName, errors })
    return errors
  }, [validateUrl, t])

  // Event handlers
  const handleClose = useCallback(() => {
    debugLog('INTERACTION', 'Close button clicked', { isLoading })
    if (!isLoading) {
      onClose()
    }
  }, [isLoading, onClose])

  const handleFormDataChange = useCallback((field: string, value: string) => {
    debugLog('INTERACTION', 'Form data changed', { field, value: value.substring(0, 20) + '...' })
    setFormData(prev => ({ ...prev, [field]: value }))
  }, [])

  const handlePasswordDataChange = useCallback((field: string, value: string) => {
    debugLog('INTERACTION', 'Password data changed', { field, valueLength: value.length })
    setPasswordData(prev => ({ ...prev, [field]: value }))
  }, [])

  const handleShowPasswordToggle = useCallback((field: keyof typeof showPasswords) => {
    debugLog('INTERACTION', 'Password visibility toggled', { field })
    setShowPasswords(prev => ({ ...prev, [field]: !prev[field] }))
  }, [])

  const handlePhoneChange = useCallback((phoneData: { country_code: string; area_code: string; phone_number: string }) => {
    debugLog('INTERACTION', 'Phone data changed', phoneData)
    setFormData(prev => ({
      ...prev,
      country_code: phoneData.country_code,
      area_code: phoneData.area_code,
      phone_number: phoneData.phone_number
    }))
  }, [])

  // ✅ FONCTION handleProfileSave SIMPLIFIÉE - Utilise le store unifié
  const handleProfileSave = useCallback(async () => {
    if (!isMountedRef.current || isLoading) return
    setIsLoading(true)
    setFormErrors([])

    try {
      const errors: string[] = []

      // Validation complète avec traductions
      if (!formData.firstName.trim()) {
        errors.push(t('error.firstNameRequired'))
      } else if (formData.firstName.length > 50) {
        errors.push(t('error.firstNameTooLong'))
      }

      if (!formData.lastName.trim()) {
        errors.push(t('error.lastNameRequired'))
      } else if (formData.lastName.length > 50) {
        errors.push(t('error.lastNameTooLong'))
      }

      const emailErrors = validateEmail(formData.email)
      errors.push(...emailErrors)

      const hasPhoneData = formData.country_code || formData.area_code || formData.phone_number
      if (hasPhoneData) {
        const phoneValidation = validatePhoneFields(
          formData.country_code,
          formData.area_code,
          formData.phone_number
        )
        if (!phoneValidation.isValid) {
          errors.push(...phoneValidation.errors.map(err => `${t('error.phonePrefix')} ${err}`))
        }
      }

      if (formData.linkedinProfile) {
        const linkedinErrors = validateLinkedInUrl(formData.linkedinProfile, t('profile.linkedinProfile'))
        errors.push(...linkedinErrors)
      }

      if (formData.companyWebsite) {
        const websiteErrors = validateUrl(formData.companyWebsite, t('profile.companyWebsite'))
        errors.push(...websiteErrors)
      }

      if (formData.linkedinCorporate) {
        const corporateErrors = validateLinkedInUrl(formData.linkedinCorporate, t('profile.linkedinCorporate'))
        errors.push(...corporateErrors)
      }

      if (formData.companyName && formData.companyName.length > 100) {
        errors.push(t('error.companyNameTooLong'))
      }

      if (errors.length > 0) {
        if (isMountedRef.current) setFormErrors(errors)
        return
      }

      // ✅ UTILISER LE STORE UNIFIÉ au lieu d'apiClient direct
      console.log('[UserInfoModal] Mise à jour via store unifié')
      
      const updateData = {
        firstName: formData.firstName?.trim(),
        lastName: formData.lastName?.trim(),
        name: `${formData.firstName?.trim()} ${formData.lastName?.trim()}`.trim(),
        email: formData.email?.trim(),
        country_code: formData.country_code,
        area_code: formData.area_code,
        phone_number: formData.phone_number,
        country: formData.country,
        linkedinProfile: formData.linkedinProfile,
        companyName: formData.companyName,
        companyWebsite: formData.companyWebsite,
        linkedinCorporate: formData.linkedinCorporate
      }

      await updateProfile(updateData)

      console.log('[UserInfoModal] Profil mis à jour avec succès via store unifié')

      if (!isMountedRef.current) return

      // Fermer immédiatement la modale
      startTransition(() => {
        if (isMountedRef.current) {
          handleClose()
        }
      })

    } catch (error: any) {
      if (isMountedRef.current) {
        console.error('Erreur mise à jour profil:', error)
        let errorMessage = t('common.unexpectedError')
        
        if (error.message) {
          if (error.message.includes('Failed to fetch')) {
            errorMessage = 'Problème de connexion réseau. Vérifiez votre connexion internet.'
          } else if (error.message.includes('401') || error.message.includes('unauthorized')) {
            errorMessage = t('error.userNotConnected')
          } else {
            errorMessage = error.message
          }
        }
        
        setFormErrors([errorMessage])
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false)
      }
    }
  }, [
    isLoading,
    formData,
    validateEmail,
    validateUrl,
    validateLinkedInUrl,
    validatePhoneFields,
    updateProfile,
    handleClose,
    t
  ])

  // ✅ FONCTION handlePasswordChange SIMPLIFIÉE - Utilise apiClient comme les autres composants
  const handlePasswordChange = useCallback(async () => {
    debugLog('API', 'Password change started')
    
    if (isLoading) return
    
    const errors: string[] = []
    
    if (!passwordData.currentPassword) {
      errors.push(t('error.currentPasswordRequired'))
    }
    if (!passwordData.newPassword) {
      errors.push(t('error.newPasswordRequired'))
    }
    if (!passwordData.confirmPassword) {
      errors.push(t('error.confirmPasswordRequired'))
    }
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      errors.push(t('form.passwordMismatch'))
    }
    
    // UTILISATION DE LA NOUVELLE LOGIQUE DE VALIDATION
    const passwordValidationErrors = validatePasswordField(passwordData.newPassword)
    errors.push(...passwordValidationErrors)
    
    setPasswordErrors(errors)
    
    if (errors.length > 0) {
      debugLog('API', 'Password change validation failed', { errors })
      return
    }

    setIsLoading(true)
    
    try {
      debugLog('API', 'Changing password via apiClient')
      
      // ✅ UTILISE APILIENT au lieu d'appels fetch directs
      const response = await apiClient.postSecure('/auth/change-password', {
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword
      })

      if (!response.success) {
        throw new Error(response.error?.message || t('error.changePassword'))
      }

      debugLog('API', 'Password changed successfully')
      
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      })
      setPasswordErrors([])
      console.log(t('success.passwordChanged'))
      
      // Fermeture non bloquante et sûre
      startTransition(() => {
        if (isMountedRef.current) {
          handleClose()
        }
      })
      
    } catch (error: any) {
      debugLog('API', 'Password change error', { error: error?.message })
      console.error('Erreur technique:', error)
      
      let errorMessage = t('error.passwordServerError')
      if (error.message?.includes('Incorrect current password')) {
        errorMessage = t('error.currentPasswordIncorrect')
      }
      
      setPasswordErrors([errorMessage])
    } finally {
      debugLog('API', 'Password change finished')
      setIsLoading(false)
    }
  }, [passwordData, validatePasswordField, handleClose, isLoading, t])

  const tabs = useMemo(() => [
    { id: 'profile', label: t('nav.profile'), icon: '👤' },
    { id: 'password', label: t('profile.password'), icon: '🔑' }
  ], [t])

  // Keyboard handling
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) {
        debugLog('INTERACTION', 'Escape key pressed')
        handleClose()
      }
    }

    debugLog('EVENTS', 'Adding keyboard listener')
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      debugLog('EVENTS', 'Removing keyboard listener')
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [handleClose, isLoading])

  // Handle overlay click
  const handleOverlayClick = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !isLoading) {
      handleClose()
    }
  }, [handleClose, isLoading])

  debugLog('RENDER', 'Component rendering', {
    activeTab,
    hasCountries: countries.length,
    usingFallback,
    countriesLoading
  })

  return (
    <div 
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        backdropFilter: 'blur(2px)'
      }}
      onClick={handleOverlayClick}
      data-debug="modal-overlay"
    >
      {/* MODAL CONTAINER */}
      <div 
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        data-modal="user-info"
        data-debug="modal-content"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {t('profile.title')}
          </h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition-colors hover:bg-gray-100 rounded-full w-8 h-8 flex items-center justify-center"
            aria-label={t('modal.close')}
            title={t('modal.close')}
            disabled={isLoading}
            data-debug="close-button"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="flex px-6" data-debug="tabs-nav">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  debugLog('INTERACTION', `Tab clicked: ${tab.id}`)
                  setActiveTab(tab.id)
                }}
                className={`py-3 px-4 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                data-debug={`tab-${tab.id}`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="p-6" data-debug="modal-body">
          <div className="space-y-6">
            
            {/* Errors */}
            <ErrorDisplay errors={formErrors} title={t('error.validationErrors')} />

            {/* Fallback Warning */}
            {usingFallback && !countriesLoading && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                <div className="flex items-center space-x-2">
                  <svg className="w-4 h-4 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <span className="text-sm text-yellow-800">
                    {t('countries.fallbackWarning')}
                  </span>
                </div>
              </div>
            )}

            {/* Profile Tab */}
            {activeTab === 'profile' && (
              <div className="space-y-6" data-debug="profile-tab">
                
                {/* Personal Info */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <span className="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                    {t('profile.personalInfo')}
                    <span className="text-red-500 ml-1">*</span>
                  </h3>
                  
                  <div className="grid grid-cols-1 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.firstName')}
                      </label>
                      <input
                        type="text"
                        value={formData.firstName}
                        onChange={(e) => handleFormDataChange('firstName', e.target.value)}
                        className="input-primary"
                        required
                        data-debug="firstName-input"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.lastName')}
                      </label>
                      <input
                        type="text"
                        value={formData.lastName}
                        onChange={(e) => handleFormDataChange('lastName', e.target.value)}
                        className="input-primary"
                        required
                        data-debug="lastName-input"
                      />
                    </div>
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('profile.email')}
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => handleFormDataChange('email', e.target.value)}
                      className="input-primary"
                      required
                      data-debug="email-input"
                    />
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      {t('profile.phone')} <span className="text-gray-500 text-sm">({t('common.optional')})</span>
                    </label>
                    <div data-debug="phone-input">
                      <PhoneInput
                        countryCode={formData.country_code}
                        areaCode={formData.area_code}
                        phoneNumber={formData.phone_number}
                        onChange={handlePhoneChange}
                        countries={countries}
                        countriesLoading={countriesLoading}
                        usingFallback={usingFallback}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('profile.country')} <span className="text-gray-500 text-sm">({t('common.optional')})</span>
                    </label>
                    <div data-debug="country-select">
                      <CountrySelect
                        countries={countries}
                        value={formData.country}
                        onChange={(countryValue: string) => handleFormDataChange('country', countryValue)}
                        placeholder={t('placeholder.countrySelect')}
                      />
                    </div>
                  </div>
                </div>

                {/* Professional Info */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                    {t('profile.professionalInfo')}
                    <span className="text-gray-500 text-sm ml-2">({t('common.optional')})</span>
                  </h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.linkedinProfile')}
                      </label>
                      <input
                        type="url"
                        value={formData.linkedinProfile}
                        onChange={(e) => handleFormDataChange('linkedinProfile', e.target.value)}
                        placeholder={t('placeholder.linkedinPersonal')}
                        className="input-primary"
                        data-debug="linkedin-input"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.companyName')}
                      </label>
                      <input
                        type="text"
                        value={formData.companyName}
                        onChange={(e) => handleFormDataChange('companyName', e.target.value)}
                        placeholder={t('placeholder.companyName')}
                        className="input-primary"
                        data-debug="company-name-input"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.companyWebsite')}
                      </label>
                      <input
                        type="url"
                        value={formData.companyWebsite}
                        onChange={(e) => handleFormDataChange('companyWebsite', e.target.value)}
                        placeholder={t('placeholder.companyWebsite')}
                        className="input-primary"
                        data-debug="company-website-input"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.linkedinCorporate')}
                      </label>
                      <input
                        type="url"
                        value={formData.linkedinCorporate}
                        onChange={(e) => handleFormDataChange('linkedinCorporate', e.target.value)}
                        placeholder={t('placeholder.linkedinCorporate')}
                        className="input-primary"
                        data-debug="linkedin-corporate-input"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Password Tab */}
            {activeTab === 'password' && (
              <div className="space-y-6" data-debug="password-tab">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <span className="w-2 h-2 bg-orange-500 rounded-full mr-2"></span>
                    {t('profile.password')}
                  </h3>
                  
                  <div className="space-y-4">
                    <PasswordInput
                      id="currentPassword"
                      label={t('profile.currentPassword')}
                      value={passwordData.currentPassword}
                      onChange={(value) => handlePasswordDataChange('currentPassword', value)}
                      placeholder={t('placeholder.currentPassword')}
                      autoComplete="current-password"
                      required
                      showPassword={showPasswords.currentPassword}
                      onToggleShow={() => handleShowPasswordToggle('currentPassword')}
                    />
                    
                    <PasswordInput
                      id="newPassword"
                      label={t('profile.newPassword')}
                      value={passwordData.newPassword}
                      onChange={(value) => handlePasswordDataChange('newPassword', value)}
                      placeholder={t('placeholder.newPassword')}
                      autoComplete="new-password"
                      required
                      showStrength
                      showPassword={showPasswords.newPassword}
                      onToggleShow={() => handleShowPasswordToggle('newPassword')}
                    />
                    
                    <PasswordInput
                      id="confirmPassword"
                      label={t('profile.confirmPassword')}
                      value={passwordData.confirmPassword}
                      onChange={(value) => handlePasswordDataChange('confirmPassword', value)}
                      placeholder={t('placeholder.confirmPassword')}
                      autoComplete="new-password"
                      required
                      showPassword={showPasswords.confirmPassword}
                      onToggleShow={() => handleShowPasswordToggle('confirmPassword')}
                    />
                  </div>
                </div>
                
                <ErrorDisplay errors={passwordErrors} title={t('profile.passwordErrors')} />
              </div>
            )}

            {/* Footer Buttons */}
            <div className="flex justify-end space-x-3 pt-4 pb-8" data-debug="footer">
              <button
                onClick={handleClose}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium transition-colors"
                disabled={isLoading}
                data-debug="cancel-button"
              >
                {t('modal.cancel')}
              </button>
              <button
                onClick={activeTab === 'profile' ? handleProfileSave : handlePasswordChange}
                disabled={isLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                data-debug="save-button"
              >
                {isLoading && (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                )}
                {isLoading ? t('modal.loading') : t('modal.save')}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}