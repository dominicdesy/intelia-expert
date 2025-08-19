'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/lib/stores/auth'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { hasHydrated, setHasHydrated } = useAuthStore()

  useEffect(() => {
    // Marquer comme hydraté dès que possible
    if (!hasHydrated) {
      setHasHydrated(true)
      console.log('✅ [AuthProvider] Store hydraté - backend auth uniquement')
    }
  }, [hasHydrated, setHasHydrated])

  // 🔥 SUPPRESSION COMPLÈTE de toute la logique Supabase
  // 🔥 SUPPRESSION COMPLÈTE des vérifications d'auth automatiques
  // 🔥 SUPPRESSION COMPLÈTE des redirections automatiques
  // 🔥 SUPPRESSION COMPLÈTE des périodes de grâce
  
  // Chaque page gère maintenant sa propre authentification selon ses besoins
  // La page /chat/ utilise useAuthStore avec initializeSession()
  // Les pages publiques n'ont pas besoin d'auth
  
  return <>{children}</>
}

// 🗑️ SUPPRESSION du contexte AuthContext (plus nécessaire)
// 🗑️ SUPPRESSION de useAuthContext (plus nécessaire)