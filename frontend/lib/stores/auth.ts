// lib/stores/auth.ts - SYSTÈME D'AUTH UNIFIÉ - SUPABASE DIRECT + SESSION TRACKING
// Version avec OAuth direct via auth.intelia.com + tracking temps de connexion + refresh automatique token

"use client";

import React, { useEffect } from "react";
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { apiClient } from "@/lib/api/client";
import type { User as AppUser } from "@/types";
import { secureLog } from "@/lib/utils/secureLogger";

// Interface pour les données utilisateur du backend
interface BackendUserData {
  user_id: string;
  email: string;
  full_name?: string;
  first_name?: string;  // NOUVEAU: champs séparés depuis Supabase
  last_name?: string;   // NOUVEAU: champs séparés depuis Supabase
  phone?: string;
  phone_number?: string;
  country?: string;
  country_code?: string;
  area_code?: string;
  linkedin_profile?: string;
  facebook_profile?: string;
  company_name?: string;
  company_website?: string;
  linkedin_corporate?: string;
  user_type?: string;
  language?: string;
  created_at?: string;
  plan?: string;
  avatar_url?: string;
  consent_given?: boolean;
  consent_date?: string;
  updated_at?: string;
  profile_id?: string;
  preferences?: any;
  is_admin?: boolean;
  production_type?: string[];  // NOUVEAU: User profiling
  category?: string;  // NOUVEAU: User profiling
  category_other?: string;  // NOUVEAU: User profiling
}

// Types d'état du store
interface AuthState {
  user: AppUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  hasHydrated: boolean;
  lastAuthCheck: number;
  authErrors: string[];
  isOAuthLoading: string | null; // Provider en cours de connexion OAuth

  // NOUVEAUX ÉTATS POUR SESSION TRACKING
  sessionStart: Date | null;
  sessionDuration: number;
  lastHeartbeat: number;
  heartbeatInterval: NodeJS.Timeout | null;

  // Actions existantes
  setHasHydrated: (v: boolean) => void;
  handleAuthError: (error: any, ctx?: string) => void;
  clearAuthErrors: () => void;
  checkAuth: () => Promise<void>;
  initializeSession: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    userData: Partial<AppUser>,
  ) => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (data: Partial<AppUser>) => Promise<void>;
  getAuthToken: () => Promise<string | null>;
  updateConsent: (consentGiven: boolean) => Promise<void>;
  exportUserData: () => Promise<any>;
  deleteUserData: () => Promise<void>;

  // ACTIONS OAUTH SUPABASE DIRECT
  loginWithOAuth: (provider: "linkedin" | "facebook") => Promise<void>;
  handleOAuthTokenFromURL: () => Promise<boolean>;

  // NOUVELLES ACTIONS POUR SESSION TRACKING
  startSessionTracking: () => void;
  endSessionTracking: () => Promise<void>;
  sendHeartbeat: () => Promise<void>;

  // NOUVELLE ACTION POUR REFRESH AUTOMATIQUE
  refreshTokenIfNeeded: () => Promise<void>;
}

