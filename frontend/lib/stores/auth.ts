// lib/stores/auth.ts - SYSTÈME D'AUTH UNIFIÉ - BACKEND ONLY
// Version backend-centralisée pour OAuth

'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { apiClient } from '@/lib/api/client'
import type { User as AppUser } from '@/types'

// Interface pour les données utilisateur du backend
interface BackendUserData {
  user_id: string
  email: string
  full_name?: string
  phone?: string
  country?: string
  linkedin_profile?: string
  company_name?: string
  company_website?: string
  linkedin_corporate?: string
  user_type?: string
  language?: string
  created_at?: string
  plan?: string
  avatar_url?: string
  consent_given?: boolean
  consent_date?: string
  updated_at?: string
  profile_id?: string
  preferences?: any
  is_admin?: boolean
}

// Types d'état du store
interface AuthState {
  user: AppUser | null
  isLoading: boolean
  isAuthenticated: boolean
  hasHydrated: boolean
  lastAuthCheck: number
  authErrors: string[]
  isOAuthLoading: string | null  // Provider en cours de connexion OAuth

  // Actions existantes
  setHasHydrated: (v: boolean) => void
  handleAuthError: (error: any, ctx?: string) => void
  clearAuthErrors: () => void
  checkAuth: () => Promise<void>
  initializeSession: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, userData: Partial<AppUser>) => Promise<void>
  logout: () => Promise<void>
  updateProfile: (data: Partial<AppUser>) => Promise<void>
  getAuthToken: () => Promise<string | null>
  updateConsent: (consentGiven: boolean) => Promise<void>
  exportUserData: () => Promise<any>
  deleteUserData: () => Promise<void>
  
  // 🆕 ACTIONS OAUTH BACKEND-CENTRALISÉES
  loginWithOAuth: (provider: 'linkedin' | 'facebook') => Promise<void>
  handleOAuthTokenFromURL: () => Promise<void>
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
      isOAuthLoading: null,

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

      // ✅ INITIALIZE SESSION - Méthode ajoutée
      initializeSession: async () => {
        console.log('[AuthStore] Initialisation de session...')
        
        try {
          // 🆕 NOUVEAU: Vérifier d'abord s'il y a un token OAuth dans l'URL
          await get().handleOAuthTokenFromURL()
          
          // Vérifier si un token existe dans localStorage
          const authData = localStorage.getItem('intelia-expert-auth')
          
          if (authData) {
            // Si token existe, vérifier l'authentification
            await get().checkAuth()
          } else {
            // Aucun token, utilisateur non authentifié
            set({ 
              user: null, 
              isAuthenticated: false,
              lastAuthCheck: Date.now()
            })
            console.log('[AuthStore] Aucun token trouvé - session non initialisée')
          }
        } catch (error) {
          console.error('[AuthStore] Erreur initialisation session:', error)
          get().handleAuthError(error, 'initializeSession')
          
          // En cas d'erreur, reset l'état
          set({ 
            user: null, 
            isAuthenticated: false,
            lastAuthCheck: Date.now()
          })
        }
      },

      // CHECK AUTH : Utilise /auth/me
      checkAuth: async () => {
        try {
          console.log('[AuthStore] Vérification auth via /auth/me')
          
          const response = await apiClient.getSecure<BackendUserData>('/auth/me')
          
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

      // LOGIN : Utilise /auth/login
      login: async (email: string, password: string) => {
        set({ isLoading: true, authErrors: [] })
        console.log('[AuthStore] Login via /auth/login:', email)
        
        try {
          const response = await apiClient.post<{access_token: string, expires_at?: string}>('/auth/login', {
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

      // 🆕 LOGIN WITH OAUTH : REDIRECTION DIRECTE VERS BACKEND
      loginWithOAuth: async (provider: 'linkedin' | 'facebook') => {
        set({ isOAuthLoading: provider, authErrors: [] })
        console.log(`[AuthStore] OAuth login initié pour ${provider} - redirection directe vers backend`)
        
        try {
          // Construire l'URL du backend OAuth
          const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app/api'
          const oauthUrl = `${backendUrl}/v1/auth/oauth/${provider}/login`
          
          console.log(`[AuthStore] Redirection vers:`, oauthUrl)
          
          // Redirection directe vers le backend - pas d'API call
          window.location.href = oauthUrl
          
        } catch (e: any) {
          console.error(`[AuthStore] Erreur OAuth ${provider}:`, e)
          get().handleAuthError(e, `loginWithOAuth-${provider}`)
          
          let userMessage = e?.message || `Erreur de connexion avec ${provider}`
          
          set({ isOAuthLoading: null })
          throw new Error(userMessage)
        }
      },

      // 🆕 HANDLE OAUTH TOKEN FROM URL : Récupère le token depuis l'URL après redirection backend
      handleOAuthTokenFromURL: async () => {
        try {
          // Vérifier s'il y a des paramètres OAuth dans l'URL
          const urlParams = new URLSearchParams(window.location.search)
          const oauthToken = urlParams.get('oauth_token')
          const oauthSuccess = urlParams.get('oauth_success')
          const oauthProvider = urlParams.get('oauth_provider')
          const oauthEmail = urlParams.get('oauth_email')
          
          if (oauthSuccess === 'true' && oauthToken) {
            console.log('[AuthStore] Token OAuth détecté dans l\'URL')
            
            // Stocker le token dans localStorage
            const authData = {
              access_token: oauthToken,
              token_type: 'bearer',
              synced_at: Date.now(),
              oauth_provider: oauthProvider
            }
            localStorage.setItem('intelia-expert-auth', JSON.stringify(authData))
            
            // Nettoyer l'URL
            const cleanUrl = new URL(window.location.href)
            cleanUrl.searchParams.delete('oauth_token')
            cleanUrl.searchParams.delete('oauth_success')
            cleanUrl.searchParams.delete('oauth_email')
            cleanUrl.searchParams.delete('oauth_provider')
            window.history.replaceState({}, '', cleanUrl.pathname + cleanUrl.search)
            
            // Vérifier l'auth pour récupérer les données utilisateur complètes
            await get().checkAuth()
            
            // Reset du loading OAuth
            set({ isOAuthLoading: null })
            
            // Déclencher l'événement de redirection
            setTimeout(() => {
              window.dispatchEvent(new Event('auth-state-changed'))
            }, 100)
            
            console.log(`[AuthStore] OAuth ${oauthProvider} réussi:`, oauthEmail)
            return true
          }
          
          // Vérifier les erreurs OAuth
          const oauthError = urlParams.get('oauth_error')
          if (oauthError) {
            console.error('[AuthStore] Erreur OAuth dans l\'URL:', oauthError)
            
            // Nettoyer l'URL
            const cleanUrl = new URL(window.location.href)
            cleanUrl.searchParams.delete('oauth_error')
            window.history.replaceState({}, '', cleanUrl.pathname + cleanUrl.search)
            
            // Reset du loading et ajouter l'erreur
            set({ isOAuthLoading: null })
            get().handleAuthError({ message: decodeURIComponent(oauthError) }, 'oauth-url-error')
            
            return false
          }
          
          return false
          
        } catch (error) {
          console.error('[AuthStore] Erreur traitement token OAuth URL:', error)
          set({ isOAuthLoading: null })
          return false
        }
      },

      // REGISTER : Utilise /auth/register
      register: async (email: string, password: string, userData: Partial<AppUser>) => {
        set({ isLoading: true, authErrors: [] })
        console.log('[AuthStore] Register via /auth/register:', email)
        
        try {
          const fullName = userData?.name || ''
          if (!fullName || fullName.length < 2) {
            throw new Error('Le nom doit contenir au moins 2 caractères')
          }

          const response = await apiClient.post<{token?: string, user?: any}>('/auth/register', {
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

      // LOGOUT : Nettoyage simple
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
          
          // Nettoyer aussi sessionStorage OAuth
          sessionStorage.removeItem('oauth_state')
          sessionStorage.removeItem('oauth_provider')
          
          // Reset du store
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            isOAuthLoading: null,
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

      // UPDATE PROFILE : Via backend si endpoint disponible
      updateProfile: async (data: Partial<AppUser>) => {
        set({ isLoading: true })
        console.log('[AuthStore] UpdateProfile')
        
        try {
          const currentUser = get().user
          if (!currentUser) {
            throw new Error('Utilisateur non connecté')
          }

          // Préparer les données pour l'API backend
          const apiData: any = {}

          if (data.firstName !== undefined) {
            apiData.first_name = String(data.firstName).trim()
          }

          if (data.lastName !== undefined) {
            apiData.last_name = String(data.lastName).trim()
          }

          // Construire full_name à partir des composants
          if (data.firstName !== undefined || data.lastName !== undefined) {
            const fullName = `${data.firstName || ''} ${data.lastName || ''}`.trim()
            apiData.full_name = fullName
          }

          // Ajouter les autres champs
          if (data.country_code !== undefined) apiData.country_code = data.country_code
          if (data.area_code !== undefined) apiData.area_code = data.area_code
          if (data.phone_number !== undefined) apiData.phone_number = data.phone_number
          if (data.country !== undefined) apiData.country = data.country
          if (data.linkedinProfile !== undefined) apiData.linkedin_profile = data.linkedinProfile
          if (data.companyName !== undefined) apiData.company_name = data.companyName
          if (data.companyWebsite !== undefined) apiData.company_website = data.companyWebsite
          if (data.linkedinCorporate !== undefined) apiData.linkedin_corporate = data.linkedinCorporate

          console.log('[AuthStore] Envoi vers API backend via apiClient:', '/users/profile')

          // Utiliser apiClient.putSecure() pour mettre à jour le profil
          const response = await apiClient.putSecure<{success: boolean, message: string, user: any}>('/users/profile', apiData)
          
          if (!response.success) {
            throw new Error(response.error?.message || 'Erreur lors de la mise à jour du profil')
          }

          console.log('[AuthStore] Profil mis à jour avec succès:', response.data?.success)

          // Recharger les données utilisateur
          await get().checkAuth()
          
          set({ isLoading: false })
          console.log('[AuthStore] Profil mis à jour et rechargé')
          
        } catch (e: any) {
          get().handleAuthError(e, 'updateProfile')
          set({ isLoading: false })
          throw new Error(e?.message || 'Erreur de mise à jour du profil')
        }
      },

      // GET AUTH TOKEN : Depuis localStorage uniquement
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

      // ✅ UPDATE CONSENT - Gestion du consentement RGPD
      updateConsent: async (consentGiven: boolean) => {
        console.log('[AuthStore] Mise à jour du consentement:', consentGiven)
        
        try {
          const currentUser = get().user
          if (!currentUser) {
            throw new Error('Utilisateur non connecté')
          }

          const response = await apiClient.putSecure('/users/consent', {
            consent_given: consentGiven,
            consent_date: new Date().toISOString()
          })
          
          if (!response.success) {
            throw new Error(response.error?.message || 'Erreur lors de la mise à jour du consentement')
          }

          // Recharger les données utilisateur pour refléter le changement
          await get().checkAuth()
          
          console.log('[AuthStore] Consentement mis à jour avec succès')
          
        } catch (e: any) {
          get().handleAuthError(e, 'updateConsent')
          throw new Error(e?.message || 'Erreur lors de la mise à jour du consentement')
        }
      },

      // ✅ EXPORT USER DATA - Conformité RGPD
      exportUserData: async () => {
        console.log('[AuthStore] Export des données utilisateur (RGPD)')
        
        try {
          const currentUser = get().user
          if (!currentUser) {
            throw new Error('Utilisateur non connecté')
          }

          const response = await apiClient.getSecure('/users/export-data')
          
          if (!response.success) {
            throw new Error(response.error?.message || 'Erreur lors de l\'export des données')
          }

          console.log('[AuthStore] Export des données réussi')
          return response.data
          
        } catch (e: any) {
          get().handleAuthError(e, 'exportUserData')
          throw new Error(e?.message || 'Erreur lors de l\'export des données')
        }
      },

      // ✅ DELETE USER DATA - Suppression compte RGPD
      deleteUserData: async () => {
        console.log('[AuthStore] Suppression des données utilisateur (RGPD)')
        
        try {
          const currentUser = get().user
          if (!currentUser) {
            throw new Error('Utilisateur non connecté')
          }

          const response = await apiClient.deleteSecure<any>('/users/delete-account')
          
          if (!response.success) {
            throw new Error(response.error?.message || 'Erreur lors de la suppression du compte')
          }

          // Déconnexion automatique après suppression
          await get().logout()
          
          console.log('[AuthStore] Suppression du compte réussie')
          
        } catch (e: any) {
          get().handleAuthError(e, 'deleteUserData')
          throw new Error(e?.message || 'Erreur lors de la suppression du compte')
        }
      },
    }),
    {
      name: 'intelia-auth-store',
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