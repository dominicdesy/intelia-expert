// middleware.ts - Version corrigée utilisant votre approche existante + corrections pour déconnexion

import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function middleware(req: NextRequest) {
  const res = NextResponse.next()
  
  try {
    const supabase = createMiddlewareClient({ req, res })
    const { data: { session } } = await supabase.auth.getSession()

    console.log('🔄 [Middleware] Vérification:', {
      path: req.nextUrl.pathname,
      hasSession: !!session,
      userAgent: req.headers.get('user-agent')?.substring(0, 50)
    })

    const { pathname } = req.nextUrl

    // 🚨 GESTION SPÉCIALE POUR DÉCONNEXION - NOUVELLE CORRECTION
    if (pathname === '/auth/logout') {
      console.log('🚪 [Middleware] Route logout détectée - nettoyage forcé')
      
      // Créer une réponse de redirection vers login
      const loginUrl = new URL('/auth/login', req.url)
      loginUrl.searchParams.set('auth', 'logout')
      const logoutResponse = NextResponse.redirect(loginUrl)
      
      // Nettoyer tous les cookies d'auth dans la réponse
      const cookiesToClear = [
        'supabase-auth-token',
        'supabase.auth.token', 
        'sb-access-token',
        'sb-refresh-token',
        // Cookies de votre ancienne approche
        'sb-localhost-auth-token',
        'sb-' + process.env.NEXT_PUBLIC_SUPABASE_URL?.split('//')[1]?.split('.')[0] + '-auth-token'
      ]
      
      cookiesToClear.forEach(cookieName => {
        logoutResponse.cookies.delete(cookieName)
        // Aussi marquer comme expiré
        logoutResponse.cookies.set(cookieName, '', { 
          expires: new Date(0),
          path: '/',
          domain: req.nextUrl.hostname
        })
      })
      
      console.log('✅ [Middleware] Redirection logout avec nettoyage cookies')
      return logoutResponse
    }

    // Routes publiques (conservé de votre logique)
    const publicRoutes = [
      '/auth/login',
      '/auth/signup', 
      '/auth/forgot-password',
      '/auth/reset-password',
      '/auth/confirm',
      '/privacy',
      '/terms',
      '/',  // Page d'accueil publique
      '/_next',
      '/favicon.ico',
      '/images',
      '/icons'
    ]

    const isPublicRoute = publicRoutes.some(route => 
      pathname.startsWith(route) || pathname === route
    )

    // Si route publique, appliquer les headers de sécurité et continuer
    if (isPublicRoute) {
      const secureResponse = applySecurityHeaders(res)
      return secureResponse
    }

    // Routes protégées (conservé de votre logique)
    const protectedPaths = ['/chat', '/profile', '/settings', '/admin']
    const isProtectedPath = protectedPaths.some(path => 
      pathname.startsWith(path)
    )

    // ✅ CORRECTION PRINCIPALE: Redirection PROPRE sans paramètres indésirables
    if (isProtectedPath && !session) {
      console.log('🚫 [Middleware] Accès refusé à route protégée:', pathname)
      console.log('🏠 [Middleware] Redirection vers accueil SANS paramètres')
      
      // ✅ REDIRECTION PROPRE vers l'accueil (conservé de votre logique)
      const homeUrl = new URL('/', req.url)
      return NextResponse.redirect(homeUrl)
    }

    // ✅ ÉVITER LES REDIRECTIONS INUTILES pour les utilisateurs connectés
    if (pathname === '/' && session) {
      console.log('✅ [Middleware] Utilisateur connecté sur accueil - Pas de redirection forcée')
      // Laisser l'utilisateur sur la page d'accueil, ne pas forcer vers /chat
    }

    // Headers de sécurité conservés pour Zoho SalesIQ
    const secureResponse = applySecurityHeaders(res)
    return secureResponse

  } catch (error) {
    console.error('❌ [Middleware] Erreur:', error)
    return NextResponse.next()
  }
}

