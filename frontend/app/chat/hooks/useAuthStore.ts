'use client';

// useAuthStore.ts — Zustand + Supabase (final, relative import to /frontend/supabase.ts)
// - Dedup in-flight /v1/auth/me calls
// - TTL 60s cache
// - Filter onAuthStateChange events (reload only when uid/token changed)
// - Concurrency guard for reload()
// - Safe logout with cache cleanup

import { create } from 'zustand';
import type { Session } from '@supabase/supabase-js';

// ⬇️ Your Supabase client is at the root of /frontend → import it relatively
import { supabase } from '../../../supabase';
// If your file instead has a default export, use this line and remove the one above:
// import supabase from '../../../supabase';

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

  init: () => Promise<void>;
  reload: () => Promise<void>;
  logout: () => Promise<void>;
};

const BACKEND_ME_URL = '/v1/auth/me';
const ME_TTL_MS = 60_000;

// Module-scoped caches/locks
let meCache: { value: BackendProfile; userId?: string; ts: number } = {
  value: null,
  userId: undefined,
  ts: 0,
};
let meInFlight: Promise<BackendProfile> | null = null;
let loadUserInFlight: Promise<void> | null = null;
let initStarted = false;

let lastSessionRef: { uid?: string; token?: string } = {};
let authSubscription: { unsubscribe: () => void } | null = null;

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

async function fetchBackendProfile(session: Session): Promise<BackendProfile> {
  const token = session?.access_token;
  const userId = session?.user?.id;

  if (!token || !userId) {
    console.warn('⚠️ fetchBackendProfile: token ou userId manquant');
    return null;
  }

  const now = Date.now();
  if (meCache.value && meCache.userId === userId && now - meCache.ts < ME_TTL_MS) {
    return meCache.value;
  }
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

function hasSessionChanged(session: Session | null): boolean {
  const uid = session?.user?.id;
  const tok = session?.access_token;
  const changed = uid !== lastSessionRef.uid || tok !== lastSessionRef.token;
  if (changed) lastSessionRef = { uid, token: tok };
  return changed;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  isLoggingOut: false,
  initialized: false,

  init: async () => {
    if (initStarted) return;
    initStarted = true;

    await get().reload();

    if (!authSubscription) {
      const { data } = supabase.auth.onAuthStateChange(async (event, session) => {
        if (get().isLoggingOut) return;

        if (event === 'SIGNED_OUT') {
          meCache = { value: null, userId: undefined, ts: 0 };
          set({ user: null, isAuthenticated: false, isLoading: false });
          lastSessionRef = { uid: undefined, token: undefined };
          return;
        }

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

  reload: async () => {
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
          meCache = { value: null, userId: undefined, ts: 0 };
          lastSessionRef = { uid: undefined, token: undefined };
          set({ user: null, isAuthenticated: false, isLoading: false });
          return;
        }

        const backendProfile = await fetchBackendProfile(session);
        const normalized = normalizeUser(session, backendProfile);

        set({ user: normalized, isAuthenticated: true, isLoading: false });
      } catch (e) {
        console.error('❌ reload() exception:', e);
        set({ user: null, isAuthenticated: false, isLoading: false });
      }
    })();

    loadUserInFlight = run;
    await run;
    loadUserInFlight = null;
  },

  logout: async () => {
    set({ isLoggingOut: true, isLoading: true });
    try {
      await supabase.auth.signOut();
    } catch (e) {
      console.error('❌ supabase.auth.signOut error:', e);
    } finally {
      meCache = { value: null, userId: undefined, ts: 0 };
      lastSessionRef = { uid: undefined, token: undefined };
      set({ user: null, isAuthenticated: false, isLoading: false, isLoggingOut: false });
    }
  },
}));

// (Optional) Call useAuthStore.getState().init() once from your root layout/page.
