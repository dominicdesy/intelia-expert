"use client";

import React, { useState } from "react";
import { useTranslation } from "@/lib/languages/i18n";
import { BaseDialog } from "../BaseDialog";
import { CurrencySelector } from "./CurrencySelector";
import { redirectToCheckout, redirectToCustomerPortal } from "@/lib/api/stripe";
import { supabase } from "@/lib/supabase/client";
import { Check, X } from "lucide-react";
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
  const { t, currentLanguage } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">("monthly");
  const [isManaging, setIsManaging] = useState(false);

  // Map free plan to essential for backwards compatibility
  const currentPlan = user?.plan === "free" ? "essential" : (user?.plan || "essential");

  // Prix mensuels
  const monthlyPrices = { essential: 0, pro: 18, elite: 28 };

  // Prix annuels (15% de rabais)
  const yearlyPrices = {
    essential: 0,
    pro: Math.round(18 * 12 * 0.85 * 100) / 100, // 183.60
    elite: Math.round(28 * 12 * 0.85 * 100) / 100, // 285.60
  };

  const prices = billingCycle === "monthly" ? monthlyPrices : yearlyPrices;

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
      console.error("[AccountModal] portal error:", error);
      toast.error(error instanceof Error ? error.message : t("stripe.portal.error"));
      setIsManaging(false);
    }
  };

  const handleUpgrade = async (planName: string) => {
    setIsLoading(true);
    setSelectedPlan(planName);

    try {
      let accessToken: string | null = null;

      const authData = localStorage.getItem("intelia-expert-auth");
      if (authData) {
        try {
          const parsed = JSON.parse(authData);
          accessToken = parsed.access_token;
        } catch (e) {
          console.error("[AccountModal] parse error:", e);
        }
      }

      if (!accessToken) {
        const { data: { session }, error } = await supabase.auth.getSession();
        if (!error && session?.access_token) {
          accessToken = session.access_token;
        }
      }

      if (!accessToken) {
        toast.error(t("chat.sessionExpired"));
        setIsLoading(false);
        setSelectedPlan(null);
        return;
      }

      const fullPlanName = billingCycle === "yearly" ? `${planName}_yearly` : planName;
      await redirectToCheckout(fullPlanName, accessToken, currentLanguage);
    } catch (error) {
      console.error("[AccountModal] checkout error:", error);
      toast.error(error instanceof Error ? error.message : "Erreur lors de la redirection");
      setIsLoading(false);
      setSelectedPlan(null);
    }
  };

  return (
    <BaseDialog
      isOpen={isOpen}
      onClose={onClose}
      title={t("subscription.title")}
      description=""
      maxWidth="max-w-7xl"
    >
      <div className="mx-auto max-w-[1200px] space-y-8 px-6">
        {/* Currency Selector */}
        {user && <CurrencySelector user={user} />}

        {/* Billing Toggle */}
        <div className="flex items-center justify-center gap-4 py-1 text-sm">
          <span className={`font-medium ${billingCycle === "monthly" ? "text-gray-900" : "text-gray-500"}`}>
            {t("billing.monthly")}
          </span>
          <button
            aria-label="Basculer le cycle de facturation"
            onClick={() => setBillingCycle(billingCycle === "monthly" ? "yearly" : "monthly")}
            className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${billingCycle === "yearly" ? "bg-emerald-500" : "bg-gray-300"}`}
          >
            <span
              className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${billingCycle === "yearly" ? "translate-x-7" : "translate-x-2"}`}
            />
          </button>
          <span className={`font-medium ${billingCycle === "yearly" ? "text-gray-900" : "text-gray-500"}`}>
            {t("billing.yearly")}
          </span>
          {billingCycle === "yearly" && (
            <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
              {t("billing.discount15")}
            </span>
          )}
        </div>

        {/* Plans */}
        <section
          aria-label="Plans d’abonnement"
          className="grid grid-cols-1 gap-6 md:grid-cols-3"
        >
          {/* Essential */}
          <article
            className="relative rounded-2xl bg-white p-6 shadow-sm transition-all hover:-translate-y-1 hover:shadow-md border"
            style={{ borderColor: '#e5e7eb' }}
          >
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="rounded-full px-3 py-1 text-[11px] font-semibold uppercase shadow-sm" style={{ backgroundColor: '#f3f4f6', color: '#374151' }}>
                {t("billing.free")}
              </span>
            </div>

            <header className="mb-6 mt-1 text-center">
              <h3 className="mb-1 text-2xl font-bold" style={{ color: '#374151' }}>Essential</h3>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-4xl font-bold" style={{ color: '#111827' }}>0</span>
                <span className="text-xl" style={{ color: '#6b7280' }}>$</span>
                <span className="text-sm" style={{ color: '#6b7280' }}>/ mois</span>
              </div>
            </header>

            <button
              disabled
              className="w-full rounded-lg py-3 font-semibold"
              style={{ backgroundColor: '#6b7280', color: '#ffffff' }}
            >
              {currentPlan === "essential" ? t("billing.currentPlan") : t("billing.freePlan")}
            </button>
          </article>

          {/* Pro (featured) */}
          <article
            className="relative rounded-2xl p-6 shadow-[0_8px_24px_rgba(34,106,228,.12)] transition-all hover:-translate-y-1 border-2"
            style={{
              background: 'linear-gradient(to bottom, rgba(34,106,228,0.06), #ffffff)',
              borderColor: '#226ae4'
            }}
          >
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="rounded-full px-3 py-1 text-[11px] font-semibold uppercase text-white shadow" style={{ backgroundColor: '#226ae4' }}>
                {t("billing.popular")}
              </span>
            </div>

            <header className="mb-6 mt-1 text-center">
              <h3 className="mb-1 text-2xl font-bold" style={{ color: '#1240a4' }}>Pro</h3>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-4xl font-bold" style={{ color: '#111827' }}>
                  {billingCycle === "monthly" ? prices.pro.toFixed(2) : (prices.pro / 12).toFixed(2)}
                </span>
                <span className="text-xl" style={{ color: '#6b7280' }}>$</span>
                <span className="text-sm" style={{ color: '#6b7280' }}>/ {billingCycle === "monthly" ? "mois" : "an"}</span>
              </div>
              {billingCycle === "yearly" && (
                <p className="mt-1 text-xs" style={{ color: '#1240a4' }}>
                  Soit {(prices.pro / 12).toFixed(2)} $/mois
                </p>
              )}
              <p className="mt-2 text-xs font-medium" style={{ color: '#1240a4' }}>{t("billing.trial14days")}</p>
            </header>

            {currentPlan === "pro" ? (
              <button
                onClick={handleManageSubscription}
                disabled={isManaging}
                className="w-full rounded-lg py-3 font-semibold text-white transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                style={{ backgroundColor: '#226ae4' }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#1240a4'}
                onMouseLeave={(e) => !isManaging && (e.currentTarget.style.backgroundColor = '#226ae4')}
              >
                {isManaging ? t("billing.loading") : t("billing.manageSubscription")}
              </button>
            ) : (
              <button
                onClick={() => handleUpgrade("pro")}
                disabled={isLoading}
                className="w-full rounded-lg py-3 font-semibold text-white shadow-md transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                style={{ backgroundColor: '#226ae4' }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#1240a4'}
                onMouseLeave={(e) => !isLoading && (e.currentTarget.style.backgroundColor = '#226ae4')}
              >
                {isLoading && selectedPlan === "pro" ? t("billing.redirecting") : t("billing.startFreeTrial")}
              </button>
            )}
          </article>

          {/* Elite */}
          <article
            className="relative rounded-2xl p-6 shadow-[0_8px_24px_rgba(228,126,58,.15)] transition-all hover:-translate-y-1 border-2"
            style={{
              background: 'linear-gradient(to bottom, rgba(228,126,58,0.06), #ffffff)',
              borderColor: '#e47e3a'
            }}
          >
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="rounded-full px-3 py-1 text-[11px] font-semibold uppercase text-white shadow" style={{ backgroundColor: '#e47e3a' }}>
                {t("billing.recommended")}
              </span>
            </div>

            <header className="mb-6 mt-1 text-center">
              <h3 className="mb-1 text-2xl font-bold" style={{ color: '#e47e3a' }}>Elite</h3>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-4xl font-bold" style={{ color: '#111827' }}>
                  {billingCycle === "monthly" ? prices.elite.toFixed(2) : (prices.elite / 12).toFixed(2)}
                </span>
                <span className="text-xl" style={{ color: '#6b7280' }}>$</span>
                <span className="text-sm" style={{ color: '#6b7280' }}>/ {billingCycle === "monthly" ? "mois" : "an"}</span>
              </div>
              {billingCycle === "yearly" && (
                <p className="mt-1 text-xs" style={{ color: '#e47e3a' }}>
                  Soit {(prices.elite / 12).toFixed(2)} $/mois
                </p>
              )}
              <p className="mt-2 text-xs font-medium" style={{ color: '#e47e3a' }}>{t("billing.trial14days")}</p>
            </header>

            {currentPlan === "elite" ? (
              <button
                onClick={handleManageSubscription}
                disabled={isManaging}
                className="w-full rounded-lg py-3 font-semibold text-white transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                style={{ backgroundColor: '#e47e3a' }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#cc6f33'}
                onMouseLeave={(e) => !isManaging && (e.currentTarget.style.backgroundColor = '#e47e3a')}
              >
                {isManaging ? t("billing.loading") : t("billing.manageSubscription")}
              </button>
            ) : (
              <button
                onClick={() => handleUpgrade("elite")}
                disabled={isLoading}
                className="w-full rounded-lg py-3 font-semibold text-white shadow-md transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                style={{ backgroundColor: '#e47e3a' }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#cc6f33'}
                onMouseLeave={(e) => !isLoading && (e.currentTarget.style.backgroundColor = '#e47e3a')}
              >
                {isLoading && selectedPlan === "elite" ? t("billing.redirecting") : t("billing.startFreeTrial")}
              </button>
            )}
          </article>
        </section>

        {/* Comparison */}
        <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-6 text-center text-xl font-bold text-gray-900">
            {t("subscription.comparison.title")}
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">{t("subscription.comparison.feature")}</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold" style={{ color: '#374151' }}>{t("subscription.comparison.essential")}</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold" style={{ color: '#1240a4', backgroundColor: 'rgba(34,106,228,0.06)' }}>{t("subscription.comparison.pro")}</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold" style={{ color: '#e47e3a', backgroundColor: 'rgba(228,126,58,0.06)' }}>{t("subscription.comparison.elite")}</th>
                </tr>
              </thead>
              <tbody>
                {/* Base features */}
                <tr>
                  <td colSpan={4} className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-600 bg-gray-50">
                    {t("subscription.comparison.category.base")}
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">{t("subscription.comparison.feature.languages")}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
                        <Check className="h-4 w-4" style={{ color: '#2cc780' }} />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center" style={{ backgroundColor: 'rgba(34,106,228,0.06)' }}>
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
                        <Check className="h-4 w-4" style={{ color: '#2cc780' }} />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center" style={{ backgroundColor: 'rgba(228,126,58,0.06)' }}>
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
                        <Check className="h-4 w-4" style={{ color: '#2cc780' }} />
                      </div>
                    </div>
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">{t("subscription.comparison.feature.roleAdaptation")}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
                        <Check className="h-4 w-4" style={{ color: '#2cc780' }} />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center" style={{ backgroundColor: 'rgba(34,106,228,0.06)' }}>
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
                        <Check className="h-4 w-4" style={{ color: '#2cc780' }} />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center" style={{ backgroundColor: 'rgba(228,126,58,0.06)' }}>
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
                        <Check className="h-4 w-4" style={{ color: '#2cc780' }} />
                      </div>
                    </div>
                  </td>
                </tr>

                {/* Capacités */}
                <tr>
                  <td colSpan={4} className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-600 bg-gray-50">
                    {t("subscription.comparison.category.capacity")}
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">{t("subscription.comparison.feature.queries")}</td>
                  <td className="px-4 py-3 text-center text-sm" style={{ color: '#374151' }}>{t("subscription.comparison.value.100")}</td>
                  <td className="px-4 py-3 text-center text-sm font-semibold" style={{ color: '#1240a4', backgroundColor: 'rgba(34,106,228,0.06)' }}>{t("subscription.comparison.value.unlimitedStar")}</td>
                  <td className="px-4 py-3 text-center text-sm font-semibold" style={{ color: '#e47e3a', backgroundColor: 'rgba(228,126,58,0.06)' }}>{t("subscription.comparison.value.unlimitedStar")}</td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">{t("subscription.comparison.feature.history")}</td>
                  <td className="px-4 py-3 text-center text-sm" style={{ color: '#374151' }}>{t("subscription.comparison.value.30days")}</td>
                  <td className="px-4 py-3 text-center text-sm font-semibold" style={{ color: '#1240a4', backgroundColor: 'rgba(34,106,228,0.06)' }}>{t("subscription.comparison.value.unlimited")}</td>
                  <td className="px-4 py-3 text-center text-sm font-semibold" style={{ color: '#e47e3a', backgroundColor: 'rgba(228,126,58,0.06)' }}>{t("subscription.comparison.value.unlimited")}</td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">{t("subscription.comparison.feature.pdfExport")}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
                        <X className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center" style={{ backgroundColor: 'rgba(34,106,228,0.06)' }}>
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100">
                        <Check className="h-4 w-4 text-blue-700" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center" style={{ backgroundColor: 'rgba(228,126,58,0.06)' }}>
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100">
                        <Check className="h-4 w-4 text-amber-700" />
                      </div>
                    </div>
                  </td>
                </tr>

                {/* IA */}
                <tr>
                  <td colSpan={4} className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-600 bg-gray-50">
                    {t("subscription.comparison.category.ai")}
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">{t("subscription.comparison.feature.imageAnalysis")}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
                        <X className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center text-sm font-semibold" style={{ color: '#1240a4', backgroundColor: 'rgba(34,106,228,0.06)' }}>{t("subscription.comparison.value.25perMonth")}</td>
                  <td className="px-4 py-3 text-center text-sm font-semibold" style={{ color: '#e47e3a', backgroundColor: 'rgba(228,126,58,0.06)' }}>{t("subscription.comparison.value.unlimitedStar")}</td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">{t("subscription.comparison.feature.voiceInput")}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
                        <X className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center" style={{ backgroundColor: 'rgba(34,106,228,0.06)' }}>
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100">
                        <Check className="h-4 w-4 text-blue-700" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center" style={{ backgroundColor: 'rgba(228,126,58,0.06)' }}>
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100">
                        <Check className="h-4 w-4 text-amber-700" />
                      </div>
                    </div>
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">{t("subscription.comparison.feature.voiceAssistant")}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
                        <X className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center" style={{ backgroundColor: 'rgba(34,106,228,0.06)' }}>
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100">
                        <Check className="h-4 w-4 text-blue-700" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center" style={{ backgroundColor: 'rgba(228,126,58,0.06)' }}>
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100">
                        <Check className="h-4 w-4 text-amber-700" />
                      </div>
                    </div>
                  </td>
                </tr>

                {/* Expérience */}
                <tr>
                  <td colSpan={4} className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-600 bg-gray-50">
                    {t("subscription.comparison.category.experience")}
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">{t("subscription.comparison.feature.adFree")}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
                        <X className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center" style={{ backgroundColor: 'rgba(34,106,228,0.06)' }}>
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
                        <X className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center" style={{ backgroundColor: 'rgba(228,126,58,0.06)' }}>
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100">
                        <Check className="h-4 w-4 text-amber-700" />
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Notes */}
          <div className="mt-6 grid gap-3 text-xs text-gray-500 md:grid-cols-2">
            <div className="rounded-lg bg-gray-50 p-3">
              <span className="font-semibold text-gray-700">{t("billing.notes.trial")}</span>
              <div className="mt-1">{t("billing.notes.trialDesc")}</div>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <span className="font-semibold text-gray-700">{t("billing.notes.secure")}</span>
              <div className="mt-1">{t("billing.notes.secureDesc")}</div>
            </div>
          </div>

          <p className="mt-4 text-xs leading-5 text-gray-500">
            {t("billing.notes.unlimited")}
          </p>
        </section>
      </div>
    </BaseDialog>
  );
};

export default AccountModal;
