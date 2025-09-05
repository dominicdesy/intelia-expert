// app/auth/callback/route.ts - Route de callback pour OAuth avec redirection simplifiée
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const error = requestUrl.searchParams.get('error')
  const error_description = requestUrl.searchParams.get('error_description')

  console.log('🔄 [Auth Callback] Code:', !!code, 'Error:', error)

  if (error) {
    console.error('❌ [Auth Callback] Erreur d\'authentification:', error, error_description)
    // Rediriger vers la page de login avec l'erreur
    return NextResponse.redirect(new URL(`/auth/login?error=${encodeURIComponent(error_description || error)}`, request.url))
  }

  if (code) {
    // ✅ NOUVEAU: Redirection directe vers chat avec paramètre OAuth
    console.log('🔄 [Auth Callback] Redirection directe vers chat avec OAuth...')
    return NextResponse.redirect(new URL('/chat?oauth_complete=true', request.url))
  }

  // Fallback: rediriger vers login
  console.warn('⚠️ [Auth Callback] Pas de code reçu, redirection vers login')
  return NextResponse.redirect(new URL('/auth/login', request.url))
}