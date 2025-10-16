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

  // Map "free" to "essential" for backwards compatibility
  const currentPlan = user?.plan === "free" ? "essential" : (user?.plan || "essential");
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

  const handleContactUs = () => {
    window.location.href = "mailto:support@intelia.com?subject=" + encodeURIComponent(t("contact.corporatePlanSubject"));
  };

  const plans = Object.entries(PLAN_CONFIGS).map(([key, config]) => ({
    key,
    ...config,
  }));

  return (
    <>
      <BaseDialog isOpen={isOpen} onClose={onClose} title={t("subscription.title")}>
        <div className="space-y-8">
          {/* Current Plan Badge */}
          <div className="text-center">
            <p className="text-sm text-gray-600 mb-2">{t("plan.currentPlan")}</p>
            <div
              className={`inline-flex items-center px-4 py-2 rounded-full ${userPlan.bgColor} ${userPlan.borderColor} border`}
            >
              <span className={`font-semibold ${userPlan.color}`}>
                {t(`plan.${currentPlan}` as any)}
              </span>
            </div>
          </div>

          {/* Pricing Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {plans.map((plan) => {
              const isCurrentPlan = plan.key === currentPlan;
              const isCorporate = plan.key === "corporate";

              return (
                <div
                  key={plan.key}
                  className={`relative rounded-lg border-2 p-6 flex flex-col ${
                    isCurrentPlan
                      ? `${plan.borderColor} ${plan.bgColor}`
                      : "border-gray-200 bg-white hover:border-gray-300"
                  } transition-all duration-200`}
                >
                  {/* Popular Badge */}
                  {plan.popular && !isCurrentPlan && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                      <span className="bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                        {t("plan.popular")}
                      </span>
                    </div>
                  )}

                  {/* Current Plan Badge */}
                  {isCurrentPlan && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                      <span className={`${plan.color} ${plan.bgColor} border ${plan.borderColor} text-xs font-semibold px-3 py-1 rounded-full`}>
                        {t("plan.currentPlan")}
                      </span>
                    </div>
                  )}

                  {/* Plan Header */}
                  <div className="mb-4">
                    <h3 className={`text-lg font-bold mb-1 ${plan.color}`}>
                      {t(`plan.${plan.key}` as any)}
                    </h3>
                    <p className="text-sm text-gray-600">
                      {t(`plan.${plan.key}.description` as any)}
                    </p>
                  </div>

                  {/* Price */}
                  <div className="mb-6">
                    {plan.price === null ? (
                      <div className="text-2xl font-bold text-gray-900">
                        {t("plan.contactUs")}
                      </div>
                    ) : plan.price === 0 ? (
                      <div className="text-2xl font-bold text-gray-900">
                        {t("plan.essential")}
                      </div>
                    ) : (
                      <div>
                        <span className="text-3xl font-bold text-gray-900">
                          ${plan.price}
                        </span>
                        <span className="text-gray-600 text-sm ml-1">
                          {t("plan.perMonth")}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Features List */}
                  <ul className="space-y-3 mb-6 flex-grow">
                    {plan.features.map((feature, index) => (
                      <li key={index} className="flex items-start text-sm">
                        <svg
                          className={`w-5 h-5 ${plan.color} mr-2 flex-shrink-0 mt-0.5`}
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
                        <span className="text-gray-700">{t(feature as any)}</span>
                      </li>
                    ))}
                  </ul>

                  {/* CTA Button */}
                  <div className="mt-auto">
                    {isCurrentPlan && !isCorporate && (
                      <button
                        onClick={handleManageSubscription}
                        disabled={isManaging}
                        className={`w-full px-4 py-3 rounded-lg font-medium transition-colors ${plan.color} ${plan.bgColor} border ${plan.borderColor} hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed`}
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

                    {!isCurrentPlan && isCorporate && (
                      <button
                        onClick={handleContactUs}
                        className="w-full px-4 py-3 bg-orange-600 text-white rounded-lg font-medium hover:bg-orange-700 transition-colors"
                      >
                        {t("plan.contactUs")}
                      </button>
                    )}

                    {!isCurrentPlan && !isCorporate && (
                      <button
                        onClick={() => setShowUpgradeModal(true)}
                        className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
                      >
                        {t("stripe.account.upgradePlan")}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Close Button */}
          <div className="flex justify-center pt-4">
            <button
              onClick={onClose}
              className="px-6 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
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
