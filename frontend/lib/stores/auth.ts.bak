// lib/stores/auth.ts - Store d'authentification AMÉLIORÉ avec toutes les corrections
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { User, RGPDConsent } from '@/types'
import { supabase, auth } from '@/lib/supabase/client'
import toast from 'react-hot-toast'

interface AuthState {
  // État existant
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  hasHydrated: boolean
  
  // ✅ NOUVEAUX ÉTATS pour gestion améliorée
  lastAuthCheck: number
  authErrors: string[]
  isRecovering: boolean
  sessionCheckCount: number
  
  // Actions principales
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, userData: Partial<User>) => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
  initializeSession: () => Promise<boolean>
  setHasHydrated: (hasHydrated: boolean) => void
  
  // Actions profil
  updateProfile: (data: Partial<User>) => Promise<void>
  deleteUserData: () => Promise<void>
  exportUserData: () => Promise<any>
  updateConsent: (consent: RGPDConsent) => Promise<void>
  
  // ✅ NOUVELLES ACTIONS pour gestion erreurs
  handleAuthError: (error: any) => void
  clearAuthErrors: () => void
  
  // Action de nettoyage
  clearAuth: () => void
}

// 🔥 PROTECTION ANTI-BOUCLE GLOBALE RENFORCÉE
let isListenerActive = false
let authCheckInProgress = false
let lastAuthStateChange = 0
const AUTH_THROTTLE_DELAY = 1000 // 1 seconde entre les changements d'état

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // État initial
      user: null,
      isLoading: false,
      isAuthenticated: false,
      hasHydrated: false,
      
      // ✅ NOUVEAUX ÉTATS
      lastAuthCheck: 0,
      authErrors: [],
      isRecovering: false,
      sessionCheckCount: 0,

      // ✅ NOUVELLE FONCTION : Gestion intelligente des erreurs auth
      handleAuthError: (error: any) => {
        console.log('🔧 [Auth] Gestion erreur auth:', error)
        
        const { authErrors } = get()
        const errorMessage = error?.message || error?.toString() || 'Erreur inconnue'
        
        // Détecter les erreurs de session expirée
        if (error?.status === 403 || 
            error?.message?.includes('Auth session missing') ||
            error?.message?.includes('Forbidden') ||
            error?.message?.includes('JWT expired') ||
            error?.message?.includes('Invalid token')) {
          
          console.log('🔄 [Auth] Session expirée détectée, nettoyage en cours')
          
          set({ 
            user: null, 
            isAuthenticated: false, 
            isRecovering: true,
            authErrors: [...authErrors, `Session expirée: ${errorMessage}`]
          })
          
          // Nettoyer automatiquement après 5 secondes
          setTimeout(() => {
            const currentState = get()
            if (currentState.isRecovering) {
              set({ 
                isRecovering: false, 
                authErrors: [] 
              })
            }
          }, 5000)
          
        } else {
          // Autres erreurs non critiques
          set({ 
            authErrors: [...authErrors, errorMessage].slice(-3) // Garder seulement les 3 dernières
          })
          
          // Nettoyer après 10 secondes
          setTimeout(() => {
            set({ authErrors: [] })
          }, 10000)
        }
      },

      // ✅ NOUVELLE FONCTION : Nettoyer les erreurs
      clearAuthErrors: () => {
        set({ authErrors: [], isRecovering: false })
      },

      // Nettoyage complet de l'authentification - AMÉLIORÉ
      clearAuth: () => {
        console.log('🧹 [Auth] Nettoyage complet de l\'authentification')
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          isRecovering: false,
          authErrors: []
        })
      },

      // Marquer l'hydratation comme terminée
      setHasHydrated: (hasHydrated: boolean) => {
        set({ hasHydrated })
      },

      // 🔄 INITIALISATION SESSION AMÉLIORÉE
      initializeSession: async (): Promise<boolean> => {
        const { lastAuthCheck, sessionCheckCount } = get()
        const now = Date.now()
        
        // ✅ PROTECTION : Éviter les vérifications trop fréquentes
        if (now - lastAuthCheck < 2000) {
          console.log('🔄 [Auth] Vérification auth trop récente, skip')
          return false
        }
        
        // 🔥 PROTECTION: Éviter les appels multiples
        if (authCheckInProgress) {
          console.log('⚠️ [Auth] Initialisation déjà en cours, abandon')
          return false
        }

        try {
          authCheckInProgress = true
          set({ 
            lastAuthCheck: now,
            sessionCheckCount: sessionCheckCount + 1
          })
          
          console.log('🔄 Initialisation session... (tentative', sessionCheckCount + 1, ')')
          set({ isLoading: true })

          const currentUser = await auth.getCurrentUser()

          if (!currentUser) {
            console.log('❌ Aucune session à initialiser')
            set({ user: null, isAuthenticated: false, isLoading: false })
            return false
          }

          // Mapper l'utilisateur Supabase vers notre interface User
          const mappedUser: User = {
            id: currentUser.id,
            email: currentUser.email!,
            name: currentUser.user_metadata?.name || currentUser.email!.split('@')[0],
            user_type: currentUser.user_metadata?.user_type || 'producer',
            language: currentUser.user_metadata?.language || 'fr',
            avatar_url: currentUser.user_metadata?.avatar_url || undefined,
            created_at: currentUser.created_at || new Date().toISOString(),
            updated_at: new Date().toISOString(),
            consent_given: true,
            consent_date: new Date().toISOString()
          }

          set({ 
            user: mappedUser, 
            isAuthenticated: true, 
            isLoading: false,
            authErrors: [] // Nettoyer les erreurs en cas de succès
          })

          console.log('✅ Session initialisée pour:', mappedUser.email)
          return true

        } catch (error: any) {
          console.error('❌ Erreur initialisation session:', error)
          
          // ✅ UTILISER LA NOUVELLE GESTION D'ERREUR
          get().handleAuthError(error)
          
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false 
          })
          return false
        } finally {
          authCheckInProgress = false
        }
      },

      // 🔑 CONNEXION ORIGINALE (Supabase direct) - AMÉLIORÉE
      login: async (email: string, password: string) => {
        try {
          set({ isLoading: true, authErrors: [] }) // Nettoyer les erreurs précédentes
          console.log('🔑 Connexion pour:', email)

          const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password,
          })

          if (error) {
            console.error('❌ Erreur connexion:', error.message)
            
            // ✅ GESTION D'ERREUR AMÉLIORÉE
            get().handleAuthError(error)
            
            const errorMessages: Record<string, string> = {
              'Invalid login credentials': 'Email ou mot de passe incorrect',
              'Email not confirmed': 'Veuillez confirmer votre email',
              'Too many requests': 'Trop de tentatives. Réessayez plus tard.',
              'User not found': 'Aucun compte trouvé avec cet email',
              'Invalid email': 'Format d\'email invalide'
            }
            
            const userMessage = errorMessages[error.message] || error.message
            throw new Error(userMessage)
          }

          if (!data.user) {
            throw new Error('Aucune donnée utilisateur reçue')
          }

          const user: User = {
            id: data.user.id,
            email: data.user.email!,
            name: data.user.user_metadata?.name || data.user.email!.split('@')[0],
            user_type: data.user.user_metadata?.user_type || 'producer',
            language: data.user.user_metadata?.language || 'fr',
            avatar_url: data.user.user_metadata?.avatar_url || undefined,
            created_at: data.user.created_at || new Date().toISOString(),
            updated_at: new Date().toISOString(),
            consent_given: true,
            consent_date: new Date().toISOString()
          }

          console.log('✅ Connexion réussie pour:', user.email)

          set({ 
            user, 
            isAuthenticated: true, 
            isLoading: false,
            authErrors: [], // Nettoyer les erreurs
            isRecovering: false
          })

          toast.success(`Bienvenue ${user.name} !`, {
            icon: '👋',
            duration: 3000
          })

        } catch (error: any) {
          console.error('❌ Erreur connexion:', error)
          
          // ✅ GESTION D'ERREUR AMÉLIORÉE
          get().handleAuthError(error)
          
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false 
          })
          toast.error(error.message || 'Erreur de connexion', {
            icon: '⚠️',
            duration: 4000
          })
          throw error
        }
      },

      // 📝 INSCRIPTION - AMÉLIORÉE
      register: async (email: string, password: string, userData: Partial<User>) => {
        try {
          set({ isLoading: true, authErrors: [] })
          console.log('📝 Création compte pour:', email)

          const fullName = userData.name?.trim() || ''
          
          if (fullName.length < 2) {
            throw new Error('Le nom doit contenir au moins 2 caractères')
          }

          if (password.length < 8) {
            throw new Error('Le mot de passe doit contenir au moins 8 caractères')
          }

          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
          if (!emailRegex.test(email)) {
            throw new Error('Format d\'email invalide')
          }

          console.log('✅ Validations passées, création compte...')

          const { data, error } = await supabase.auth.signUp({
            email,
            password,
            options: {
              data: {
                name: fullName,
                user_type: userData.user_type || 'producer',
                language: userData.language || 'fr'
              }
            }
          })

          if (error) {
            console.error('❌ Erreur création compte:', error)
            
            // ✅ GESTION D'ERREUR AMÉLIORÉE
            get().handleAuthError(error)
            
            const errorMessages: Record<string, string> = {
              'User already registered': 'Un compte existe déjà avec cet email',
              'Password should be at least': 'Le mot de passe doit contenir au moins 8 caractères',
              'Invalid email': 'Format d\'email invalide',
              'Signup is disabled': 'Les inscriptions sont temporairement désactivées',
              'Weak password': 'Mot de passe trop faible'
            }
            
            const userMessage = errorMessages[error.message] || error.message
            throw new Error(userMessage)
          }

          if (!data.user) {
            throw new Error('Erreur lors de la création du compte')
          }

          console.log('✅ Compte créé avec succès')
          
          set({ isLoading: false, authErrors: [] })
          
          if (data.user.email_confirmed_at) {
            toast.success('Compte créé et confirmé ! Vous pouvez vous connecter.', {
              icon: '✅',
              duration: 5000
            })
          } else {
            toast.success('Compte créé ! Vérifiez votre email pour confirmer.', {
              icon: '📧',
              duration: 6000
            })
          }

        } catch (error: any) {
          console.error('❌ Erreur inscription:', error)
          
          // ✅ GESTION D'ERREUR AMÉLIORÉE
          get().handleAuthError(error)
          
          set({ isLoading: false })
          toast.error(error.message || 'Erreur lors de la création du compte', {
            icon: '⚠️',
            duration: 4000
          })
          throw error
        }
      },

      // 🚪 DÉCONNEXION CORRIGÉE - SANS MODIFICATION (déjà optimisée)
      logout: async () => {
        console.log('🚪 [Auth] Début déconnexion sécurisée')
        
        const { isLoading } = get()
        if (isLoading) {
          console.log('⚠️ [Auth] Déconnexion déjà en cours, ignorée')
          return
        }

        set({ isLoading: true })

        try {
          console.log('🧹 [Auth] Nettoyage état local prioritaire')
          get().clearAuth()
          
          try {
            localStorage.removeItem('intelia-remember-me')
            localStorage.removeItem('intelia-last-email')
            localStorage.removeItem('supabase.auth.token')
            localStorage.removeItem('intelia-auth-storage')
            
            Object.keys(localStorage).forEach(key => {
              if (key.startsWith('sb-') || key.includes('supabase')) {
                localStorage.removeItem(key)
              }
            })
          } catch (localStorageError) {
            console.warn('⚠️ [Auth] Erreur nettoyage localStorage:', localStorageError)
          }

          try {
            console.log('🔄 [Auth] Appel auth.signOut()')
            const result = await auth.signOut()
            
            if (!result.success) {
              console.warn('⚠️ [Auth] Erreur auth.signOut (non bloquante):', result.error)
            } else {
              console.log('✅ [Auth] auth.signOut() réussi')
            }
          } catch (authError) {
            console.warn('⚠️ [Auth] Erreur auth.signOut (non bloquante):', authError)
          }

          try {
            console.log('🔄 [Auth] Appel supabase.auth.signOut()')
            const { error } = await supabase.auth.signOut({
              scope: 'local'
            })
            
            if (error) {
              console.warn('⚠️ [Auth] Erreur Supabase logout (non bloquante):', error.message)
            } else {
              console.log('✅ [Auth] Supabase logout réussi')
            }
          } catch (supabaseError) {
            console.warn('⚠️ [Auth] Erreur Supabase logout (non bloquante):', supabaseError)
          }

          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            authErrors: [],
            isRecovering: false
          })

          toast.success('Déconnexion réussie', {
            icon: '👋',
            duration: 2000
          })
          
          console.log('✅ [Auth] Déconnexion complète réussie')

        } catch (error: any) {
          console.error('❌ [Auth] Erreur critique during logout:', error)
          
          get().clearAuth()
          set({ isLoading: false })
          
          toast.error('Erreur de déconnexion, mais vous êtes déconnecté localement', {
            icon: '⚠️',
            duration: 3000
          })
          
          console.log('🔧 [Auth] Déconnexion forcée malgré erreur - pas de throw')
        }
      },

      // 🔍 VÉRIFICATION SESSION - AMÉLIORÉE
      checkAuth: async () => {
        const { lastAuthCheck, sessionCheckCount } = get()
        const now = Date.now()
        
        // ✅ PROTECTION : Éviter les vérifications trop fréquentes
        if (now - lastAuthCheck < 3000) {
          console.log('🔄 [Auth] Vérification auth trop récente, skip')
          return
        }
        
        // 🔥 PROTECTION: Éviter les appels multiples
        if (authCheckInProgress) {
          console.log('⚠️ [Auth] Vérification auth déjà en cours, abandon')
          return
        }

        try {
          authCheckInProgress = true
          set({ 
            lastAuthCheck: now,
            sessionCheckCount: sessionCheckCount + 1
          })
          
          console.log('🔍 Vérification session... (check', sessionCheckCount + 1, ')')
          
          const user = await auth.getCurrentUser()

          if (!user) {
            console.log('❌ Aucune session active')
            set({ user: null, isAuthenticated: false })
            return
          }

          const userMapped: User = {
            id: user.id,
            email: user.email!,
            name: user.user_metadata?.name || user.email!.split('@')[0],
            user_type: user.user_metadata?.user_type || 'producer',
            language: user.user_metadata?.language || 'fr',
            avatar_url: user.user_metadata?.avatar_url || undefined,
            created_at: user.created_at || new Date().toISOString(),
            updated_at: new Date().toISOString(),
            consent_given: true,
            consent_date: new Date().toISOString()
          }

          set({ 
            user: userMapped, 
            isAuthenticated: true,
            authErrors: [] // Nettoyer les erreurs en cas de succès
          })
          console.log('✅ Session restaurée pour:', userMapped.email)

        } catch (error: any) {
          console.error('❌ Erreur vérification auth:', error)
          
          // ✅ GESTION D'ERREUR AMÉLIORÉE
          get().handleAuthError(error)
          
          set({ user: null, isAuthenticated: false })
        } finally {
          authCheckInProgress = false
        }
      },

      // 👤 MISE À JOUR PROFIL - AMÉLIORÉE
      updateProfile: async (data: Partial<User>) => {
        try {
          const { user } = get()
          if (!user) throw new Error('Utilisateur non connecté')

          console.log('👤 Mise à jour profil:', data)

          const { error } = await supabase.auth.updateUser({
            data: {
              name: data.name,
              user_type: data.user_type,
              language: data.language
            }
          })

          if (error) {
            console.error('❌ Erreur mise à jour Supabase:', error)
            
            // ✅ GESTION D'ERREUR AMÉLIORÉE
            get().handleAuthError(error)
            
            throw new Error(error.message)
          }

          const updatedUser = { 
            ...user, 
            ...data,
            updated_at: new Date().toISOString()
          }
          set({ user: updatedUser, authErrors: [] })

          toast.success('Profil mis à jour avec succès', {
            icon: '✅',
            duration: 3000
          })
          console.log('✅ Profil mis à jour')

        } catch (error: any) {
          console.error('❌ Erreur mise à jour profil:', error)
          
          // ✅ GESTION D'ERREUR AMÉLIORÉE
          get().handleAuthError(error)
          
          toast.error(error.message || 'Erreur mise à jour profil', {
            icon: '⚠️',
            duration: 4000
          })
          throw error
        }
      },

      // 🗑️ SUPPRESSION COMPTE - INCHANGÉE
      deleteUserData: async () => {
        try {
          const { user } = get()
          if (!user) throw new Error('Utilisateur non connecté')

          console.log('🗑️ Suppression compte utilisateur...')
          
          await get().logout()
          
          toast.success('Demande de suppression enregistrée. Contactez le support pour finaliser.', {
            icon: '🗑️',
            duration: 5000
          })
          console.log('✅ Suppression compte (déconnexion)')

        } catch (error: any) {
          console.error('❌ Erreur suppression compte:', error)
          
          // ✅ GESTION D'ERREUR AMÉLIORÉE
          get().handleAuthError(error)
          
          toast.error(error.message || 'Erreur suppression compte', {
            icon: '⚠️',
            duration: 4000
          })
          throw error
        }
      },

      // 📄 EXPORT DONNÉES - INCHANGÉE
      exportUserData: async () => {
        try {
          const { user } = get()
          if (!user) throw new Error('Utilisateur non connecté')

          console.log('📄 Export données utilisateur...')

          const supabaseUser = await auth.getCurrentUser()

          const exportData = {
            user: user,
            supabaseUser: supabaseUser,
            exportDate: new Date().toISOString(),
            dataRetentionInfo: {
              retention: '30 jours',
              autoDelete: true,
              nextDeletion: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
            }
          }

          const blob = new Blob([JSON.stringify(exportData, null, 2)], {
            type: 'application/json'
          })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `intelia-export-${user.id}-${new Date().toISOString().split('T')[0]}.json`
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          URL.revokeObjectURL(url)

          console.log('✅ Données exportées')
          toast.success('Données exportées avec succès', {
            icon: '📄',
            duration: 3000
          })
          
          return exportData

        } catch (error: any) {
          console.error('❌ Erreur export données:', error)
          
          // ✅ GESTION D'ERREUR AMÉLIORÉE
          get().handleAuthError(error)
          
          toast.error(error.message || 'Erreur export données', {
            icon: '⚠️',
            duration: 4000
          })
          throw error
        }
      },

      // 📋 MISE À JOUR CONSENTEMENTS - INCHANGÉE
      updateConsent: async (consent: RGPDConsent) => {
        try {
          const { user } = get()
          if (!user) throw new Error('Utilisateur non connecté')

          console.log('📋 Mise à jour consentements:', consent)

          const updatedUser = { 
            ...user, 
            consent_given: true,
            consent_date: new Date().toISOString(),
            updated_at: new Date().toISOString()
          }
          set({ user: updatedUser, authErrors: [] })

          toast.success('Consentements mis à jour', {
            icon: '📋',
            duration: 3000
          })
          console.log('✅ Consentements mis à jour')

        } catch (error: any) {
          console.error('❌ Erreur mise à jour consentements:', error)
          
          // ✅ GESTION D'ERREUR AMÉLIORÉE
          get().handleAuthError(error)
          
          toast.error(error.message || 'Erreur mise à jour consentements', {
            icon: '⚠️',
            duration: 4000
          })
          throw error
        }
      }
    }),
    {
      name: 'intelia-auth-storage',
      storage: createJSONStorage(() => {
        if (typeof window !== 'undefined') {
          return localStorage
        }
        return {
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {}
        }
      }),
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated 
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.setHasHydrated(true)
        }
      }
    }
  )
)

