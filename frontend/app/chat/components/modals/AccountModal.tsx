"use client";

import React, { useState } from "react";
import { useTranslation } from "@/lib/languages/i18n";
import { PLAN_CONFIGS } from "@/types";
import { BaseDialog } from "../BaseDialog";
import { UpgradePlanModal } from "./UpgradePlanModal";
import { redirectToCustomerPortal } from "@/lib/api/stripe";
import toast from "react-hot-toast";

interface AccountModalProps {
  isOpen: boolean;
  user: any;
  onClose: () => void;
}

export const AccountModal: React.FC<AccountModalProps> = ({
  isOpen,
  user,
  onClose,
}) => {
  const { t } = useTranslation();
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [isManaging, setIsManaging] = useState(false);

  const currentPlan = user?.plan || "essential";
  const userPlan = PLAN_CONFIGS[currentPlan as keyof typeof PLAN_CONFIGS] || PLAN_CONFIGS.essential;

  const handleManageSubscription = async () => {
    setIsManaging(true);
    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        toast.error(t("chat.sessionExpired"));
        return;
      }

      await redirectToCustomerPortal(token);
    } catch (error) {
      console.error("[AccountModal] Erreur portail:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : t("stripe.portal.error")
      );
      setIsManaging(false);
    }
  };

  return (
    <>
      <BaseDialog isOpen={isOpen} onClose={onClose} title={t("subscription.title")}>
        <div className="space-y-6">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {t("subscription.currentPlan")}
            </h3>
            <div
              className={`inline-flex items-center px-4 py-2 rounded-full ${userPlan.bgColor} ${userPlan.borderColor} border`}
            >
              <span className={`font-medium ${userPlan.color}`}>
                {userPlan.name}
              </span>
              <span className="mx-2 text-gray-400">•</span>
              <span className={`font-bold ${userPlan.color}`}>
                {currentPlan === "essential"
                  ? t("subscription.free")
                  : `$${userPlan.price}${t("stripe.upgrade.perMonth")}`}
              </span>
            </div>
          </div>

          <div
            className={`p-4 rounded-lg ${userPlan.bgColor} ${userPlan.borderColor} border`}
          >
            <h4 className="font-medium text-gray-900 mb-3">
              {t("subscription.featuresIncluded")}:
            </h4>
            <ul className="space-y-2">
              {userPlan.features.map((feature, index) => (
                <li
                  key={index}
                  className="flex items-center text-sm text-gray-700"
                >
                  <span className="text-green-500 mr-2">✓</span>
                  {feature}
                </li>
              ))}
            </ul>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3">
            {currentPlan === "essential" && (
              <button
                onClick={() => setShowUpgradeModal(true)}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium"
              >
                {t("stripe.account.upgradeButton")}
              </button>
            )}

            {currentPlan !== "essential" && (
              <button
                onClick={handleManageSubscription}
                disabled={isManaging}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isManaging ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
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
                    {t("common.loading")}
                  </span>
                ) : (
                  t("stripe.account.manageSubscription")
                )}
              </button>
            )}

            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            >
              {t("modal.close")}
            </button>
          </div>
        </div>
      </BaseDialog>

      {/* Upgrade Modal */}
      <UpgradePlanModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
        currentPlan={currentPlan}
      />
    </>
  );
};