// Store unifié utilisant Supabase direct + session tracking
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      hasHydrated: false,
      lastAuthCheck: 0,
      authErrors: [],
      isOAuthLoading: null,

      // NOUVEAUX ÉTATS POUR SESSION TRACKING
      sessionStart: null,
      sessionDuration: 0,
      lastHeartbeat: 0,
      heartbeatInterval: null,

      setHasHydrated: (v: boolean) => {
        set({ hasHydrated: v });
      },

      handleAuthError: (error: any, ctx?: string) => {
        const msg = (error?.message || "Authentication error").toString();
        secureLog.error(`[AuthStore] ${ctx || "Error"}`, error);
        set((s) => ({ authErrors: [...s.authErrors, msg] }));
      },

      clearAuthErrors: () => {
        set({ authErrors: [] });
      },

      // NOUVELLES MÉTHODES POUR SESSION TRACKING
      startSessionTracking: () => {
        // Éviter de créer plusieurs intervals
        if (get().heartbeatInterval) return;

        const now = new Date();
        secureLog.log("[AuthStore] Session tracking started");

        // Créer un interval unique qui gère heartbeat ET refresh
        const interval = setInterval(async () => {
          if (!get().isAuthenticated) {
            get().endSessionTracking();
            return;
          }

          try {
            // 1. Heartbeat
            await apiClient.postSecure('/auth/heartbeat');

            // 2. Rafraîchir le token (renouvelle automatiquement les 60 min)
            await get().refreshTokenIfNeeded();

            set({ lastHeartbeat: Date.now() });
          } catch (error) {
            secureLog.error('[SessionTracking] Heartbeat error', error);
          }
        }, 30000); // Toutes les 30 secondes
        
        set({
          sessionStart: now,
          lastHeartbeat: Date.now(),
          heartbeatInterval: interval,
        });
      },

      endSessionTracking: async () => {
        const { sessionStart, heartbeatInterval } = get();
        
        // Nettoyer l'interval si il existe
        if (heartbeatInterval) {
          clearInterval(heartbeatInterval);
        }
        
        if (sessionStart) {
          const duration = (Date.now() - sessionStart.getTime()) / 1000;
          set({
            sessionDuration: duration,
            sessionStart: null,
            lastHeartbeat: 0,
            heartbeatInterval: null,
          });

          secureLog.log(
            `[AuthStore] Session ended - duration: ${Math.round(duration)}s`,
          );

          try {
            const response = await apiClient.postSecure("/auth/logout", {
              reason: "manual",
            });
            if (response.success) {
              secureLog.log("[AuthStore] Logout tracking sent to backend");
            }
          } catch (error) {
            secureLog.warn("[AuthStore] Logout tracking error", error);
          }
        }
      },

      sendHeartbeat: async () => {
        // Cette fonction est maintenant gérée par startSessionTracking
        // On la garde pour compatibilité mais elle ne fait plus rien
        secureLog.log("[AuthStore] sendHeartbeat called (managed by automatic interval)");
      },

      // NOUVELLE FONCTION: REFRESH AUTOMATIQUE DU TOKEN
      refreshTokenIfNeeded: async () => {
        const authData = localStorage.getItem('intelia-expert-auth');
        if (!authData) return;

        try {
          const parsed = JSON.parse(authData);
          const expiresAt = new Date(parsed.expires_at || 0).getTime();
          const now = Date.now();
          const tenMinutes = 10 * 60 * 1000;

          // Si le token expire dans moins de 10 minutes, le rafraîchir
          if (expiresAt - now < tenMinutes) {
            secureLog.log('[AuthStore] Token near expiration, refreshing...');

            const response = await apiClient.postSecure<{
              access_token: string;
              expires_at: string;
              token_type: string;
            }>('/auth/refresh-token');

            if (response.success && response.data) {
              const newAuthData = {
                access_token: response.data.access_token,
                token_type: response.data.token_type || 'bearer',
                expires_at: response.data.expires_at,
                synced_at: Date.now(),
              };

              localStorage.setItem('intelia-expert-auth', JSON.stringify(newAuthData));
              secureLog.log('[AuthStore] Token refreshed successfully');
            }
          }
        } catch (error) {
          secureLog.error('[AuthStore] Token refresh error', error);
        }
      },

      // INITIALIZE SESSION - Méthode modifiée
      initializeSession: async () => {
        secureLog.log("[AuthStore] Session initialization...");

        try {
          // NOUVEAU: Vérifier d'abord s'il y a un token OAuth dans l'URL
          await get().handleOAuthTokenFromURL();

          // Vérifier si un token existe dans localStorage
          const authData = localStorage.getItem("intelia-expert-auth");

          if (authData) {
            // NOUVEAU: Rafraîchir le token si nécessaire avant de vérifier l'auth
            await get().refreshTokenIfNeeded();

            // Si token existe, vérifier l'authentification
            await get().checkAuth();

            // NOUVEAU: Démarrer le tracking de session si authentifié
            if (get().isAuthenticated) {
              get().startSessionTracking();
            }
          } else {
            // Aucun token, utilisateur non authentifié
            set({
              user: null,
              isAuthenticated: false,
              lastAuthCheck: Date.now(),
            });
            secureLog.log(
              "[AuthStore] No token found - session not initialized",
            );
          }
        } catch (error) {
          secureLog.error("[AuthStore] Session initialization error", error);
          get().handleAuthError(error, "initializeSession");

          // En cas d'erreur, reset l'état
          set({
            user: null,
            isAuthenticated: false,
            lastAuthCheck: Date.now(),
          });
        }
      },

      // CHECK AUTH : Utilise /auth/me
      checkAuth: async () => {
        try {
          secureLog.log("[AuthStore] Checking auth via /auth/me");

          // NOUVEAU: Rafraîchir le token si nécessaire avant de vérifier l'auth
          await get().refreshTokenIfNeeded();

          const response =
            await apiClient.getSecure<BackendUserData>("/auth/me");

          if (response.success && response.data) {
            const userData = response.data;

            // Adapter les données backend vers AppUser
            const appUser: AppUser = {
              id: userData.user_id,
              email: userData.email,
              name:
                userData.full_name ||
                userData.email?.split("@")[0] ||
                "Utilisateur",
              // CORRECTION: Utiliser first_name/last_name depuis Supabase si disponibles
              firstName: userData.first_name || userData.full_name?.split(" ")[0] || "",
              lastName: userData.last_name || userData.full_name?.split(" ").slice(1).join(" ") || "",
              phone: userData.phone || userData.phone_number || "",
              country: userData.country || "",
              linkedinProfile: userData.linkedin_profile || "",
              facebookProfile: userData.facebook_profile,
              companyName: userData.company_name || "",
              companyWebsite: userData.company_website || "",
              linkedinCorporate: userData.linkedin_corporate || "",
              user_type: userData.user_type || "producer",
              language: userData.language || "fr",
              created_at: userData.created_at || new Date().toISOString(),
              plan: userData.plan || "essential",
              full_name: userData.full_name,
              avatar_url: userData.avatar_url,
              consent_given: userData.consent_given ?? true,
              consent_date: userData.consent_date,
              updated_at: userData.updated_at,
              user_id: userData.user_id,
              profile_id: userData.profile_id,
              preferences: userData.preferences || {},
              is_admin: userData.is_admin || false,
              production_type: userData.production_type || [],
              category: userData.category || "",
              category_other: userData.category_other || "",
            };

            set({
              user: appUser,
              isAuthenticated: true,
              lastAuthCheck: Date.now(),
              authErrors: [],
            });

            // ✅ SYNC IMMEDIATE: Synchroniser la langue avec localStorage pour i18n
            if (appUser.language) {
              try {
                const langData = {
                  state: {
                    currentLanguage: appUser.language,
                  },
                };
                localStorage.setItem("intelia-language", JSON.stringify(langData));
                secureLog.log(`[AuthStore] Language synchronized to localStorage: ${appUser.language}`);
              } catch (error) {
                secureLog.warn("[AuthStore] Error syncing language to localStorage:", error);
              }
            }

            secureLog.log("[AuthStore] Auth successful");
          } else {
            set({
              user: null,
              isAuthenticated: false,
              lastAuthCheck: Date.now(),
            });
            secureLog.log("[AuthStore] Not authenticated");
          }
        } catch (e: any) {
          secureLog.error("[AuthStore] checkAuth error", e);
          set({
            user: null,
            isAuthenticated: false,
            lastAuthCheck: Date.now(),
          });
        }
      },

      // LOGIN : Utilise /auth/login avec gestion d'erreurs améliorée + session tracking
      login: async (email: string, password: string) => {
        set({ isLoading: true, authErrors: [] });
        secureLog.log("[AuthStore] Login attempt");

        try {
          const response = await apiClient.post<{
            access_token: string;
            expires_at?: string;
          }>("/auth/login", {
            email,
            password,
          });

          if (!response.success) {
            throw new Error(response.error?.message || "Erreur de connexion");
          }

          const { access_token, expires_at } = response.data;

          // Sauvegarder le token dans localStorage
          const authData = {
            access_token,
            expires_at,
            token_type: "bearer",
            synced_at: Date.now(),
          };
          localStorage.setItem("intelia-expert-auth", JSON.stringify(authData));

          // Vérifier l'auth pour récupérer les données utilisateur
          await get().checkAuth();

          // NOUVEAU: Démarrer le tracking de session après login réussi
          if (get().isAuthenticated) {
            get().startSessionTracking();
          }

          set({ isLoading: false });

          // Déclencher l'événement de redirection
          setTimeout(() => {
            window.dispatchEvent(new Event("auth-state-changed"));
          }, 100);

          secureLog.log("[AuthStore] Login successful");
        } catch (e: any) {
          secureLog.error("[AuthStore] Login error", e);
          get().handleAuthError(e, "login");

          // GESTION D'ERREURS AMÉLIORÉE
          let userMessage = "Erreur de connexion";

          // Analyser le code de statut HTTP
          if (e?.status || e?.response?.status) {
            const statusCode = e.status || e.response?.status;
            secureLog.log("[AuthStore] HTTP status code", { statusCode });

            switch (statusCode) {
              case 400:
                userMessage = "Données de connexion invalides";
                break;
              case 401:
                userMessage = "Email ou mot de passe incorrect";
                break;
              case 403:
                userMessage = "Accès refusé";
                break;
              case 404:
                userMessage = "Service de connexion non trouvé";
                break;
              case 429:
                userMessage =
                  "Trop de tentatives de connexion. Veuillez réessayer dans quelques minutes.";
                break;
              case 500:
                userMessage =
                  "Erreur technique du serveur. Veuillez réessayer.";
                break;
              case 502:
              case 503:
              case 504:
                userMessage =
                  "Service temporairement indisponible. Veuillez réessayer.";
                break;
              default:
                userMessage = `Erreur de connexion (Code: ${statusCode})`;
            }
          }
          // Analyser le message d'erreur
          else if (e?.message) {
            const errorMsg = e.message.toLowerCase();
            secureLog.log("[AuthStore] Error message type identified");

            if (
              errorMsg.includes("invalid login credentials") ||
              errorMsg.includes("email ou mot de passe incorrect") ||
              errorMsg.includes("credentials") ||
              errorMsg.includes("password")
            ) {
              userMessage = "Email ou mot de passe incorrect";
            } else if (
              errorMsg.includes("email not confirmed") ||
              errorMsg.includes("email non confirmé") ||
              errorMsg.includes("verify") ||
              errorMsg.includes("confirmer")
            ) {
              userMessage =
                "Veuillez confirmer votre email avant de vous connecter";
            } else if (
              errorMsg.includes("request failed") ||
              errorMsg.includes("network") ||
              errorMsg.includes("fetch")
            ) {
              userMessage =
                "Problème de connexion réseau. Vérifiez votre connexion internet.";
            } else if (
              errorMsg.includes("rate limit") ||
              errorMsg.includes("too many") ||
              errorMsg.includes("trop de tentatives")
            ) {
              userMessage =
                "Trop de tentatives de connexion. Veuillez réessayer dans quelques minutes.";
            } else if (errorMsg.includes("timeout")) {
              userMessage = "Délai de connexion dépassé. Veuillez réessayer.";
            } else if (
              errorMsg.includes("server") ||
              errorMsg.includes("internal") ||
              errorMsg.includes("500")
            ) {
              userMessage =
                "Erreur technique du serveur. Veuillez réessayer ou contactez le support.";
            } else {
              userMessage = e.message;
            }
          }
          // Erreur de format/parsing
          else if (e?.name === "SyntaxError") {
            userMessage = "Erreur de communication avec le serveur";
          }
          // Erreur réseau général
          else if (!navigator.onLine) {
            userMessage = "Pas de connexion internet";
          }

          secureLog.log("[AuthStore] User-friendly error message prepared");

          set({ isLoading: false });
          throw new Error(userMessage);
        }
      },

      // LOGIN WITH OAUTH : REDIRECTION DIRECTE VERS SUPABASE
      loginWithOAuth: async (provider: "linkedin" | "facebook") => {
        set({ isOAuthLoading: provider, authErrors: [] });
        secureLog.log(
          `[AuthStore] OAuth login initiated for ${provider}`,
        );

        try {
          // NOUVEAU: Redirection directe vers le domaine Supabase configuré
          const supabaseUrl = "https://auth.intelia.com";
          const providerName =
            provider === "linkedin" ? "linkedin_oidc" : provider;
          const redirectTo = encodeURIComponent(
            "https://expert.intelia.com/chat",
          );
          const oauthUrl = `${supabaseUrl}/auth/v1/authorize?provider=${providerName}&redirect_to=${redirectTo}`;

          secureLog.log(`[AuthStore] Redirecting to Supabase OAuth`);

          // Redirection directe vers Supabase - pas d'appel backend intermédiaire
          window.location.href = oauthUrl;
        } catch (e: any) {
          secureLog.error(`[AuthStore] OAuth ${provider} error`, e);
          get().handleAuthError(e, `loginWithOAuth-${provider}`);

          let userMessage =
            e?.message || `Erreur de connexion avec ${provider}`;

          set({ isOAuthLoading: null });
          throw new Error(userMessage);
        }
      },

      // HANDLE OAUTH TOKEN FROM URL : Récupère le token depuis l'URL après redirection Supabase
      handleOAuthTokenFromURL: async () => {
        try {
          // Vérifier s'il y a des paramètres OAuth dans l'URL
          const urlParams = new URLSearchParams(window.location.search);

          // Gérer les tokens Supabase dans l'URL (format fragment #access_token=...)
          const hashParams = new URLSearchParams(window.location.hash.slice(1));
          const accessToken =
            hashParams.get("access_token") || urlParams.get("access_token");
          const tokenType =
            hashParams.get("token_type") || urlParams.get("token_type");
          const refreshToken =
            hashParams.get("refresh_token") || urlParams.get("refresh_token");
          const expiresIn =
            hashParams.get("expires_in") || urlParams.get("expires_in");

          // Aussi vérifier les anciens paramètres pour compatibilité
          const oauthToken = urlParams.get("oauth_token");
          const oauthSuccess = urlParams.get("oauth_success");
          const oauthProvider = urlParams.get("oauth_provider");
          const oauthEmail = urlParams.get("oauth_email");

          if (
            (accessToken && tokenType === "bearer") ||
            (oauthSuccess === "true" && oauthToken)
          ) {
            const finalToken = accessToken || oauthToken;
            secureLog.log("[AuthStore] OAuth token detected in URL");

            // Calculer l'expiration
            const expiresAt = expiresIn
              ? new Date(Date.now() + parseInt(expiresIn) * 1000).toISOString()
              : undefined;

            // Stocker le token dans localStorage
            const authData = {
              access_token: finalToken,
              token_type: "bearer",
              refresh_token: refreshToken,
              expires_at: expiresAt,
              synced_at: Date.now(),
              oauth_provider: oauthProvider || "supabase",
            };
            localStorage.setItem(
              "intelia-expert-auth",
              JSON.stringify(authData),
            );

            // Nettoyer l'URL des paramètres OAuth
            const cleanUrl = new URL(window.location.href);
            cleanUrl.searchParams.delete("oauth_token");
            cleanUrl.searchParams.delete("oauth_success");
            cleanUrl.searchParams.delete("oauth_email");
            cleanUrl.searchParams.delete("oauth_provider");
            cleanUrl.searchParams.delete("access_token");
            cleanUrl.searchParams.delete("token_type");
            cleanUrl.searchParams.delete("refresh_token");
            cleanUrl.searchParams.delete("expires_in");
            cleanUrl.hash = ""; // Nettoyer aussi le hash
            window.history.replaceState(
              {},
              "",
              cleanUrl.pathname + cleanUrl.search,
            );

            // Vérifier l'auth pour récupérer les données utilisateur complètes
            await get().checkAuth();

            // NOUVEAU: Démarrer le tracking de session après OAuth réussi
            if (get().isAuthenticated) {
              get().startSessionTracking();
            }

            // Reset du loading OAuth
            set({ isOAuthLoading: null });

            // Déclencher l'événement de redirection
            setTimeout(() => {
              window.dispatchEvent(new Event("auth-state-changed"));
            }, 100);

            secureLog.log(
              `[AuthStore] OAuth Supabase successful`,
            );
            return true;
          }

          // Vérifier les erreurs OAuth
          const oauthError =
            urlParams.get("oauth_error") || urlParams.get("error");
          const errorDescription = urlParams.get("error_description");

          if (oauthError) {
            secureLog.error(
              "[AuthStore] OAuth error in URL",
              { type: oauthError },
            );

            // Nettoyer l'URL
            const cleanUrl = new URL(window.location.href);
            cleanUrl.searchParams.delete("oauth_error");
            cleanUrl.searchParams.delete("error");
            cleanUrl.searchParams.delete("error_description");
            cleanUrl.hash = "";
            window.history.replaceState(
              {},
              "",
              cleanUrl.pathname + cleanUrl.search,
            );

            // Reset du loading et ajouter l'erreur
            set({ isOAuthLoading: null });
            const errorMsg = errorDescription
              ? `${oauthError}: ${errorDescription}`
              : oauthError;
            get().handleAuthError(
              { message: decodeURIComponent(errorMsg) },
              "oauth-url-error",
            );

            return false;
          }

          return false;
        } catch (error) {
          secureLog.error(
            "[AuthStore] OAuth URL token processing error",
            error,
          );
          set({ isOAuthLoading: null });
          return false;
        }
      },

      // REGISTER : Utilise /auth/register
      register: async (
        email: string,
        password: string,
        userData: Partial<AppUser>,
      ) => {
        set({ isLoading: true, authErrors: [] });
        secureLog.log("[AuthStore] Registration attempt");

        try {
          const fullName = userData?.name || "";
          if (!fullName || fullName.length < 2) {
            throw new Error("Le nom doit contenir au moins 2 caractères");
          }

          // Détecter la langue préférée depuis le store de langue ou le navigateur
          const languageStore = (window as any).__LANGUAGE_STORE__;
          const preferredLanguage =
            languageStore?.getState?.()?.currentLanguage ||
            userData.preferredLanguage ||
            navigator.language.split('-')[0] ||
            'en';

          secureLog.log("[AuthStore] Language detected for registration", { preferredLanguage });

          const payload = {
            email,
            password,
            full_name: fullName,
            first_name: userData.firstName,
            last_name: userData.lastName,
            company: userData.companyName,
            phone: userData.phone,
            country: userData.country,
            preferred_language: preferredLanguage,
            production_type: (userData as any).production_type,
            category: (userData as any).category,
            category_other: (userData as any).category_other,
          };

          secureLog.log("[AuthStore] Registration payload prepared");

          const response = await apiClient.post<{ token?: string; user?: any }>(
            "/auth/register",
            payload,
          );

          if (!response.success) {
            throw new Error(
              response.error?.message || "Erreur lors de la création du compte",
            );
          }

          const { token, user } = response.data;

          if (token) {
            // Sauvegarder le token
            const authData = {
              access_token: token,
              token_type: "bearer",
              synced_at: Date.now(),
            };
            localStorage.setItem(
              "intelia-expert-auth",
              JSON.stringify(authData),
            );

            // Récupérer les données utilisateur
            await get().checkAuth();

            // NOUVEAU: Démarrer le tracking de session après register réussi
            if (get().isAuthenticated) {
              get().startSessionTracking();
            }
          }

          set({ isLoading: false });
          secureLog.log("[AuthStore] Registration successful");
        } catch (e: any) {
          get().handleAuthError(e, "register");

          let userMessage =
            e?.message || "Erreur lors de la création du compte";

          if (userMessage.includes("already registered")) {
            userMessage = "Cette adresse email est déjà utilisée";
          } else if (userMessage.includes("Password should be at least")) {
            userMessage = "Le mot de passe doit contenir au moins 6 caractères";
          }

          set({ isLoading: false });
          throw new Error(userMessage);
        }
      },

      // LOGOUT : Nettoyage simple + fin de session tracking
      logout: async () => {
        secureLog.log("[AuthStore] Logout - localStorage cleanup");

        try {
          // NOUVEAU: Terminer le tracking de session avant le logout
          await get().endSessionTracking();

          // Nettoyage localStorage sélectif
          const keysToRemove = [];

          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (
              key &&
              key !== "intelia-remember-me-persist" &&
              key !== "intelia-language" &&
              key !== "intelia_ad_history"
            ) {
              if (
                key.startsWith("supabase-") ||
                (key.startsWith("intelia-") &&
                  key !== "intelia-remember-me-persist" &&
                  key !== "intelia-language" &&
                  key !== "intelia_ad_history") ||
                key.includes("auth") ||
                key.includes("session") ||
                key === "intelia-expert-auth"
              ) {
                keysToRemove.push(key);
              }
            }
          }

          keysToRemove.forEach((key) => {
            localStorage.removeItem(key);
          });

          // Nettoyer aussi sessionStorage OAuth
          sessionStorage.removeItem("oauth_state");
          sessionStorage.removeItem("oauth_provider");

          // Reset du store
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            isOAuthLoading: null,
            authErrors: [],
            lastAuthCheck: Date.now(),
            // Reset session tracking
            sessionStart: null,
            sessionDuration: 0,
            lastHeartbeat: 0,
            heartbeatInterval: null,
          });

          sessionStorage.setItem("recent-logout", Date.now().toString());
          secureLog.log("[AuthStore] Logout successful");
        } catch (e: any) {
          secureLog.error("[AuthStore] Logout error", e);
          throw new Error(e?.message || "Erreur lors de la déconnexion");
        }
      },

      // UPDATE PROFILE : Via backend si endpoint disponible
      updateProfile: async (data: Partial<AppUser>) => {
        set({ isLoading: true });
        secureLog.log("[AuthStore] UpdateProfile");

        try {
          const currentUser = get().user;
          if (!currentUser) {
            throw new Error("Utilisateur non connecté");
          }

          // Préparer les données pour l'API backend
          const apiData: any = {};

          if (data.firstName !== undefined) {
            apiData.first_name = String(data.firstName).trim();
          }

          if (data.lastName !== undefined) {
            apiData.last_name = String(data.lastName).trim();
          }

          // Construire full_name à partir des composants
          if (data.firstName !== undefined || data.lastName !== undefined) {
            const fullName =
              `${data.firstName || ""} ${data.lastName || ""}`.trim();
            apiData.full_name = fullName;
          }

          // Ajouter les autres champs
          if (data.country_code !== undefined)
            apiData.country_code = data.country_code;
          if (data.area_code !== undefined) apiData.area_code = data.area_code;
          if (data.phone_number !== undefined)
            apiData.phone_number = data.phone_number;
          if (data.whatsapp_number !== undefined)
            apiData.whatsapp_number = data.whatsapp_number;
          if (data.country !== undefined) apiData.country = data.country;
          if (data.linkedinProfile !== undefined)
            apiData.linkedin_profile = data.linkedinProfile;
          if (data.companyName !== undefined)
            apiData.company_name = data.companyName;
          if (data.companyWebsite !== undefined)
            apiData.company_website = data.companyWebsite;
          if (data.linkedinCorporate !== undefined)
            apiData.linkedin_corporate = data.linkedinCorporate;
          if (data.language !== undefined)
            apiData.language = data.language;

          secureLog.log(
            "[AuthStore] Sending to backend API: /users/profile",
          );

          // Utiliser apiClient.putSecure() pour mettre à jour le profil
          const response = await apiClient.putSecure<{
            success: boolean;
            message: string;
            user: any;
          }>("/users/profile", apiData);

          if (!response.success) {
            throw new Error(
              response.error?.message ||
                "Erreur lors de la mise à jour du profil",
            );
          }

          secureLog.log(
            "[AuthStore] Profile updated successfully",
          );

          // Recharger les données utilisateur
          await get().checkAuth();

          set({ isLoading: false });
          secureLog.log("[AuthStore] Profile updated and reloaded");
        } catch (e: any) {
          get().handleAuthError(e, "updateProfile");
          set({ isLoading: false });
          throw new Error(e?.message || "Erreur de mise à jour du profil");
        }
      },

      // GET AUTH TOKEN : Depuis localStorage uniquement
      getAuthToken: async () => {
        try {
          const authData = localStorage.getItem("intelia-expert-auth");
          if (!authData) return null;

          const parsed = JSON.parse(authData);
          return parsed.access_token || null;
        } catch (error) {
          secureLog.error("[AuthStore] Token retrieval error", error);
          return null;
        }
      },

      // UPDATE CONSENT - Gestion du consentement RGPD
      updateConsent: async (consentGiven: boolean) => {
        secureLog.log("[AuthStore] Updating consent");

        try {
          const currentUser = get().user;
          if (!currentUser) {
            throw new Error("Utilisateur non connecté");
          }

          const response = await apiClient.putSecure("/users/consent", {
            consent_given: consentGiven,
            consent_date: new Date().toISOString(),
          });

          if (!response.success) {
            throw new Error(
              response.error?.message ||
                "Erreur lors de la mise à jour du consentement",
            );
          }

          // Recharger les données utilisateur pour refléter le changement
          await get().checkAuth();

          secureLog.log("[AuthStore] Consent updated successfully");
        } catch (e: any) {
          get().handleAuthError(e, "updateConsent");
          throw new Error(
            e?.message || "Erreur lors de la mise à jour du consentement",
          );
        }
      },

      // EXPORT USER DATA - Conformité RGPD
      exportUserData: async () => {
        secureLog.log("[AuthStore] Exporting user data (GDPR)");

        try {
          const currentUser = get().user;
          if (!currentUser) {
            throw new Error("Utilisateur non connecté");
          }

          const response = await apiClient.getSecure("/users/export-data");

          if (!response.success) {
            throw new Error(
              response.error?.message || "Erreur lors de l'export des données",
            );
          }

          secureLog.log("[AuthStore] Data export successful");
          return response.data;
        } catch (e: any) {
          get().handleAuthError(e, "exportUserData");
          throw new Error(e?.message || "Erreur lors de l'export des données");
        }
      },

      // DELETE USER DATA - Suppression compte RGPD
      deleteUserData: async () => {
        secureLog.log("[AuthStore] Deleting user data (GDPR)");

        try {
          const currentUser = get().user;
          if (!currentUser) {
            throw new Error("Utilisateur non connecté");
          }

          const response = await apiClient.deleteSecure<any>(
            "/users/delete-account",
          );

          if (!response.success) {
            throw new Error(
              response.error?.message ||
                "Erreur lors de la suppression du compte",
            );
          }

          // Déconnexion automatique après suppression
          await get().logout();

          secureLog.log("[AuthStore] Account deletion successful");
        } catch (e: any) {
          get().handleAuthError(e, "deleteUserData");
          throw new Error(
            e?.message || "Erreur lors de la suppression du compte",
          );
        }
      },
    }),
    {
      name: "intelia-auth-store",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        lastAuthCheck: state.lastAuthCheck,
        hasHydrated: state.hasHydrated,
      }),
      onRehydrateStorage: () => (state, error) => {
        if (error) secureLog.error("Auth store rehydrate error", error);

        // Protection contre la rehydration pendant une déconnexion récente
        const recentLogout = sessionStorage.getItem("recent-logout");
        if (recentLogout) {
          const logoutTime = parseInt(recentLogout);
          if (Date.now() - logoutTime < 1000) {
            secureLog.log(
              "[AuthStore] Rehydration blocked - recent logout",
            );
            if (state) {
              state.user = null;
              state.isAuthenticated = false;
            }
            return;
          }
        }

        if (state) {
          state.setHasHydrated(true);
          secureLog.log("[AuthStore] Store rehydrated");
        }
      },
    },
  ),
);

// NOUVEAU: Hook simplifié - le tracking est maintenant automatique via startSessionTracking
export const useSessionHeartbeat = () => {
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    // L'interval heartbeat + refresh est maintenant géré automatiquement
    // par startSessionTracking(), donc ce hook ne fait plus rien
    secureLog.log("[SessionHeartbeat] Automatic tracking active");
  }, [isAuthenticated]);
};

// Fonction utilitaire exportée
export const getAuthToken = async (): Promise<string | null> => {
  try {
    const authData = localStorage.getItem("intelia-expert-auth");
    if (!authData) return null;

    const parsed = JSON.parse(authData);
    return parsed.access_token || null;
  } catch (error) {
    secureLog.error("[AuthStore] Utility token retrieval error", error);
    return null;
  }
};