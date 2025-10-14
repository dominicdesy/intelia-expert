"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase/client";
import { secureLog } from "@/lib/utils/secureLogger";

export default function AuthCallback() {
  const router = useRouter();

  useEffect(() => {
    const handleCallback = async () => {
      try {
        secureLog.log("[AuthCallback] Début traitement callback Supabase");
        secureLog.log("[AuthCallback] URL complète:", window.location.href);
        secureLog.log("[AuthCallback] Hash complet:", window.location.hash);
        secureLog.log("[AuthCallback] Search params:", window.location.search);

        // Vérifier s'il y a un hash dans l'URL (tokens Supabase)
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const accessToken = hashParams.get("access_token");
        const refreshToken = hashParams.get("refresh_token");
        const type = hashParams.get("type");

        secureLog.log("[AuthCallback] Hash params:", {
          hasAccessToken: !!accessToken,
          hasRefreshToken: !!refreshToken,
          type,
          fullHash: window.location.hash,
        });

        if (accessToken && refreshToken) {
          secureLog.log("[AuthCallback] Tokens trouvés, création session locale...");

          // Créer une session Supabase locale avec les tokens
          const { data, error } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });

          if (error) {
            secureLog.error("[AuthCallback] Erreur création session:", error);
            throw error;
          }

          secureLog.log("[AuthCallback] Session créée avec succès:", {
            user: data.session?.user?.email,
            expiresAt: data.session?.expires_at,
          });

          // Vérifier le type de callback
          if (type === "invite" || type === "invitation") {
            secureLog.log("[AuthCallback] Type invitation détecté, redirection vers /auth/invitation");
            router.push("/auth/invitation");
          } else if (type === "recovery") {
            secureLog.log("[AuthCallback] Type recovery détecté, redirection vers /auth/reset-password");
            router.push("/auth/reset-password");
          } else {
            // Par défaut, rediriger vers le chat
            secureLog.log("[AuthCallback] Type par défaut, redirection vers /chat");
            router.push("/chat");
          }
        } else {
          // Pas de tokens dans le hash - vérifier si session existe déjà
          const { data: sessionData, error: sessionError } = await supabase.auth.getSession();

          if (sessionError || !sessionData.session) {
            secureLog.warn("[AuthCallback] Pas de tokens et pas de session existante");
            router.push("/auth/login?error=no_session");
            return;
          }

          secureLog.log("[AuthCallback] Session existante trouvée, redirection...");
          router.push("/chat");
        }
      } catch (error) {
        secureLog.error("[AuthCallback] Erreur traitement callback:", error);
        router.push("/auth/login?error=callback_failed");
      }
    };

    // Délai pour s'assurer que le hash est bien chargé
    const timer = setTimeout(handleCallback, 100);
    return () => clearTimeout(timer);
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Authentification en cours...
        </h2>
        <p className="text-sm text-gray-600">
          Veuillez patienter pendant que nous finalisons votre connexion.
        </p>
      </div>
    </div>
  );
}
