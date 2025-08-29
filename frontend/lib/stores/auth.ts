// lib/stores/auth.ts — Store d'auth SUPABASE NATIF (VERSION FINALE CORRIGÉE + SINGLETON + API EXPERT + REMEMBER ME + REACT #300 FIX)
'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import toast from 'react-hot-toast'
import type { User as AppUser, RGPDConsent } from '@/types'
import { getSupabaseClient } from '@/lib/supabase/singleton'

// ---- DEBUG ----
const AUTH_DEBUG = true
const alog = (...args: any[]) => {
  if (AUTH_DEBUG) {
    console.debug('[SupabaseAuthStore/Singleton]', ...args)
  }
}

alog('Store Auth Supabase NATIF chargé (singleton + React #300 fix)')

// CORRECTION CRITIQUE: Variable globale pour gérer l'état de montage avec logs debug
let isStoreActive = true

// CORRECTION: Fonctions pour contrôler l'état du store avec logs debug
export const markStoreUnmounted = () => {
  console.log('🕒 [DEBUG-TIMEOUT-STORE] Execution markStoreUnmounted - isStoreActive:', isStoreActive)
  isStoreActive = false
  console.log('⚠️ [DEBUG-TIMEOUT-STORE] Store marqué comme démonté')
}

export const markStoreMounted = () => {
  console.log('🕒 [DEBUG-TIMEOUT-STORE] Execution markStoreMounted - isStoreActive:', isStoreActive)
  isStoreActive = true
  console.log('✅ [DEBUG-TIMEOUT-STORE] Store marqué comme monté')
}

// ============================================================================
// SOLUTION REACT #300: setState NON-BLOQUANTS avec microtâches
// ============================================================================

// Utilitaire de planification non-bloquante (microtâche)
const schedule = 
  typeof queueMicrotask === 'function'
    ? queueMicrotask
    : (fn: () => void) => Promise.resolve().then(fn)

// Wrapper pour set() de Zustand afin de décaler l'écriture d'un microtick
// Cela évite les collisions avec le cycle de démontage React
let zustandSetFn: any = null // Sera initialisé dans le store

const safeSet = <T extends Partial<AuthState>>(
  partial: T | ((s: AuthState) => T),
  replace = false,
  debugLabel = 'unknown'
) => {
  if (!isStoreActive) {
    console.log('⚠️ [DEBUG-MICROTASK] safeSet ignoré - store démonté:', debugLabel)
    return
  }
  
  schedule(() => {
    try {
      if (isStoreActive && zustandSetFn) {
        zustandSetFn(partial as any, replace)
        console.log('✅ [DEBUG-MICROTASK] setState appliqué en microtâche:', debugLabel)
      } else {
        console.log('⚠️ [DEBUG-MICROTASK] setState ignoré - store inactif/non-initialisé:', debugLabel)
      }
    } catch (error) {
      console.error('❌ [DEBUG-MICROTASK] Erreur setState microtâche:', debugLabel, error)
    }
  })
}

// ANCIEN WRAPPER conservé pour compatibilité (utilise maintenant safeSet)
const safeSetState = (setFn: any, stateName: string) => {
  console.log('🕒 [DEBUG-TIMEOUT-STORE-SET] Redirection vers safeSet:', stateName)
  safeSet(() => setFn(), false, stateName)
}

// NOUVEAU: Import des utilitaires RememberMe
let rememberMeUtils: any = null

