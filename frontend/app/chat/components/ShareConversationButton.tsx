"use client";

import React, { useState } from "react";
import { Share2, Copy, Check, X, Clock, Trash2 } from "lucide-react";
import { useTranslation } from "@/lib/languages/i18n";
import { secureLog } from "@/lib/utils/secureLogger";

interface ShareConversationButtonProps {
  conversationId: string;
  onShareCreated?: (shareUrl: string) => void;
}

interface ShareData {
  share_id: string;
  share_url: string;
  share_token: string;
  anonymize: boolean;
  expires_at: string | null;
  created_at: string;
}

const ShareConversationButton: React.FC<ShareConversationButtonProps> = ({
  conversationId,
  onShareCreated,
}) => {
  const { t } = useTranslation();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [shareData, setShareData] = useState<ShareData | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Options du formulaire
  const [expiresInDays, setExpiresInDays] = useState<number>(30);

  const getAuthToken = async (): Promise<string | null> => {
    try {
      const authData = localStorage.getItem("intelia-expert-auth");
      if (authData) {
        const parsed = JSON.parse(authData);
        return parsed.access_token || null;
      }
      return null;
    } catch (error) {
      secureLog.error("Erreur récupération token:", error);
      return null;
    }
  };

  const handleCreateShare = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const token = await getAuthToken();
      if (!token) {
        throw new Error("Non authentifié. Veuillez vous connecter.");
      }

      const response = await fetch(
        `https://expert.intelia.com/api/v1/conversations/${conversationId}/share`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            share_type: "public",
            anonymize: false,
            expires_in_days: expiresInDays,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || t("share.error"));
      }

      const data = await response.json();
      setShareData(data);

      if (onShareCreated) {
        onShareCreated(data.share_url);
      }
    } catch (err: any) {
      setError(err.message || "Une erreur est survenue");
      secureLog.error("Erreur création partage:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyLink = async () => {
    if (!shareData) return;

    try {
      await navigator.clipboard.writeText(shareData.share_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      secureLog.error("Erreur copie:", err);
      setError("Impossible de copier le lien");
    }
  };

  const handleClose = () => {
    setIsModalOpen(false);
    setShareData(null);
    setError(null);
    setCopied(false);
    // Reset des options
    setExpiresInDays(30);
  };

  return (
    <>
      {/* Bouton pour ouvrir le modal */}
      <button
        onClick={() => setIsModalOpen(true)}
        className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
        title={t("share.modalTitle")}
      >
        <Share2 size={16} />
        <span>{t("share.button")}</span>
      </button>

      {/* Modal de partage */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-semibold text-gray-900">
                {t("share.modalTitle")}
              </h3>
              <button
                onClick={handleClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Content */}
            <div className="p-4">
              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}

              {!shareData ? (
                // Formulaire de configuration
                <div className="space-y-4">
                  <div className="space-y-3">
                    {/* Option expiration */}
                    <div>
                      <label className="block font-medium text-gray-900 mb-2">
                        {t("share.expiration")}
                      </label>
                      <select
                        value={expiresInDays}
                        onChange={(e) => setExpiresInDays(parseInt(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="7">{t("share.expiration.7days")}</option>
                        <option value="30">{t("share.expiration.30days")}</option>
                        <option value="90">{t("share.expiration.90days")}</option>
                      </select>
                    </div>
                  </div>

                  <button
                    onClick={handleCreateShare}
                    disabled={isLoading}
                    className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                  >
                    {isLoading ? t("share.generating") : t("share.generate")}
                  </button>
                </div>
              ) : (
                // Affichage du lien généré
                <div className="space-y-4">
                  <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center gap-2 text-green-700 font-medium mb-2">
                      <Check size={18} />
                      <span>{t("share.successTitle")}</span>
                    </div>
                    <div className="text-sm text-green-600">
                      {t("share.successMessage")}
                    </div>
                  </div>

                  {/* Lien */}
                  <div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={shareData.share_url}
                        readOnly
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm"
                      />
                      <button
                        onClick={handleCopyLink}
                        className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-2"
                        title={t("share.copy")}
                      >
                        {copied ? (
                          <>
                            <Check size={16} className="text-green-600" />
                            <span className="text-sm">{t("share.copied")}</span>
                          </>
                        ) : (
                          <>
                            <Copy size={16} />
                            <span className="text-sm">{t("share.copy")}</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Informations */}
                  <div className="space-y-2 text-sm text-gray-600">
                    {shareData.expires_at && (
                      <div className="flex items-center gap-2">
                        <Clock size={14} />
                        <span>
                          Expire le{" "}
                          {new Date(shareData.expires_at).toLocaleDateString("fr-FR")}
                        </span>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={handleClose}
                    className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    {t("modal.close")}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ShareConversationButton;
