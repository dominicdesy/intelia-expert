// useAuthStore.ts — rewrite (Zustand + Supabase v2)
// -------------------------------------------------
// ✅ Déduplication en vol des appels /v1/auth/me
// ✅ TTL 60s pour éviter les rafales
// ✅ Filtrage des events onAuthStateChange (no-op ignorés)
// ✅ Garde de concurrence pour loadUser()
// ✅ Nettoyage sûr au logout
// ⚠️ Ajuster l'import du client Supabase selon votre projet

import { create } from 'zustand';
import type { Session } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase'; // <— adapte ce chemin si besoin

// ======================
// Types & constantes
// ======================

export type User = {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  phone?: string;
  country?: string;
  linkedinProfile?: string;
  companyName?: string;
  companyWebsite?: string;
  linkedinCorporate?: string;
  user_type?: string; // super_admin, admin, producer, etc.
  language?: string;
  created_at?: string;
  plan?: 'essential' | 'pro' | 'enterprise';
  name?: string;
};

type BackendProfile = { user_type?: string } | null;

type AuthState = {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isLoggingOut: boolean;
  initialized: boolean;

  // Actions
  init: () => Promise<void>;
  reload: () => Promise<void>;
  logout: () => Promise<void>;
};

// Endpoint backend (conforme aux logs DigitalOcean)
const BACKEND_ME_URL = '/v1/auth/me';

// TTL du cache /v1/auth/me
const ME_TTL_MS = 60_000;

// ======================
// Caches & verrous module-scoped
// ======================

let meCache: { value: BackendProfile; userId?: string; ts: number } = {
  value: null,
  userId: undefined,
  ts: 0,
};

let meInFlight: Promise<BackendProfile> | null = null;
let loadUserInFlight: Promise<void> | null = null;
let initStarted = false;

// Dernière session connue (pour ignorer les no-ops d'events)
let lastSessionRef: { uid?: string; token?: string } = {};

// Subscription onAuthStateChange (une seule fois)
let authSubscription: { unsubscribe: () => void } | null = null;

// ======================
// Helpers
// ======================

function safeGet<T>(obj: any, path: string, fallback?: T): T | undefined {
  try {
    return path.split('.').reduce<any>((o, k) => (o ? o[k] : undefined), obj) ?? fallback;
  } catch {
    return fallback;
  }
}

function normalizeUser(session: Session, backendProfile: BackendProfile): User {
  const meta = session.user?.user_metadata || {};
  const fn = (meta.first_name || meta.firstName || '').toString();
  const ln = (meta.last_name || meta.lastName || '').toString();

  const name =
    `${fn} ${ln}`.trim() ||
    (session.user?.email?.split?.('@')?.[0] ?? '') ||
    undefined;

  return {
    id: session.user.id,
    email: session.user.email || '',
    firstName: fn || undefined,
    lastName: ln || undefined,
    phone: meta.phone || undefined,
    country: meta.country || undefined,
    linkedinProfile: meta.linkedin_profile || undefined,
    companyName: meta.company_name || undefined,
    companyWebsite: meta.company_website || undefined,
    linkedinCorporate: meta.linkedin_corporate || undefined,
    // priorité backend → corrige les cas super_admin
    user_type:
      (backendProfile?.user_type as string | undefined) ||
      (meta.role as string | undefined) ||
      'producer',
    language: meta.language || 'fr',
    created_at: session.user.created_at || undefined,
    plan: 'essential',
    name,
  };
}

/**
 * GET /v1/auth/me — dédupliqué + TTL
 */
async function fetchBackendProfile(session: Session): Promise<BackendProfile> {
  const token = session?.access_token;
  const userId = session?.user?.id;

  if (!token || !userId) {
    console.warn('⚠️ fetchBackendProfile: token ou userId manquant');
    return null;
  }

  const now = Date.now();

  // TTL cache
  if (meCache.value && meCache.userId === userId && now - meCache.ts < ME_TTL_MS) {
    return meCache.value;
  }

  // Déduplication des requêtes en vol
  if (meInFlight) return meInFlight;

  meInFlight = fetch(BACKEND_ME_URL, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  })
    .then(async (res) => {
      if (!res.ok) throw new Error(`GET ${BACKEND_ME_URL} → ${res.status}`);
      const data = await res.json();
      // Normalisation minimale (le backend peut renvoyer role/user_type)
      const profile: BackendProfile = {
        user_type: (data?.user_type as string | undefined) || (data?.role as string | undefined),
      };
      meCache = { value: profile, userId, ts: Date.now() };
      return profile;
    })
    .catch((err) => {
      console.warn('⚠️ Profil backend indisponible :', err);
      return null;
    })
    .finally(() => {
      meInFlight = null;
    });

  return meInFlight;
}

