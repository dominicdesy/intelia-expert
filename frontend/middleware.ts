// middleware.ts - VERSION TEMPORAIRE POUR TESTS
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function middleware(req: NextRequest) {
  const res = NextResponse.next()
  
  try {
    const supabase = createMiddlewareClient({ req, res })
    const { data: { session } } = await supabase.auth.getSession()

    // Routes protégées
    const protectedPaths = ['/chat', '/profile', '/settings', '/admin']
    const isProtectedPath = protectedPaths.some(path => 
      req.nextUrl.pathname.startsWith(path)
    )

    // Redirection UNIQUEMENT si pas authentifié sur route protégée
    if (isProtectedPath && !session) {
      console.log('🚫 Accès refusé - Redirection vers login')
      const redirectUrl = new URL('/', req.url)
      redirectUrl.searchParams.set('redirect', req.nextUrl.pathname)
      redirectUrl.searchParams.set('message', 'login_required')
      return NextResponse.redirect(redirectUrl)
    }

    // COMMENTÉ TEMPORAIREMENT - Pas de redirection auto vers chat
    /*
    if (req.nextUrl.pathname === '/' && session && !req.nextUrl.searchParams.has('redirect')) {
      console.log('✅ Utilisateur connecté - Redirection vers chat')
      return NextResponse.redirect(new URL('/chat', req.url))
    }
    */

    // Headers de sécurité
    const response = NextResponse.next()
    
    const cspHeader = [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com",
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      "font-src 'self' https://fonts.gstatic.com",
      "img-src 'self' data: https: blob:",
      `connect-src 'self' https://*.supabase.co https://expert-app-cngws.ondigitalocean.app`,
      "media-src 'self'",
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

  } catch (error) {
    console.error('❌ Erreur middleware:', error)
    return NextResponse.next()
  }
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|images|icons|.*\\.png$|.*\\.jpg$|.*\\.svg$|.*\\.ico$).*)',
  ],
}