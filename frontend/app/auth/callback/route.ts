// app/auth/callback/route.ts
import { NextResponse, type NextRequest } from 'next/server'
import { cookies } from 'next/headers'
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'

// ⚠️ Hardcode provisoire (on enlèvera ça quand tu voudras repasser aux env vars)
const BASE_URL = 'https://expert.intelia.com' as const

// Autoriser uniquement des chemins internes (ex. /chat, /dashboard)
// pour éviter les redirections ouvertes vers des domaines externes.
function pickSafeInternalPath(nextParam: string | null): string {
  if (!nextParam) return '/chat'
  // autorise seulement un chemin absolu interne: commence par "/" et pas par "//"
  if (nextParam.startsWith('/') && !nextParam.startsWith('//')) {
    return nextParam
  }
  return '/chat'
}

export async function GET(request: NextRequest) {
  const url = new URL(request.url)
  const code = url.searchParams.get('code')
  const providerError = url.searchParams.get('error') // p.ex. access_denied
  const providerErrorDesc = url.searchParams.get('error_description')
  const nextParam = url.searchParams.get('next') // optionnel: /chemin interne

  // Logs minimalistes pour diag (sans PII)
  console.log('[OAuth/Callback] hit', {
    hasCode: !!code,
    providerError,
    hasNext: !!nextParam,
  })

  // Cas: le provider renvoie une erreur (ex. user a annulé sur LinkedIn)
  if (providerError) {
    const msg = `provider_error: ${providerError}${providerErrorDesc ? ` - ${providerErrorDesc}` : ''}`
    const to = new URL(`/?auth=error&message=${encodeURIComponent(msg)}`, BASE_URL)
    return NextResponse.redirect(to, { status: 303 })
  }

  if (!code) {
    const to = new URL('/?auth=error&message=missing_oauth_code', BASE_URL)
    return NextResponse.redirect(to, { status: 303 })
  }

  try {
    const cookieStore = cookies()
    const supabase = createRouteHandlerClient({ cookies: () => cookieStore })

    const { data, error } = await supabase.auth.exchangeCodeForSession(code)
    if (error) {
      console.error('[OAuth/Callback] exchangeCodeForSession error:', error)
      const to = new URL(
        `/?auth=error&message=${encodeURIComponent(`callback_error: ${error.message}`)}`,
        BASE_URL
      )
      return NextResponse.redirect(to, { status: 303 })
    }

    console.log('[OAuth/Callback] session created ✅', { userId: data?.user?.id })

    // Redirection finale (par défaut /chat, ou bien ?next=/chemin-interne)
    const safePath = pickSafeInternalPath(nextParam)
    const to = new URL(safePath, BASE_URL)
    return NextResponse.redirect(to, { status: 303 })
  } catch (e: any) {
    console.error('[OAuth/Callback] unexpected exception:', e)
    const to = new URL(
      `/?auth=error&message=${encodeURIComponent(`callback_error: ${e?.message || e}`)}`,
      BASE_URL
    )
    return NextResponse.redirect(to, { status: 303 })
  }
}