// Fonction pour appliquer vos headers de sécurité existants (conservée intégralement)
function applySecurityHeaders(response: NextResponse): NextResponse {
  const cspHeader = [
    "default-src 'self'",
    // ✅ SCRIPT-SRC CORRIGÉ pour autoriser Zoho SalesIQ (conservé)
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://salesiq.zohopublic.com https://*.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
    // ✅ STYLE-SRC CORRIGÉ pour autoriser Zoho SalesIQ (conservé)
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://salesiq.zohopublic.com https://*.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
    "font-src 'self' https://fonts.gstatic.com https://*.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
    // ✅ IMG-SRC CORRIGÉ pour autoriser Zoho SalesIQ (conservé)
    "img-src 'self' data: https: blob: https://salesiq.zohopublic.com https://*.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
    // ✅ CONNECT-SRC CORRIGÉ - URL WEBSOCKET CONSERVÉE (conservé)
    "connect-src 'self' https://*.supabase.co https://expert-app-cngws.ondigitalocean.app https://salesiq.zohopublic.com https://*.zoho.com wss://*.zoho.com wss://vts.zohopublic.com wss://salesiq.zohopublic.com https://*.zohostatic.com",
    // ✅ FRAME-SRC CONSERVÉ pour autoriser les iframes Zoho (conservé)
    "frame-src 'self' https://salesiq.zohopublic.com https://*.zoho.com",
    // ✅ CHILD-SRC CONSERVÉ pour autoriser les pop-ups Zoho (conservé)
    "child-src 'self' https://salesiq.zohopublic.com https://*.zoho.com",
    // ✅ WORKER-SRC CONSERVÉ pour les service workers (conservé)
    "worker-src 'self' blob:",
    "media-src 'self' https://*.zoho.com",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "upgrade-insecure-requests"ohostatic.com https://*.zohocdn.com",
    "font-src 'self' https://fonts.gstatic.com https://*.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
    // ✅ IMG-SRC CORRIGÉ pour autoriser Zoho SalesIQ (conservé)
    "img-src 'self' data: https: blob: https://salesiq.zohopublic.com https://*.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
    // ✅ CONNECT-SRC CORRIGÉ - URL WEBSOCKET CONSERVÉE (conservé)
    "connect-src 'self' https://*.supabase.co https://expert-app-cngws.ondigitalocean.app https://salesiq.zohopublic.com https://*.zoho.com wss://*.zoho.com wss://vts.zohopublic.com wss://salesiq.zohopublic.com https://*.zohostatic.com",
    // ✅ FRAME-SRC CONSERVÉ pour autoriser les iframes Zoho (conservé)
    "frame-src 'self' https://salesiq.zohopublic.com https://*.zoho.com",
    // ✅ CHILD-SRC CONSERVÉ pour autoriser les pop-ups Zoho (conservé)
    "child-src 'self' https://salesiq.zohopublic.com https://*.zoho.com",
    // ✅ WORKER-SRC CONSERVÉ pour les service workers (conservé)
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
}ohostatic.com https://*.zohocdn.com",
    "font-src 'self' https://fonts.gstatic.com https://*.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
    // ✅ IMG-SRC CORRIGÉ pour autoriser Zoho SalesIQ (conservé)
    "img-src 'self' data: https: blob: https://salesiq.zohopublic.com https://*.zoho.com https://*.zohostatic.com https://*.zohocdn.com",
    // ✅ CONNECT-SRC CORRIGÉ - URL WEBSOCKET CONSERVÉE (conservé)
    "connect-src 'self' https://*.supabase.co https://expert-app-cngws.ondigitalocean.app https://salesiq.zohopublic.com https://*.zoho.com wss://*.zoho.com wss://vts.zohopublic.com wss://salesiq.zohopublic.com https://*.zohostatic.com",
    // ✅ FRAME-SRC CONSERVÉ pour autoriser les iframes Zoho (conservé)
    "frame-src 'self' https://salesiq.zohopublic.com https://*.zoho.com",
    // ✅ CHILD-SRC CONSERVÉ pour autoriser les pop-ups Zoho (conservé)
    "child-src 'self' https://salesiq.zohopublic.com https://*.zoho.com",
    // ✅ WORKER-SRC CONSERVÉ pour les service workers (conservé)
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