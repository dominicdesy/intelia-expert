// UserInfoModal.tsx - STRUCTURE SIMPLIFIÉE AVEC NOUVELLES CLASSES CSS

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

// Hook sécurisé useCountries avec protection complète
const useCountries = () => {
  const [countries, setCountries] = useState<Country[]>(fallbackCountries)
  const [loading, setLoading] = useState(false)
  const [usingFallback, setUsingFallback] = useState(true)
  const isMountedRef = useRef(true)

  useEffect(() => {
    isMountedRef.current = true
    let isCancelled = false
    
    const fetchCountries = async () => {
      if (!isMountedRef.current || isCancelled) return
      
      try {
        if (isMountedRef.current && !isCancelled) {
          setLoading(true)
        }
        
        const response = await fetch('https://restcountries.com/v3.1/all?fields=cca2,name,idd,flag,translations')
        
        if (!response.ok || isCancelled || !isMountedRef.current) return
        
        const data = await response.json()
        
        if (isCancelled || !isMountedRef.current) return
        
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
        
        if (formattedCountries.length >= 50 && !isCancelled && isMountedRef.current) {
          setCountries(formattedCountries)
          setUsingFallback(false)
        }
        
      } catch (err) {
        if (!isCancelled && isMountedRef.current) {
          console.warn('[UserInfoModal] API échouée, utilisation fallback:', err)
        }
      } finally {
        if (!isCancelled && isMountedRef.current) {
          setLoading(false)
        }
      }
    }

    fetchCountries()
    
    return () => {
      isCancelled = true
      isMountedRef.current = false
    }
  }, [])

  return { countries, loading, usingFallback }
}

