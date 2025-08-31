'use client'

import { useEffect, useRef } from 'react'
import { useAuthStore } from '@/lib/stores/auth'
import { getSupabaseClient } from '@/lib/supabase/singleton'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { hasHydrated, setHasHydrated, checkAuth } = useAuthStore()
  
  // Protection race condition et démontage
  const isMountedRef = useRef(true)
  const subscriptionRef = useRef<any>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  
  // CORRECTION CRITIQUE: Flag pour bloquer TOUS les setState pendant déconnexion
  const isLoggingOutRef = useRef(false)
  const logoutTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Wrapper sécurisé pour checkAuth
  const safeCheckAuth = async () => {
    if (!isMountedRef.current || isLoggingOutRef.current) {
      console.log('[AuthProvider] checkAuth ignoré - composant démonté ou déconnexion en cours')
      return
    }
    try {
      await checkAuth()
    } catch (error) {
      if (isMountedRef.current && !isLoggingOutRef.current) {
        console.error('[AuthProvider] Erreur checkAuth sécurisé:', error)
      }
    }
  }

  // Logique d'hydratation SANS initialisation automatique pour éviter la boucle
  useEffect(() => {
    // Vérifier si une déconnexion récente est en cours
    const recentLogout = sessionStorage.getItem('recent-logout')
    if (recentLogout) {
      const logoutTime = parseInt(recentLogout)
      if (Date.now() - logoutTime < 5000) {
        console.log('[AuthProvider] Initialisation différée - déconnexion récente')
        return
      }
    }

    if (!hasHydrated && isMountedRef.current && !isLoggingOutRef.current) {
      setHasHydrated(true)
      console.log('[AuthProvider] Store hydraté - AUCUNE initialisation automatique')
      
      // SUPPRESSION COMPLÈTE de l'appel à initializeSession() qui causait la boucle
      // La page chat gère maintenant sa propre initialisation
    }
  }, [hasHydrated, setHasHydrated])

  // CORRECTION FINALE: Listener Supabase qui NE FAIT PLUS DE setState pour SIGNED_OUT
  useEffect(() => {
    let isCancelled = false
    
    const supabase = getSupabaseClient()
    
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('🔥 [DEBUG-AUTH] === ÉVÉNEMENT SUPABASE ===')
        console.log('🔥 [DEBUG-AUTH] Event:', event, 'Session:', !!session)
        console.log('🔥 [DEBUG-AUTH] isMountedRef:', isMountedRef.current)
        console.log('🔥 [DEBUG-AUTH] isLoggingOutRef:', isLoggingOutRef.current)
        console.log('🔥 [DEBUG-AUTH] isCancelled:', isCancelled)
        
        if (isCancelled || !isMountedRef.current || isLoggingOutRef.current) {
          console.log('🔥 [DEBUG-AUTH] ÉVÉNEMENT IGNORÉ - composant démonté ou déconnexion active')
          return
        }
        
        console.log('🔥 [DEBUG-AUTH] Traitement de l\'événement:', event)
        
        try {
          switch (event) {
            case 'INITIAL_SESSION':
              console.log('🔥 [DEBUG-AUTH] INITIAL_SESSION ignoré')
              break
              
            case 'SIGNED_IN':
              console.log('🔥 [DEBUG-AUTH] SIGNED_IN - vérification état...')
              if (!isLoggingOutRef.current) {
                console.log('🔥 [DEBUG-AUTH] Utilisateur connecté - checkAuth')
                await safeCheckAuth()
              } else {
                console.log('🔥 [DEBUG-AUTH] SIGNED_IN ignoré - déconnexion en cours')
              }
              break
              
            case 'SIGNED_OUT':
              console.log('🔥 [DEBUG-AUTH] SIGNED_OUT - NOUVELLE STRATÉGIE SANS setState')
              
              // CORRECTION FINALE: NE PLUS FAIRE DE setState ICI
              // Cette ligne causait React #300 car elle s'exécutait pendant le démontage
              // useAuthStore.setState({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() })
              
              // À la place, juste marquer le flag et laisser le store gérer
              isLoggingOutRef.current = true
              
              console.log('🔥 [DEBUG-AUTH] SIGNED_OUT traité - PAS de setState, juste flag activé')
              
              // Le timeout reste pour débloquer après sécurité
              if (logoutTimeoutRef.current) {
                clearTimeout(logoutTimeoutRef.current)
              }

              logoutTimeoutRef.current = setTimeout(() => {
                console.log('🕐 [DEBUG-TIMEOUT-AUTH] Execution timeout 5s - isMounted:', isMountedRef.current)
                if (isMountedRef.current) {
                  console.log('🔥 [DEBUG-AUTH] Fin du blocage après 5s')
                } else {
                  console.log('⚠️ [DEBUG-TIMEOUT-AUTH] Timeout 5s ignoré - AuthProvider démonté')
                }
              }, 5000)
              
              break
              
            case 'TOKEN_REFRESHED':
              if (!isLoggingOutRef.current) {
                console.log('🔥 [DEBUG-AUTH] Token rafraîchi')
                await safeCheckAuth()
              } else {
                console.log('🔥 [DEBUG-AUTH] TOKEN_REFRESHED ignoré - déconnexion en cours')
              }
              break
              
            case 'USER_UPDATED':
              if (!isLoggingOutRef.current) {
                console.log('🔥 [DEBUG-AUTH] Utilisateur mis à jour')
                await safeCheckAuth()
              } else {
                console.log('🔥 [DEBUG-AUTH] USER_UPDATED ignoré - déconnexion en cours')
              }
              break
              
            default:
              console.log('🔥 [DEBUG-AUTH] Événement non géré:', event)
          }
        } catch (error) {
          if (isMountedRef.current && !isLoggingOutRef.current) {
            console.error('🔥 [DEBUG-AUTH] Erreur traitement événement:', event, error)
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
        
        // Vérification synchronisation avec le store
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
      
      if (logoutTimeoutRef.current) {
        clearTimeout(logoutTimeoutRef.current)
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
      
      if (logoutTimeoutRef.current) {
        clearTimeout(logoutTimeoutRef.current)
        logoutTimeoutRef.current = null
      }
    }
  }, [])