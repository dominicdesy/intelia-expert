// app/auth/callback/route.ts - ROUTE DE CALLBACK SUPABASE CORRIGÉE

import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
import { NextResponse, type NextRequest } from 'next/server'

/**
 * ✅ ROUTE DE CALLBACK SUPABASE CORRIGÉE
 * Objectif: Éviter les redirections avec paramètres indésirables
 * Résultat: Redirection propre vers https://expert.intelia.com/
 */
export async function GET(request: NextRequest) {
  console.log('🔗 [Auth Callback] Traitement callback authentification')
  
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const error = requestUrl.searchParams.get('error')
  const errorDescription = requestUrl.searchParams.get('error_description')
  
  console.log('📍 [Auth Callback] Paramètres reçus:', {
    code: !!code,
    error: error,
    errorDescription: errorDescription,
    origin: requestUrl.origin,
    pathname: requestUrl.pathname
  })
  
  // ✅ GESTION D'ERREUR D'AUTHENTIFICATION
  if (error) {
    console.error('❌ [Auth Callback] Erreur authentification:', error, errorDescription)
    
    // ✅ Redirection vers l'accueil SANS paramètres problématiques
    const homeUrl = new URL(requestUrl.origin)
    console.log('🏠 [Auth Callback] Redirection erreur vers:', homeUrl.toString())
    
    return NextResponse.redirect(homeUrl)
  }
  
  // ✅ TRAITEMENT DU CODE D'AUTHENTIFICATION
  if (code) {
    console.log('🔐 [Auth Callback] Code d\'authentification reçu, échange en cours...')
    
    try {
      const supabase = createRouteHandlerClient({ cookies })
      
      // Échanger le code contre une session
      const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
      
      if (exchangeError) {
        console.error('❌ [Auth Callback] Erreur échange code:', exchangeError)
        
        // ✅ Même en cas d'erreur, redirection propre
        const homeUrl = new URL(requestUrl.origin)
        console.log('🏠 [Auth Callback] Redirection après erreur échange:', homeUrl.toString())
        
        return NextResponse.redirect(homeUrl)
      }
      
      if (data?.session?.user) {
        console.log('✅ [Auth Callback] Session créée avec succès pour:', data.session.user.email)
        
        // ✅ REDIRECTION PROPRE VERS L'ACCUEIL (SANS PARAMÈTRES)
        const homeUrl = new URL(requestUrl.origin)
        console.log('🏠 [Auth Callback] Redirection succès vers:', homeUrl.toString())
        
        return NextResponse.redirect(homeUrl)
      } else {
        console.warn('⚠️ [Auth Callback] Session créée mais pas d\'utilisateur')
        
        const homeUrl = new URL(requestUrl.origin)
        return NextResponse.redirect(homeUrl)
      }
      
    } catch (error) {
      console.error('❌ [Auth Callback] Erreur critique échange:', error)
      
      const homeUrl = new URL(requestUrl.origin)
      return NextResponse.redirect(homeUrl)
    }
  }
  
  // ✅ PAS DE CODE - Redirection vers l'accueil
  console.log('ℹ️ [Auth Callback] Pas de code, redirection vers accueil')
  const homeUrl = new URL(requestUrl.origin)
  
  return NextResponse.redirect(homeUrl)
}