export const UserInfoModal = ({ user, onClose }: UserInfoModalProps) => {
  // Protection render conditionnel
  if (!user) {
    console.log('[DEBUG-UserInfoModal] Pas d\'utilisateur - pas de render')
    return null
  }

  console.log('[DEBUG-UserInfoModal] Montage du modal')
  
  const { updateProfile } = useAuthStore()
  const { t } = useTranslation()
  const { validatePhoneFields } = usePhoneValidation()
  
  // Protection contre setState après unmount - AVANT tous les states
  const isMountedRef = useRef(true)
  
  // States avec valeurs initiales stables
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('profile')
  const [formErrors, setFormErrors] = useState<string[]>([])
  const [passwordErrors, setPasswordErrors] = useState<string[]>([])
  
  // Mémorisation des données user pour éviter re-calculs constants
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

  // FormData initialisé une seule fois
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

  const { countries, loading: countriesLoading, usingFallback } = useCountries()

  // Setup/Cleanup cycle - UNE SEULE FOIS
  useEffect(() => {
    console.log('[DEBUG-UserInfoModal] Composant monté - initialisation formData')
    setFormData(userDataMemo)
  }, []) // AUCUNE dependency pour éviter la boucle

  // Sync formData intelligent - évite la boucle infinie
  useEffect(() => {
    const needsSync = (
      formData.firstName !== userDataMemo.firstName ||
      formData.lastName !== userDataMemo.lastName ||
      formData.email !== userDataMemo.email ||
      formData.country_code !== userDataMemo.country_code ||
      formData.area_code !== userDataMemo.area_code ||
      formData.phone_number !== userDataMemo.phone_number ||
      formData.country !== userDataMemo.country ||
      formData.linkedinProfile !== userDataMemo.linkedinProfile ||
      formData.companyName !== userDataMemo.companyName ||
      formData.companyWebsite !== userDataMemo.companyWebsite ||
      formData.linkedinCorporate !== userDataMemo.linkedinCorporate
    )
    
    if (isMountedRef.current && needsSync) {
      console.log('[DEBUG-UserInfoModal] Sync nécessaire - mise à jour formData')
      setFormData(userDataMemo)
    }
  }, [userDataMemo])

  // setState protégé
  const safeSetState = useCallback((stateFn: () => void, debugLabel: string) => {
    if (isMountedRef.current) {
      console.log(`[DEBUG-UserInfoModal] setState ${debugLabel} - isMounted: true`)
      stateFn()
    } else {
      console.log(`[DEBUG-UserInfoModal] setState ${debugLabel} BLOQUÉ - composant démonté`)
    }
  }, [])

  // Safe close optimisé
  const safeClose = useCallback(() => {
    console.log('[DEBUG-UserInfoModal] safeClose - isMounted:', isMountedRef.current, 'isLoading:', isLoading)
    
    if (isMountedRef.current && !isLoading) {
      setFormErrors([])
      setPasswordErrors([])
      onClose()
    } else if (isLoading) {
      console.log('[DEBUG-UserInfoModal] safeClose ignoré - operation en cours')
    }
  }, [isLoading, onClose])

  // Validation password
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

  // Handler téléphone
  const handlePhoneChange = useCallback((phoneData: { country_code: string; area_code: string; phone_number: string }) => {
    safeSetState(() => {
      setFormData(prev => ({
        ...prev,
        country_code: phoneData.country_code,
        area_code: phoneData.area_code,
        phone_number: phoneData.phone_number
      }))
    }, 'handlePhoneChange')
  }, [safeSetState])

  // Handle profile save
  const handleProfileSave = useCallback(async () => {
    console.log('[DEBUG-UserInfoModal] handleProfileSave - isMounted:', isMountedRef.current, 'isLoading:', isLoading)
    
    if (!isMountedRef.current || isLoading) {
      console.log('[DEBUG-UserInfoModal] handleProfileSave BLOQUÉ - démonté ou en cours')
      return
    }
    
    safeSetState(() => setIsLoading(true), 'setIsLoading(true)')
    safeSetState(() => setFormErrors([]), 'setFormErrors([])')
    
    try {
      const errors: string[] = []
      
      if (!formData.firstName.trim()) {
        errors.push('Le prénom est requis')
      }
      if (!formData.lastName.trim()) {
        errors.push('Le nom est requis')
      }
      if (!formData.email.trim()) {
        errors.push('L\'email est requis')
      }
      
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
      
      if (errors.length > 0) {
        safeSetState(() => setFormErrors(errors), 'setFormErrors(errors)')
        return
      }

      console.log('[DEBUG-UserInfoModal] Appel updateProfile...')
      
      if (!isMountedRef.current) {
        console.log('[DEBUG-UserInfoModal] Composant démonté avant updateProfile - abandon')
        return
      }
      
      await updateProfile(formData)
      
      if (!isMountedRef.current) {
        console.log('[DEBUG-UserInfoModal] Composant démonté pendant updateProfile - pas de UI update')
        return
      }
      
      console.log('[DEBUG-UserInfoModal] updateProfile réussi')
      
      alert(t('profile.title') + ' mis à jour avec succès!')
      safeClose()
      
    } catch (error: any) {
      console.error('[DEBUG-UserInfoModal] Erreur mise à jour profil:', error)
      
      if (isMountedRef.current) {
        alert('Erreur lors de la mise à jour: ' + (error?.message || 'Erreur inconnue'))
      }
    } finally {
      if (isMountedRef.current) {
        safeSetState(() => setIsLoading(false), 'setIsLoading(false) final')
      }
    }
  }, [formData, validatePhoneFields, updateProfile, t, safeClose, isLoading, safeSetState])

  // Handle password change avec protections
  const handlePasswordChange = useCallback(async () => {
    console.log('[DEBUG-UserInfoModal] handlePasswordChange - isMounted:', isMountedRef.current, 'isLoading:', isLoading)
    
    if (!isMountedRef.current || isLoading) {
      console.log('[DEBUG-UserInfoModal] handlePasswordChange BLOQUÉ - démonté ou en cours')
      return
    }
    
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
    
    safeSetState(() => setPasswordErrors(errors), 'setPasswordErrors')
    
    if (errors.length > 0) {
      return
    }

    safeSetState(() => setIsLoading(true), 'setIsLoading(true) password')
    
    try {
      if (!isMountedRef.current) {
        return
      }
      
      console.log('[DEBUG-UserInfoModal] Vérification mot de passe actuel...')
      
      const loginResponse = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: user?.email,
          password: passwordData.currentPassword
        })
      })

      if (!loginResponse.ok) {
        if (isMountedRef.current) {
          safeSetState(() => setPasswordErrors(['Le mot de passe actuel est incorrect']), 'setPasswordErrors login fail')
        }
        return
      }

      const loginData = await loginResponse.json()
      const backendToken = loginData.access_token

      if (!isMountedRef.current) {
        return
      }

      console.log('[DEBUG-UserInfoModal] Changement mot de passe...')
      
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
        if (isMountedRef.current) {
          safeSetState(() => setPasswordErrors([result?.detail || result?.message || 'Erreur lors du changement de mot de passe']), 'setPasswordErrors change fail')
        }
        return
      }
      
      if (!isMountedRef.current) {
        return
      }
      
      console.log('[DEBUG-UserInfoModal] Mot de passe changé avec succès')
      
      safeSetState(() => {
        setPasswordData({
          currentPassword: '',
          newPassword: '',
          confirmPassword: ''
        })
        setPasswordErrors([])
      }, 'reset password data')
      
      alert('Mot de passe changé avec succès!')
      safeClose()
      
    } catch (error: any) {
      console.error('[DEBUG-UserInfoModal] Erreur technique:', error)
      
      if (isMountedRef.current) {
        safeSetState(() => setPasswordErrors(['Erreur de connexion au serveur. Veuillez réessayer.']), 'setPasswordErrors catch')
      }
    } finally {
      if (isMountedRef.current) {
        safeSetState(() => setIsLoading(false), 'setIsLoading(false) password final')
      }
    }
  }, [passwordData, validatePassword, user?.email, safeClose, isLoading, safeSetState])

  // Tabs configuration
  const tabs = useMemo(() => [
    { id: 'profile', label: t('nav.profile'), icon: '👤' },
    { id: 'password', label: t('profile.password'), icon: '🔐' }
  ], [t])

  // Handler avec protection pour les changements d'onglets
  const handleTabChange = useCallback((tabId: string) => {
    safeSetState(() => setActiveTab(tabId), 'setActiveTab')
  }, [safeSetState])

  // Handlers de formulaire protégés
  const handleFormDataChange = useCallback((field: string, value: any) => {
    safeSetState(() => {
      setFormData(prev => ({ ...prev, [field]: value }))
    }, `setFormData ${field}`)
  }, [safeSetState])

  const handlePasswordDataChange = useCallback((field: string, value: string) => {
    safeSetState(() => {
      setPasswordData(prev => ({ ...prev, [field]: value }))
    }, `setPasswordData ${field}`)
  }, [safeSetState])

  const handleShowPasswordToggle = useCallback((field: string) => {
    safeSetState(() => {
      setShowPasswords(prev => ({ ...prev, [field]: !prev[field as keyof typeof prev] }))
    }, `toggle show password ${field}`)
  }, [safeSetState])

  console.log('[DEBUG-UserInfoModal] Render - isMounted:', isMountedRef.current, 'isLoading:', isLoading)

  return (
    <div 
      onClick={safeClose}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
        backgroundColor: 'rgba(0, 0, 0, 0.5)'
      }}
    >
      <div 
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: '42rem',
          maxHeight: '85vh',
          background: 'white',
          borderRadius: '0.75rem',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        
        {/* Header */}
        <div style={{ 
          padding: '1.5rem', 
          borderBottom: '1px solid #e5e7eb', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          flexShrink: 0
        }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#111827', margin: 0 }}>
            {t('profile.title')}
          </h2>
          <button
            onClick={safeClose}
            disabled={isLoading}
            style={{
              color: '#9ca3af',
              fontSize: '1.5rem',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '0.5rem',
              borderRadius: '0.5rem',
              transition: 'all 0.2s'
            }}
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
        <div style={{ borderBottom: '1px solid #e5e7eb' }}>
          <nav style={{ display: 'flex', padding: '0 1.5rem' }}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                style={{
                  padding: '0.75rem 1rem',
                  borderBottom: activeTab === tab.id ? '2px solid #3b82f6' : '2px solid transparent',
                  color: activeTab === tab.id ? '#2563eb' : '#6b7280',
                  fontWeight: '500',
                  fontSize: '0.875rem',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <span style={{ marginRight: '0.5rem' }}>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content Container */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
          
          {/* Error Messages */}
          {formErrors.length > 0 && (
            <div style={{
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '0.5rem',
              padding: '1rem',
              marginBottom: '1.5rem'
            }}>
              <div style={{ color: '#991b1b', fontSize: '0.875rem' }}>
                <p style={{ fontWeight: '500', marginBottom: '0.5rem', margin: 0 }}>Erreurs de validation :</p>
                <ul style={{ listStyle: 'disc', paddingLeft: '1.25rem', margin: 0 }}>
                  {formErrors.map((error, index) => (
                    <li key={index} style={{ marginBottom: '0.25rem' }}>{error}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Fallback Warning */}
          {usingFallback && !countriesLoading && (
            <div style={{
              backgroundColor: '#fffbeb',
              border: '1px solid #fde68a',
              borderRadius: '0.5rem',
              padding: '0.75rem',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <svg style={{ width: '1rem', height: '1rem', color: '#d97706' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span style={{ fontSize: '0.875rem', color: '#92400e' }}>
                Liste de pays limitée (service externe temporairement indisponible)
              </span>
            </div>
          )}

          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              
              {/* Personal Info Section */}
              <div>
                <h3 style={{ 
                  fontSize: '1.125rem', 
                  fontWeight: '500', 
                  color: '#111827', 
                  marginBottom: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  margin: '0 0 1rem 0'
                }}>
                  <span style={{ 
                    width: '0.5rem', 
                    height: '0.5rem', 
                    backgroundColor: '#ef4444', 
                    borderRadius: '50%', 
                    marginRight: '0.5rem' 
                  }}></span>
                  {t('profile.personalInfo')}
                  <span style={{ color: '#ef4444', marginLeft: '0.25rem' }}>*</span>
                </h3>
                
                {/* Name Fields Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>
                      {t('profile.firstName')} <span style={{ color: '#ef4444' }}>*</span>
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
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>
                      {t('profile.lastName')} <span style={{ color: '#ef4444' }}>*</span>
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

                {/* Email Field */}
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>
                    {t('profile.email')} <span style={{ color: '#ef4444' }}>*</span>
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleFormDataChange('email', e.target.value)}
                    className="input-primary"
                    required
                  />
                </div>

                {/* Phone Field */}
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.75rem' }}>
                    {t('profile.phone')} <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>(optionnel)</span>
                  </label>
                  <PhoneInput
                    countryCode={formData.country_code}
                    areaCode={formData.area_code}
                    phoneNumber={formData.phone_number}
                    onChange={handlePhoneChange}
                  />
                </div>

                {/* Country Field */}
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>
                    {t('profile.country')} <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>(optionnel)</span>
                  </label>
                  <CountrySelect
                    countries={countries}
                    value={formData.country}
                    onChange={(countryValue: string) => handleFormDataChange('country', countryValue)}
                    placeholder="Sélectionner un pays ou rechercher..."
                  />
                </div>
              </div>

              {/* Professional Info Section */}
              <div>
                <h3 style={{ 
                  fontSize: '1.125rem', 
                  fontWeight: '500', 
                  color: '#111827', 
                  marginBottom: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  margin: '0 0 1rem 0'
                }}>
                  <span style={{ 
                    width: '0.5rem', 
                    height: '0.5rem', 
                    backgroundColor: '#3b82f6', 
                    borderRadius: '50%', 
                    marginRight: '0.5rem' 
                  }}></span>
                  Informations Professionnelles
                  <span style={{ fontSize: '0.875rem', color: '#6b7280', marginLeft: '0.5rem' }}>(optionnel)</span>
                </h3>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>
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
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>
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
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>
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
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>
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
            <div>
              <h3 style={{ 
                fontSize: '1.125rem', 
                fontWeight: '500', 
                color: '#111827', 
                marginBottom: '1rem',
                display: 'flex',
                alignItems: 'center',
                margin: '0 0 1rem 0'
              }}>
                <span style={{ 
                  width: '0.5rem', 
                  height: '0.5rem', 
                  backgroundColor: '#f59e0b', 
                  borderRadius: '50%', 
                  marginRight: '0.5rem' 
                }}></span>
                {t('profile.password')}
              </h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                
                {/* Current Password */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>
                    {t('profile.currentPassword')} <span style={{ color: '#ef4444' }}>*</span>
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showPasswords.currentPassword ? "text" : "password"}
                      name="currentPassword"
                      autoComplete="current-password"
                      value={passwordData.currentPassword}
                      onChange={(e) => handlePasswordDataChange('currentPassword', e.target.value)}
                      className="input-primary"
                      placeholder="Tapez votre mot de passe actuel"
                      required
                      style={{ paddingRight: '2.5rem' }}
                    />
                    <button
                      type="button"
                      onClick={() => handleShowPasswordToggle('currentPassword')}
                      style={{
                        position: 'absolute',
                        right: '0.75rem',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        background: 'none',
                        border: 'none',
                        color: '#9ca3af',
                        cursor: 'pointer',
                        padding: '0.25rem'
                      }}
                    >
                      {showPasswords.currentPassword ? (
                        <svg style={{ width: '1.25rem', height: '1.25rem' }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 11-4.243-4.243m4.242 4.242L9.88 9.88" />
                        </svg>
                      ) : (
                        <svg style={{ width: '1.25rem', height: '1.25rem' }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>
                
                {/* New Password */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>
                    {t('profile.newPassword')} <span style={{ color: '#ef4444' }}>*</span>
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showPasswords.newPassword ? "text" : "password"}
                      name="newPassword"
                      autoComplete="new-password"
                      value={passwordData.newPassword}
                      onChange={(e) => handlePasswordDataChange('newPassword', e.target.value)}
                      className="input-primary"
                      placeholder="Tapez votre nouveau mot de passe"
                      required
                      style={{ paddingRight: '2.5rem' }}
                    />
                    <button
                      type="button"
                      onClick={() => handleShowPasswordToggle('newPassword')}
                      style={{
                        position: 'absolute',
                        right: '0.75rem',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        background: 'none',
                        border: 'none',
                        color: '#9ca3af',
                        cursor: 'pointer',
                        padding: '0.25rem'
                      }}
                    >
                      {showPasswords.newPassword ? (
                        <svg style={{ width: '1.25rem', height: '1.25rem' }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 11-4.243-4.243m4.242 4.242L9.88 9.88" />
                        </svg>
                      ) : (
                        <svg style={{ width: '1.25rem', height: '1.25rem' }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                      )}
                    </button>
                  </div>
                  
                  {/* Password Requirements */}
                  <div style={{ 
                    marginTop: '0.75rem', 
                    padding: '0.75rem', 
                    backgroundColor: '#f9fafb', 
                    borderRadius: '0.5rem' 
                  }}>
                    <p style={{ fontSize: '0.75rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem', margin: 0 }}>
                      Le mot de passe doit contenir :
                    </p>
                    <div style={{ 
                      display: 'grid', 
                      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', 
                      gap: '0.25rem', 
                      fontSize: '0.75rem' 
                    }}>
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        color: passwordData.newPassword.length >= 8 ? '#059669' : '#9ca3af' 
                      }}>
                        <span style={{ marginRight: '0.25rem' }}>
                          {passwordData.newPassword.length >= 8 ? '✅' : '⭕'}
                        </span>
                        8+ caractères
                      </div>
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        color: /[A-Z]/.test(passwordData.newPassword) ? '#059669' : '#9ca3af' 
                      }}>
                        <span style={{ marginRight: '0.25rem' }}>
                          {/[A-Z]/.test(passwordData.newPassword) ? '✅' : '⭕'}
                        </span>
                        Une majuscule
                      </div>
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        color: /[a-z]/.test(passwordData.newPassword) ? '#059669' : '#9ca3af' 
                      }}>
                        <span style={{ marginRight: '0.25rem' }}>
                          {/[a-z]/.test(passwordData.newPassword) ? '✅' : '⭕'}
                        </span>
                        Une minuscule
                      </div>
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        color: /\d/.test(passwordData.newPassword) ? '#059669' : '#9ca3af' 
                      }}>
                        <span style={{ marginRight: '0.25rem' }}>
                          {/\d/.test(passwordData.newPassword) ? '✅' : '⭕'}
                        </span>
                        Un chiffre
                      </div>
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        color: /[!@#$%^&*(),.?":{}|<>]/.test(passwordData.newPassword) ? '#059669' : '#9ca3af',
                        gridColumn: 'span 2'
                      }}>
                        <span style={{ marginRight: '0.25rem' }}>
                          {/[!@#$%^&*(),.?":{}|<>]/.test(passwordData.newPassword) ? '✅' : '⭕'}
                        </span>
                        Un caractère spécial (!@#$%^&*...)
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Confirm Password */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>
                    {t('profile.confirmPassword')} <span style={{ color: '#ef4444' }}>*</span>
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showPasswords.confirmPassword ? "text" : "password"}
                      name="confirmPassword"
                      autoComplete="new-password"
                      value={passwordData.confirmPassword}
                      onChange={(e) => handlePasswordDataChange('confirmPassword', e.target.value)}
                      className="input-primary"
                      placeholder="Confirmez votre nouveau mot de passe"
                      required
                      style={{ paddingRight: '2.5rem' }}
                    />
                    <button
                      type="button"
                      onClick={() => handleShowPasswordToggle('confirmPassword')}
                      style={{
                        position: 'absolute',
                        right: '0.75rem',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        background: 'none',
                        border: 'none',
                        color: '#9ca3af',
                        cursor: 'pointer',
                        padding: '0.25rem'
                      }}
                    >
                      {showPasswords.confirmPassword ? (
                        <svg style={{ width: '1.25rem', height: '1.25rem' }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 11-4.243-4.243m4.242 4.242L9.88 9.88" />
                        </svg>
                      ) : (
                        <svg style={{ width: '1.25rem', height: '1.25rem' }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>
                
                {/* Password Error Messages */}
                {passwordErrors.length > 0 && (
                  <div style={{
                    backgroundColor: '#fef2f2',
                    border: '1px solid #fecaca',
                    borderRadius: '0.5rem',
                    padding: '1rem'
                  }}>
                    <div style={{ color: '#991b1b', fontSize: '0.875rem' }}>
                      <p style={{ fontWeight: '500', marginBottom: '0.5rem', margin: 0 }}>Erreurs :</p>
                      <ul style={{ listStyle: 'disc', paddingLeft: '1.25rem', margin: 0 }}>
                        {passwordErrors.map((error, index) => (
                          <li key={index} style={{ marginBottom: '0.25rem' }}>{error}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ 
          padding: '1.5rem', 
          borderTop: '1px solid #e5e7eb', 
          backgroundColor: '#f9fafb',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '0.75rem',
          flexShrink: 0
        }}>
          <button
            onClick={safeClose}
            disabled={isLoading}
            style={{
              padding: '0.5rem 1.25rem',
              color: '#4b5563',
              fontWeight: '500',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              borderRadius: '0.375rem',
              transition: 'all 0.2s'
            }}
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
              padding: '0.5rem 1.25rem',
              backgroundColor: isLoading ? '#9ca3af' : '#2563eb',
              color: 'white',
              fontWeight: '500',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
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
              <div className="spinner" style={{
                width: '1rem',
                height: '1rem',
                borderColor: 'white',
                borderTopColor: 'transparent'
              }}></div>
            )}
            {isLoading ? 'Chargement...' : 'Sauvegarder'}
          </button>
        </div>
      </div>
    </div>
  )
}