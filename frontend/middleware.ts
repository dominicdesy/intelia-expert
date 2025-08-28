// middleware.ts - Version Supabase avec CACHE et PROTECTION BOUCLE

import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// PROTECTION GLOBALE contre les vérifications multiples
const middlewareCache = {
  lastCheck: 0,
  lastSessionState: null as boolean | null,
  lastUserId: null as string | null,
  CACHE_DURATION: 2000, // 2 secondes de cache
  checkCount: 0,
  MAX_CHECKS_PER_MINUTE: 30
}

// Reset du cache périodiquement
setInterval(() => {
  middlewareCache.checkCount = 0
}, 60000) // Reset toutes les minutes

export async function middleware(req: NextRequest) {
  const res = NextResponse.next()
  
  try {
    const now = Date.now()
    const pathname = req.nextUrl.pathname

    // PROTECTION: Limite le nombre de vérifications
    if (middlewareCache.checkCount > middlewareCache.MAX_CHECKS_PER_MINUTE) {
      console.warn('🛡️ [Middleware] Trop de vérifications, utilisation du cache')
      
      // Utiliser le dernier état connu
      if (middlewareCache.lastSessionState === false) {
        const publicRoutes = [
          '/auth/login', '/auth/signup', '/auth/forgot-password',
          '/auth/reset-password', '/auth/confirm', '/auth/callback',
          '/auth/invitation', '/privacy', '/terms', '/',
          '/_next', '/favicon.ico', '/images', '/icons'
        ]
        
        const isPublicRoute = publicRoutes.some(route => 
          pathname.startsWith(route) || pathname === route
        )
        
        if (!isPublicRoute) {
          return NextResponse.redirect(new URL('/', req.url))
        }
      }
      
      return applySecurityHeaders(res)
    }

    // CACHE: Utiliser le cache si récent
    if (now - middlewareCache.lastCheck < middlewareCache.CACHE_DURATION) {
      console.log('⚡ [Middleware] Utilisation du cache - pas de vérification Supabase')
      
      // Appliquer la même logique que si on avait fait la vérification
      if (middlewareCache.lastSessionState === false) {
        const protectedPaths = ['/chat', '/profile', '/settings', '/admin']
        const isProtectedPath = protectedPaths.some(path => pathname.startsWith(path))
        
        if (isProtectedPath) {
          return NextResponse.redirect(new URL('/', req.url))
        }
      }
      
      return applySecurityHeaders(res)
    }

    // Incrémenter le compteur de vérifications
    middlewareCache.checkCount++
    middlewareCache.lastCheck = now

    const supabase = createMiddlewareClient({ req, res })
    const { data: { session } } = await supabase.auth.getSession()

    // Mettre à jour le cache
    middlewareCache.lastSessionState = !!session
    middlewareCache.lastUserId = session?.user?.id || null

    // LOGS RÉDUITS (seulement si changement d'état)
    const sessionChanged = middlewareCache.lastSessionState !== (!!session)
    if (sessionChanged || middlewareCache.checkCount <= 3) {
      console.log('🔄 [Middleware] Vérification Supabase:', {
        path: pathname,
        hasSession: !!session,
        userEmail: session?.user?.email,
        cached: false
      })
    }

    // 🆕 REDIRECTION /welcome → /auth/invitation (NOUVEAU)
    if (pathname === '/welcome' || pathname === '/welcome/') {
      console.log('🔄 [Middleware] Redirection /welcome → /auth/invitation')
      
      const invitationUrl = new URL('/auth/invitation', req.url)
      req.nextUrl.searchParams.forEach((value, key) => {
        invitationUrl.searchParams.set(key, value)
      })
      
      return NextResponse.redirect(invitationUrl)
    }

    // 🚨 GESTION SPÉCIALE POUR DÉCONNEXION - CONSERVÉE
    if (pathname === '/auth/logout') {
      console.log('🚪 [Middleware] Route logout détectée - nettoyage forcé')
      
      await supabase.auth.signOut()
      
      const loginUrl = new URL('/auth/login', req.url)
      loginUrl.searchParams.set('auth', 'logout')
      const logoutResponse = NextResponse.redirect(loginUrl)
      
      const cookiesToClear = [
        'supabase-auth-token',
        'supabase.auth.token', 
        'sb-access-token',
        'sb-refresh-token',
        'sb-' + process.env.NEXT_PUBLIC_SUPABASE_URL?.split('//')[1]?.split('.')[0] + '-auth-token'
      ]
      
      cookiesToClear.forEach(cookieName => {
        logoutResponse.cookies.delete(cookieName)
        logoutResponse.cookies.set(cookieName, '', { 
          expires: new Date(0),
          path: '/',
          domain: req.nextUrl.hostname
        })
      })
      
      // Reset du cache lors du logout
      middlewareCache.lastSessionState = false
      middlewareCache.lastUserId = null
      
      return logoutResponse
    }

    // Routes publiques (conservé)
    const publicRoutes = [
      '/auth/login', '/auth/signup', '/auth/forgot-password',
      '/auth/reset-password', '/auth/confirm', '/auth/callback',
      '/auth/invitation', '/privacy', '/terms', '/',
      '/_next', '/favicon.ico', '/images', '/icons'
    ]

    const isPublicRoute = publicRoutes.some(route => 
      pathname.startsWith(route) || pathname === route
    )

    if (isPublicRoute) {
      return applySecurityHeaders(res)
    }

    // Routes protégées
    const protectedPaths = ['/chat', '/profile', '/settings', '/admin']
    const isProtectedPath = protectedPaths.some(path => pathname.startsWith(path))

    if (isProtectedPath && !session) {
      console.log('🚫 [Middleware] Accès refusé à route protégée:', pathname)
      return NextResponse.redirect(new URL('/', req.url))
    }

    // Éviter les redirections inutiles pour les utilisateurs connectés
    if (pathname === '/' && session) {
      console.log('✅ [Middleware] Utilisateur connecté sur accueil - Pas de redirection forcée')
    }

    // Redirection des pages d'auth vers chat si connecté
    if (pathname.startsWith('/auth/') && session && pathname !== '/auth/callback' && pathname !== '/auth/invitation') {
      console.log('🔄 [Middleware] Utilisateur connecté sur page auth, redirection vers chat')
      return NextResponse.redirect(new URL('/chat', req.url))
    }

    return applySecurityHeaders(res)

  } catch (error) {
    console.error('❌ [Middleware] Erreur Supabase:', error)
    
    // En cas d'erreur, assumer pas de session
    middlewareCache.lastSessionState = false
    middlewareCache.lastUserId = null
    
    return NextResponse.next()
  }
}

