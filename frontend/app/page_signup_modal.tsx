/**
 * Page Signup Modal
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
"use client";

import React, { useState, useRef, useEffect } from "react";
import { AlertMessage } from "./page_components";
import { useCountries } from "./page_hooks";
import { useTranslation } from "@/lib/languages/i18n";

interface SignupModalProps {
  authLogic: any;
  localError: string;
  localSuccess: string;
  toggleMode: () => void;
}

// Composant CountrySelect local pour éviter les problèmes d'import
interface Country {
  value: string;
  label: string;
  phoneCode: string;
  flag?: string;
}

interface CountrySelectProps {
  countries: Country[];
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  className?: string;
}

const CountrySelect: React.FC<CountrySelectProps> = ({
  countries,
  value,
  onChange,
  placeholder,
  className = "",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const selectRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();

  const filteredCountries = countries.filter(
    (country) =>
      country.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
      country.value.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const selectedCountry = countries.find((c) => c.value === value);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        selectRef.current &&
        !selectRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setSearchTerm("");
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div ref={selectRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="block w-full rounded-md border border-gray-300 px-3 py-2 text-left shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm bg-white"
      >
        {selectedCountry ? (
          <div className="flex items-center space-x-2">
            {selectedCountry.flag && <span>{selectedCountry.flag}</span>}
            <span>{selectedCountry.label}</span>
          </div>
        ) : (
          <span className="text-gray-400">{placeholder}</span>
        )}
        <div className="absolute inset-y-0 right-0 flex items-center pr-2">
          <svg
            className="w-4 h-4 text-gray-400"
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
        </div>
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-hidden">
          <div className="p-2 border-b border-gray-200">
            <input
              type="text"
              placeholder={
                t("countries.searchPlaceholder" as any) ||
                "Rechercher un pays..."
              }
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="max-h-48 overflow-y-auto">
            {filteredCountries.length > 0 ? (
              filteredCountries.map((country) => (
                <button
                  key={country.value}
                  type="button"
                  onClick={() => {
                    onChange(country.value);
                    setIsOpen(false);
                    setSearchTerm("");
                  }}
                  className={`w-full text-left px-3 py-2 hover:bg-gray-100 flex items-center space-x-2 ${
                    value === country.value ? "bg-blue-50 text-blue-600" : ""
                  }`}
                >
                  {country.flag && <span>{country.flag}</span>}
                  <span className="flex-1">{country.label}</span>
                </button>
              ))
            ) : (
              <div className="px-3 py-2 text-gray-500 text-sm">
                {t("countries.noResults" as any) || "Aucun pays trouvé"}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Validation de mot de passe synchronisée avec page.tsx
const validatePassword = (password: string, t: (key: string) => string) => {
  const errors = [];

  // Vérifier que le mot de passe n'est pas vide ou seulement des espaces
  if (!password || password.trim().length === 0) {
    errors.push(
      t("validation.required.password") || "Le mot de passe est requis",
    );
    return { isValid: false, errors };
  }

  // Minimum 8 caractères
  if (password.length < 8) {
    errors.push(
      t("validation.password.minLength") || "Au moins 8 caractères requis",
    );
  }

  // Au moins une majuscule
  if (!/[A-Z]/.test(password)) {
    errors.push(
      t("validation.password.uppercase") || "Au moins une majuscule requise",
    );
  }

  // Au moins une minuscule
  if (!/[a-z]/.test(password)) {
    errors.push(
      t("validation.password.lowercase") || "Au moins une minuscule requise",
    );
  }

  // Au moins un chiffre
  if (!/\d/.test(password)) {
    errors.push(
      t("validation.password.number") || "Au moins un chiffre requis",
    );
  }

  // Au moins un caractère spécial
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push(
      t("validation.password.special") || "Au moins un caractère spécial requis (!@#$%^&*(),.?\":{}|<>)",
    );
  }

  return { isValid: errors.length === 0, errors };
};

// Composant d'indicateur de force du mot de passe
const PasswordStrengthIndicator: React.FC<{ password: string }> = ({
  password,
}) => {
  const { t } = useTranslation();
  const validation = validatePassword(password, t as any);

  const requirements = [
    {
      test: password.length >= 8,
      label:
        t("validation.password.minLength" as any) ||
        "Au moins 8 caractères",
    },
    {
      test: /[A-Z]/.test(password),
      label:
        t("validation.password.uppercase" as any) ||
        "Au moins une majuscule",
    },
    {
      test: /[a-z]/.test(password),
      label:
        t("validation.password.lowercase" as any) ||
        "Au moins une minuscule",
    },
    {
      test: /\d/.test(password),
      label: t("validation.password.number" as any) || "Au moins un chiffre",
    },
    {
      test: /[!@#$%^&*(),.?":{}|<>]/.test(password),
      label: t("validation.password.special" as any) || "Au moins un caractère spécial (!@#$%...)",
    },
  ];

  // Calculer le score de force
  const passedRequirements = requirements.filter((req) => req.test).length;
  const strength = passedRequirements / requirements.length;

  const getStrengthColor = () => {
    if (strength < 0.4) return "bg-red-500";
    if (strength < 0.7) return "bg-yellow-500";
    if (strength < 0.9) return "bg-blue-500";
    return "bg-green-500";
  };

  const getStrengthLabel = () => {
    if (strength < 0.4)
      return t("resetPassword.strength.weak" as any) || "Faible";
    if (strength < 0.7)
      return t("resetPassword.strength.medium" as any) || "Moyen";
    if (strength < 0.9) return t("resetPassword.strength.good" as any) || "Bon";
    return t("resetPassword.strength.excellent" as any) || "Excellent";
  };

  return (
    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-gray-700">
          {t("resetPassword.passwordStrength" as any) ||
            "Force du mot de passe"}
        </p>
        <span
          className={`text-xs font-medium ${
            strength < 0.4
              ? "text-red-600"
              : strength < 0.7
                ? "text-yellow-600"
                : strength < 0.9
                  ? "text-blue-600"
                  : "text-green-600"
          }`}
        >
          {getStrengthLabel()}
        </span>
      </div>

      {/* Barre de progression */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
        <div
          className={`h-2 rounded-full transition-all duration-300 ${getStrengthColor()}`}
          style={{ width: `${strength * 100}%` }}
        ></div>
      </div>

      {/* Liste des exigences */}
      <div className="grid grid-cols-1 gap-1 text-xs">
        {requirements.map((req, index) => (
          <div
            key={index}
            className={`flex items-center ${req.test ? "text-green-600" : "text-gray-400"}`}
          >
            <span className="mr-2 text-sm">{req.test ? "✅" : "⭕"}</span>
            <span>{req.label}</span>
          </div>
        ))}
      </div>

      {/* Conseils pour améliorer le mot de passe */}
      {strength < 1 && (
        <div className="mt-3 pt-2 border-t border-gray-200">
          <p className="text-xs text-gray-600 font-medium mb-1">
            {t("resetPassword.tips" as any) || "Conseils"} :
          </p>
          <ul className="text-xs text-gray-600 space-y-1">
            {password.length < 12 && (
              <li>
                •{" "}
                {t("resetPassword.tip.longerPassword" as any) ||
                  "Utilisez 12+ caractères pour plus de sécurité"}
              </li>
            )}
            {!/[A-Z]/.test(password) && !/[a-z]/.test(password) && (
              <li>
                •{" "}
                {t("resetPassword.tip.mixCase" as any) ||
                  "Mélangez majuscules et minuscules"}
              </li>
            )}
            {!/[!@#$%^&*()_+=\[\]{};':"|,.<>?-]/.test(password) && (
              <li>
                •{" "}
                {t("resetPassword.tip.specialChars" as any) ||
                  "Les caractères spéciaux renforcent la sécurité (optionnel)"}
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
};

export function SignupModal({
  authLogic,
  localError,
  localSuccess,
  toggleMode,
}: SignupModalProps) {
  // CORRECTION : Utiliser seulement t, pas loading pour éviter la boucle
  const { t } = useTranslation();
  const isMountedRef = React.useRef(true); // Protection démontage

  // Cleanup au démontage
  React.useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Fonction de fallback pour les traductions
  const safeT = (key: string) => {
    const translation = t(key as any);
    // Si la traduction retourne la clé elle-même, c'est qu'elle n'est pas encore chargée
    if (translation === key) {
      // Fallbacks en français pour les clés principales
      const fallbacks: Record<string, string> = {
        "auth.createAccount": "Créer un compte",
        "profile.firstName": "Prénom",
        "profile.lastName": "Nom de famille",
        "profile.email": "Email",
        "profile.country": "Pays",
        "profile.password": "Mot de passe",
        "profile.confirmPassword": "Confirmer le mot de passe",
        "form.required": "*",
        "modal.back": "Retour",
        "common.loading": "Chargement...",
        "placeholder.countrySelect": "Sélectionner un pays",
        "error.generic": "Erreur",
        "auth.success": "Succès",
        "gdpr.notice":
          "En vous connectant, vous acceptez nos conditions d'utilisation et notre politique de confidentialité.",
        "countries.noResults": "Aucun pays trouvé",
        "countries.searchPlaceholder": "Rechercher un pays...",
        "countries.limitedList":
          "Liste de pays limitée (service externe temporairement indisponible)",
      };
      return fallbacks[key] || key;
    }
    return translation;
  };

  // Chargement des pays uniquement dans SignupModal
  const {
    countries,
    loading: countriesLoading,
    usingFallback,
  } = useCountries();

  const {
    signupData,
    showPassword,
    setShowPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    isLoading,
    handleSignupChange,
    handleSignup,
  } = authLogic;

  const [formError, setFormError] = React.useState("");
  const [formSuccess, setFormSuccess] = React.useState("");
  const [buttonState, setButtonState] = React.useState<
    "idle" | "loading" | "success" | "error"
  >("idle");

  // État pour le consentement GDPR (Article 7 - Consentement explicite)
  const [acceptTerms, setAcceptTerms] = React.useState(false);

  // Gestion locale simplifiée de l'auto-remplissage country
  const handleCountryChange = React.useCallback(
    (value: string) => {
      handleSignupChange("country", value);
    },
    [handleSignupChange],
  );

  // Auto-détecter le pays de l'utilisateur via son IP
  React.useEffect(() => {
    const detectUserCountry = async () => {
      // Ne détecter que si le pays n'est pas déjà sélectionné
      if (signupData.country) return;

      try {
        const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
        const response = await fetch(`${apiBaseUrl}/v1/auth/detect-country`);
        const data = await response.json();

        if (data.success && data.country_code) {
          // Pré-sélectionner le pays détecté
          handleCountryChange(data.country_code);
          console.log(`🌍 Pays détecté automatiquement: ${data.country_name} (${data.country_code})`);
        }
      } catch (error) {
        console.error("Erreur lors de la détection du pays:", error);
        // Échec silencieux - l'utilisateur peut sélectionner manuellement
      }
    };

    detectUserCountry();
  }, [signupData.country, handleCountryChange]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");
    setFormSuccess("");
    setButtonState("loading");

    try {
      const result = await handleSignup(e);

      if (result && result.success) {
        setButtonState("success");
        setFormSuccess(result.message || safeT("auth.success"));

        // Passer en mode login après 4 secondes
        setTimeout(() => {
          // PROTECTION: Vérifier que le composant est toujours monté
          if (!isMountedRef.current) return;
          toggleMode();
        }, 4000);
      }
    } catch (error: any) {
      setButtonState("error");
      setFormError(error.message);

      // Revenir à l'état normal après 3 secondes
      setTimeout(() => {
        // PROTECTION: Vérifier que le composant est toujours monté
        if (!isMountedRef.current) return;
        setButtonState("idle");
      }, 3000);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      onSubmit(e as any);
    }
  };

  // Fonction pour obtenir le contenu du bouton selon l'état
  const getButtonContent = () => {
    switch (buttonState) {
      case "loading":
        return (
          <div className="flex items-center space-x-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            <span>{safeT("auth.creating")}</span>
          </div>
        );
      case "success":
        return (
          <div className="flex items-center space-x-2">
            <svg
              className="w-4 h-4 text-white"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clipRule="evenodd"
              />
            </svg>
            <span>{safeT("auth.accountCreated")}</span>
          </div>
        );
      case "error":
        return (
          <div className="flex items-center space-x-2">
            <svg
              className="w-4 h-4 text-white"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <span>{safeT("error.generic")}</span>
          </div>
        );
      default:
        return safeT("auth.createAccount");
    }
  };

  // Fonction pour obtenir les classes CSS du bouton selon l'état
  const getButtonClasses = () => {
    const baseClasses =
      "flex justify-center items-center rounded-md border border-transparent py-2 px-4 text-sm font-medium text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 ease-in-out";

    switch (buttonState) {
      case "loading":
        return `${baseClasses} bg-blue-500 hover:bg-blue-600 focus:ring-blue-500 animate-pulse`;
      case "success":
        return `${baseClasses} bg-green-500 hover:bg-green-600 focus:ring-green-500 scale-105`;
      case "error":
        return `${baseClasses} bg-red-500 hover:bg-red-600 focus:ring-red-500 animate-shake`;
      default:
        return `${baseClasses} bg-green-600 hover:bg-green-700 focus:ring-green-500 hover:scale-105`;
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 p-4 overflow-hidden overscroll-none">
      {/* Styles CSS pour l'animation shake */}
      <style jsx>{`
        @keyframes shake {
          0%,
          100% {
            transform: translateX(0);
          }
          25% {
            transform: translateX(-4px);
          }
          75% {
            transform: translateX(4px);
          }
        }
        .animate-shake {
          animation: shake 0.5s ease-in-out;
        }
      `}</style>

      <div className="w-full max-w-md mx-auto bg-white rounded-lg shadow-xl max-h-[calc(100vh-2rem)] overflow-y-auto overscroll-contain">
        {/* Header de la modale avec bouton fermer */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-lg">
          <h3 className="text-lg font-semibold text-gray-900">
            {safeT("auth.createAccount")}
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

        {/* Corps de la modale */}
        <div className="flex-1 px-6 py-4">
          {/* Messages d'erreur et succès pour signup */}
          {(localError || formError) && (
            <AlertMessage
              type="error"
              title={safeT("error.generic")}
              message={localError || formError}
            />
          )}

          {(localSuccess || formSuccess) && (
            <AlertMessage
              type="success"
              title=""
              message={localSuccess || formSuccess}
            />
          )}

          {/* Avertissement fallback pays */}
          {usingFallback && !countriesLoading && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
              <div className="flex items-center space-x-2">
                <svg
                  className="w-4 h-4 text-yellow-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z"
                  />
                </svg>
                <span className="text-sm text-yellow-800">
                  {safeT("countries.limitedList")}
                </span>
              </div>
            </div>
          )}

          {/* FORMULAIRE D'INSCRIPTION SIMPLIFIÉ */}
          <form onSubmit={onSubmit} onKeyPress={handleKeyPress}>
            <div className="space-y-4">
              {/* Prénom */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {safeT("profile.firstName")}{" "}
                  <span className="text-red-500">{safeT("form.required")}</span>
                </label>
                <input
                  type="text"
                  name="given-name"
                  autoComplete="given-name"
                  required
                  value={signupData.firstName}
                  onChange={(e) =>
                    handleSignupChange("firstName", e.target.value)
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                  disabled={isLoading}
                />
              </div>

              {/* Nom */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {safeT("profile.lastName")}{" "}
                  <span className="text-red-500">{safeT("form.required")}</span>
                </label>
                <input
                  type="text"
                  name="family-name"
                  autoComplete="family-name"
                  required
                  value={signupData.lastName}
                  onChange={(e) =>
                    handleSignupChange("lastName", e.target.value)
                  }
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                  disabled={isLoading}
                />
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {safeT("profile.email")}{" "}
                  <span className="text-red-500">{safeT("form.required")}</span>
                </label>
                <input
                  type="email"
                  name="email"
                  autoComplete="email"
                  inputMode="email"
                  required
                  value={signupData.email}
                  onChange={(e) => handleSignupChange("email", e.target.value)}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                  disabled={isLoading}
                />
              </div>

              {/* Sélecteur de pays */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {safeT("profile.country")}{" "}
                  <span className="text-red-500">{safeT("form.required")}</span>
                </label>

                {countriesLoading ? (
                  <div className="block w-full rounded-md border border-gray-300 px-3 py-2 bg-gray-50">
                    <div className="flex items-center space-x-2">
                      <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-sm text-gray-600">
                        {safeT("common.loading")}
                      </span>
                    </div>
                  </div>
                ) : (
                  <CountrySelect
                    countries={countries}
                    value={signupData.country}
                    onChange={handleCountryChange}
                    placeholder={safeT("placeholder.countrySelect")}
                    className="w-full"
                  />
                )}
              </div>

              {/* Production Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t("profile.productionType.label" as any)}
                </label>
                <div className="space-y-2">
                  <label className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                    <input
                      type="checkbox"
                      checked={signupData.productionType?.includes('broiler') || false}
                      onChange={(e) => {
                        const currentTypes = signupData.productionType || [];
                        const newProductionType = e.target.checked
                          ? [...currentTypes, 'broiler']
                          : currentTypes.filter(t => t !== 'broiler');
                        handleSignupChange('productionType', newProductionType);
                      }}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 cursor-pointer"
                      disabled={isLoading}
                    />
                    <span className="ml-3 text-sm text-gray-700">
                      {t("profile.productionType.broiler" as any)}
                    </span>
                  </label>
                  <label className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                    <input
                      type="checkbox"
                      checked={signupData.productionType?.includes('layer') || false}
                      onChange={(e) => {
                        const currentTypes = signupData.productionType || [];
                        const newProductionType = e.target.checked
                          ? [...currentTypes, 'layer']
                          : currentTypes.filter(t => t !== 'layer');
                        handleSignupChange('productionType', newProductionType);
                      }}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 cursor-pointer"
                      disabled={isLoading}
                    />
                    <span className="ml-3 text-sm text-gray-700">
                      {t("profile.productionType.layer" as any)}
                    </span>
                  </label>
                </div>
              </div>

              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t("profile.category.label" as any)}
                </label>
                <select
                  value={signupData.category || ""}
                  onChange={(e) => handleSignupChange('category', e.target.value)}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm bg-white"
                  disabled={isLoading}
                >
                  <option value="">-- {t("common.optional" as any)} --</option>
                  <option value="breeding_hatchery">{t("profile.category.breedingHatchery" as any)}</option>
                  <option value="feed_nutrition">{t("profile.category.feedNutrition" as any)}</option>
                  <option value="farm_operations">{t("profile.category.farmOperations" as any)}</option>
                  <option value="health_veterinary">{t("profile.category.healthVeterinary" as any)}</option>
                  <option value="processing">{t("profile.category.processing" as any)}</option>
                  <option value="management_oversight">{t("profile.category.managementOversight" as any)}</option>
                  <option value="equipment_technology">{t("profile.category.equipmentTechnology" as any)}</option>
                  <option value="other">{t("profile.category.other" as any)}</option>
                </select>

                {/* Category Other - Conditional */}
                {signupData.category === 'other' && (
                  <input
                    type="text"
                    value={signupData.categoryOther || ""}
                    onChange={(e) => handleSignupChange('categoryOther', e.target.value)}
                    placeholder={t("profile.category.otherPlaceholder" as any)}
                    className="mt-2 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    disabled={isLoading}
                  />
                )}
              </div>

              {/* Mot de passe */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {safeT("profile.password")}{" "}
                  <span className="text-red-500">{safeT("form.required")}</span>
                </label>
                <div className="mt-1 relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    name="new-password"
                    autoComplete="new-password"
                    required
                    value={signupData.password}
                    onChange={(e) =>
                      handleSignupChange("password", e.target.value)
                    }
                    className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    placeholder="••••••••"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    tabIndex={-1}
                    aria-label={showPassword ? safeT("login.hidePassword") : safeT("login.showPassword")}
                  >
                    <svg
                      className="h-4 w-4 text-gray-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
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
                  </button>
                </div>

                {/* Indicateur de force du mot de passe moderne */}
                {signupData.password && (
                  <PasswordStrengthIndicator password={signupData.password} />
                )}
              </div>

              {/* Confirmer mot de passe */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {safeT("profile.confirmPassword")}{" "}
                  <span className="text-red-500">{safeT("form.required")}</span>
                </label>
                <div className="mt-1 relative">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    name="new-password-confirm"
                    autoComplete="new-password"
                    required
                    value={signupData.confirmPassword}
                    onChange={(e) =>
                      handleSignupChange("confirmPassword", e.target.value)
                    }
                    className="block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm"
                    placeholder="••••••••"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    tabIndex={-1}
                    aria-label={showConfirmPassword ? safeT("login.hidePassword") : safeT("login.showPassword")}
                  >
                    <svg
                      className="h-4 w-4 text-gray-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
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
                  </button>
                </div>
                {signupData.confirmPassword && (
                  <div className="mt-2">
                    {signupData.password === signupData.confirmPassword ? (
                      <div className="flex items-center text-xs text-green-600">
                        <svg
                          className="h-3 w-3 mr-1"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                            clipRule="evenodd"
                          />
                        </svg>
                        {t("validation.password.match" as any) ||
                          "Mots de passe identiques"}
                      </div>
                    ) : (
                      <div className="flex items-center text-xs text-red-600">
                        <svg
                          className="h-3 w-3 mr-1"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                            clipRule="evenodd"
                          />
                        </svg>
                        {t("validation.password.mismatch" as any) ||
                          "Les mots de passe ne correspondent pas"}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </form>
        </div>

        {/* Footer de la modale avec boutons */}
        <div className="flex-shrink-0 bg-gray-50 border-t border-gray-200 px-6 py-4 rounded-b-lg">
          {/* Séparateur avec texte légal */}
          <div className="relative mb-4">
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-gray-50 text-gray-500"></span>
            </div>
          </div>

          {/* GDPR Consent Checkbox - Article 7 RGPD */}
          <div className="mb-6 mt-0">
            <label className="flex items-start space-x-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={acceptTerms}
                onChange={(e) => setAcceptTerms(e.target.checked)}
                required
                className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer"
              />
              <span className="text-xs text-gray-700 leading-relaxed select-none">
                {safeT("gdpr.signupNotice")}{" "}
                <a
                  href="/terms"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 underline transition-colors font-medium"
                >
                  {safeT("legal.terms")}
                </a>{" "}
                {safeT("legal.and")}{" "}
                <a
                  href="/privacy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 underline transition-colors font-medium"
                >
                  {safeT("legal.privacy")}
                </a>
                .
              </span>
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={toggleMode}
              className="rounded-md border border-gray-300 bg-white py-2 px-4 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              {safeT("modal.back")}
            </button>
            <button
              onClick={onSubmit}
              disabled={isLoading || buttonState !== "idle" || !acceptTerms}
              className={getButtonClasses()}
            >
              {getButtonContent()}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
