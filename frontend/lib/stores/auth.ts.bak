// lib/stores/auth.ts — Store d'auth SUPABASE (migré depuis auth-temp)
'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import toast from 'react-hot-toast'
import type { User as AppUser, RGPDConsent } from '@/types'
import { supabase } from '@/lib/supabase/client'

// ---- DEBUG ----
const AUTH_DEBUG = (
  (typeof window !== 'undefined' && (
    localStorage.getItem('AUTH_DEBUG') === '1' ||
    localStorage.getItem('SUPABASE_DEBUG') === '1'
  )) || process.env.NEXT_PUBLIC_AUTH_DEBUG === '1'
)
const alog = (...args: any[]) => {
  if (AUTH_DEBUG) {
    if (typeof window !== 'undefined') console.debug('[SupabaseAuthStore]', ...args)
    else console.debug('[SupabaseAuthStore/SSR]', ...args)
  }
}
const maskEmail = (e: string) => e?.replace(/(^.).*(@.*$)/, '$1***$2')

alog('✅ Loaded Supabase Auth Store from /lib/stores/auth.ts')

// ---- Configuration API ----
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://expert-app-cngws.ondigitalocean.app/api'
const API_TIMEOUT = 30000 // 30 secondes

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
        'Origin': 'https://expert.intelia.com',
        ...options.headers,
      },
    })
    
    clearTimeout(timeoutId)
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Erreur réseau' }))
      throw new Error(errorData.detail || errorData.message || `Erreur ${response.status}`)
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

// Fonction pour obtenir le token Supabase
async function getSupabaseToken(): Promise<string | null> {
  try {
    const { data: { session } } = await supabase.auth.getSession()
    const token = session?.access_token || null
    alog('🔑 Token Supabase:', token ? 'présent' : 'absent')
    return token
  } catch (error) {
    alog('❌ Erreur récupération token Supabase:', error)
    return null
  }
}

// Adapter les données utilisateur Supabase vers AppUser
function adaptSupabaseUser(supabaseUser: any, additionalData?: any): AppUser {
  const baseUser: AppUser = {
    id: supabaseUser.id,
    email: supabaseUser.email,
    user_type: additionalData?.user_type || 'producer',
    name: additionalData?.full_name || supabaseUser.user_metadata?.full_name || supabaseUser.email?.split('@')[0] || 'Utilisateur',
    language: additionalData?.language || 'fr',
  }

  // Ajouter les champs optionnels seulement s'ils existent dans le type AppUser
  if (additionalData?.phone && 'phone' in baseUser) {
    (baseUser as any).phone = additionalData.phone
  }
  if (additionalData?.company && 'company' in baseUser) {
    (baseUser as any).company = additionalData.company
  }
  if (additionalData?.rgpd_consent && 'rgpd_consent' in baseUser) {
    (baseUser as any).rgpd_consent = additionalData.rgpd_consent
  }

  return baseUser
}

