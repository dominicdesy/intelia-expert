/**
 * VoiceRealtimeProvider
 * =====================
 *
 * Client Component wrapper pour VoiceRealtimeButton
 * Permet d'utiliser le bouton dans un Server Component (layout.tsx)
 *
 * Utilise dynamic import avec ssr:false pour éviter erreur React #310
 */

"use client";

import dynamic from "next/dynamic";

// Import dynamique sans SSR pour éviter hydration mismatch
const VoiceRealtimeButton = dynamic(
  () => import("@/components/VoiceRealtimeButton").then((mod) => mod.VoiceRealtimeButton),
  {
    ssr: false,
    loading: () => null, // Pas de loader pendant import
  }
);

export function VoiceRealtimeProvider() {
  return <VoiceRealtimeButton />;
}
