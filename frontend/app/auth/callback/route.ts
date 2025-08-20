// app/auth/callback/route.ts - Route de callback pour OAuth via backend
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
    try {
      console.log('🔄 [Auth Callback] Échange du code via backend...')
      
      // ✅ NOUVEAU: Appel au backend au lieu de Supabase direct
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'https://expert-app-cngws.ondigitalocean.app/api'}/v1/auth/oauth-callback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: code,
          redirect_url: `${requestUrl.origin}/auth/callback`
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        console.error('❌ [Auth Callback] Erreur échange code:', errorData)
        return NextResponse.redirect(new URL(`/auth/login?error=${encodeURIComponent(errorData.detail || 'Erreur d\'authentification')}`, request.url))
      }

      const data = await response.json()
      console.log('✅ [Auth Callback] Session créée via backend')

      if (data.access_token) {
        // Créer une réponse avec redirection vers le chat
        const redirectResponse = NextResponse.redirect(new URL('/chat', request.url))
        
        // Optionnel: stocker le token dans un cookie sécurisé
        redirectResponse.cookies.set('access_token', data.access_token, {
          httpOnly: true,
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'lax',
          maxAge: 60 * 60 * 24 * 7 // 7 jours
        })

        return redirectResponse
      }
    } catch (error) {
      console.error('❌ [Auth Callback] Erreur inattendue:', error)
      return NextResponse.redirect(new URL(`/auth/login?error=${encodeURIComponent('Erreur d\'authentification')}`, request.url))
    }
  }

  // Fallback: rediriger vers login
  console.warn('⚠️ [Auth Callback] Pas de code reçu, redirection vers login')
  return NextResponse.redirect(new URL('/auth/login', request.url))
}