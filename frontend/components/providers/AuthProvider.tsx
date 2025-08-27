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
  // Flag pour empêcher les setState pendant la déconnexion
  const isLoggingOutRef = useRef(false)

  // Wrapper sécurisé pour checkAuth
  const safeCheckAuth = async () => {
    if (!isMountedRef.current || isLoggingOutRef.current) {
      console.log('[AuthProvider] checkAuth ignoré - composant démonté ou déconnexion en cours')
      return
    }
    try {
      await checkAuth()
    } catch (error) {
      if (isMountedRef.current) {
        console.error('[AuthProvider] Erreur checkAuth sécurisé:', error)
      }
    }
  }

  // CORRECTION: Wrapper sécurisé sans setTimeout pour éviter les race conditions
  const safeSetState = (updates: any) => {
    if (!isMountedRef.current || isLoggingOutRef.current) {
      console.log('[AuthProvider] setState ignoré - composant démonté ou déconnexion en cours')
      return
    }
    
    try {
      // SUPPRESSION du setTimeout - cause des setState après unmount
      useAuthStore.setState(updates)
    } catch (error) {
      console.warn('[AuthProvider] Erreur setState:', error)
    }
  }

  // Logique d'hydratation avec protection
  useEffect(() => {
    if (!hasHydrated && isMountedRef.current && !isLoggingOutRef.current) {
      setHasHydrated(true)
      console.log('[AuthProvider] Store hydraté - Supabase auth')
      
      if (!isInitializingRef.current) {
        isInitializingRef.current = true
        
        initializeSession().then((success) => {
          if (isMountedRef.current && !isLoggingOutRef.current) {
            console.log('[AuthProvider] Session initialisée:', success ? 'succès' : 'échec')
          }
          isInitializingRef.current = false
        }).catch((error) => {
          if (isMountedRef.current && !isLoggingOutRef.current) {
            console.error('[AuthProvider] Erreur initialisation session:', error)
          }
          isInitializingRef.current = false
        })
      }
    }
  }, [hasHydrated, setHasHydrated, initializeSession])

  // Listener Supabase avec protection complète et détection de déconnexion
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
        
        // Détecter le début de la déconnexion
        if (event === 'SIGNED_OUT' || (event === 'SIGNED_IN' && !session)) {
          isLoggingOutRef.current = true
          console.log('[AuthProvider] Déconnexion détectée - blocage des setState')
        }
        
        try {
          switch (event) {
            case 'INITIAL_SESSION':
              console.log('[AuthProvider] Événement Supabase non géré: INITIAL_SESSION')
              break
              
            case 'SIGNED_IN':
              if (!isLoggingOutRef.current) {
                console.log('[AuthProvider] Utilisateur connecté')
                await safeCheckAuth()
              }
              break
              
            case 'SIGNED_OUT':
              console.log('[AuthProvider] Utilisateur déconnecté')
              // Pour SIGNED_OUT, setState direct puis blocage total
              if (isMountedRef.current && !isCancelled) {
                try {
                  useAuthStore.setState({ 
                    user: null, 
                    isAuthenticated: false,
                    lastAuthCheck: Date.now()
                  })
                  console.log('[AuthProvider] État déconnexion appliqué')
                } catch (error) {
                  console.warn('[AuthProvider] Erreur setState final:', error)
                }
              }
              // Bloquer tous les setState suivants
              isLoggingOutRef.current = true
              break
              
            case 'TOKEN_REFRESHED':
              if (!isLoggingOutRef.current) {
                console.log('[AuthProvider] Token rafraîchi')
                await safeCheckAuth()
              }
              break
              
            case 'USER_UPDATED':
              if (!isLoggingOutRef.current) {
                console.log('[AuthProvider] Utilisateur mis à jour')
                await safeCheckAuth()
              }
              break
              
            default:
              console.log('[AuthProvider] Événement Supabase non géré:', event)
          }
        } catch (error) {
          if (isMountedRef.current && !isLoggingOutRef.current) {
            console.error('[AuthProvider] Erreur traitement événement:', event, error)
          }
        }
      }
    )

    // Stocker la subscription pour nettoyage
    subscriptionRef.current = subscription

    // Vérification périodique avec protection renforcée
    const intervalId = setInterval(async () => {
      if (isCancelled || !isMountedRef.current || isLoggingOutRef.current) {
        return
      }
      
      try {
        const supabase = getSupabaseClient()
        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (error) {
          console.warn('[AuthProvider] Erreur vérification session:', error)
          return
        }
        
        if (!isMountedRef.current || isCancelled || isLoggingOutRef.current) {
          return
        }
        
        const isAuthenticated = useAuthStore.getState().isAuthenticated
        const hasSession = !!session
        
        if (isAuthenticated !== hasSession) {
          console.log('[AuthProvider] Synchronisation état auth nécessaire')
          await safeCheckAuth()
        }
      } catch (error) {
        if (isMountedRef.current && !isLoggingOutRef.current) {
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
    isLoggingOutRef.current = false
    
    return () => {
      console.log('[AuthProvider] Démontage - nettoyage des refs')
      isMountedRef.current = false
      isInitializingRef.current = false
      isLoggingOutRef.current = true // Bloquer définitivement les setState
      
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