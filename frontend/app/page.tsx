"use client";
// Build: 1.0.0.9 - FINAL FIX: React hooks order + hydration warnings resolved

import React, { useState, Suspense, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslation } from "@/lib/languages/i18n";
import { useAuthStore } from "@/lib/stores/auth"; // Store unifié
import { usePasskey } from "@/lib/hooks/usePasskey";
import { availableLanguages } from "../lib/languages/config";
import { rememberMeUtils } from "./page_hooks";
import { SignupModal } from "./page_signup_modal";

// Logo Intelia dans un carré avec bordure bleue
const InteliaLogo = ({ className = "w-20 h-20" }: { className?: string }) => (
  <div
    className={`${className} bg-white border-2 border-blue-100 rounded-2xl shadow-lg flex items-center justify-center p-3`}
  >
    <img
      src="/images/logo.png"
      alt="Intelia Logo"
      className="w-full h-full object-contain"
    />
  </div>
);

// Sélecteur de langue moderne
const LanguageSelector = () => {
  const { changeLanguage, currentLanguage } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  const currentLang =
    availableLanguages.find((lang) => lang.code === currentLanguage) ||
    availableLanguages[0];

  const handleLanguageChange = (langCode: string) => {
    changeLanguage(langCode);
    setIsOpen(false);
  };

  return (
    <div className="relative language-selector">
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className="flex items-center space-x-2 px-4 py-2.5 text-sm bg-white border border-blue-200 rounded-xl shadow-sm hover:bg-blue-50 transition-all duration-300 text-blue-700 relative z-[10000]"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span>{currentLang.flag}</span>
        <span>{currentLang.nativeName}</span>
        <svg
          className={`w-4 h-4 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-[9999]"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full right-0 mt-1 w-48 bg-white border border-blue-200 rounded-xl shadow-xl z-[10001] max-h-64 overflow-y-auto">
            {availableLanguages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => handleLanguageChange(lang.code)}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-blue-50 flex items-center space-x-3 transition-colors duration-150 ${
                  lang.code === currentLanguage
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-700"
                } first:rounded-t-xl last:rounded-b-xl`}
                role="option"
                aria-selected={lang.code === currentLanguage}
              >
                <span className="text-xl">{lang.flag}</span>
                <div className="flex-1">
                  <div className="font-medium">{lang.nativeName}</div>
                </div>
                {lang.code === currentLanguage && (
                  <svg
                    className="w-4 h-4 text-blue-600"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

// Composant qui gère useSearchParams dans Suspense
function AuthCallbackHandler() {
  const searchParams = useSearchParams();
  const { t } = useTranslation();
  const [authMessage, setAuthMessage] = useState("");
  const isMountedRef = React.useRef(true);

  // Cleanup au démontage
  React.useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  React.useEffect(() => {
    const authStatus = searchParams?.get("auth");
    if (!authStatus) return;

    if (authStatus === "success") {
      setAuthMessage(t("auth.success"));
    } else if (authStatus === "error") {
      setAuthMessage(t("auth.error"));
    } else if (authStatus === "incomplete") {
      setAuthMessage(t("auth.incomplete"));
    }

    // Nettoyer l'URL
    try {
      const url = new URL(window.location.href);
      url.searchParams.delete("auth");
      window.history.replaceState({}, "", url.pathname);
    } catch (error) {
      console.error("Erreur nettoyage URL:", error);
    }

    const timeoutId = setTimeout(() => {
      // PROTECTION: Vérifier que le composant est toujours monté avant setState
      if (!isMountedRef.current) return;
      setAuthMessage("");
    }, 3000);

    return () => clearTimeout(timeoutId);
  }, [searchParams, t]);

  if (authMessage) {
    return (
      <div className="mb-4 p-3 bg-blue-50 border border-blue-200 text-blue-700 rounded-xl text-sm">
        {authMessage}
      </div>
    );
  }

  return null;
}

// PAGE LOGIN COMPLÈTE - VERSION UNIFIÉE
function LoginPageContent() {
  const router = useRouter();
  const { t, currentLanguage, loading: translationsLoading } = useTranslation();
  const { login, register, loginWithOAuth, isOAuthLoading, checkAuth, isAuthenticated, startSessionTracking } = useAuthStore(); // Store unifié avec OAuth
  const isMountedRef = React.useRef(true); // Protection démontage

  // Cleanup au démontage
  React.useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // États simples
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showSignup, setShowSignup] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Passkey authentication
  const {
    isSupported: isPasskeySupported,
    isLoading: isPasskeyLoading,
    authenticateWithPasskey,
  } = usePasskey();

  // Détection mobile
  useEffect(() => {
    const detectMobile = () => {
      const userAgent = navigator.userAgent.toLowerCase();
      const isMobileUA = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
      const isSmallScreen = window.innerWidth <= 768;
      const hasTouchScreen = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      const isIPadOS = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;

      return (isMobileUA || isIPadOS || (isSmallScreen && hasTouchScreen));
    };

    setIsMobile(detectMobile());

    const handleResize = () => {
      setIsMobile(detectMobile());
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // États pour le signup - DOIVENT être AVANT tout return conditionnel
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
    productionType: [] as string[],
    category: "",
    categoryOther: "",
  });

  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Chargement du rememberMe au démarrage
  // IMPORTANT: Tous les hooks DOIVENT être AVANT tout return conditionnel (règle des hooks)
  useEffect(() => {
    const savedData = rememberMeUtils.load();
    if (savedData.rememberMe && savedData.lastEmail) {
      setEmail(savedData.lastEmail);
      setRememberMe(true);
    }
  }, []); // Pas besoin de protection ici car opération synchrone

  // Afficher un état de chargement pendant que les traductions chargent
  if (translationsLoading) {
    return <LoadingFallback />;
  }

  // Fonctions de validation
  const validatePassword = (password: string) => {
    const errors = [];
    if (password.length < 8) errors.push(t("validation.password.minLength"));
    if (!/[A-Z]/.test(password))
      errors.push(t("validation.password.uppercase"));
    if (!/[a-z]/.test(password))
      errors.push(t("validation.password.lowercase"));
    if (!/[0-9]/.test(password)) errors.push(t("validation.password.number"));
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password))
      errors.push(t("validation.password.special"));
    return { isValid: errors.length === 0, errors };
  };

  const validatePhone = (
    countryCode: string,
    areaCode: string,
    phoneNumber: string,
  ) => {
    return (
      countryCode &&
      areaCode &&
      phoneNumber &&
      areaCode.length >= 2 &&
      phoneNumber.length >= 6
    );
  };

  // Gestion des changements du formulaire signup
  const handleSignupChange = (field: string, value: string | string[]) => {
    setSignupData((prev) => ({ ...prev, [field]: value }));
  };

  // FONCTION OAUTH LOGIN - Utilise le nouveau store
  const handleOAuthLogin = async (provider: "linkedin" | "facebook") => {
    console.log(`[OAuth] Début de connexion ${provider}`);

    setError("");

    try {
      // Utilise la nouvelle méthode du store
      await loginWithOAuth(provider);

      console.log(
        `[OAuth] Connexion ${provider} initiée - redirection en cours...`,
      );
      // La redirection se fera automatiquement vers le provider OAuth
    } catch (error: any) {
      console.error(`[OAuth] Erreur connexion ${provider}:`, error);

      if (error.message?.includes("OAuth")) {
        setError(t("auth.oauthError") || "Erreur de connexion OAuth");
      } else {
        setError(error.message || t("auth.error") || "Erreur de connexion");
      }
    }
  };

  // FONCTION SIGNUP UNIFIÉE - utilise le store au lieu de fetch direct
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log("[Signup] Utilisation du store unifié:", {
      email: signupData.email,
      firstName: signupData.firstName,
      lastName: signupData.lastName,
      country: signupData.country,
      // Données sensibles masquées pour sécurité
      password: "***",
      confirmPassword: "***",
    });

    setIsLoading(true);
    setError("");

    try {
      // Validation côté client
      if (
        !signupData.email ||
        !signupData.password ||
        !signupData.firstName ||
        !signupData.lastName
      ) {
        throw new Error(
          t("validation.correctErrors") || "Veuillez corriger les erreurs",
        );
      }

      if (signupData.password !== signupData.confirmPassword) {
        throw new Error(
          t("validation.password.mismatch") ||
            "Les mots de passe ne correspondent pas",
        );
      }

      // Validation du mot de passe
      const passwordValidation = validatePassword(signupData.password);
      if (!passwordValidation.isValid) {
        throw new Error(passwordValidation.errors[0]);
      }

      // UTILISATION DU STORE UNIFIÉ au lieu de fetch direct
      const userData = {
        name: `${signupData.firstName} ${signupData.lastName}`,
        firstName: signupData.firstName,
        lastName: signupData.lastName,
        country: signupData.country, // AJOUTÉ: pays de l'utilisateur
        companyName: signupData.companyName,
        phone:
          signupData.countryCode &&
          signupData.areaCode &&
          signupData.phoneNumber
            ? `${signupData.countryCode}${signupData.areaCode}${signupData.phoneNumber}`
            : undefined,
        preferredLanguage: currentLanguage, // Passer la langue actuelle du frontend
        production_type: signupData.productionType.length > 0 ? signupData.productionType : null,
        category: signupData.category || null,
        category_other: signupData.category === 'other' ? signupData.categoryOther : null,
      };

      console.log("[Signup] Langue envoyée au backend:", currentLanguage);

      await register(signupData.email, signupData.password, userData);

      setSuccess(
        t("verification.pending.emailSent") || "Compte créé avec succès!",
      );

      // Fermer la modal après succès
      const timeoutId = setTimeout(() => {
        // PROTECTION: Vérifier que le composant est toujours monté
        if (!isMountedRef.current) return;
        setShowSignup(false);
        setSuccess("");
      }, 2000);

      return {
        success: true,
        message:
          t("verification.pending.emailSent") || "Compte créé avec succès!",
      };
    } catch (error: any) {
      console.error("[Signup] Erreur store unifié:", error);

      let errorMessage =
        error.message || t("error.generic") || "Erreur générique";

      if (
        errorMessage.includes("already registered") ||
        errorMessage.includes("already exists") ||
        errorMessage.includes("User already exists")
      ) {
        errorMessage =
          t("auth.emailAlreadyExists") ||
          "Cette adresse email est déjà utilisée";
      } else if (
        errorMessage.includes("Password") ||
        errorMessage.includes("password")
      ) {
        errorMessage =
          t("auth.passwordRequirementsNotMet") ||
          "Le mot de passe ne respecte pas les critères requis";
      } else if (
        errorMessage.includes("Invalid email") ||
        errorMessage.includes("email")
      ) {
        errorMessage = t("error.emailInvalid") || "Adresse email invalide";
      }

      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Logique d'authentification pour la SignupModal
  const authLogic = {
    signupData,
    showPassword,
    setShowPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    isLoading,
    handleSignupChange,
    handleSignup,
    validatePassword,
    validatePhone,
  };

  // FONCTION DE CONNEXION - améliorée avec gestion d'erreurs harmonisée
  const handleLogin = async () => {
    setError("");
    setSuccess("");

    if (!email.trim()) {
      setError(t("error.emailRequired") || "L'adresse email est requise");
      return;
    }

    if (!password) {
      setError(
        t("validation.required.password") || "Le mot de passe est requis",
      );
      return;
    }

    setIsLoading(true);

    try {
      // Utilise le store unifié
      await login(email.trim(), password);

      // Sauvegarde du rememberMe après succès
      rememberMeUtils.save(email.trim(), rememberMe);

      setSuccess(t("auth.success") || "Connexion réussie");

      const timeoutId = setTimeout(() => {
        // PROTECTION: Vérifier que le composant est toujours monté
        if (!isMountedRef.current) return;
        router.push("/chat");
      }, 1000);
    } catch (error: any) {
      console.error("[Login] Erreur de connexion:", error);

      // Gestion d'erreurs harmonisée avec les autres composants
      let errorMessage =
        error.message || t("auth.error") || "Erreur de connexion";

      // Messages d'erreur spécifiques selon le type d'erreur
      if (
        errorMessage.includes("Email ou mot de passe incorrect") ||
        errorMessage.includes("Invalid login credentials") ||
        errorMessage.includes("credentials") ||
        errorMessage.includes("incorrect")
      ) {
        setError(
          t("auth.invalidCredentials") || "Email ou mot de passe incorrect",
        );
      } else if (
        errorMessage.includes("Email non confirmé") ||
        errorMessage.includes("Email not confirmed") ||
        errorMessage.includes("verify") ||
        errorMessage.includes("confirmer")
      ) {
        setError(
          t("auth.emailNotConfirmed") ||
            "Email non confirmé. Vérifiez votre boîte mail.",
        );
      } else if (
        errorMessage.includes("Trop de tentatives") ||
        errorMessage.includes("rate limit") ||
        errorMessage.includes("too many")
      ) {
        setError(
          "Trop de tentatives de connexion. Veuillez réessayer dans quelques minutes.",
        );
      } else if (
        errorMessage.includes("connexion réseau") ||
        errorMessage.includes("network") ||
        errorMessage.includes("impossible de contacter")
      ) {
        setError(
          "Problème de connexion réseau. Vérifiez votre connexion internet.",
        );
      } else if (
        errorMessage.includes("serveur") ||
        errorMessage.includes("server") ||
        errorMessage.includes("500")
      ) {
        setError(t("error.serverError") || "Erreur technique du serveur. Veuillez réessayer.");
      } else {
        setError(errorMessage);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Gérer la touche Entrée pour soumettre le formulaire
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !isLoading && !isOAuthLoading) {
      handleLogin();
    }
  };

  // Handle passkey authentication
  const handlePasskeyLogin = async () => {
    setError("");
    setSuccess("");

    try {
      const result = await authenticateWithPasskey();

      // Backend now returns TokenResponse: {access_token, token_type, expires_at}
      if (result.access_token) {
        // Store token in localStorage (same as regular login)
        const authData = {
          access_token: result.access_token,
          token_type: result.token_type || "bearer",
          expires_at: result.expires_at,
          synced_at: Date.now(),
        };
        localStorage.setItem("intelia-expert-auth", JSON.stringify(authData));

        // Check auth to load user data
        await checkAuth();

        // Start session tracking if authenticated
        if (isAuthenticated) {
          startSessionTracking();
        }

        setSuccess(t("auth.success") || "Authenticated successfully!");
        setTimeout(() => {
          if (!isMountedRef.current) return;
          router.push("/chat");
        }, 1000);
      } else {
        setError(t("error.noTokenReceived") || "Authentication failed: No token received");
      }
    } catch (err: any) {
      const errorMessage = err.message || t("auth.error") || "Authentication failed";
      setError(errorMessage);
    }
  };

  return (
    <div
      className="min-h-screen relative bg-white overflow-y-auto overflow-x-hidden"
      style={{
        WebkitOverflowScrolling: 'touch',
        overscrollBehavior: 'contain',
        height: '100dvh',
        maxHeight: '100dvh'
      }}
    >
      {/* Background avec lignes de démarcation bleues */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Formes géométriques bleues subtiles */}
        <div className="absolute top-20 left-20 w-32 h-32 bg-blue-100/30 rounded-full blur-xl"></div>
      </div>

      {/* Sélecteur de langue */}
      <div className="absolute top-6 right-6 z-[10000]">
        <LanguageSelector />
      </div>

      {/* Contenu principal */}
      <div className="relative z-10 flex flex-col justify-center items-center min-h-full px-4 sm:px-6 lg:px-8 py-8">
        <div className="w-full max-w-md">
          {/* Header avec logo */}
          <div className={isMobile ? 'text-left mb-8' : 'text-center mb-8'}>
            <div className={`flex mb-6 ${isMobile ? 'justify-start' : 'justify-center'}`}>
              <InteliaLogo className="w-16 h-16" />
            </div>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">
              {t("page.title")}
            </h1>
            <p className="text-gray-600 text-lg">{t("app.description")}</p>
          </div>

          {/* Card principale avec bordures bleues */}
          <div className="bg-white border-2 border-blue-100 rounded-3xl shadow-xl p-8 relative overflow-hidden">
            {/* Callback d'auth dans Suspense */}
            <Suspense fallback={null}>
              <AuthCallbackHandler />
            </Suspense>

            {/* Messages d'erreur */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">
                {error}
              </div>
            )}

            {/* Messages de succès */}
            {success && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-xl text-sm">
                {success}
              </div>
            )}

            <div className="space-y-6 relative z-10">
              {/* Email */}
              <div className="space-y-2">
                <label
                  htmlFor="email"
                  className="block text-sm font-medium text-gray-700"
                >
                  {t("login.emailLabel")}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg
                      className="h-5 w-5 text-blue-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207"
                      />
                    </svg>
                  </div>
                  <input
                    id="email"
                    type="email"
                    name="email"
                    autoComplete="username"
                    inputMode="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="w-full pl-12 pr-4 py-4 bg-gray-50 border-2 border-blue-100 rounded-2xl text-gray-800 placeholder-gray-500 focus:border-blue-300 focus:bg-white transition-all duration-300"
                    placeholder={t("login.emailPlaceholder")}
                    disabled={isLoading || isOAuthLoading !== null}
                  />
                </div>
              </div>

              {/* Mot de passe */}
              <div className="space-y-2">
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-gray-700"
                >
                  {t("login.passwordLabel")}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg
                      className="h-5 w-5 text-blue-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                      />
                    </svg>
                  </div>
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    name="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="w-full pl-12 pr-12 py-4 bg-gray-50 border-2 border-blue-100 rounded-2xl text-gray-800 placeholder-gray-500 focus:border-blue-300 focus:bg-white transition-all duration-300"
                    placeholder={t("login.passwordPlaceholder")}
                    disabled={isLoading || isOAuthLoading !== null}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-blue-400 hover:text-blue-600 transition-colors"
                    disabled={isLoading || isOAuthLoading !== null}
                    aria-label={showPassword ? t("login.hidePassword") : t("login.showPassword")}
                  >
                    {showPassword ? (
                      <svg
                        className="h-5 w-5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"
                        />
                      </svg>
                    ) : (
                      <svg
                        className="h-5 w-5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                        />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Remember me & Mot de passe oublié */}
              <div className="flex items-center justify-between">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-blue-300 bg-gray-50 text-blue-600 focus:ring-blue-500 focus:ring-offset-0"
                    disabled={isLoading || isOAuthLoading !== null}
                  />
                  <span className="ml-3 text-sm text-gray-700">
                    {t("login.rememberMe")}
                  </span>
                </label>
                <Link
                  href="/auth/forgot-password"
                  className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
                >
                  {t("auth.forgotPassword")}
                </Link>
              </div>

              {/* Bouton de connexion */}
              <button
                onClick={handleLogin}
                disabled={isLoading || isOAuthLoading !== null || isPasskeyLoading}
                className="w-full relative py-4 px-6 bg-blue-100 hover:bg-blue-200 border-2 border-blue-100 hover:border-blue-200 text-blue-700 font-semibold rounded-2xl shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center space-x-2">
                    <div className="w-5 h-5 border-2 border-blue-700/30 border-t-blue-700 rounded-full animate-spin"></div>
                    <span>{t("auth.connecting")}</span>
                  </div>
                ) : (
                  <span className="flex items-center justify-center space-x-2">
                    <span>{t("auth.login")}</span>
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
                        d="M13 7l5 5m0 0l-5 5m5-5H6"
                      />
                    </svg>
                  </span>
                )}
              </button>

              {/* Bouton de connexion biométrique (Passkey) */}
              {isPasskeySupported() && (
                <button
                  onClick={handlePasskeyLogin}
                  disabled={isPasskeyLoading || isLoading || isOAuthLoading !== null}
                  className="w-full relative py-4 px-6 bg-gradient-to-r from-purple-100 to-blue-100 hover:from-purple-200 hover:to-blue-200 border-2 border-purple-100 hover:border-purple-200 text-purple-700 font-semibold rounded-2xl shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                >
                  {isPasskeyLoading ? (
                    <div className="flex items-center justify-center space-x-2">
                      <div className="w-5 h-5 border-2 border-purple-700/30 border-t-purple-700 rounded-full animate-spin"></div>
                      <span>{t("auth.connecting")}</span>
                    </div>
                  ) : (
                    <span className="flex items-center justify-center space-x-2">
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
                          d="M7.864 4.243A7.5 7.5 0 0119.5 10.5c0 2.92-.556 5.709-1.568 8.268M5.742 6.364A7.465 7.465 0 004.5 10.5a7.464 7.464 0 01-1.15 3.993m1.989 3.559A11.209 11.209 0 008.25 10.5a3.75 3.75 0 117.5 0c0 .527-.021 1.049-.064 1.565M12 10.5a14.94 14.94 0 01-3.6 9.75m6.633-4.596a18.666 18.666 0 01-2.485 5.33"
                        />
                      </svg>
                      <span>Face ID / Touch ID</span>
                    </span>
                  )}
                </button>
              )}

              {/* Séparateur pour les boutons sociaux */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-blue-200"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white text-gray-500">
                    {t("common.or")}
                  </span>
                </div>
              </div>

              {/* Boutons de connexion sociale */}
              <div className="space-y-3">
                {/* LinkedIn */}
                <button
                  onClick={() => handleOAuthLogin("linkedin")}
                  disabled={isOAuthLoading !== null || isLoading}
                  className="w-full py-4 px-6 bg-[#0A66C2] hover:bg-[#004182] text-white font-medium rounded-2xl transition-all duration-300 transform hover:scale-[1.02] flex items-center justify-center space-x-3 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                >
                  {isOAuthLoading === "linkedin" ? (
                    <div className="flex items-center space-x-2">
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      <span>{t("auth.connecting")}</span>
                    </div>
                  ) : (
                    <>
                      <svg
                        className="w-5 h-5"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                      </svg>
                      <span>{t("auth.continueWith")} LinkedIn</span>
                    </>
                  )}
                </button>

                {/* Facebook */}
                <button
                  onClick={() => handleOAuthLogin("facebook")}
                  disabled={isOAuthLoading !== null || isLoading}
                  className="w-full py-4 px-6 bg-[#1877F2] hover:bg-[#166FE5] text-white font-medium rounded-2xl transition-all duration-300 transform hover:scale-[1.02] flex items-center justify-center space-x-3 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                >
                  {isOAuthLoading === "facebook" ? (
                    <div className="flex items-center space-x-2">
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      <span>{t("auth.connecting")}</span>
                    </div>
                  ) : (
                    <>
                      <svg
                        className="w-5 h-5"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                      </svg>
                      <span>{t("auth.continueWith")} Facebook</span>
                    </>
                  )}
                </button>
              </div>

              {/* Nouveau séparateur */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-blue-200"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white text-gray-500">
                    {t("auth.noAccountYet")}
                  </span>
                </div>
              </div>

              {/* Bouton d'inscription */}
              <button
                onClick={() => setShowSignup(true)}
                disabled={isOAuthLoading !== null || isLoading}
                className="w-full py-4 px-6 bg-gray-50 hover:bg-blue-50 border-2 border-blue-100 hover:border-blue-200 text-blue-700 font-medium rounded-2xl transition-all duration-300 transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                <span className="flex items-center justify-center space-x-2">
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
                      d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
                    />
                  </svg>
                  <span>{t("auth.createAccount")}</span>
                </span>
              </button>
            </div>
          </div>

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-xs text-gray-500">{t("gdpr.notice")}</p>
            <div className="mt-3 space-x-1 text-xs">
              <Link
                href="/terms"
                className="transition-colors"
                style={{ color: "#226ae4" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = "#1e5db3";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = "#226ae4";
                }}
              >
                {t("legal.terms")}
              </Link>
              <span className="text-gray-400">•</span>
              <Link
                href="/privacy"
                className="transition-colors"
                style={{ color: "#226ae4" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = "#1e5db3";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = "#226ae4";
                }}
              >
                {t("legal.privacy")}
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Modal d'inscription */}
      {showSignup && (
        <SignupModal
          authLogic={authLogic}
          localError=""
          localSuccess=""
          toggleMode={() => setShowSignup(false)}
        />
      )}
    </div>
  );
}

// Composant fallback sans traductions (pour éviter d'afficher les clés)
const LoadingFallback = () => {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <img
          src="/images/logo.png"
          alt="Intelia Logo"
          className="w-16 h-16 mx-auto mb-4 object-contain drop-shadow-lg"
        />
        <div className="w-12 h-12 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin mx-auto mb-4"></div>
      </div>
    </div>
  );
};

// PAGE PRINCIPALE avec gestion du chargement des traductions
export default function LoginPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <LoginPageContent />
    </Suspense>
  );
}
