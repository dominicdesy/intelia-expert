'use client'

import React from 'react'
import { AlertMessage } from './page_components'

interface SignupModalProps {
  authLogic: any
  t: any
  localError: string
  localSuccess: string
  toggleMode: () => void
}

export function SignupModal({ 
  authLogic, 
  t, 
  localError, 
  localSuccess, 
  toggleMode 
}: SignupModalProps) {
  const {
    signupData,
    showPassword,
    setShowPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    isLoading,
    countries,
    countriesLoading,
    handleSignupChange,
    handleSignup,
    validatePassword,
    validatePhone
  } = authLogic

  const [formError, setFormError] = React.useState('')
  const [formSuccess, setFormSuccess] = React.useState('')

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setFormSuccess('')

    try {
      await handleSignup(e)
      setFormSuccess(t.accountCreated)
      
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
          <h3 className="text-lg font-semibold text-gray-900">{t.createAccount}</h3>
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
              title={t.signupError} 
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

          {/* FORMULAIRE D'INSCRIPTION */}
          <form onSubmit={onSubmit} onKeyPress={handleKeyPress}>
            <div className="space-y-6">
              {/* Section Informations personnelles */}
              <div className="border-b border-gray-200 pb-6">
                <h4 className="text-md font-medium text-gray-900 mb-4">{t.personalInfo}</h4>
                
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      {t.firstName} <span className="text-red-500">{t.required}</span>
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
                      {t.lastName} <span className="text-red-500">{t.required}</span>
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
                    {t.linkedinProfile} {t.optional}
                  </label>
                  <input
                    type="url"
                    value={signupData.linkedinProfile}
                    onChange={(e) => handleSignupChange('linkedinProfile', e.target.value)}
                    placeholder="https://linkedin.com/in/votre-profil"
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* Section Contact */}
              <div className="border-b border-gray-200 pb-6">
                <h4 className="text-md font-medium text-gray-900 mb-4">{t.contact}</h4>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    {t.email} <span className="text-red-500">{t.required}</span>
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
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700">
                    {t.country} <span className="text-red-500">{t.required}</span>
                  </label>
                  
                  {countriesLoading ? (
                    <div className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 bg-gray-50">
                      <div className="flex items-center space-x-2">
                        <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                        <span className="text-sm text-gray-600">{t.loadingCountries}</span>
                      </div>
                    </div>
                  ) : (
                    <select
                      required
                      value={signupData.country}
                      onChange={(e) => handleSignupChange('country', e.target.value)}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 bg-white shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      disabled={isLoading}
                    >
                      <option value="">{t.selectCountry}</option>
                      {countries.map((country: any) => (
                        <option key={country.value} value={country.value}>
                          {country.flag ? `${country.flag} ` : ''}{country.label} ({country.phoneCode})
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                {/* Téléphone optionnel */}
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Téléphone {t.optional}
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">{t.countryCode}</label>
                      <input
                        type="text"
                        value={signupData.countryCode}
                        onChange={(e) => handleSignupChange('countryCode', e.target.value)}
                        placeholder="+1"
                        className="block w-full rounded-md border border-gray-300 px-2 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-sm"
                        disabled={isLoading}
                      />
                    </div>
                    
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">{t.areaCode}</label>
                      <input
                        type="tel"
                        value={signupData.areaCode}
                        onChange={(e) => handleSignupChange('areaCode', e.target.value)}
                        placeholder="514"
                        maxLength={3}
                        className="block w-full rounded-md border border-gray-300 px-2 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-sm"
                        disabled={isLoading}
                      />
                    </div>
                    
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">{t.phoneNumber}</label>
                      <input
                        type="tel"
                        value={signupData.phoneNumber}
                        onChange={(e) => handleSignupChange('phoneNumber', e.target.value)}
                        placeholder="1234567"
                        maxLength={7}
                        className="block w-full rounded-md border border-gray-300 px-2 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 text-sm"
                        disabled={isLoading}
                      />
                    </div>
                  </div>
                  
                  {(signupData.countryCode || signupData.areaCode || signupData.phoneNumber) && (
                    <div className="mt-2">
                      {validatePhone(signupData.countryCode, signupData.areaCode, signupData.phoneNumber) ? (
                        <div className="flex items-center text-xs text-green-600">
                          <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          Format téléphone valide
                        </div>
                      ) : (
                        <div className="flex items-center text-xs text-red-600">
                          <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                          </svg>
                          Tous les champs téléphone sont requis
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Section Entreprise */}
              <div className="border-b border-gray-200 pb-6">
                <h4 className="text-md font-medium text-gray-900 mb-4">{t.company}</h4>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    {t.companyName} {t.optional}
                  </label>
                  <input
                    type="text"
                    value={signupData.companyName}
                    onChange={(e) => handleSignupChange('companyName', e.target.value)}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    disabled={isLoading}
                  />
                </div>

                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700">
                    {t.companyWebsite} {t.optional}
                  </label>
                  <input
                    type="url"
                    value={signupData.companyWebsite}
                    onChange={(e) => handleSignupChange('companyWebsite', e.target.value)}
                    placeholder="https://www.entreprise.com"
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    disabled={isLoading}
                  />
                </div>

                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700">
                    {t.companyLinkedin} {t.optional}
                  </label>
                  <input
                    type="url"
                    value={signupData.companyLinkedin}
                    onChange={(e) => handleSignupChange('companyLinkedin', e.target.value)}
                    placeholder="https://linkedin.com/company/votre-entreprise"
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
                      {t.password} <span className="text-red-500">{t.required}</span>
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
                      {t.confirmPassword} <span className="text-red-500">{t.required}</span>
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
              {t.backToLogin}
            </button>
            <button
              onClick={onSubmit}
              disabled={isLoading}
              className="flex-1 rounded-md border border-transparent bg-green-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? t.creating : t.createAccount}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}