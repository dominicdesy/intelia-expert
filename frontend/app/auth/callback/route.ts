// app/auth/callback/route.ts - Route de callback pour Supabase
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
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
      const supabase = createRouteHandlerClient({ cookies })
      
      // Échanger le code contre une session
      const { data, error: sessionError } = await supabase.auth.exchangeCodeForSession(code)
      
      if (sessionError) {
        console.error('❌ [Auth Callback] Erreur échange code:', sessionError)
        return NextResponse.redirect(new URL(`/auth/login?error=${encodeURIComponent(sessionError.message)}`, request.url))
      }

      if (data.session && data.user) {
        console.log('✅ [Auth Callback] Session créée pour:', data.user.email)
        
        // 🆕 NOUVEAU: Créer/mettre à jour le profil utilisateur si nécessaire
        try {
          const { data: existingProfile } = await supabase
            .from('users')
            .select('*')
            .eq('auth_user_id', data.user.id)
            .single()

          if (!existingProfile) {
            console.log('🆕 [Auth Callback] Création profil utilisateur')
            const { error: profileError } = await supabase
              .from('users')
              .insert({
                auth_user_id: data.user.id,
                email: data.user.email,
                full_name: data.user.user_metadata?.full_name || data.user.email?.split('@')[0] || 'Utilisateur',
                user_type: 'producer',
                language: 'fr',
              })

            if (profileError) {
              console.warn('⚠️ [Auth Callback] Erreur création profil:', profileError)
            } else {
              console.log('✅ [Auth Callback] Profil utilisateur créé')
            }
          } else {
            console.log('✅ [Auth Callback] Profil utilisateur existe déjà')
          }
        } catch (profileError) {
          console.warn('⚠️ [Auth Callback] Erreur gestion profil:', profileError)
          // Ne pas faire échouer l'authentification pour une erreur de profil
        }

        // Rediriger vers le chat
        return NextResponse.redirect(new URL('/chat', request.url))
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