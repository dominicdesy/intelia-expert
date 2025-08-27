// lib/stores/auth.ts — Store d'auth SUPABASE NATIF (VERSION FINALE CORRIGÉE + SINGLETON + API EXPERT)
'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import toast from 'react-hot-toast'
import type { User as AppUser, RGPDConsent } from '@/types'
import { getSupabaseClient } from '@/lib/supabase/singleton'

// ---- DEBUG ----
const AUTH_DEBUG = true // Activé pour debug
const alog = (...args: any[]) => {
  if (AUTH_DEBUG) {
    console.debug('[SupabaseAuthStore/Singleton]', ...args)
  }
}

alog('Store Auth Supabase NATIF chargé (singleton)')

// CORRECTION: Variable globale pour gérer l'état de montage
let isStoreActive = true

// CORRECTION: Fonctions pour contrôler l'état du store
export const markStoreUnmounted = () => {
  isStoreActive = false
  console.log('[AuthStore] Marqué comme démonté')
}

export const markStoreMounted = () => {
  isStoreActive = true
  console.log('[AuthStore] Marqué comme monté')
}

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
  initializeSession: () => Promise<boolean>
  checkAuth: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, userData: Partial<AppUser>) => Promise<void>
  logout: () => Promise<void>
  updateProfile: (data: Partial<AppUser>) => Promise<void>
  updateConsent: (consent: RGPDConsent) => Promise<void>
  deleteUserData: () => Promise<void>
  exportUserData: () => Promise<any>
  getAuthToken: () => Promise<string | null>
}

// Adapter utilisateur Supabase vers AppUser COMPLET
function adaptSupabaseUser(supabaseUser: any, additionalData?: any): AppUser {
  // Construire le nom complet
  const fullName = additionalData?.full_name || 
                   supabaseUser.user_metadata?.full_name || 
                   supabaseUser.email?.split('@')[0] || 
                   'Utilisateur'
  
  // Séparer firstName et lastName
  const nameParts = fullName.trim().split(' ')
  const firstName = nameParts[0] || ''
  const lastName = nameParts.slice(1).join(' ') || ''

  return {
    // Champs obligatoires de l'interface User
    id: supabaseUser.id,
    email: supabaseUser.email,
    name: fullName,
    firstName: firstName,
    lastName: lastName,
    phone: additionalData?.phone || '', // Champ obligatoire, défaut vide
    country: additionalData?.country || '',
    linkedinProfile: additionalData?.linkedinProfile || '',
    companyName: additionalData?.companyName || '',
    companyWebsite: additionalData?.companyWebsite || '',
    linkedinCorporate: additionalData?.linkedinCorporate || '',
    user_type: additionalData?.user_type || 'producer',
    language: additionalData?.language || 'fr',
    created_at: additionalData?.created_at || new Date().toISOString(),
    plan: additionalData?.plan || 'essential',

    // Champs optionnels
    country_code: additionalData?.country_code,
    area_code: additionalData?.area_code,
    phone_number: additionalData?.phone_number,
    full_name: fullName,
    avatar_url: additionalData?.avatar_url,
    consent_given: additionalData?.consent_given ?? true,
    consent_date: additionalData?.consent_date,
    updated_at: additionalData?.updated_at,
    user_id: supabaseUser.id, // Alias pour compatibilité
    profile_id: additionalData?.profile_id,
    preferences: additionalData?.preferences,
    is_admin: additionalData?.is_admin || false
  }
}