// Fonction pour appliquer les headers de sécurité (CONSERVÉE)
function applySecurityHeaders(response: NextResponse): NextResponse {
  const cspHeader = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://salesiq.zohopublic.com https://*.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://salesiq.zohopublic.com https://*.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
    "font-src 'self' https://fonts.gstatic.com https://*.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
    "img-src 'self' data: https: blob: https://salesiq.zohopublic.com https://*.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
    "connect-src 'self' https://*.supabase.co https://expert-app-cngws.ondigitalocean.app https://salesiq.zohopublic.com https://*.zoho.com wss://*.zoho.com wss://vts.zohopublic.com wss://salesiq.zohopublic.com https://*.zohostatic.com https://restcountries.com",
    "frame-src 'self' https://salesiq.zohopublic.com https://*.zoho.com",
    "child-src 'self' https://salesiq.zohopublic.com https://*.zoho.com",
    "worker-src 'self' blob:",
    "media-src 'self' https://*.zoho.com",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "upgrade-insecure-requests"
  ].join('; ')

  response.headers.set('Content-Security-Policy', cspHeader)
  response.headers.set('X-Frame-Options', 'DENY')
  response.headers.set('X-Content-Type-Options', 'nosniff')
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  response.headers.set('X-XSS-Protection', '1; mode=block')
  
  return response
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|images|icons|.*\\.png$|.*\\.jpg$|.*\\.svg$|.*\\.ico$).*)',
  ],
}