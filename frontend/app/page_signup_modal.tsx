'use client'

import React, { useState, useRef, useEffect, useMemo } from 'react'
import { AlertMessage } from './page_components'
import { useCountries, useCountryCodeMap } from './page_hooks'
import { useTranslation } from '@/lib/languages/i18n'

interface SignupModalProps {
  authLogic: any
  localError: string
  localSuccess: string
  toggleMode: () => void
}

// Composant CountrySelect local pour éviter les problèmes d'import
interface Country {
  value: string
  label: string
  phoneCode: string
  flag?: string
}

interface CountrySelectProps {
  countries: Country[]
  value: string
  onChange: (value: string) => void
  placeholder: string
  className?: string
}

const CountrySelect: React.FC<CountrySelectProps> = ({ 
  countries, 
  value, 
  onChange, 
  placeholder,
  className = "" 
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const selectRef = useRef<HTMLDivElement>(null)

  const filteredCountries = countries.filter(country =>
    country.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
    country.value.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const selectedCountry = countries.find(c => c.value === value)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (selectRef.current && !selectRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchTerm('')
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  return (
    <div ref={selectRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="block w-full rounded-md border border-gray-300 px-3 py-2 text-left shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm bg-white"
      >
        {selectedCountry ? (
          <div className="flex items-center space-x-2">
            {selectedCountry.flag && <span>{selectedCountry.flag}</span>}
            <span>{selectedCountry.label}</span>
            <span className="text-gray-500 ml-auto">{selectedCountry.phoneCode}</span>
          </div>
        ) : (
          <span className="text-gray-400">{placeholder}</span>
        )}
        <div className="absolute inset-y-0 right-0 flex items-center pr-2">
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-hidden">
          <div className="p-2 border-b border-gray-200">
            <input
              type="text"
              placeholder="Rechercher un pays..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="max-h-48 overflow-y-auto">
            {filteredCountries.length > 0 ? (
              filteredCountries.map((country) => (
                <button
                  key={country.value}
                  type="button"
                  onClick={() => {
                    onChange(country.value)
                    setIsOpen(false)
                    setSearchTerm('')
                  }}
                  className={`w-full text-left px-3 py-2 hover:bg-gray-100 flex items-center space-x-2 ${
                    value === country.value ? 'bg-blue-50 text-blue-600' : ''
                  }`}
                >
                  {country.flag && <span>{country.flag}</span>}
                  <span className="flex-1">{country.label}</span>
                  <span className="text-gray-500">{country.phoneCode}</span>
                </button>
              ))
            ) : (
              <div className="px-3 py-2 text-gray-500 text-sm">Aucun pays trouvé</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Composant PhoneCodeSelect pour les codes téléphoniques
interface PhoneCode {
  code: string
  country: string
  flag?: string
  priority?: number
}

interface PhoneCodeSelectProps {
  countries: Country[]
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  className?: string
}

const PhoneCodeSelect: React.FC<PhoneCodeSelectProps> = ({ 
  countries, 
  value, 
  onChange, 
  disabled = false,
  className = "" 
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const selectRef = useRef<HTMLDivElement>(null)

  // Convertir les données countries en codes téléphoniques
  const phoneCodes = useMemo(() => {
    const fallbackCodes = [
      { code: '+1', country: 'Canada/États-Unis', flag: '🇨🇦🇺🇸', priority: 1 },
      { code: '+33', country: 'France', flag: '🇫🇷', priority: 2 },
      { code: '+32', country: 'Belgique', flag: '🇧🇪', priority: 3 },
      { code: '+41', country: 'Suisse', flag: '🇨🇭', priority: 4 },
      { code: '+49', country: 'Allemagne', flag: '🇩🇪', priority: 5 },
      { code: '+44', country: 'Royaume-Uni', flag: '🇬🇧', priority: 6 },
      { code: '+39', country: 'Italie', flag: '🇮🇹', priority: 7 },
      { code: '+34', country: 'Espagne', flag: '🇪🇸', priority: 8 },
      { code: '+52', country: 'Mexique', flag: '🇲🇽', priority: 9 },
      { code: '+55', country: 'Brésil', flag: '🇧🇷', priority: 10 }
    ]

    if (countries.length === 0) {
      return fallbackCodes
    }

    // Transformer les données countries en phoneCodes
    const transformed = countries
      .filter(country => country.phoneCode && country.phoneCode !== '+')
      .reduce((acc: PhoneCode[], current) => {
        const existing = acc.find(item => item.code === current.phoneCode)
        if (existing) {
          // Si plusieurs pays ont le même code, les combiner
          if (!existing.country.includes(current.label)) {
            existing.country += `, ${current.label}`
          }
        } else {
          acc.push({
            code: current.phoneCode,
            country: current.label,
            flag: current.flag
          })
        }
        return acc
      }, [])
      .sort((a: PhoneCode, b: PhoneCode) => {
        // Priorité aux codes les plus courants
        const priorityA = fallbackCodes.find(f => f.code === a.code)?.priority || 999
        const priorityB = fallbackCodes.find(f => f.code === b.code)?.priority || 999
        
        if (priorityA !== priorityB) {
          return priorityA - priorityB
        }
        
        return a.country.localeCompare(b.country)
      })

    return transformed.length > 20 ? transformed : fallbackCodes
  }, [countries])

  const filteredCodes = phoneCodes.filter(code =>
    code.code.includes(searchTerm) ||
    code.country.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const selectedCode = phoneCodes.find(c => c.code === value)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (selectRef.current && !selectRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchTerm('')
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  return (
    <div ref={selectRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="block w-full rounded-md border border-gray-300 px-2 py-2 text-left shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-sm bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
      >
        {selectedCode ? (
          <div className="flex items-center space-x-1">
            {selectedCode.flag && <span className="text-xs">{selectedCode.flag}</span>}
            <span className="font-mono">{selectedCode.code}</span>
          </div>
        ) : (
          <span className="text-gray-400">+1</span>
        )}
        <div className="absolute inset-y-0 right-0 flex items-center pr-1">
          <svg className="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-48 overflow-hidden">
          <div className="p-1 border-b border-gray-200">
            <input
              type="text"
              placeholder="Rechercher..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="max-h-40 overflow-y-auto">
            {filteredCodes.length > 0 ? (
              filteredCodes.map((code) => (
                <button
                  key={code.code}
                  type="button"
                  onClick={() => {
                    onChange(code.code)
                    setIsOpen(false)
                    setSearchTerm('')
                  }}
                  className={`w-full text-left px-2 py-1.5 hover:bg-gray-100 flex items-center justify-between text-xs ${
                    value === code.code ? 'bg-blue-50 text-blue-600' : ''
                  }`}
                >
                  <div className="flex items-center space-x-1">
                    {code.flag && <span>{code.flag}</span>}
                    <span className="font-mono font-medium">{code.code}</span>
                  </div>
                  <span className="text-gray-500 text-xs truncate ml-1">{code.country.split(',')[0]}</span>
                </button>
              ))
            ) : (
              <div className="px-2 py-1.5 text-gray-500 text-xs">Aucun code trouvé</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export function SignupModal({ 
  authLogic, 
  localError, 
  localSuccess, 
  toggleMode 
}: SignupModalProps) {
  // ✅ UTILISE DIRECTEMENT useTranslation au lieu de recevoir t comme prop
  const { t } = useTranslation()
  
  // Chargement des pays uniquement dans SignupModal
  const { countries, loading: countriesLoading, usingFallback } = useCountries()
  const countryCodeMap = useCountryCodeMap(countries)

  const {
    signupData,
    showPassword,
    setShowPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    isLoading,
    handleSignupChange,
    handleSignup,
    validatePassword,
    validatePhone
  } = authLogic

  const [formError, setFormError] = React.useState('')
  const [formSuccess, setFormSuccess] = React.useState('')

  // Gestion locale de l'auto-remplissage country → countryCode
  const handleCountryChange = React.useCallback((value: string) => {
    // Mettre à jour le pays
    handleSignupChange('country', value)
    
    // Auto-remplir le code pays si disponible
    if (value && countryCodeMap[value]) {
      console.log('🏳️ [Country] Auto-remplissage code pays:', value, '->', countryCodeMap[value])
      handleSignupChange('countryCode', countryCodeMap[value])
    }
  }, [handleSignupChange, countryCodeMap])

  // Fonction pour gérer le changement de code téléphonique
  const handlePhoneCodeChange = React.useCallback((value: string) => {
    handleSignupChange('countryCode', value)
  }, [handleSignupChange])

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setFormSuccess('')

    try {
      await handleSignup(e)
      setFormSuccess(t('auth.success'))
      
      // Passer en mode login après 4 secondes
      setTimeout(() => {
        toggleMode()
      }, 4000)
      
    } catch (error: any) {
      setFormError(error.message)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onSubmit(e as any)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 p-4 overflow-hidden overscroll-none">
      <div className="w-full max-w-2xl mx-auto bg-white rounded-lg shadow-xl max-h-[calc(100vh-2rem)] overflow-y-auto overscroll-contain">
        
        {/* Header de la modale avec bouton fermer */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-lg">
          <h3 className="text-lg font-semibold text-gray-900">{t('auth.createAccount')}</h3>
          <button
            onClick={toggleMode}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Corps de la modale */}
        <div className="flex-1 px-6 py-4">
          
          {/* Messages d'erreur et succès pour signup */}
          {(localError || formError) && (
            <AlertMessage 
              type="error" 
              title={t('error.generic')} 
              message={localError || formError} 
            />
          )}

          {(localSuccess || formSuccess) && (
            <AlertMessage 
              type="success" 
              title="" 
              message={localSuccess || formSuccess} 
            />
          )}

          {/* Avertissement fallback pays */}
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

          {/* FORMULAIRE D'INSCRIPTION */}
          <form onSubmit={onSubmit} onKeyPress={handleKeyPress}>
            <div className="space-y-6">
              {/* Section Informations personnelles */}
              <div className="border-b border-gray-200 pb-6">
                <h4 className="text-md font-medium text-gray-900 mb-4">{t('profile.personalInfo')}</h4>
                
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t('profile.firstName')} <span className="text-red-500">{t('form.required')}</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={signupData.firstName}
                      onChange={(e) => handleSignupChange('firstName', e.target.value)}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isLoading}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t('profile.lastName')} <span className="text-red-500">{t('form.required')}</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={signupData.lastName}
                      onChange={(e) => handleSignupChange('lastName', e.target.value)}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isLoading}
                    />
                  </div>
                </div>

                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700">
                    {t('profile.linkedinProfile')} {t('common.optional')}
                  </label>
                  <input
                    type="url"
                    value={signupData.linkedinProfile}
                    onChange={(e) => handleSignupChange('linkedinProfile', e.target.value)}
                    placeholder={t('placeholder.linkedinPersonal')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* Section Contact */}
              <div className="border-b border-gray-200 pb-6">
                <h4 className="text-md font-medium text-gray-900 mb-4">{t('profile.contact')}</h4>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    {t('profile.email')} <span className="text-red-500">{t('form.required')}</span>
                  </label>
                  <input
                    type="email"
                    required
                    value={signupData.email}
                    onChange={(e) => handleSignupChange('email', e.target.value)}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    disabled={isLoading}
                  />
                </div>

                {/* Sélecteur de pays avec composant local */}
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {t('profile.country')} <span className="text-red-500">{t('form.required')}</span>
                  </label>
                  
                  {countriesLoading ? (
                    <div className="block w-full rounded-md border border-gray-300 px-3 py-2 bg-gray-50">
                      <div className="flex items-center space-x-2">
                        <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                        <span className="text-sm text-gray-600">{t('common.loading')}</span>
                      </div>
                    </div>
                  ) : (
                    <CountrySelect
                      countries={countries}
                      value={signupData.country}
                      onChange={handleCountryChange}
                      placeholder={t('placeholder.countrySelect')}
                      className="w-full"
                    />
                  )}
                </div>

                {/* Téléphone optionnel avec PhoneCodeSelect */}
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {t('profile.phone')} {t('common.optional')}
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Code pays</label>
                      <PhoneCodeSelect
                        countries={countries}
                        value={signupData.countryCode}
                        onChange={handlePhoneCodeChange}
                        disabled={isLoading}
                        className="w-full"
                      />
                    </div>					
                    
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Code région</label>
                      <input
                        type="tel"
                        value={signupData.areaCode}
                        onChange={(e) => handleSignupChange('areaCode', e.target.value.replace(/\D/g, ''))}
                        placeholder="514"
                        maxLength={4}
                        className="block w-full rounded-md border border-gray-300 px-2 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-sm"
                        disabled={isLoading}
                      />
                    </div>
                    
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Numéro</label>
                      <input
                        type="tel"
                        value={signupData.phoneNumber}
                        onChange={(e) => handleSignupChange('phoneNumber', e.target.value.replace(/\D/g, ''))}
                        placeholder="1234567"
                        maxLength={10}
                        className="block w-full rounded-md border border-gray-300 px-2 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-sm"
                        disabled={isLoading}
                      />
                    </div>
                  </div>
                  
                  {(signupData.countryCode || signupData.areaCode || signupData.phoneNumber) && (
                    <div className="mt-2">
                      {(() => {
                        const hasAllFields = signupData.countryCode && signupData.areaCode && signupData.phoneNumber
                        const hasAnyField = signupData.countryCode || signupData.areaCode || signupData.phoneNumber
                        
                        if (hasAllFields && validatePhone(signupData.countryCode, signupData.areaCode, signupData.phoneNumber)) {
                          return (
                            <div className="flex items-center text-xs text-green-600">
                              <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                              </svg>
                              Format téléphone valide
                            </div>
                          )
                        } else if (hasAnyField && !hasAllFields) {
                          return (
                            <div className="flex items-center text-xs text-yellow-600">
                              <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                              </svg>
                              Téléphone incomplet (facultatif)
                            </div>
                          )
                        } else if (hasAllFields && !validatePhone(signupData.countryCode, signupData.areaCode, signupData.phoneNumber)) {
                          return (
                            <div className="flex items-center text-xs text-red-600">
                              <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                              </svg>
                              Format téléphone invalide
                            </div>
                          )
                        }
                        return null
                      })()}
                    </div>
                  )}
                </div>
              </div>

              {/* Section Entreprise */}
              <div className="border-b border-gray-200 pb-6">
                <h4 className="text-md font-medium text-gray-900 mb-4">{t('profile.company')}</h4>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    {t('profile.companyName')} {t('common.optional')}
                  </label>
                  <input
                    type="text"
                    value={signupData.companyName}
                    onChange={(e) => handleSignupChange('companyName', e.target.value)}
                    placeholder={t('placeholder.companyName')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    disabled={isLoading}
                  />
                </div>

                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700">
                    {t('profile.companyWebsite')} {t('common.optional')}
                  </label>
                  <input
                    type="url"
                    value={signupData.companyWebsite}
                    onChange={(e) => handleSignupChange('companyWebsite', e.target.value)}
                    placeholder={t('placeholder.companyWebsite')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    disabled={isLoading}
                  />
                </div>

                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700">
                    {t('profile.companyLinkedin')} {t('common.optional')}
                  </label>
                  <input
                    type="url"
                    value={signupData.companyLinkedin}
                    onChange={(e) => handleSignupChange('companyLinkedin', e.target.value)}
                    placeholder={t('placeholder.linkedinCorporate')}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* Section Mot de passe */}
              <div>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t('profile.password')} <span className="text-red-500">{t('form.required')}</span>
                    </label>
                    <div className="mt-1 relative">
                      <input
                        type={showPassword ? "text" : "password"}
                        required
                        value={signupData.password}
                        onChange={(e) => handleSignupChange('password', e.target.value)}
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        placeholder="••••••••"
                        disabled={isLoading}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                        tabIndex={-1}
                      >
                        <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </button>
                    </div>
                    {signupData.password && (
                      <div className="mt-2 space-y-1">
                        {(() => {
                          const validation = validatePassword(signupData.password)
                          return validation.errors.map((error: string, index: number) => (
                            <div key={index} className="flex items-center text-xs text-red-600">
                              <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                              </svg>
                              {error}
                            </div>
                          ))
                        })()}
                        {validatePassword(signupData.password).isValid && (
                          <div className="flex items-center text-xs text-green-600">
                            <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            Mot de passe valide
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t('profile.confirmPassword')} <span className="text-red-500">{t('form.required')}</span>
                    </label>
                    <div className="mt-1 relative">
                      <input
                        type={showConfirmPassword ? "text" : "password"}
                        required
                        value={signupData.confirmPassword}
                        onChange={(e) => handleSignupChange('confirmPassword', e.target.value)}
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        placeholder="••••••••"
                        disabled={isLoading}
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                        tabIndex={-1}
                      >
                        <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </button>
                    </div>
                    {signupData.confirmPassword && (
                      <div className="mt-2">
                        {signupData.password === signupData.confirmPassword ? (
                          <div className="flex items-center text-xs text-green-600">
                            <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            Mots de passe identiques
                          </div>
                        ) : (
                          <div className="flex items-center text-xs text-red-600">
                            <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                            </svg>
                            Les mots de passe ne correspondent pas
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </form>
        </div>

        {/* Footer de la modale avec boutons */}
        <div className="flex-shrink-0 bg-gray-50 border-t border-gray-200 px-6 py-4 rounded-b-lg">
          <div className="flex space-x-3">
            <button
              type="button"
              onClick={toggleMode}
              className="flex-1 rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              {t('modal.back')}
            </button>
            <button
              onClick={onSubmit}
              disabled={isLoading}
              className="flex-1 rounded-md border border-transparent bg-green-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? t('common.loading') : t('auth.createAccount')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}