// Store Supabase NATIF (avec singleton et protection démontage)
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      hasHydrated: false,
      lastAuthCheck: 0,
      authErrors: [],

      // CORRECTION: Wrapper sécurisé pour setState
      safeSetState: (updates: Partial<AuthState>) => {
        if (!isStoreActive) {
          console.warn('[AuthStore] setState ignoré - store démonté')
          return
        }
        set(updates)
      },

      setHasHydrated: (v: boolean) => {
        if (!isStoreActive) return
        set({ hasHydrated: v })
      },

      handleAuthError: (error: any, ctx?: string) => {
        if (!isStoreActive) return
        
        const msg = (error?.message || 'Authentication error').toString()
        console.error('[SupabaseAuth/Singleton]', ctx || '', error)
        set((s) => ({ authErrors: [...s.authErrors, msg] }))
      },

      clearAuthErrors: () => {
        if (!isStoreActive) return
        set({ authErrors: [] })
      },

      initializeSession: async () => {
        if (!isStoreActive) return false
        
        try {
          alog('initializeSession via Supabase natif (singleton)')
          
          const supabase = getSupabaseClient()
          const { data: { session }, error } = await supabase.auth.getSession()
          
          if (error) {
            alog('Erreur session Supabase (singleton):', error)
            if (isStoreActive) {
              set({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() })
            }
            return false
          }

          if (!session || !session.user) {
            alog('Pas de session Supabase (singleton)')
            if (isStoreActive) {
              set({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() })
            }
            return false
          }

          alog('Session Supabase trouvée (singleton):', session.user.email)

          // Récupérer le profil utilisateur depuis Supabase
          let profileData = {}
          try {
            const { data: profile } = await supabase
              .from('users')
              .select('*')
              .eq('auth_user_id', session.user.id)
              .single()
            
            if (profile) {
              profileData = profile
              alog('Profil utilisateur trouvé (singleton):', profile.user_type)
            } else {
              alog('Pas de profil utilisateur, création automatique (singleton)...')
              // Créer un profil de base
              const { error: insertError } = await supabase
                .from('users')
                .insert({
                  auth_user_id: session.user.id,
                  email: session.user.email,
                  full_name: session.user.user_metadata?.full_name || session.user.email?.split('@')[0],
                  user_type: 'producer',
                  language: 'fr'
                })
              
              if (!insertError) {
                profileData = { user_type: 'producer', language: 'fr' }
                alog('Profil créé automatiquement (singleton)')
              }
            }
          } catch (profileError) {
            alog('Erreur profil, utilisation valeurs par défaut (singleton):', profileError)
            profileData = { user_type: 'producer', language: 'fr' }
          }

          if (!isStoreActive) return false

          const appUser = adaptSupabaseUser(session.user, profileData)

          set({ 
            user: appUser, 
            isAuthenticated: true, 
            lastAuthCheck: Date.now()
          })
          
          alog('initializeSession réussi (singleton):', appUser.email)
          return true
          
        } catch (e) {
          if (isStoreActive) {
            get().handleAuthError(e, 'initializeSession')
            set({ isAuthenticated: false, user: null })
          }
          return false
        }
      },

      checkAuth: async () => {
        if (!isStoreActive) return
        
        try {
          const supabase = getSupabaseClient()
          const { data: { session } } = await supabase.auth.getSession()
          
          if (!session || !session.user) {
            if (isStoreActive) {
              set({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() })
            }
            return
          }

          // Récupérer le profil utilisateur mis à jour
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
            alog('Erreur récupération profil lors du checkAuth (singleton)')
          }

          if (!isStoreActive) return

          const appUser = adaptSupabaseUser(session.user, profileData)

          set({
            user: appUser,
            isAuthenticated: true,
            lastAuthCheck: Date.now()
          })
          
          alog('checkAuth réussi (singleton)')
          
        } catch (e) {
          if (isStoreActive) {
            get().handleAuthError(e, 'checkAuth')
            set({ isAuthenticated: false, user: null })
          }
        }
      },

      login: async (email: string, password: string) => {
        if (!isStoreActive) return
        
        set({ isLoading: true, authErrors: [] })
        alog('login via Supabase natif (singleton):', email)
        
        try {
          const supabase = getSupabaseClient()
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

          alog('Login Supabase réussi (singleton):', data.user.email)

          if (isStoreActive) {
            set({ isLoading: false })
          }
          
        } catch (e: any) {
          if (isStoreActive) {
            get().handleAuthError(e, 'login')
            alog('Erreur login (singleton):', e?.message)
            
            // Messages d'erreur Supabase spécifiques
            let userMessage = e?.message || 'Erreur de connexion'
            if (userMessage.includes('Invalid login credentials')) {
              userMessage = 'Email ou mot de passe incorrect'
            } else if (userMessage.includes('Email not confirmed')) {
              userMessage = 'Veuillez confirmer votre email avant de vous connecter'
            }
            
            throw new Error(userMessage)
          }
        } finally {
          if (isStoreActive) {
            set({ isLoading: false })
          }
        }
      },

      register: async (email: string, password: string, userData: Partial<AppUser>) => {
        if (!isStoreActive) return
        
        set({ isLoading: true, authErrors: [] })
        alog('register via Supabase natif (singleton):', email)
        
        try {
          const fullName = (userData?.name || '').toString().trim()
          if (!fullName || fullName.length < 2) {
            throw new Error('Le nom doit contenir au moins 2 caractères')
          }

          const supabase = getSupabaseClient()
          
          // Inscription Supabase
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

          alog('Inscription Supabase réussie (singleton):', data.user.email)

          // Créer le profil utilisateur dans la table users
          if (data.user.id) {
            try {
              const { error: profileError } = await supabase
                .from('users')
                .insert({
                  auth_user_id: data.user.id,
                  email: email,
                  full_name: fullName,
                  user_type: userData.user_type || 'producer',
                  language: userData.language || 'fr'
                })

              if (profileError) {
                alog('Erreur création profil (singleton):', profileError)
              } else {
                alog('Profil utilisateur créé (singleton)')
              }
            } catch (profileError) {
              alog('Erreur création profil (singleton):', profileError)
            }
          }

          if (isStoreActive) {
            set({ isLoading: false })
          }
          
          if (!data.session) {
            toast.success('Compte créé ! Vérifiez votre email pour confirmer votre inscription.')
          } else {
            // L'utilisateur est directement connecté
            if (isStoreActive) {
              await get().initializeSession()
            }
          }
          
        } catch (e: any) {
          if (isStoreActive) {
            get().handleAuthError(e, 'register')
            alog('Erreur register (singleton):', e?.message)
            
            let userMessage = e?.message || 'Erreur lors de la création du compte'
            
            // Messages d'erreur spécifiques Supabase
            if (userMessage.includes('already registered')) {
              userMessage = 'Cette adresse email est déjà utilisée'
            } else if (userMessage.includes('Password should be at least')) {
              userMessage = 'Le mot de passe doit contenir au moins 6 caractères'
            }
            
            throw new Error(userMessage)
          }
        } finally {
          if (isStoreActive) {
            set({ isLoading: false })
          }
        }
      },

      logout: async () => {
        if (!isStoreActive) return
        
        set({ isLoading: true })
        alog('logout via Supabase natif (singleton)')
        
        try {
          const supabase = getSupabaseClient()
          const { error } = await supabase.auth.signOut()
          
          if (error) {
            throw new Error(error.message)
          }

          // Nettoyer le localStorage
          try {
            localStorage.removeItem('intelia-chat-storage')
          } catch {}

          if (isStoreActive) {
            set({ user: null, isAuthenticated: false })
          }
          alog('Logout réussi (singleton)')
          
        } catch (e: any) {
          if (isStoreActive) {
            get().handleAuthError(e, 'logout')
            alog('Erreur logout (singleton):', e?.message)
            throw new Error(e?.message || 'Erreur lors de la déconnexion')
          }
        } finally {
          if (isStoreActive) {
            set({ isLoading: false })
          }
        }
      },

      updateProfile: async (data: Partial<AppUser>) => {
        if (!isStoreActive) return
        
        set({ isLoading: true })
        alog('updateProfile via Supabase (singleton)')
        
        try {
          const currentUser = get().user
          if (!currentUser) {
            throw new Error('Utilisateur non connecté')
          }

          const supabase = getSupabaseClient()
          
          // Mettre à jour le profil dans Supabase
          const updateData: any = {}
          
          if (data.name !== undefined) updateData.full_name = data.name
          if (data.user_type !== undefined) updateData.user_type = data.user_type
          if (data.language !== undefined) updateData.language = data.language

          const { error } = await supabase
            .from('users')
            .update(updateData)
            .eq('auth_user_id', currentUser.id)

          if (error) {
            throw new Error(error.message)
          }

          if (isStoreActive) {
            // Mettre à jour localement
            const updatedUser = { ...currentUser, ...data }
            set({ user: updatedUser })
          }
          
          alog('updateProfile réussi (singleton)')
          
        } catch (e: any) {
          if (isStoreActive) {
            get().handleAuthError(e, 'updateProfile')
            throw new Error(e?.message || 'Erreur de mise à jour du profil')
          }
        } finally {
          if (isStoreActive) {
            set({ isLoading: false })
          }
        }
      },

      updateConsent: async (consent: RGPDConsent) => {
        if (!isStoreActive) return
        
        alog('updateConsent via Supabase (singleton)')
        
        try {
          const currentUser = get().user
          if (!currentUser) return

          const supabase = getSupabaseClient()
          const { error } = await supabase
            .from('users')
            .update({ rgpd_consent: consent })
            .eq('auth_user_id', currentUser.id)

          if (error) {
            throw new Error(error.message)
          }
        } catch (e: any) {
          alog('updateConsent error (singleton):', e?.message)
          throw new Error(e?.message || 'Erreur de mise à jour du consentement')
        }
      },

      deleteUserData: async () => {
        if (!isStoreActive) return
        
        const currentUser = get().user
        if (!currentUser) throw new Error('Non authentifié')

        try {
          const supabase = getSupabaseClient()
          
          // Supprimer le profil utilisateur
          const { error } = await supabase
            .from('users')
            .delete()
            .eq('auth_user_id', currentUser.id)

          if (error) {
            alog('Erreur suppression profil (singleton):', error)
          }

          // Déconnecter
          if (isStoreActive) {
            await get().logout()
          }
          
        } catch (e: any) {
          throw new Error(e?.message || 'Erreur de suppression des données')
        }
      },

      exportUserData: async () => {
        const currentUser = get().user
        if (!currentUser) throw new Error('Non authentifié')

        try {
          const supabase = getSupabaseClient()
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
          throw new Error(e?.message || 'Erreur d\'exportation des données')
        }
      },

      // Nouvelle méthode: Récupérer le token Supabase pour l'API Expert
      getAuthToken: async () => {
        if (!isStoreActive) return null
        
        try {
          const supabase = getSupabaseClient()
          const { data: { session } } = await supabase.auth.getSession()
          
          if (session?.access_token) {
            alog('Token Supabase récupéré pour API Expert')
            return session.access_token
          }
          
          alog('Pas de token Supabase disponible')
          return null
        } catch (error) {
          alog('Erreur récupération token:', error)
          return null
        }
      },
    }),
    {
      name: 'supabase-auth-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        lastAuthCheck: state.lastAuthCheck,
        hasHydrated: state.hasHydrated,
      }),
      onRehydrateStorage: () => (state, error) => {
        if (error) console.error('Erreur rehydrate auth store:', error)
        if (state && isStoreActive) {
          state.setHasHydrated(true)
          alog('Auth store rehydraté (singleton)')
        }
      },
    }
  )
)

// Fonction utilitaire exportée: Pour utilisation dans d'autres fichiers
export const getAuthToken = async (): Promise<string | null> => {
  if (!isStoreActive) return null
  
  try {
    const supabase = getSupabaseClient()
    const { data: { session } } = await supabase.auth.getSession()
    
    if (session?.access_token) {
      alog('Token Supabase récupéré (fonction utilitaire)')
      return session.access_token
    }
    
    return null
  } catch (error) {
    alog('Erreur récupération token (fonction utilitaire):', error)
    return null
  }
}