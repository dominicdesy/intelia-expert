"use client";

import React, { useState } from "react";
import { BaseDialog } from "../BaseDialog";
import { PLAN_CONFIGS } from "@/types";
import { redirectToCheckout } from "@/lib/api/stripe";
import { useTranslation } from "@/lib/languages/i18n";
import toast from "react-hot-toast";

interface UpgradePlanModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentPlan?: string;
}

export const UpgradePlanModal: React.FC<UpgradePlanModalProps> = ({
  isOpen,
  onClose,
  currentPlan = "essential",
}) => {
  const { t, currentLanguage } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);

  const handleUpgrade = async (planName: string) => {
    setIsLoading(true);
    setSelectedPlan(planName);

    try {
      // Récupérer le token JWT
      const token = localStorage.getItem("access_token");
      if (!token) {
        toast.error(t("chat.sessionExpired"));
        return;
      }

      // Rediriger vers Stripe Checkout avec la langue utilisateur
      await redirectToCheckout(planName, token, currentLanguage);
    } catch (error) {
      console.error("[UpgradePlan] Erreur:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : t("stripe.upgrade.error")
      );
      setIsLoading(false);
      setSelectedPlan(null);
    }
  };

  const plans = Object.entries(PLAN_CONFIGS).filter(
    ([key]) => key !== "essential"
  );

  return (
    <BaseDialog
      isOpen={isOpen}
      onClose={onClose}
      title={t("stripe.upgrade.title")}
    >
      <div className="space-y-6">
        {/* Description */}
        <div className="text-center text-sm text-gray-600">
          {t("stripe.upgrade.choosePlan")}
        </div>

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {plans.map(([planKey, planConfig]) => {
            const isCurrentPlan = currentPlan === planKey;
            const isSelected = selectedPlan === planKey;

            return (
              <div
                key={planKey}
                className={`
                  p-6 rounded-lg border-2 transition-all
                  ${isCurrentPlan ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:shadow-lg"}
                  ${planConfig.borderColor}
                  ${planConfig.bgColor}
                  ${isSelected ? "ring-2 ring-offset-2 ring-blue-500" : ""}
                `}
                onClick={() => !isCurrentPlan && !isLoading && setSelectedPlan(planKey)}
              >
                {/* Badge Plan Actuel */}
                {isCurrentPlan && (
                  <div className="mb-3">
                    <span className="inline-block px-3 py-1 text-xs font-semibold bg-green-100 text-green-800 rounded-full">
                      {t("stripe.upgrade.currentPlanBadge")}
                    </span>
                  </div>
                )}

                {/* Nom du Plan */}
                <h3 className={`text-2xl font-bold ${planConfig.color} mb-2`}>
                  {planConfig.name}
                </h3>

                {/* Prix */}
                <div className="mb-4">
                  <span className="text-3xl font-bold text-gray-900">
                    ${planConfig.price}
                  </span>
                  <span className="text-gray-600">{t("stripe.upgrade.perMonth")}</span>
                </div>

                {/* Features */}
                <ul className="space-y-2 mb-6">
                  {planConfig.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start text-sm text-gray-700">
                      <span className="text-green-500 mr-2 mt-0.5">✓</span>
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* Bouton */}
                {!isCurrentPlan && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleUpgrade(planKey);
                    }}
                    disabled={isLoading}
                    className={`
                      w-full py-3 px-4 rounded-md font-medium transition-colors
                      ${
                        isLoading && isSelected
                          ? "bg-gray-400 cursor-not-allowed"
                          : "bg-blue-600 hover:bg-blue-700 text-white"
                      }
                    `}
                  >
                    {isLoading && isSelected ? (
                      <span className="flex items-center justify-center">
                        <svg
                          className="animate-spin h-5 w-5 mr-2"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                            fill="none"
                          />
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          />
                        </svg>
                        {t("stripe.upgrade.redirecting")}
                      </span>
                    ) : (
                      t("stripe.upgrade.selectPlan")
                    )}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* Informations supplémentaires */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start">
            <span className="text-blue-600 text-xl mr-3">ℹ️</span>
            <div className="text-sm text-blue-900">
              <p className="font-medium mb-1">{t("stripe.upgrade.paymentSecure")}</p>
              <ul className="list-disc list-inside space-y-1 text-blue-800">
                <li>{t("stripe.upgrade.stripeLink")}</li>
                <li>{t("stripe.upgrade.cancelAnytime")}</li>
                <li>{t("stripe.upgrade.monthlyBilling")}</li>
                <li>{t("stripe.upgrade.noCommitment")}</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Bouton Fermer */}
        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
          >
            {t("ui.close")}
          </button>
        </div>
      </div>
    </BaseDialog>
  );
};
