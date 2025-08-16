'use client'

import { useEffect, useRef, useState } from 'react'
import { usePathname } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { checkAuth, isLoading, hasHydrated, isAuthenticated } = useAuthStore()
  const pathname = usePathname()

  // 🔥 PROTECTION ANTI-BOUCLE RENFORCÉE
  const authCheckLock = useRef(false)
  const lastPathname = useRef('')
  const [isInitialized, setIsInitialized] = useState(false)

  // ✅ Pages publiques où on ne doit PAS vérifier l'auth
  const publicRoutes = [
    '/',
    '/auth',
    '/auth/login',
    '/auth/register', 
    '/auth/signup',
    '/auth/callback',
    '/auth/reset',
    '/auth/forgot-password',
    '/terms',
    '/privacy'
  ]

  const isPublicPage = publicRoutes.some(route => 
    pathname === route || pathname.startsWith(route + '/')
  ) || pathname.startsWith('/auth/')

  // 🚨 PAGES PROTÉGÉES - Nécessitent authentification
  const protectedRoutes = ['/chat', '/dashboard', '/profile', '/settings']
  const isProtectedPage = protectedRoutes.some(route => 
    pathname === route || pathname.startsWith(route + '/')
  )

  // 🔥 INITIALISATION UNE SEULE FOIS
  useEffect(() => {
    if (!hasHydrated || isInitialized) {
      return
    }

    console.log('🔧 [AuthProvider] Initialisation provider')
    setIsInitialized(true)
  }, [hasHydrated, isInitialized])

  // 🔥 VÉRIFICATION AUTH PROTÉGÉE
  useEffect(() => {
    // Attendre l'initialisation
    if (!isInitialized || !hasHydrated) {
      return
    }

    // Skip si page publique
    if (isPublicPage) {
      console.log('ℹ️ [AuthProvider] Page publique détectée, skip auth check:', pathname)
      authCheckLock.current = false // Reset le lock pour les pages publiques
      return
    }

    // Skip si pas une page protégée
    if (!isProtectedPage) {
      console.log('ℹ️ [AuthProvider] Page non protégée, skip:', pathname)
      return
    }

    // 🛡️ PROTECTION CONTRE MULTIPLES APPELS
    if (authCheckLock.current && lastPathname.current === pathname) {
      console.log('⚠️ [AuthProvider] Auth déjà vérifié pour cette page, skip')
      return
    }

    // 🔥 NOUVEAU: Si déjà authentifié sur une page protégée, pas besoin de re-vérifier
    if (isAuthenticated && lastPathname.current === pathname) {
      console.log('✅ [AuthProvider] Utilisateur déjà authentifié, skip verification')
      return
    }

    console.log('🔍 [AuthProvider] Vérification auth pour page protégée:', pathname)
    
    // Marquer comme en cours de vérification
    authCheckLock.current = true
    lastPathname.current = pathname

    // Vérifier l'auth avec délai pour éviter conflits
    const timeoutId = setTimeout(() => {
      checkAuth().finally(() => {
        // 🔥 IMPORTANT: Reset le lock après vérification
        authCheckLock.current = false
      })
    }, 100)

    return () => {
      clearTimeout(timeoutId)
    }
  }, [
    pathname, 
    isPublicPage, 
    isProtectedPage, 
    checkAuth, 
    isInitialized, 
    hasHydrated,
    isAuthenticated // 🔥 AJOUTÉ: Surveiller l'état d'auth
  ])

  // 🔥 RESET DES FLAGS LORS DU CHANGEMENT DE PAGE
  useEffect(() => {
    if (lastPathname.current !== pathname) {
      console.log('🔄 [AuthProvider] Changement de page:', lastPathname.current, '→', pathname)
      
      // Reset seulement si on change vraiment de page
      if (lastPathname.current !== '') {
        authCheckLock.current = false
      }
    }
  }, [pathname])

  // 🔥 LOADING STATE AMÉLIORÉ
  if (!hasHydrated || !isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Initialisation...</p>
        </div>
      </div>
    )
  }

  // ✅ Loader seulement si on charge ET qu'on est sur une page protégée
  if (isLoading && isProtectedPage && !isPublicPage) {
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