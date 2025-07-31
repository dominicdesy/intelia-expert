// app/auth/callback/page.tsx - CALLBACK AUTHENTIFICATION SOCIALE
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'
import { supabase } from '@/lib/supabase/client'
import Image from 'next/image'

export default function AuthCallback() {
  const router = useRouter()
  const { initializeSession } = useAuthStore()

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        console.log('🔄 Traitement callback authentification...')
        
        // Gérer le callback d'authentification OAuth
        const { data, error } = await supabase.auth.getSession()
        
        if (error) {
          console.error('❌ Erreur callback auth:', error)
          router.push('/?error=auth_failed')
          return
        }

        if (data.session) {
          console.log('✅ Session callback trouvée, initialisation...')
          
          // Initialiser la session (cela va récupérer ou créer le profil)
          await initializeSession()
          
          // Rediriger vers le chat
          router.push('/chat')
        } else {
          console.log('❌ Aucune session dans callback, retour login')
          router.push('/')
        }
      } catch (error) {
        console.error('💥 Erreur traitement callback:', error)
        router.push('/?error=callback_failed')
      }
    }

    handleAuthCallback()
  }, [router, initializeSession])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center max-w-md">
        {/* Logo */}
        <Image
          src="/images/logo-intelia.png"
          alt="Intelia Expert"
          width={150}
          height={50}
          className="mx-auto mb-8"
          priority
        />
        
        {/* Animation de chargement */}
        <div className="mb-6">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-intelia-blue-600 mx-auto"></div>
        </div>
        
        {/* Messages */}
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Connexion en cours...
        </h2>
        <p className="text-gray-600 mb-4">
          Nous finalisons votre connexion, veuillez patienter.
        </p>
        
        {/* Indicateur de progression */}
        <div className="w-full bg-gray-200 rounded-full h-1.5 mb-4">
          <div className="bg-intelia-blue-600 h-1.5 rounded-full animate-pulse" style={{ width: '60%' }}></div>
        </div>
        
        <p className="text-xs text-gray-500">
          Si cette page ne se charge pas, <a href="/" className="text-intelia-blue-600 hover:underline">cliquez ici</a>
        </p>
      </div>
    </div>
  )
}