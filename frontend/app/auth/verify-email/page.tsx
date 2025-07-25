'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'

export default function VerifyEmailPage() {
  const [message, setMessage] = useState('')
  const searchParams = useSearchParams()

  useEffect(() => {
    // Vérifier si il y a un token dans l'URL
    const token = searchParams.get('token')
    const email = searchParams.get('email')
    
    if (token) {
      setMessage('Vérification en cours...')
      // Ici on pourrait vérifier le token avec Supabase
    } else if (email) {
      setMessage(`Un email de confirmation a été envoyé à ${email}`)
    } else {
      setMessage('Vérifiez votre email pour confirmer votre compte.')
    }
  }, [searchParams])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-blue-100">
            <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Vérification Email
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Intelia Expert - Assistant IA spécialisé
          </p>
        </div>

        <div className="bg-white py-8 px-6 shadow rounded-lg">
          <div className="text-center">
            <div className="mb-4">
              <div className="mx-auto h-16 w-16 flex items-center justify-center rounded-full bg-green-100">
                <svg className="h-10 w-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
            
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Compte créé avec succès !
            </h3>
            
            <p className="text-gray-600 mb-6">
              {message}
            </p>

            <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-6">
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
                href="/auth/login"
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                Retour à la connexion
              </Link>
              
              <Link 
                href="/"
                className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                Retour à l'accueil
              </Link>
            </div>
          </div>
        </div>

        <div className="text-center">
          <p className="text-xs text-gray-500">
            Vous n'avez pas reçu d'email ? Vérifiez vos spams ou{' '}
            <Link href="/auth/signup" className="text-blue-600 hover:text-blue-500">
              réessayez l'inscription
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}