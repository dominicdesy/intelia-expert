'use client'

import { getSupabaseClient, resetSupabaseClient } from './singleton'

// ✅ Exporte le client basé sur createClientComponentClient (PKCE OK)
export const supabase = getSupabaseClient()

// Optionnel: si tu veux forcer un reset du singleton
export const resetClient = () => resetSupabaseClient()

export default supabase
