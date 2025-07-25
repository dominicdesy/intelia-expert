// lib/auth.ts - Authentification Supabase réelle

import { createClient } from '@supabase/supabase-js'

// Configuration Supabase
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Types pour l'authentification
export interface AuthUser {
  id: string
  email: string
  name?: string
  user_type?: 'producer' | 'professional'
  language?: 'fr' | 'en' | 'es'
}

export interface AuthError {
  message: string
  status?: number
}

// Service d'authentification
export class AuthService {
  
  // Connexion utilisateur
  static async signIn(email: string, password: string): Promise<AuthUser> {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password: password
      })

      if (error) {
        console.error('❌ Erreur login:', error)
        throw new AuthError(this.getErrorMessage(error.message))
      }

      if (!data.user) {
        throw new AuthError('Aucun utilisateur trouvé')
      }

      // Récupérer le profil utilisateur
      const profile = await this.getUserProfile(data.user.id)
      
      return {
        id: data.user.id,
        email: data.user.email!,
        ...profile
      }

    } catch (error: any) {
      console.error('❌ Erreur connexion:', error)
      throw error instanceof AuthError ? error : new AuthError('Erreur de connexion')
    }
  }

  // Inscription utilisateur
  static async signUp(
    email: string, 
    password: string, 
    userData: {
      name: string
      user_type: 'producer' | 'professional'
      language: 'fr' | 'en' | 'es'
    }
  ): Promise<{ needsConfirmation: boolean }> {
    try {
      const { data, error } = await supabase.auth.signUp({
        email: email.trim(),
        password: password,
        options: {
          data: {
            name: userData.name,
            user_type: userData.user_type,
            language: userData.language
          }
        }
      })

      if (error) {
        console.error('❌ Erreur inscription:', error)
        throw new AuthError(this.getErrorMessage(error.message))
      }

      // Créer le profil utilisateur
      if (data.user && !data.user.email_confirmed_at) {
        await this.createUserProfile(data.user.id, userData)
      }

      return {
        needsConfirmation: !data.user?.email_confirmed_at
      }

    } catch (error: any) {
      console.error('❌ Erreur inscription:', error)
      throw error instanceof AuthError ? error : new AuthError('Erreur lors de l\'inscription')
    }
  }

  // Réinitialisation mot de passe
  static async resetPassword(email: string): Promise<void> {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/reset-password`
      })

      if (error) {
        console.error('❌ Erreur reset password:', error)
        throw new AuthError(this.getErrorMessage(error.message))
      }

    } catch (error: any) {
      console.error('❌ Erreur reset:', error)
      throw error instanceof AuthError ? error : new AuthError('Erreur lors de la réinitialisation')
    }
  }

  // Déconnexion
  static async signOut(): Promise<void> {
    try {
      const { error } = await supabase.auth.signOut()
      if (error) {
        console.error('❌ Erreur logout:', error)
        throw new AuthError('Erreur lors de la déconnexion')
      }
    } catch (error: any) {
      console.error('❌ Erreur déconnexion:', error)
      throw new AuthError('Erreur lors de la déconnexion')
    }
  }

  // Récupérer session actuelle
  static async getCurrentUser(): Promise<AuthUser | null> {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      
      if (!session?.user) {
        return null
      }

      const profile = await this.getUserProfile(session.user.id)
      
      return {
        id: session.user.id,
        email: session.user.email!,
        ...profile
      }

    } catch (error) {
      console.error('❌ Erreur récupération utilisateur:', error)
      return null
    }
  }

  // Créer profil utilisateur
  private static async createUserProfile(userId: string, userData: any): Promise<void> {
    try {
      const { error } = await supabase
        .from('user_profiles')
        .insert([
          {
            id: userId,
            name: userData.name,
            user_type: userData.user_type,
            language: userData.language,
            created_at: new Date().toISOString()
          }
        ])

      if (error) {
        console.error('❌ Erreur création profil:', error)
      }
    } catch (error) {
      console.error('❌ Erreur profil:', error)
    }
  }

  // Récupérer profil utilisateur
  private static async getUserProfile(userId: string): Promise<Partial<AuthUser>> {
    try {
      const { data, error } = await supabase
        .from('user_profiles')
        .select('name, user_type, language')
        .eq('id', userId)
        .single()

      if (error || !data) {
        return {}
      }

      return {
        name: data.name,
        user_type: data.user_type,
        language: data.language
      }
    } catch (error) {
      console.error('❌ Erreur récupération profil:', error)
      return {}
    }
  }

  // Messages d'erreur traduits
  private static getErrorMessage(error: string): string {
    const errorMessages: { [key: string]: string } = {
      'Invalid login credentials': 'Email ou mot de passe incorrect',
      'Email not confirmed': 'Veuillez confirmer votre email avant de vous connecter',
      'User already registered': 'Un compte existe déjà avec cette adresse email',
      'Password should be at least 6 characters': 'Le mot de passe doit contenir au moins 6 caractères',
      'Unable to validate email address: invalid format': 'Format d\'email invalide',
      'Signup is disabled': 'Les inscriptions sont temporairement désactivées',
      'Too many requests': 'Trop de tentatives. Veuillez patienter quelques minutes.',
      'Invalid email': 'Adresse email invalide'
    }

    return errorMessages[error] || error || 'Une erreur est survenue'
  }
}

// Hook pour utiliser l'authentification
export function useAuthState() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Récupérer utilisateur initial
    AuthService.getCurrentUser().then(user => {
      setUser(user)
      setLoading(false)
    })

    // Écouter les changements d'état d'auth
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (session?.user) {
          const profile = await AuthService.getUserProfile(session.user.id)
          setUser({
            id: session.user.id,
            email: session.user.email!,
            ...profile
          })
        } else {
          setUser(null)
        }
        setLoading(false)
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  return { user, loading }
}
