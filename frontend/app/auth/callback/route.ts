// app/auth/callback/route.ts
import { NextResponse, type NextRequest } from 'next/server'
import { cookies } from 'next/headers'
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'

export async function GET(request: NextRequest) {
  const url = new URL(request.url)
  const code = url.searchParams.get('code')
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://expert.intelia.com'

  // Pas de code → retour login avec message clair
  if (!code) {
    return NextResponse.redirect(new URL('/?auth=error&message=missing_oauth_code', baseUrl))
  }

  try {
    // IMPORTANT: client lié au contexte de la requête (cookies)
    const supabase = createRouteHandlerClient({ cookies })

    // Échange le code OAuth contre une session (dépose les cookies sur expert.intelia.com)
    const { data, error } = await supabase.auth.exchangeCodeForSession(code)

    if (error) {
      const msg = encodeURIComponent(`callback_error: ${error.message || 'unknown'}`)
      return NextResponse.redirect(new URL(`/?auth=error&message=${msg}`, baseUrl))
    }

    // Succès → amenez l’utilisateur là où vous voulez (chat, dashboard, etc.)
    return NextResponse.redirect(new URL('/chat', baseUrl))
  } catch (e: unknown) {
    // Sécurité: sérialisation d'erreur robuste (évite "… is not a function")
    const msg =
      e instanceof Error ? e.message
      : typeof e === 'string' ? e
      : 'unknown_callback_error'
    return NextResponse.redirect(
      new URL(`/?auth=error&message=${encodeURIComponent(`callback_error: ${msg}`)}`, baseUrl)
    )
  }
}
