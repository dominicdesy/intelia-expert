// page_hooks.ts - Version avec support multilingue basé sur useTranslation
import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { useTranslation } from "@/lib/languages/i18n";
import type { Country } from "./page_types";
import { secureLog } from "@/lib/utils/secureLogger";

// Mapping des codes de langue vers les codes utilisés par REST Countries
const getLanguageCode = (currentLanguage: string): string => {
  const mapping: Record<string, string> = {
    fr: "fra", // Français
    es: "spa", // Espagnol
    de: "deu", // Allemand
    pt: "por", // Portugais
    nl: "nld", // Néerlandais
    pl: "pol", // Polonais
    zh: "zho", // Chinois
    hi: "hin", // Hindi
    th: "tha", // Thaï
    en: "eng", // Anglais (fallback)
  };
  return mapping[currentLanguage] || "eng";
};

// Fallback countries avec noms par défaut en français
const fallbackCountries: Country[] = [
  { value: "CA", label: "Canada", phoneCode: "+1", flag: "🇨🇦" },
  { value: "US", label: "États-Unis", phoneCode: "+1", flag: "🇺🇸" },
  { value: "FR", label: "France", phoneCode: "+33", flag: "🇫🇷" },
  { value: "GB", label: "Royaume-Uni", phoneCode: "+44", flag: "🇬🇧" },
  { value: "DE", label: "Allemagne", phoneCode: "+49", flag: "🇩🇪" },
  { value: "IT", label: "Italie", phoneCode: "+39", flag: "🇮🇹" },
  { value: "ES", label: "Espagne", phoneCode: "+34", flag: "🇪🇸" },
  { value: "BE", label: "Belgique", phoneCode: "+32", flag: "🇧🇪" },
  { value: "CH", label: "Suisse", phoneCode: "+41", flag: "🇨🇭" },
  { value: "MX", label: "Mexique", phoneCode: "+52", flag: "🇲🇽" },
  { value: "BR", label: "Brésil", phoneCode: "+55", flag: "🇧🇷" },
  { value: "AU", label: "Australie", phoneCode: "+61", flag: "🇦🇺" },
  { value: "JP", label: "Japon", phoneCode: "+81", flag: "🇯🇵" },
  { value: "CN", label: "Chine", phoneCode: "+86", flag: "🇨🇳" },
  { value: "IN", label: "Inde", phoneCode: "+91", flag: "🇮🇳" },
  { value: "NL", label: "Pays-Bas", phoneCode: "+31", flag: "🇳🇱" },
  { value: "SE", label: "Suède", phoneCode: "+46", flag: "🇸🇪" },
  { value: "NO", label: "Norvège", phoneCode: "+47", flag: "🇳🇴" },
  { value: "DK", label: "Danemark", phoneCode: "+45", flag: "🇩🇰" },
  { value: "FI", label: "Finlande", phoneCode: "+358", flag: "🇫🇮" },
];

// Cache global pour éviter les multiples appels API - MODIFIÉ pour inclure la langue
let countriesCache: Record<string, Country[]> = {};
let isLoadingGlobal = false;
let loadingPromises: Record<string, Promise<Country[]>> = {};

// Version optimisée des logs pour réduire le "bruit"
const DEBUG_MODE = process.env.NODE_ENV === "development";

const debugLog = (category: string, message: string, data?: any) => {
  if (!DEBUG_MODE) return;

  const emoji = {
    form: "📝",
    auth: "🔐",
    storage: "💾",
    error: "❌",
    success: "✅",
    countries: "🌍",
  };

  secureLog.log(`${emoji[category] || "📝"} [${category}] ${message} ${data ? data : ""} `);
};

