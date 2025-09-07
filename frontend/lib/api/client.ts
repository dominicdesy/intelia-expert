// SYSTÈME D'AUTH UNIFIÉ - BACKEND ONLY
// lib/stores/auth.ts - Version simplifiée qui utilise UNIQUEMENT le backend

'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { apiClient } from '@/lib/api/client'
import type { User as AppUser } from '@/types'

// Types d'état du store
interface AuthState {
  user: AppUser | null
  isLoading: boolean
  isAuthenticated: boolean
  hasHydrated: boolean
  lastAuthCheck: number
  authErrors: string[]

  // Actions
  setHasHydrated: (v: boolean) => void
  handleAuthError: (error: any, ctx?: string) => void
  clearAuthErrors: () => void
  checkAuth: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, userData: Partial<AppUser>) => Promise<void>
  logout: () => Promise<void>
  updateProfile: (data: Partial<AppUser>) => Promise<void>
  getAuthToken: () => Promise<string | null>
}

// Store unifié utilisant UNIQUEMENT le backend
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      hasHydrated: false,
      lastAuthCheck: 0,
      authErrors: [],

      setHasHydrated: (v: boolean) => {
        set({ hasHydrated: v })
      },

      handleAuthError: (error: any, ctx?: string) => {
        const msg = (error?.message || 'Authentication error').toString()
        console.error('[AuthStore]', ctx || '', error)
        set((s) => ({ authErrors: [...s.authErrors, msg] }))
      },

      clearAuthErrors: () => {
        set({ authErrors: [] })
      },

      // ✅ CHECK AUTH : Utilise /auth/me
      checkAuth: async () => {
        try {
          console.log('[AuthStore] Vérification auth via /auth/me')
          
          const response = await apiClient.getSecure('/auth/me')
          
          if (response.success && response.data) {
            const userData = response.data
            
            // Adapter les données backend vers AppUser
            const appUser: AppUser = {
              id: userData.user_id,
              email: userData.email,
              name: userData.full_name || userData.email?.split('@')[0] || 'Utilisateur',
              firstName: userData.full_name?.split(' ')[0] || '',
              lastName: userData.full_name?.split(' ').slice(1).join(' ') || '',
              phone: userData.phone || '',
              country: userData.country || '',
              linkedinProfile: userData.linkedin_profile || '',
              companyName: userData.company_name || '',
              companyWebsite: userData.company_website || '',
              linkedinCorporate: userData.linkedin_corporate || '',
              user_type: userData.user_type || 'producer',
              language: userData.language || 'fr',
              created_at: userData.created_at || new Date().toISOString(),
              plan: userData.plan || 'essential',
              full_name: userData.full_name,
              avatar_url: userData.avatar_url,
              consent_given: userData.consent_given ?? true,
              consent_date: userData.consent_date,
              updated_at: userData.updated_at,
              user_id: userData.user_id,
              profile_id: userData.profile_id,
              preferences: userData.preferences || {},
              is_admin: userData.is_admin || false
            }

            set({ 
              user: appUser, 
              isAuthenticated: true, 
              lastAuthCheck: Date.now(),
              authErrors: []
            })
            
            console.log('[AuthStore] Auth réussie:', appUser.email)
          } else {
            set({ 
              user: null, 
              isAuthenticated: false, 
              lastAuthCheck: Date.now() 
            })
            console.log('[AuthStore] Non authentifié')
          }
        } catch (e: any) {
          console.error('[AuthStore] Erreur checkAuth:', e)
          set({ 
            user: null, 
            isAuthenticated: false, 
            lastAuthCheck: Date.now() 
          })
        }
      },

      // ✅ LOGIN : Utilise /auth/login
      login: async (email: string, password: string) => {
        set({ isLoading: true, authErrors: [] })
        console.log('[AuthStore] Login via /auth/login:', email)
        
        try {
          const response = await apiClient.post('/auth/login', {
            email,
            password
          })

          if (!response.success) {
            throw new Error(response.error?.message || 'Erreur de connexion')
          }

          const { access_token, expires_at } = response.data

          // Sauvegarder le token dans localStorage
          const authData = {
            access_token,
            expires_at,
            token_type: 'bearer',
            synced_at: Date.now()
          }
          localStorage.setItem('intelia-expert-auth', JSON.stringify(authData))

          // Vérifier l'auth pour récupérer les données utilisateur
          await get().checkAuth()
          
          set({ isLoading: false })
          
          // Déclencher l'événement de redirection
          setTimeout(() => {
            window.dispatchEvent(new Event('auth-state-changed'))
          }, 100)
          
          console.log('[AuthStore] Login réussi')
          
        } catch (e: any) {
          get().handleAuthError(e, 'login')
          
          let userMessage = e?.message || 'Erreur de connexion'
          if (userMessage.includes('Invalid login credentials')) {
            userMessage = 'Email ou mot de passe incorrect'
          } else if (userMessage.includes('Email not confirmed')) {
            userMessage = 'Veuillez confirmer votre email avant de vous connecter'
          }
          
          set({ isLoading: false })
          throw new Error(userMessage)
        }
      },

      // ✅ REGISTER : Utilise /auth/register
      register: async (email: string, password: string, userData: Partial<AppUser>) => {
        set({ isLoading: true, authErrors: [] })
        console.log('[AuthStore] Register via /auth/register:', email)
        
        try {
          const fullName = userData?.name || ''
          if (!fullName || fullName.length < 2) {
            throw new Error('Le nom doit contenir au moins 2 caractères')
          }

          const response = await apiClient.post('/auth/register', {
            email,
            password,
            full_name: fullName,
            first_name: userData.firstName,
            last_name: userData.lastName,
            company: userData.companyName,
            phone: userData.phone
          })

          if (!response.success) {
            throw new Error(response.error?.message || 'Erreur lors de la création du compte')
          }

          const { token, user } = response.data

          if (token) {
            // Sauvegarder le token
            const authData = {
              access_token: token,
              token_type: 'bearer',
              synced_at: Date.now()
            }
            localStorage.setItem('intelia-expert-auth', JSON.stringify(authData))

            // Récupérer les données utilisateur
            await get().checkAuth()
          }
          
          set({ isLoading: false })
          console.log('[AuthStore] Register réussi')
          
        } catch (e: any) {
          get().handleAuthError(e, 'register')
          
          let userMessage = e?.message || 'Erreur lors de la création du compte'
          
          if (userMessage.includes('already registered')) {
            userMessage = 'Cette adresse email est déjà utilisée'
          } else if (userMessage.includes('Password should be at least')) {
            userMessage = 'Le mot de passe doit contenir au moins 6 caractères'
          }
          
          set({ isLoading: false })
          throw new Error(userMessage)
        }
      },

      // ✅ LOGOUT : Nettoyage simple
      logout: async () => {
        console.log('[AuthStore] Logout - nettoyage localStorage')
        
        try {
          // Nettoyage localStorage sélectif
          const keysToRemove = []
          
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i)
            if (key && key !== 'intelia-remember-me-persist') {
              if (key.startsWith('supabase-') || 
                  key.startsWith('intelia-') && key !== 'intelia-remember-me-persist' ||
                  key.includes('auth') || 
                  key.includes('session') ||
                  key === 'intelia-expert-auth') {
                keysToRemove.push(key)
              }
            }
          }
          
          keysToRemove.forEach(key => {
            localStorage.removeItem(key)
          })
          
          // Reset du store
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            authErrors: [],
            lastAuthCheck: Date.now()
          })

          sessionStorage.setItem('recent-logout', Date.now().toString())
          console.log('[AuthStore] Logout réussi')
          
        } catch (e: any) {
          console.error('[AuthStore] Erreur logout:', e)
          throw new Error(e?.message || 'Erreur lors de la déconnexion')
        }
      },

      // ✅ UPDATE PROFILE : Via backend si endpoint disponible
      updateProfile: async (data: Partial<AppUser>) => {
        set({ isLoading: true })
        console.log('[AuthStore] UpdateProfile')
        
        try {
          const currentUser = get().user
          if (!currentUser) {
            throw new Error('Utilisateur non connecté')
          }

          // Mise à jour locale immédiate
          const updatedUser = { 
            ...currentUser,
            ...data,
            email: currentUser.email, // L'email ne change jamais
          }
          
          set({ user: updatedUser, isLoading: false })
          console.log('[AuthStore] Profil mis à jour localement')
          
          // TODO: Ajouter appel backend si endpoint /auth/profile existe
          
        } catch (e: any) {
          get().handleAuthError(e, 'updateProfile')
          set({ isLoading: false })
          throw new Error(e?.message || 'Erreur de mise à jour du profil')
        }
      },

      // ✅ GET AUTH TOKEN : Depuis localStorage uniquement
      getAuthToken: async () => {
        try {
          const authData = localStorage.getItem('intelia-expert-auth')
          if (!authData) return null
          
          const parsed = JSON.parse(authData)
          return parsed.access_token || null
        } catch (error) {
          console.error('[AuthStore] Erreur récupération token:', error)
          return null
        }
      },
    }),
    {
      name: 'intelia-auth-store', // Nouveau nom pour éviter les conflits
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        lastAuthCheck: state.lastAuthCheck,
        hasHydrated: state.hasHydrated,
      }),
      onRehydrateStorage: () => (state, error) => {
        if (error) console.error('Erreur rehydrate auth store:', error)
        
        // Protection contre la rehydration pendant une déconnexion récente
        const recentLogout = sessionStorage.getItem('recent-logout')
        if (recentLogout) {
          const logoutTime = parseInt(recentLogout)
          if (Date.now() - logoutTime < 1000) {
            console.log('[AuthStore] Rehydration bloquée - déconnexion récente')
            if (state) {
              state.user = null
              state.isAuthenticated = false
            }
            return
          }
        }
        
        if (state) {
          state.setHasHydrated(true)
          console.log('[AuthStore] Store rehydraté')
        }
      },
    }
  )
)

// Fonction utilitaire exportée
export const getAuthToken = async (): Promise<string | null> => {
  try {
    const authData = localStorage.getItem('intelia-expert-auth')
    if (!authData) return null
    
    const parsed = JSON.parse(authData)
    return parsed.access_token || null
  } catch (error) {
    console.error('[AuthStore] Erreur récupération token utilitaire:', error)
    return null
  }
}