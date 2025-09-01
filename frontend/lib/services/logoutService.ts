// lib/services/logoutService.ts
// Service de logout independant pour eviter les problemes React #300

export const logoutService = {
  async performLogout(): Promise<void> {
    console.log('[LogoutService] Debut deconnexion via service independant')
    
    try {
      // 1. Preserver RememberMe si necessaire
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

      // 2. Deconnexion Supabase
      console.log('[LogoutService] Tentative deconnexion Supabase...')
      try {
        const { getSupabaseClient } = await import('@/lib/supabase/singleton')
        const supabase = getSupabaseClient()
        await supabase.auth.signOut()
        console.log('[LogoutService] Deconnexion Supabase terminee')
      } catch (supabaseError) {
        console.warn('[LogoutService] Erreur Supabase (continue quand meme):', supabaseError)
      }

      // 3. Nettoyage localStorage selectif
      console.log('[LogoutService] Nettoyage localStorage...')
      const keysToRemove = []
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key && key !== 'intelia-remember-me-persist') {
          // Supprimer les cles auth/session mais GARDER RememberMe
          if (key.startsWith('supabase-') || 
              (key.startsWith('intelia-') && key !== 'intelia-remember-me-persist') ||
              key.includes('auth') || 
              key.includes('session') ||
              key === 'intelia-expert-auth' ||
              key === 'intelia-chat-storage') {
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
      
      console.log(`[LogoutService] ${keysToRemove.length} cles supprimees, RememberMe preserve`)

      // 4. Restaurer RememberMe si necessaire
      if (preservedRememberMe) {
        try {
          localStorage.setItem('intelia-remember-me-persist', JSON.stringify(preservedRememberMe))
          console.log('[LogoutService] RememberMe restaure')
        } catch (error) {
          console.warn('[LogoutService] Erreur restauration RememberMe:', error)
        }
      }

      // 5. Marquer la deconnexion et forcer le reload
      sessionStorage.setItem('recent-logout', Date.now().toString())
      sessionStorage.setItem('logout-complete', 'true')
      
      console.log('[LogoutService] Redirection forcee vers /')
      
      // 6. Reload complet pour eviter tous les problemes de state React/Zustand
      setTimeout(() => {
        window.location.href = '/'
      }, 100) // Petit delai pour voir les logs
      
    } catch (error) {
      console.error('[LogoutService] Erreur durant logout:', error)
      // En cas d'erreur, forcer quand meme le reload
      setTimeout(() => {
        window.location.href = '/'
      }, 100)
    }
  }
}