'use client'

import { useEffect, useRef } from 'react'
import { useAuthStore } from '@/lib/stores/auth'
import { getSupabaseClient } from '@/lib/supabase/singleton'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { hasHydrated, setHasHydrated, initializeSession, checkAuth } = useAuthStore()
  
  // Protection race condition et démontage
  const isInitializingRef = useRef(false)
  const isMountedRef = useRef(true)
  const subscriptionRef = useRef<any>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  // Wrapper sécurisé pour checkAuth
  const safeCheckAuth = async () => {
    if (!isMountedRef.current) {
      console.log('[AuthProvider] checkAuth ignoré - composant démonté')
      return
    }
    try {
      await checkAuth()
    } catch (error) {
      console.error('[AuthProvider] Erreur checkAuth sécurisé:', error)
    }
  }

  // Wrapper sécurisé pour setState
  const safeSetState = (updates: any) => {
    if (!isMountedRef.current) {
      console.log('[AuthProvider] setState ignoré - composant démonté')
      return
    }
    useAuthStore.setState(updates)
  }

  // Logique d'hydratation avec protection
  useEffect(() => {
    if (!hasHydrated && isMountedRef.current) {
      setHasHydrated(true)
      console.log('[AuthProvider] Store hydraté - Supabase auth')
      
      if (!isInitializingRef.current) {
        isInitializingRef.current = true
        
        initializeSession().then((success) => {
          if (isMountedRef.current) {
            console.log('[AuthProvider] Session initialisée:', success ? 'succès' : 'échec')
          }
          isInitializingRef.current = false
        }).catch((error) => {
          if (isMountedRef.current) {
            console.error('[AuthProvider] Erreur initialisation session:', error)
          }
          isInitializingRef.current = false
        })
      }
    }
  }, [hasHydrated, setHasHydrated, initializeSession])

  // Listener Supabase avec protection complète
  useEffect(() => {
    let isCancelled = false
    
    const supabase = getSupabaseClient()
    
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (isCancelled || !isMountedRef.current) {
          console.log('[AuthProvider] Événement Supabase ignoré - composant démonté')
          return
        }
        
        console.log('[AuthProvider] Changement état Supabase:', event, !!session)
        
        try {
          switch (event) {
            case 'INITIAL_SESSION':
              console.log('[AuthProvider] Événement Supabase non géré: INITIAL_SESSION')
              break
              
            case 'SIGNED_IN':
              console.log('[AuthProvider] Utilisateur connecté')
              await safeCheckAuth()
              break
              
            case 'SIGNED_OUT':
              console.log('[AuthProvider] Utilisateur déconnecté')
              if (isMountedRef.current && !isCancelled) {
                safeSetState({ 
                  user: null, 
                  isAuthenticated: false,
                  lastAuthCheck: Date.now()
                })
              }
              break
              
            case 'TOKEN_REFRESHED':
              console.log('[AuthProvider] Token rafraîchi')
              await safeCheckAuth()
              break
              
            case 'USER_UPDATED':
              console.log('[AuthProvider] Utilisateur mis à jour')
              await safeCheckAuth()
              break
              
            default:
              console.log('[AuthProvider] Événement Supabase non géré:', event)
          }
        } catch (error) {
          if (isMountedRef.current) {
            console.error('[AuthProvider] Erreur traitement événement:', event, error)
          }
        }
      }
    )

    // Stocker la subscription pour nettoyage
    subscriptionRef.current = subscription

    // Vérification périodique avec protection
    const intervalId = setInterval(async () => {
      if (isCancelled || !isMountedRef.current) {
        return
      }
      
      try {
        const supabase = getSupabaseClient()
        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (error) {
          console.warn('[AuthProvider] Erreur vérification session:', error)
          return
        }
        
        if (!isMountedRef.current || isCancelled) {
          return
        }
        
        const isAuthenticated = useAuthStore.getState().isAuthenticated
        const hasSession = !!session
        
        if (isAuthenticated !== hasSession) {
          console.log('[AuthProvider] Synchronisation état auth nécessaire')
          await safeCheckAuth()
        }
      } catch (error) {
        if (isMountedRef.current) {
          console.warn('[AuthProvider] Erreur vérification périodique:', error)
        }
      }
    }, 60000)

    intervalRef.current = intervalId

    // Cleanup complet avec protection
    return () => {
      isCancelled = true
      
      if (subscriptionRef.current) {
        try {
          subscriptionRef.current.unsubscribe()
        } catch (error) {
          console.warn('[AuthProvider] Erreur unsubscribe:', error)
        }
      }
      
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
      
      console.log('[AuthProvider] Nettoyage subscription et interval')
    }
  }, [checkAuth])

  // Effect de démontage pour nettoyer les refs
  useEffect(() => {
    isMountedRef.current = true
    
    return () => {
      console.log('[AuthProvider] Démontage - nettoyage des refs')
      isMountedRef.current = false
      isInitializingRef.current = false
      
      // Nettoyage final des ressources
      if (subscriptionRef.current) {
        try {
          subscriptionRef.current.unsubscribe()
        } catch (error) {
          console.warn('[AuthProvider] Erreur final unsubscribe:', error)
        }
        subscriptionRef.current = null
      }
      
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [])

  return <>{children}</>
}