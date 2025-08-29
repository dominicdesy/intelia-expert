// lib/stores/auth.ts

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

alog('Store Auth Supabase NATIF chargÃ© (singleton + React #300 fix)')

// ============================================================================
// SOLUTION REACT #300: ContrÃ´le du cycle de vie et Ã©tats de logout
// ============================================================================

// Variables de contrÃ´le du cycle de vie
let isStoreActive = true
let logoutInProgress = false

// CORRECTION: Ne pas marquer le store comme dÃ©montÃ© sauf pendant logout rÃ©el
export const markStoreUnmounted = () => {
  console.log('[DEBUG-LOGOUT] markStoreUnmounted appelÃ© - SEULEMENT pendant logout')
  isStoreActive = false
  logoutInProgress = true
}

export const markStoreMounted = () => {
  console.log('[DEBUG-TIMEOUT-STORE] Store rÃ©activÃ©')
  isStoreActive = true
  logoutInProgress = false
}

// NOUVEAU: Fonction sÃ©parÃ©e pour logout seulement
export const markLogoutStart = () => {
  console.log('[DEBUG-LOGOUT] DÃ©but logout - blocage setState prÃ©ventif')
  logoutInProgress = true
  // NE PAS marquer isStoreActive = false ici !
}

export const markLogoutEnd = () => {
  console.log('[DEBUG-LOGOUT] Fin logout - rÃ©activation setState')
  logoutInProgress = false
  // Laisser isStoreActive tel quel
}

let zustandSetFn: any = null // Sera initialisÃ© dans le store

// CORRECTION CRITIQUE: safeSet simplifiÃ© - exÃ©cution IMMÃ‰DIATE, plus de microtÃ¢ches
const safeSet = <T extends Partial<AuthState>>(
  partial: T | ((s: AuthState) => T),
  replace = false,
  debugLabel = 'unknown'
) => {
  // VÃ©rifications prÃ©alables simplifiÃ©es
  if (!isStoreActive) {
    console.log('[DEBUG-IMMEDIATE] safeSet bloquÃ© - store inactif:', debugLabel)
    return
  }

  // Bloquer seulement pendant logout ET si ce n'est pas une opÃ©ration de logout
  if (logoutInProgress && !debugLabel.includes('logout')) {
    console.log('[DEBUG-IMMEDIATE] safeSet bloquÃ© - logout en cours:', debugLabel)
    return
  }
  
  // CORRECTION FINALE: ExÃ©cution IMMÃ‰DIATE pour TOUTES les opÃ©rations - plus de microtÃ¢ches
  try {
    if (zustandSetFn) {
      zustandSetFn(partial as any, replace)
      console.log('[DEBUG-IMMEDIATE] setState appliquÃ© immÃ©diatement:', debugLabel)
    }
  } catch (error) {
    console.error('[DEBUG-IMMEDIATE] Erreur setState immÃ©diat:', debugLabel, error)
  }
}

// ANCIEN WRAPPER conservÃ© pour compatibilitÃ© (utilise maintenant safeSet)
const safeSetState = (setFn: any, stateName: string) => {
  console.log('[DEBUG-TIMEOUT-STORE-SET] Redirection vers safeSet:', stateName)
  safeSet(() => setFn(), false, stateName)
}

// NOUVEAU: Import des utilitaires RememberMe
let rememberMeUtils: any = null

