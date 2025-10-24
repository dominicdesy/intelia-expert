"use client";

import React, { useState } from "react";
import { Download } from "lucide-react";
import { secureLog } from "@/lib/utils/secureLogger";
import { useTranslation } from "@/lib/languages/i18n";

interface ExportPDFButtonProps {
  conversationId: string;
}

const ExportPDFButton: React.FC<ExportPDFButtonProps> = ({
  conversationId,
}) => {
  const { t } = useTranslation();
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setIsExporting(true);
    setError(null);

    try {
      // Récupérer le token d'auth
      const authData = localStorage.getItem("intelia-expert-auth");
      if (!authData) {
        throw new Error(t("export.notAuthenticated"));
      }
      const { access_token } = JSON.parse(authData);

      // Faire l'appel direct avec fetch pour récupérer le blob
      const response = await fetch(
        `https://expert.intelia.com/api/v1/conversations/${conversationId}/export/pdf`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${access_token}`,
          },
        }
      );

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error("PLAN_RESTRICTION");
        }
        throw new Error(t("export.serverError"));
      }

      // Récupérer le blob
      const blob = await response.blob();

      // Créer un URL pour le blob
      const url = window.URL.createObjectURL(blob);

      // Créer un lien temporaire et cliquer dessus pour télécharger
      const link = document.createElement("a");
      link.href = url;
      link.download = `intelia_conversation_${new Date().toISOString().split("T")[0]}.pdf`;
      document.body.appendChild(link);
      link.click();

      // Nettoyer
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      secureLog.log("PDF exporté avec succès");
    } catch (err: any) {
      secureLog.error("Erreur export PDF:", err);

      // Gérer les erreurs spécifiques
      if (err.message === "PLAN_RESTRICTION") {
        setError(t("export.planRestriction"));
      } else {
        setError(t("export.error"));
      }
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <>
      <button
        onClick={handleExport}
        disabled={isExporting}
        className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        title={t("export.tooltip")}
      >
        <Download size={16} className={isExporting ? "animate-pulse" : ""} />
        <span>
          {isExporting ? t("export.exporting") : t("export.button")}
        </span>
      </button>

      {/* Message d'erreur */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg z-50 max-w-md">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-600"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-sm text-red-700">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="flex-shrink-0 text-red-400 hover:text-red-600"
            >
              <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default ExportPDFButton;
