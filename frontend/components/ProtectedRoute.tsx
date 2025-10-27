/**
 * Protectedroute
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
// components/ProtectedRoute.tsx - PROTECTION ROUTES AVANCÉE
"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import ClientOnly from "./ClientOnly";
import { secureLog } from "@/lib/utils/secureLogger";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredUserType?: "producer" | "professional";
  adminOnly?: boolean;
  fallback?: React.ReactNode;
  redirectTo?: string;
}

export default function ProtectedRoute({
  children,
  requiredUserType,
  adminOnly = false,
  fallback,
  redirectTo = "/",
}: ProtectedRouteProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isAuthenticated, hasHydrated } = useAuthStore();
  const { checkAuth } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);

  // Fallback par défaut
  const defaultFallback = (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-intelia-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Vérification des permissions...</p>
      </div>
    </div>
  );

  useEffect(() => {
    const performAuthCheck = async () => {
      if (!hasHydrated) {
        return; // Attendre l'hydratation
      }

      try {
        // Vérifier l'auth si pas encore fait
        if (!user && !isAuthenticated) {
          await checkAuth();
        }

        setIsChecking(false);
      } catch (error) {
        secureLog.error("❌ Erreur vérification auth:", error);
        setIsChecking(false);
      }
    };

    performAuthCheck();
  }, [hasHydrated, user, isAuthenticated, checkAuth]);

  useEffect(() => {
    if (!hasHydrated || isChecking) {
      return; // Attendre la vérification
    }

    // Pas connecté = redirection login avec message
    if (!isAuthenticated || !user) {
      secureLog.log("🚫 Utilisateur non authentifié - Redirection");

      const currentPath = window.location.pathname;
      const redirectUrl = new URL(redirectTo, window.location.origin);
      redirectUrl.searchParams.set("redirect", currentPath);
      redirectUrl.searchParams.set("message", "auth_required");

      router.replace(redirectUrl.toString());
      return;
    }

    // Vérifier le type d'utilisateur si requis
    if (requiredUserType && user.user_type !== requiredUserType) {
      secureLog.warn("🚫 Accès refusé: type utilisateur insuffisant");
      router.replace("/unauthorized?reason=user_type");
      return;
    }

    // Vérifier admin si requis
    if (adminOnly) {
      // Logique admin à implémenter selon vos besoins
      const isAdmin = user.user_type === "professional"; // Exemple

      if (!isAdmin) {
        secureLog.warn("🚫 Accès refusé: permissions admin requises");
        router.replace("/unauthorized?reason=admin_required");
        return;
      }
    }
  }, [
    hasHydrated,
    isChecking,
    isAuthenticated,
    user,
    requiredUserType,
    adminOnly,
    router,
    redirectTo,
  ]);

  // États d'affichage
  if (!hasHydrated || isChecking) {
    return (
      <ClientOnly fallback={fallback || defaultFallback}>
        {fallback || defaultFallback}
      </ClientOnly>
    );
  }

  if (!isAuthenticated || !user) {
    return fallback || defaultFallback;
  }

  // Vérification type utilisateur
  if (requiredUserType && user.user_type !== requiredUserType) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="text-6xl mb-4">🚫</div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Accès Refusé</h1>
          <p className="text-gray-600 mb-4">
            Cette page nécessite un compte <strong>{requiredUserType}</strong>.
          </p>
          <p className="text-sm text-gray-500 mb-4">
            Votre compte actuel :{" "}
            <span className="font-medium">{user.user_type}</span>
          </p>
          <button onClick={() => router.push("/chat")} className="btn-primary">
            Retour au Chat
          </button>
        </div>
      </div>
    );
  }

  // Vérification admin
  if (adminOnly && user.user_type !== "professional") {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="text-6xl mb-4">👮‍♂️</div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">
            Accès Administrateur Requis
          </h1>
          <p className="text-gray-600 mb-4">
            Cette section est réservée aux administrateurs.
          </p>
          <button onClick={() => router.push("/chat")} className="btn-primary">
            Retour au Chat
          </button>
        </div>
      </div>
    );
  }

  // Tout est OK, afficher le contenu
  return <ClientOnly>{children}</ClientOnly>;
}

// Hook utilitaire pour vérifier les permissions
export function usePermissions() {
  const { user } = useAuthStore();

  return {
    isProducer: user?.user_type === "producer",
    isProfessional: user?.user_type === "professional",
    isAdmin: user?.user_type === "professional", // À adapter selon votre logique
    canAccessProfessionalFeatures: user?.user_type === "professional",
    canAccessAdminPanel: user?.user_type === "professional",
  };
}
