// lib/api/config.ts
export const API_CONFIG = {
  // Base URL peut être configurée via env ou détectée automatiquement
  BASE_URL:
    process.env.NEXT_PUBLIC_API_BASE ??
    "/api/v1", // Le backend est accessible via /api/v1 en dev et prod

  ENDPOINTS: {
    STATS_FAST: {
      DASHBOARD: "/stats-fast/dashboard",
      QUESTIONS: "/stats-fast/questions",
      INVITATIONS: "/stats-fast/invitations",
    },
    AUTH: {
      ME: "/auth/me",
      LOGIN: "/auth/login",
    },
  },

  // Configuration dynamique du token cookie
  SUPABASE_COOKIE_NAME:
    process.env.NEXT_PUBLIC_SUPABASE_COOKIE_NAME ??
    "sb-cdrmjshmkdfwwtsfdvbl-auth-token",
};

// Helper pour construire les URLs complètes
export const buildApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

// Raccourcis pour les endpoints stats
export const STATS_ENDPOINTS = {
  DASHBOARD: buildApiUrl(API_CONFIG.ENDPOINTS.STATS_FAST.DASHBOARD),
  QUESTIONS: buildApiUrl(API_CONFIG.ENDPOINTS.STATS_FAST.QUESTIONS),
  INVITATIONS: buildApiUrl(API_CONFIG.ENDPOINTS.STATS_FAST.INVITATIONS),
};
