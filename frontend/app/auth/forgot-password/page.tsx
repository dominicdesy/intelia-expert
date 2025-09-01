'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useTranslation } from '@/lib/languages/i18n'

// Logo Intelia
const InteliaLogo = ({ className = "w-12 h-12" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// Page Mot de Passe Oublié - VERSION ULTRA-SIMPLE COMME CONTACTMODAL
export default function ForgotPasswordPage() {
  // EXACTEMENT COMME CONTACTMODAL - RIEN D'AUTRE
  const { t, currentLanguage } = useTranslation()
  
  // États simples
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  // Fonction de soumission simple
  const handleSubmit = async () => {
    setError('')
    setSuccess('')
    
    // Validations basiques
    if (!email.trim()) {
      setError(t('forgotPassword.enterEmail'))
      return
    }
    
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError(t('forgotPassword.invalidEmail'))
      return
    }

    setIsLoading(true)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app/api'}/v1/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email.trim()
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Erreur ${response.status}`)
      }

      setSuccess(`${t('forgotPassword.emailSent')} ${email.trim()}`)
      setEmail('')
      
    } catch (error: any) {
      if (error.message.includes('404')) {
        setError(t('forgotPassword.emailNotFound'))
      } else if (error.message.includes('429')) {
        setError(t('forgotPassword.tooManyAttempts'))
      } else if (error.message.includes('Failed to fetch')) {
        setError(t('forgotPassword.connectionError'))
      } else {
        setError(error.message || t('forgotPassword.genericError'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <InteliaLogo className="w-12 h-12" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {t('forgotPassword.title')}
          </h1>
          <p className="text-gray-600 leading-relaxed">
            {t('forgotPassword.description')}
          </p>
        </div>

        {/* Messages d'erreur */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Messages de succès */}
        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{success}</span>
            </div>
            <div className="mt-2 text-xs text-green-600">
              {t('forgotPassword.checkInbox')}
            </div>
          </div>
        )}

        {/* Formulaire */}
        <div className="bg-white p-6 rounded-lg shadow-lg border border-gray-200">
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                {t('forgotPassword.emailLabel')}
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
                placeholder={t('forgotPassword.emailPlaceholder')}
                disabled={isLoading}
                autoComplete="email"
              />
            </div>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading || !email.trim()}
              className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>{t('forgotPassword.sending')}</span>
                </div>
              ) : (
                t('forgotPassword.sendButton')
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <div className="mt-6 text-center space-y-3">
          <Link
            href="/"
            className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            {t('forgotPassword.backToLogin')}
          </Link>
          
          <div className="text-xs text-gray-500">
            {t('forgotPassword.noAccount')}{' '}
            <Link href="/?signup=true" className="text-blue-600 hover:underline transition-colors">
              {t('auth.createAccount')}
            </Link>
          </div>
        </div>

        {/* Support */}
        <div className="mt-4 p-3 bg-gray-50 rounded-lg text-center">
          <p className="text-xs text-gray-600">
            {t('forgotPassword.supportProblem')}{' '}
            <button
              type="button"
              onClick={() => window.open('mailto:support@intelia.com?subject=Problème réinitialisation mot de passe', '_blank')}
              className="text-blue-600 hover:underline font-medium transition-colors"
            >
              {t('forgotPassword.contactSupport')}
            </button>
          </p>
        </div>

        {/* Information sécurité */}
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500 leading-relaxed">
            {t('forgotPassword.securityInfo')}
            <br />
            {t('forgotPassword.securityInfo2')}
          </p>
        </div>

        {/* Debug simple */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-4 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
            <strong>Debug:</strong> Langue: {currentLanguage} | Titre: {t('forgotPassword.title')}
          </div>
        )}
      </div>
    </div>
  )
}