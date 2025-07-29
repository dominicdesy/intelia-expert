'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/lib/stores/auth'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { checkAuth, isLoading } = useAuthStore()

  useEffect(() => {
    // Vérifier l'authentification au chargement de l'app
    checkAuth()
  }, [checkAuth])

  // Optionnel: Afficher un loader pendant la vérification initiale
  if (isLoading) {
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