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

// Clean countries hook with AbortController
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

// Inline styles to avoid CSS conflicts
const styles = {
  overlay: {
    position: 'fixed' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    zIndex: 10000,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '16px'
  },
  modal: {
    position: 'relative' as const,
    width: '100%',
    maxWidth: '672px', // max-w-2xl
    maxHeight: '85vh',
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden'
  },
  header: {
    padding: '24px',
    borderBottom: '1px solid #e5e7eb',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexShrink: 0
  },
  closeButton: {
    color: '#9ca3af',
    fontSize: '24px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '8px',
    borderRadius: '8px',
    transition: 'all 0.2s',
    width: '32px',
    height: '32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  tabsContainer: {
    borderBottom: '1px solid #e5e7eb',
    flexShrink: 0
  },
  tabsNav: {
    display: 'flex',
    padding: '0 24px'
  },
  tab: {
    padding: '12px 16px',
    fontSize: '14px',
    fontWeight: '500',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.2s',
    borderBottom: '2px solid transparent'
  },
  activeTab: {
    color: '#2563eb',
    borderBottomColor: '#3b82f6'
  },
  inactiveTab: {
    color: '#6b7280'
  },
  content: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '24px'
  },
  footer: {
    padding: '24px',
    borderTop: '1px solid #e5e7eb',
    backgroundColor: '#f9fafb',
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    flexShrink: 0
  },
  input: {
    width: '100%',
    padding: '8px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '16px',
    color: '#111827',
    backgroundColor: '#ffffff'
  },
  button: {
    padding: '8px 20px',
    fontSize: '14px',
    fontWeight: '500',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  primaryButton: {
    backgroundColor: '#2563eb',
    color: 'white'
  },
  secondaryButton: {
    color: '#4b5563',
    background: 'none'
  },
  errorBox: {
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '24px'
  },
  warningBox: {
    backgroundColor: '#fffbeb',
    border: '1px solid #fde68a',
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '16px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  }
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
    <div style={{
      marginTop: '12px',
      padding: '12px',
      backgroundColor: '#f9fafb',
      borderRadius: '8px'
    }}>
      <p style={{
        fontSize: '12px',
        fontWeight: '500',
        color: '#374151',
        marginBottom: '8px',
        margin: 0
      }}>
        Le mot de passe doit contenir :
      </p>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '4px',
        fontSize: '12px'
      }}>
        {requirements.map((req, index) => (
          <div
            key={index}
            style={{
              display: 'flex',
              alignItems: 'center',
              color: req.test ? '#059669' : '#9ca3af',
              gridColumn: index === requirements.length - 1 ? 'span 2' : 'auto'
            }}
          >
            <span style={{ marginRight: '4px' }}>
              {req.test ? '✅' : '⭕'}
            </span>
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
      <label style={{
        display: 'block',
        fontSize: '14px',
        fontWeight: '500',
        color: '#374151',
        marginBottom: '8px'
      }}>
        {label} {required && <span style={{ color: '#ef4444' }}>*</span>}
      </label>
      <div style={{ position: 'relative' }}>
        <input
          id={id}
          type={showPassword ? "text" : "password"}
          name={id}
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          required={required}
          style={{
            ...styles.input,
            paddingRight: '40px'
          }}
        />
        <button
          type="button"
          onClick={onToggleShow}
          style={{
            position: 'absolute',
            right: '12px',
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'none',
            border: 'none',
            color: '#9ca3af',
            cursor: 'pointer',
            padding: '4px'
          }}
        >
          {showPassword ? (
            <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 11-4.243-4.243m4.242 4.242L9.88 9.88" />
            </svg>
          ) : (
            <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
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
    <div style={styles.errorBox}>
      <div style={{ color: '#991b1b', fontSize: '14px' }}>
        <p style={{ fontWeight: '500', marginBottom: '8px', margin: 0 }}>{title} :</p>
        <ul style={{ listStyle: 'disc', paddingLeft: '20px', margin: 0 }}>
          {errors.map((error, index) => (
            <li key={index} style={{ marginBottom: '4px' }}>{error}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}

// Main component
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
    <div
      style={styles.overlay}
      onClick={handleClose}
    >
      <div
        style={styles.modal}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={styles.header}>
          <h2 style={{ 
            fontSize: '20px', 
            fontWeight: '600', 
            color: '#111827', 
            margin: 0 
          }}>
            {t('profile.title')}
          </h2>
          <button
            onClick={handleClose}
            style={styles.closeButton}
            disabled={isLoading}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = '#4b5563'
              e.currentTarget.style.backgroundColor = '#f3f4f6'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = '#9ca3af'
              e.currentTarget.style.backgroundColor = 'transparent'
            }}
          >
            ×
          </button>
        </div>

        {/* Tabs */}
        <div style={styles.tabsContainer}>
          <nav style={styles.tabsNav}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  ...styles.tab,
                  ...(activeTab === tab.id ? styles.activeTab : styles.inactiveTab),
                  borderBottomColor: activeTab === tab.id ? '#3b82f6' : 'transparent'
                }}
              >
                <span style={{ marginRight: '8px' }}>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div style={styles.content}>
          
          {/* Errors */}
          <ErrorDisplay errors={formErrors} title="Erreurs de validation" />

          {/* Fallback Warning */}
          {usingFallback && !countriesLoading && (
            <div style={styles.warningBox}>
              <svg style={{ width: '16px', height: '16px', color: '#d97706' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span style={{ fontSize: '14px', color: '#92400e' }}>
                Liste de pays limitée (service externe temporairement indisponible)
              </span>
            </div>
          )}

          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              {/* Personal Info */}
              <div>
                <h3 style={{ 
                  fontSize: '18px', 
                  fontWeight: '500', 
                  color: '#111827', 
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  margin: '0 0 16px 0'
                }}>
                  <span style={{ 
                    width: '8px', 
                    height: '8px', 
                    backgroundColor: '#ef4444', 
                    borderRadius: '50%', 
                    marginRight: '8px' 
                  }}></span>
                  {t('profile.personalInfo')}
                  <span style={{ color: '#ef4444', marginLeft: '4px' }}>*</span>
                </h3>
                
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
                  gap: '16px', 
                  marginBottom: '16px' 
                }}>
                  <div>
                    <label style={{ 
                      display: 'block', 
                      fontSize: '14px', 
                      fontWeight: '500', 
                      color: '#374151', 
                      marginBottom: '8px' 
                    }}>
                      {t('profile.firstName')} <span style={{ color: '#ef4444' }}>*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.firstName}
                      onChange={(e) => handleFormDataChange('firstName', e.target.value)}
                      style={styles.input}
                      required
                    />
                  </div>
                  
                  <div>
                    <label style={{ 
                      display: 'block', 
                      fontSize: '14px', 
                      fontWeight: '500', 
                      color: '#374151', 
                      marginBottom: '8px' 
                    }}>
                      {t('profile.lastName')} <span style={{ color: '#ef4444' }}>*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.lastName}
                      onChange={(e) => handleFormDataChange('lastName', e.target.value)}
                      style={styles.input}
                      required
                    />
                  </div>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{ 
                    display: 'block', 
                    fontSize: '14px', 
                    fontWeight: '500', 
                    color: '#374151', 
                    marginBottom: '8px' 
                  }}>
                    {t('profile.email')} <span style={{ color: '#ef4444' }}>*</span>
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleFormDataChange('email', e.target.value)}
                    style={styles.input}
                    required
                  />
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{ 
                    display: 'block', 
                    fontSize: '14px', 
                    fontWeight: '500', 
                    color: '#374151', 
                    marginBottom: '12px' 
                  }}>
                    {t('profile.phone')} <span style={{ fontSize: '14px', color: '#6b7280' }}>(optionnel)</span>
                  </label>
                  <PhoneInput
                    countryCode={formData.country_code}
                    areaCode={formData.area_code}
                    phoneNumber={formData.phone_number}
                    onChange={handlePhoneChange}
                  />
                </div>

                <div>
                  <label style={{ 
                    display: 'block', 
                    fontSize: '14px', 
                    fontWeight: '500', 
                    color: '#374151', 
                    marginBottom: '8px' 
                  }}>
                    {t('profile.country')} <span style={{ fontSize: '14px', color: '#6b7280' }}>(optionnel)</span>
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
                <h3 style={{ 
                  fontSize: '18px', 
                  fontWeight: '500', 
                  color: '#111827', 
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  margin: '0 0 16px 0'
                }}>
                  <span style={{ 
                    width: '8px', 
                    height: '8px', 
                    backgroundColor: '#3b82f6', 
                    borderRadius: '50%', 
                    marginRight: '8px' 
                  }}></span>
                  Informations Professionnelles
                  <span style={{ fontSize: '14px', color: '#6b7280', marginLeft: '8px' }}>(optionnel)</span>
                </h3>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div>
                    <label style={{ 
                      display: 'block', 
                      fontSize: '14px', 
                      fontWeight: '500', 
                      color: '#374151', 
                      marginBottom: '8px' 
                    }}>
                      Profil LinkedIn Personnel
                    </label>
                    <input
                      type="url"
                      value={formData.linkedinProfile}
                      onChange={(e) => handleFormDataChange('linkedinProfile', e.target.value)}
                      placeholder="https://linkedin.com/in/votre-profil"
                      style={styles.input}
                    />
                  </div>

                  <div>
                    <label style={{ 
                      display: 'block', 
                      fontSize: '14px', 
                      fontWeight: '500', 
                      color: '#374151', 
                      marginBottom: '8px' 
                    }}>
                      {t('profile.companyName')}
                    </label>
                    <input
                      type="text"
                      value={formData.companyName}
                      onChange={(e) => handleFormDataChange('companyName', e.target.value)}
                      placeholder="Nom de votre entreprise ou exploitation"
                      style={styles.input}
                    />
                  </div>

                  <div>
                    <label style={{ 
                      display: 'block', 
                      fontSize: '14px', 
                      fontWeight: '500', 
                      color: '#374151', 
                      marginBottom: '8px' 
                    }}>
                      {t('profile.companyWebsite')}
                    </label>
                    <input
                      type="url"
                      value={formData.companyWebsite}
                      onChange={(e) => handleFormDataChange('companyWebsite', e.target.value)}
                      placeholder="https://www.votre-entreprise.com"
                      style={styles.input}
                    />
                  </div>

                  <div>
                    <label style={{ 
                      display: 'block', 
                      fontSize: '14px', 
                      fontWeight: '500', 
                      color: '#374151', 
                      marginBottom: '8px' 
                    }}>
                      Page LinkedIn Entreprise
                    </label>
                    <input
                      type="url"
                      value={formData.linkedinCorporate}
                      onChange={(e) => handleFormDataChange('linkedinCorporate', e.target.value)}
                      placeholder="https://linkedin.com/company/votre-entreprise"
                      style={styles.input}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Password Tab */}
          {activeTab === 'password' && (
            <div>
              <h3 style={{ 
                fontSize: '18px', 
                fontWeight: '500', 
                color: '#111827', 
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'center',
                margin: '0 0 16px 0'
              }}>
                <span style={{ 
                  width: '8px', 
                  height: '8px', 
                  backgroundColor: '#f59e0b', 
                  borderRadius: '50%', 
                  marginRight: '8px' 
                }}></span>
                {t('profile.password')}
              </h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
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
              
              <div style={{ marginTop: '16px' }}>
                <ErrorDisplay errors={passwordErrors} title="Erreurs" />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          <button
            onClick={handleClose}
            style={{ ...styles.button, ...styles.secondaryButton }}
            disabled={isLoading}
            onMouseEnter={(e) => {
              if (!isLoading) {
                e.currentTarget.style.color = '#1f2937'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = '#4b5563'
            }}
          >
            Annuler
          </button>
          <button
            onClick={activeTab === 'profile' ? handleProfileSave : handlePasswordChange}
            disabled={isLoading}
            style={{
              ...styles.button,
              ...styles.primaryButton,
              backgroundColor: isLoading ? '#9ca3af' : '#2563eb',
              cursor: isLoading ? 'not-allowed' : 'pointer'
            }}
            onMouseEnter={(e) => {
              if (!isLoading) {
                e.currentTarget.style.backgroundColor = '#1d4ed8'
              }
            }}
            onMouseLeave={(e) => {
              if (!isLoading) {
                e.currentTarget.style.backgroundColor = '#2563eb'
              }
            }}
          >
            {isLoading && (
              <div style={{
                width: '16px',
                height: '16px',
                border: '2px solid white',
                borderTopColor: 'transparent',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }}></div>
            )}
            {isLoading ? 'Chargement...' : 'Sauvegarder'}
          </button>
        </div>
      </div>

      <style jsx>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}