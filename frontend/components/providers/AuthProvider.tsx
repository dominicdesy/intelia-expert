// hooks/useAuthStore.ts - VERSION DEBUG POUR IDENTIFIER L'ERREUR

import { useState, useEffect } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { User, AuthStore, ProfileUpdateData } from '../types'

const supabase = createClientComponentClient()

// ==================== STORE AVEC DIAGNOSTIC COMPLET ====================
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

  // ✅ VERSION DEBUG AVEC ISOLATION DES ÉTAPES
  const logout = async (): Promise<void> => {
    console.log('🔍 [DEBUG] Début logout - Version diagnostic')
    
    try {
      // ÉTAPE 1: État local (le plus sûr)
      console.log('🔍 [DEBUG] ÉTAPE 1: Réinitialisation état local')
      setUser(null)
      setIsAuthenticated(false)
      console.log('✅ [DEBUG] État local réinitialisé avec succès')
      
      // ÉTAPE 2: Test Supabase (potentielle source d'erreur)
      console.log('🔍 [DEBUG] ÉTAPE 2: Test déconnexion Supabase')
      try {
        console.log('🔍 [DEBUG] Appel supabase.auth.signOut...')
        const { error } = await supabase.auth.signOut()
        
        if (error) {
          console.error('❌ [DEBUG] ERREUR SUPABASE:', error)
          console.error('❌ [DEBUG] Message erreur:', error.message)
          console.error('❌ [DEBUG] Code erreur:', error.status)
          throw new Error(`Supabase signOut failed: ${error.message}`)
        } else {
          console.log('✅ [DEBUG] Supabase signOut réussi')
        }
      } catch (supabaseError: any) {
        console.error('❌ [DEBUG] EXCEPTION SUPABASE:', supabaseError)
        console.error('❌ [DEBUG] Stack trace:', supabaseError.stack)
        
        // CONTINUER même si Supabase échoue
        console.log('⚠️ [DEBUG] Continuation malgré erreur Supabase')
      }
      
      // ÉTAPE 3: Nettoyage stockage (peut causer des erreurs)
      console.log('🔍 [DEBUG] ÉTAPE 3: Test nettoyage stockage')
      try {
        if (typeof Storage !== 'undefined' && typeof localStorage !== 'undefined') {
          console.log('🔍 [DEBUG] localStorage disponible, nettoyage...')
          
          const keysToRemove: string[] = []
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i)
            if (key && (
              key.includes('supabase') || 
              key.includes('sb-') || 
              key.includes('auth')
            )) {
              keysToRemove.push(key)
            }
          }
          
          console.log('🔍 [DEBUG] Clés à supprimer:', keysToRemove)
          
          keysToRemove.forEach(key => {
            try {
              localStorage.removeItem(key)
              console.log('✅ [DEBUG] Supprimé:', key)
            } catch (removeError) {
              console.error('❌ [DEBUG] Erreur suppression clé:', key, removeError)
            }
          })
        } else {
          console.log('⚠️ [DEBUG] localStorage non disponible')
        }
      } catch (storageError: any) {
        console.error('❌ [DEBUG] EXCEPTION STOCKAGE:', storageError)
        console.error('❌ [DEBUG] Stack trace stockage:', storageError.stack)
      }
      
      // ÉTAPE 4: Attente (sécurité)
      console.log('🔍 [DEBUG] ÉTAPE 4: Attente sécurité')
      await new Promise(resolve => setTimeout(resolve, 100))
      console.log('✅ [DEBUG] Attente terminée')
      
      // ÉTAPE 5: Redirection (source potentielle d'erreur)
      console.log('🔍 [DEBUG] ÉTAPE 5: Test redirection')
      try {
        if (typeof window !== 'undefined' && window.location) {
          console.log('🔍 [DEBUG] window.location disponible')
          console.log('🔍 [DEBUG] URL actuelle:', window.location.href)
          console.log('🔍 [DEBUG] Tentative redirection vers /')
          
          // Test simple sans rechargement
          console.log('🔍 [DEBUG] Redirection simple...')
          window.location.href = '/'
          
        } else {
          console.error('❌ [DEBUG] window.location non disponible')
        }
      } catch (redirectError: any) {
        console.error('❌ [DEBUG] EXCEPTION REDIRECTION:', redirectError)
        console.error('❌ [DEBUG] Stack trace redirection:', redirectError.stack)
      }
      
    } catch (globalError: any) {
      console.error('❌ [DEBUG] ERREUR GLOBALE LOGOUT:', globalError)
      console.error('❌ [DEBUG] Message global:', globalError.message)
      console.error('❌ [DEBUG] Stack trace global:', globalError.stack)
      
      // Fallback ultime
      console.log('🔍 [DEBUG] Fallback ultime activé')
      try {
        setUser(null)
        setIsAuthenticated(false)
        
        if (typeof window !== 'undefined') {
          console.log('🔍 [DEBUG] Redirection fallback')
          window.location.replace('/')
        }
      } catch (fallbackError) {
        console.error('❌ [DEBUG] ÉCHEC FALLBACK:', fallbackError)
      }
    }
    
    console.log('🔍 [DEBUG] Fin fonction logout')
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