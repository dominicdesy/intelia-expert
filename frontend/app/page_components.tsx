// page_components.tsx
import React, { useState } from 'react'
import Link from 'next/link'
import type { Language } from '@/types'
import type { TranslationStrings } from './page_types'

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

// Message d'alerte
export const AlertMessage = ({ type, title, message }: {
  type: 'error' | 'success'
  title: string
  message: string
}) => {
  const isError = type === 'error'
  
  return (
    <div className={`mb-6 ${isError ? 'bg-red-50' : 'bg-green-50'} border ${isError ? 'border-red-200' : 'border-green-200'} rounded-lg p-4`}>
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
          <div className={`${title ? 'mt-1 ' : ''}text-sm ${isError ? 'text-red-700' : 'text-green-700'}`}>
            {message}
          </div>
        </div>
      </div>
    </div>
  )
}

// Input de mot de passe avec bouton show/hide
export const PasswordInput = ({ value, onChange, id, name, autoComplete, required, placeholder }: {
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  id?: string
  name?: string
  autoComplete?: string
  required?: boolean
  placeholder?: string
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
        className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
      />
      <button
        type="button"
        onClick={() => setShowPassword(!showPassword)}
        className="absolute inset-y-0 right-0 pr-3 flex items-center hover:text-gray-600 transition-colors"
        tabIndex={-1}
      >
        {showPassword ? (
          <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.34 6.34m6.822 10.565l-3.536-3.536" />
          </svg>
        ) : (
          <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        )}
      </button>
    </div>
  )
}

// Indicateur de correspondance des mots de passe
export const PasswordMatchIndicator = ({ password, confirmPassword }: {
  password: string
  confirmPassword: string
}) => {
  if (!confirmPassword) return null

  const doMatch = password === confirmPassword

  return (
    <div className="mt-2">
      {doMatch ? (
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
  )
}

// Spinner de chargement
export const LoadingSpinner = () => (
  <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
    <div className="text-center">
      <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
      <p className="mt-4 text-gray-600">Initialisation...</p>
    </div>
  </div>
)

// Footer d'authentification
export const AuthFooter = ({ t }: { t: TranslationStrings }) => (
  <div className="mt-6 pt-6 border-t border-gray-200">
    <div className="flex items-start space-x-3 p-4 bg-blue-50 rounded-lg border border-blue-200">
      <div className="flex-shrink-0 mt-0.5">
        <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-blue-800 leading-relaxed">
          <span className="font-medium">Déclaration de conformité :</span>{' '}
          {t.gdprNotice}{' '}
          <Link 
            href="/terms" 
            className="text-blue-700 hover:text-blue-900 underline font-medium transition-colors"
            target="_blank"
          >
            {t.terms}
          </Link>{' '}
          et notre{' '}
          <Link 
            href="/privacy" 
            className="text-blue-700 hover:text-blue-900 underline font-medium transition-colors"
            target="_blank"
          >
            {t.privacy}
          </Link>
          .
        </p>
      </div>
    </div>
    
    <div className="mt-4 text-center">
      <p className="text-xs text-gray-500">
        {t.needHelp}{' '}
        <button
          type="button"
          onClick={() => window.open('mailto:support@intelia.com', '_blank')}
          className="text-blue-600 hover:underline font-medium"
        >
          {t.contactSupport}
        </button>
      </p>
    </div>
  </div>
)