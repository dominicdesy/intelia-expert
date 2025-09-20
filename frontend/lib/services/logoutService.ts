// lib/services/logoutService.ts
// Service de logout independant pour eviter les problemes React #300

export const logoutService = {
  async performLogout(user?: any): Promise<void> {
    console.log("[LogoutService] Debut deconnexion via service independant");

    // Timeout global pour forcer la redirection en cas de blocage
    const forceRedirect = setTimeout(() => {
      console.log(
        "[LogoutService] TIMEOUT GLOBAL - Redirection forcée après 8 secondes",
      );
      window.location.href = "/";
    }, 8000); // 8 secondes maximum pour tout le processus

    try {
      // 1. Detecter la langue de l'utilisateur AVANT le nettoyage
      let userLanguage = "fr"; // Defaut francais
      try {
        // Methode 1: Depuis le parametre user passe
        if (user?.language) {
          userLanguage = user.language;
          console.log(
            "[LogoutService] Langue detectee depuis user:",
            userLanguage,
          );
        }
        // Methode 2: Depuis le localStorage du store Zustand
        else {
          const zustandLang = localStorage.getItem("intelia-language");
          if (zustandLang) {
            const parsed = JSON.parse(zustandLang);
            userLanguage = parsed?.state?.currentLanguage || "fr";
            console.log(
              "[LogoutService] Langue detectee depuis localStorage:",
              userLanguage,
            );
          }
        }
      } catch (error) {
        console.warn(
          "[LogoutService] Erreur detection langue, utilisation du francais:",
          error,
        );
      }
      console.log("[LogoutService] Etape 1 terminee - Detection langue");

      // 2. Preserver RememberMe si necessaire
      let preservedRememberMe = null;
      try {
        const rememberMeData = localStorage.getItem(
          "intelia-remember-me-persist",
        );
        if (rememberMeData) {
          preservedRememberMe = JSON.parse(rememberMeData);
          console.log("[LogoutService] RememberMe preserve");
        }
      } catch (error) {
        console.warn("[LogoutService] Erreur preservation RememberMe:", error);
      }
      console.log("[LogoutService] Etape 2 terminee - Preservation RememberMe");

      // 3. Deconnexion Supabase avec timeout robuste
      console.log("[LogoutService] Tentative deconnexion Supabase...");
      try {
        // Import avec timeout de 2 secondes
        const importPromise = import("@/lib/supabase/singleton");
        const importTimeout = new Promise((_, reject) =>
          setTimeout(() => reject(new Error("Import timeout")), 2000),
        );

        const { getSupabaseClient } = (await Promise.race([
          importPromise,
          importTimeout,
        ])) as any;
        const supabase = getSupabaseClient();

        // Deconnexion avec timeout de 3 secondes
        const signOutPromise = supabase.auth.signOut();
        const signOutTimeout = new Promise((_, reject) =>
          setTimeout(() => reject(new Error("SignOut timeout")), 3000),
        );

        await Promise.race([signOutPromise, signOutTimeout]);
        console.log(
          "[LogoutService] Deconnexion Supabase terminee avec succes",
        );
      } catch (supabaseError) {
        console.warn(
          "[LogoutService] Erreur/Timeout Supabase (continue quand meme):",
          supabaseError?.message || supabaseError,
        );
      }
      console.log("[LogoutService] Etape 3 terminee - Deconnexion Supabase");

      // 4. Nettoyage localStorage selectif
      console.log("[LogoutService] Nettoyage localStorage...");
      const keysToRemove = [];
      try {
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (
            key &&
            key !== "intelia-remember-me-persist" &&
            key !== "intelia-language"
          ) {
            // Nettoyage plus cible pour eviter de supprimer les stores Zustand
            if (
              key.startsWith("supabase-") ||
              key === "intelia-expert-auth" ||
              key === "intelia-chat-storage" ||
              key.includes("session")
            ) {
              keysToRemove.push(key);
            }
          }
        }

        keysToRemove.forEach((key) => {
          try {
            localStorage.removeItem(key);
            console.log(`[LogoutService] Supprime: ${key}`);
          } catch (e) {
            console.warn(`[LogoutService] Impossible de supprimer ${key}:`, e);
          }
        });
      } catch (storageError) {
        console.warn(
          "[LogoutService] Erreur lors du nettoyage localStorage:",
          storageError,
        );
      }
      console.log("[LogoutService] Etape 4 terminee - Nettoyage localStorage");

      // 5. Reinitialiser le store auth au lieu de le supprimer
      try {
        localStorage.setItem(
          "auth-storage",
          JSON.stringify({
            state: {
              user: null,
              isAuthenticated: false,
              isLoading: false,
              hasHydrated: true,
            },
            version: 0,
          }),
        );
        console.log("[LogoutService] Store auth reinitialise");
      } catch (error) {
        console.warn(
          "[LogoutService] Erreur reinitialisation store auth:",
          error,
        );
      }
      console.log(
        "[LogoutService] Etape 5 terminee - Reinitialisation store auth",
      );

      console.log(
        `[LogoutService] ${keysToRemove.length} cles supprimees, RememberMe et Language preserves, Store auth reinitialise`,
      );

      // 6. Restaurer RememberMe si necessaire
      if (preservedRememberMe) {
        try {
          localStorage.setItem(
            "intelia-remember-me-persist",
            JSON.stringify(preservedRememberMe),
          );
          console.log("[LogoutService] RememberMe restaure");
        } catch (error) {
          console.warn(
            "[LogoutService] Erreur restauration RememberMe:",
            error,
          );
        }
      }
      console.log("[LogoutService] Etape 6 terminee - Restauration RememberMe");

      // 7. Marquer le logout comme complete
      try {
        sessionStorage.setItem("recent-logout", Date.now().toString());
        sessionStorage.setItem("logout-complete", "true");
        console.log("[LogoutService] Marqueurs de logout definis");
      } catch (error) {
        console.warn(
          "[LogoutService] Erreur definition marqueurs logout:",
          error,
        );
      }
      console.log("[LogoutService] Etape 7 terminee - Marqueurs logout");

      console.log(
        "[LogoutService] Redirection vers page d'accueil, langue preservee:",
        userLanguage,
      );

      // 8. Annuler le timeout global car tout s'est bien passe
      clearTimeout(forceRedirect);

      // 9. Redirection finale avec un petit delai pour laisser les logs s'afficher
      console.log("[LogoutService] Demarrage redirection dans 200ms...");
      setTimeout(() => {
        console.log("[LogoutService] REDIRECTION MAINTENANT vers /");
        window.location.href = "/";
      }, 200);
    } catch (error) {
      console.error("[LogoutService] Erreur durant logout:", error);

      // Annuler le timeout global
      clearTimeout(forceRedirect);

      // En cas d'erreur, forcer quand meme la redirection vers la page d'accueil
      console.log("[LogoutService] Redirection d'urgence apres erreur...");
      setTimeout(() => {
        console.log("[LogoutService] REDIRECTION D'URGENCE vers /");
        window.location.href = "/";
      }, 500);
    }
  },
};
