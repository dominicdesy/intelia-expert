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
          setTimeout(() => {
            document.documentElement.classList.add("language-ready");
            secureLog.log("[LanguageProvider] 🎯 Interface prête - Flash évité");
          }, 200); // Délai plus long pour laisser i18n.ts finir
        } catch (error) {
          secureLog.error("[LanguageProvider] Erreur initialisation:", error);
          // En cas d'erreur, forcer l'affichage pour éviter un écran noir
          document.documentElement.classList.add("language-ready");
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
              // Remettre la classe après le changement
              setTimeout(() => {
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
      if (!document.documentElement.classList.contains("language-ready")) {
        secureLog.warn(
          "[LanguageProvider] ⚠️ Timeout sécurité atteint - Affichage forcé",
        );
        document.documentElement.classList.add("language-ready");
      }
    }, 3000); // 3 secondes max pour laisser le temps à i18n.ts

    return () => clearTimeout(safetyTimer);
  }, []);

  return <>{children}</>;
}
