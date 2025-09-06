// lib/supabase/singleton.ts
'use client'

import { createClient, SupabaseClient } from '@supabase/supabase-js'
import type { Database } from '@/types/supabase'

// Configuration environnement
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// Validation des variables d'environnement
if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  throw new Error('❌ Variables Supabase manquantes: NEXT_PUBLIC_SUPABASE_URL et NEXT_PUBLIC_SUPABASE_ANON_KEY requises')
}

// ✅ SINGLETON: Une seule instance globale
let supabaseInstance: SupabaseClient<Database> | null = null

/**
 * 🎯 SINGLETON SUPABASE CLIENT
 * Garantit qu'une seule instance GoTrueClient existe dans toute l'application
 */
export const getSupabaseClient = (): SupabaseClient<Database> => {
  // Si l'instance n'existe pas encore, la créer
  if (!supabaseInstance) {
    console.log('🚀 [Supabase] Création instance singleton')
    
    supabaseInstance = createClient<Database>(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: {
        // Configuration auth optimisée
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        flowType: 'pkce', // Plus sécurisé
        storage: typeof window !== 'undefined' ? window.localStorage : undefined,
        storageKey: 'intelia-expert-auth', // Clé unique pour éviter les conflits
      },
      global: {
        headers: {
          'X-Client-Info': 'intelia-expert-app',
        },
      },
      realtime: {
        params: {
          eventsPerSecond: 10, // Limite les événements
        },
      },
    })

    // Log pour debug
    console.log('✅ [Supabase] Instance singleton créée avec succès')
  } else {
    console.log('♻️ [Supabase] Réutilisation instance singleton existante')
  }

  return supabaseInstance
}

/**
 * 🔄 RESET SINGLETON (pour tests ou logout complet)
 */
export const resetSupabaseClient = (): void => {
  console.log('🗑️ [Supabase] Reset instance singleton')
  supabaseInstance = null
}

/**
 * 🎯 EXPORT PAR DÉFAUT : Instance singleton
 */
export const supabase = getSupabaseClient()

// Alias pour compatibilité
export default supabase