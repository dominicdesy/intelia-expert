// components/providers/LanguageProvider.tsx - VERSION CORRIGÉE POUR SYNCHRONISATION
"use client";

import { useEffect, useRef } from "react";
import { useTranslation } from "@/lib/languages/i18n";
import { isValidLanguageCode } from "@/lib/languages/config";
import { secureLog } from "@/lib/utils/secureLogger";

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const { changeLanguage, currentLanguage } = useTranslation();
  const hasInitializedRef = useRef(false);
  const isInitializingRef = useRef(false);
  const isMountedRef = useRef(true); // AJOUT: Protection démontage

  // Cleanup au démontage - DOIT ÊTRE EN PREMIER
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    // Initialisation UNE SEULE FOIS - MAIS SANS ÉCRASER I18N
    if (hasInitializedRef.current || isInitializingRef.current) return;
    isInitializingRef.current = true;

    const initializeLanguage = async () => {
      if (typeof window !== "undefined") {
        try {
          // ✅ CORRECTION : NE PAS forcer de langue, juste marquer comme prêt
          // Le hook useTranslation dans i18n.ts gère déjà la logique de langue

          secureLog.log(`[LanguageProvider] Synchronisation avec i18n, langue actuelle: ${currentLanguage} `);

          // Attendre que i18n.ts termine son initialisation
          const timeoutId = setTimeout(() => {
            // PROTECTION: Vérifier que le composant est toujours monté
            if (!isMountedRef.current) return;

            document.documentElement.classList.add("language-ready");
            // Émettre l'événement pour le script anti-flash
            window.dispatchEvent(new Event("languageReady"));
            secureLog.log("[LanguageProvider] 🎯 Interface prête - Flash évité");
          }, 500); // Délai augmenté pour iOS/iPad

          // Cleanup du timeout
          return () => clearTimeout(timeoutId);
        } catch (error) {
          secureLog.error("[LanguageProvider] Erreur initialisation:", error);
          // En cas d'erreur, forcer l'affichage pour éviter un écran noir
          if (isMountedRef.current) {
            document.documentElement.classList.add("language-ready");
            window.dispatchEvent(new Event("languageReady"));
          }
        } finally {
          hasInitializedRef.current = true;
          isInitializingRef.current = false;
        }
      }
    };

    initializeLanguage();
  }, [currentLanguage]); // ✅ CORRECTION : Écouter currentLanguage au lieu de changeLanguage

  // ÉCOUTER les changements de langue et les propager
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (!isMountedRef.current) return; // PROTECTION

      if (e.key === "intelia-language" && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue);
          const newLang = parsed?.state?.currentLanguage;

          if (
            newLang &&
            isValidLanguageCode(newLang) &&
            newLang !== currentLanguage
          ) {
            // Pas de flash lors des changements manuels
            document.documentElement.classList.remove("language-ready");

            changeLanguage(newLang).then(() => {
              // PROTECTION: Vérifier que le composant est toujours monté
              if (!isMountedRef.current) return;

              // Remettre la classe après le changement
              setTimeout(() => {
                if (!isMountedRef.current) return;
                document.documentElement.classList.add("language-ready");
              }, 100);
            });

            secureLog.log("[LanguageProvider] 🔄 Changement détecté:", newLang);
          }
        } catch (error) {
          secureLog.warn("[LanguageProvider] Erreur storage change:", error);
        }
      }
    };

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [changeLanguage, currentLanguage]);

  // Timeout de sécurité pour éviter un écran noir permanent
  useEffect(() => {
    const safetyTimer = setTimeout(() => {
      // PROTECTION: Vérifier que le composant est toujours monté
      if (!isMountedRef.current) return;

      if (!document.documentElement.classList.contains("language-ready")) {
        secureLog.warn(
          "[LanguageProvider] ⚠️ Timeout sécurité atteint - Affichage forcé",
        );
        document.documentElement.classList.add("language-ready");
        window.dispatchEvent(new Event("languageReady"));
      }
    }, 3000); // 3 secondes max pour laisser le temps à i18n.ts

    return () => clearTimeout(safetyTimer);
  }, []);

  return <>{children}</>;
}
