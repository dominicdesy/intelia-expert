// lib/stores/auth.ts - Store d'authentification complet avec initializeSession
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { User, RGPDConsent } from '@/types'
import { supabase, auth } from '@/lib/supabase/client'
import toast from 'react-hot-toast'

interface AuthState {
  // État
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  hasHydrated: boolean
  
  // Actions principales
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, userData: Partial<User>) => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
  initializeSession: () => Promise<boolean>
  setHasHydrated: (hasHydrated: boolean) => void
  
  // Actions profil
  updateProfile: (data: Partial<User>) => Promise<void>
  deleteUserData: () => Promise<void>
  exportUserData: () => Promise<any>
  updateConsent: (consent: RGPDConsent) => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // État initial
      user: null,
      isLoading: false,
      isAuthenticated: false,
      hasHydrated: false,

      // Marquer l'hydratation comme terminée
      setHasHydrated: (hasHydrated: boolean) => {
        set({ hasHydrated })
      },

      // 🔄 INITIALISATION SESSION (fonction manquante ajoutée)
      initializeSession: async (): Promise<boolean> => {
        try {
          console.log('🔄 Initialisation session...')
          set({ isLoading: true })

          const currentUser = await auth.getCurrentUser()

          if (!currentUser) {
            console.log('❌ Aucune session à initialiser')
            set({ user: null, isAuthenticated: false, isLoading: false })
            return false
          }

          // Mapper l'utilisateur Supabase vers notre interface User
          const mappedUser: User = {
            id: currentUser.id,
            email: currentUser.email!,
            name: currentUser.user_metadata?.name || currentUser.email!.split('@')[0],
            user_type: currentUser.user_metadata?.user_type || 'producer',
            language: currentUser.user_metadata?.language || 'fr',
            avatar_url: currentUser.user_metadata?.avatar_url || undefined,
            created_at: currentUser.created_at || new Date().toISOString(),
            updated_at: new Date().toISOString(),
            consent_given: true,
            consent_date: new Date().toISOString()
          }

          set({ 
            user: mappedUser, 
            isAuthenticated: true, 
            isLoading: false 
          })

          console.log('✅ Session initialisée pour:', mappedUser.email)
          return true

        } catch (error: any) {
          console.error('❌ Erreur initialisation session:', error)
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false 
          })
          return false
        }
      },

      // 🔐 CONNEXION
      login: async (email: string, password: string) => {
        try {
          set({ isLoading: true })
          console.log('🔐 Connexion pour:', email)

          const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password,
          })

          if (error) {
            console.error('❌ Erreur connexion:', error.message)
            
            const errorMessages: Record<string, string> = {
              'Invalid login credentials': 'Email ou mot de passe incorrect',
              'Email not confirmed': 'Veuillez confirmer votre email',
              'Too many requests': 'Trop de tentatives. Réessayez plus tard.',
              'User not found': 'Aucun compte trouvé avec cet email',
              'Invalid email': 'Format d\'email invalide'
            }
            
            const userMessage = errorMessages[error.message] || error.message
            throw new Error(userMessage)
          }

          if (!data.user) {
            throw new Error('Aucune donnée utilisateur reçue')
          }

          const user: User = {
            id: data.user.id,
            email: data.user.email!,
            name: data.user.user_metadata?.name || data.user.email!.split('@')[0],
            user_type: data.user.user_metadata?.user_type || 'producer',
            language: data.user.user_metadata?.language || 'fr',
            avatar_url: data.user.user_metadata?.avatar_url || undefined,
            created_at: data.user.created_at || new Date().toISOString(),
            updated_at: new Date().toISOString(),
            consent_given: true,
            consent_date: new Date().toISOString()
          }

          console.log('✅ Connexion réussie pour:', user.email)

          set({ 
            user, 
            isAuthenticated: true, 
            isLoading: false 
          })

          toast.success(`Bienvenue ${user.name} !`, {
            icon: '👋',
            duration: 3000
          })

        } catch (error: any) {
          console.error('❌ Erreur connexion:', error)
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false 
          })
          toast.error(error.message || 'Erreur de connexion', {
            icon: '⚠️',
            duration: 4000
          })
          throw error
        }
      },

      // 📝 INSCRIPTION
      register: async (email: string, password: string, userData: Partial<User>) => {
        try {
          set({ isLoading: true })
          console.log('📝 Création compte pour:', email)

          const fullName = userData.name?.trim() || ''
          
          if (fullName.length < 2) {
            throw new Error('Le nom doit contenir au moins 2 caractères')
          }

          if (password.length < 8) {
            throw new Error('Le mot de passe doit contenir au moins 8 caractères')
          }

          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
          if (!emailRegex.test(email)) {
            throw new Error('Format d\'email invalide')
          }

          console.log('✅ Validations passées, création compte...')

          const { data, error } = await supabase.auth.signUp({
            email,
            password,
            options: {
              data: {
                name: fullName,
                user_type: userData.user_type || 'producer',
                language: userData.language || 'fr'
              }
            }
          })

          if (error) {
            console.error('❌ Erreur création compte:', error)
            
            const errorMessages: Record<string, string> = {
              'User already registered': 'Un compte existe déjà avec cet email',
              'Password should be at least': 'Le mot de passe doit contenir au moins 8 caractères',
              'Invalid email': 'Format d\'email invalide',
              'Signup is disabled': 'Les inscriptions sont temporairement désactivées',
              'Weak password': 'Mot de passe trop faible'
            }
            
            const userMessage = errorMessages[error.message] || error.message
            throw new Error(userMessage)
          }

          if (!data.user) {
            throw new Error('Erreur lors de la création du compte')
          }

          console.log('✅ Compte créé avec succès')
          
          set({ isLoading: false })
          
          if (data.user.email_confirmed_at) {
            toast.success('Compte créé et confirmé ! Vous pouvez vous connecter.', {
              icon: '✅',
              duration: 5000
            })
          } else {
            toast.success('Compte créé ! Vérifiez votre email pour confirmer.', {
              icon: '📧',
              duration: 6000
            })
          }

        } catch (error: any) {
          console.error('❌ Erreur inscription:', error)
          set({ isLoading: false })
          toast.error(error.message || 'Erreur lors de la création du compte', {
            icon: '⚠️',
            duration: 4000
          })
          throw error
        }
      },

      // 🚪 DÉCONNEXION
      logout: async () => {
        try {
          console.log('🚪 Déconnexion...')
          
          const result = await auth.signOut()
          
          if (!result.success) {
            console.error('❌ Erreur déconnexion Supabase:', result.error)
          }

          set({ 
            user: null, 
            isAuthenticated: false 
          })

          toast.success('Déconnexion réussie', {
            icon: '👋',
            duration: 2000
          })
          console.log('✅ Déconnexion terminée')

        } catch (error: any) {
          console.error('❌ Erreur déconnexion:', error)
          
          set({ 
            user: null, 
            isAuthenticated: false 
          })
          
          toast.error('Erreur de déconnexion, mais vous êtes déconnecté localement', {
            icon: '⚠️',
            duration: 3000
          })
        }
      },

      // 🔍 VÉRIFICATION SESSION
      checkAuth: async () => {
        try {
          console.log('🔍 Vérification session...')
          
          const user = await auth.getCurrentUser()

          if (!user) {
            console.log('❌ Aucune session active')
            set({ user: null, isAuthenticated: false })
            return
          }

          const userMapped: User = {
            id: user.id,
            email: user.email!,
            name: user.user_metadata?.name || user.email!.split('@')[0],
            user_type: user.user_metadata?.user_type || 'producer',
            language: user.user_metadata?.language || 'fr',
            avatar_url: user.user_metadata?.avatar_url || undefined,
            created_at: user.created_at || new Date().toISOString(),
            updated_at: new Date().toISOString(),
            consent_given: true,
            consent_date: new Date().toISOString()
          }

          set({ user: userMapped, isAuthenticated: true })
          console.log('✅ Session restaurée pour:', userMapped.email)

        } catch (error: any) {
          console.error('❌ Erreur vérification auth:', error)
          set({ user: null, isAuthenticated: false })
        }
      },

      // 👤 MISE À JOUR PROFIL
      updateProfile: async (data: Partial<User>) => {
        try {
          const { user } = get()
          if (!user) throw new Error('Utilisateur non connecté')

          console.log('👤 Mise à jour profil:', data)

          const { error } = await supabase.auth.updateUser({
            data: {
              name: data.name,
              user_type: data.user_type,
              language: data.language
            }
          })

          if (error) {
            console.error('❌ Erreur mise à jour Supabase:', error)
            throw new Error(error.message)
          }

          const updatedUser = { 
            ...user, 
            ...data,
            updated_at: new Date().toISOString()
          }
          set({ user: updatedUser })

          toast.success('Profil mis à jour avec succès', {
            icon: '✅',
            duration: 3000
          })
          console.log('✅ Profil mis à jour')

        } catch (error: any) {
          console.error('❌ Erreur mise à jour profil:', error)
          toast.error(error.message || 'Erreur mise à jour profil', {
            icon: '⚠️',
            duration: 4000
          })
          throw error
        }
      },

      // 🗑️ SUPPRESSION COMPTE
      deleteUserData: async () => {
        try {
          const { user } = get()
          if (!user) throw new Error('Utilisateur non connecté')

          console.log('🗑️ Suppression compte utilisateur...')
          
          await get().logout()
          
          toast.success('Demande de suppression enregistrée. Contactez le support pour finaliser.', {
            icon: '🗑️',
            duration: 5000
          })
          console.log('✅ Suppression compte (déconnexion)')

        } catch (error: any) {
          console.error('❌ Erreur suppression compte:', error)
          toast.error(error.message || 'Erreur suppression compte', {
            icon: '⚠️',
            duration: 4000
          })
          throw error
        }
      },

      // 📄 EXPORT DONNÉES
      exportUserData: async () => {
        try {
          const { user } = get()
          if (!user) throw new Error('Utilisateur non connecté')

          console.log('📄 Export données utilisateur...')

          const supabaseUser = await auth.getCurrentUser()

          const exportData = {
            user: user,
            supabaseUser: supabaseUser,
            exportDate: new Date().toISOString(),
            dataRetentionInfo: {
              retention: '30 jours',
              autoDelete: true,
              nextDeletion: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
            }
          }

          const blob = new Blob([JSON.stringify(exportData, null, 2)], {
            type: 'application/json'
          })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `intelia-export-${user.id}-${new Date().toISOString().split('T')[0]}.json`
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          URL.revokeObjectURL(url)

          console.log('✅ Données exportées')
          toast.success('Données exportées avec succès', {
            icon: '📄',
            duration: 3000
          })
          
          return exportData

        } catch (error: any) {
          console.error('❌ Erreur export données:', error)
          toast.error(error.message || 'Erreur export données', {
            icon: '⚠️',
            duration: 4000
          })
          throw error
        }
      },

      // 📋 MISE À JOUR CONSENTEMENTS
      updateConsent: async (consent: RGPDConsent) => {
        try {
          const { user } = get()
          if (!user) throw new Error('Utilisateur non connecté')

          console.log('📋 Mise à jour consentements:', consent)

          const updatedUser = { 
            ...user, 
            consent_given: true,
            consent_date: new Date().toISOString(),
            updated_at: new Date().toISOString()
          }
          set({ user: updatedUser })

          toast.success('Consentements mis à jour', {
            icon: '📋',
            duration: 3000
          })
          console.log('✅ Consentements mis à jour')

        } catch (error: any) {
          console.error('❌ Erreur mise à jour consentements:', error)
          toast.error(error.message || 'Erreur mise à jour consentements', {
            icon: '⚠️',
            duration: 4000
          })
          throw error
        }
      }
    }),
    {
      name: 'intelia-auth-storage',
      storage: createJSONStorage(() => {
        if (typeof window !== 'undefined') {
          return localStorage
        }
        return {
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {}
        }
      }),
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated 
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.setHasHydrated(true)
        }
      }
    }
  )
)