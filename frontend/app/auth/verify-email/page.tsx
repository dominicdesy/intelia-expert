'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuthStore } from '@/lib/stores/auth'

// ==================== LOGO INTELIA ====================
const InteliaLogo = ({ className = "w-12 h-12" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

// ==================== PAGE SUCCÈS VÉRIFICATION ====================
const VerificationSuccessPage = ({ email }: { email?: string }) => {
  const router = useRouter()

  useEffect(() => {
    // Redirection automatique après 5 secondes vers la page de connexion
    const timer = setTimeout(() => {
      router.push('/')
    }, 5000)
    
    return () => clearTimeout(timer)
  }, [router])

  return (
    <div className="bg-white py-8 px-6 shadow-lg rounded-lg border border-gray-200">
      <div className="text-center">
        <div className="mb-4">
          <div className="mx-auto h-16 w-16 flex items-center justify-center rounded-full bg-green-100">
            <svg className="h-10 w-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>
        
        <h3 className="text-xl font-bold text-gray-900 mb-2">
          ✅ Email vérifié avec succès !
        </h3>
        
        <p className="text-gray-600 mb-4">
          {email ? `Votre adresse ${email} a été confirmée.` : 'Votre adresse email a été confirmée.'}
        </p>

        <p className="text-sm text-gray-500 mb-6">
          Vous pouvez maintenant vous connecter à votre compte Intelia Expert.
        </p>

        <div className="flex justify-center mb-4">
          <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full"></div>
        </div>

        <p className="text-xs text-gray-500 mb-6">
          Redirection automatique dans 5 secondes...
        </p>

        <div className="space-y-3">
          <Link 
            href="/"
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
          >
            Se connecter maintenant
          </Link>
        </div>
      </div>
    </div>
  )
}

// ==================== PAGE ERREUR VÉRIFICATION ====================
const VerificationErrorPage = ({ error }: { error: string }) => (
  <div className="bg-white py-8 px-6 shadow-lg rounded-lg border border-red-200">
    <div className="text-center">
      <div className="mb-4">
        <div className="mx-auto h-16 w-16 flex items-center justify-center rounded-full bg-red-100">
          <svg className="h-10 w-10 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
      </div>
      
      <h3 className="text-xl font-bold text-gray-900 mb-2">
        ❌ Erreur de vérification
      </h3>
      
      <p className="text-red-600 mb-6">
        {error}
      </p>

      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <h4 className="text-sm font-medium text-red-800 mb-2">
          Causes possibles :
        </h4>
        <ul className="text-sm text-red-700 list-disc list-inside space-y-1">
          <li>Le lien a expiré (plus de 24h)</li>
          <li>Le lien a déjà été utilisé</li>
          <li>Le lien est invalide ou corrompu</li>
        </ul>
      </div>

      <div className="space-y-3">
        <Link 
          href="/?signup=true"
          className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
        >
          Recommencer l'inscription
        </Link>
        
        <Link 
          href="/"
          className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
        >
          Retour à la connexion
        </Link>
      </div>
    </div>
  </div>
)

// ==================== PAGE EN ATTENTE ====================
const PendingVerificationPage = ({ email }: { email?: string }) => (
  <div className="bg-white py-8 px-6 shadow-lg rounded-lg border border-gray-200">
    <div className="text-center">
      <div className="mb-4">
        <div className="mx-auto h-16 w-16 flex items-center justify-center rounded-full bg-blue-100">
          <svg className="h-10 w-10 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
      </div>
      
      <h3 className="text-xl font-bold text-gray-900 mb-2">
        📧 Vérification email en attente
      </h3>
      
      <p className="text-gray-600 mb-4">
        {email ? 
          `Un email de confirmation a été envoyé à ${email}` : 
          'Un email de confirmation vous a été envoyé'
        }
      </p>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <h4 className="text-sm font-medium text-blue-800 mb-2">
          Prochaines étapes :
        </h4>
        <ol className="text-sm text-blue-700 list-decimal list-inside space-y-1">
          <li>Consultez votre boîte email</li>
          <li>Cliquez sur le lien de confirmation</li>
          <li>Revenez vous connecter</li>
        </ol>
      </div>

      <div className="space-y-3">
        <Link 
          href="/"
          className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
        >
          Retour à la connexion
        </Link>
        
        <button
          onClick={() => window.location.reload()}
          className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
        >
          Rafraîchir la page
        </button>
      </div>
    </div>
  </div>
)

// ==================== CONTENU PRINCIPAL ====================
function VerifyEmailPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { isAuthenticated, user } = useAuthStore()
  
  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'pending'>('loading')
  const [message, setMessage] = useState('')
  const [email, setEmail] = useState<string | null>(null)

  // 🔄 Redirection si déjà connecté
  useEffect(() => {
    if (isAuthenticated && user) {
      console.log('✅ [VerifyEmail] Utilisateur déjà connecté, redirection...')
      router.push('/chat')
    }
  }, [isAuthenticated, user, router])

  useEffect(() => {
    const verifyEmail = async () => {
      // Extraire les paramètres de l'URL
      const token = searchParams.get('token')
      const confirmationUrl = searchParams.get('confirmation_url') // Supabase style
      const emailParam = searchParams.get('email')
      const type = searchParams.get('type') // Peut être 'signup' ou autre
      
      console.log('🔍 [VerifyEmail] Paramètres URL:', { token, confirmationUrl, emailParam, type })
      
      setEmail(emailParam)

      // Si pas de token, afficher page en attente
      if (!token && !confirmationUrl) {
        console.log('📧 [VerifyEmail] Pas de token - page en attente')
        setStatus('pending')
        setMessage(emailParam ? 
          `Un email de confirmation a été envoyé à ${emailParam}` : 
          'Vérifiez votre email pour confirmer votre compte.'
        )
        return
      }

      // Vérification
      const finalToken = token || confirmationUrl
      
      try {
        console.log('🔄 [VerifyEmail] Vérification en cours...')
        setMessage('Vérification en cours...')
        
        // 🔧 APPEL API pour vérifier l'email
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app/api'}/v1/auth/verify-email`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            token: finalToken,
            type: type || 'signup'
          })
        })

        if (response.ok) {
          const data = await response.json()
          console.log('✅ [VerifyEmail] Vérification réussie')
          
          setStatus('success')
          setMessage('Email vérifié avec succès !')
          setEmail(data.email || emailParam)
          
        } else {
          const errorData = await response.json().catch(() => ({}))
          console.log('❌ [VerifyEmail] Vérification échouée:', errorData)
          
          setStatus('error')
          
          // Messages d'erreur spécifiques
          if (response.status === 400) {
            setMessage('Le lien de vérification est invalide ou a expiré.')
          } else if (response.status === 409) {
            setMessage('Cette adresse email est déjà vérifiée.')
          } else {
            setMessage(errorData.detail || 'Erreur lors de la vérification de l\'email.')
          }
        }
        
      } catch (error) {
        console.error('❌ [VerifyEmail] Erreur réseau:', error)
        setStatus('error')
        setMessage('Problème de connexion. Vérifiez votre connexion internet.')
      }
    }

    verifyEmail()
  }, [searchParams])

  // 🚀 Si l'utilisateur est connecté, redirection
  if (isAuthenticated && user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Redirection en cours...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <InteliaLogo className="w-12 h-12" />
          </div>
          <h2 className="text-3xl font-bold text-gray-900">
            Vérification Email
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Intelia Expert - Assistant IA spécialisé
          </p>
        </div>

        {/* Contenu conditionnel selon le statut */}
        {status === 'loading' && (
          <div className="bg-white py-8 px-6 shadow-lg rounded-lg border border-gray-200">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">{message}</p>
            </div>
          </div>
        )}

        {status === 'success' && <VerificationSuccessPage email={email || undefined} />}
        {status === 'error' && <VerificationErrorPage error={message} />}
        {status === 'pending' && <PendingVerificationPage email={email || undefined} />}

        {/* Footer informatif */}
        <div className="text-center">
          <p className="text-xs text-gray-500">
            Vous n'avez pas reçu d'email ? Vérifiez vos spams ou{' '}
            <Link href="/?signup=true" className="text-blue-600 hover:text-blue-500 font-medium">
              réessayez l'inscription
            </Link>
          </p>
        </div>

        {/* Support */}
        <div className="p-3 bg-gray-50 rounded-lg text-center">
          <p className="text-xs text-gray-600">
            Problème avec la vérification ?{' '}
            <button
              type="button"
              onClick={() => window.open('mailto:support@intelia.com?subject=Problème vérification email', '_blank')}
              className="text-blue-600 hover:underline font-medium transition-colors"
            >
              Contactez le support
            </button>
          </p>
        </div>

        {/* Debug en développement */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-4 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
            <strong>🔧 Dev Debug:</strong>
            <br />• Status: {status}
            <br />• Email: {email || 'Non défini'}
            <br />• Message: {message}
            <br />• API URL: {process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app/api'}
          </div>
        )}
      </div>
    </div>
  )
}

// ==================== EXPORT PRINCIPAL AVEC SUSPENSE ====================
export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-blue-100 mb-4">
            <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement de la vérification...</p>
        </div>
      </div>
    }>
      <VerifyEmailPageContent />
    </Suspense>
  )
}