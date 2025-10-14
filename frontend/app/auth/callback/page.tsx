"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase/client";
import { secureLog } from "@/lib/utils/secureLogger";

export default function AuthCallback() {
  const router = useRouter();

  useEffect(() => {
    console.log("🔵 [DEBUG] useEffect callback déclenché");

    const handleCallback = async () => {
      console.log("🔵 [DEBUG] handleCallback appelé");
      console.log("🔵 [DEBUG] URL:", window.location.href);

      try {
        secureLog.log("[AuthCallback] Début traitement callback Supabase");
        secureLog.log("[AuthCallback] URL complète:", window.location.href);
        console.log("[AuthCallback PROD] Version: 1.0.0.14");

        // PRIORITÉ 1: Vérifier s'il y a un token_hash dans les query params (lien d'invitation personnalisé)
        const urlParams = new URLSearchParams(window.location.search);
        const tokenHash = urlParams.get("token_hash") || urlParams.get("token");
        const typeParam = urlParams.get("type");

        secureLog.log("[AuthCallback] Query params:", {
          hasTokenHash: !!tokenHash,
          type: typeParam,
        });

        // Si token_hash présent (invitation avec custom domain), échanger via backend
        if (tokenHash && typeParam === "invite") {
          secureLog.log("[AuthCallback] Token hash trouvé, échange via backend...");

          const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
          const exchangeResponse = await fetch(
            `${API_BASE_URL}/v1/auth/invitations/exchange-token`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                token: tokenHash,
              }),
            }
          );

          const exchangeResult = await exchangeResponse.json();
          secureLog.log("[AuthCallback] Résultat échange:", { success: exchangeResult.success });

          if (!exchangeResult.success || !exchangeResult.access_token) {
            secureLog.error("[AuthCallback] Échec échange token:", exchangeResult.error);
            router.push(`/?error=${encodeURIComponent(exchangeResult.error || "token_exchange_failed")}`);
            return;
          }

          // Créer une session avec les tokens échangés
          const { data, error } = await supabase.auth.setSession({
            access_token: exchangeResult.access_token,
            refresh_token: exchangeResult.refresh_token,
          });

          if (error) {
            secureLog.error("[AuthCallback] Erreur création session:", error);
            router.push("/?error=session_creation_failed");
            return;
          }

          secureLog.log("[AuthCallback] Session créée avec succès pour:", exchangeResult.user_email);
          router.push("/auth/invitation");
          return;
        }

        // PRIORITÉ 2: Vérifier s'il y a des tokens dans le hash (OAuth standard)
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const accessToken = hashParams.get("access_token");
        const refreshToken = hashParams.get("refresh_token");

        secureLog.log("[AuthCallback] Tokens dans hash:", {
          hasAccessToken: !!accessToken,
          hasRefreshToken: !!refreshToken,
        });

        if (accessToken && refreshToken) {
          secureLog.log("[AuthCallback] Tokens trouvés dans hash, création session locale...");

          // Créer une session Supabase locale avec les tokens
          const { data, error } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });

          if (error) {
            secureLog.error("[AuthCallback] Erreur création session:", error);
            throw error;
          }

          console.log("[AuthCallback PROD] Session créée:", {
            user: data.session?.user?.email,
            expiresAt: data.session?.expires_at,
            userMetadata: data.session?.user?.user_metadata,
          });

          // Déterminer la redirection selon le type dans user_metadata
          const invitationType = data.session?.user?.user_metadata?.invitation_type;

          console.log("[AuthCallback PROD] invitationType:", invitationType);
          console.log("[AuthCallback PROD] typeParam:", typeParam);
          console.log("[AuthCallback PROD] Vérification:", {
            invitationType,
            is_invite_match: invitationType === "invite",
            typeParam_invite: typeParam === "invite",
            will_redirect_to_invitation: invitationType === "invite" || typeParam === "invite" || typeParam === "invitation"
          });

          if (invitationType === "invite" || typeParam === "invite" || typeParam === "invitation") {
            console.log("[AuthCallback PROD] ✅ REDIRECTION VERS /auth/invitation");
            router.push("/auth/invitation");
          } else if (typeParam === "recovery") {
            console.log("[AuthCallback PROD] REDIRECTION VERS /auth/reset-password");
            router.push("/auth/reset-password");
          } else {
            // Par défaut, rediriger vers le chat
            console.log("[AuthCallback PROD] REDIRECTION VERS /chat (par défaut)");
            router.push("/chat");
          }
        } else {
          // PRIORITÉ 3: Pas de tokens - vérifier si session existe déjà
          secureLog.log("[AuthCallback] Aucun token trouvé, vérification session existante...");
          const { data: sessionData, error: sessionError } = await supabase.auth.getSession();

          if (sessionError || !sessionData.session) {
            secureLog.warn("[AuthCallback] Pas de tokens et pas de session existante");
            router.push("/?error=no_session");
            return;
          }

          console.log("[AuthCallback PROD] Session existante trouvée:", {
            user: sessionData.session?.user?.email,
            metadata: sessionData.session?.user?.user_metadata,
          });

          // Vérifier le type même avec une session existante
          const invitationType = sessionData.session?.user?.user_metadata?.invitation_type;

          console.log("[AuthCallback PROD] Session existante - invitationType:", invitationType);
          console.log("[AuthCallback PROD] Session existante - typeParam:", typeParam);

          if (invitationType === "invite" || typeParam === "invite" || typeParam === "invitation") {
            console.log("[AuthCallback PROD] ✅ REDIRECTION VERS /auth/invitation (session existante)");
            router.push("/auth/invitation");
          } else if (typeParam === "recovery") {
            console.log("[AuthCallback PROD] REDIRECTION VERS /auth/reset-password (session existante)");
            router.push("/auth/reset-password");
          } else {
            console.log("[AuthCallback PROD] REDIRECTION VERS /chat (session existante, par défaut)");
            router.push("/chat");
          }
        }
      } catch (error) {
        secureLog.error("[AuthCallback] Erreur traitement callback:", error);
        router.push("/?error=callback_failed");
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
