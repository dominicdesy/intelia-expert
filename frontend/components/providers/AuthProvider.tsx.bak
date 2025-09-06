'use client'

import { useEffect, useRef } from 'react'
import { useAuthStore } from '@/lib/stores/auth'
import { getSupabaseClient } from '@/lib/supabase/singleton'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { hasHydrated, setHasHydrated, checkAuth } = useAuthStore()

  // Protections contre courses et démontage
  const isMountedRef = useRef(true)
  const isLoggingOutRef = useRef(false)
  const subscriptionRef = useRef<any>(null)
  const logoutTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    isMountedRef.current = true
    const supabase = getSupabaseClient()

    // Hydrate le store une seule fois (sans init auto pour éviter les boucles)
    if (!hasHydrated && isMountedRef.current && !isLoggingOutRef.current) {
      setHasHydrated(true)
      console.log('[AuthProvider] Store hydraté - AUCUNE initialisation automatique')
    }

    // 🔔 Écoute des événements auth — IMPORTANT: ne pas ignorer INITIAL_SESSION
    const { data: sub } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('🔥 [DEBUG-AUTH] === ÉVÉNEMENT SUPABASE ===')
      console.log('🔥 [DEBUG-AUTH] Event:', event, 'Session:', !!session)
      console.log('🔥 [DEBUG-AUTH] isMountedRef:', isMountedRef.current)
      console.log('🔥 [DEBUG-AUTH] isLoggingOutRef:', isLoggingOutRef.current)

      try {
        switch (event) {
          case 'INITIAL_SESSION':
          case 'SIGNED_IN':
          case 'TOKEN_REFRESHED':
            if (!isLoggingOutRef.current) {
              await checkAuth()
            } else {
              console.log('🔥 [DEBUG-AUTH] Événement ignoré - déconnexion en cours')
            }
            break

          case 'USER_UPDATED':
            if (!isLoggingOutRef.current) {
              await checkAuth()
            }
            break

          case 'SIGNED_OUT':
            console.log('🔥 [DEBUG-AUTH] SIGNED_OUT - stratégie sans setState immédiat')
            isLoggingOutRef.current = true
            try {
              await checkAuth() // met à jour le store côté app
            } finally {
              if (logoutTimeoutRef.current) clearTimeout(logoutTimeoutRef.current)
              logoutTimeoutRef.current = setTimeout(() => {
                isLoggingOutRef.current = false
                console.log('🕐 [DEBUG-TIMEOUT-AUTH] Fin du blocage après 5s')
              }, 5000)
            }
            break

          default:
            console.log('🔥 [DEBUG-AUTH] Événement non géré:', event)
        }
      } catch (e) {
        console.error('[AuthProvider] Erreur dans onAuthStateChange:', e)
      }
    })

    subscriptionRef.current = sub

    return () => {
      isMountedRef.current = false
      isLoggingOutRef.current = false

      try {
        subscriptionRef.current?.subscription?.unsubscribe?.()
      } catch {}
      subscriptionRef.current = null

      if (logoutTimeoutRef.current) {
        clearTimeout(logoutTimeoutRef.current)
        logoutTimeoutRef.current = null
      }
    }
  }, [hasHydrated, setHasHydrated, checkAuth])

  return <>{children}</>
}
