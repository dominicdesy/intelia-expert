// lib/stores/auth.ts — extraits pertinents
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { User, RGPDConsent } from '@/types'
import { supabase, supabaseAuth, auth } from '@/lib/supabase/client' // ⬅️ ajoutez supabaseAuth ici
import toast from 'react-hot-toast'

// Helpers (à placer après les imports)
const sleep = (ms: number) => new Promise(res => setTimeout(res, ms))

async function trySignInCheck(email: string, password: string) {
  // Vérifie si le compte a quand même été créé (avec/sans confirmation)
  const { data, error } = await supabaseAuth.auth.signInWithPassword({ email, password })
  if (data?.session) {
    return { created: true as const, pendingEmailConfirm: false }
  }
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

// ... votre définition de state & store ici ...

// Dans votre create<AuthState>(), remplacez UNIQUEMENT la méthode register par ceci :
register: async (email: string, password: string, userData: Partial<User>) => {
  try {
    set({ isLoading: true, authErrors: [] })
    console.log('📝 Création compte pour:', email)

    const fullName = (userData?.name || '').trim()
    if (fullName.length < 2) {
      throw new Error('Le nom doit contenir au moins 2 caractères')
    }

    const signUpOnce = async () => {
      return await supabaseAuth.auth.signUp({
        email,
        password,
        options: {
          data: {
            name: fullName,
            user_type: userData.user_type || 'producer',
            language: userData.language || 'fr'
          },
          emailRedirectTo: typeof window !== 'undefined'
            ? `${window.location.origin}/auth/callback`
            : undefined
        }
      })
    }

    // 1) Essai #1
    const { data, error } = await signUpOnce()
    if (!error) {
      // Succès direct (peut nécessiter confirmation)
      toast.success('Compte créé. Vérifiez vos e-mails si une confirmation est requise.', { icon: '📧' })
      return
    }

    // 2) Timeout/504/réseau ? Vérifier si le compte existe
    const status: any = (error as any)?.status || 0
    const msg = (error?.message || '').toLowerCase()
    const maybeTimeout = status === 504 ||
      msg.includes('timeout') || msg.includes('gateway') ||
      msg.includes('network') || msg.includes('fetch failed')

    if (maybeTimeout) {
      const check = await trySignInCheck(email, password)
      if (check.created === true) {
        if (check.pendingEmailConfirm) {
          throw Object.assign(new Error(
            'Votre compte a été créé, mais vous devez confirmer votre adresse e-mail. Vérifiez votre boîte de réception.'
          ), { code: 'SIGNUP_CREATED_NEEDS_CONFIRM' })
        }
        // Session active
        return
      }

      // 3) Toujours pas créé ? Dernier essai après une courte pause
      await sleep(1500)
      const { error: again } = await signUpOnce()
      if (!again) return

      // Re-check par sécurité
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

    // 4) Erreur fonctionnelle
    get().handleAuthError(error)
    const errorMessages: Record<string, string> = {
      'Email rate limit exceeded': 'Trop de tentatives. Réessayez plus tard.',
      'User already registered': 'Un compte existe déjà avec cet e‑mail.',
      'Password should be at least': 'Mot de passe trop court.'
    }
    const known = Object.entries(errorMessages).find(([k]) => (error?.message || '').includes(k))
    throw new Error(known ? known[1] : (error?.message || 'Erreur lors de la création du compte'))
  } catch (error: any) {
    set({ isLoading: false })
    toast.error(error.message || 'Erreur lors de la création du compte', { icon: '⚠️', duration: 4000 })
    throw error
  } finally {
    set({ isLoading: false })
  }
}