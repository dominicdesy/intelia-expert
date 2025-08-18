// lib/stores/auth.ts — Store d'auth BACKEND API (robuste + timeout gérés)
'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import toast from 'react-hot-toast'
import type { User as AppUser, RGPDConsent } from '@/types'

// ---- DEBUG ----
const AUTH_DEBUG = (
  (typeof window !== 'undefined' && (
    localStorage.getItem('AUTH_DEBUG') === '1' ||
    localStorage.getItem('BACKEND_DEBUG') === '1'
  )) || process.env.NEXT_PUBLIC_AUTH_DEBUG === '1'
)
const alog = (...args: any[]) => {
  if (AUTH_DEBUG) {
    if (typeof window !== 'undefined') console.debug('[BackendAuthStore]', ...args)
    else console.debug('[BackendAuthStore/SSR]', ...args)
  }
}
const maskEmail = (e: string) => e?.replace(/(^.).*(@.*$)/, '$1***$2')

alog('✅ Loaded Backend Auth Store from /lib/stores/auth.ts')

// ---- Configuration API ----
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://expert-app-cngws.ondigitalocean.app'
const API_TIMEOUT = 30000 // 30 secondes (plus court que Supabase direct)

// ---- Types d'état du store ----
interface AuthState {
  // État
  user: AppUser | null
  isLoading: boolean
  isAuthenticated: boolean
  hasHydrated: boolean
  lastAuthCheck: number
  authErrors: string[]
  isRecovering: boolean
  sessionCheckCount: number

  // Actions
  setHasHydrated: (v: boolean) => void
  handleAuthError: (error: any, ctx?: string) => void
  clearAuthErrors: () => void
  initializeSession: () => Promise<boolean>
  checkAuth: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, userData: Partial<AppUser>) => Promise<void>
  logout: () => Promise<void>
  updateProfile: (data: Partial<AppUser>) => Promise<void>
  updateConsent: (consent: RGPDConsent) => Promise<void>
  deleteUserData: () => Promise<void>
  exportUserData: () => Promise<any>
}

// ---- Helpers API ----
const sleep = (ms: number) => new Promise(res => setTimeout(res, ms))

// Fetch avec timeout pour appels backend
async function apiCall(endpoint: string, options: RequestInit = {}) {
  const url = `${API_BASE_URL}${endpoint}`
  alog('🌐 API Call:', url)
  
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT)
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })
    
    clearTimeout(timeoutId)
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Erreur réseau' }))
      throw new Error(errorData.message || `Erreur ${response.status}`)
    }
    
    return await response.json()
    
  } catch (error: any) {
    clearTimeout(timeoutId)
    
    if (error.name === 'AbortError') {
      throw new Error('La requête a pris trop de temps. Vérifiez votre connexion.')
    }
    
    throw error
  }
}

// Fonction pour obtenir le token depuis localStorage/session
function getStoredToken(): string | null {
  try {
    // Vérifier dans localStorage, sessionStorage, ou cookie
    return localStorage.getItem('auth_token') || 
           sessionStorage.getItem('auth_token') ||
           null
  } catch {
    return null
  }
}

