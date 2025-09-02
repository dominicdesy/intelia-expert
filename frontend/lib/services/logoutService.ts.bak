// lib/services/logoutService.ts
// Service de logout independant pour eviter les problemes React #300

export const logoutService = {
  async performLogout(user?: any): Promise<void> {
    console.log('[LogoutService] Debut deconnexion via service independant')
    
    try {
      // 1. Detecter la langue de l'utilisateur AVANT le nettoyage
      let userLanguage = 'fr' // Defaut francais
      try {
        // Methode 1: Depuis le parametre user passe
        if (user?.language) {
          userLanguage = user.language
          console.log('[LogoutService] Langue detectee depuis user:', userLanguage)
        }
        // Methode 2: Depuis le localStorage du store Zustand
        else {
          const zustandLang = localStorage.getItem('intelia-language')
          if (zustandLang) {
            const parsed = JSON.parse(zustandLang)
            userLanguage = parsed?.state?.currentLanguage || 'fr'
            console.log('[LogoutService] Langue detectee depuis localStorage:', userLanguage)
          }
        }
      } catch (error) {
        console.warn('[LogoutService] Erreur detection langue, utilisation du francais:', error)
      }

      // 2. Preserver RememberMe si necessaire
      let preservedRememberMe = null
      try {
        const rememberMeData = localStorage.getItem('intelia-remember-me-persist')
        if (rememberMeData) {
          preservedRememberMe = JSON.parse(rememberMeData)
          console.log('[LogoutService] RememberMe preserve')
        }
      } catch (error) {
        console.warn('[LogoutService] Erreur preservation RememberMe:', error)
      }

      // 3. Deconnexion Supabase
      console.log('[LogoutService] Tentative deconnexion Supabase...')
      try {
        const { getSupabaseClient } = await import('@/lib/supabase/singleton')
        const supabase = getSupabaseClient()
        await supabase.auth.signOut()
        console.log('[LogoutService] Deconnexion Supabase terminee')
      } catch (supabaseError) {
        console.warn('[LogoutService] Erreur Supabase (continue quand meme):', supabaseError)
      }

      // 4. Nettoyage localStorage selectif
      console.log('[LogoutService] Nettoyage localStorage...')
      const keysToRemove = []
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key && key !== 'intelia-remember-me-persist' && key !== 'intelia-language') {
          // ✅ CORRECTION : Nettoyage plus ciblé pour éviter de supprimer les stores Zustand
          if (key.startsWith('supabase-') || 
              key === 'intelia-expert-auth' ||
              key === 'intelia-chat-storage' ||
              key.includes('session')) {
            keysToRemove.push(key)
          }
        }
      }
      
      keysToRemove.forEach(key => {
        try {
          localStorage.removeItem(key)
          console.log(`[LogoutService] Supprime: ${key}`)
        } catch (e) {
          console.warn(`[LogoutService] Impossible de supprimer ${key}:`, e)
        }
      })
      
      // ✅ NOUVEAU : Réinitialiser le store auth au lieu de le supprimer
      try {
        localStorage.setItem('auth-storage', JSON.stringify({
          state: {
            user: null,
            isAuthenticated: false,
            isLoading: false,
            hasHydrated: true
          },
          version: 0
        }))
        console.log('[LogoutService] Store auth réinitialisé')
      } catch (error) {
        console.warn('[LogoutService] Erreur réinitialisation store auth:', error)
      }
      
      console.log(`[LogoutService] ${keysToRemove.length} cles supprimees, RememberMe et Language preserves, Store auth reinitialise`)

      // 5. Restaurer RememberMe si necessaire
      if (preservedRememberMe) {
        try {
          localStorage.setItem('intelia-remember-me-persist', JSON.stringify(preservedRememberMe))
          console.log('[LogoutService] RememberMe restaure')
        } catch (error) {
          console.warn('[LogoutService] Erreur restauration RememberMe:', error)
        }
      }

      // 6. Preserver la langue pour la page d'accueil (plus nécessaire car intelia-language est préservé)
      sessionStorage.setItem('recent-logout', Date.now().toString())
      sessionStorage.setItem('logout-complete', 'true')
      
      console.log('[LogoutService] Redirection vers page d\'accueil, langue preservee:', userLanguage)
      
      // 7. Rediriger vers la page d'accueil (app/page.tsx) dans la bonne langue
      setTimeout(() => {
        window.location.href = '/'
      }, 100)
      
    } catch (error) {
      console.error('[LogoutService] Erreur durant logout:', error)
      // En cas d'erreur, forcer quand meme la redirection vers la page d'accueil
      setTimeout(() => {
        window.location.href = '/'
      }, 100)
    }
  }
}