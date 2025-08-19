'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/lib/stores/auth'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { hasHydrated, setHasHydrated } = useAuthStore()

  useEffect(() => {
    if (!hasHydrated) {
      setHasHydrated(true)
      console.log('✅ [AuthProvider] Store hydraté - backend auth uniquement')
    }
  }, [hasHydrated, setHasHydrated])

  return <>{children}</>
}