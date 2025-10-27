/**
 * Client
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
"use client";

import { getSupabaseClient, resetSupabaseClient } from "./singleton";

// ✅ Exporte le client basé sur createClientComponentClient (PKCE OK)
export const supabase = getSupabaseClient();

// Optionnel: si tu veux forcer un reset du singleton
export const resetClient = () => resetSupabaseClient();

export default supabase;
