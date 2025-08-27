// UserInfoModal.tsx - VERSION CORRIGÉE REACT #300

import React, { useState, useEffect, useMemo, useCallback } from 'react'
import { useAuthStore, markStoreUnmounted, markStoreMounted } from '@/lib/stores/auth'
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

// HOOK SÉCURISÉ useCountries avec protection complète
const useCountries = () => {
  const [countries, setCountries] = useState<Country[]>(fallbackCountries)
  const [loading, setLoading] = useState(false)
  const [usingFallback, setUsingFallback] = useState(true)
  
  // PROTECTION CRITIQUE: Protection contre setState après unmount
  const isMountedRef = React.useRef(true)

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
          console.warn('🌍 [UserInfoModal] API échouée, utilisation fallback:', err)
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
  console.log('🏗️ [DEBUG-UserInfoModal] Montage du modal')
  
  const { updateProfile } = useAuthStore()
  const { t } = useTranslation()
  const { validatePhoneFields } = usePhoneValidation()
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('profile')
  
  const { countries, loading: countriesLoading, usingFallback } = useCountries()
  
  // CORRECTION CRITIQUE #1: Protection complète contre setState après unmount
  const isMountedRef = React.useRef(true)
  
  // CORRECTION CRITIQUE #2: Contrôle du store auth
  React.useEffect(() => {
    isMountedRef.current = true
    markStoreMounted()
    console.log('✅ [DEBUG-UserInfoModal] Composant monté - store marqué comme actif')
    
    return () => {
      console.log('🧹 [DEBUG-UserInfoModal] Composant en cours de démontage')
      isMountedRef.current = false
      markStoreUnmounted()
      console.log('🛑 [DEBUG-UserInfoModal] Store marqué comme inactif - TOUS les setState bloqués')
    }
  }, [])

  // Initialiser une seule fois avec useMemo
  const initialFormData = useMemo(() => ({
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
  }), [user])

  const [formData, setFormData] = useState(initialFormData)

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

  const [passwordErrors, setPasswordErrors] = useState<string[]>([])
  const [formErrors, setFormErrors] = useState<string[]>([])

  // CORRECTION CRITIQUE #3: Sync form data avec protection
  React.useEffect(() => {
    console.log('🔄 [DEBUG-UserInfoModal] Sync formData - isMounted:', isMountedRef.current)
    
    if (isMountedRef.current) {
      setFormData(initialFormData)
    }
  }, [initialFormData])
  
  // CORRECTION CRITIQUE #4: Safe close avec protection loading
  const safeClose = useCallback(() => {
    console.log('❌ [DEBUG-UserInfoModal] safeClose - isMounted:', isMountedRef.current, 'isLoading:', isLoading)
    
    if (!isLoading && isMountedRef.current) {
      onClose()
    }
  }, [isLoading, onClose])

  // CORRECTION CRITIQUE #5: Toutes les fonctions setState protégées
  const safeSetState = useCallback((updater: any, stateName: string) => {
    if (!isMountedRef.current) {
      console.log(`⚠️ [DEBUG-UserInfoModal] setState ${stateName} ignoré - composant démonté`)
      return
    }
    
    console.log(`🔄 [DEBUG-UserInfoModal] setState ${stateName} - isMounted: true`)
    updater()
  }, [])

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

  // CORRECTION CRITIQUE #6: handleProfileSave avec protections renforcées
  const handleProfileSave = useCallback(async () => {
    console.log('💾 [DEBUG-UserInfoModal] handleProfileSave - isMounted:', isMountedRef.current, 'isLoading:', isLoading)
    
    // PROTECTION: Early return si déjà en cours ou démonté
    if (!isMountedRef.current || isLoading) {
      console.log('⚠️ [DEBUG-UserInfoModal] handleProfileSave abandonné - démonté ou en cours')
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
      
      // Validation téléphone uniquement si au moins un champ rempli
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

      console.log('🔄 [DEBUG-UserInfoModal] Appel updateProfile...')
      
      // PROTECTION: Vérification avant l'appel async
      if (!isMountedRef.current) {
        console.log('⚠️ [DEBUG-UserInfoModal] Composant démonté avant updateProfile - abandon')
        return
      }
      
      await updateProfile(formData)
      
      // PROTECTION: Vérification APRÈS l'appel async
      if (!isMountedRef.current) {
        console.log('⚠️ [DEBUG-UserInfoModal] Composant démonté pendant updateProfile - pas de UI update')
        return
      }
      
      console.log('✅ [DEBUG-UserInfoModal] updateProfile réussi')
      // Montrer alert avant fermeture
      alert(t('profile.title') + ' mis à jour avec succès!')
      safeClose()
      
    } catch (error: any) {
      console.error('❌ [DEBUG-UserInfoModal] Erreur mise à jour profil:', error)
      
      // PROTECTION: Vérifier avant alert
      if (isMountedRef.current) {
        alert('Erreur lors de la mise à jour: ' + (error?.message || 'Erreur inconnue'))
      }
    } finally {
      // PROTECTION: Double protection setState final
      if (isMountedRef.current) {
        safeSetState(() => setIsLoading(false), 'setIsLoading(false) final')
      } else {
        console.log('⚠️ [DEBUG-UserInfoModal] setState setIsLoading(false) final ignoré - composant démonté')
      }
    }
  }, [formData, validatePhoneFields, updateProfile, t, safeClose, isLoading, safeSetState])

  // CORRECTION CRITIQUE #7: handlePasswordChange avec protections renforcées
  const handlePasswordChange = useCallback(async () => {
    console.log('🔐 [DEBUG-UserInfoModal] handlePasswordChange - isMounted:', isMountedRef.current, 'isLoading:', isLoading)
    
    // PROTECTION: Early return si déjà en cours ou démonté
    if (!isMountedRef.current || isLoading) {
      console.log('⚠️ [DEBUG-UserInfoModal] handlePasswordChange abandonné')
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
      // PROTECTION: Vérification avant operations async
      if (!isMountedRef.current) {
        console.log('⚠️ [DEBUG-UserInfoModal] Composant démonté avant password change - abandon')
        return
      }
      
      console.log('🔄 [DEBUG-UserInfoModal] Vérification mot de passe actuel...')
      
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
        let loginError: any = null
        try {
          loginError = await loginResponse.json()
        } catch {}
        
        if (isMountedRef.current) {
          safeSetState(() => setPasswordErrors(['Le mot de passe actuel est incorrect']), 'setPasswordErrors login fail')
        }
        return
      }

      const loginData = await loginResponse.json()
      const backendToken = loginData.access_token

      // PROTECTION: Vérification après première async operation
      if (!isMountedRef.current) {
        console.log('⚠️ [DEBUG-UserInfoModal] Composant démonté après login check')
        return
      }

      console.log('🔄 [DEBUG-UserInfoModal] Changement mot de passe...')
      
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
      
      // PROTECTION: Vérification finale avant UI updates
      if (!isMountedRef.current) {
        console.log('⚠️ [DEBUG-UserInfoModal] Composant démonté après password change')
        return
      }
      
      console.log('✅ [DEBUG-UserInfoModal] Mot de passe changé avec succès')
      
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
      console.error('❌ [DEBUG-UserInfoModal] Erreur technique:', error)
      
      if (isMountedRef.current) {
        safeSetState(() => setPasswordErrors(['Erreur de connexion au serveur. Veuillez réessayer.']), 'setPasswordErrors catch')
      }
    } finally {
      // PROTECTION: Double protection setState final
      if (isMountedRef.current) {
        safeSetState(() => setIsLoading(false), 'setIsLoading(false) password final')
      } else {
        console.log('⚠️ [DEBUG-UserInfoModal] setState setIsLoading(false) password final ignoré - composant démonté')
      }
    }
  }, [passwordData, validatePassword, user?.email, safeClose, isLoading, safeSetState])

  const tabs = useMemo(() => [
    { id: 'profile', label: t('nav.profile'), icon: '👤' },
    { id: 'password', label: t('profile.password'), icon: '🔐' }
  ], [t])

  // PROTECTION: Handler avec protection pour les changements d'onglets
  const handleTabChange = useCallback((tabId: string) => {
    safeSetState(() => setActiveTab(tabId), 'setActiveTab')
  }, [safeSetState])

  // PROTECTION: Handlers de formulaire protégés
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

  console.log('🔄 [DEBUG-UserInfoModal] Render - isMounted:', isMountedRef.current, 'isLoading:', isLoading)

  return (
    <>
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-50" 
        onClick={safeClose}
      />
      
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div 
          className="bg-white rounded-xl shadow-2xl w-full max-w-2xl h-[85vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between p-6 border-b border-gray-200 flex-shrink-0">
            <h2 className="text-xl font-semibold text-gray-900">
              {t('profile.title')}
            </h2>
            <button
              onClick={safeClose}
              className="text-gray-400 hover:text-gray-600 text-2xl font-light w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors"
              disabled={isLoading}
            >
              ×
            </button>
          </div>

          <div className="border-b border-gray-200 flex-shrink-0">
            <nav className="flex px-6">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
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

          <div className="flex-1 overflow-y-auto">
            <div className="p-6 space-y-6">
              {formErrors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="text-sm text-red-800">
                    <p className="font-medium mb-2">Erreurs de validation :</p>
                    <ul className="list-disc list-inside space-y-1">
                      {formErrors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {usingFallback && !countriesLoading && (
                <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
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

              {activeTab === 'profile' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                      <span className="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                      {t('profile.personalInfo')}
                      <span className="text-red-500 ml-1">*</span>
                    </h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

                    <div className="mt-4">
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

                    <div className="mt-4">
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

                    <div className="mt-4">
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

              {activeTab === 'password' && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                    <span className="w-2 h-2 bg-orange-500 rounded-full mr-2"></span>
                    {t('profile.password')}
                  </h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.currentPassword')} <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type={showPasswords.currentPassword ? "text" : "password"}
                          name="currentPassword"
                          autoComplete="current-password"
                          value={passwordData.currentPassword}
                          onChange={(e) => handlePasswordDataChange('currentPassword', e.target.value)}
                          className="input-primary pr-10"
                          placeholder="Tapez votre mot de passe actuel"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => handleShowPasswordToggle('currentPassword')}
                          className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                        >
                          {showPasswords.currentPassword ? (
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
                      <div className="text-xs text-gray-500 mt-1">
                        Caractères tapés: {passwordData.currentPassword.length}
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.newPassword')} <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type={showPasswords.newPassword ? "text" : "password"}
                          name="newPassword"
                          autoComplete="new-password"
                          value={passwordData.newPassword}
                          onChange={(e) => handlePasswordDataChange('newPassword', e.target.value)}
                          className="input-primary pr-10"
                          placeholder="Tapez votre nouveau mot de passe"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => handleShowPasswordToggle('newPassword')}
                          className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                        >
                          {showPasswords.newPassword ? (
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
                      <div className="text-xs text-gray-500 mt-1">
                        Caractères tapés: {passwordData.newPassword.length}
                      </div>
                      <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs font-medium text-gray-700 mb-2">Le mot de passe doit contenir :</p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-xs">
                          <div className={`flex items-center ${passwordData.newPassword.length >= 8 ? 'text-green-600' : 'text-gray-400'}`}>
                            <span className="mr-1">{passwordData.newPassword.length >= 8 ? '✅' : '⭕'}</span>
                            8+ caractères
                          </div>
                          <div className={`flex items-center ${/[A-Z]/.test(passwordData.newPassword) ? 'text-green-600' : 'text-gray-400'}`}>
                            <span className="mr-1">{/[A-Z]/.test(passwordData.newPassword) ? '✅' : '⭕'}</span>
                            Une majuscule
                          </div>
                          <div className={`flex items-center ${/[a-z]/.test(passwordData.newPassword) ? 'text-green-600' : 'text-gray-400'}`}>
                            <span className="mr-1">{/[a-z]/.test(passwordData.newPassword) ? '✅' : '⭕'}</span>
                            Une minuscule
                          </div>
                          <div className={`flex items-center ${/\d/.test(passwordData.newPassword) ? 'text-green-600' : 'text-gray-400'}`}>
                            <span className="mr-1">{/\d/.test(passwordData.newPassword) ? '✅' : '⭕'}</span>
                            Un chiffre
                          </div>
                          <div className={`flex items-center ${/[!@#$%^&*(),.?":{}|<>]/.test(passwordData.newPassword) ? 'text-green-600' : 'text-gray-400'} sm:col-span-2`}>
                            <span className="mr-1">{/[!@#$%^&*(),.?":{}|<>]/.test(passwordData.newPassword) ? '✅' : '⭕'}</span>
                            Un caractère spécial (!@#$%^&*...)
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t('profile.confirmPassword')} <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type={showPasswords.confirmPassword ? "text" : "password"}
                          name="confirmPassword"
                          autoComplete="new-password"
                          value={passwordData.confirmPassword}
                          onChange={(e) => handlePasswordDataChange('confirmPassword', e.target.value)}
                          className="input-primary pr-10"
                          placeholder="Confirmez votre nouveau mot de passe"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => handleShowPasswordToggle('confirmPassword')}
                          className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                        >
                          {showPasswords.confirmPassword ? (
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
                      <div className="text-xs text-gray-500 mt-1">
                        Caractères tapés: {passwordData.confirmPassword.length}
                      </div>
                    </div>
                    
                    {passwordErrors.length > 0 && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                        <div className="text-sm text-red-800">
                          <p className="font-medium mb-2">Erreurs :</p>
                          <ul className="list-disc list-inside space-y-1">
                            {passwordErrors.map((error, index) => (
                              <li key={index}>{error}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex justify-end space-x-3 p-6 border-t border-gray-200 flex-shrink-0 bg-gray-50">
            <button
              onClick={safeClose}
              className="px-5 py-2 text-gray-600 hover:text-gray-800 font-medium transition-colors"
              disabled={isLoading}
            >
              {t('modal.cancel')}
            </button>
            <button
              onClick={activeTab === 'profile' ? handleProfileSave : handlePasswordChange}
              disabled={isLoading}
              className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors flex items-center"
            >
              {isLoading && (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
              )}
              {isLoading ? t('modal.loading') : t('modal.save')}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}