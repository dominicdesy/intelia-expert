// app/auth/callback/route.ts
import { NextResponse, type NextRequest } from 'next/server'
import { cookies } from 'next/headers'
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'

export async function GET(request: NextRequest) {
  const url = new URL(request.url)
  const code = url.searchParams.get('code')
  const errorParam = url.searchParams.get('error')

  console.log('[OAuth/Callback] hit', {
    hasCode: !!code,
    errorParam,
    href: url.toString(),
  })

  if (!code) {
    console.error('[OAuth/Callback] missing "code" param')
    return NextResponse.redirect(
      'https://expert.intelia.com/?auth=error&message=missing_oauth_code'
    )
  }

  try {
    const cookieStore = cookies()
    const supabase = createRouteHandlerClient({ cookies: () => cookieStore })

    const { data, error } = await supabase.auth.exchangeCodeForSession(code)
    if (error) {
      console.error('[OAuth/Callback] exchangeCodeForSession error:', error)
      return NextResponse.redirect(
        `https://expert.intelia.com/?auth=error&message=${encodeURIComponent(
          `callback_error: ${error.message}`
        )}`
      )
    }

    console.log('[OAuth/Callback] session created ✅', {
      userId: data?.user?.id,
    })

    // 👉 Hardcode redirection vers /chat
    return NextResponse.redirect('https://expert.intelia.com/chat')
  } catch (e: any) {
    console.error('[OAuth/Callback] unexpected exception:', e)
    return NextResponse.redirect(
      `https://expert.intelia.com/?auth=error&message=${encodeURIComponent(
        `callback_error: ${e?.message || e}`
      )}`
    )
  }
}
