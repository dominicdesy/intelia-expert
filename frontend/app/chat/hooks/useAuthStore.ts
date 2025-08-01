// hooks/useAuthStore.ts - DÉCONNEXION CORRIGÉE AVEC REMEMBER ME

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

  // ✅ FONCTION UTILITAIRE POUR REMEMBER ME
  const rememberMeUtils = {
    // Sauvegarder les préférences remember me
    save: (email: string, remember = true) => {
      if (remember && email) {
        localStorage.setItem('intelia-remember-me', 'true')
        localStorage.setItem('intelia-last-email', email.trim())
        console.log('💾 [RememberMe] Email sauvegardé:', email)
      } else {
        localStorage.removeItem('intelia-remember-me')
        localStorage.removeItem('intelia-last-email')
        console.log('🗑️ [RememberMe] Préférences supprimées')
      }
    },
    
    // Charger les préférences remember me
    load: () => {
      const rememberMe = localStorage.getItem('intelia-remember-me') === 'true'
      const lastEmail = localStorage.getItem('intelia-last-email') || ''
      
      return {
        rememberMe,
        lastEmail: rememberMe ? lastEmail : '',
        hasRememberedEmail: rememberMe && lastEmail.length > 0
      }
    },
    
    // Effacer complètement (pour déconnexion définitive si besoin)
    clear: () => {
      localStorage.removeItem('intelia-remember-me')
      localStorage.removeItem('intelia-last-email')
      console.log('🧹 [RememberMe] Nettoyage complet')
    }
  }

  // ✅ DÉCONNEXION CORRIGÉE - PRÉSERVE REMEMBER ME
  const logout = async (): Promise<void> => {
    try {
      console.log('🚪 [Logout] Début déconnexion sécurisée')
      
      // ✅ MARQUER LE LOGOUT COMME EN COURS
      isLoggingOutRef.current = true
      
      // ✅ ÉTAPE 1: SAUVEGARDER les préférences AVANT nettoyage
      let savedRememberMe = false
      let savedLastEmail = ''
      let savedLanguage = ''
      
      try {
        if (typeof window !== 'undefined' && typeof localStorage !== 'undefined') {
          savedRememberMe = localStorage.getItem('intelia-remember-me') === 'true'
          savedLastEmail = localStorage.getItem('intelia-last-email') || ''
          savedLanguage = localStorage.getItem('intelia-language') || ''
          
          console.log('💾 [Logout] Sauvegarde préférences:', { 
            savedRememberMe, 
            savedLastEmail: savedLastEmail ? savedLastEmail.substring(0, 10) + '...' : 'none',
            savedLanguage 
          })
        }
      } catch (error) {
        console.warn('⚠️ [Logout] Erreur sauvegarde préférences:', error)
      }
      
      // ✅ ÉTAPE 2: Réinitialiser l'état local IMMÉDIATEMENT
      if (isMountedRef.current) {
        setUser(null)
        setIsAuthenticated(false)
        setIsLoading(true) // Mettre en loading pendant la déconnexion
      }
      
      // ✅ ÉTAPE 3: Nettoyage stockage local SÉLECTIF
      try {
        if (typeof window !== 'undefined') {
          // ✅ Nettoyer localStorage - SEULEMENT les données de session/auth
          if (typeof localStorage !== 'undefined') {
            const keysToRemove = Object.keys(localStorage).filter(key => {
              // ✅ GARDER les préférences utilisateur importantes
              if (key === 'intelia-remember-me') return false
              if (key === 'intelia-last-email') return false
              if (key === 'intelia-language') return false
              
              // ✅ SUPPRIMER seulement les données de session/auth
              return (
                key.includes('supabase') || 
                key.includes('sb-') || 
                key.includes('auth') ||
                key.includes('session') ||
                key.includes('token') ||
                key.startsWith('intelia-auth') ||
                key.startsWith('intelia-chat') ||
                key.startsWith('intelia-user')
              )
            })
            
            keysToRemove.forEach(key => {
              try {
                localStorage.removeItem(key)
                console.log('🗑️ [Logout] Supprimé localStorage (auth only):', key)
              } catch (e) {
                console.warn('⚠️ [Logout] Impossible de supprimer:', key)
              }
            })
          }
          
          // ✅ Nettoyer sessionStorage (tout peut être supprimé)
          if (typeof sessionStorage !== 'undefined') {
            try {
              sessionStorage.clear()
              console.log('🗑️ [Logout] SessionStorage nettoyé')
            } catch (e) {
              console.warn('⚠️ [Logout] Erreur nettoyage sessionStorage:', e)
            }
          }
        }
      } catch (storageError) {
        console.warn('⚠️ [Logout] Erreur nettoyage stockage:', storageError)
      }

      // ✅ ÉTAPE 4: RESTAURER les préférences utilisateur sauvegardées
      try {
        if (typeof window !== 'undefined' && typeof localStorage !== 'undefined') {
          // Restaurer remember me seulement si activé
          if (savedRememberMe && savedLastEmail) {
            localStorage.setItem('intelia-remember-me', 'true')
            localStorage.setItem('intelia-last-email', savedLastEmail)
            console.log('✅ [Logout] Préférences remember me restaurées')
          }
          
          // Restaurer langue
          if (savedLanguage) {
            localStorage.setItem('intelia-language', savedLanguage)
            console.log('✅ [Logout] Langue restaurée:', savedLanguage)
          }
        }
      } catch (error) {
        console.warn('⚠️ [Logout] Erreur restauration préférences:', error)
      }

      // ✅ ÉTAPE 5: Déconnexion Supabase (silencieuse)
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
      
      // ✅ ÉTAPE 6: Attendre un peu pour que les changements soient appliqués
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // ✅ ÉTAPE 7: Redirection FORCÉE et IMMÉDIATE
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
      
      // ✅ RÉCUPÉRATION D'URGENCE - préserver remember me
      try {
        // Marquer comme déconnecté même en cas d'erreur
        if (isMountedRef.current) {
          setUser(null)
          setIsAuthenticated(false)
        }
        
        // Nettoyage d'urgence SÉLECTIF
        if (typeof window !== 'undefined' && typeof localStorage !== 'undefined') {
          // Sauvegarder remember me avant nettoyage d'urgence
          const emergencyRememberMe = localStorage.getItem('intelia-remember-me')
          const emergencyLastEmail = localStorage.getItem('intelia-last-email') 
          const emergencyLanguage = localStorage.getItem('intelia-language')
          
          try {
            // Nettoyage d'urgence
            const keysToKeep = ['intelia-remember-me', 'intelia-last-email', 'intelia-language']
            const allKeys = Object.keys(localStorage)
            
            allKeys.forEach(key => {
              if (!keysToKeep.includes(key)) {
                localStorage.removeItem(key)
              }
            })
            
            // Restaurer les préférences importantes
            if (emergencyRememberMe === 'true' && emergencyLastEmail) {
              localStorage.setItem('intelia-remember-me', 'true')
              localStorage.setItem('intelia-last-email', emergencyLastEmail)
            }
            if (emergencyLanguage) {
              localStorage.setItem('intelia-language', emergencyLanguage)
            }
            
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

  // ✅ FONCTION LOGIN AVEC REMEMBER ME (à utiliser dans votre composant login)
  const login = async (email: string, password: string): Promise<void> => {
    try {
      console.log('🔐 Connexion pour:', email)
      setIsLoading(true)
      
      const { data, error } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password: password
      })
      
      if (error) {
        console.error('❌ Erreur connexion:', error)
        throw error
      }
      
      if (data.user) {
        console.log('✅ Connexion réussie pour:', email)
        // La mise à jour de l'état sera gérée par onAuthStateChange
      }
      
    } catch (error: any) {
      console.error('❌ Erreur login:', error)
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  // ✅ FONCTION REGISTER AVEC METADATA
  const register = async (email: string, password: string, userData?: Partial<User>): Promise<void> => {
    try {
      console.log('📝 Inscription pour:', email)
      setIsLoading(true)
      
      const { data, error } = await supabase.auth.signUp({
        email: email.trim(),
        password: password,
        options: {
          data: {
            first_name: userData?.firstName || '',
            last_name: userData?.lastName || '',
            role: userData?.user_type || 'producer',
            language: userData?.language || 'fr'
          }
        }
      })
      
      if (error) {
        console.error('❌ Erreur inscription:', error)
        throw error
      }
      
      console.log('✅ Inscription réussie pour:', email)
      
    } catch (error: any) {
      console.error('❌ Erreur register:', error)
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  // ✅ FONCTION D'INITIALISATION SESSION
  const initializeSession = async (): Promise<boolean> => {
    try {
      console.log('🔄 Initialisation session...')
      
      const { data: { session }, error } = await supabase.auth.getSession()
      
      if (error) {
        console.error('❌ Erreur récupération utilisateur:', error)
        return false
      }
      
      if (session) {
        console.log('✅ Session restaurée pour:', session.user.email)
        return true
      } else {
        console.log('❌ Aucune session à initialiser')
        return false
      }
      
    } catch (error) {
      console.error('❌ Erreur initialisation session:', error)
      return false
    }
  }

  // ✅ ÉTAT POUR VÉRIFIER SI LE STORE EST HYDRATÉ
  const [hasHydrated, setHasHydrated] = useState(false)
  
  useEffect(() => {
    setHasHydrated(true)
  }, [])

  return {
    user,
    isAuthenticated,
    isLoading,
    hasHydrated,
    logout,
    login,
    register,
    updateProfile,
    initializeSession
  }
}