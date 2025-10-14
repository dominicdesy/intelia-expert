"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useAuthStore } from "@/lib/stores/auth";
import type {
  AdData,
  AdTriggerCriteria,
  UserSessionStats,
  User,
} from "@/types";
import { AD_CONFIG } from "@/types";
import { secureLog } from "@/lib/utils/secureLogger";

export const useAdSystem = () => {
  const { user, isAuthenticated } = useAuthStore();
  const [sessionStats, setSessionStats] = useState<UserSessionStats | null>(
    null,
  );
  const [showAd, setShowAd] = useState(false);
  const [currentAd, setCurrentAd] = useState<AdData | null>(null);
  const isMountedRef = useRef(true); // Protection démontage

  // Cleanup au démontage
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Utiliser la configuration depuis types/index.ts
  const AD_CRITERIA = AD_CONFIG.TRIGGERS;

  // Vérifier les critères d'affichage de publicité
  const checkAdEligibility = useCallback(async () => {
    // PROTECTION: Vérifier que le composant est toujours monté
    if (!isMountedRef.current) return;
    if (!isAuthenticated || !user) return;

    try {
      // Utiliser votre API client existant
      const authData = localStorage.getItem("intelia-expert-auth");
      if (!authData) return;

      const token = JSON.parse(authData).access_token;

      const response = await fetch(
        "/api/v1/logging/analytics/my-sessions?days=7",
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        },
      );

      if (response.ok) {
        const data = await response.json();

        // Correction: Utiliser la structure correcte des données
        const totalSessions = data.summary?.total_sessions || 0;

        // Correction: Calculer la durée moyenne depuis les sessions individuelles
        let averageSessionDuration = 0;
        if (data.recent_sessions && data.recent_sessions.length > 0) {
          // Estimer la durée basée sur l'écart entre les logins (approximation)
          const sessions = data.recent_sessions;
          let totalEstimatedDuration = 0;
          let validSessions = 0;

          for (let i = 0; i < sessions.length; i++) {
            const loginTime = new Date(sessions[i].login_time);

            if (i > 0) {
              // Utiliser l'écart avec la session précédente comme estimation
              const prevLoginTime = new Date(sessions[i - 1].login_time);
              const estimatedDuration =
                Math.abs(prevLoginTime.getTime() - loginTime.getTime()) / 1000;

              // Limiter à des valeurs réalistes (entre 1 minute et 2 heures)
              if (estimatedDuration >= 60 && estimatedDuration <= 7200) {
                totalEstimatedDuration += estimatedDuration;
                validSessions++;
              }
            } else {
              // Pour la première session, estimer 3 minutes par défaut
              totalEstimatedDuration += 180;
              validSessions++;
            }
          }

          if (validSessions > 0) {
            averageSessionDuration = totalEstimatedDuration / validSessions;
          }
        }

        secureLog.log("🔍 Debug Ad System:", {
          totalSessions,
          averageSessionDuration,
          data: data.summary,
        });

        const stats: UserSessionStats = {
          totalSessions,
          averageSessionDuration,
          lastAdShown: localStorage.getItem("lastAdShown"),
          qualifiesForAd: false,
        };

        // Vérifier les critères
        const meetsSessionCriteria =
          stats.totalSessions >= AD_CRITERIA.MIN_SESSIONS;
        const meetsDurationCriteria =
          stats.averageSessionDuration >= AD_CRITERIA.MIN_DURATION_PER_SESSION;

        // Vérifier le cooldown
        const lastAdTime = stats.lastAdShown
          ? new Date(stats.lastAdShown)
          : null;
        const now = new Date();
        const cooldownExpired =
          !lastAdTime ||
          now.getTime() - lastAdTime.getTime() >
            AD_CRITERIA.COOLDOWN_PERIOD * 60 * 60 * 1000;

        stats.qualifiesForAd =
          meetsSessionCriteria && meetsDurationCriteria && cooldownExpired;

        secureLog.log("🎯 Critères publicitaires:", {
          sessions: `${stats.totalSessions} >= ${AD_CRITERIA.MIN_SESSIONS} = ${meetsSessionCriteria}`,
          duration: `${Math.round(stats.averageSessionDuration)}s >= ${AD_CRITERIA.MIN_DURATION_PER_SESSION}s = ${meetsDurationCriteria}`,
          cooldown: `Expiré = ${cooldownExpired}`,
          eligible: stats.qualifiesForAd,
        });

        // PROTECTION: Vérifier que le composant est toujours monté avant setState
        if (!isMountedRef.current) return;
        setSessionStats(stats);

        // TEST FORCÉ EN DÉVELOPPEMENT
        if (process.env.NODE_ENV === "development") {
          secureLog.log("🚀 Mode développement: forçage publicité");
          stats.qualifiesForAd = true;
        }

        // Déclencher la publicité si éligible
        if (stats.qualifiesForAd) {
          secureLog.log("✅ Déclenchement publicité...");
          await triggerAd();
        }
      }
    } catch (error) {
      secureLog.error(
        "❌ Erreur lors de la vérification de l'éligibilité publicitaire:",
        error,
      );
    }
  }, [isAuthenticated, user, AD_CRITERIA]);

  // Obtenir une publicité personnalisée avec rotation et multi-langue
  const getPersonalizedAd = useCallback(async (): Promise<AdData | null> => {
    // Import dynamique du catalogue
    const { selectNextAd, getAdTranslations } = await import("@/lib/ads/ads-catalog");
    const { useTranslation } = await import("@/lib/languages/i18n");

    // Sélectionner la prochaine pub selon le type d'utilisateur
    const selectedAd = selectNextAd(user?.user_type);

    if (!selectedAd) {
      secureLog.warn("[useAdSystem] Aucune publicité disponible");
      return null;
    }

    // Obtenir la langue actuelle (via le store de langue)
    const languageStore = localStorage.getItem("intelia-language");
    let currentLanguage = "fr"; // Défaut

    try {
      if (languageStore) {
        const parsed = JSON.parse(languageStore);
        currentLanguage = parsed?.state?.currentLanguage || "fr";
      }
    } catch {
      currentLanguage = "fr";
    }

    // Obtenir les traductions pour cette pub et cette langue
    const translations = getAdTranslations(selectedAd, currentLanguage);

    secureLog.log(`[useAdSystem] Pub sélectionnée: ${selectedAd.id}, langue: ${currentLanguage}`);

    // Construire l'objet AdData avec les traductions
    const adData: AdData = {
      id: selectedAd.id,
      title: translations.mainTitle,
      description: translations.description,
      imageUrl: selectedAd.imageUrl,
      ctaText: translations.ctaText,
      ctaUrl: selectedAd.ctaUrl,
      company: translations.companyName,
      features: [
        translations.feature1,
        translations.feature2,
        translations.feature3,
      ],
      // Nouvelles propriétés pour le modal amélioré
      headerTitle: translations.headerTitle,
      ctaSubtext: translations.ctaSubtext,
    };

    return adData;
  }, [user]);

  // Déclencher l'affichage de la publicité
  const triggerAd = useCallback(async () => {
    try {
      secureLog.log("🎬 Chargement publicité...");
      const adData = await getPersonalizedAd();
      setCurrentAd(adData);
      setShowAd(true);
      secureLog.log("📺 Publicité affichée:", adData.title);
    } catch (error) {
      secureLog.error("❌ Erreur lors du chargement de la publicité:", error);
    }
  }, [getPersonalizedAd]);

  // Gérer la fermeture de la publicité
  const handleAdClose = useCallback(() => {
    secureLog.log("❌ Fermeture publicité");
    setShowAd(false);
    setCurrentAd(null);

    // Enregistrer le timestamp pour le cooldown
    localStorage.setItem("lastAdShown", new Date().toISOString());
  }, []);

  // Gérer le clic sur la publicité
  const handleAdClick = useCallback((adId: string) => {
    secureLog.log("👆 Clic publicité:", adId);

    // Enregistrer le timestamp pour le cooldown
    localStorage.setItem("lastAdShown", new Date().toISOString());

    // Fermer la modal
    setTimeout(() => {
      // PROTECTION: Vérifier que le composant est toujours monté
      if (!isMountedRef.current) return;
      setShowAd(false);
      setCurrentAd(null);
    }, 1000);
  }, []);

  // Vérifier l'éligibilité au démarrage et périodiquement
  useEffect(() => {
    if (isAuthenticated) {
      secureLog.log("🏁 Initialisation Ad System...");

      // Délai initial pour laisser le temps aux sessions de se charger
      const initialDelay = setTimeout(() => {
        secureLog.log("🔍 Vérification éligibilité publicité...");
        checkAdEligibility();
      }, AD_CRITERIA.INITIAL_CHECK_DELAY || 3000);

      // Puis vérifier selon l'intervalle configuré
      const interval = setInterval(
        () => {
          secureLog.log("🔄 Vérification périodique publicité...");
          checkAdEligibility();
        },
        AD_CRITERIA.CHECK_INTERVAL || 5 * 60 * 1000,
      );

      return () => {
        clearTimeout(initialDelay);
        clearInterval(interval);
      };
    }
  }, [isAuthenticated, checkAdEligibility, AD_CRITERIA]);

  // Test manual trigger
  useEffect(() => {
    const handleManualTrigger = () => {
      secureLog.log("🧪 Déclenchement manuel publicité");
      triggerAd();
    };

    window.addEventListener("triggerAd", handleManualTrigger);

    return () => {
      window.removeEventListener("triggerAd", handleManualTrigger);
    };
  }, [triggerAd]);

  return {
    sessionStats,
    showAd,
    currentAd,
    handleAdClose,
    handleAdClick,
    checkAdEligibility,
    triggerAd,
  };
};
