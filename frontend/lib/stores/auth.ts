// lib/stores/auth.ts — Store d'auth robuste (timeouts/504 gérés) + DEBUG + exports nommés & défaut
'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import toast from 'react-hot-toast'
import { supabase, supabaseAuth } from '@/lib/supabase/client'
import type { User as AppUser, RGPDConsent } from '@/types' // Ajustez si nécessaire

// ---- DEBUG ----
const AUTH_DEBUG = (
  (typeof window !== 'undefined' && (
    localStorage.getItem('AUTH_DEBUG') === '1' ||
    localStorage.getItem('SUPABASE_DEBUG') === '1'
  )) || process.env.NEXT_PUBLIC_AUTH_DEBUG === '1'
)
const alog = (...args: any[]) => {
  if (AUTH_DEBUG) {
    if (typeof window !== 'undefined') console.debug('[AuthStore]', ...args)
    else console.debug('[AuthStore/SSR]', ...args)
  }
}
const maskEmail = (e: string) => e?.replace(/(^.).*(@.*$)/, '$1***$2')

alog('✅ Loaded from /lib/stores/auth.ts')

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

// ---- Helpers ----
const sleep = (ms: number) => new Promise(res => setTimeout(res, ms))

type SignInCheck =
  | { created: true; pendingEmailConfirm: boolean }
  | { created: false; pendingEmailConfirm: false }
  | { created: null; pendingEmailConfirm: false; raw?: any }

function mapSessionToAppUser(sess: any): AppUser | null {
  const u = sess?.user
  if (!u) return null
  const meta = u.user_metadata || {}
  const appUser: any = {
    id: u.id,
    email: u.email,
    name: meta.name || meta.full_name || '',
    user_type: meta.user_type || 'producer',
    language: meta.language || 'fr',
    ...meta,
  }
  return appUser as AppUser
}

