// hooks/useAuthStore.ts - DÉCONNEXION CORRIGÉE SANS ERREUR CLIENT

import { useState, useEffect } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { User, AuthStore, ProfileUpdateData } from '../types'

const supabase = createClientComponentClient()

// ==================== STORE D'AUTHENTIFICATION CORRIGÉ ====================
export const useAuthStore = (): AuthStore => {
  const [user, setUser] = useState<User | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadUser = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (error) {
          console.error('❌ Erreur récupération session:', error)
          setIsAuthenticated(false)
          setIsLoading(false)
          return
        }

        if (session?.user) {
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
        } else {
          console.log('ℹ️ Aucun utilisateur connecté')
          setIsAuthenticated(false)
        }
      } catch (error) {
        console.error('❌ Erreur chargement utilisateur:', error)
        setIsAuthenticated(false)
      } finally {
        setIsLoading(false)
      }
    }

    loadUser()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
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

  // ✅ DÉCONNEXION SIMPLIFIÉE SANS ROUTER - ÉVITE LES ERREURS CLIENT
  const logout = async (): Promise<void> => {
    try {
      console.log('🚪 [Logout] Début déconnexion simplifiée')
      
      // ✅ ÉTAPE 1: Réinitialiser l'état local IMMÉDIATEMENT
      setUser(null)
      setIsAuthenticated(false)
      
      // ✅ ÉTAPE 2: Déconnexion Supabase
      try {
        const { error } = await supabase.auth.signOut({ scope: 'global' })
        if (error) {
          console.warn('⚠️ [Logout] Avertissement Supabase:', error.message)
        } else {
          console.log('✅ [Logout] Déconnexion Supabase réussie')
        }
      } catch (supabaseError) {
        console.warn('⚠️ [Logout] Erreur Supabase ignorée:', supabaseError)
      }
      
      // ✅ ÉTAPE 3: Nettoyage stockage local SÉCURISÉ
      try {
        // Nettoyer localStorage avec vérification
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
        
        // Nettoyer sessionStorage avec vérification
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
      } catch (storageError) {
        console.warn('⚠️ [Logout] Erreur nettoyage stockage:', storageError)
      }
      
      // ✅ ÉTAPE 4: Attendre que les changements soient appliqués
      await new Promise(resolve => setTimeout(resolve, 200))
      
      // ✅ ÉTAPE 5: Redirection SIMPLE et SÛRE
      console.log('🏠 [Logout] Redirection vers accueil')
      
      // Méthode la plus fiable - rechargement complet de la page
      if (typeof window !== 'undefined') {
        window.location.href = '/'
      }
      
    } catch (error) {
      console.error('❌ [Logout] Erreur critique:', error)
      
      // ✅ FALLBACK ULTIME - Nettoyage d'urgence
      setUser(null)
      setIsAuthenticated(false)
      
      try {
        if (typeof localStorage !== 'undefined') {
          localStorage.clear()
        }
        if (typeof sessionStorage !== 'undefined') {
          sessionStorage.clear()
        }
      } catch (clearError) {
        console.warn('⚠️ [Logout] Nettoyage d\'urgence échoué:', clearError)
      }
      
      // Redirection forcée même en cas d'erreur
      if (typeof window !== 'undefined') {
        window.location.href = '/'
      }
    }
  }

  const updateProfile = async (data: ProfileUpdateData): Promise<{ success: boolean; error?: string }> => {
    try {
      console.log('📝 Mise à jour profil:', data)
      
      // Préparer les métadonnées utilisateur avec toutes les nouvelles données
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
      
      // Mise à jour des données utilisateur locales avec toutes les nouvelles informations
      if (user) {
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