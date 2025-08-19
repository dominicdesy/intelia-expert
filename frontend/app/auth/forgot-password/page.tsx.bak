'use client'

import { useState } from 'react'
import Link from 'next/link'

// ==================== LOGO INTELIA ====================
const InteliaLogo = ({ className = "w-12 h-12" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// ==================== PAGE MOT DE PASSE OUBLIÉ ====================
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    setError('')
    setSuccess('')
    
    // Validations
    if (!email.trim()) {
      setError('Veuillez entrer votre adresse email')
      return
    }
    
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Veuillez entrer une adresse email valide')
      return
    }

    setIsLoading(true)

    try {
      // TODO: Intégrer avec Supabase
      // const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
      //   redirectTo: `${window.location.origin}/auth/reset-password`
      // })
      
      console.log('📧 Envoi email de réinitialisation à:', email.trim())
      
      // Simulation temporaire
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      setSuccess(`Un email de réinitialisation a été envoyé à ${email.trim()}`)
      setEmail('')
      
    } catch (error: any) {
      console.error('❌ Erreur lors de l\'envoi de l\'email:', error)
      setError(error.message || 'Erreur lors de l\'envoi de l\'email de réinitialisation')
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      handleSubmit()
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
            Mot de passe oublié
          </h1>
          <p className="text-gray-600 leading-relaxed">
            Entrez votre adresse email et nous vous enverrons un lien pour réinitialiser votre mot de passe
          </p>
        </div>

        {/* Messages d'erreur */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            <div className="flex items-center space-x-2">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Messages de succès */}
        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">
            <div className="flex items-center space-x-2">
              <span>✅</span>
              <span>{success}</span>
            </div>
            <div className="mt-2 text-xs text-green-600">
              Vérifiez votre boîte de réception et vos spams
            </div>
          </div>
        )}

        {/* Formulaire */}
        <div className="bg-white p-6 rounded-lg shadow-lg border border-gray-200">
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Adresse email
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyPress={handleKeyPress}
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
                placeholder="votre@email.com"
                disabled={isLoading}
              />
            </div>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading}
              className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Envoi en cours...</span>
                </div>
              ) : (
                'Envoyer le lien de réinitialisation'
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <div className="mt-6 text-center space-y-3">
          <Link
            href="/auth/login"
            className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Retour à la connexion
          </Link>
          
          <div className="text-xs text-gray-500">
            Vous n'avez pas de compte ?{' '}
            <Link href="/auth/signup" className="text-blue-600 hover:underline transition-colors">
              Créer un compte
            </Link>
          </div>
        </div>

        {/* Support */}
        <div className="mt-8 p-3 bg-gray-50 rounded-lg text-center">
          <p className="text-xs text-gray-600">
            Problème avec la réinitialisation ?{' '}
            <button
              type="button"
              onClick={() => window.open('mailto:support@intelia.com', '_blank')}
              className="text-blue-600 hover:underline font-medium transition-colors"
            >
              Contactez le support
            </button>
          </p>
        </div>

        {/* Information sécurité */}
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500 leading-relaxed">
            🔒 Pour votre sécurité, le lien de réinitialisation expire dans 1 heure.
            <br />
            Aucun email reçu ? Vérifiez vos spams ou contactez le support.
          </p>
        </div>
      </div>
    </div>
  )
}