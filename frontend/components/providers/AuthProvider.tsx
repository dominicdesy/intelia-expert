// AuthProvider.tsx - Version corrigée avec session tracking automatique
"use client";

import React, { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import { secureLog } from "@/lib/utils/secureLogger";

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const {
    hasHydrated,
    setHasHydrated,
    checkAuth,
    isAuthenticated,
    initializeSession,
    sendHeartbeat,
  } = useAuthStore();

  // Initialisation unique avec session tracking
  useEffect(() => {
    if (!hasHydrated) {
      setHasHydrated(true);

      // Utiliser initializeSession au lieu de checkAuth pour démarrer le tracking
      initializeSession();
    }
  }, [hasHydrated, setHasHydrated, initializeSession]);

  // Gestion des redirections
  useEffect(() => {
    if (!hasHydrated) return;

    const publicRoutes = [
      "/",
      "/auth/login",
      "/auth/signup",
      "/auth/forgot-password",
      "/auth/reset-password",
      "/privacy",
      "/terms",
    ];

    if (isAuthenticated && publicRoutes.includes(pathname)) {
      router.push("/chat");
    }
  }, [isAuthenticated, pathname, hasHydrated, router]);

  // Heartbeat automatique pour maintenir la session active
  useEffect(() => {
    if (!isAuthenticated) return;

    // Heartbeat initial après 30 secondes
    const initialHeartbeat = setTimeout(() => {
      sendHeartbeat();
    }, 30000);

    // Heartbeat régulier toutes les 2 minutes
    const heartbeatInterval = setInterval(() => {
      sendHeartbeat();
    }, 120000); // 2 minutes

    secureLog.log("[AuthProvider] Heartbeat automatique activé");

    return () => {
      clearTimeout(initialHeartbeat);
      clearInterval(heartbeatInterval);
      secureLog.log("[AuthProvider] Heartbeat automatique désactivé");
    };
  }, [isAuthenticated, sendHeartbeat]);

  // Gestion de la fermeture de l'onglet/navigateur pour terminer la session proprement
  useEffect(() => {
    if (!isAuthenticated) return;

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      // Envoyer un signal de fin de session via l'endpoint logout
      const authData = localStorage.getItem("intelia-expert-auth");
      if (authData) {
        try {
          const parsed = JSON.parse(authData);
          const token = parsed.access_token;

          if (token) {
            // CORRECTION: Utiliser l'endpoint logout au lieu de heartbeat
            const baseUrl =
              process.env.NEXT_PUBLIC_API_BASE_URL ||
              "https://expert.intelia.com/api";
            const logoutUrl = `${baseUrl}/v1/auth/logout`;

            fetch(logoutUrl, {
              method: "POST",
              headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                reason: "browser_close", // Correction: utiliser 'reason' comme dans l'endpoint
              }),
              keepalive: true,
            }).catch(() => {
              // Ignorer les erreurs silencieusement lors de la fermeture
            });

            secureLog.log(
              "[AuthProvider] Signal de fermeture envoyé via logout endpoint",
            );
          }
        } catch (error) {
          secureLog.warn("[AuthProvider] Erreur envoi logout:", error);
        }
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        // Page cachée, potentiellement fermée
        handleBeforeUnload({} as BeforeUnloadEvent);
      }
    };

    // Écouter les événements de fermeture
    window.addEventListener("beforeunload", handleBeforeUnload);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [isAuthenticated]);

  // Debug: Afficher les informations de session en développement
  useEffect(() => {
    if (process.env.NODE_ENV === "development" && isAuthenticated) {
      const { sessionStart, lastHeartbeat } = useAuthStore.getState();

      if (sessionStart) {
        const sessionDuration = (Date.now() - sessionStart.getTime()) / 1000;
        secureLog.log(
          `[AuthProvider] Session active depuis ${Math.round(sessionDuration)}s`,
        );

        if (lastHeartbeat) {
          const timeSinceHeartbeat = (Date.now() - lastHeartbeat) / 1000;
          secureLog.log(
            `[AuthProvider] Dernier heartbeat il y a ${Math.round(timeSinceHeartbeat)}s`,
          );
        }
      }
    }
  }, [isAuthenticated]);

  return <>{children}</>;
}
