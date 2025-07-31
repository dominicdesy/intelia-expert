// middleware.ts - Version corrigée combinant votre logique existante + corrections pour déconnexion

import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  })

  try {
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          get(name: string) {
            return request.cookies.get(name)?.value
          },
          set(name: string, value: string, options: any) {
            request.cookies.set({
              name,
              value,
              ...options,
            })
            response = NextResponse.next({
              request: {
                headers: request.headers,
              },
            })
            response.cookies.set({
              name,
              value,
              ...options,
            })
          },
          remove(name: string, options: any) {
            request.cookies.set({
              name,
              value: '',
              ...options,
            })
            response = NextResponse.next({
              request: {
                headers: request.headers,
              },
            })
            response.cookies.set({
              name,
              value: '',
              ...options,
            })
          },
        },
      }
    )

    const { pathname } = request.nextUrl
    console.log('🔄 [Middleware] Vérification:', {
      path: pathname,
      userAgent: request.headers.get('user-agent')?.substring(0, 50)
    })

    // 🚨 GESTION SPÉCIALE POUR DÉCONNEXION - PRIORITÉ ABSOLUE
    if (pathname === '/auth/logout') {
      console.log('🚪 [Middleware] Route logout détectée - nettoyage forcé')
      
      // Nettoyer tous les cookies d'auth
      const cookiesToClear = [
        'supabase-auth-token',
        'supabase.auth.token', 
        'sb-access-token',
        'sb-refresh-token'
      ]
      
      cookiesToClear.forEach(cookieName => {
        response.cookies.delete(cookieName)
      })
      
      // Redirection propre vers login
      const loginUrl = new URL('/auth/login', request.url)
      loginUrl.searchParams.set('auth', 'logout')
      return NextResponse.redirect(loginUrl)
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
      // Appliquer vos headers de sécurité existants
      const secureResponse = applySecurityHeaders(response)
      return secureResponse
    }

    // Vérifier l'authentification pour les routes protégées
    const { data: { session }, error } = await supabase.auth.getSession()
    
    // Routes protégées (conservé de votre logique)
    const protectedPaths = ['/chat', '/profile', '/settings', '/admin']
    const isProtectedPath = protectedPaths.some(path => 
      pathname.startsWith(path)
    )

    if (isProtectedPath && (!session || error)) {
      console.log('🚫 [Middleware] Accès refusé à route protégée:', pathname)
      console.log('🏠 [Middleware] Redirection vers accueil SANS paramètres')
      
      // ✅ REDIRECTION PROPRE vers l'accueil (conservé de votre logique)
      const homeUrl = new URL('/', request.url)
      return NextResponse.redirect(homeUrl)
    }

    // ✅ ÉVITER LES REDIRECTIONS INUTILES (conservé de votre logique)
    if (pathname === '/' && session) {
      console.log('✅ [Middleware] Utilisateur connecté sur accueil - Pas de redirection forcée')
    }

    // Appliquer les headers de sécurité et continuer
    const secureResponse = applySecurityHeaders(response)
    return secureResponse

  } catch (middlewareError) {
    console.error('❌ [Middleware] Erreur générale:', middlewareError)
    return response
  }
}

// Fonction pour appliquer vos headers de sécurité existants
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