// Fonction de fetch avec support multilingue
const fetchCountriesGlobal = async (
  languageCode: string,
): Promise<Country[]> => {
  // Si on a déjà les données en cache pour cette langue, les retourner
  if (countriesCache[languageCode]) {
    debugLog("countries", `Données déjà en cache pour ${languageCode}`);
    return countriesCache[languageCode];
  }

  // Si un chargement est déjà en cours pour cette langue, attendre sa fin
  if (loadingPromises[languageCode]) {
    debugLog(
      "countries",
      `Chargement en cours pour ${languageCode}, attente...`,
    );
    return loadingPromises[languageCode];
  }

  // Créer une nouvelle promesse de chargement pour cette langue
  loadingPromises[languageCode] = new Promise(async (resolve) => {
    try {
      debugLog(
        "countries",
        `Début du chargement depuis l'API REST Countries en ${languageCode}...`,
      );

      isLoadingGlobal = true;

      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        debugLog("countries", "Timeout atteint (10s)");
        controller.abort();
      }, 10000);

      const response = await fetch(
        "https://restcountries.com/v3.1/all?fields=cca2,name,idd,flag,translations",
        {
          headers: {
            Accept: "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; Intelia/1.0)",
            "Cache-Control": "no-cache",
          },
          signal: controller.signal,
        },
      );

      clearTimeout(timeoutId);
      debugLog(
        "countries",
        `Statut HTTP: ${response.status} ${response.statusText}`,
      );

      if (!response.ok) {
        throw new Error(`API indisponible: ${response.status}`);
      }

      const data = await response.json();
      debugLog("countries", `Données reçues: ${data.length} pays bruts`);

      if (!Array.isArray(data)) {
        debugLog("error", "Format invalide - pas un array");
        throw new Error("Format de données invalide");
      }

      const formattedCountries = data
        .map((country: any) => {
          let phoneCode = "";
          if (country.idd?.root) {
            phoneCode = country.idd.root;
            if (country.idd.suffixes && country.idd.suffixes[0]) {
              phoneCode += country.idd.suffixes[0];
            }
          }

          // MODIFICATION PRINCIPALE : Récupération du nom selon la langue
          let countryName = country.name?.common || country.cca2;

          // Essayer d'abord la traduction dans la langue demandée
          if (country.translations && country.translations[languageCode]) {
            countryName =
              country.translations[languageCode].common ||
              country.translations[languageCode].official;
          }
          // Si pas de traduction dans la langue demandée, essayer l'anglais
          else if (country.name?.common) {
            countryName = country.name.common;
          }

          return {
            value: country.cca2,
            label: countryName,
            phoneCode: phoneCode,
            flag: country.flag || "",
          };
        })
        .filter((country: Country) => {
          const hasValidCode =
            country.phoneCode &&
            country.phoneCode !== "undefined" &&
            country.phoneCode !== "null" &&
            country.phoneCode.length > 1 &&
            country.phoneCode.startsWith("+") &&
            /^\+\d+$/.test(country.phoneCode);

          const hasValidInfo =
            country.value &&
            country.value.length === 2 &&
            country.label &&
            country.label.length > 1;

          return hasValidCode && hasValidInfo;
        })
        .sort((a: Country, b: Country) => {
          // Tri selon la langue actuelle
          const locale =
            languageCode === "fra"
              ? "fr"
              : languageCode === "spa"
                ? "es"
                : languageCode === "deu"
                  ? "de"
                  : languageCode === "por"
                    ? "pt"
                    : languageCode === "nld"
                      ? "nl"
                      : languageCode === "pol"
                        ? "pl"
                        : languageCode === "zho"
                          ? "zh"
                          : "en";

          return a.label.localeCompare(b.label, locale, { numeric: true });
        });

      debugLog(
        "countries",
        `Pays valides après filtrage: ${formattedCountries.length}`,
      );

      if (formattedCountries.length >= 50) {
        debugLog(
          "success",
          `API validée! Utilisation des données complètes en ${languageCode}`,
        );

        // Mise en cache globale pour cette langue
        countriesCache[languageCode] = formattedCountries;
        resolve(formattedCountries);
      } else {
        debugLog(
          "error",
          `Pas assez de pays valides: ${formattedCountries.length}/50`,
        );
        throw new Error(
          `Qualité insuffisante: ${formattedCountries.length}/50 pays`,
        );
      }
    } catch (err: any) {
      debugLog("error", "ERREUR:", err);
      debugLog("countries", "Passage en mode fallback");

      // Même le fallback va en cache pour éviter les re-fetch
      countriesCache[languageCode] = fallbackCountries;
      resolve(fallbackCountries);
    } finally {
      debugLog("countries", "Chargement terminé");
      isLoadingGlobal = false;
      // Nettoyer la promesse après utilisation
      delete loadingPromises[languageCode];
    }
  });

  return loadingPromises[languageCode];
};

