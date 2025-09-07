// AuthProvider.tsx - Version avec session tracking automatique
'use client'

import React, { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { 
    hasHydrated, 
    setHasHydrated, 
    checkAuth, 
    isAuthenticated,
    initializeSession,
    sendHeartbeat 
  } = useAuthStore()

  // Initialisation unique avec session tracking
  useEffect(() => {
    if (!hasHydrated) {
      setHasHydrated(true)
      
      // Utiliser initializeSession au lieu de checkAuth pour démarrer le tracking
      initializeSession()
    }
  }, [hasHydrated, setHasHydrated, initializeSession])

  // Gestion des redirections
  useEffect(() => {
    if (!hasHydrated) return

    const publicRoutes = ['/', '/auth/login', '/auth/signup', '/auth/forgot-password', '/auth/reset-password', '/privacy', '/terms']
    
    if (isAuthenticated && publicRoutes.includes(pathname)) {
      router.push('/chat')
    }
  }, [isAuthenticated, pathname, hasHydrated, router])

  // Heartbeat automatique pour maintenir la session active
  useEffect(() => {
    if (!isAuthenticated) return

    // Heartbeat initial après 30 secondes
    const initialHeartbeat = setTimeout(() => {
      sendHeartbeat()
    }, 30000)

    // Heartbeat régulier toutes les 2 minutes
    const heartbeatInterval = setInterval(() => {
      sendHeartbeat()
    }, 120000) // 2 minutes

    console.log('[AuthProvider] Heartbeat automatique activé')

    return () => {
      clearTimeout(initialHeartbeat)
      clearInterval(heartbeatInterval)
      console.log('[AuthProvider] Heartbeat automatique désactivé')
    }
  }, [isAuthenticated, sendHeartbeat])

  // Gestion de la fermeture de l'onglet/navigateur pour terminer la session proprement
  useEffect(() => {
    if (!isAuthenticated) return

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      // Envoyer un signal de fin de session via beacon API (non-bloquant)
      const authData = localStorage.getItem('intelia-expert-auth')
      if (authData) {
        try {
          const parsed = JSON.parse(authData)
          const token = parsed.access_token
          
          if (token && navigator.sendBeacon) {
            // Utiliser l'endpoint heartbeat existant pour signaler la fermeture
            const url = `${process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app'}/v1/auth/heartbeat`
            
            // Inclure le token dans l'URL pour sendBeacon
            const urlWithToken = `${url}?token=${encodeURIComponent(token)}`
            const data = JSON.stringify({ 
              logout_type: 'browser_close',
              timestamp: new Date().toISOString()
            })
            
            navigator.sendBeacon(urlWithToken, new Blob([data], {
              type: 'application/json'
            }))
            
            console.log('[AuthProvider] Signal de fermeture envoyé via beacon')
          }
        } catch (error) {
          console.warn('[AuthProvider] Erreur envoi beacon:', error)
        }
      }
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        // Page cachée, potentiellement fermée
        handleBeforeUnload({} as BeforeUnloadEvent)
      }
    }

    // Écouter les événements de fermeture
    window.addEventListener('beforeunload', handleBeforeUnload)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [isAuthenticated])

  // Debug: Afficher les informations de session en développement
  useEffect(() => {
    if (process.env.NODE_ENV === 'development' && isAuthenticated) {
      const { sessionStart, lastHeartbeat } = useAuthStore.getState()
      
      if (sessionStart) {
        const sessionDuration = (Date.now() - sessionStart.getTime()) / 1000
        console.log(`[AuthProvider] Session active depuis ${Math.round(sessionDuration)}s`)
        
        if (lastHeartbeat) {
          const timeSinceHeartbeat = (Date.now() - lastHeartbeat) / 1000
          console.log(`[AuthProvider] Dernier heartbeat il y a ${Math.round(timeSinceHeartbeat)}s`)
        }
      }
    }
  }, [isAuthenticated])

  return <>{children}</>
}