// app/auth/callback/route.ts
// Version mise à jour pour l'architecture Backend OAuth
import { NextResponse, type NextRequest } from 'next/server'

const BASE_URL = 'https://expert.intelia.com' as const
const API_BASE_URL = 'https://expert.intelia.com/api' as const

// Autoriser uniquement des chemins internes sécurisés
function pickSafeInternalPath(nextParam: string | null): string {
  if (!nextParam) return '/chat'
  if (nextParam.startsWith('/') && !nextParam.startsWith('//')) {
    return nextParam
  }
  return '/chat'
}

export async function GET(request: NextRequest) {
  const url = new URL(request.url)
  const code = url.searchParams.get('code')
  const state = url.searchParams.get('state')
  const providerError = url.searchParams.get('error')
  const providerErrorDesc = url.searchParams.get('error_description')
  const nextParam = url.searchParams.get('next')

  console.log('[OAuth/Callback] Backend OAuth callback:', {
    hasCode: !!code,
    hasState: !!state,
    providerError,
    hasNext: !!nextParam,
  })

  // Cas: le provider renvoie une erreur (ex. user a annulé sur LinkedIn)
  if (providerError) {
    const msg = `${providerError}${providerErrorDesc ? `: ${providerErrorDesc}` : ''}`
    console.error('[OAuth/Callback] Provider error:', msg)
    const to = new URL(`/?auth=error&message=${encodeURIComponent(msg)}`, BASE_URL)
    return NextResponse.redirect(to, { status: 303 })
  }

  if (!code) {
    console.error('[OAuth/Callback] Missing authorization code')
    const to = new URL('/?auth=error&message=missing_oauth_code', BASE_URL)
    return NextResponse.redirect(to, { status: 303 })
  }

  if (!state) {
    console.error('[OAuth/Callback] Missing OAuth state')
    const to = new URL('/?auth=error&message=missing_oauth_state', BASE_URL)
    return NextResponse.redirect(to, { status: 303 })
  }

  try {
    // Déterminer le provider depuis l'état ou l'URL
    // En général, le provider est stocké côté client, mais on peut l'inférer
    let provider = 'linkedin' // Default, mais on devrait l'obtenir autrement
    
    // Essayer de détecter le provider depuis le referrer ou d'autres indices
    const referer = request.headers.get('referer') || ''
    if (referer.includes('linkedin')) {
      provider = 'linkedin'
    } else if (referer.includes('facebook')) {
      provider = 'facebook'
    }

    console.log('[OAuth/Callback] Detected provider:', provider)

    // Appeler notre backend pour traiter le callback OAuth
    const callbackResponse = await fetch(`${API_BASE_URL}/v1/auth/oauth/callback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        provider,
        code,
        state
      })
    })

    const callbackData = await callbackResponse.json()

    if (!callbackResponse.ok || !callbackData.success) {
      console.error('[OAuth/Callback] Backend callback failed:', callbackData)
      const errorMsg = callbackData.message || `HTTP ${callbackResponse.status}`
      const to = new URL(
        `/?auth=error&message=${encodeURIComponent(`callback_error: ${errorMsg}`)}`,
        BASE_URL
      )
      return NextResponse.redirect(to, { status: 303 })
    }

    console.log('[OAuth/Callback] Backend callback successful')

    // Le backend a retourné un token JWT
    const { token, user } = callbackData
    
    if (!token) {
      console.error('[OAuth/Callback] No token returned from backend')
      const to = new URL('/?auth=error&message=no_token_returned', BASE_URL)
      return NextResponse.redirect(to, { status: 303 })
    }

    // Créer la réponse de redirection avec le token
    const safePath = pickSafeInternalPath(nextParam)
    const redirectUrl = new URL(safePath, BASE_URL)
    
    // Ajouter le token et les infos utilisateur comme paramètres de query temporaires
    // Le frontend les récupérera et les stockera dans localStorage
    redirectUrl.searchParams.set('oauth_token', token)
    redirectUrl.searchParams.set('oauth_success', 'true')
    if (user?.email) {
      redirectUrl.searchParams.set('oauth_email', user.email)
    }
    if (provider) {
      redirectUrl.searchParams.set('oauth_provider', provider)
    }

    console.log('[OAuth/Callback] Redirecting to:', safePath)
    
    return NextResponse.redirect(redirectUrl, { status: 303 })

  } catch (e: any) {
    console.error('[OAuth/Callback] Unexpected exception:', e)
    const to = new URL(
      `/?auth=error&message=${encodeURIComponent(`callback_error: ${e?.message || e}`)}`,
      BASE_URL
    )
    return NextResponse.redirect(to, { status: 303 })
  }
}