// ---- Store ----
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      hasHydrated: false,
      lastAuthCheck: 0,
      authErrors: [],
      isRecovering: false,
      sessionCheckCount: 0,

      setHasHydrated: (v: boolean) => set({ hasHydrated: v }),

      handleAuthError: (error: any, ctx?: string) => {
        const msg = (error?.message || 'Authentication error').toString()
        console.error('⚠️ [BackendAuth]', ctx || '', error)
        set((s) => ({ authErrors: [...s.authErrors, msg] }))
      },

      clearAuthErrors: () => set({ authErrors: [] }),

      initializeSession: async () => {
        try {
          alog('🔄 initializeSession via backend')
          
          const token = getStoredToken()
          if (!token) {
            alog('❌ No stored token found')
            set({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() })
            return false
          }

          // Vérifier le token avec le backend
          const userData = await apiCall('/api/auth/verify', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })

          const appUser = userData.user
          set({ 
            user: appUser, 
            isAuthenticated: !!appUser, 
            lastAuthCheck: Date.now(), 
            isRecovering: false 
          })
          
          alog('✅ initializeSession success', appUser?.email && maskEmail(appUser.email))
          return !!appUser
          
        } catch (e) {
          get().handleAuthError(e, 'initializeSession')
          // Token invalide, nettoyer
          try { 
            localStorage.removeItem('auth_token')
            sessionStorage.removeItem('auth_token')
          } catch {}
          set({ isAuthenticated: false, user: null })
          return false
        }
      },

      checkAuth: async () => {
        try {
          const token = getStoredToken()
          if (!token) {
            set({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() })
            return
          }

          const userData = await apiCall('/api/auth/verify', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
          })

          set({
            user: userData.user,
            isAuthenticated: !!userData.user,
            lastAuthCheck: Date.now(),
            sessionCheckCount: get().sessionCheckCount + 1,
            isRecovering: false,
          })
          
          alog('✅ checkAuth success', { checks: get().sessionCheckCount })
          
        } catch (e) {
          get().handleAuthError(e, 'checkAuth')
          set({ isAuthenticated: false, user: null })
        }
      },

      login: async (email: string, password: string) => {
        set({ isLoading: true })
        alog('🔄 login via backend', maskEmail(email))
        
        try {
          const result = await apiCall('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
          })

          // Stocker le token
          if (result.token) {
            localStorage.setItem('auth_token', result.token)
          }

          set({ 
            user: result.user, 
            isAuthenticated: !!result.user,
            isLoading: false 
          })
          
          alog('✅ login success', result.user?.email && maskEmail(result.user.email))
          
        } catch (e: any) {
          get().handleAuthError(e, 'login')
          alog('❌ login error', e?.message)
          throw new Error(e?.message || 'Erreur de connexion')
        } finally {
          set({ isLoading: false })
        }
      },

      register: async (email: string, password: string, userData: Partial<AppUser>) => {
        set({ isLoading: true, authErrors: [] })
        alog('🔄 register via backend', maskEmail(email))
        
        try {
          const fullName = (userData?.name || '').toString().trim()
          if (!fullName || fullName.length < 2) {
            throw new Error('Le nom doit contenir au moins 2 caractères')
          }

          // 🚀 APPEL BACKEND (robuste)
          const result = await apiCall('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({
              email: email.trim(),
              password,
              userData: {
                name: fullName,
                user_type: userData.user_type || 'producer',
                language: userData.language || 'fr',
                ...userData
              }
            })
          })

          // Stocker le token si fourni
          if (result.token) {
            localStorage.setItem('auth_token', result.token)
          }

          set({ 
            user: result.user, 
            isAuthenticated: !!result.user,
            isLoading: false 
          })

          alog('✅ register success via backend')
          toast.success('Compte créé avec succès ! Vérifiez vos emails si nécessaire.', { icon: '🎉' })
          
        } catch (e: any) {
          get().handleAuthError(e, 'register')
          alog('❌ register error', e?.message)
          
          // Messages d'erreur plus clairs
          let userMessage = e?.message || 'Erreur lors de la création du compte'
          
          if (userMessage.includes('already exists') || userMessage.includes('déjà utilisé')) {
            userMessage = 'Cette adresse email est déjà utilisée.'
          } else if (userMessage.includes('weak') || userMessage.includes('password')) {
            userMessage = 'Le mot de passe ne respecte pas les critères de sécurité.'
          } else if (userMessage.includes('timeout') || userMessage.includes('temps')) {
            userMessage = 'Le service met du temps à répondre. Réessayez dans quelques instants.'
          }
          
          toast.error(userMessage, { icon: '⚠️' })
          throw new Error(userMessage)
          
        } finally {
          set({ isLoading: false })
        }
      },

      logout: async () => {
        set({ isLoading: true })
        alog('🔄 logout via backend')
        
        try {
          const token = getStoredToken()
          
          // Appeler le backend pour logout (optionnel)
          if (token) {
            try {
              await apiCall('/api/auth/logout', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
              })
            } catch {
              // Ignorer les erreurs de logout backend
            }
          }

          // Nettoyer côté client
          try {
            localStorage.removeItem('auth_token')
            sessionStorage.removeItem('auth_token')
            localStorage.removeItem('intelia-chat-storage')
          } catch {}

          set({ user: null, isAuthenticated: false })
          alog('✅ logout success')
          
        } catch (e: any) {
          get().handleAuthError(e, 'logout')
          alog('❌ logout error', e?.message)
          throw new Error(e?.message || 'Erreur lors de la déconnexion')
        } finally {
          set({ isLoading: false })
        }
      },

      updateProfile: async (data: Partial<AppUser>) => {
        set({ isLoading: true })
        alog('🔄 updateProfile via backend', Object.keys(data || {}))
        
        try {
          const token = getStoredToken()
          if (!token) throw new Error('Non authentifié')

          const result = await apiCall('/api/auth/update-profile', {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(data)
          })

          set({ user: result.user || get().user })
          alog('✅ updateProfile success')
          
        } catch (e: any) {
          get().handleAuthError(e, 'updateProfile')
          alog('❌ updateProfile error', e?.message)
          throw new Error(e?.message || 'Erreur de mise à jour du profil')
        } finally {
          set({ isLoading: false })
        }
      },

      updateConsent: async (consent: RGPDConsent) => {
        alog('🔄 updateConsent via backend', consent)
        await get().updateProfile({ rgpd_consent: consent } as any)
      },

      deleteUserData: async () => {
        const token = getStoredToken()
        if (!token) throw new Error('Non authentifié')

        await apiCall('/api/auth/delete-user', {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        })
        
        // Nettoyer après suppression
        get().logout()
      },

      exportUserData: async () => {
        const token = getStoredToken()
        if (!token) throw new Error('Non authentifié')

        return await apiCall('/api/auth/export-user', {
          method: 'GET',
          headers: { 'Authorization': `Bearer ${token}` }
        })
      },
    }),
    {
      name: 'backend-auth-store',
      storage: createJSONStorage(() => {
        if (typeof window === 'undefined') {
          const noop = {
            getItem: async (_key: string) => null,
            setItem: async (_key: string, _value: string) => {},
            removeItem: async (_key: string) => {},
          }
          return noop as unknown as Storage
        }
        return window.localStorage
      }),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        lastAuthCheck: state.lastAuthCheck,
        hasHydrated: state.hasHydrated,
      }),
      onRehydrateStorage: () => (state, error) => {
        if (error) console.error('❌ Backend auth rehydrate error', error)
        state?.setHasHydrated(true)
        alog('✅ Backend auth rehydrated')
      },
    }
  )
)

// Export par défaut (compat)
export default useAuthStore