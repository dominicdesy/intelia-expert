// AuthProvider.tsx - Version simplifiée
'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { hasHydrated, setHasHydrated, checkAuth, isAuthenticated } = useAuthStore()

  // Initialisation unique
  useEffect(() => {
    if (!hasHydrated) {
      setHasHydrated(true)
      checkAuth() // Vérifie via /auth/me
    }
  }, [hasHydrated, setHasHydrated, checkAuth])

  // Gestion des redirections
  useEffect(() => {
    if (!hasHydrated) return

    const publicRoutes = ['/', '/auth/login', '/auth/signup', '/auth/forgot-password', '/auth/reset-password', '/privacy', '/terms']
    
    if (isAuthenticated && publicRoutes.includes(pathname)) {
      router.push('/chat')
    }
  }, [isAuthenticated, pathname, hasHydrated, router])

  return <>{children}</>
}