// Hook pour charger les pays depuis l'API REST Countries - VERSION MULTILINGUE
export const useCountries = () => {
  const { currentLanguage } = useTranslation();
  const languageCode = getLanguageCode(currentLanguage);

  debugLog(
    "countries",
    `Hook useCountries appelé pour la langue: ${currentLanguage} (${languageCode})`,
  );

  // État initial basé sur le cache pour cette langue
  const [countries, setCountries] = useState<Country[]>(
    () => countriesCache[languageCode] || fallbackCountries,
  );
  const [loading, setLoading] = useState(() => !countriesCache[languageCode]);
  const [usingFallback, setUsingFallback] = useState(
    () => !countriesCache[languageCode],
  );

  // Références pour éviter les re-renders
  const hasFetched = useRef<Record<string, boolean>>({});
  const isMounted = useRef(true);

  // MODIFICATION : useEffect qui réagit au changement de langue
  useEffect(() => {
    // Éviter les doubles appels pour la même langue
    if (hasFetched.current[languageCode]) {
      debugLog("countries", `Fetch déjà effectué pour ${languageCode}, skip`);
      return;
    }

    hasFetched.current[languageCode] = true;
    debugLog(
      "countries",
      `DÉMARRAGE du processus de chargement des pays pour ${languageCode}`,
    );

    // Si on a déjà les données en cache pour cette langue, les utiliser immédiatement
    if (countriesCache[languageCode]) {
      debugLog(
        "countries",
        `Utilisation du cache existant pour ${languageCode}`,
      );
      setCountries(countriesCache[languageCode]);
      setUsingFallback(false);
      setLoading(false);
      return;
    }

    // Délai pour éviter les conflits avec l'hydratation
    const timer = setTimeout(async () => {
      // PROTECTION: Vérifier le montage AVANT de commencer
      if (!isMounted.current) return;

      debugLog(
        "countries",
        `Démarrage après délai de 100ms pour ${languageCode}`,
      );
      setLoading(true);
      try {
        const result = await fetchCountriesGlobal(languageCode);

        // PROTECTION: Vérifier le montage APRÈS l'opération async
        if (!isMounted.current) return;

        setCountries(result);
        setUsingFallback(result === fallbackCountries);
        setLoading(false);
      } catch (error) {
        debugLog("error", "Erreur dans le timer:", error);

        // PROTECTION: Vérifier le montage APRÈS l'erreur
        if (!isMounted.current) return;

        setCountries(fallbackCountries);
        setUsingFallback(true);
        setLoading(false);
      }
    }, 100);

    // Cleanup function
    return () => {
      clearTimeout(timer);
    };
  }, [languageCode]); // MODIFICATION : Dépendance sur languageCode pour recharger quand la langue change

  // Cleanup au démontage
  useEffect(() => {
    return () => {
      isMounted.current = false;
    };
  }, []);

  debugLog(
    "countries",
    `Render - ${countries.length} pays en ${languageCode}, loading:${loading}, fallback:${usingFallback}`,
  );

  // Mémoisation du retour pour éviter les re-renders des composants parents
  return useMemo(
    () => ({
      countries,
      loading,
      usingFallback,
    }),
    [countries, loading, usingFallback],
  );
};

// Le reste du code reste identique...
export const useCountryCodeMap = (countries: Country[]) => {
  return useMemo(() => {
    const mapping = countries.reduce(
      (acc, country) => {
        acc[country.value] = country.phoneCode;
        return acc;
      },
      {} as Record<string, string>,
    );

    debugLog(
      "countries",
      `Mapping créé avec ${Object.keys(mapping).length} entrées`,
    );

    return mapping;
  }, [countries]);
};

export const validateEmail = (email: string): boolean => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
};

export const validatePassword = (
  password: string,
): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (password.length < 8) {
    errors.push("Au moins 8 caractères");
  }
  if (!/[A-Z]/.test(password)) {
    errors.push("Une majuscule");
  }
  if (!/[0-9]/.test(password)) {
    errors.push("Un chiffre");
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
};

export const validatePhone = (
  countryCode: string,
  areaCode: string,
  phoneNumber: string,
): boolean => {
  if (!countryCode.trim() && !areaCode.trim() && !phoneNumber.trim()) {
    return true;
  }

  if (countryCode.trim() || areaCode.trim() || phoneNumber.trim()) {
    if (!countryCode.trim() || !/^\+[1-9]\d{0,3}$/.test(countryCode.trim())) {
      return false;
    }

    if (!areaCode.trim() || !/^\d{3}$/.test(areaCode.trim())) {
      return false;
    }

    if (!phoneNumber.trim() || !/^\d{7}$/.test(phoneNumber.trim())) {
      return false;
    }
  }

  return true;
};

export const validateLinkedIn = (url: string): boolean => {
  if (!url.trim()) return true;
  return /^(https?:\/\/)?(www\.)?linkedin\.com\/(in|company)\/[\w\-]+\/?$/.test(
    url,
  );
};

export const validateWebsite = (url: string): boolean => {
  if (!url.trim()) return true;
  return /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/.test(
    url,
  );
};

