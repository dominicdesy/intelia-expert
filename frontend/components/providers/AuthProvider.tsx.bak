'use client'

import { useEffect, useRef } from 'react'
import { usePathname } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { checkAuth, isLoading } = useAuthStore()
  const pathname = usePathname()

  // 🛡️ PROTECTION ANTI-BOUCLE
  const hasCheckedAuth = useRef(false)
  const lastPathname = useRef('')

  // ✅ Pages publiques où on ne doit PAS vérifier l'auth
  const isPublicPage = [
    '/',                    // Page d'accueil/login
    '/auth/login',         // Page de login
    '/auth/register',      // Page d'inscription
    '/auth/signup',        // Page d'inscription alternative
    '/auth/callback',      // Callback OAuth
    '/auth/reset',         // Reset password
    '/terms',              // Conditions d'utilisation
    '/privacy'             // Politique de confidentialité
  ].includes(pathname) || pathname.startsWith('/auth/')

  useEffect(() => {
    // 🛡️ EMPÊCHER LA BOUCLE INFINIE
    if (isPublicPage) {
      console.log('ℹ️ [AuthProvider] Page publique détectée, skip auth check:', pathname)
      return
    }

    // 🛡️ Ne vérifier qu'UNE SEULE FOIS par changement de page
    if (hasCheckedAuth.current && lastPathname.current === pathname) {
      console.log('⚠️ [AuthProvider] Auth déjà vérifié pour cette page, skip')
      return
    }

    console.log('🔍 [AuthProvider] Vérification auth pour page protégée:', pathname)
    
    // Marquer comme vérifié
    hasCheckedAuth.current = true
    lastPathname.current = pathname

    // Vérifier l'auth avec un délai pour éviter les conflits
    const timeoutId = setTimeout(() => {
      checkAuth()
    }, 100)

    return () => {
      clearTimeout(timeoutId)
    }
  }, [pathname, isPublicPage]) // 🛡️ RETIRER checkAuth des dépendances !

  // 🛡️ Reset le flag quand on change de page
  useEffect(() => {
    if (lastPathname.current !== pathname) {
      hasCheckedAuth.current = false
    }
  }, [pathname])

  // ✅ Pas de loader sur les pages publiques
  if (isLoading && !isPublicPage) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Vérification de l'authentification...</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}