/**
 * Compare session courante vs dernière connue (uid + token).
 * Renvoie true si changement réel.
 */
function hasSessionChanged(session: Session | null): boolean {
  const uid = session?.user?.id;
  const tok = session?.access_token;
  const changed = uid !== lastSessionRef.uid || tok !== lastSessionRef.token;
  if (changed) {
    lastSessionRef = { uid, token: tok };
  }
  return changed;
}

// ======================
// Store Zustand
// ======================

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  isLoggingOut: false,
  initialized: false,

  /**
   * init(): lance le chargement initial + souscrit aux events auth (une seule fois)
   */
  init: async () => {
    if (initStarted) return;
    initStarted = true;

    await get().reload();

    // Abonnement unique aux events d'auth
    if (!authSubscription) {
      const { data } = supabase.auth.onAuthStateChange(async (event, session) => {
        // En cas de logout en cours, on ignore
        if (get().isLoggingOut) {
          // debug: console.log('[Auth] Ignoré car logout en cours:', event);
          return;
        }

        // Gestion explicite du SIGNED_OUT
        if (event === 'SIGNED_OUT') {
          // Clear immédiat
          meCache = { value: null, userId: undefined, ts: 0 };
          set({ user: null, isAuthenticated: false, isLoading: false });
          // Reset last session ref
          lastSessionRef = { uid: undefined, token: undefined };
          return;
        }

        // Pour les autres events: on recharge seulement si la session a VRAIMENT changé
        if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED' || event === 'USER_UPDATED') {
          if (hasSessionChanged(session || null)) {
            await get().reload();
          }
          return;
        }
      });

      authSubscription = data.subscription;
    }

    set({ initialized: true });
  },

  /**
   * reload(): charge la session courante et met à jour l'état
   * Protégé contre les appels concurrents.
   */
  reload: async () => {
    // Déduplication des rechargements concurrents
    if (loadUserInFlight) return loadUserInFlight;

    const run = (async () => {
      try {
        set({ isLoading: true });

        const { data, error } = await supabase.auth.getSession();
        if (error) {
          console.error('❌ supabase.auth.getSession error:', error);
          set({ user: null, isAuthenticated: false, isLoading: false });
          return;
        }

        const session = data.session;
        if (!session?.user) {
          // Pas de session → pas d’appel backend
          meCache = { value: null, userId: undefined, ts: 0 };
          lastSessionRef = { uid: undefined, token: undefined };
          set({ user: null, isAuthenticated: false, isLoading: false });
          return;
        }

        // Dédupliqué + TTL
        const backendProfile = await fetchBackendProfile(session);
        const normalized = normalizeUser(session, backendProfile);

        set({
          user: normalized,
          isAuthenticated: true,
          isLoading: false,
        });
      } catch (e) {
        console.error('❌ reload() exception:', e);
        set({ user: null, isAuthenticated: false, isLoading: false });
      }
    })();

    loadUserInFlight = run;
    await run;
    loadUserInFlight = null;
  },

  /**
   * logout(): déconnexion sûre + nettoyage des caches
   */
  logout: async () => {
    // Empêche les effets en parallèle pendant le signOut
    set({ isLoggingOut: true, isLoading: true });

    try {
      await supabase.auth.signOut();
    } catch (e) {
      console.error('❌ supabase.auth.signOut error:', e);
    } finally {
      // Nettoyage local
      meCache = { value: null, userId: undefined, ts: 0 };
      lastSessionRef = { uid: undefined, token: undefined };

      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        isLoggingOut: false,
      });
    }
  },
}));

// ======================
// Auto-init optionnel
// ======================
// Si vous préférez initier depuis votre App (recommandé):
//   useEffect(() => { useAuthStore.getState().init(); }, []);
// Sinon, décommentez les 2 lignes ci-dessous pour auto-init
// setTimeout(() => {
//   useAuthStore.getState().init().catch(console.error);
// }, 0);
