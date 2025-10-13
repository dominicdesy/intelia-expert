"use client";

import React, { useState, forwardRef } from "react";
import Link from "next/link";
import type { Language } from "@/types";
import {
  useTranslation,
  availableLanguages,
  getLanguageByCode,
} from "@/lib/languages/i18n";

// Logo Intelia
export const InteliaLogo = ({
  className = "w-16 h-16",
}: {
  className?: string;
}) => (
  <img src="/images/favicon.png" alt="Intelia Logo" className={className} />
);

// Sélecteur de langue intégré avec le système i18n
export const LanguageSelector = () => {
  const { changeLanguage, currentLanguage } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  const handleLanguageChange = (languageCode: string) => {
    changeLanguage(languageCode);
    setIsOpen(false); // Fermer le dropdown après sélection
  };

  const currentLangConfig = getLanguageByCode(currentLanguage);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 transition-colors"
      >
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
            d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
          />
        </svg>
        <span className="mr-1">{currentLangConfig?.flag}</span>
        <span>{currentLangConfig?.nativeName || currentLangConfig?.name}</span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
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
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
            {availableLanguages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => handleLanguageChange(lang.code)}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center space-x-3 ${
                  lang.code === currentLanguage
                    ? "bg-blue-50 text-blue-600"
                    : "text-gray-700"
                } first:rounded-t-lg last:rounded-b-lg transition-colors`}
              >
                <span className="text-xl">{lang.flag}</span>
                <div className="flex-1">
                  <div className="font-medium">{lang.nativeName}</div>
                </div>
                {lang.code === currentLanguage && (
                  <svg
                    className="w-4 h-4 text-blue-500"
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

// Composant d'alerte pour les erreurs/succès - CORRIGÉ : utilise directement useTranslation
export const AlertMessage = ({
  type,
  title,
  message,
}: {
  type: "error" | "success";
  title: string;
  message: string;
}) => {
  const isError = type === "error";

  return (
    <div
      className={`mb-6 ${isError ? "bg-red-50 border-red-200" : "bg-green-50 border-green-200"} border rounded-lg p-4`}
    >
      <div className="flex">
        <div className="flex-shrink-0">
          {isError ? (
            <svg
              className="h-5 w-5 text-red-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
          ) : (
            <svg
              className="h-5 w-5 text-green-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
          )}
        </div>
        <div className="ml-3">
          {title && (
            <h3
              className={`text-sm font-medium ${isError ? "text-red-800" : "text-green-800"}`}
            >
              {title}
            </h3>
          )}
          <div
            className={`${title ? "mt-1" : ""} text-sm ${isError ? "text-red-700" : "text-green-700"}`}
          >
            {message}
          </div>
        </div>
      </div>
    </div>
  );
};

// Input avec toggle de visibilité pour les mots de passe - AVEC forwardRef
export const PasswordInput = forwardRef<
  HTMLInputElement,
  {
    id?: string;
    name?: string;
    value: string;
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    placeholder?: string;
    required?: boolean;
    autoComplete?: string;
    className?: string;
  }
>(
  (
    {
      id,
      name,
      value,
      onChange,
      placeholder,
      required = false,
      autoComplete,
      className = "block w-full rounded-md border border-gray-300 px-3 py-2 pr-10 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm",
    },
    ref,
  ) => {
    const [showPassword, setShowPassword] = useState(false);

    return (
      <div className="relative">
        <input
          ref={ref}
          id={id}
          name={name}
          type={showPassword ? "text" : "password"}
          autoComplete={autoComplete}
          required={required}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className={className}
        />
        <button
          type="button"
          className="absolute inset-y-0 right-0 pr-3 flex items-center"
          onClick={() => setShowPassword(!showPassword)}
          tabIndex={-1}
        >
          {showPassword ? (
            <svg
              className="h-5 w-5 text-gray-400"
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
              className="h-5 w-5 text-gray-400"
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
    );
  },
);

// Ajout du displayName pour le debugging
PasswordInput.displayName = "PasswordInput";

// Indicateur de correspondance des mots de passe - CORRIGÉ : utilise directement useTranslation
export const PasswordMatchIndicator = ({
  password,
  confirmPassword,
}: {
  password: string;
  confirmPassword: string;
}) => {
  const { t } = useTranslation();

  if (!password || !confirmPassword) return null;

  const match = confirmPassword === password;

  return (
    <div className="mt-2 text-xs">
      {match ? (
        <span className="text-green-600 flex items-center">
          <svg
            className="w-3 h-3 mr-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
          {t("validation.password.match") || "Les mots de passe correspondent"}
        </span>
      ) : (
        <span className="text-red-600 flex items-center">
          <svg
            className="w-3 h-3 mr-1"
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
          {t("validation.password.mismatch") ||
            "Les mots de passe ne correspondent pas"}
        </span>
      )}
    </div>
  );
};

// Loading Spinner - CORRIGÉ : utilise directement useTranslation
export const LoadingSpinner = ({ text }: { text?: string }) => {
  const { t } = useTranslation();
  const displayText = text || t("common.loading") || "Chargement...";

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
      <div className="text-center">
        <InteliaLogo className="w-16 h-16 mx-auto mb-4" />
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">{displayText}</p>
      </div>
    </div>
  );
};

// Footer avec liens - CORRIGÉ : utilise directement le hook useTranslation
export const AuthFooter = () => {
  const { t } = useTranslation();

  return (
    <div className="mt-6 text-center">
      <p className="text-xs text-gray-500">
        {t("gdpr.notice") || "En continuant, vous acceptez nos"}{" "}
        <Link href="/terms" className="text-blue-600 hover:text-blue-500">
          {t("legal.terms") || "Conditions d'utilisation"}
        </Link>
        {" et notre "}
        <Link href="/privacy" className="text-blue-600 hover:text-blue-500">
          {t("legal.privacy") || "Politique de confidentialité"}
        </Link>
      </p>
    </div>
  );
};