async function trySignInCheck(email: string, password: string): Promise<SignInCheck> {
  alog('trySignInCheck()', maskEmail(email))
  const { data, error } = await supabaseAuth.auth.signInWithPassword({ email, password })
  if (data?.session) {
    alog('trySignInCheck → session present')
    return { created: true, pendingEmailConfirm: false }
  }

  const msg = (error?.message || '').toLowerCase()
  const code = (error as any)?.status || (error as any)?.code
  alog('trySignInCheck → no session', { code, msg })

  if (msg.includes('confirm') || msg.includes('not confirmed') || msg.includes('email not confirmed')) {
    alog('trySignInCheck → created but pending email confirmation')
    return { created: true, pendingEmailConfirm: true }
  }
  if (msg.includes('invalid') || msg.includes('invalid login credentials') || code === 400) {
    return { created: false, pendingEmailConfirm: false }
  }
  return { created: null, pendingEmailConfirm: false, raw: error }
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

      clearAuthErrors: () => set({ authErrors: [] }),

      initializeSession: async () => {
        try {
          const { data: { session } } = await supabase.auth.getSession()
          const appUser = mapSessionToAppUser(session)
          set({ user: appUser, isAuthenticated: !!session, lastAuthCheck: Date.now(), isRecovering: false })
          alog('initializeSession →', { isAuth: !!session, email: appUser?.email && maskEmail(appUser.email) })
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
          alog('checkAuth →', { isAuth: !!session, checks: get().sessionCheckCount })
        } catch (e) {
          get().handleAuthError(e, 'checkAuth')
          set({ isAuthenticated: false, user: null })
        }
      },

      login: async (email: string, password: string) => {
        set({ isLoading: true })
        alog('login()', maskEmail(email))
        try {
          const { data, error } = await supabaseAuth.auth.signInWithPassword({ email, password })
          if (error) throw error
          const appUser = mapSessionToAppUser(data?.session)
          set({ user: appUser, isAuthenticated: !!data?.session })
          alog('login → success', appUser?.email && maskEmail(appUser.email))
        } catch (e: any) {
          get().handleAuthError(e, 'login')
          alog('login → error', e?.message)
          throw new Error(e?.message || 'Erreur de connexion')
        } finally {
          set({ isLoading: false })
        }
      },

      register: async (email: string, password: string, userData: Partial<AppUser>) => {
        set({ isLoading: true, authErrors: [] })
        alog('register()', maskEmail(email))
        try {
          const fullName = (userData?.name || '').toString().trim()
          if (!fullName || fullName.length < 2) {
            throw new Error('Le nom doit contenir au moins 2 caractères')
          }

          const signUpOnce = async () => {
            alog('signUpOnce → calling supabaseAuth.auth.signUp')
            return await supabaseAuth.auth.signUp({
              email,
              password,
              options: {
                data: {
                  name: fullName,
                  user_type: (userData as any)?.user_type || 'producer',
                  language: (userData as any)?.language || 'fr',
                },
                emailRedirectTo: typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : undefined,
              },
            })
          }

          // Essai #1
          const { error } = await signUpOnce()
          if (!error) {
            alog('register → success (first attempt)')
            toast.success('Compte créé. Vérifiez vos e‑mails si une confirmation est requise.', { icon: '📧' })
            return
          }

          // 504/timeout/réseau ?
          const status: any = (error as any)?.status || 0
          const msg = (error?.message || '').toLowerCase()
          const name = (error as any)?.name || ''
          const causeMsg = String((error as any)?.cause?.message || (error as any)?.cause || '').toLowerCase()
          const maybeTimeout =
            status === 504 ||
            name === 'AbortError' ||
            msg.includes('timeout') || causeMsg.includes('timeout') ||
            msg.includes('aborted') || msg.includes('abort') ||
            msg.includes('gateway') || msg.includes('network') ||
            msg.includes('fetch failed')
          alog('register → first error', { status, msg, maybeTimeout })

          if (maybeTimeout) {
            const check = await trySignInCheck(email, password)
            if (check.created === true) {
              if (check.pendingEmailConfirm) {
                alog('register → account created, pending email confirmation')
                throw Object.assign(new Error('Votre compte a été créé, mais vous devez confirmer votre adresse e‑mail. Vérifiez votre boîte de réception.'), { code: 'SIGNUP_CREATED_NEEDS_CONFIRM' })
              }
              alog('register → account created & session active')
              return
            }

            await sleep(1500)
            const { error: again } = await signUpOnce()
            if (!again) { alog('register → success (second attempt)'); return }

            const recheck = await trySignInCheck(email, password)
            if (recheck.created === true) {
              if (recheck.pendingEmailConfirm) {
                alog('register → created on retry, pending email confirmation')
                throw Object.assign(new Error('Votre compte a été créé, mais vous devez confirmer votre adresse e‑mail. Vérifiez votre boîte de réception.'), { code: 'SIGNUP_CREATED_NEEDS_CONFIRM' })
              }
              alog('register → created on retry, session active')
              return
            }

            alog('register → temporary down (504) after retry')
            throw Object.assign(new Error('Le service d’inscription est temporairement indisponible (504). Réessayez plus tard.'), { code: 'SIGNUP_TEMPORARY_DOWN' })
          }

          // Erreur fonctionnelle (e‑mail déjà utilisé, mot de passe invalide, …)
          throw new Error(error?.message || 'Erreur lors de la création du compte')
        } catch (e: any) {
          get().handleAuthError(e, 'register')
          alog('register → error', e?.message)
          toast.error(e?.message || 'Erreur lors de la création du compte', { icon: '⚠️' })
          throw e
        } finally {
          set({ isLoading: false })
        }
      },

      logout: async () => {
        set({ isLoading: true })
        alog('logout()')
        try {
          const { error } = await supabase.auth.signOut()
          if (error) throw error
          set({ user: null, isAuthenticated: false })
          try { localStorage.removeItem('intelia-chat-storage') } catch {}
          alog('logout → success')
        } catch (e: any) {
          get().handleAuthError(e, 'logout')
          alog('logout → error', e?.message)
          throw new Error(e?.message || 'Erreur lors de la déconnexion')
        } finally {
          set({ isLoading: false })
        }
      },

      updateProfile: async (data: Partial<AppUser>) => {
        set({ isLoading: true })
        alog('updateProfile()', Object.keys(data || {}))
        try {
          const { data: upd, error } = await supabase.auth.updateUser({ data })
          if (error) throw error
          const appUser = mapSessionToAppUser({ user: upd?.user })
          set({ user: appUser || get().user })
          alog('updateProfile → success')
        } catch (e: any) {
          get().handleAuthError(e, 'updateProfile')
          alog('updateProfile → error', e?.message)
          throw new Error(e?.message || 'Erreur de mise à jour du profil')
        } finally {
          set({ isLoading: false })
        }
      },

      updateConsent: async (consent: RGPDConsent) => {
        alog('updateConsent()', consent)
        await get().updateProfile({ rgpd_consent: consent } as any)
      },

      deleteUserData: async () => {
        console.warn('deleteUserData: non implémenté côté client')
      },

      exportUserData: async () => {
        console.warn('exportUserData: non implémenté côté client')
        return null
      },
    }),
    {
      name: 'auth-store',
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
        if (error) console.error('❌ Persist rehydrate error', error)
        state?.setHasHydrated(true)
        alog('rehydrated')
      },
    }
  )
)

// ---- Abonnement aux changements d’auth ----
let authListenerAttached = false
export function attachAuthStateChangeListener() {
  if (authListenerAttached) return
  authListenerAttached = true

  alog('attachAuthStateChangeListener()')
  supabase.auth.onAuthStateChange(async (event, session) => {
    alog('onAuthStateChange →', event)
    if (event === 'SIGNED_IN' && session) {
      const appUser = mapSessionToAppUser(session)
      useAuthStore.setState({ user: appUser, isAuthenticated: true, isRecovering: false })
      alog('state: SIGNED_IN', appUser?.email && maskEmail(appUser.email))
    } else if (event === 'SIGNED_OUT') {
      useAuthStore.setState({ user: null, isAuthenticated: false })
      alog('state: SIGNED_OUT')
    } else if (event === 'TOKEN_REFRESHED') {
      alog('state: TOKEN_REFRESHED')
    } else if (event === 'INITIAL_SESSION') {
      alog('state: INITIAL_SESSION')
    }
  })
}

// Export par défaut (compat imports par défaut)
export default useAuthStore