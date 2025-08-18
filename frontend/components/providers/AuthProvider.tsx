'use client'

import { useEffect, useRef, useState, createContext, useContext } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'

interface AuthProviderProps {
  children: React.ReactNode
}

// ✅ NOUVEAU CONTEXTE pour partager l'état auth avec tous les composants
interface AuthContextType {
  isAuthReady: boolean
  isInGracePeriod: boolean
  authErrors: string[]
  isRecovering: boolean
  clearAuthErrors: () => void
}

const AuthContext = createContext<AuthContextType>({
  isAuthReady: false,
  isInGracePeriod: true,
  authErrors: [],
  isRecovering: false,
  clearAuthErrors: () => {}
})

export const useAuthContext = () => useContext(AuthContext)

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter()
  const { 
    checkAuth, 
    isLoading, 
    hasHydrated, 
    isAuthenticated,
    // ✅ NOUVEAUX ÉTATS du store amélioré
    authErrors,
    isRecovering,
    clearAuthErrors,
    lastAuthCheck
  } = useAuthStore()
  const pathname = usePathname()

  // 🔥 PROTECTION ANTI-BOUCLE RENFORCÉE
  const authCheckLock = useRef(false)
  const lastPathname = useRef('')
  const gracePeriodTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const authCheckTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  
  const [isInitialized, setIsInitialized] = useState(false)
  // ✅ NOUVEAUX ÉTATS pour période de grâce
  const [isInGracePeriod, setIsInGracePeriod] = useState(true)
  const [isAuthReady, setIsAuthReady] = useState(false)
  const [gracePeriodCount, setGracePeriodCount] = useState(0)

  // ✅ Pages publiques où on ne doit PAS vérifier l'auth
  const publicRoutes = [
    '/',
    '/auth',
    '/auth/login',
    '/auth/register', 
    '/auth/signup',
    '/auth/callback',
    '/auth/reset',
    '/auth/forgot-password',
    '/terms',
    '/privacy'
  ]

  const isPublicPage = publicRoutes.some(route => 
    pathname === route || pathname.startsWith(route + '/')
  ) || pathname.startsWith('/auth/')

  // 🚨 PAGES PROTÉGÉES - Nécessitent authentification
  const protectedRoutes = ['/chat', '/dashboard', '/profile', '/settings']
  const isProtectedPage = protectedRoutes.some(route => 
    pathname === route || pathname.startsWith(route + '/')
  )

  // 🔍 FONCTION DE DEBUG AJOUTÉE
  const debugAuthCheck = () => {
    console.log('=== DEBUG: AuthProvider checkAuth ===')
    console.log('Supabase config:', {
      url: process.env.NEXT_PUBLIC_SUPABASE_URL ? 'OK' : 'MANQUANT',
      key: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? 'OK' : 'MANQUANT',
      url_value: process.env.NEXT_PUBLIC_SUPABASE_URL,
      key_length: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.length
    })
    console.log('Contexte:', {
      pathname,
      isPublicPage,
      isProtectedPage,
      isAuthenticated,
      isLoading,
      hasHydrated,
      isInGracePeriod
    })
  }

  // ✅ NOUVELLE FONCTION : Gestion intelligente de la redirection
  const handleAuthRedirect = (reason: string) => {
    console.log('🔄 [AuthProvider] Redirection vers login:', reason)
    
    // Nettoyer les timeouts
    if (authCheckTimeoutRef.current) {
      clearTimeout(authCheckTimeoutRef.current)
    }
    
    try {
      // Utiliser router.replace pour éviter les boucles
      router.replace('/')
    } catch (error) {
      console.error('🔧 [AuthProvider] Erreur redirection router:', error)
      // Fallback vers window.location si nécessaire
      if (typeof window !== 'undefined') {
        window.location.href = '/'
      }
    }
  }

  // ✅ NOUVELLE GESTION : Période de grâce pour éviter redirections prématurées
  useEffect(() => {
    // 🔥 PROTECTION CRITIQUE : Éviter la boucle infinie
    if (!hasHydrated || isInGracePeriod === false) return

    // 🔥 PROTECTION : Ne démarrer qu'une seule fois
    if (gracePeriodCount > 0) {
      console.log('⚠️ [AuthProvider] Période de grâce déjà démarrée, skip')
      return
    }

    const gracePeriodDuration = isPublicPage ? 1000 : 3000 // Plus court pour pages publiques
    
    if (gracePeriodTimeoutRef.current) {
      clearTimeout(gracePeriodTimeoutRef.current)
    }
    
    setGracePeriodCount(1) // Marquer comme démarré
    console.log(`🔄 [AuthProvider] Période de grâce démarrée UNIQUE (${gracePeriodDuration}ms)`)
    
    gracePeriodTimeoutRef.current = setTimeout(() => {
      console.log('✅ [AuthProvider] Période de grâce terminée')
      setIsInGracePeriod(false)
      setIsAuthReady(true)
      
      // Si on est sur page protégée et pas authentifié après grâce, vérifier une dernière fois
      if (isProtectedPage && !isAuthenticated && !isLoading) {
        console.log('🔍 [AuthProvider] Vérification finale après période de grâce')
        
        authCheckTimeoutRef.current = setTimeout(() => {
          const currentState = useAuthStore.getState()
          if (!currentState.isAuthenticated && isProtectedPage && !currentState.isLoading) {
            handleAuthRedirect('Non authentifié après période de grâce')
          }
        }, 1000)
      }
    }, gracePeriodDuration)

    return () => {
      if (gracePeriodTimeoutRef.current) {
        clearTimeout(gracePeriodTimeoutRef.current)
      }
    }
  }, [hasHydrated]) // 🔥 DÉPENDANCES RÉDUITES - seulement hasHydrated

  // 🔥 INITIALISATION UNE SEULE FOIS
  useEffect(() => {
    if (!hasHydrated || isInitialized) {
      return
    }

    console.log('🔧 [AuthProvider] Initialisation provider')
    setIsInitialized(true)
  }, [hasHydrated, isInitialized])

  // ✅ SURVEILLANCE DES ERREURS AUTH pour redirection automatique
  useEffect(() => {
    if (!isAuthReady || isInGracePeriod) return
    
    // Si erreurs critiques de session et on est sur page protégée
    if (authErrors.length > 0 && isProtectedPage) {
      const hasSessionError = authErrors.some(error => 
        error.includes('Session expirée') || 
        error.includes('Auth session missing') ||
        error.includes('Forbidden')
      )
      
      if (hasSessionError && !isAuthenticated) {
        console.log('🔄 [AuthProvider] Erreur session détectée, redirection')
        handleAuthRedirect('Erreur de session détectée')
      }
    }
  }, [authErrors, isProtectedPage, isAuthenticated, isAuthReady, isInGracePeriod])

  // 🔥 VÉRIFICATION AUTH PROTÉGÉE ET INTELLIGENTE
  useEffect(() => {
    // Attendre l'initialisation et la fin de la période de grâce
    if (!isInitialized || !hasHydrated || isInGracePeriod) {
      return
    }

    // Skip si page publique
    if (isPublicPage) {
      console.log('ℹ️ [AuthProvider] Page publique détectée, skip auth check:', pathname)
      authCheckLock.current = false // Reset le lock pour les pages publiques
      return
    }

    // Skip si pas une page protégée
    if (!isProtectedPage) {
      console.log('ℹ️ [AuthProvider] Page non protégée, skip:', pathname)
      return
    }

    // 🛡️ PROTECTION CONTRE MULTIPLES APPELS
    if (authCheckLock.current && lastPathname.current === pathname) {
      console.log('⚠️ [AuthProvider] Auth déjà vérifié pour cette page, skip')
      return
    }

    // ✅ NOUVEAU: Éviter les vérifications trop fréquentes
    const now = Date.now()
    if (lastAuthCheck && now - lastAuthCheck < 2000) {
      console.log('🔄 [AuthProvider] Vérification auth trop récente, skip')
      return
    }

    // 🔥 NOUVEAU: Si déjà authentifié sur une page protégée, pas besoin de re-vérifier
    if (isAuthenticated && lastPathname.current === pathname && !isRecovering) {
      console.log('✅ [AuthProvider] Utilisateur déjà authentifié et stable, skip verification')
      return
    }

    console.log('🔍 [AuthProvider] Vérification auth pour page protégée:', pathname)
    
    // 🔍 APPEL DU DEBUG ICI
    debugAuthCheck()
    
    // Marquer comme en cours de vérification
    authCheckLock.current = true
    lastPathname.current = pathname

    // Vérifier l'auth avec délai pour éviter conflits
    if (authCheckTimeoutRef.current) {
      clearTimeout(authCheckTimeoutRef.current)
    }
    
    authCheckTimeoutRef.current = setTimeout(() => {
      checkAuth()
        .then(() => {
          // Après vérification, si toujours pas authentifié sur page protégée
          setTimeout(() => {
            const currentState = useAuthStore.getState()
            if (!currentState.isAuthenticated && isProtectedPage && !currentState.isLoading) {
              console.log('🔄 [AuthProvider] Toujours non authentifié après vérification')
              handleAuthRedirect('Échec vérification auth')
            }
          }, 1000)
        })
        .catch((error) => {
          console.error('❌ [AuthProvider] Erreur vérification auth:', error)
          if (isProtectedPage) {
            handleAuthRedirect('Erreur lors de la vérification')
          }
        })
        .finally(() => {
          // 🔥 IMPORTANT: Reset le lock après vérification
          authCheckLock.current = false
        })
    }, 200) // Délai plus court pour réactivité

    return () => {
      if (authCheckTimeoutRef.current) {
        clearTimeout(authCheckTimeoutRef.current)
      }
    }
  }, [
    pathname, 
    isPublicPage, 
    isProtectedPage, 
    checkAuth, 
    isInitialized, 
    hasHydrated,
    isAuthenticated,
    isInGracePeriod,
    isRecovering,
    lastAuthCheck
  ])

  // 🔥 RESET DES FLAGS LORS DU CHANGEMENT DE PAGE
  useEffect(() => {
    if (lastPathname.current !== pathname) {
      console.log('🔄 [AuthProvider] Changement de page:', lastPathname.current, '→', pathname)
      
      // Reset seulement si on change vraiment de page
      if (lastPathname.current !== '') {
        authCheckLock.current = false
        // Nettoyer les erreurs lors du changement de page vers page publique
        if (isPublicPage && authErrors.length > 0) {
          clearAuthErrors()
        }
      }
    }
  }, [pathname, isPublicPage, authErrors, clearAuthErrors])

  // ✅ NETTOYAGE lors du démontage
  useEffect(() => {
    return () => {
      if (gracePeriodTimeoutRef.current) {
        clearTimeout(gracePeriodTimeoutRef.current)
      }
      if (authCheckTimeoutRef.current) {
        clearTimeout(authCheckTimeoutRef.current)
      }
    }
  }, [])

  // 🔥 LOADING STATE AMÉLIORÉ avec période de grâce
  if (!hasHydrated || !isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Initialisation...</p>
        </div>
      </div>
    )
  }

  // ✅ NOUVEAU: Loading pendant période de grâce sur pages protégées
  if (isInGracePeriod && isProtectedPage) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-pulse h-8 w-8 bg-emerald-300 rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">Vérification de l'authentification...</p>
          <div className="mt-2 text-xs text-gray-500">
            Patientez quelques instants... ({gracePeriodCount}/3)
          </div>
          
          {/* ✅ AFFICHAGE DES ERREURS PENDANT LA PÉRIODE DE GRÂCE */}
          {authErrors.length > 0 && (
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg max-w-md mx-auto">
              <p className="text-yellow-800 text-sm font-medium">Problème détecté :</p>
              <p className="text-yellow-700 text-xs mt-1">
                {authErrors[authErrors.length - 1]}
              </p>
            </div>
          )}
        </div>
      </div>
    )
  }

  // ✅ Loader seulement si on charge ET qu'on est sur une page protégée
  if (isLoading && isProtectedPage && !isPublicPage && isAuthReady) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Vérification de l'authentification...</p>
          
          {/* ✅ INDICATEUR DE RÉCUPÉRATION */}
          {isRecovering && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg max-w-md mx-auto">
              <p className="text-blue-800 text-sm">Récupération de la session en cours...</p>
            </div>
          )}
        </div>
      </div>
    )
  }

  // ✅ CONTEXTE AUTH pour tous les composants enfants
  const authContextValue: AuthContextType = {
    isAuthReady,
    isInGracePeriod,
    authErrors,
    isRecovering,
    clearAuthErrors
  }

  return (
    <AuthContext.Provider value={authContextValue}>
      {children}
    </AuthContext.Provider>
  )
}