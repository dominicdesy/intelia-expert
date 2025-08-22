// page_components.tsx - Composants UI pour la page d'authentification avec debug
'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import type { Language } from '@/types'
import type { Country } from './page_hooks'

// Logo Intelia
export const InteliaLogo = ({ className = "w-16 h-16" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// Sélecteur de langue
export const LanguageSelector = ({ onLanguageChange, currentLanguage }: { 
  onLanguageChange: (lang: Language) => void
  currentLanguage: Language 
}) => {
  const [isOpen, setIsOpen] = useState(false)

  const languages = [
    { code: 'fr' as Language, name: 'Français', flag: '🇫🇷' },
    { code: 'en' as Language, name: 'English', flag: '🇺🇸' },
    { code: 'es' as Language, name: 'Español', flag: '🇪🇸' },
    { code: 'de' as Language, name: 'Deutsch', flag: '🇩🇪' }
  ]

  const currentLang = languages.find(lang => lang.code === currentLanguage)

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 transition-colors"
      >
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
        </svg>
        <span>{currentLang?.name}</span>
        <svg className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
            {languages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => {
                  onLanguageChange(lang.code)
                  setIsOpen(false)
                }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center space-x-2 ${
                  lang.code === currentLanguage ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
                } first:rounded-t-lg last:rounded-b-lg transition-colors`}
              >
                <span>{lang.flag}</span>
                <span>{lang.name}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// Sélecteur de pays amélioré avec debug complet
export const CountrySelector = ({ 
  countries, 
  countriesLoading, 
  usingFallback, 
  value, 
  onChange, 
  t 
}: {
  countries: Country[]
  countriesLoading: boolean
  usingFallback: boolean
  value: string
  onChange: (value: string) => void
  t: any
}) => {
  return (
    <div className="mt-4">
      <label className="block text-sm font-medium text-gray-700">
        {t.country} <span className="text-red-500">{t.required}</span>
      </label>
      
      {/* Boîte de debug en mode développement AMÉLIORÉE */}
      {process.env.NODE_ENV === 'development' && (
        <div className="mt-1 mb-2 text-xs bg-blue-50 border border-blue-200 rounded p-3">
          <div className="font-semibold text-blue-800 mb-2">🔧 Debug Countries API:</div>
          <div className="grid grid-cols-2 gap-2 text-blue-700">
            <div>📊 Pays chargés: <span className="font-mono bg-blue-100 px-1 rounded">{countries.length}</span></div>
            <div>⏳ Loading: <span className="font-mono bg-blue-100 px-1 rounded">{countriesLoading ? 'Oui' : 'Non'}</span></div>
            <div>🔄 Mode Fallback: <span className="font-mono bg-blue-100 px-1 rounded">{usingFallback ? 'Oui' : 'Non'}</span></div>
            <div>🎯 Source: <span className="font-mono bg-blue-100 px-1 rounded">{usingFallback ? 'Liste locale' : 'API REST Countries'}</span></div>
          </div>
          {countries.length > 0 && (
            <div className="mt-2 p-2 bg-blue-100 rounded">
              <div className="font-semibold text-blue-800">📋 Premier pays:</div>
              <div className="font-mono text-xs text-blue-700">
                {countries[0].flag} {countries[0].label} ({countries[0].value}) - {countries[0].phoneCode}
              </div>
            </div>
          )}
          <div className="mt-2 text-xs text-blue-600">
            💡 Vérifiez la console pour les logs détaillés
          </div>
        </div>
      )}
      
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
          value={value}
          onChange={(e) => {
            console.log('🏳️ [Country] Sélection pays:', e.target.value)
            onChange(e.target.value)
          }}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
        >
          <option value="">{t.selectCountry}</option>
          {countries.length === 0 ? (
            <option disabled>Aucun pays disponible</option>
          ) : (
            countries.map(country => (
              <option key={country.value} value={country.value}>
                {country.flag ? `${country.flag} ` : ''}{country.label} ({country.phoneCode})
              </option>
            ))
          )}
        </select>
      )}
      
      {/* Message d'information si fallback AMÉLIORÉ */}
      {!countriesLoading && usingFallback && (
        <div className="mt-1 text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-1">
          ⚠️ Liste de pays limitée - L'API REST Countries n'est pas accessible. Utilisation de {countries.length} pays prédéfinis.
        </div>
      )}
      
      {/* Message de succès si API fonctionne */}
      {!countriesLoading && !usingFallback && (
        <div className="mt-1 text-xs text-green-600 bg-green-50 border border-green-200 rounded px-2 py-1">
          ✅ API REST Countries active - {countries.length} pays chargés avec drapeaux et codes téléphoniques
        </div>
      )}
    </div>
  )
}

// Composant d'alerte pour les erreurs/succès
export const AlertMessage = ({ 
  type, 
  title, 
  message 
}: { 
  type: 'error' | 'success'
  title: string
  message: string 
}) => {
  const isError = type === 'error'
  
  return (
    <div className={`mb-6 ${isError ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'} border rounded-lg p-4`}>
      <div className="flex">
        <div className="flex-shrink-0">
          {isError ? (
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          )}
        </div>
        <div className="ml-3">
          {title && (
            <h3 className={`text-sm font-medium ${isError ? 'text-red-800' : 'text-green-800'}`}>
              {title}
            </h3>
          )}
          <div className={`${title ? 'mt-1' : ''} text-sm ${isError ? 'text-red-700' : 'text-green-700'}`}>
            {message}
          </div>
        </div>
      </div>
    </div>
  )
}

// Input avec toggle de visibilité pour les mots de passe
export const PasswordInput = ({
  id,
  name,
  value,
  onChange,
  placeholder,
  required = false,
  autoComplete,
  className = "block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
}: {
  id?: string
  name?: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  placeholder?: string
  required?: boolean
  autoComplete?: string
  className?: string
}) => {
  const [showPassword, setShowPassword] = useState(false)

  return (
    <div className="relative">
      <input
        id={id}
        name={name}
        type={showPassword ? "text" : "password"}
        autoComplete={autoComplete}
        required={required}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className={className}
      />
      <button
        type="button"
        className="absolute inset-y-0 right-0 pr-3 flex items-center"
        onClick={() => setShowPassword(!showPassword)}
      >
        {showPassword ? (
          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
          </svg>
        ) : (
          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        )}
      </button>
    </div>
  )
}

// Indicateur de correspondance des mots de passe
export const PasswordMatchIndicator = ({ 
  password, 
  confirmPassword 
}: { 
  password: string
  confirmPassword: string 
}) => {
  if (!password || !confirmPassword) return null

  const match = confirmPassword === password

  return (
    <div className="mt-2 text-xs">
      {match ? (
        <span className="text-green-600 flex items-center">
          <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Les mots de passe correspondent
        </span>
      ) : (
        <span className="text-red-600 flex items-center">
          <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          Les mots de passe ne correspondent pas
        </span>
      )}
    </div>
  )
}

// Loading Spinner
export const LoadingSpinner = ({ text = "Chargement..." }: { text?: string }) => (
  <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
    <div className="text-center">
      <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p className="text-gray-600">{text}</p>
    </div>
  </div>
)

// Footer avec liens
export const AuthFooter = ({ t }: { t: any }) => (
  <div className="mt-6 text-center">
    <p className="text-xs text-gray-500">
      {t.gdprNotice}{' '}
      <Link href="/terms" className="text-blue-600 hover:text-blue-500">
        {t.terms}
      </Link>
      {' '}et notre{' '}
      <Link href="/privacy" className="text-blue-600 hover:text-blue-500">
        {t.privacy}
      </Link>
    </p>
  </div>
)