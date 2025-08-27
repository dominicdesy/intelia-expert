import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useAuthStore } from '@/lib/stores/auth'
import { useTranslation } from '../../hooks/useTranslation'
import { UserInfoModalProps } from '@/types'
import { PhoneInput, usePhoneValidation } from '../PhoneInput'
import { CountrySelect } from '../CountrySelect'

const fallbackCountries = [
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

interface Country {
  value: string
  label: string
  phoneCode: string
  flag?: string
}

// Countries hook with AbortController
const useCountries = () => {
  const [countries, setCountries] = useState<Country[]>(fallbackCountries)
  const [loading, setLoading] = useState(false)
  const [usingFallback, setUsingFallback] = useState(true)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const fetchCountries = async () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
      
      abortControllerRef.current = new AbortController()
      const signal = abortControllerRef.current.signal

      try {
        setLoading(true)
        const response = await fetch(
          'https://restcountries.com/v3.1/all?fields=cca2,name,idd,flag,translations',
          { signal }
        )
        
        if (!response.ok || signal.aborted) return
        
        const data = await response.json()
        if (signal.aborted) return
        
        const formattedCountries = data
          .map((country: any) => ({
            value: country.cca2,
            label: country.translations?.fra?.common || country.name.common,
            phoneCode: (country.idd?.root || '') + (country.idd?.suffixes?.[0] || ''),
            flag: country.flag
          }))
          .filter((country: Country) => 
            country.phoneCode && 
            country.phoneCode.length > 1 &&
            country.phoneCode.startsWith('+') &&
            country.value && 
            country.label
          )
          .sort((a: Country, b: Country) => a.label.localeCompare(b.label))
        
        if (formattedCountries.length >= 50 && !signal.aborted) {
          setCountries(formattedCountries)
          setUsingFallback(false)
        }
        
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          console.warn('Countries API failed, using fallback:', error)
        }
      } finally {
        if (!signal.aborted) {
          setLoading(false)
        }
      }
    }

    fetchCountries()
    
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  return { countries, loading, usingFallback }
}

