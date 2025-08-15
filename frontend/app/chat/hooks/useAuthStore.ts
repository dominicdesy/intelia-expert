

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User, BackendUserData, mapBackendUserToUser } from '../types'

interface AuthStore {
  // Actions d'authentification
  login: (email: string, password: string) => Promise<void>
  loginWithToken: (token: string) => Promise<void>
  logout: () => void
  register: (email: string, password: string, name?: string) => Promise<void>
  
  // Gestion utilisateur
  setUser: (user: User | null) => void
  updateUser: (userData: Partial<User>) => void
  refreshUser: () => Promise<void>
  
  // Récupération automatique au démarrage
  initializeAuth: () => Promise<void>
  
  // Gestion des erreurs
  error: string | null
  setError: (error: string | null) => void
  clearError: () => void
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      error: null,

      // ✅ LOGIN AVEC EMAIL/PASSWORD
      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        
        try {
          const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
          })
          
          if (!response.ok) {
            const errorData = await response.json()
            throw new Error(errorData.detail || 'Login failed')
          }
          
          const { access_token } = await response.json()
          
          // Utiliser loginWithToken pour récupérer les données utilisateur
          await get().loginWithToken(access_token)
          
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Login failed'
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false,
            error: errorMessage
          })
          throw error
        }
      },

      // ✅ LOGIN AVEC TOKEN (utilisé pour l'auto-login et après register)
      loginWithToken: async (token: string) => {
        set({ isLoading: true, error: null })
        
        try {
          // Récupérer les données utilisateur avec le token
          const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          
          if (!response.ok) {
            throw new Error('Failed to fetch user data')
          }
          
          const backendUserData: BackendUserData = await response.json()
          
          // ✅ CONVERSION: Backend -> Frontend User
          const user = mapBackendUserToUser(backendUserData)
          
          // Stocker le token
          localStorage.setItem('auth_token', token)
          
          set({ 
            user, 
            isAuthenticated: true, 
            isLoading: false,
            error: null
          })
          
        } catch (error) {
          console.error('Login with token failed:', error)
          // Nettoyer le token invalide
          localStorage.removeItem('auth_token')
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false,
            error: 'Session expired. Please login again.'
          })
          throw error
        }
      },

      // ✅ REGISTER
      register: async (email: string, password: string, name?: string) => {
        set({ isLoading: true, error: null })
        
        try {
          const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
              email, 
              password, 
              full_name: name 
            }),
          })
          
          if (!response.ok) {
            const errorData = await response.json()
            throw new Error(errorData.detail || 'Registration failed')
          }
          
          const { access_token } = await response.json()
          
          // Auto-login après registration
          await get().loginWithToken(access_token)
          
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Registration failed'
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false,
            error: errorMessage
          })
          throw error
        }
      },

      // ✅ LOGOUT
      logout: () => {
        localStorage.removeItem('auth_token')
        set({ 
          user: null, 
          isAuthenticated: false, 
          isLoading: false,
          error: null
        })
      },

      // ✅ SET USER
      setUser: (user: User | null) => {
        set({ 
          user, 
          isAuthenticated: !!user,
          error: null
        })
      },

      // ✅ UPDATE USER
      updateUser: (userData: Partial<User>) => {
        const currentUser = get().user
        if (currentUser) {
          set({ 
            user: { ...currentUser, ...userData } 
          })
        }
      },

      // ✅ REFRESH USER DATA
      refreshUser: async () => {
        const token = localStorage.getItem('auth_token')
        if (!token) {
          return
        }

        try {
          const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          
          if (!response.ok) {
            throw new Error('Failed to refresh user data')
          }
          
          const backendUserData: BackendUserData = await response.json()
          const user = mapBackendUserToUser(backendUserData)
          
          set({ user })
          
        } catch (error) {
          console.error('Failed to refresh user:', error)
          // Ne pas déconnecter automatiquement sur erreur de refresh
        }
      },

      // ✅ INITIALIZE AUTH (récupération auto au démarrage)
      initializeAuth: async () => {
        const token = localStorage.getItem('auth_token')
        if (!token) {
          set({ isLoading: false })
          return
        }

        try {
          await get().loginWithToken(token)
        } catch (error) {
          // Le token est invalide, l'utilisateur sera déconnecté automatiquement
          console.log('Auto-login failed, user needs to login again')
        }
      },

      // ✅ ERROR MANAGEMENT
      setError: (error: string | null) => {
        set({ error })
      },

      clearError: () => {
        set({ error: null })
      }
    }),
    {
      name: 'auth-storage',
      // Persister seulement les données nécessaires (pas le token pour sécurité)
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated 
      }),
      onRehydrateStorage: () => (state) => {
        // Initialiser l'auth après rehydration
        if (state) {
          state.initializeAuth()
        }
      }
    }
  )
)

// ✅ HOOK HELPER pour récupérer juste les données utilisateur
export const useUser = () => {
  const user = useAuthStore(state => state.user)
  const isAuthenticated = useAuthStore(state => state.isAuthenticated)
  const isLoading = useAuthStore(state => state.isLoading)
  
  return { user, isAuthenticated, isLoading }
}

// ✅ HOOK HELPER pour les actions d'auth
export const useAuth = () => {
  const login = useAuthStore(state => state.login)
  const logout = useAuthStore(state => state.logout)
  const register = useAuthStore(state => state.register)
  const refreshUser = useAuthStore(state => state.refreshUser)
  const error = useAuthStore(state => state.error)
  const clearError = useAuthStore(state => state.clearError)
  
  return { 
    login, 
    logout, 
    register, 
    refreshUser, 
    error, 
    clearError 
  }
}