// app/auth/callback/route.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { getSupabaseClient } from '@/lib/supabase/singleton'

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const error = requestUrl.searchParams.get('error')
  const error_description = requestUrl.searchParams.get('error_description')

  console.log('[Auth Callback] Code:', !!code, 'Error:', error)

  // URL de base pour la redirection
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://expert.intelia.com'

  if (error) {
    console.error('[Auth Callback] Erreur d\'authentification:', error, error_description)
    return NextResponse.redirect(
      new URL(`/?auth=error&message=${encodeURIComponent(error_description || error)}`, baseUrl)
    )
  }

  if (code) {
    try {
      // Utiliser votre client Supabase existant
      const supabase = getSupabaseClient()
      
      console.log('[Auth Callback] Echange du code OAuth...')
      
      // Echanger le code contre une session
      const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
      
      if (exchangeError) {
        console.error('[Auth Callback] Erreur echange de code:', exchangeError)
        return NextResponse.redirect(
          new URL(`/?auth=error&message=${encodeURIComponent(exchangeError.message)}`, baseUrl)
        )
      }

      if (data.user && data.session) {
        console.log('[Auth Callback] Session creee pour:', data.user.email)
        
        // Redirection vers chat avec succes
        return NextResponse.redirect(new URL('/chat?auth=success', baseUrl))
      } else {
        console.error('[Auth Callback] Pas d\'utilisateur ou de session')
        return NextResponse.redirect(
          new URL('/?auth=error&message=no_user_session', baseUrl)
        )
      }
      
    } catch (error: any) {
      console.error('[Auth Callback] Erreur inattendue:', error)
      return NextResponse.redirect(
        new URL(`/?auth=error&message=${encodeURIComponent(error.message || 'oauth_exchange_failed')}`, baseUrl)
      )
    }
  }

  // Fallback: pas de code recu
  console.warn('[Auth Callback] Pas de code recu, redirection vers login')
  return NextResponse.redirect(new URL('/?auth=error&message=missing_code', baseUrl))
}