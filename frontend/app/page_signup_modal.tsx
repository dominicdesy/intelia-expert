'use client'

import React, { useState, useRef, useEffect } from 'react'
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

export function SignupModal({ 
  authLogic, 
  localError, 
  localSuccess, 
  toggleMode 
}: SignupModalProps) {
  // Utilise directement useTranslation au lieu de recevoir t comme prop
  const { t } = useTranslation()
  
  // Chargement des pays uniquement dans SignupModal
  const { countries, loading: countriesLoading, usingFallback } = useCountries()

  const {
    signupData,
    showPassword,
    setShowPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    isLoading,
    handleSignupChange,
    handleSignup,
    validatePassword
  } = authLogic

  const [formError, setFormError] = React.useState('')
  const [formSuccess, setFormSuccess] = React.useState('')

  // Gestion locale simplifiée de l'auto-remplissage country
  const handleCountryChange = React.useCallback((value: string) => {
    handleSignupChange('country', value)
  }, [handleSignupChange])

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setFormSuccess('')

    try {
      const result = await handleSignup(e)
      
      if (result && result.success) {
        setFormSuccess(result.message || t('auth.success'))
        
        // Passer en mode login après 4 secondes
        setTimeout(() => {
          toggleMode()
        }, 4000)
      }
      
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
      <div className="w-full max-w-md mx-auto bg-white rounded-lg shadow-xl max-h-[calc(100vh-2rem)] overflow-y-auto overscroll-contain">
        
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

          {/* FORMULAIRE D'INSCRIPTION SIMPLIFIÉ */}
          <form onSubmit={onSubmit} onKeyPress={handleKeyPress}>
            <div className="space-y-4">
              
              {/* Prénom et Nom */}
              <div className="grid grid-cols-2 gap-4">
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

              {/* Email */}
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

              {/* Sélecteur de pays */}
              <div>
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

              {/* Mot de passe */}
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

              {/* Confirmer mot de passe */}
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
              className="flex w-full justify-center rounded-md border border-transparent bg-green-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Création en cours...</span>
                </div>
              ) : (
                t('auth.createAccount')
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}