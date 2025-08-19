'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/lib/stores/auth'
import { supabase } from '@/lib/supabase/client'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { hasHydrated, setHasHydrated, initializeSession, checkAuth } = useAuthStore()

  useEffect(() => {
    if (!hasHydrated) {
      setHasHydrated(true)
      console.log('✅ [AuthProvider] Store hydraté - Supabase auth')
      
      // Initialiser la session au démarrage
      initializeSession().then((success) => {
        console.log('🔄 [AuthProvider] Session initialisée:', success ? 'succès' : 'échec')
      }).catch((error) => {
        // ✅ AMÉLIORATION: Gestion d'erreur
        console.error('❌ [AuthProvider] Erreur initialisation session:', error)
      })
    }
  }, [hasHydrated, setHasHydrated, initializeSession])

  useEffect(() => {
    // 🆕 NOUVEAU: Écouter les changements d'état d'authentification Supabase
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('🔄 [AuthProvider] Changement état Supabase:', event, !!session)
        
        try {
          switch (event) {
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
          // ✅ AMÉLIORATION: Gestion d'erreur dans les événements
          console.error('❌ [AuthProvider] Erreur traitement événement:', event, error)
        }
      }
    )

    // 🆕 NOUVEAU: Vérification périodique de la session
    const intervalId = setInterval(async () => {
      try {
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

    // Nettoyage
    return () => {
      subscription.unsubscribe()
      clearInterval(intervalId)
      console.log('🧹 [AuthProvider] Nettoyage subscription et interval')
    }
  }, [checkAuth])

  return <>{children}</>
}