// Lazy loading des utilitaires RememberMe pour éviter les imports circulaires
const getRememberMeUtils = async () => {
  if (!rememberMeUtils) {
    try {
      const { rememberMeUtils: rmUtils } = await import('@/app/page_hooks')
      rememberMeUtils = rmUtils
      console.log('✅ [RememberMe] Utilitaires chargés dans auth store')
    } catch (error) {
      console.warn('⚠️ [RememberMe] Impossible de charger les utilitaires:', error)
      // Fallback simple si les utilitaires ne sont pas disponibles
      rememberMeUtils = {
        preserveOnLogout: () => null,
        restoreAfterLogout: () => {},
        clear: () => {}
      }
    }
  }
  return rememberMeUtils
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
  // Construire le nom complet de manière sécurisée
  const rawFullName = additionalData?.full_name || 
                      supabaseUser.user_metadata?.full_name || 
                      supabaseUser.email?.split('@')[0] || 
                      'Utilisateur'
  
  const fullName = String(rawFullName).trim() || 'Utilisateur'
  
  // Séparer firstName et lastName
  const nameParts = fullName.trim().split(' ')
  const firstName = nameParts[0] || ''
  const lastName = nameParts.slice(1).join(' ') || ''

  return {
    // Champs obligatoires de l'interface User
    id: supabaseUser.id,
    email: supabaseUser.email || '',
    name: fullName,
    firstName: firstName,
    lastName: lastName,
    phone: additionalData?.phone || '',
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
    user_id: supabaseUser.id,
    profile_id: additionalData?.profile_id,
    preferences: additionalData?.preferences,
    is_admin: additionalData?.is_admin || false
  }
}