// Password strength component
const PasswordStrengthIndicator: React.FC<{ password: string }> = ({ password }) => {
  const requirements = [
    { test: password.length >= 8, label: '8+ caractères' },
    { test: /[A-Z]/.test(password), label: 'Une majuscule' },
    { test: /[a-z]/.test(password), label: 'Une minuscule' },
    { test: /\d/.test(password), label: 'Un chiffre' },
    { test: /[!@#$%^&*(),.?":{}|<>]/.test(password), label: 'Caractère spécial' }
  ]

  return (
    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
      <p className="text-xs font-medium text-gray-700 mb-2">
        Le mot de passe doit contenir :
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-xs">
        {requirements.map((req, index) => (
          <div
            key={index}
            className={`flex items-center ${req.test ? 'text-green-600' : 'text-gray-400'} ${
              index === requirements.length - 1 ? 'sm:col-span-2' : ''
            }`}
          >
            <span className="mr-1">{req.test ? '✅' : '⭕'}</span>
            {req.label}
          </div>
        ))}
      </div>
    </div>
  )
}

// Password input component
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
          onChange={(e) => onChange(e.target.value)}
          className="input-primary pr-10"
          placeholder={placeholder}
          required={required}
        />
        <button
          type="button"
          onClick={onToggleShow}
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

// Error display component
const ErrorDisplay: React.FC<{ errors: string[]; title: string }> = ({ errors, title }) => {
  if (errors.length === 0) return null

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

// Main component - Uses global CSS classes
export const UserInfoModal: React.FC<UserInfoModalProps> = ({ user, onClose }) => {
  if (!user) return null

  const { updateProfile } = useAuthStore()
  const { t } = useTranslation()
  const { validatePhoneFields } = usePhoneValidation()
  
  // Memoized user data
  const userDataMemo = useMemo(() => ({
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    email: user?.email || '',
    country_code: user?.country_code || '',
    area_code: user?.area_code || '',
    phone_number: user?.phone_number || '',
    country: user?.country || '',
    linkedinProfile: user?.linkedinProfile || '',
    companyName: user?.companyName || '',
    companyWebsite: user?.companyWebsite || '',
    linkedinCorporate: user?.linkedinCorporate || ''
  }), [
    user?.firstName,
    user?.lastName,
    user?.email,
    user?.country_code,
    user?.area_code,
    user?.phone_number,
    user?.country,
    user?.linkedinProfile,
    user?.companyName,
    user?.companyWebsite,
    user?.linkedinCorporate
  ])
  
  // States
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('profile')
  const [formErrors, setFormErrors] = useState<string[]>([])
  const [passwordErrors, setPasswordErrors] = useState<string[]>([])
  const [formData, setFormData] = useState(userDataMemo)
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

  // Sync form data
  useEffect(() => {
    const needsSync = Object.keys(userDataMemo).some(key => 
      formData[key as keyof typeof formData] !== userDataMemo[key as keyof typeof userDataMemo]
    )
    
    if (needsSync) {
      setFormData(userDataMemo)
    }
  }, [userDataMemo, formData])

  const { countries, loading: countriesLoading, usingFallback } = useCountries()

  // Validation functions
  const validatePassword = useCallback((password: string): string[] => {
    const errors: string[] = []
    
    if (password.length < 8) {
      errors.push('Le mot de passe doit contenir au moins 8 caractères')
    }
    if (!/[A-Z]/.test(password)) {
      errors.push('Le mot de passe doit contenir au moins une majuscule')
    }
    if (!/[a-z]/.test(password)) {
      errors.push('Le mot de passe doit contenir au moins une minuscule')
    }
    if (!/\d/.test(password)) {
      errors.push('Le mot de passe doit contenir au moins un chiffre')
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      errors.push('Le mot de passe doit contenir au moins un caractère spécial')
    }
    
    return errors
  }, [])

  const validateEmail = useCallback((email: string): string[] => {
    const errors: string[] = []
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    
    if (!email.trim()) {
      errors.push('L\'email est requis')
    } else if (!emailRegex.test(email)) {
      errors.push('Format d\'email invalide')
    } else if (email.length > 254) {
      errors.push('L\'email est trop long (maximum 254 caractères)')
    }
    
    return errors
  }, [])

  const validateUrl = useCallback((url: string, fieldName: string): string[] => {
    const errors: string[] = []
    
    if (url.trim()) {
      try {
        new URL(url)
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
          errors.push(`${fieldName} doit commencer par http:// ou https://`)
        }
      } catch {
        errors.push(`${fieldName} n'est pas une URL valide`)
      }
    }
    
    return errors
  }, [])

  const validateLinkedInUrl = useCallback((url: string, fieldName: string): string[] => {
    const errors: string[] = []
    
    if (url.trim()) {
      const urlErrors = validateUrl(url, fieldName)
      if (urlErrors.length === 0) {
        const isValidLinkedIn = url.includes('linkedin.com/') && 
          (url.includes('/in/') || url.includes('/company/'))
        
        if (!isValidLinkedIn) {
          errors.push(`${fieldName} doit être un lien LinkedIn valide`)
        }
      } else {
        errors.push(...urlErrors)
      }
    }
    
    return errors
  }, [validateUrl])

  // Event handlers
  const handleClose = useCallback(() => {
    if (!isLoading) {
      onClose()
    }
  }, [isLoading, onClose])

  const handleFormDataChange = useCallback((field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }, [])

  const handlePasswordDataChange = useCallback((field: string, value: string) => {
    setPasswordData(prev => ({ ...prev, [field]: value }))
  }, [])

  const handleShowPasswordToggle = useCallback((field: keyof typeof showPasswords) => {
    setShowPasswords(prev => ({ ...prev, [field]: !prev[field] }))
  }, [])

  const handlePhoneChange = useCallback((phoneData: { country_code: string; area_code: string; phone_number: string }) => {
    setFormData(prev => ({
      ...prev,
      country_code: phoneData.country_code,
      area_code: phoneData.area_code,
      phone_number: phoneData.phone_number
    }))
  }, [])

  const handleProfileSave = useCallback(async () => {
    if (isLoading) return
    
    setIsLoading(true)
    setFormErrors([])
    
    try {
      const errors: string[] = []
      
      // Validation
      if (!formData.firstName.trim()) {
        errors.push('Le prénom est requis')
      } else if (formData.firstName.length > 50) {
        errors.push('Le prénom est trop long (maximum 50 caractères)')
      }
      
      if (!formData.lastName.trim()) {
        errors.push('Le nom est requis')
      } else if (formData.lastName.length > 50) {
        errors.push('Le nom est trop long (maximum 50 caractères)')
      }
      
      const emailErrors = validateEmail(formData.email)
      errors.push(...emailErrors)
      
      // Phone validation
      const hasPhoneData = formData.country_code || formData.area_code || formData.phone_number
      if (hasPhoneData) {
        const phoneValidation = validatePhoneFields(
          formData.country_code, 
          formData.area_code, 
          formData.phone_number
        )
        
        if (!phoneValidation.isValid) {
          errors.push(...phoneValidation.errors.map(err => `Téléphone: ${err}`))
        }
      }
      
      // URL validations
      if (formData.linkedinProfile) {
        const linkedinErrors = validateLinkedInUrl(formData.linkedinProfile, 'Profil LinkedIn personnel')
        errors.push(...linkedinErrors)
      }
      
      if (formData.companyWebsite) {
        const websiteErrors = validateUrl(formData.companyWebsite, 'Site web de l\'entreprise')
        errors.push(...websiteErrors)
      }
      
      if (formData.linkedinCorporate) {
        const corporateErrors = validateLinkedInUrl(formData.linkedinCorporate, 'Page LinkedIn entreprise')
        errors.push(...corporateErrors)
      }
      
      if (formData.companyName && formData.companyName.length > 100) {
        errors.push('Le nom de l\'entreprise est trop long (maximum 100 caractères)')
      }
      
      if (errors.length > 0) {
        setFormErrors(errors)
        return
      }

      await updateProfile(formData)
      alert(t('profile.title') + ' mis à jour avec succès!')
      handleClose()
      
    } catch (error: any) {
      console.error('Erreur mise à jour profil:', error)
      alert('Erreur lors de la mise à jour: ' + (error?.message || 'Erreur inconnue'))
    } finally {
      setIsLoading(false)
    }
  }, [formData, validateEmail, validateUrl, validateLinkedInUrl, validatePhoneFields, updateProfile, t, handleClose, isLoading])

  const handlePasswordChange = useCallback(async () => {
    if (isLoading) return
    
    const errors: string[] = []
    
    if (!passwordData.currentPassword) {
      errors.push('Le mot de passe actuel est requis')
    }
    if (!passwordData.newPassword) {
      errors.push('Le nouveau mot de passe est requis')
    }
    if (!passwordData.confirmPassword) {
      errors.push('La confirmation du mot de passe est requise')
    }
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      errors.push('Les mots de passe ne correspondent pas')
    }
    
    const passwordValidationErrors = validatePassword(passwordData.newPassword)
    errors.push(...passwordValidationErrors)
    
    setPasswordErrors(errors)
    
    if (errors.length > 0) {
      return
    }

    setIsLoading(true)
    
    try {
      const loginResponse = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: user?.email,
          password: passwordData.currentPassword
        })
      })

      if (!loginResponse.ok) {
        setPasswordErrors(['Le mot de passe actuel est incorrect'])
        return
      }

      const loginData = await loginResponse.json()
      const backendToken = loginData.access_token

      const response = await fetch('/api/v1/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${backendToken}`
        },
        body: JSON.stringify({
          current_password: passwordData.currentPassword,
          new_password: passwordData.newPassword
        })
      })

      let result: any = null
      try {
        result = await response.json()
      } catch {}
      
      if (!response.ok) {
        setPasswordErrors([result?.detail || result?.message || 'Erreur lors du changement de mot de passe'])
        return
      }
      
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      })
      setPasswordErrors([])
      alert('Mot de passe changé avec succès!')
      handleClose()
      
    } catch (error: any) {
      console.error('Erreur technique:', error)
      setPasswordErrors(['Erreur de connexion au serveur. Veuillez réessayer.'])
    } finally {
      setIsLoading(false)
    }
  }, [passwordData, validatePassword, user?.email, handleClose, isLoading])

  const tabs = useMemo(() => [
    { id: 'profile', label: t('nav.profile'), icon: '👤' },
    { id: 'password', label: t('profile.password'), icon: '🔐' }
  ], [t])

  // Keyboard handling
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) {
        handleClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleClose, isLoading])

  return (
    <div className="user-info-modal" onClick={handleClose}>
      <div
        className="user-info-modal-content"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 flex-shrink-0">
          <h2 className="text-xl font-semibold text-gray-900">
            {t('profile.title')}
          </h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 text-2xl font-light w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors"
            disabled={isLoading}
          >
            ×
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 flex-shrink-0">
          <nav className="flex px-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-3 px-4 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-6 space-y-6">
            
            {/* Errors */}
            <ErrorDisplay errors={formErrors} title="Erreurs de validation" />

            {/* Fallback Warning */}
            {usingFallback && !countriesLoading && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                <div className="flex items-center space-x-2">
                  <svg className="w-4 h-4 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <span className="text-sm text-yellow-800">
                    Liste de pays limitée (service externe temporairement indisponible)
                  </span>
                </div>
              </div>
            )}

            {/* Profile Tab */}
            {activeTab === 'profile' && (
              <div className="space-y-6">
                
                {/* Personal Info */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <span className="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                    {t('profile.personalInfo')}
                    <span className="text-red-500 ml-1">*</span>
                  </h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.firstName')} <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={formData.firstName}
                        onChange={(e) => handleFormDataChange('firstName', e.target.value)}
                        className="input-primary"
                        required
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.lastName')} <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={formData.lastName}
                        onChange={(e) => handleFormDataChange('lastName', e.target.value)}
                        className="input-primary"
                        required
                      />
                    </div>
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('profile.email')} <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => handleFormDataChange('email', e.target.value)}
                      className="input-primary"
                      required
                    />
                  </div>

                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      {t('profile.phone')} <span className="text-gray-500 text-sm">(optionnel)</span>
                    </label>
                    <PhoneInput
                      countryCode={formData.country_code}
                      areaCode={formData.area_code}
                      phoneNumber={formData.phone_number}
                      onChange={handlePhoneChange}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('profile.country')} <span className="text-gray-500 text-sm">(optionnel)</span>
                    </label>
                    <CountrySelect
                      countries={countries}
                      value={formData.country}
                      onChange={(countryValue: string) => handleFormDataChange('country', countryValue)}
                      placeholder="Sélectionner un pays ou rechercher..."
                    />
                  </div>
                </div>

                {/* Professional Info */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                    Informations Professionnelles
                    <span className="text-gray-500 text-sm ml-2">(optionnel)</span>
                  </h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Profil LinkedIn Personnel
                      </label>
                      <input
                        type="url"
                        value={formData.linkedinProfile}
                        onChange={(e) => handleFormDataChange('linkedinProfile', e.target.value)}
                        placeholder="https://linkedin.com/in/votre-profil"
                        className="input-primary"
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
                        placeholder="Nom de votre entreprise ou exploitation"
                        className="input-primary"
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
                        placeholder="https://www.votre-entreprise.com"
                        className="input-primary"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Page LinkedIn Entreprise
                      </label>
                      <input
                        type="url"
                        value={formData.linkedinCorporate}
                        onChange={(e) => handleFormDataChange('linkedinCorporate', e.target.value)}
                        placeholder="https://linkedin.com/company/votre-entreprise"
                        className="input-primary"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Password Tab */}
            {activeTab === 'password' && (
              <div className="space-y-6">
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
                      placeholder="Tapez votre mot de passe actuel"
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
                      placeholder="Tapez votre nouveau mot de passe"
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
                      placeholder="Confirmez votre nouveau mot de passe"
                      autoComplete="new-password"
                      required
                      showPassword={showPasswords.confirmPassword}
                      onToggleShow={() => handleShowPasswordToggle('confirmPassword')}
                    />
                  </div>
                </div>
                
                <ErrorDisplay errors={passwordErrors} title="Erreurs" />
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end space-x-3 p-6 border-t border-gray-200 flex-shrink-0 bg-gray-50">
          <button
            onClick={handleClose}
            className="px-5 py-2 text-gray-600 hover:text-gray-800 font-medium transition-colors"
            disabled={isLoading}
          >
            Annuler
          </button>
          <button
            onClick={activeTab === 'profile' ? handleProfileSave : handlePasswordChange}
            disabled={isLoading}
            className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center"
          >
            {isLoading && (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
            )}
            {isLoading ? 'Chargement...' : 'Sauvegarder'}
          </button>
        </div>
      </div>
    </div>
  )
}