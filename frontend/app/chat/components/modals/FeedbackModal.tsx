import React, { useState } from "react";
import { useTranslation } from "@/lib/languages/i18n";
import { ThumbUpIcon, ThumbDownIcon } from "../../utils/icons";

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (
    feedback: "positive" | "negative",
    comment?: string,
  ) => Promise<void>;
  feedbackType: "positive" | "negative";
  isSubmitting?: boolean;
}

export const FeedbackModal = ({
  isOpen,
  onClose,
  onSubmit,
  feedbackType,
  isSubmitting = false,
}: FeedbackModalProps) => {
  const { t } = useTranslation();
  const [comment, setComment] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    setIsLoading(true);
    try {
      await onSubmit(feedbackType, comment.trim() || undefined);
      setComment("");
      onClose(); // ✅ Fermer la modal après succès
    } catch (error) {
      console.error(t("feedback.sendError"), error);
      // ✅ CORRECTION: Fermer la modal même en cas d'erreur
      setComment("");
      onClose();
      // Ne pas afficher d'alert ici, laisser la fonction parent gérer
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setComment("");
    onClose();
  };

  const isPositive = feedbackType === "positive";
  const title = isPositive
    ? t("feedback.positiveTitle")
    : t("feedback.negativeTitle");
  const placeholder = isPositive
    ? t("feedback.positivePlaceholder")
    : t("feedback.negativePlaceholder");

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-50"
        onClick={handleCancel}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-6 pb-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                {isPositive ? (
                  <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                    {/* ✅ ICÔNE THUMBS UP du chat */}
                    <div className="text-green-600">
                      <ThumbUpIcon />
                    </div>
                  </div>
                ) : (
                  <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                    {/* ✅ ICÔNE THUMBS DOWN du chat */}
                    <div className="text-red-600">
                      <ThumbDownIcon />
                    </div>
                  </div>
                )}
                <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
              </div>

              <button
                onClick={handleCancel}
                className="text-gray-400 hover:text-gray-600 transition-colors"
                disabled={isLoading}
                aria-label={t("modal.close")}
                title={t("modal.close")}
              >
                <svg
                  className="w-6 h-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {/* Description */}
            <p className="text-sm text-gray-600 mb-4">
              {t("feedback.description")}
            </p>

            {/* Textarea de commentaire */}
            <div className="mb-4">
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder={placeholder}
                rows={4}
                maxLength={500}
                className="w-full px-4 py-3 border-2 border-blue-200 rounded-xl focus:border-blue-500 focus:ring-0 outline-none resize-none text-sm placeholder-gray-400 transition-colors"
                disabled={isLoading}
              />
              <div className="flex justify-between items-center mt-2">
                <div className="text-xs text-gray-400">
                  {`${t("feedback.characterCount")}: ${comment.length}/500`}
                </div>
                {comment.length > 450 && (
                  <div className="text-xs text-orange-500">
                    {t("feedback.limitWarning")}
                  </div>
                )}
              </div>
            </div>

            {/* Note de confidentialité */}
            <div className="mb-6">
              <p className="text-xs text-gray-500 leading-relaxed">
                {t("feedback.privacyNotice")}{" "}
                <button
                  type="button"
                  className="text-blue-600 hover:text-blue-700 underline font-medium"
                  onClick={() =>
                    window.open("https://intelia.com/privacy-policy/", "_blank")
                  }
                >
                  {t("feedback.learnMore")}
                </button>
              </p>
            </div>
          </div>

          {/* Footer avec boutons */}
          <div className="px-6 py-4 bg-gray-50 rounded-b-2xl">
            <div className="flex justify-end space-x-3">
              <button
                onClick={handleCancel}
                disabled={isLoading}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t("modal.cancel")}
              </button>

              <button
                onClick={handleSubmit}
                disabled={isLoading}
                className="px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 min-w-[100px] justify-center"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>{t("feedback.sending")}</span>
                  </>
                ) : (
                  <span>{t("feedback.send")}</span>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