// Store Supabase NATIF (avec singleton et protection démontage RENFORCÉE + REMEMBER ME + REACT #300 FIX)
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => {
      // Initialiser la référence pour safeSet
      zustandSetFn = set
      
      return {
        user: null,
        isLoading: false,
        isAuthenticated: false,
        hasHydrated: false,
        lastAuthCheck: 0,
        authErrors: [],

        setHasHydrated: (v: boolean) => {
          safeSet({ hasHydrated: v }, false, 'setHasHydrated')
        },

        handleAuthError: (error: any, ctx?: string) => {
          const msg = (error?.message || 'Authentication error').toString()
          console.error('[SupabaseAuth/Singleton]', ctx || '', error)
          safeSet((s) => ({ authErrors: [...s.authErrors, msg] }), false, 'handleAuthError')
        },

        clearAuthErrors: () => {
          safeSet({ authErrors: [] }, false, 'clearAuthErrors')
        },

        initializeSession: async () => {
          if (!isStoreActive) {
            console.log('⚠️ [DEBUG-TIMEOUT-STORE] initializeSession ignoré - store démonté')
            return false
          }
          
          try {
            alog('initializeSession via Supabase natif (singleton)')
            
            const supabase = getSupabaseClient()
            const { data: { session }, error } = await supabase.auth.getSession()
            
            if (error) {
              alog('Erreur session Supabase (singleton):', error)
              safeSet({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() }, false, 'initializeSession-error')
              return false
            }

            if (!session || !session.user) {
              alog('Pas de session Supabase (singleton)')
              safeSet({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() }, false, 'initializeSession-no-session')
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

            if (!isStoreActive) {
              console.log('⚠️ [DEBUG-TIMEOUT-STORE] initializeSession interrompu - store démonté')
              return false
            }

            const appUser = adaptSupabaseUser(session.user, profileData)

            safeSet({ 
              user: appUser, 
              isAuthenticated: true, 
              lastAuthCheck: Date.now()
            }, false, 'initializeSession-success')
            
            alog('initializeSession réussi (singleton):', appUser.email)
            return true
            
          } catch (e) {
            if (isStoreActive) {
              get().handleAuthError(e, 'initializeSession')
              safeSet({ isAuthenticated: false, user: null }, false, 'initializeSession-catch')
            }
            return false
          }
        },

        checkAuth: async () => {
          if (!isStoreActive) {
            console.log('⚠️ [DEBUG-TIMEOUT-STORE] checkAuth ignoré - store démonté')
            return
          }
          
          try {
            const supabase = getSupabaseClient()
            const { data: { session } } = await supabase.auth.getSession()
            
            if (!session || !session.user) {
              safeSet({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() }, false, 'checkAuth-no-session')
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

            if (!isStoreActive) {
              console.log('⚠️ [DEBUG-TIMEOUT-STORE] checkAuth interrompu - store démonté')
              return
            }

            const appUser = adaptSupabaseUser(session.user, profileData)

            safeSet({
              user: appUser,
              isAuthenticated: true,
              lastAuthCheck: Date.now()
            }, false, 'checkAuth-success')
            
            alog('checkAuth réussi (singleton)')
            
          } catch (e) {
            if (isStoreActive) {
              get().handleAuthError(e, 'checkAuth')
              safeSet({ isAuthenticated: false, user: null }, false, 'checkAuth-error')
            }
          }
        },

        login: async (email: string, password: string) => {
          if (!isStoreActive) {
            console.log('⚠️ [DEBUG-TIMEOUT-STORE] login ignoré - store démonté')
            return
          }
          
          safeSet({ isLoading: true, authErrors: [] }, false, 'login-start')
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

            safeSet({ isLoading: false }, false, 'login-success')
            
          } catch (e: any) {
            if (isStoreActive) {
              get().handleAuthError(e, 'login')
              alog('Erreur login (singleton):', e?.message)
              
              let userMessage = e?.message || 'Erreur de connexion'
              if (userMessage.includes('Invalid login credentials')) {
                userMessage = 'Email ou mot de passe incorrect'
              } else if (userMessage.includes('Email not confirmed')) {
                userMessage = 'Veuillez confirmer votre email avant de vous connecter'
              }
              
              throw new Error(userMessage)
            }
          } finally {
            safeSet({ isLoading: false }, false, 'login-finally')
          }
        },

        register: async (email: string, password: string, userData: Partial<AppUser>) => {
          if (!isStoreActive) {
            console.log('⚠️ [DEBUG-TIMEOUT-STORE] register ignoré - store démonté')
            return
          }
          
          safeSet({ isLoading: true, authErrors: [] }, false, 'register-start')
          alog('register via Supabase natif (singleton):', email)
          
          try {
            const fullName = String(userData?.name || '').trim()
            if (!fullName || fullName.length < 2) {
              throw new Error('Le nom doit contenir au moins 2 caractères')
            }

            const supabase = getSupabaseClient()
            
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

            safeSet({ isLoading: false }, false, 'register-profile-done')
            
            if (!data.session) {
              toast.success('Compte créé ! Vérifiez votre email pour confirmer votre inscription.')
            } else {
              if (isStoreActive) {
                await get().initializeSession()
              }
            }
            
          } catch (e: any) {
            if (isStoreActive) {
              get().handleAuthError(e, 'register')
              alog('Erreur register (singleton):', e?.message)
              
              let userMessage = e?.message || 'Erreur lors de la création du compte'
              
              if (userMessage.includes('already registered')) {
                userMessage = 'Cette adresse email est déjà utilisée'
              } else if (userMessage.includes('Password should be at least')) {
                userMessage = 'Le mot de passe doit contenir au moins 6 caractères'
              }
              
              throw new Error(userMessage)
            }
          } finally {
            safeSet({ isLoading: false }, false, 'register-finally')
          }
        },

        // FONCTION LOGOUT MODIFIÉE AVEC PRÉSERVATION REMEMBER ME + REACT #300 FIX
        logout: async () => {
          if (!isStoreActive) {
            console.log('⚠️ [DEBUG-TIMEOUT-STORE] logout ignoré - store démonté')
            return
          }
          
          safeSet({ isLoading: true }, false, 'logout-start')
          console.log('[DEBUG-LOGOUT] Début déconnexion coordonnée avec préservation RememberMe')
          
          try {
            // ÉTAPE 1 : Préserver les données RememberMe AVANT le nettoyage
            const rmUtils = await getRememberMeUtils()
            const preservedRememberMe = rmUtils.preserveOnLogout()
            console.log('[DEBUG-LOGOUT] Données RememberMe préservées:', preservedRememberMe)

            // ÉTAPE 2 : Déconnexion Supabase
            const supabase = getSupabaseClient()
            const { error } = await supabase.auth.signOut()
            
            if (error) {
              throw new Error(error.message)
            }

            // ÉTAPE 3 : Nettoyage localStorage SÉLECTIF (exclure RememberMe)
            console.log('[DEBUG-LOGOUT] Nettoyage localStorage sélectif')
            
            try {
              const keysToRemove = []
              
              // Parcourir toutes les clés localStorage
              for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i)
                if (key && key !== 'intelia-remember-me-persist') {
                  // Supprimer les clés auth/session mais GARDER RememberMe
                  if (key.startsWith('supabase-') || 
                      key.startsWith('intelia-') && key !== 'intelia-remember-me-persist' ||
                      key.includes('auth') || 
                      key.includes('session') ||
                      key === 'intelia-expert-auth' ||
                      key === 'intelia-chat-storage') {
                    keysToRemove.push(key)
                  }
                }
              }
              
              // Supprimer les clés identifiées
              keysToRemove.forEach(key => {
                try {
                  localStorage.removeItem(key)
                  console.log(`[DEBUG-LOGOUT] Supprimé: ${key}`)
                } catch (e) {
                  console.warn(`[DEBUG-LOGOUT] Impossible de supprimer ${key}:`, e)
                }
              })
              
              console.log(`[DEBUG-LOGOUT] ${keysToRemove.length} clés supprimées, RememberMe préservé`)
              
            } catch (storageError) {
              console.warn('[DEBUG-LOGOUT] Erreur nettoyage localStorage:', storageError)
            }

            // ÉTAPE 4 : Nettoyer l'état du store APRÈS le nettoyage storage (avec microtâche)
            safeSet({ 
              user: null, 
              isAuthenticated: false,
              lastAuthCheck: Date.now()
            }, false, 'logout-clear-state')

            // ÉTAPE 5 : Restaurer RememberMe APRÈS le nettoyage (avec délai pour éviter conflit)
            if (preservedRememberMe) {
              schedule(() => {
                try {
                  rmUtils.restoreAfterLogout(preservedRememberMe)
                  console.log('[DEBUG-LOGOUT] RememberMe restauré après nettoyage')
                } catch (error) {
                  console.warn('[DEBUG-LOGOUT] Erreur restauration RememberMe:', error)
                }
              })
            }
            
            alog('Logout réussi avec préservation RememberMe (singleton)')
            
          } catch (e: any) {
            if (isStoreActive) {
              get().handleAuthError(e, 'logout')
              alog('Erreur logout (singleton):', e?.message)
              
              // Même en cas d'erreur, nettoyer l'état local avec protection
              safeSet({ 
                user: null, 
                isAuthenticated: false,
                lastAuthCheck: Date.now()
              }, false, 'logout-error-clear-state')
              
              throw new Error(e?.message || 'Erreur lors de la déconnexion')
            }
          } finally {
            safeSet({ isLoading: false }, false, 'logout-finally')
          }
        },

        // FONCTION UPDATEPROFILE CORRIGÉE POUR ÉVITER REACT #300 avec microtâches
        updateProfile: async (data: Partial<AppUser>) => {
          if (!isStoreActive) {
            console.log('⚠️ [DEBUG-TIMEOUT-STORE] updateProfile ignoré - store démonté')
            return
          }
          
          safeSet({ isLoading: true }, false, 'updateProfile-start')
          alog('updateProfile via Supabase (singleton)')
          
          try {
            const currentUser = get().user
            if (!currentUser) {
              throw new Error('Utilisateur non connecté')
            }

            // Validation des données avant envoi
            const validatedData: any = {}
            
            if (data.firstName !== undefined) {
              validatedData.first_name = String(data.firstName).trim()
            }
            
            if (data.lastName !== undefined) {
              validatedData.last_name = String(data.lastName).trim()
            }
            
            if (data.firstName !== undefined || data.lastName !== undefined) {
              const fullName = `${data.firstName || currentUser.firstName || ''} ${data.lastName || currentUser.lastName || ''}`.trim()
              if (fullName.length < 2) {
                throw new Error('Le nom doit contenir au moins 2 caractères')
              }
              validatedData.full_name = fullName
            }
            
            if (data.user_type !== undefined) {
              const userType = String(data.user_type)
              if (!['producer', 'professional', 'super_admin'].includes(userType)) {
                throw new Error('Type d\'utilisateur invalide')
              }
              validatedData.user_type = userType
            }
            
            if (data.language !== undefined) {
              const language = String(data.language)
              if (!['fr', 'en', 'es'].includes(language)) {
                throw new Error('Langue non supportée')
              }
              validatedData.language = language
            }

            // Ajouter tous les autres champs
            if (data.country_code !== undefined) validatedData.country_code = data.country_code
            if (data.area_code !== undefined) validatedData.area_code = data.area_code
            if (data.phone_number !== undefined) validatedData.phone_number = data.phone_number
            if (data.country !== undefined) validatedData.country = data.country
            if (data.linkedinProfile !== undefined) validatedData.linkedin_profile = data.linkedinProfile
            if (data.companyName !== undefined) validatedData.company_name = data.companyName
            if (data.companyWebsite !== undefined) validatedData.company_website = data.companyWebsite
            if (data.linkedinCorporate !== undefined) validatedData.linkedin_corporate = data.linkedinCorporate

            const supabase = getSupabaseClient()
            const { error } = await supabase
              .from('users')
              .update(validatedData)
              .eq('auth_user_id', currentUser.id)

            if (error) {
              throw new Error(error.message)
            }

            if (isStoreActive) {
              // CORRECTION CRITIQUE: Vérifier si les données ont vraiment changé
              const currentState = get()
              const hasChanges = Object.keys(data).some(key => {
                const currentValue = currentState.user?.[key as keyof AppUser]
                const newValue = data[key as keyof Partial<AppUser>]
                return currentValue !== newValue
              })
              
              if (hasChanges) {
                console.log('[updateProfile] Changements détectés - mise à jour du store (microtâche)')
                // Mise à jour locale avec validation - AVEC microtâche pour éviter React #300
                const updatedUser = { 
                  ...currentUser,
                  ...data,
                  // S'assurer que les champs requis restent définis
                  email: currentUser.email, // L'email ne change jamais
                }
                safeSet({ user: updatedUser }, false, 'updateProfile-success')
              } else {
                console.log('[updateProfile] Pas de changements détectés - setState léger')
                // Marquer quand même comme traité en microtâche
                safeSet({}, false, 'updateProfile-no-changes')
              }
            }
            
            alog('updateProfile réussi (singleton)')
            
          } catch (e: any) {
            if (isStoreActive) {
              get().handleAuthError(e, 'updateProfile')
              throw new Error(e?.message || 'Erreur de mise à jour du profil')
            }
          } finally {
            safeSet({ isLoading: false }, false, 'updateProfile-finally')
          }
        },

        updateConsent: async (consent: RGPDConsent) => {
          if (!isStoreActive) {
            console.log('⚠️ [DEBUG-TIMEOUT-STORE] updateConsent ignoré - store démonté')
            return
          }
          
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
          if (!isStoreActive) {
            console.log('⚠️ [DEBUG-TIMEOUT-STORE] deleteUserData ignoré - store démonté')
            return
          }
          
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

            // Nettoyer aussi les données RememberMe lors de la suppression du compte
            try {
              const rmUtils = await getRememberMeUtils()
              rmUtils.clear()
              console.log('[DEBUG-LOGOUT] RememberMe nettoyé lors de la suppression du compte')
            } catch (error) {
              console.warn('[DEBUG-LOGOUT] Erreur nettoyage RememberMe:', error)
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
          if (!isStoreActive) {
            console.log('⚠️ [DEBUG-TIMEOUT-STORE] getAuthToken ignoré - store démonté')
            return null
          }
          
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
      }
    },
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
  if (!isStoreActive) {
    console.log('⚠️ [DEBUG-TIMEOUT-STORE] getAuthToken utilitaire ignoré - store démonté')
    return null
  }
  
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