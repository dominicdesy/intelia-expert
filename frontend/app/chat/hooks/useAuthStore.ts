// hooks/useAuthStore.ts - AVEC DÉCONNEXION COMPLÈTE CORRIGÉE

import { useState, useEffect } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { useRouter } from 'next/navigation'
import { User, AuthStore, ProfileUpdateData } from '../types'

const supabase = createClientComponentClient()

// ==================== STORE D'AUTHENTIFICATION ÉTENDU ====================
export const useAuthStore = (): AuthStore => {
  const [user, setUser] = useState<User | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

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

  // ✅ DÉCONNEXION CORRIGÉE: Utilise Next.js Router au lieu de window.location
  const logout = async (): Promise<void> => {
    try {
      console.log('🚪 [Logout] Début déconnexion complète')
      
      // ✅ ÉTAPE 1: Réinitialiser l'état local IMMÉDIATEMENT
      console.log('🔄 [Logout] Réinitialisation état local immédiate')
      setUser(null)
      setIsAuthenticated(false)
      
      // ✅ ÉTAPE 2: Déconnexion Supabase avec scope global
      console.log('📤 [Logout] Déconnexion Supabase (scope: global)')
      try {
        const { error } = await supabase.auth.signOut({ 
          scope: 'global' // ✅ CRITIQUE: Déconnecte de TOUS les appareils/sessions
        })
        
        if (error) {
          console.error('❌ [Logout] Erreur déconnexion Supabase (non-bloquante):', error)
          // Continuer le nettoyage même en cas d'erreur
        } else {
          console.log('✅ [Logout] Déconnexion Supabase réussie')
        }
      } catch (supabaseError) {
        console.error('❌ [Logout] Erreur critique Supabase (ignorée):', supabaseError)
        // Continuer le processus même si Supabase échoue
      }
      
      // ✅ ÉTAPE 3: Nettoyage COMPLET du stockage local
      console.log('🧹 [Logout] Nettoyage stockage local complet')
      
      try {
        // Nettoyer localStorage
        const localStorageKeys = Object.keys(localStorage)
        localStorageKeys.forEach(key => {
          if (key.includes('supabase') || 
              key.includes('sb-') || 
              key.includes('auth') ||
              key.includes('session') ||
              key.includes('token') ||
              key.includes('intelia') ||
              key.startsWith('chakra-ui') ||
              key.includes('user')) {
            localStorage.removeItem(key)
            console.log('🗑️ [Logout] Supprimé localStorage:', key)
          }
        })
        
        // Nettoyer sessionStorage
        const sessionStorageKeys = Object.keys(sessionStorage)
        sessionStorageKeys.forEach(key => {
          if (key.includes('supabase') || 
              key.includes('sb-') || 
              key.includes('auth') ||
              key.includes('session') ||
              key.includes('token') ||
              key.includes('intelia') ||
              key.includes('user')) {
            sessionStorage.removeItem(key)
            console.log('🗑️ [Logout] Supprimé sessionStorage:', key)
          }
        })
      } catch (storageError) {
        console.error('❌ [Logout] Erreur nettoyage stockage (ignorée):', storageError)
      }
      
      // ✅ ÉTAPE 4: Nettoyer les cookies manuellement (backup)
      try {
        document.cookie.split(";").forEach(cookie => {
          const eqPos = cookie.indexOf("=")
          const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim()
          if (name.includes('supabase') || 
              name.includes('sb-') || 
              name.includes('auth') ||
              name.includes('session')) {
            document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;domain=${window.location.hostname}`
            document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/`
            console.log('🍪 [Logout] Cookie supprimé:', name)
          }
        })
      } catch (cookieError) {
        console.error('❌ [Logout] Erreur nettoyage cookies (ignorée):', cookieError)
      }
      
      // ✅ ÉTAPE 5: Attendre un peu pour s'assurer que tout est nettoyé
      await new Promise(resolve => setTimeout(resolve, 300))
      
      // ✅ ÉTAPE 6: Redirection PROPRE avec Next.js Router
      console.log('🏠 [Logout] Redirection vers page de connexion')
      
      try {
        // Essayer d'abord avec le router Next.js
        router.push('/')
        router.refresh() // Force un refresh pour nettoyer le cache
        
        // Fallback avec window.location après un délai
        setTimeout(() => {
          if (window.location.pathname !== '/') {
            console.log('🔄 [Logout] Fallback: redirection forcée')
            window.location.href = '/'
          }
        }, 1000)
        
      } catch (routerError) {
        console.error('❌ [Logout] Erreur router, utilisation fallback:', routerError)
        // Fallback immédiat si le router échoue
        window.location.href = '/'
      }
      
    } catch (error) {
      console.error('❌ [Logout] Erreur critique déconnexion:', error)
      
      // ✅ FALLBACK ULTIME: Même en cas d'erreur, forcer la déconnexion
      setUser(null)
      setIsAuthenticated(false)
      
      // Nettoyage d'urgence
      try {
        localStorage.clear()
        sessionStorage.clear()
      } catch (clearError) {
        console.error('❌ [Logout] Erreur nettoyage d\'urgence:', clearError)
      }
      
      // Redirection forcée même en cas d'erreur totale
      try {
        router.push('/')
      } catch (finalError) {
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