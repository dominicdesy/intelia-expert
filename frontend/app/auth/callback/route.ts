// app/auth/callback/route.ts - Route de callback pour OAuth avec redirection vers production
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const error = requestUrl.searchParams.get('error')
  const error_description = requestUrl.searchParams.get('error_description')

  console.log('🔄 [Auth Callback] Code:', !!code, 'Error:', error)

  // URL de base pour la redirection (production)
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://expert.intelia.com'

  if (error) {
    console.error('❌ [Auth Callback] Erreur d\'authentification:', error, error_description)
    // Rediriger vers la page de login avec l'erreur
    return NextResponse.redirect(new URL(`/auth/login?error=${encodeURIComponent(error_description || error)}`, baseUrl))
  }

  if (code) {
    // ✅ Conserver tous les paramètres (code, state, etc.)
    console.log('🔄 [Auth Callback] Redirection vers chat avec OAuth...')
    const qs = requestUrl.searchParams.toString()
    const target = qs
      ? new URL(`/chat?oauth_complete=true&${qs}`, baseUrl)
      : new URL('/chat?oauth_complete=true', baseUrl)
    
    return NextResponse.redirect(target)
  }

  // Fallback: rediriger vers login
  console.warn('⚠️ [Auth Callback] Pas de code reçu, redirection vers login')
  return NextResponse.redirect(new URL('/auth/login', baseUrl))