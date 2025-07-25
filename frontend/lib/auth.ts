// lib/auth.ts - VERSION PROFESSIONNELLE CORRIGÉE

import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import type { User } from '@supabase/supabase-js'
import { 
  AuthError, 
  AuthErrorFactory,
  InvalidCredentialsError,
  EmailNotConfirmedError,
  TooManyRequestsError,
  NetworkError 
} from './errors/auth-errors'

export interface LoginCredentials {
  email: string
  password: string
}

export interface SignUpCredentials extends LoginCredentials {
  name?: string
  metadata?: Record<string, any>
}

export interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  error: AuthError | null
}

/**
 * Service d'authentification professionnel avec gestion d'erreurs robuste
 * Architecture: Clean Code + Error Handling + Type Safety
 */
export class AuthService {
  private supabase = createClientComponentClient()

  /**
   * Connexion utilisateur avec gestion d'erreurs professionnelle
   */
  async login(credentials: LoginCredentials): Promise<User> {
    try {
      console.log('🔐 Tentative de connexion:', credentials.email)
      
      const { data, error } = await this.supabase.auth.signInWithPassword({
        email: credentials.email,
        password: credentials.password,
      })

      // Gestion des erreurs Supabase
      if (error) {
        console.error('❌ Erreur Supabase:', error)
        throw AuthErrorFactory.fromSupabaseError(error)
      }

      // Validation des données retournées
      if (!data.user) {
        throw new AuthError(
          'Aucun utilisateur retourné par le serveur',
          'NO_USER_RETURNED',
          500
        )
      }

      console.log('✅ Connexion réussie:', data.user.email)
      return data.user

    } catch (error) {
      // Si c'est déjà une AuthError, la propager
      if (error instanceof AuthError) {
        throw error
      }

      // Si c'est une erreur réseau ou autre
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw AuthErrorFactory.networkError()
      }

      // Erreur inconnue
      console.error('❌ Erreur inattendue lors de la connexion:', error)
      throw new AuthError(
        'Erreur inattendue lors de la connexion',
        'UNEXPECTED_LOGIN_ERROR',
        500
      )
    }
  }

  /**
   * Inscription utilisateur
   */
  async signUp(credentials: SignUpCredentials): Promise<User> {
    try {
      console.log('📝 Tentative d\'inscription:', credentials.email)

      const { data, error } = await this.supabase.auth.signUp({
        email: credentials.email,
        password: credentials.password,
        options: {
          data: {
            name: credentials.name || '',
            ...credentials.metadata
          }
        }
      })

      if (error) {
        console.error('❌ Erreur inscription:', error)
        throw AuthErrorFactory.fromSupabaseError(error)
      }

      if (!data.user) {
        throw new AuthError(
          'Échec de la création du compte',
          'SIGNUP_FAILED',
          500
        )
      }

      console.log('✅ Inscription réussie:', data.user.email)
      return data.user

    } catch (error) {
      if (error instanceof AuthError) {
        throw error
      }

      console.error('❌ Erreur inattendue lors de l\'inscription:', error)
      throw new AuthError(
        'Erreur lors de la création du compte',
        'UNEXPECTED_SIGNUP_ERROR',
        500
      )
    }
  }

  /**
   * Déconnexion utilisateur
   */
  async logout(): Promise<void> {
    try {
      console.log('🚪 Déconnexion en cours...')

      const { error } = await this.supabase.auth.signOut()

      if (error) {
        console.error('❌ Erreur déconnexion:', error)
        throw AuthErrorFactory.fromSupabaseError(error)
      }

      console.log('✅ Déconnexion réussie')

    } catch (error) {
      if (error instanceof AuthError) {
        throw error
      }

      console.error('❌ Erreur inattendue lors de la déconnexion:', error)
      throw new AuthError(
        'Erreur lors de la déconnexion',
        'UNEXPECTED_LOGOUT_ERROR',
        500
      )
    }
  }

  /**
   * Obtenir l'utilisateur actuel
   */
  async getCurrentUser(): Promise<User | null> {
    try {
      const { data: { user }, error } = await this.supabase.auth.getUser()

      if (error) {
        console.error('❌ Erreur récupération utilisateur:', error)
        return null // Ne pas throw pour cette méthode
      }

      return user

    } catch (error) {
      console.error('❌ Erreur inattendue récupération utilisateur:', error)
      return null
    }
  }

  /**
   * Réinitialisation mot de passe
   */
  async resetPassword(email: string): Promise<void> {
    try {
      console.log('🔄 Réinitialisation mot de passe:', email)

      const { error } = await this.supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`
      })

      if (error) {
        console.error('❌ Erreur réinitialisation:', error)
        throw AuthErrorFactory.fromSupabaseError(error)
      }

      console.log('✅ Email de réinitialisation envoyé')

    } catch (error) {
      if (error instanceof AuthError) {
        throw error
      }

      console.error('❌ Erreur inattendue réinitialisation:', error)
      throw new AuthError(
        'Erreur lors de la réinitialisation',
        'UNEXPECTED_RESET_ERROR',
        500
      )
    }
  }

  /**
   * Écouter les changements d'état d'authentification
   */
  onAuthStateChange(callback: (user: User | null) => void) {
    return this.supabase.auth.onAuthStateChange((event, session) => {
      console.log('🔄 Changement d\'état auth:', event)
      callback(session?.user || null)
    })
  }
}

// Export d'une instance singleton
export const authService = new AuthService()

// Export des types d'erreurs pour l'utilisation dans les composants
export {
  AuthError,
  InvalidCredentialsError,
  EmailNotConfirmedError,
  TooManyRequestsError,
  NetworkError
} from './errors/auth-errors'