// ===== SECTION RememberMe Utils inchangée =====
export const rememberMeUtils = {
  STORAGE_KEY: "intelia-remember-me-persist",

  save: (email: string, rememberMe: boolean): void => {
    try {
      if (!rememberMe || !email.trim()) {
        localStorage.removeItem(rememberMeUtils.STORAGE_KEY);
        debugLog("storage", "localStorage nettoyé");
        return;
      }

      const data = {
        email: email.trim(),
        rememberMe: true,
        timestamp: Date.now(),
        version: "1.0",
      };

      localStorage.setItem(rememberMeUtils.STORAGE_KEY, JSON.stringify(data));
      debugLog("storage", "Sauvegardé:", { email: email.trim(), rememberMe });
    } catch (error) {
      debugLog("error", "Erreur sauvegarde:", error);
    }
  },

  load: (): { rememberMe: boolean; lastEmail: string } => {
    try {
      const stored = localStorage.getItem(rememberMeUtils.STORAGE_KEY);

      if (!stored) {
        debugLog("storage", "Aucune donnée stockée");
        return { rememberMe: false, lastEmail: "" };
      }

      const data = JSON.parse(stored);

      if (!data.email || typeof data.rememberMe !== "boolean") {
        debugLog("error", "Données corrompues, nettoyage");
        localStorage.removeItem(rememberMeUtils.STORAGE_KEY);
        return { rememberMe: false, lastEmail: "" };
      }

      const age = Date.now() - (data.timestamp || 0);
      const maxAge = 30 * 24 * 60 * 60 * 1000;

      if (age > maxAge) {
        debugLog("storage", "Données expirées, nettoyage");
        localStorage.removeItem(rememberMeUtils.STORAGE_KEY);
        return { rememberMe: false, lastEmail: "" };
      }

      debugLog("storage", "Données chargées:", {
        email: data.email,
        rememberMe: data.rememberMe,
        age: Math.round(age / (24 * 60 * 60 * 1000)) + " jours",
      });

      return {
        rememberMe: data.rememberMe,
        lastEmail: data.email,
      };
    } catch (error) {
      debugLog("error", "Erreur chargement:", error);
      try {
        localStorage.removeItem(rememberMeUtils.STORAGE_KEY);
      } catch (e) {
        debugLog("error", "Impossible de nettoyer localStorage:", e);
      }
      return { rememberMe: false, lastEmail: "" };
    }
  },

  clear: (): void => {
    try {
      localStorage.removeItem(rememberMeUtils.STORAGE_KEY);
      debugLog("storage", "Données nettoyées manuellement");
    } catch (error) {
      debugLog("error", "Erreur nettoyage:", error);
    }
  },

  preserveOnLogout: (): { email: string; rememberMe: boolean } | null => {
    const current = rememberMeUtils.load();
    if (current.rememberMe && current.lastEmail) {
      return {
        email: current.lastEmail,
        rememberMe: true,
      };
    }
    return null;
  },

  restoreAfterLogout: (
    preservedData: { email: string; rememberMe: boolean } | null,
  ): void => {
    if (preservedData && preservedData.rememberMe) {
      rememberMeUtils.save(preservedData.email, true);
      debugLog("storage", "Restauré après déconnexion:", preservedData.email);
    }
  },
};

export const preserveRememberMeOnLogout = () => {
  const preserved = rememberMeUtils.preserveOnLogout();

  return {
    restore: () => {
      if (preserved) {
        rememberMeUtils.restoreAfterLogout(preserved);
      }
    },
  };
};

export const logoutWithRememberMePreservation = async (
  customLogoutFn?: () => Promise<void>,
) => {
  try {
    debugLog("auth", "Début déconnexion coordonnée");

    const preservedRememberMe = rememberMeUtils.preserveOnLogout();
    debugLog("auth", "Données RememberMe préservées:", preservedRememberMe);

    debugLog("auth", "Nettoyage localStorage sélectif");

    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key !== rememberMeUtils.STORAGE_KEY) {
        if (
          key.startsWith("intelia-") ||
          key.includes("auth") ||
          key.includes("session") ||
          key.includes("supabase")
        ) {
          keysToRemove.push(key);
        }
      }
    }

    keysToRemove.forEach((key) => {
      localStorage.removeItem(key);
      debugLog("auth", `Supprimé: ${key}`);
    });

    if (customLogoutFn) {
      await customLogoutFn();
    }

    if (preservedRememberMe) {
      setTimeout(() => {
        rememberMeUtils.restoreAfterLogout(preservedRememberMe);
        debugLog("auth", "RememberMe restauré après nettoyage");
      }, 100);
    }

    debugLog("auth", "Redirection pour éviter callbacks");
    window.location.href = "/";
  } catch (error) {
    debugLog("error", "Erreur lors de la déconnexion:", error);
    window.location.href = "/";
  }
};

export { debugLog };