// 🔥 LISTENER SUPABASE ULTRA-SÉCURISÉ - AVEC THROTTLING RENFORCÉ
if (typeof window !== 'undefined') {
  supabase.auth.onAuthStateChange((event, session) => {
    const now = Date.now()
    
    // ✅ PROTECTION TEMPORELLE : Éviter les événements trop rapprochés
    if (now - lastAuthStateChange < AUTH_THROTTLE_DELAY) {
      console.log('🔄 [Auth] Événement trop rapide, ignoré:', event)
      return
    }
    
    lastAuthStateChange = now
    
    // 🔥 PROTECTION: Éviter les appels en cascade
    if (isListenerActive) {
      console.log('⚠️ [Auth] Listener déjà actif, abandon événement:', event)
      return
    }

    console.log('🔔 [Auth] État changé:', event)
    
    // 🔥 VERROUILLER LE LISTENER
    isListenerActive = true
    
    const store = useAuthStore.getState()
    
    if (event === 'SIGNED_OUT') {
      console.log('🚪 [Auth] Événement SIGNED_OUT détecté')
      store.clearAuth()
    } else if (event === 'SIGNED_IN' && session) {
      console.log('🔑 [Auth] Événement SIGNED_IN détecté')
      
      // 🔥 CORRECTION: Seulement mettre à jour si pas déjà authentifié
      if (!store.isAuthenticated) {
        const user: User = {
          id: session.user.id,
          email: session.user.email!,
          name: session.user.user_metadata?.name || session.user.email!.split('@')[0],
          user_type: session.user.user_metadata?.user_type || 'producer',
          language: session.user.user_metadata?.language || 'fr',
          avatar_url: session.user.user_metadata?.avatar_url || undefined,
          created_at: session.user.created_at || new Date().toISOString(),
          updated_at: new Date().toISOString(),
          consent_given: true,
          consent_date: new Date().toISOString()
        }
        
        useAuthStore.setState({
          user: user,
          isAuthenticated: true,
          isLoading: false,
          authErrors: [], // ✅ NETTOYER LES ERREURS
          isRecovering: false
        })
      } else {
        console.log('⚠️ [Auth] Utilisateur déjà authentifié, skip mise à jour')
      }
    } else if (event === 'TOKEN_REFRESHED' && session) {
      console.log('🔄 [Auth] Token rafraîchi')
      // Pas besoin de mettre à jour l'utilisateur pour un refresh
    } else if (event === 'INITIAL_SESSION') {
      // ✅ GESTION AMÉLIORÉE de la session initiale
      if (!store.isAuthenticated && session) {
        console.log('🔄 [Auth] Session initiale détectée')
        // Laisser initializeSession() gérer cela
      }
    }
    
    // 🔥 DÉBLOQUER LE LISTENER après un délai plus court
    setTimeout(() => {
      isListenerActive = false
    }, 50) // Réduit de 100ms à 50ms
  })
}