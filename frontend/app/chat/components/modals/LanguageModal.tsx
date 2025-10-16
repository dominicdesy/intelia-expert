"use client";

import React, { useState } from "react";
import {
  useTranslation,
  availableLanguages,
  getLanguageByCode,
} from "@/lib/languages/i18n";
import { CheckIcon } from "../../utils/icons";
import { secureLog } from "@/lib/utils/secureLogger";
import { BaseDialog } from "../BaseDialog";

interface LanguageModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LanguageModal: React.FC<LanguageModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { t, changeLanguage, currentLanguage } = useTranslation();
  const [isUpdating, setIsUpdating] = useState(false);

  const handleLanguageChange = async (languageCode: string) => {
    if (languageCode === currentLanguage || isUpdating) return;

    setIsUpdating(true);

    try {
      secureLog.log(
        `[LanguageModal] Changement langue: ${currentLanguage} → ${languageCode}`,
      );

      // 1. Changer dans l'interface via le hook
      await changeLanguage(languageCode);
      secureLog.log("[LanguageModal] Langue changée via hook");

      // 2. Attendre que la synchronisation se fasse
      await new Promise((resolve) => setTimeout(resolve, 300));

      // 3. Émettre un événement pour forcer la synchronisation globale
      window.dispatchEvent(
        new CustomEvent("languageChanged", {
          detail: { language: languageCode },
        }),
      );

      secureLog.log("[LanguageModal] Synchronisation terminée");

      // 4. Fermer la modal
      onClose();
    } catch (error) {
      secureLog.error("[LanguageModal] Erreur changement:", error);
    } finally {
      setIsUpdating(false);
    }
  };

  const currentLangConfig = getLanguageByCode(currentLanguage);

  return (
    <BaseDialog
      isOpen={isOpen}
      onClose={onClose}
      title={t("language.title")}
      maxWidth="800px"
    >
      {/* Description */}
      <p className="text-gray-600 mb-6">{t("language.description")}</p>

      {/* Langue actuelle */}
      {currentLangConfig && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-center">
            <span className="text-2xl mr-3">{currentLangConfig.flag}</span>
            <div>
              <div className="font-semibold text-blue-900">
                {t("language.current")}: {currentLangConfig.nativeName}
              </div>
              <div className="text-sm font-bold text-gray-500">
                {currentLangConfig.code.toUpperCase()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Indicateur de chargement global */}
      {isUpdating && (
        <div className="mb-4 p-3 bg-blue-50 border-l-4 border-blue-400 text-blue-700">
          <div className="flex items-center">
            <svg
              className="animate-spin h-5 w-5 mr-2"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              ></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            <span>{t("language.updating")}</span>
          </div>
        </div>
      )}

      {/* Grille des langues disponibles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
        {availableLanguages.map((lang) => (
          <div
            key={lang.code}
            onClick={() => !isUpdating && handleLanguageChange(lang.code)}
            className={`
              relative p-4 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:shadow-md
              ${
                currentLanguage === lang.code
                  ? "border-blue-500 bg-blue-50 shadow-md"
                  : "border-gray-200 hover:border-blue-300 bg-white"
              }
              ${isUpdating ? "opacity-50 cursor-not-allowed" : "hover:bg-blue-50"}
            `}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">{lang.flag}</span>
                <div>
                  <div className="font-semibold text-gray-900 text-sm">
                    {lang.nativeName}
                  </div>
                  <div className="text-sm font-bold text-gray-500 mt-1">
                    {lang.code.toUpperCase()}
                  </div>
                </div>
              </div>

              {currentLanguage === lang.code && (
                <div className="flex items-center text-blue-600">
                  <CheckIcon className="w-5 h-5" />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Bouton de fermeture */}
      <div className="flex justify-end">
        <button
          onClick={onClose}
          className="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
          disabled={isUpdating}
        >
          {t("modal.close")}
        </button>
      </div>
    </BaseDialog>
  );
};
