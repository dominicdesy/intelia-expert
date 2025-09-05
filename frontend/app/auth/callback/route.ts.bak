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
  
  console.log('[Auth Callback] Base URL:', baseUrl)

  if (error) {
    console.error('[Auth Callback] Erreur d\'authentification:', error, error_description)
    return NextResponse.redirect(
      new URL(`/?auth=error&message=${encodeURIComponent(error_description || error)}`, baseUrl)
    )
  }

  if (code) {
    try {
      console.log('[Auth Callback] Début du traitement du code OAuth...')
      
      // Vérifier que getSupabaseClient fonctionne
      console.log('[Auth Callback] Récupération du client Supabase...')
      const supabase = getSupabaseClient()
      
      if (!supabase) {
        throw new Error('Client Supabase non disponible')
      }
      
      console.log('[Auth Callback] Client Supabase récupéré avec succès')
      console.log('[Auth Callback] Début de l\'échange du code OAuth...')
      
      // Échanger le code contre une session
      const exchangeResult = await supabase.auth.exchangeCodeForSession(code)
      
      console.log('[Auth Callback] Échange terminé, résultat:', {
        hasData: !!exchangeResult.data,
        hasUser: !!exchangeResult.data?.user,
        hasSession: !!exchangeResult.data?.session,
        hasError: !!exchangeResult.error
      })
      
      const { data, error: exchangeError } = exchangeResult
      
      if (exchangeError) {
        console.error('[Auth Callback] Erreur échange de code:', {
          message: exchangeError.message,
          name: exchangeError.name,
          status: exchangeError.status
        })
        return NextResponse.redirect(
          new URL(`/?auth=error&message=${encodeURIComponent(`exchange_error: ${exchangeError.message}`)}`, baseUrl)
        )
      }

      if (data?.user && data?.session) {
        console.log('[Auth Callback] Session créée avec succès pour:', {
          email: data.user.email,
          id: data.user.id,
          provider: data.user.app_metadata?.provider
        })
        
        console.log('[Auth Callback] Redirection vers chat...')
        
        // Redirection vers chat avec succès
        return NextResponse.redirect(new URL('/chat?auth=success', baseUrl))
      } else {
        console.error('[Auth Callback] Données manquantes:', {
          hasUser: !!data?.user,
          hasSession: !!data?.session,
          userData: data?.user ? 'present' : 'missing',
          sessionData: data?.session ? 'present' : 'missing'
        })
        return NextResponse.redirect(
          new URL('/?auth=error&message=incomplete_oauth_data', baseUrl)
        )
      }
      
    } catch (error: any) {
      console.error('[Auth Callback] Erreur détaillée dans le catch:', {
        message: error.message,
        name: error.name,
        stack: error.stack,
        toString: error.toString(),
        type: typeof error
      })
      
      // Créer un message d'erreur plus descriptif
      const errorMessage = error.message || error.toString() || 'unknown_callback_error'
      
      return NextResponse.redirect(
        new URL(`/?auth=error&message=${encodeURIComponent(`callback_error: ${errorMessage}`)}`, baseUrl)
      )
    }
  }

  // Fallback: pas de code reçu
  console.warn('[Auth Callback] Pas de code reçu, redirection vers login')
  return NextResponse.redirect(new URL('/?auth=error&message=missing_oauth_code', baseUrl))
}