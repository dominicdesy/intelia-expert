"use client";

import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  Suspense,
  useMemo,
} from "react";
import Link from "next/link";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import type { Language, User } from "@/types";

// Import des hooks et utilitaires
import {
  translations,
  validateEmail,
  validatePassword,
  validatePhone,
  rememberMeUtils,
} from "./page_hooks";

// Import des composants
import {
  InteliaLogo,
  LanguageSelector,
  AlertMessage,
  PasswordInput,
  PasswordMatchIndicator,
  LoadingSpinner,
  AuthFooter,
} from "./signup_components";

// ==================== HOOK USECOUNTRIES INTÉGRÉ ====================
const fallbackCountries = [
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

interface Country {
  value: string;
  label: string;
  phoneCode: string;
  flag?: string;
}

// Hook pour charger les pays depuis l'API REST Countries
const useCountries = () => {
  console.log("🎯 [Countries] Hook useCountries appelé!");

  const [countries, setCountries] = useState<Country[]>(fallbackCountries);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(true);

  useEffect(() => {
    console.log("🚀 [Countries] DÉMARRAGE du processus de chargement des pays");

    const fetchCountries = async () => {
      try {
        console.log(
          "🌍 [Countries] Début du chargement depuis l'API REST Countries...",
        );

        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
          console.log("⏱️ [Countries] Timeout atteint (10s)");
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
        console.log(
          `📡 [Countries] Statut HTTP: ${response.status} ${response.statusText}`,
        );

        if (!response.ok) {
          throw new Error(`API indisponible: ${response.status}`);
        }

        const data = await response.json();
        console.log(`📊 [Countries] Données reçues: ${data.length} pays bruts`);

        if (!Array.isArray(data)) {
          console.error("❌ [Countries] Format invalide - pas un array");
          throw new Error("Format de données invalide");
        }

        const formattedCountries = data
          .map((country: any, index: number) => {
            let phoneCode = "";
            if (country.idd?.root) {
              phoneCode = country.idd.root;
              if (country.idd.suffixes && country.idd.suffixes[0]) {
                phoneCode += country.idd.suffixes[0];
              }
            }

            const formatted = {
              value: country.cca2,
              label:
                country.translations?.fra?.common ||
                country.name?.common ||
                country.cca2,
              phoneCode: phoneCode,
              flag: country.flag || "",
            };

            return formatted;
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
          .sort((a: Country, b: Country) =>
            a.label.localeCompare(b.label, "fr", { numeric: true }),
          );

        console.log(
          `✅ [Countries] Pays valides après filtrage: ${formattedCountries.length}`,
        );

        if (formattedCountries.length >= 50) {
          console.log(
            "🎉 [Countries] API validée! Utilisation des données complètes",
          );
          setCountries(formattedCountries);
          setUsingFallback(false);
        } else {
          console.warn(
            `⚠️ [Countries] Pas assez de pays valides: ${formattedCountries.length}/50`,
          );
          throw new Error(
            `Qualité insuffisante: ${formattedCountries.length}/50 pays`,
          );
        }
      } catch (err: any) {
        console.error("💥 [Countries] ERREUR:", err);
        console.warn("🔄 [Countries] Passage en mode fallback");
        setCountries(fallbackCountries);
        setUsingFallback(true);
      } finally {
        console.log("🏁 [Countries] Chargement terminé");
        setLoading(false);
      }
    };

    const timer = setTimeout(() => {
      console.log("⏰ [Countries] Démarrage après délai de 100ms");
      fetchCountries();
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  return { countries, loading, usingFallback };
};

// Hook pour créer le mapping des codes téléphoniques
const useCountryCodeMap = (countries: Country[]) => {
  return useMemo(() => {
    const mapping = countries.reduce(
      (acc, country) => {
        acc[country.value] = country.phoneCode;
        return acc;
      },
      {} as Record<string, string>,
    );

    console.log(
      `🗺️ [CountryCodeMap] Mapping créé avec ${Object.keys(mapping).length} entrées`,
    );
    return mapping;
  }, [countries]);
};

// Contenu principal de la page
function PageContent() {
  console.log("🚀 [PageContent] Composant PageContent rendu");

  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const { user, isAuthenticated, isLoading, hasHydrated } = useAuthStore();
  const { login, register, initializeSession } = useAuthStore();

  // ⭐ HOOK APPELÉ IMMÉDIATEMENT - PAS DE CONDITION
  console.log("🎯 [PageContent] Appel du hook useCountries...");
  const {
    countries,
    loading: countriesLoading,
    usingFallback,
  } = useCountries();
  console.log("📊 [PageContent] Hook useCountries retourné:", {
    countriesLength: countries.length,
    loading: countriesLoading,
    usingFallback,
  });

  // Créer le mapping des codes téléphoniques dynamiquement
  const countryCodeMap = useCountryCodeMap(countries);

  // Refs pour éviter les doubles appels
  const hasInitialized = useRef(false);
  const hasCheckedAuth = useRef(false);
  const redirectLock = useRef(false);
  const sessionInitialized = useRef(false);

  const [currentLanguage, setCurrentLanguage] = useState<Language>("fr");
  const t = useMemo(() => translations[currentLanguage], [currentLanguage]);

  const [isSignupMode, setIsSignupMode] = useState(false); // ⭐ COMMENCER EN MODE LOGIN
  const [localError, setLocalError] = useState("");
  const [localSuccess, setLocalSuccess] = useState("");

  const [loginData, setLoginData] = useState({
    email: "",
    password: "",
    rememberMe: false,
  });

  const [signupData, setSignupData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    firstName: "",
    lastName: "",
    linkedinProfile: "",
    country: "",
    countryCode: "",
    areaCode: "",
    phoneNumber: "",
    companyName: "",
    companyWebsite: "",
    companyLinkedin: "",
  });

  const safeRedirectToChat = useCallback(() => {
    if (redirectLock.current) {
      console.log("🔒 [Redirect] Redirection déjà en cours, skip");
      return;
    }

    redirectLock.current = true;
    console.log("🚀 [Redirect] Redirection vers /chat...");

    try {
      router.push("/chat");
    } catch (error) {
      console.error("❌ [Redirect] Erreur redirection:", error);
      redirectLock.current = false;
    }
  }, [router]);

  // Gestion des changements de formulaires
  const handleLoginChange = (
    field: keyof typeof loginData,
    value: string | boolean,
  ) => {
    setLoginData((prev) => ({ ...prev, [field]: value }));
    setLocalError("");
  };

  const handleSignupChange = (
    field: keyof typeof signupData,
    value: string,
  ) => {
    setSignupData((prev) => {
      const newData = { ...prev, [field]: value };

      // Auto-remplir l'indicatif pays quand le pays change
      if (field === "country" && value && countryCodeMap[value]) {
        console.log(
          "🏳️ [Country] Auto-remplissage code pays:",
          value,
          "->",
          countryCodeMap[value],
        );
        newData.countryCode = countryCodeMap[value];
      }

      return newData;
    });
    setLocalError("");
  };

  const validateSignupForm = (): string | null => {
    if (!signupData.email) return t.emailRequired;
    if (!validateEmail(signupData.email)) return t.emailInvalid;
    if (!signupData.password) return t.passwordRequired;

    const passwordValidation = validatePassword(signupData.password);
    if (!passwordValidation.isValid) {
      return t.passwordTooShort;
    }

    if (signupData.password !== signupData.confirmPassword)
      return t.passwordMismatch;
    if (!signupData.firstName.trim()) return t.firstNameRequired;
    if (!signupData.lastName.trim()) return t.lastNameRequired;
    if (!signupData.country) return t.countryRequired;

    if (
      !validatePhone(
        signupData.countryCode,
        signupData.areaCode,
        signupData.phoneNumber,
      )
    ) {
      return t.phoneInvalid;
    }

    return null;
  };

  // Gestion de la connexion
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError("");
    setLocalSuccess("");

    if (!loginData.email) {
      setLocalError(t.emailRequired);
      return;
    }

    if (!validateEmail(loginData.email)) {
      setLocalError(t.emailInvalid);
      return;
    }

    if (!loginData.password) {
      setLocalError(t.passwordRequired);
      return;
    }

    try {
      console.log("🔐 [Login] Tentative connexion...");

      await login(loginData.email, loginData.password);

      // Sauvegarder remember me
      rememberMeUtils.save(loginData.email, loginData.rememberMe);

      setLocalSuccess(t.authSuccess);
      console.log("✅ [Login] Connexion réussie");

      // Redirection automatique après succès
      setTimeout(() => {
        safeRedirectToChat();
      }, 1000);
    } catch (error: any) {
      console.error("❌ [Login] Erreur connexion:", error);
      setLocalError(error?.message || t.authError);
    }
  };

  // Gestion de l'inscription
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError("");
    setLocalSuccess("");

    const validationError = validateSignupForm();
    if (validationError) {
      setLocalError(validationError);
      return;
    }

    try {
      console.log("🔐 [Signup] Tentative création compte...");

      const userData = {
        email: signupData.email,
        firstName: signupData.firstName,
        lastName: signupData.lastName,
        linkedinProfile: signupData.linkedinProfile,
        country: signupData.country,
        countryCode: signupData.countryCode,
        areaCode: signupData.areaCode,
        phoneNumber: signupData.phoneNumber,
        companyName: signupData.companyName,
        companyWebsite: signupData.companyWebsite,
        companyLinkedin: signupData.companyLinkedin,
      };

      await register(signupData.email, signupData.password, userData);

      setLocalSuccess(t.accountCreated);
      console.log("✅ [Signup] Création compte réussie");

      // Retour au mode login après création
      setTimeout(() => {
        setIsSignupMode(false);
        setLoginData((prev) => ({ ...prev, email: signupData.email }));
      }, 2000);
    } catch (error: any) {
      console.error("❌ [Signup] Erreur création compte:", error);
      setLocalError(error?.message || t.signupError);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      if (isSignupMode) {
        handleSignup(e as any);
      } else {
        handleLogin(e as any);
      }
    }
  };

  const toggleMode = () => {
    console.log(
      "🔄 [UI] Basculement mode:",
      isSignupMode ? "signup → login" : "login → signup",
    );
    setIsSignupMode(!isSignupMode);
    setLocalError("");
    setLocalSuccess("");
  };

  // Effects d'initialisation
  useEffect(() => {
    if (!hasInitialized.current) {
      hasInitialized.current = true;
      console.log("🎯 [Init] Initialisation unique");

      // Charger remember me
      const { rememberMe, lastEmail } = rememberMeUtils.load();
      if (rememberMe && lastEmail) {
        setLoginData((prev) => ({
          ...prev,
          email: lastEmail,
          rememberMe: true,
        }));
      }
    }
  }, []);

  useEffect(() => {
    if (!hasHydrated) return;

    if (!sessionInitialized.current) {
      sessionInitialized.current = true;
      console.log("🔐 [Session] Initialisation unique de la session");
      initializeSession();
    }
  }, [hasHydrated, initializeSession]);

  useEffect(() => {
    if (!hasHydrated) return;

    if (!hasCheckedAuth.current && !isLoading) {
      hasCheckedAuth.current = true;
      console.log("🔐 [Auth] Vérification unique de l'authentification");

      if (isAuthenticated && user) {
        console.log("✅ [Auth] Utilisateur connecté, redirection...");
        safeRedirectToChat();
      } else {
        console.log("❌ [Auth] Utilisateur non connecté");
      }
    }
  }, [hasHydrated, isLoading, isAuthenticated, user, safeRedirectToChat]);

  // 🔒 EFFET POUR BLOQUER LE SCROLL HTML + BODY EN MODE SIGNUP (CORRIGÉ)
  useEffect(() => {
    if (isSignupMode) {
      // Bloquer le scroll du body ET du html
      document.body.style.overflow = "hidden";
      document.documentElement.style.overflow = "hidden";
    } else {
      // Restaurer le scroll du body ET du html
      document.body.style.overflow = "unset";
      document.documentElement.style.overflow = "unset";
    }

    // Cleanup au démontage
    return () => {
      document.body.style.overflow = "unset";
      document.documentElement.style.overflow = "unset";
    };
  }, [isSignupMode]);

  // Affichage loading pendant l'hydratation
  if (!hasHydrated || isLoading) {
    console.log("⏳ [Render] Affichage du spinner de chargement");
    return <LoadingSpinner />;
  }

  console.log("🎨 [Render] Rendu de la page principale");

  return (
    <>
      {/* PAGE PRINCIPALE (LOGIN) */}
      <div
        className={`min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 relative ${isSignupMode ? "overflow-hidden" : ""}`}
      >
        {/* ⭐ BOÎTE DE DEBUG GLOBALE - RETIRÉE EN PRODUCTION */}
        {process.env.NODE_ENV === "development" && (
          <div className="fixed top-16 right-4 bg-purple-50 border border-purple-200 rounded-lg p-4 text-xs max-w-sm z-50">
            <div className="font-semibold text-purple-800 mb-2">
              🧪 Debug Global
            </div>
            <div className="space-y-1 text-purple-700">
              <div>
                🎭 Mode:{" "}
                <span className="font-mono bg-purple-100 px-1 rounded">
                  {isSignupMode ? "Modal" : "Page"}
                </span>
              </div>
              <div>
                📊 Pays:{" "}
                <span className="font-mono bg-purple-100 px-1 rounded">
                  {countries.length}
                </span>
              </div>
              <div>
                ⏳ Loading:{" "}
                <span className="font-mono bg-purple-100 px-1 rounded">
                  {countriesLoading ? "Oui" : "Non"}
                </span>
              </div>
              <div>
                🔄 Fallback:{" "}
                <span className="font-mono bg-purple-100 px-1 rounded">
                  {usingFallback ? "Oui" : "Non"}
                </span>
              </div>
            </div>
            <button
              onClick={toggleMode}
              className="mt-2 text-xs bg-purple-100 hover:bg-purple-200 px-2 py-1 rounded"
            >
              {isSignupMode ? "Fermer Modal" : "Ouvrir Modal"}
            </button>
          </div>
        )}

        <div className="absolute top-4 right-4">
          <LanguageSelector
            onLanguageChange={setCurrentLanguage}
            currentLanguage={currentLanguage}
          />
        </div>

        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="flex justify-center">
            <InteliaLogo className="w-16 h-16" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            {t.title}
          </h2>
        </div>

        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10">
            {/* Messages d'erreur et succès pour login */}
            {localError && !isSignupMode && (
              <AlertMessage
                type="error"
                title={t.loginError}
                message={localError}
              />
            )}

            {localSuccess && !isSignupMode && (
              <AlertMessage type="success" title="" message={localSuccess} />
            )}

            {/* FORMULAIRE DE CONNEXION */}
            <form onSubmit={handleLogin} onKeyPress={handleKeyPress}>
              <div className="space-y-6">
                <div>
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-gray-700"
                  >
                    {t.email}
                  </label>
                  <div className="mt-1">
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={loginData.email}
                      onChange={(e) =>
                        handleLoginChange("email", e.target.value)
                      }
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="password"
                    className="block text-sm font-medium text-gray-700"
                  >
                    {t.password}
                  </label>
                  <div className="mt-1">
                    <PasswordInput
                      id="password"
                      name="password"
                      value={loginData.password}
                      onChange={(e) =>
                        handleLoginChange("password", e.target.value)
                      }
                      autoComplete="current-password"
                      required
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <input
                      id="remember-me"
                      name="remember-me"
                      type="checkbox"
                      checked={loginData.rememberMe}
                      onChange={(e) =>
                        handleLoginChange("rememberMe", e.target.checked)
                      }
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <label
                      htmlFor="remember-me"
                      className="ml-2 block text-sm text-gray-900"
                    >
                      {t.rememberMe}
                    </label>
                  </div>

                  <div className="text-sm">
                    <Link
                      href="/forgot-password"
                      className="font-medium text-blue-600 hover:text-blue-500"
                    >
                      {t.forgotPassword}
                    </Link>
                  </div>
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="flex w-full justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? t.connecting : t.login}
                  </button>
                </div>
              </div>
            </form>

            {/* Bouton pour ouvrir la modale d'inscription */}
            <div className="mt-6 text-center">
              <p className="text-sm text-gray-600">
                {t.newToIntelia}{" "}
                <button
                  onClick={toggleMode}
                  className="font-medium text-blue-600 hover:text-blue-500"
                >
                  {t.createAccount}
                </button>
              </p>
            </div>

            {/* Footer */}
            <AuthFooter t={t} />
          </div>
        </div>
      </div>

      {/* 🔧 MODAL D'INSCRIPTION - VERSION CORRIGÉE SANS DOUBLE SCROLL */}
      {isSignupMode && (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-50 p-4 overflow-hidden overscroll-none">
          <div className="w-full max-w-2xl mx-auto bg-white rounded-lg shadow-xl max-h-[calc(100vh-2rem)] overflow-y-auto overscroll-contain">
            {/* Header de la modale avec bouton fermer */}
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-lg">
              <h3 className="text-lg font-semibold text-gray-900">
                {t.createAccount}
              </h3>
              <button
                onClick={toggleMode}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {/* Corps de la modale - OVERFLOW SUPPRIMÉ */}
            <div className="flex-1 px-6 py-4">
              {/* Messages d'erreur et succès pour signup */}
              {localError && (
                <AlertMessage
                  type="error"
                  title={t.signupError}
                  message={localError}
                />
              )}

              {localSuccess && (
                <AlertMessage type="success" title="" message={localSuccess} />
              )}

              {/* FORMULAIRE D'INSCRIPTION */}
              <form onSubmit={handleSignup} onKeyPress={handleKeyPress}>
                <div className="space-y-6">
                  {/* Section Informations personnelles */}
                  <div className="border-b border-gray-200 pb-6">
                    <h4 className="text-md font-medium text-gray-900 mb-4">
                      {t.personalInfo}
                    </h4>

                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                      <div>
                        <label className="block text-sm font-medium text-gray-700">
                          {t.firstName}{" "}
                          <span className="text-red-500">{t.required}</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={signupData.firstName}
                          onChange={(e) =>
                            handleSignupChange("firstName", e.target.value)
                          }
                          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700">
                          {t.lastName}{" "}
                          <span className="text-red-500">{t.required}</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={signupData.lastName}
                          onChange={(e) =>
                            handleSignupChange("lastName", e.target.value)
                          }
                          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        />
                      </div>
                    </div>

                    <div className="mt-4">
                      <label className="block text-sm font-medium text-gray-700">
                        {t.linkedinProfile} {t.optional}
                      </label>
                      <input
                        type="url"
                        value={signupData.linkedinProfile}
                        onChange={(e) =>
                          handleSignupChange("linkedinProfile", e.target.value)
                        }
                        placeholder="https://linkedin.com/in/votre-profil"
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                    </div>
                  </div>

                  {/* Section Contact */}
                  <div className="border-b border-gray-200 pb-6">
                    <h4 className="text-md font-medium text-gray-900 mb-4">
                      {t.contact}
                    </h4>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        {t.email}{" "}
                        <span className="text-red-500">{t.required}</span>
                      </label>
                      <input
                        type="email"
                        required
                        value={signupData.email}
                        onChange={(e) =>
                          handleSignupChange("email", e.target.value)
                        }
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                    </div>

                    {/* Sélecteur de pays */}
                    <div className="mt-4">
                      <label className="block text-sm font-medium text-gray-700">
                        {t.country}{" "}
                        <span className="text-red-500">{t.required}</span>
                      </label>

                      {countriesLoading ? (
                        <div className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 bg-gray-50">
                          <div className="flex items-center space-x-2">
                            <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                            <span className="text-sm text-gray-600">
                              {t.loadingCountries}
                            </span>
                          </div>
                        </div>
                      ) : (
                        <select
                          required
                          value={signupData.country}
                          onChange={(e) =>
                            handleSignupChange("country", e.target.value)
                          }
                          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 bg-white shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                        >
                          <option value="">{t.selectCountry}</option>
                          {countries.map((country) => (
                            <option key={country.value} value={country.value}>
                              {country.flag ? `${country.flag} ` : ""}
                              {country.label} ({country.phoneCode})
                            </option>
                          ))}
                        </select>
                      )}
                    </div>

                    {/* Téléphone optionnel */}
                    <div className="mt-4">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {t.phoneNumber} {t.optional}
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">
                            {t.countryCode}
                          </label>
                          <input
                            type="text"
                            placeholder="+1"
                            value={signupData.countryCode}
                            onChange={(e) =>
                              handleSignupChange("countryCode", e.target.value)
                            }
                            className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">
                            {t.areaCode}
                          </label>
                          <input
                            type="text"
                            placeholder="514"
                            value={signupData.areaCode}
                            onChange={(e) =>
                              handleSignupChange("areaCode", e.target.value)
                            }
                            className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">
                            {t.phoneNumber}
                          </label>
                          <input
                            type="text"
                            placeholder="1234567"
                            value={signupData.phoneNumber}
                            onChange={(e) =>
                              handleSignupChange("phoneNumber", e.target.value)
                            }
                            className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Section Entreprise */}
                  <div className="border-b border-gray-200 pb-6">
                    <h4 className="text-md font-medium text-gray-900 mb-4">
                      {t.company}
                    </h4>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        {t.companyName} {t.optional}
                      </label>
                      <input
                        type="text"
                        value={signupData.companyName}
                        onChange={(e) =>
                          handleSignupChange("companyName", e.target.value)
                        }
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                    </div>

                    <div className="mt-4">
                      <label className="block text-sm font-medium text-gray-700">
                        {t.companyWebsite} {t.optional}
                      </label>
                      <input
                        type="url"
                        value={signupData.companyWebsite}
                        onChange={(e) =>
                          handleSignupChange("companyWebsite", e.target.value)
                        }
                        placeholder="https://votre-entreprise.com"
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                    </div>

                    <div className="mt-4">
                      <label className="block text-sm font-medium text-gray-700">
                        {t.companyLinkedin} {t.optional}
                      </label>
                      <input
                        type="url"
                        value={signupData.companyLinkedin}
                        onChange={(e) =>
                          handleSignupChange("companyLinkedin", e.target.value)
                        }
                        placeholder="https://linkedin.com/company/votre-entreprise"
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                      />
                    </div>
                  </div>

                  {/* Section Mot de passe */}
                  <div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        {t.password}{" "}
                        <span className="text-red-500">{t.required}</span>
                      </label>
                      <div className="mt-1">
                        <PasswordInput
                          value={signupData.password}
                          onChange={(e) =>
                            handleSignupChange("password", e.target.value)
                          }
                          required
                        />
                      </div>
                    </div>

                    <div className="mt-4">
                      <label className="block text-sm font-medium text-gray-700">
                        {t.confirmPassword}{" "}
                        <span className="text-red-500">{t.required}</span>
                      </label>
                      <div className="mt-1">
                        <PasswordInput
                          value={signupData.confirmPassword}
                          onChange={(e) =>
                            handleSignupChange(
                              "confirmPassword",
                              e.target.value,
                            )
                          }
                          required
                        />
                      </div>
                    </div>

                    {/* Indicateur de correspondance des mots de passe */}
                    <PasswordMatchIndicator
                      password={signupData.password}
                      confirmPassword={signupData.confirmPassword}
                    />
                  </div>
                </div>
              </form>
            </div>

            {/* Footer de la modale avec boutons */}
            <div className="flex-shrink-0 bg-gray-50 border-t border-gray-200 px-6 py-4 rounded-b-lg">
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={toggleMode}
                  className="flex-1 rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  {t.backToLogin}
                </button>
                <button
                  onClick={handleSignup}
                  disabled={isLoading}
                  className="flex-1 rounded-md border border-transparent bg-green-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? t.creating : t.createAccount}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// Export principal avec Suspense
export default function Page() {
  console.log("🎁 [Page] Composant Page principal appelé");
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <PageContent />
    </Suspense>
  );
}
