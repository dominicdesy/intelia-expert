'use client'

import { useEffect, useRef } from 'react'
import { useAuthStore } from '@/lib/stores/auth'
import { getSupabaseClient } from '@/lib/supabase/singleton'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { hasHydrated, setHasHydrated, initializeSession, checkAuth } = useAuthStore()
  
  // ✅ AJOUT MINIMAL : Protection race condition
  const isInitializingRef = useRef(false)

  // ✅ CONSERVÉ : Logique d'hydratation originale
  useEffect(() => {
    if (!hasHydrated) {
      setHasHydrated(true)
      console.log('✅ [AuthProvider] Store hydraté - Supabase auth')
      
      // ✅ CORRECTION MINIMALE : Protection contre double initialisation
      if (!isInitializingRef.current) {
        isInitializingRef.current = true
        
        // Initialiser la session au démarrage
        initializeSession().then((success) => {
          console.log('🔄 [AuthProvider] Session initialisée:', success ? 'succès' : 'échec')
          isInitializingRef.current = false
        }).catch((error) => {
          // ✅ CONSERVÉ : Gestion d'erreur originale
          console.error('❌ [AuthProvider] Erreur initialisation session:', error)
          isInitializingRef.current = false
        })
      }
    }
  }, [hasHydrated, setHasHydrated, initializeSession])

  // ✅ CONSERVÉ : Logique listener Supabase originale
  useEffect(() => {
    // 🔧 CONSERVÉ : SINGLETON: Récupérer l'instance unique au moment de l'utilisation
    const supabase = getSupabaseClient()
    
    // ✅ CONSERVÉ : Écouter les changements d'état d'authentification Supabase
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('🔄 [AuthProvider] Changement état Supabase:', event, !!session)
        
        try {
          switch (event) {
            case 'INITIAL_SESSION':
              // ✅ CORRECTION : Éviter conflit avec initializeSession()
              console.log('ℹ️ [AuthProvider] Événement Supabase non géré: INITIAL_SESSION')
              break
              
            case 'SIGNED_IN':
              console.log('✅ [AuthProvider] Utilisateur connecté')
              await checkAuth()
              break
              
            case 'SIGNED_OUT':
              console.log('🚪 [AuthProvider] Utilisateur déconnecté')
              useAuthStore.setState({ 
                user: null, 
                isAuthenticated: false,
                lastAuthCheck: Date.now()
              })
              break
              
            case 'TOKEN_REFRESHED':
              console.log('🔄 [AuthProvider] Token rafraîchi')
              await checkAuth()
              break
              
            case 'USER_UPDATED':
              console.log('👤 [AuthProvider] Utilisateur mis à jour')
              await checkAuth()
              break
              
            default:
              console.log('ℹ️ [AuthProvider] Événement Supabase non géré:', event)
          }
        } catch (error) {
          // ✅ CONSERVÉ : Gestion d'erreur dans les événements originale
          console.error('❌ [AuthProvider] Erreur traitement événement:', event, error)
        }
      }
    )

    // ✅ CONSERVÉ : Vérification périodique de la session avec singleton originale
    const intervalId = setInterval(async () => {
      try {
        const supabase = getSupabaseClient() // Singleton à chaque vérification
        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (error) {
          console.warn('⚠️ [AuthProvider] Erreur vérification session:', error)
          return
        }
        
        const isAuthenticated = useAuthStore.getState().isAuthenticated
        const hasSession = !!session
        
        // Si l'état local ne correspond pas à l'état Supabase
        if (isAuthenticated !== hasSession) {
          console.log('🔄 [AuthProvider] Synchronisation état auth nécessaire')
          await checkAuth()
        }
      } catch (error) {
        console.warn('⚠️ [AuthProvider] Erreur vérification périodique:', error)
      }
    }, 60000) // Vérifier toutes les minutes

    // ✅ CONSERVÉ : Nettoyage original
    return () => {
      subscription.unsubscribe()
      clearInterval(intervalId)
      console.log('🧹 [AuthProvider] Nettoyage subscription et interval')
    }
  }, [checkAuth])

  // ✅ CONSERVÉ : Return original
  return <>{children}</>
}