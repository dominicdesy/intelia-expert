// hooks/useAuthStore.ts - DÉCONNEXION CORRIGÉE SANS ERREUR

import { useState, useEffect, useRef } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { User, AuthStore, ProfileUpdateData } from '../types'

const supabase = createClientComponentClient()

export const useAuthStore = (): AuthStore => {
  const [user, setUser] = useState<User | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  
  // ✅ REF POUR ÉVITER LES ACTIONS APRÈS UNMOUNT
  const isMountedRef = useRef(true)
  const isLoggingOutRef = useRef(false)

  useEffect(() => {
    isMountedRef.current = true
    
    return () => {
      isMountedRef.current = false
    }
  }, [])

  useEffect(() => {
    const loadUser = async () => {
      try {
        // ✅ VÉRIFIER SI LE COMPOSANT EST TOUJOURS MONTÉ
        if (!isMountedRef.current || isLoggingOutRef.current) return

        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (error) {
          console.error('❌ Erreur récupération session:', error)
          if (isMountedRef.current && !isLoggingOutRef.current) {
            setIsAuthenticated(false)
            setIsLoading(false)
          }
          return
        }

        if (session?.user && isMountedRef.current && !isLoggingOutRef.current) {
          console.log('✅ Utilisateur connecté:', session.user.email)
          
          const userData: User = {
            id: session.user.id,
            email: session.user.email || '',
            name: `${session.user.user_metadata?.first_name || ''} ${session.user.user_metadata?.last_name || ''}`.trim() || session.user.email?.split('@')[0] || '',
            firstName: session.user.user_metadata?.first_name || '',
            lastName: session.user.user_metadata?.last_name || '',
            phone: session.user.user_metadata?.phone || '',
            country: session.user.user_metadata?.country || '',
            linkedinProfile: session.user.user_metadata?.linkedin_profile || '',
            companyName: session.user.user_metadata?.company_name || '',
            companyWebsite: session.user.user_metadata?.company_website || '',
            linkedinCorporate: session.user.user_metadata?.linkedin_corporate || '',
            user_type: session.user.user_metadata?.role || 'producer',
            language: session.user.user_metadata?.language || 'fr',
            created_at: session.user.created_at || '',
            plan: 'essential'
          }
          
          setUser(userData)
          setIsAuthenticated(true)
        } else if (isMountedRef.current && !isLoggingOutRef.current) {
          console.log('ℹ️ Aucun utilisateur connecté')
          setIsAuthenticated(false)
        }
      } catch (error) {
        console.error('❌ Erreur chargement utilisateur:', error)
        if (isMountedRef.current && !isLoggingOutRef.current) {
          setIsAuthenticated(false)
        }
      } finally {
        if (isMountedRef.current && !isLoggingOutRef.current) {
          setIsLoading(false)
        }
      }
    }

    loadUser()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        // ✅ IGNORER LES ÉVÉNEMENTS PENDANT LE LOGOUT
        if (isLoggingOutRef.current) {
          console.log('🚫 Événement auth ignoré (logout en cours):', event)
          return
        }

        if (!isMountedRef.current) {
          console.log('🚫 Événement auth ignoré (composant démonté):', event)
          return
        }

        console.log('🔄 Changement auth:', event, session?.user?.email)
        
        if (event === 'SIGNED_OUT') {
          setUser(null)
          setIsAuthenticated(false)
        } else if (event === 'SIGNED_IN' && session?.user) {
          loadUser()
        }
      }
    )

    return () => {
      if (subscription?.unsubscribe) {
        subscription.unsubscribe()
      }
    }
  }, [])

  // ✅ DÉCONNEXION SIMPLIFIÉE AVEC CONTRÔLE D'ÉTAT
  const logout = async (): Promise<void> => {
    try {
      console.log('🚪 [Logout] Début déconnexion sécurisée')
      
      // ✅ MARQUER LE LOGOUT COMME EN COURS
      isLoggingOutRef.current = true
      
      // ✅ ÉTAPE 1: Réinitialiser l'état local IMMÉDIATEMENT
      if (isMountedRef.current) {
        setUser(null)
        setIsAuthenticated(false)
        setIsLoading(true) // Mettre en loading pendant la déconnexion
      }
      
      // ✅ ÉTAPE 2: Nettoyage stockage local AVANT Supabase
      try {
        if (typeof window !== 'undefined') {
          // Nettoyer localStorage
          if (typeof localStorage !== 'undefined') {
            const keysToRemove = Object.keys(localStorage).filter(key => 
              key.includes('supabase') || 
              key.includes('sb-') || 
              key.includes('auth') ||
              key.includes('session') ||
              key.includes('token') ||
              key.includes('intelia')
            )
            
            keysToRemove.forEach(key => {
              try {
                localStorage.removeItem(key)
                console.log('🗑️ [Logout] Supprimé localStorage:', key)
              } catch (e) {
                console.warn('⚠️ [Logout] Impossible de supprimer:', key)
              }
            })
          }
          
          // Nettoyer sessionStorage
          if (typeof sessionStorage !== 'undefined') {
            const sessionKeysToRemove = Object.keys(sessionStorage).filter(key => 
              key.includes('supabase') || 
              key.includes('sb-') || 
              key.includes('auth') ||
              key.includes('session') ||
              key.includes('intelia')
            )
            
            sessionKeysToRemove.forEach(key => {
              try {
                sessionStorage.removeItem(key)
                console.log('🗑️ [Logout] Supprimé sessionStorage:', key)
              } catch (e) {
                console.warn('⚠️ [Logout] Impossible de supprimer session:', key)
              }
            })
          }
        }
      } catch (storageError) {
        console.warn('⚠️ [Logout] Erreur nettoyage stockage:', storageError)
      }

      // ✅ ÉTAPE 3: Déconnexion Supabase (silencieuse)
      try {
        const { error } = await supabase.auth.signOut({ scope: 'global' })
        if (error) {
          console.warn('⚠️ [Logout] Avertissement Supabase (ignoré):', error.message)
        } else {
          console.log('✅ [Logout] Déconnexion Supabase réussie')
        }
      } catch (supabaseError) {
        console.warn('⚠️ [Logout] Erreur Supabase (ignorée):', supabaseError)
        // Continuer même si Supabase échoue
      }
      
      // ✅ ÉTAPE 4: Attendre un peu pour que les changements soient appliqués
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // ✅ ÉTAPE 5: Redirection FORCÉE et IMMÉDIATE
      console.log('🏠 [Logout] Redirection immédiate vers accueil')
      
      // Redirection la plus fiable possible
      if (typeof window !== 'undefined') {
        // Empêcher tout autre traitement
        window.onbeforeunload = null
        
        // Redirection immédiate avec rechargement complet
        window.location.replace('/')
        
        // Fallback au cas où replace ne fonctionne pas
        setTimeout(() => {
          window.location.href = '/'
        }, 50)
        
        // Fallback ultime
        setTimeout(() => {
          window.location.reload()
        }, 200)
      }
      
    } catch (error) {
      console.error('❌ [Logout] Erreur critique (récupération):', error)
      
      // ✅ RÉCUPÉRATION D'URGENCE
      try {
        // Marquer comme déconnecté même en cas d'erreur
        if (isMountedRef.current) {
          setUser(null)
          setIsAuthenticated(false)
        }
        
        // Nettoyage d'urgence
        if (typeof window !== 'undefined') {
          try {
            localStorage.clear()
            sessionStorage.clear()
          } catch (clearError) {
            console.warn('⚠️ [Logout] Nettoyage d\'urgence échoué:', clearError)
          }
          
          // Redirection forcée même en cas d'erreur
          window.location.replace('/')
        }
      } catch (emergencyError) {
        console.error('❌ [Logout] Récupération d\'urgence échouée:', emergencyError)
        
        // Dernier recours - rechargement de la page
        if (typeof window !== 'undefined') {
          window.location.reload()
        }
      }
    }
  }

  const updateProfile = async (data: ProfileUpdateData): Promise<{ success: boolean; error?: string }> => {
    try {
      console.log('📝 Mise à jour profil:', data)
      
      const updates = {
        data: {
          first_name: data.firstName,
          last_name: data.lastName,
          phone: data.phone,
          country: data.country,
          linkedin_profile: data.linkedinProfile,
          company_name: data.companyName,
          company_website: data.companyWebsite,
          linkedin_corporate: data.linkedinCorporate,
          language: data.language
        }
      }
      
      const { error } = await supabase.auth.updateUser(updates)
      
      if (error) {
        console.error('❌ Erreur mise à jour profil:', error)
        return { success: false, error: error.message }
      }
      
      if (user && isMountedRef.current) {
        const updatedUser: User = {
          ...user,
          firstName: data.firstName,
          lastName: data.lastName,
          email: data.email,
          phone: data.phone,
          country: data.country,
          linkedinProfile: data.linkedinProfile,
          companyName: data.companyName,
          companyWebsite: data.companyWebsite,
          linkedinCorporate: data.linkedinCorporate,
          name: `${data.firstName} ${data.lastName}`.trim(),
          language: data.language || user.language
        }
        
        setUser(updatedUser)
        console.log('✅ Profil mis à jour localement:', updatedUser)
      }
      
      return { success: true }
    } catch (error: any) {
      console.error('❌ Erreur critique mise à jour:', error)
      return { success: false, error: error.message }
    }
  }

  return {
    user,
    isAuthenticated,
    isLoading,
    logout,
    updateProfile
  }
}