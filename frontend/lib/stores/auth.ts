// lib/stores/auth.ts — Store d'authentification stable (compat + correctifs timeouts/504)
// NOTE: Conserve l'API existante: useAuthStore (export nommé) + export default useAuthStore

'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import toast from 'react-hot-toast'
import { supabase, supabaseAuth } from '@/lib/supabase/client'
import type { User as AppUser, RGPDConsent } from '@/types'

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

// ---- Helpers ----
const sleep = (ms: number) => new Promise(res => setTimeout(res, ms))

function mapSessionToAppUser(sess: any): AppUser | null {
  const u = sess?.user
  if (!u) return null
  // On mape minimalement pour compat; adaptez si vos types sont différents
  const meta = u.user_metadata || {}
  const appUser: any = {
    id: u.id,
    email: u.email,
    name: meta.name || meta.full_name || '',
    user_type: meta.user_type || 'producer',
    language: meta.language || 'fr',
    // conservez d'autres champs si nécessaires...
    ...meta,
  }
  return appUser as AppUser
}

async function trySignInCheck(email: string, password: string) {
  const { data, error } = await supabaseAuth.auth.signInWithPassword({ email, password })

  if (data?.session) return { created: true as const, pendingEmailConfirm: false }

  const msg = (error?.message || '').toLowerCase()
  const code = (error as any)?.status || (error as any)?.code

  if (msg.includes('confirm') || msg.includes('not confirmed') || msg.includes('email not confirmed')) {
    return { created: true as const, pendingEmailConfirm: true }
  }
  if (msg.includes('invalid') || msg.includes('invalid login credentials') || code === 400) {
    return { created: false as const, pendingEmailConfirm: false }
  }
  return { created: null as const, pendingEmailConfirm: false, raw: error }
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
        console.error('⚠️ [Auth]', ctx || '', error)
        set((s) => ({ authErrors: [...s.authErrors, msg] }))
      },

      initializeSession: async () => {
        try {
          const { data: { session } } = await supabase.auth.getSession()
          const appUser = mapSessionToAppUser(session)
          set({
            user: appUser,
            isAuthenticated: !!session,
            lastAuthCheck: Date.now(),
            isRecovering: false,
          })
          return !!session
        } catch (e) {
          get().handleAuthError(e, 'initializeSession')
          set({ isAuthenticated: false, user: null })
          return false
        }
      },

      checkAuth: async () => {
        try {
          const { data: { session } } = await supabase.auth.getSession()
        const appUser = mapSessionToAppUser(session)
          set({
            user: appUser,
            isAuthenticated: !!session,
            lastAuthCheck: Date.now(),
            sessionCheckCount: get().sessionCheckCount + 1,
            isRecovering: false,
          })
        } catch (e) {
          get().handleAuthError(e, 'checkAuth')
          set({ isAuthenticated: false, user: null })
        }
      },

      login: async (email: string, password: string) => {
        set({ isLoading: true })
        try {
          const { data, error } = await supabaseAuth.auth.signInWithPassword({ email, password })
          if (error) throw error
          const appUser = mapSessionToAppUser(data?.session)
          set({ user: appUser, isAuthenticated: !!data?.session })
        } catch (e: any) {
          get().handleAuthError(e, 'login')
          throw new Error(e?.message || 'Erreur de connexion')
        } finally {
          set({ isLoading: false })
        }
      },

      register: async (email: string, password: string, userData: Partial<AppUser>) => {
        set({ isLoading: true })
        try {
          const fullName = (userData?.name || '').toString().trim()
          if (!fullName || fullName.length < 2) {
            throw new Error('Le nom doit contenir au moins 2 caractères')
          }

          const signUpOnce = async () => {
            return await supabaseAuth.auth.signUp({
              email,
              password,
              options: {
                data: {
                  name: fullName,
                  user_type: (userData as any)?.user_type || 'producer',
                  language: (userData as any)?.language || 'fr',
                },
                emailRedirectTo: typeof window !== 'undefined'
                  ? `${window.location.origin}/auth/callback`
                  : undefined,
              },
            })
          }

          // Essai #1
          const { error } = await signUpOnce()
          if (!error) {
            toast.success('Compte créé. Vérifiez vos e-mails si une confirmation est requise.', { icon: '📧' })
            return
          }

          // 504/timeout/réseau ?
          const status: any = (error as any)?.status || 0
          const msg = (error?.message || '').toLowerCase()
          const maybeTimeout =
            status === 504 ||
            msg.includes('timeout') ||
            msg.includes('gateway') ||
            msg.includes('network') ||
            msg.includes('fetch failed')

          if (maybeTimeout) {
            const check = await trySignInCheck(email, password)
            if (check.created === true) {
              if (check.pendingEmailConfirm) {
                throw Object.assign(new Error(
                  'Votre compte a été créé, mais vous devez confirmer votre adresse e-mail. Vérifiez votre boîte de réception.'
                ), { code: 'SIGNUP_CREATED_NEEDS_CONFIRM' })
              }
              return
            }

            await sleep(1500)
            const { error: again } = await signUpOnce()
            if (!again) return

            const recheck = await trySignInCheck(email, password)
            if (recheck.created === true) {
              if (recheck.pendingEmailConfirm) {
                throw Object.assign(new Error(
                  'Votre compte a été créé, mais vous devez confirmer votre adresse e-mail. Vérifiez votre boîte de réception.'
                ), { code: 'SIGNUP_CREATED_NEEDS_CONFIRM' })
              }
              return
            }

            throw Object.assign(new Error(
              'Le service d’inscription est temporairement indisponible (504). Réessayez plus tard.'
            ), { code: 'SIGNUP_TEMPORARY_DOWN' })
          }

          // Erreur fonctionnelle
          throw new Error(error?.message || 'Erreur lors de la création du compte')
        } catch (e: any) {
          get().handleAuthError(e, 'register')
          toast.error(e?.message || 'Erreur lors de la création du compte', { icon: '⚠️' })
          throw e
        } finally {
          set({ isLoading: false })
        }
      },

      logout: async () => {
        set({ isLoading: true })
        try {
          const { error } = await supabase.auth.signOut()
          if (error) throw error
          set({ user: null, isAuthenticated: false })
          try { localStorage.removeItem('intelia-chat-storage') } catch {}
        } catch (e: any) {
          get().handleAuthError(e, 'logout')
          throw new Error(e?.message || 'Erreur lors de la déconnexion')
        } finally {
          set({ isLoading: false })
        }
      },

      updateProfile: async (data: Partial<AppUser>) => {
        set({ isLoading: true })
        try {
          const { data: upd, error } = await supabase.auth.updateUser({ data })
          if (error) throw error
          const appUser = mapSessionToAppUser({ user: upd?.user })
          set({ user: appUser || get().user })
        } catch (e: any) {
          get().handleAuthError(e, 'updateProfile')
          throw new Error(e?.message || 'Erreur de mise à jour du profil')
        } finally {
          set({ isLoading: false })
        }
      },

      updateConsent: async (consent: RGPDConsent) => {
        // Stocke le consentement dans le profil (métadonnées)
        await get().updateProfile({ rgpd_consent: consent } as any)
      },

      deleteUserData: async () => {
        // Placeholder : implémentez votre effacement backend si nécessaire
        console.warn('deleteUserData: non implémenté côté client')
      },

      exportUserData: async () => {
        // Placeholder : implémentez votre export backend si nécessaire
        console.warn('exportUserData: non implémenté côté client')
        return null
      },
    }),
    {
      name: 'auth-store',
      storage: createJSONStorage(() => {
        if (typeof window === 'undefined') {
          // No-op storage for SSR safety
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
        if (error) {
          console.error('❌ Persist rehydrate error', error)
        }
        state?.setHasHydrated(true)
      },
    }
  )
)

// ---- Abonnement aux changements d’auth pour garder le store à jour ----
let authListenerAttached = false
export function attachAuthStateChangeListener() {
  if (authListenerAttached) return
  authListenerAttached = true

  supabase.auth.onAuthStateChange(async (event, session) => {
    const store = useAuthStore.getState()

    if (event === 'SIGNED_IN' && session) {
      const appUser = mapSessionToAppUser(session)
      useAuthStore.setState({ user: appUser, isAuthenticated: true, isRecovering: false })
    } else if (event === 'SIGNED_OUT') {
      useAuthStore.setState({ user: null, isAuthenticated: false })
    } else if (event === 'TOKEN_REFRESHED') {
      // rien à faire; l'utilisateur reste connecté
    } else if (event === 'INITIAL_SESSION') {
      // Laisse initializeSession gérer
    }
  })
}

// Export par défaut pour compat
export default useAuthStore
