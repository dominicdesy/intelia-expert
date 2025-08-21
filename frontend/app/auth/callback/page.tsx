'use client'
// app/auth/callback/page.tsx - Page pour gérer les invitations Supabase (fragments #)

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getSupabaseClient } from '@/lib/supabase/singleton'

export default function AuthCallbackPage() {
  const router = useRouter()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')
  const [userInfo, setUserInfo] = useState<any>(null)

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        console.log('🔐 [AuthCallback] Début traitement callback')
        
        const supabase = getSupabaseClient()
        
        // Vérifier s'il y a des fragments d'auth dans l'URL
        const hash = window.location.hash
        console.log('🔍 [AuthCallback] Hash URL:', hash ? 'présent' : 'absent')
        
        if (hash && (hash.includes('access_token') || hash.includes('type=invite'))) {
          console.log('📧 [AuthCallback] Invitation détectée dans URL')
          setMessage('Finalisation de votre invitation...')
          
          // Supabase va automatiquement traiter les tokens du hash
          const { data: sessionData, error: sessionError } = await supabase.auth.getSession()
          
          if (sessionError) {
            console.error('❌ [AuthCallback] Erreur session:', sessionError)
            throw new Error(`Erreur d'authentification: ${sessionError.message}`)
          }
          
          if (sessionData.session) {
            console.log('✅ [AuthCallback] Session créée:', sessionData.session.user.email)
            
            // Extraire les métadonnées d'invitation
            const userMetadata = sessionData.session.user.user_metadata
            console.log('📋 [AuthCallback] Métadonnées utilisateur:', userMetadata)
            
            setUserInfo({
              email: sessionData.session.user.email,
              invitedBy: userMetadata?.inviter_name || userMetadata?.invited_by,
              invitationDate: userMetadata?.invitation_date,
              personalMessage: userMetadata?.personal_message,
              language: userMetadata?.language || 'fr'
            })
            
            setStatus('success')
            setMessage('Invitation acceptée avec succès !')
            
            // Nettoyer l'URL en supprimant les fragments
            window.history.replaceState({}, document.title, window.location.pathname)
            
            // Redirection vers le chat après 3 secondes
            setTimeout(() => {
              console.log('🚀 [AuthCallback] Redirection vers chat')
              router.push('/chat')
            }, 3000)
            
          } else {
            throw new Error('Aucune session créée après traitement de l\'invitation')
          }
          
        } else {
          // Pas de fragments d'auth, vérifier s'il y a une session existante
          console.log('🔍 [AuthCallback] Pas d\'invitation, vérification session existante')
          
          const { data: existingSession } = await supabase.auth.getSession()
          
          if (existingSession.session) {
            console.log('✅ [AuthCallback] Session existante trouvée')
            setStatus('success')
            setMessage('Vous êtes déjà connecté !')
            setTimeout(() => router.push('/chat'), 1500)
          } else {
            console.log('ℹ️ [AuthCallback] Aucune session, redirection vers login')
            setStatus('error')
            setMessage('Aucune invitation trouvée')
            setTimeout(() => router.push('/auth/login'), 2000)
          }
        }
        
      } catch (error) {
        console.error('❌ [AuthCallback] Erreur traitement:', error)
        setStatus('error')
        
        if (error instanceof Error) {
          setMessage(error.message)
        } else {
          setMessage('Erreur lors du traitement de votre invitation')
        }
        
        // Redirection vers login après erreur
        setTimeout(() => {
          router.push('/auth/login?error=' + encodeURIComponent(
            error instanceof Error ? error.message : 'Erreur d\'invitation'
          ))
        }, 4000)
      }
    }

    // Délai pour laisser Supabase traiter les fragments
    const timer = setTimeout(handleAuthCallback, 500)
    return () => clearTimeout(timer)
  }, [router])

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Logo Intelia */}
        <div className="flex justify-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-lg flex items-center justify-center">
            <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zM3 19.235v-.11a6.375 6.375 0 0112.75 0v.109A12.318 12.318 0 019.374 21c-2.331 0-4.512-.645-6.374-1.766z" />
            </svg>
          </div>
        </div>
        
        <h1 className="text-center text-3xl font-bold text-gray-900 mb-2">
          Intelia Expert
        </h1>
        <p className="text-center text-sm text-gray-600 mb-8">
          Finalisation de votre invitation
        </p>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
          
          {/* Statut Loading */}
          {status === 'loading' && (
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Traitement en cours...
              </h2>
              <p className="text-sm text-gray-600">
                {message || 'Finalisation de votre invitation'}
              </p>
            </div>
          )}

          {/* Statut Success */}
          {status === 'success' && (
            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              
              <h2 className="text-lg font-semibold text-green-900 mb-4">
                {message}
              </h2>
              
              {userInfo && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4 text-left">
                  <h3 className="font-medium text-green-900 mb-2">Bienvenue !</h3>
                  <div className="text-sm text-green-800 space-y-1">
                    <p><strong>Email :</strong> {userInfo.email}</p>
                    {userInfo.invitedBy && (
                      <p><strong>Invité par :</strong> {userInfo.invitedBy}</p>
                    )}
                    {userInfo.personalMessage && (
                      <div className="mt-2 p-2 bg-white rounded border">
                        <p className="text-xs text-gray-600 mb-1">Message personnel :</p>
                        <p className="text-sm italic">"{userInfo.personalMessage}"</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              <div className="text-sm text-gray-600">
                <p>Redirection vers votre tableau de bord...</p>
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-green-600 h-2 rounded-full animate-pulse" style={{width: '100%'}}></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Statut Error */}
          {status === 'error' && (
            <div className="text-center">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
              </div>
              
              <h2 className="text-lg font-semibold text-red-900 mb-2">
                Erreur de traitement
              </h2>
              <p className="text-sm text-red-700 mb-4">
                {message}
              </p>
              
              <div className="text-xs text-gray-600">
                Redirection vers la page de connexion...
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="mt-8 pt-4 border-t border-gray-200">
            <p className="text-xs text-gray-500 text-center">
              Besoin d'aide ? Contactez-nous à support@intelia.com
            </p>
          </div>
          
        </div>
      </div>
    </div>
  )
}