// lib/services/logoutService.ts
// Service de logout indépendant pour éviter les problèmes React #300

export const logoutService = {
  async performLogout(): Promise<void> {
    console.log('[LogoutService] Début déconnexion via service indépendant')
    
    try {
      // 1. Préserver RememberMe si nécessaire
      let preservedRememberMe = null
      try {
        const rememberMeData = localStorage.getItem('intelia-remember-me-persist')
        if (rememberMeData) {
          preservedRememberMe = JSON.parse(rememberMeData)
          console.log('[LogoutService] RememberMe préservé')
        }
      } catch (error) {
        console.warn('[LogoutService] Erreur préservation RememberMe:', error)
      }

      // 2. Déconnexion Supabase
      const { getSupabaseClient } = await import('@/lib/supabase/singleton')
      const supabase = getSupabaseClient()
      await supabase.auth.signOut()
      console.log('[LogoutService] Déconnexion Supabase terminée')

      // 3. Nettoyage localStorage sélectif
      const keysToRemove = []
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
      
      keysToRemove.forEach(key => {
        try {
          localStorage.removeItem(key)
          console.log(`[LogoutService] Supprimé: ${key}`)
        } catch (e) {
          console.warn(`[LogoutService] Impossible de supprimer ${key}:`, e)
        }
      })
      
      console.log(`[LogoutService] ${keysToRemove.length} clés supprimées, RememberMe préservé`)

      // 4. Restaurer RememberMe si nécessaire
      if (preservedRememberMe) {
        try {
          localStorage.setItem('intelia-remember-me-persist', JSON.stringify(preservedRememberMe))
          console.log('[LogoutService] RememberMe restauré')
        } catch (error) {
          console.warn('[LogoutService] Erreur restauration RememberMe:', error)
        }
      }

      // 5. Marquer la déconnexion et forcer le reload pour reset tous les états React
      sessionStorage.setItem('recent-logout', Date.now().toString())
      sessionStorage.setItem('logout-complete', 'true')
      
      console.log('[LogoutService] Redirection forcée vers /')
      
      // 6. Reload complet pour éviter tous les problèmes de state React/Zustand
      window.location.href = '/'
      
    } catch (error) {
      console.error('[LogoutService] Erreur durant logout:', error)
      // En cas d'erreur, forcer quand même le reload
      window.location.href = '/'
    }
  }
}