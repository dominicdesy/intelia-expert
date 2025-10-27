/**
 * SatisfactionSurvey Component
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
/**
 * SatisfactionSurvey Component
 * ============================
 *
 * Sondage de satisfaction globale affiché après ~25 puis ~40 messages
 * Apparaît juste au-dessus du champ "Type your message"
 *
 * Features:
 * - 3 options: 😊 Satisfied | 😐 Neutral | 🙁 Unsatisfied
 * - Champ commentaire optionnel
 * - Animation d'apparition/disparition
 * - Sauvegarde dans PostgreSQL
 * - Skip possible
 */

"use client";

import React, { useState } from "react";
import { useTranslation } from "@/lib/languages/i18n";

interface SatisfactionSurveyProps {
  conversationId: string;
  userId: string;
  messageCount: number;
  onComplete: () => void;
  onSkip: () => void;
}

export const SatisfactionSurvey: React.FC<SatisfactionSurveyProps> = ({
  conversationId,
  userId,
  messageCount,
  onComplete,
  onSkip,
}) => {
  const { t } = useTranslation();
  const [selectedRating, setSelectedRating] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [showComment, setShowComment] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleRatingClick = async (rating: string) => {
    setSelectedRating(rating);

    // Si insatisfait, montrer le champ commentaire
    if (rating === "unsatisfied") {
      setShowComment(true);
      return; // Ne pas soumettre immédiatement
    }

    // Sinon, soumettre directement
    await submitSurvey(rating, "");
  };

  const submitSurvey = async (rating: string, userComment: string) => {
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/v1/satisfaction/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          user_id: userId,
          rating,
          comment: userComment || null,
          message_count: messageCount,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to submit survey");
      }

      // Succès - Afficher message de remerciement
      setIsSuccess(true);

      // Disparaître après 3 secondes
      setTimeout(() => {
        onComplete();
      }, 3000);
    } catch (error) {
      console.error("Error submitting satisfaction survey:", error);
      // En cas d'erreur, fermer quand même pour ne pas bloquer l'utilisateur
      setTimeout(onComplete, 2000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCommentSubmit = async () => {
    if (selectedRating) {
      await submitSurvey(selectedRating, comment);
    }
  };

  // Message de succès
  if (isSuccess) {
    return (
      <div className="mb-3 p-4 bg-green-50 border border-green-200 rounded-lg shadow-sm animate-fade-in">
        <div className="text-center">
          <div className="text-2xl mb-2">✅</div>
          <div className="text-green-800 font-medium">
            {t("chat.satisfactionThanks") || "Thank you for your feedback!"}
          </div>
          <div className="text-green-600 text-sm mt-1">
            {t("chat.satisfactionHelpful") || "Your rating helps us improve Intelia Expert."}
          </div>
        </div>
      </div>
    );
  }

  // Formulaire de sondage
  return (
    <div className="mb-3 p-4 bg-blue-50 border border-blue-200 rounded-lg shadow-sm animate-slide-up">
      <div className="text-center mb-3">
        <div className="text-lg font-medium text-gray-900 mb-1">
          🌟 {t("chat.satisfactionQuestion") || "Before you go — could you rate your experience today?"}
        </div>
      </div>

      {/* Boutons de rating */}
      {!showComment && (
        <div className="flex items-center justify-center gap-3 mb-3">
          {/* Satisfied */}
          <button
            onClick={() => handleRatingClick("satisfied")}
            disabled={isSubmitting}
            className="flex flex-col items-center justify-center p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition-all active:scale-95 disabled:opacity-50 min-w-[100px] sm:min-w-[120px]"
            title={t("chat.satisfactionSatisfied") || "Satisfied"}
          >
            <div className="text-3xl mb-2">😊</div>
            <div className="text-sm font-medium text-gray-700">
              {t("chat.satisfactionSatisfied") || "Satisfied"}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {t("chat.satisfactionHelpful") || "Helpful"}
            </div>
          </button>

          {/* Neutral */}
          <button
            onClick={() => handleRatingClick("neutral")}
            disabled={isSubmitting}
            className="flex flex-col items-center justify-center p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-yellow-500 hover:bg-yellow-50 transition-all active:scale-95 disabled:opacity-50 min-w-[100px] sm:min-w-[120px]"
            title={t("chat.satisfactionNeutral") || "Neutral"}
          >
            <div className="text-3xl mb-2">😐</div>
            <div className="text-sm font-medium text-gray-700">
              {t("chat.satisfactionNeutral") || "Neutral"}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {t("chat.satisfactionOkay") || "Okay"}
            </div>
          </button>

          {/* Unsatisfied */}
          <button
            onClick={() => handleRatingClick("unsatisfied")}
            disabled={isSubmitting}
            className="flex flex-col items-center justify-center p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-red-500 hover:bg-red-50 transition-all active:scale-95 disabled:opacity-50 min-w-[100px] sm:min-w-[120px]"
            title={t("chat.satisfactionUnsatisfied") || "Unsatisfied"}
          >
            <div className="text-3xl mb-2">🙁</div>
            <div className="text-sm font-medium text-gray-700">
              {t("chat.satisfactionUnsatisfied") || "Unsatisfied"}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {t("chat.satisfactionPoor") || "Poor"}
            </div>
          </button>
        </div>
      )}

      {/* Champ commentaire (si insatisfait) */}
      {showComment && (
        <div className="mb-3 animate-fade-in">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            💬 {t("chat.satisfactionCommentPrompt") || "Tell us more (optional):"}
          </label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={t("chat.satisfactionCommentPlaceholder") || "What could we improve?"}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
            rows={3}
            maxLength={500}
          />
          <div className="flex items-center justify-end gap-2 mt-2">
            <button
              onClick={() => setShowComment(false)}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            >
              {t("modal.cancel") || "Cancel"}
            </button>
            <button
              onClick={handleCommentSubmit}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (t("chat.sending") || "Sending...") : (t("chat.submit") || "Submit")}
            </button>
          </div>
        </div>
      )}

      {/* Bouton Skip */}
      {!showComment && (
        <div className="text-center">
          <button
            onClick={onSkip}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            {t("chat.satisfactionSkip") || "Skip this survey"}
          </button>
        </div>
      )}
    </div>
  );
};