// Lazy loading des utilitaires RememberMe pour Ã©viter les imports circulaires
const getRememberMeUtils = async () => {
  if (!rememberMeUtils) {
    try {
      const { rememberMeUtils: rmUtils } = await import('@/app/page_hooks')
      rememberMeUtils = rmUtils
      console.log('[RememberMe] Utilitaires chargÃ©s dans auth store')
    } catch (error) {
      console.warn('[RememberMe] Impossible de charger les utilitaires:', error)
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

// Types d'Ã©tat du store
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
  // Construire le nom complet de maniÃ¨re sÃ©curisÃ©e
  const rawFullName = additionalData?.full_name || 
                      supabaseUser.user_metadata?.full_name || 
                      supabaseUser.email?.split('@')[0] || 
                      'Utilisateur'
  
  const fullName = String(rawFullName).trim() || 'Utilisateur'
  
  // SÃ©parer firstName et lastName
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

// Store Supabase NATIF (avec singleton et protection dÃ©montage RENFORCÃ‰E + REMEMBER ME + REACT #300 FIX)
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => {
      // Initialiser la rÃ©fÃ©rence pour safeSet
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
          // CORRECTION: VÃ©rifier seulement logoutInProgress, pas isStoreActive
          if (logoutInProgress) {
            console.log('[DEBUG-LOGOUT] initializeSession ignorÃ© - logout en cours')
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

            alog('Session Supabase trouvÃ©e (singleton):', session.user.email)

            // RÃ©cupÃ©rer le profil utilisateur depuis Supabase
            let profileData = {}
            try {
              const { data: profile } = await supabase
                .from('users')
                .select('*')
                .eq('auth_user_id', session.user.id)
                .single()
              
              if (profile) {
                profileData = profile
                alog('Profil utilisateur trouvÃ© (singleton):', profile.user_type)
              } else {
                alog('Pas de profil utilisateur, crÃ©ation automatique (singleton)...')
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
                  alog('Profil crÃ©Ã© automatiquement (singleton)')
                }
              }
            } catch (profileError) {
              alog('Erreur profil, utilisation valeurs par dÃ©faut (singleton):', profileError)
              profileData = { user_type: 'producer', language: 'fr' }
            }

            // CORRECTION: VÃ©rifier seulement logoutInProgress avant setState final
            if (logoutInProgress) {
              console.log('[DEBUG-LOGOUT] initializeSession interrompu - logout en cours')
              return false
            }

            const appUser = adaptSupabaseUser(session.user, profileData)

            safeSet({ 
              user: appUser, 
              isAuthenticated: true, 
              lastAuthCheck: Date.now()
            }, false, 'initializeSession-success')
            
            alog('initializeSession rÃ©ussi (singleton):', appUser.email)
            return true
            
          } catch (e) {
            // CORRECTION: Pas de vÃ©rification isStoreActive ici non plus
            if (!logoutInProgress) {
              get().handleAuthError(e, 'initializeSession')
              safeSet({ isAuthenticated: false, user: null }, false, 'initializeSession-catch')
            }
            return false
          }
        },

        checkAuth: async () => {
          if (!isStoreActive) {
            console.log('[DEBUG-TIMEOUT-STORE] checkAuth ignorÃ© - store dÃ©montÃ©')
            return
          }
          
          try {
            const supabase = getSupabaseClient()
            const { data: { session } } = await supabase.auth.getSession()
            
            if (!session || !session.user) {
              safeSet({ user: null, isAuthenticated: false, lastAuthCheck: Date.now() }, false, 'checkAuth-no-session')
              return
            }

            // RÃ©cupÃ©rer le profil utilisateur mis Ã  jour
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
              alog('Erreur rÃ©cupÃ©ration profil lors du checkAuth (singleton)')
            }

            if (!isStoreActive) {
              console.log('[DEBUG-TIMEOUT-STORE] checkAuth interrompu - store dÃ©montÃ©')
              return
            }

            const appUser = adaptSupabaseUser(session.user, profileData)

            safeSet({
              user: appUser,
              isAuthenticated: true,
              lastAuthCheck: Date.now()
            }, false, 'checkAuth-success')
            
            alog('checkAuth rÃ©ussi (singleton)')
            
          } catch (e) {
            if (isStoreActive) {
              get().handleAuthError(e, 'checkAuth')
              safeSet({ isAuthenticated: false, user: null }, false, 'checkAuth-error')
            }
          }
        },

        login: async (email: string, password: string) => {
          if (!isStoreActive) {
            console.log('[DEBUG-TIMEOUT-STORE] login ignorÃ© - store dÃ©montÃ©')
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
              throw new Error('Aucun utilisateur retournÃ©')
            }

            alog('Login Supabase rÃ©ussi (singleton):', data.user.email)

            safeSet({ isLoading: false }, false, 'login-success')
            
            // Nettoyer le flag logout aprÃ¨s connexion rÃ©ussie
            sessionStorage.removeItem('recent-logout')
            console.log('[Login] Flag recent-logout nettoyÃ©')
            
            // DÃ©clencher la vÃ©rification auth pour redirection
            setTimeout(() => {
              console.log('[Login] DÃ©clenchement Ã©vÃ©nement auth-state-changed')
              window.dispatchEvent(new Event('auth-state-changed'))
            }, 100)
            
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
            console.log('[DEBUG-TIMEOUT-STORE] register ignorÃ© - store dÃ©montÃ©')
            return
          }
          
          safeSet({ isLoading: true, authErrors: [] }, false, 'register-start')
          alog('register via Supabase natif (singleton):', email)
          
          try {
            const fullName = String(userData?.name || '').trim()
            if (!fullName || fullName.length < 2) {
              throw new Error('Le nom doit contenir au moins 2 caractÃ¨res')
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
              throw new Error('Erreur lors de la crÃ©ation du compte')
            }

            alog('Inscription Supabase rÃ©ussie (singleton):', data.user.email)

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
                  alog('Erreur crÃ©ation profil (singleton):', profileError)
                } else {
                  alog('Profil utilisateur crÃ©Ã© (singleton)')
                }
              } catch (profileError) {
                alog('Erreur crÃ©ation profil (singleton):', profileError)
              }
            }

            safeSet({ isLoading: false }, false, 'register-profile-done')
            
            if (!data.session) {
              toast.success('Compte crÃ©Ã© ! VÃ©rifiez votre email pour confirmer votre inscription.')
            } else {
              if (isStoreActive) {
                await get().initializeSession()
              }
            }
            
          } catch (e: any) {
            if (isStoreActive) {
              get().handleAuthError(e, 'register')
              alog('Erreur register (singleton):', e?.message)
              
              let userMessage = e?.message || 'Erreur lors de la crÃ©ation du compte'
              
              if (userMessage.includes('already registered')) {
                userMessage = 'Cette adresse email est dÃ©jÃ  utilisÃ©e'
              } else if (userMessage.includes('Password should be at least')) {
                userMessage = 'Le mot de passe doit contenir au moins 6 caractÃ¨res'
              }
              
              throw new Error(userMessage)
            }
          } finally {
            safeSet({ isLoading: false }, false, 'register-finally')
          }
        },

        // CORRECTION CRITIQUE: Logout simplifiÃ© sans protections bloquantes
        logout: async () => {
          console.log('[DEBUG-LOGOUT] DÃ©but dÃ©connexion sans protections bloquantes')
          
          if (!isStoreActive) {
            console.log('[DEBUG-TIMEOUT-STORE] logout ignorÃ© - store dÃ©montÃ©')
            return
          }
          
          try {
            // Ã‰TAPE 1: PrÃ©server les donnÃ©es RememberMe AVANT le nettoyage
            const rmUtils = await getRememberMeUtils()
            const preservedRememberMe = rmUtils.preserveOnLogout()
            console.log('[DEBUG-LOGOUT] DonnÃ©es RememberMe prÃ©servÃ©es:', preservedRememberMe)

            // Ã‰TAPE 2: DÃ©connexion Supabase
            const supabase = getSupabaseClient()
            const { error } = await supabase.auth.signOut()
            
            if (error) {
              throw new Error(error.message)
            }

            // Ã‰TAPE 3: Nettoyage localStorage SÃ‰LECTIF (exclure RememberMe)
            console.log('[DEBUG-LOGOUT] Nettoyage localStorage sÃ©lectif')
            
            try {
              const keysToRemove = []
              
              // Parcourir toutes les clÃ©s localStorage
              for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i)
                if (key && key !== 'intelia-remember-me-persist') {
                  // Supprimer les clÃ©s auth/session mais GARDER RememberMe
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
              
              // Supprimer les clÃ©s identifiÃ©es
              keysToRemove.forEach(key => {
                try {
                  localStorage.removeItem(key)
                  console.log(`[DEBUG-LOGOUT] SupprimÃ©: ${key}`)
                } catch (e) {
                  console.warn(`[DEBUG-LOGOUT] Impossible de supprimer ${key}:`, e)
                }
              })
              
              console.log(`[DEBUG-LOGOUT] ${keysToRemove.length} clÃ©s supprimÃ©es, RememberMe prÃ©servÃ©`)
              
            } catch (storageError) {
              console.warn('[DEBUG-LOGOUT] Erreur nettoyage localStorage:', storageError)
            }

            // Ã‰TAPE 4: Nettoyage IMMÃ‰DIAT du store Zustand pour Ã©viter les boucles
            console.log('[DEBUG-LOGOUT] Nettoyage immÃ©diat du store pour Ã©viter les boucles')
            if (zustandSetFn) {
              zustandSetFn({
                user: null,
                isAuthenticated: false,
                isLoading: false,
                authErrors: [],
                lastAuthCheck: Date.now()
              }, false)
              console.log('[DEBUG-LOGOUT] Store Zustand nettoyÃ© immÃ©diatement')
            }

            // Ã‰TAPE 5: Marquer la session comme terminÃ©e
            sessionStorage.setItem('recent-logout', Date.now().toString())
            sessionStorage.removeItem('current-session')
            
            // Ã‰TAPE 6: RÃ©activer les setState APRÃˆS nettoyage
            markLogoutEnd()

            // Ã‰TAPE 5: Restaurer RememberMe APRÃˆS le nettoyage
            if (preservedRememberMe) {
              setTimeout(() => {  // Utiliser setTimeout au lieu de microtÃ¢che pour plus de sÃ©curitÃ©
                try {
                  rmUtils.restoreAfterLogout(preservedRememberMe)
                  console.log('[DEBUG-LOGOUT] RememberMe restaurÃ© aprÃ¨s nettoyage')
                } catch (error) {
                  console.warn('[DEBUG-LOGOUT] Erreur restauration RememberMe:', error)
                }
              }, 100)
            }
            
            alog('Logout rÃ©ussi avec prÃ©servation RememberMe (singleton)')
            
          } catch (e: any) {
            console.error('[DEBUG-LOGOUT] Erreur durant logout:', e)
            
            // En cas d'erreur, nettoyer quand mÃªme le store
            if (zustandSetFn) {
              zustandSetFn({
                user: null,
                isAuthenticated: false,
                isLoading: false,
                authErrors: [],
                lastAuthCheck: Date.now()
              }, false)
            }
            
            markLogoutEnd()
            throw new Error(e?.message || 'Erreur lors de la dÃ©connexion')
          }
        },

        // FONCTION UPDATEPROFILE CORRIGÃ‰E POUR Ã‰VITER REACT #300 avec microtÃ¢ches
        updateProfile: async (data: Partial<AppUser>) => {
          if (!isStoreActive) {
            console.log('[DEBUG-TIMEOUT-STORE] updateProfile ignorÃ© - store dÃ©montÃ©')
            return
          }
          
          safeSet({ isLoading: true }, false, 'updateProfile-start')
          alog('updateProfile via Supabase (singleton)')
          
          try {
            const currentUser = get().user
            if (!currentUser) {
              throw new Error('Utilisateur non connectÃ©')
            }

            // Validation des donnÃ©es avant envoi
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
                throw new Error('Le nom doit contenir au moins 2 caractÃ¨res')
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
                throw new Error('Langue non supportÃ©e')
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
              // CORRECTION CRITIQUE: VÃ©rifier si les donnÃ©es ont vraiment changÃ©
              const currentState = get()
              const hasChanges = Object.keys(data).some(key => {
                const currentValue = currentState.user?.[key as keyof AppUser]
                const newValue = data[key as keyof Partial<AppUser>]
                return currentValue !== newValue
              })
              
              if (hasChanges) {
                console.log('[updateProfile] Changements dÃ©tectÃ©s - mise Ã  jour du store')
                // Mise Ã  jour locale avec validation - EXÃ‰CUTION IMMÃ‰DIATE
                const updatedUser = { 
                  ...currentUser,
                  ...data,
                  // S'assurer que les champs requis restent dÃ©finis
                  email: currentUser.email, // L'email ne change jamais
                }
                safeSet({ user: updatedUser }, false, 'updateProfile-success')
              } else {
                console.log('[updateProfile] Pas de changements dÃ©tectÃ©s - setState lÃ©ger')
                safeSet({}, false, 'updateProfile-no-changes')
              }
            }
            
            alog('updateProfile rÃ©ussi (singleton)')
            
          } catch (e: any) {
            if (isStoreActive) {
              get().handleAuthError(e, 'updateProfile')
              throw new Error(e?.message || 'Erreur de mise Ã  jour du profil')
            }
          } finally {
            safeSet({ isLoading: false }, false, 'updateProfile-finally')
          }
        },

        updateConsent: async (consent: RGPDConsent) => {
          if (!isStoreActive) {
            console.log('[DEBUG-TIMEOUT-STORE] updateConsent ignorÃ© - store dÃ©montÃ©')
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
            throw new Error(e?.message || 'Erreur de mise Ã  jour du consentement')
          }
        },

        deleteUserData: async () => {
          if (!isStoreActive) {
            console.log('[DEBUG-TIMEOUT-STORE] deleteUserData ignorÃ© - store dÃ©montÃ©')
            return
          }
          
          const currentUser = get().user
          if (!currentUser) throw new Error('Non authentifiÃ©')

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

            // Nettoyer aussi les donnÃ©es RememberMe lors de la suppression du compte
            try {
              const rmUtils = await getRememberMeUtils()
              rmUtils.clear()
              console.log('[DEBUG-LOGOUT] RememberMe nettoyÃ© lors de la suppression du compte')
            } catch (error) {
              console.warn('[DEBUG-LOGOUT] Erreur nettoyage RememberMe:', error)
            }

            // DÃ©connecter
            if (isStoreActive) {
              await get().logout()
            }
            
          } catch (e: any) {
            throw new Error(e?.message || 'Erreur de suppression des donnÃ©es')
          }
        },

        exportUserData: async () => {
          const currentUser = get().user
          if (!currentUser) throw new Error('Non authentifiÃ©')

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
              message: 'DonnÃ©es utilisateur exportÃ©es'
            }
            
          } catch (e: any) {
            throw new Error(e?.message || 'Erreur d\'exportation des donnÃ©es')
          }
        },

        // Nouvelle mÃ©thode: RÃ©cupÃ©rer le token Supabase pour l'API Expert
        getAuthToken: async () => {
          if (!isStoreActive) {
            console.log('[DEBUG-TIMEOUT-STORE] getAuthToken ignorÃ© - store dÃ©montÃ©')
            return null
          }
          
          try {
            const supabase = getSupabaseClient()
            const { data: { session } } = await supabase.auth.getSession()
            
            if (session?.access_token) {
              alog('Token Supabase rÃ©cupÃ©rÃ© pour API Expert')
              return session.access_token
            }
            
            alog('Pas de token Supabase disponible')
            return null
          } catch (error) {
            alog('Erreur rÃ©cupÃ©ration token:', error)
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
        
        // Protection contre la rehydration pendant une dÃ©connexion rÃ©cente
        const recentLogout = sessionStorage.getItem('recent-logout')
        if (recentLogout) {
          const logoutTime = parseInt(recentLogout)
          if (Date.now() - logoutTime < 1000) {
            console.log('[AuthStore] Rehydration bloquÃ©e - dÃ©connexion rÃ©cente')
            if (state) {
              state.user = null
              state.isAuthenticated = false
            }
            return
          }
        }
        
        if (state && isStoreActive) {
          state.setHasHydrated(true)
          alog('Auth store rehydratÃ© (singleton)')
        }
      },
    }
  )
)

// Fonction utilitaire exportÃ©e: Pour utilisation dans d'autres fichiers
export const getAuthToken = async (): Promise<string | null> => {
  if (!isStoreActive) {
    console.log('[DEBUG-TIMEOUT-STORE] getAuthToken utilitaire ignorÃ© - store dÃ©montÃ©')
    return null
  }
  
  try {
    const supabase = getSupabaseClient()
    const { data: { session } } = await supabase.auth.getSession()
    
    if (session?.access_token) {
      alog('Token Supabase rÃ©cupÃ©rÃ© (fonction utilitaire)')
      return session.access_token
    }
    
    return null
  } catch (error) {
    alog('Erreur rÃ©cupÃ©ration token (fonction utilitaire):', error)
    return null
  }
}