// ---- Store Supabase ----
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
        console.error('⚠️ [SupabaseAuth]', ctx || '', error)
        set((s) => ({ authErrors: [...s.authErrors, msg] }))
      },

      clearAuthErrors: () => set({ authErrors: [] }),

      initializeSession: async () => {
        try {
          alog('🔄 initializeSession via Supabase')
          
          const { data: { session }, error } = await supabase.auth.getSession()
          
          if (error) {
            alog('❌ Erreur session Supabase:', error)
            set({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() })
            return false
          }

          if (!session || !session.user) {
            alog('❌ Pas de session Supabase')
            set({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() })
            return false
          }

          // 🆕 Récupérer le profil utilisateur depuis Supabase
          let profileData = {}
          try {
            const { data: profile } = await supabase
              .from('users')
              .select('*')
              .eq('auth_user_id', session.user.id)
              .single()
            
            if (profile) {
              profileData = profile
              alog('✅ Profil utilisateur trouvé:', profile.user_type)
            }
          } catch (profileError) {
            alog('⚠️ Pas de profil utilisateur trouvé, utilisation des valeurs par défaut')
          }

          const appUser = adaptSupabaseUser(session.user, profileData)

          set({ 
            user: appUser, 
            isAuthenticated: true, 
            lastAuthCheck: Date.now(), 
            isRecovering: false 
          })
          
          alog('✅ initializeSession success', appUser?.email && maskEmail(appUser.email))
          return true
          
        } catch (e) {
          get().handleAuthError(e, 'initializeSession')
          set({ isAuthenticated: false, user: null })
          return false
        }
      },

      checkAuth: async () => {
        try {
          const { data: { session } } = await supabase.auth.getSession()
          
          if (!session || !session.user) {
            set({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() })
            return
          }

          // 🆕 Récupérer le profil utilisateur mis à jour
          let profileData = {}
          try {
            const { data: profile } = await supabase
              .from('users')
              .select('*')
              .eq('auth_user_id', session.user.id)
              .single()
            
            if (profile) {
              profileData = profile
            }
          } catch (profileError) {
            alog('⚠️ Erreur récupération profil lors du checkAuth')
          }

          const appUser = adaptSupabaseUser(session.user, profileData)

          set({
            user: appUser,
            isAuthenticated: true,
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
        alog('🔄 login via Supabase', maskEmail(email))
        
        try {
          const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password
          })

          if (error) {
            throw new Error(error.message)
          }

          if (!data.user) {
            throw new Error('Aucun utilisateur retourné')
          }

          // 🆕 Récupérer le profil utilisateur
          let profileData = {}
          try {
            const { data: profile } = await supabase
              .from('users')
              .select('*')
              .eq('auth_user_id', data.user.id)
              .single()
            
            if (profile) {
              profileData = profile
            }
          } catch (profileError) {
            alog('⚠️ Pas de profil utilisateur trouvé lors du login')
          }

          const appUser = adaptSupabaseUser(data.user, profileData)

          set({ 
            user: appUser, 
            isAuthenticated: true,
            isLoading: false 
          })
          
          alog('✅ login success', appUser?.email && maskEmail(appUser.email))
          
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
        alog('🔄 register via Supabase', maskEmail(email))
        
        try {
          const fullName = (userData?.name || '').toString().trim()
          if (!fullName || fullName.length < 2) {
            throw new Error('Le nom doit contenir au moins 2 caractères')
          }

          // 🔑 Inscription Supabase
          const { data, error } = await supabase.auth.signUp({
            email,
            password,
            options: {
              data: {
                full_name: fullName,
                user_type: userData.user_type || 'producer',
                language: userData.language || 'fr'
              }
            }
          })

          if (error) {
            throw new Error(error.message)
          }

          if (!data.user) {
            throw new Error('Erreur lors de la création du compte')
          }

          // 🆕 Créer le profil utilisateur dans la table users
          if (data.user.id) {
            try {
              const profileData: any = {
                auth_user_id: data.user.id,
                email: email,
                full_name: fullName,
                user_type: userData.user_type || 'producer',
                language: userData.language || 'fr',
              }

              // Ajouter les champs optionnels seulement s'ils sont fournis et existent
              const userDataAny = userData as any
              if (userDataAny.phone) {
                profileData.phone = userDataAny.phone
              }
              if (userDataAny.company) {
                profileData.company = userDataAny.company
              }

              const { error: profileError } = await supabase
                .from('users')
                .insert(profileData)

              if (profileError) {
                alog('⚠️ Erreur création profil:', profileError)
              } else {
                alog('✅ Profil utilisateur créé')
              }
            } catch (profileError) {
              alog('⚠️ Erreur création profil:', profileError)
            }
          }

          const appUser = adaptSupabaseUser(data.user, {
            full_name: fullName,
            user_type: userData.user_type || 'producer',
            language: userData.language || 'fr',
            phone: (userData as any).phone,
            company: (userData as any).company,
          })

          set({ 
            user: appUser, 
            isAuthenticated: !!data.session,
            isLoading: false 
          })
          
          alog('✅ register success', appUser?.email && maskEmail(appUser.email))
          
          if (!data.session) {
            toast.success('Compte créé ! Vérifiez votre email pour confirmer votre inscription.')
          }
          
        } catch (e: any) {
          get().handleAuthError(e, 'register')
          alog('❌ register error', e?.message)
          
          let userMessage = e?.message || 'Erreur lors de la création du compte'
          
          // Messages d'erreur spécifiques Supabase
          if (userMessage.includes('already registered')) {
            userMessage = 'Cette adresse email est déjà utilisée'
          } else if (userMessage.includes('Password should be at least')) {
            userMessage = 'Le mot de passe doit contenir au moins 6 caractères'
          } else if (userMessage.includes('Invalid email')) {
            userMessage = 'Adresse email invalide'
          }
          
          toast.error(userMessage, { icon: '⚠️' })
          throw new Error(userMessage)
          
        } finally {
          set({ isLoading: false })
        }
      },

      logout: async () => {
        set({ isLoading: true })
        alog('🔄 logout via Supabase')
        
        try {
          const { error } = await supabase.auth.signOut()
          
          if (error) {
            throw new Error(error.message)
          }

          // Nettoyer le localStorage
          try {
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
        alog('🔄 updateProfile via Supabase', Object.keys(data || {}))
        
        try {
          const currentUser = get().user
          if (!currentUser) {
            throw new Error('Utilisateur non connecté')
          }

          // 🆕 Mettre à jour le profil dans Supabase
          const updateData: any = {}
          
          if (data.name !== undefined) updateData.full_name = data.name
          if (data.user_type !== undefined) updateData.user_type = data.user_type
          if (data.language !== undefined) updateData.language = data.language
          
          // Ajouter les champs optionnels seulement s'ils sont fournis
          const dataAny = data as any
          if (dataAny.phone !== undefined) updateData.phone = dataAny.phone
          if (dataAny.company !== undefined) updateData.company = dataAny.company

          const { error } = await supabase
            .from('users')
            .update(updateData)
            .eq('auth_user_id', currentUser.id)

          if (error) {
            throw new Error(error.message)
          }

          // Mettre à jour localement
          const updatedUser = { ...currentUser, ...data }
          set({ user: updatedUser })
          
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
        alog('🔄 updateConsent via Supabase', consent)
        
        // Mettre à jour seulement si le champ rgpd_consent existe dans AppUser
        const currentUser = get().user
        if (currentUser) {
          const currentUserAny = currentUser as any
          if ('rgpd_consent' in currentUserAny) {
            await get().updateProfile({ rgpd_consent: consent } as any)
          } else {
            // Sinon, juste mettre à jour dans Supabase
            try {
              const { error } = await supabase
                .from('users')
                .update({ rgpd_consent: consent })
                .eq('auth_user_id', currentUser?.id)

              if (error) {
                throw new Error(error.message)
              }
            } catch (e: any) {
              alog('❌ updateConsent error', e?.message)
              throw new Error(e?.message || 'Erreur de mise à jour du consentement')
            }
          }
        }
      },

      deleteUserData: async () => {
        const currentUser = get().user
        if (!currentUser) throw new Error('Non authentifié')

        try {
          // 🆕 Supprimer le profil utilisateur
          const { error } = await supabase
            .from('users')
            .delete()
            .eq('auth_user_id', currentUser.id)

          if (error) {
            alog('⚠️ Erreur suppression profil:', error)
          }

          // Supprimer le compte Supabase (nécessite des permissions spéciales)
          // Note: Cette fonctionnalité nécessite généralement un endpoint backend
          alog('⚠️ Suppression compte Supabase nécessite un endpoint backend')

          // Pour l'instant, juste déconnecter
          await get().logout()
          
        } catch (e: any) {
          alog('❌ deleteUserData error', e?.message)
          throw new Error(e?.message || 'Erreur de suppression des données')
        }
      },

      exportUserData: async () => {
        const currentUser = get().user
        if (!currentUser) throw new Error('Non authentifié')

        try {
          // 🆕 Récupérer toutes les données utilisateur
          const { data: profile } = await supabase
            .from('users')
            .select('*')
            .eq('auth_user_id', currentUser.id)
            .single()

          return {
            user_profile: profile,
            export_date: new Date().toISOString(),
            message: 'Données utilisateur exportées'
          }
          
        } catch (e: any) {
          alog('❌ exportUserData error', e?.message)
          throw new Error(e?.message || 'Erreur d\'exportation des données')
        }
      },
    }),
    {
      name: 'supabase-auth-store',
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
        if (error) console.error('❌ Supabase auth rehydrate error', error)
        state?.setHasHydrated(true)
        alog('✅ Supabase auth rehydrated')
      },
    }
  )
)