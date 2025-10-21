/**
 * VoiceRealtimeProvider
 * =====================
 *
 * Client Component wrapper pour VoiceRealtimeButton
 * Permet d'utiliser le bouton dans un Server Component (layout.tsx)
 */

"use client";

import { VoiceRealtimeButton } from "@/components/VoiceRealtimeButton";

export function VoiceRealtimeProvider() {
  return <VoiceRealtimeButton />;
}
