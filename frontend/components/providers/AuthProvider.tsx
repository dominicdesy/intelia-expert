'use client'

import { useEffect } from 'react'
import { usePathname } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { checkAuth, isLoading } = useAuthStore()
  const pathname = usePathname()

  // ✅ Pages publiques où on ne doit PAS vérifier l'auth
  const isPublicPage = [
    '/',                    // Page d'accueil/login
    '/auth/login',         // Page de login
    '/auth/register',      // Page d'inscription
    '/auth/callback',      // Callback OAuth
    '/auth/reset',         // Reset password
    '/terms',              // Conditions d'utilisation
    '/privacy'             // Politique de confidentialité
  ].includes(pathname) || pathname.startsWith('/auth/')

  useEffect(() => {
    // ✅ Ne vérifier l'auth QUE sur les pages protégées
    if (!isPublicPage) {
      console.log('🔍 [AuthProvider] Vérification auth pour page protégée:', pathname)
      checkAuth()
    } else {
      console.log('ℹ️ [AuthProvider] Page publique détectée, skip auth check:', pathname)
    }
  }, [checkAuth, isPublicPage, pathname])

  // ✅ Pas de loader sur les pages publiques
  if (isLoading && !isPublicPage) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement...</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}