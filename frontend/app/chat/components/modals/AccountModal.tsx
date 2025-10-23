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
            Mensuel
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
            Annuel
          </span>
          {billingCycle === "yearly" && (
            <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
              -15%
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
            className="relative rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-all hover:-translate-y-1 hover:shadow-md"
          >
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="rounded-full bg-gray-100 px-3 py-1 text-[11px] font-semibold uppercase text-gray-700 shadow-sm">
                Gratuit
              </span>
            </div>

            <header className="mb-6 mt-1 text-center">
              <h3 className="mb-1 text-2xl font-bold text-gray-900">Essential</h3>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-4xl font-bold text-gray-900">0</span>
                <span className="text-xl text-gray-600">$</span>
                <span className="text-sm text-gray-500">/ mois</span>
              </div>
            </header>

            <button
              disabled
              className="w-full rounded-lg bg-gray-100 py-3 font-semibold text-gray-700"
            >
              {currentPlan === "essential" ? "Plan actuel" : "Plan gratuit"}
            </button>
          </article>

          {/* Pro (featured) */}
          <article
            className="relative rounded-2xl border-2 border-blue-500 bg-gradient-to-b from-blue-50 to-white p-6 shadow-[0_8px_24px_rgba(37,99,235,.12)] transition-all hover:-translate-y-1"
          >
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="rounded-full bg-gradient-to-r from-blue-600 to-blue-500 px-3 py-1 text-[11px] font-semibold uppercase text-white shadow">
                Populaire
              </span>
            </div>

            <header className="mb-6 mt-1 text-center">
              <h3 className="mb-1 text-2xl font-bold text-blue-700">Pro</h3>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-4xl font-bold text-gray-900">
                  {billingCycle === "monthly" ? prices.pro.toFixed(2) : (prices.pro / 12).toFixed(2)}
                </span>
                <span className="text-xl text-gray-600">$</span>
                <span className="text-sm text-gray-500">/ {billingCycle === "monthly" ? "mois" : "an"}</span>
              </div>
              {billingCycle === "yearly" && (
                <p className="mt-1 text-xs text-emerald-600">
                  Soit {(prices.pro / 12).toFixed(2)} $/mois
                </p>
              )}
              <p className="mt-2 text-xs font-medium text-blue-700">Essai gratuit de 14 jours</p>
            </header>

            {currentPlan === "pro" ? (
              <button
                onClick={handleManageSubscription}
                disabled={isManaging}
                className="w-full rounded-lg bg-blue-600 py-3 font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isManaging ? "Chargement..." : "Gérer mon abonnement"}
              </button>
            ) : (
              <button
                onClick={() => handleUpgrade("pro")}
                disabled={isLoading}
                className="w-full rounded-lg bg-blue-600 py-3 font-semibold text-white shadow-md transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isLoading && selectedPlan === "pro" ? "Redirection..." : "Commencer l’essai gratuit"}
              </button>
            )}
          </article>

          {/* Elite */}
          <article
            className="relative rounded-2xl border-2 border-amber-400 bg-gradient-to-b from-amber-50 to-white p-6 shadow-[0_8px_24px_rgba(245,158,11,.15)] transition-all hover:-translate-y-1"
          >
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="rounded-full bg-gradient-to-r from-amber-400 to-amber-500 px-3 py-1 text-[11px] font-semibold uppercase text-white shadow">
                Recommandé
              </span>
            </div>

            <header className="mb-6 mt-1 text-center">
              <h3 className="mb-1 text-2xl font-bold text-amber-700">Elite</h3>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-4xl font-bold text-gray-900">
                  {billingCycle === "monthly" ? prices.elite.toFixed(2) : (prices.elite / 12).toFixed(2)}
                </span>
                <span className="text-xl text-gray-600">$</span>
                <span className="text-sm text-gray-500">/ {billingCycle === "monthly" ? "mois" : "an"}</span>
              </div>
              {billingCycle === "yearly" && (
                <p className="mt-1 text-xs text-emerald-600">
                  Soit {(prices.elite / 12).toFixed(2)} $/mois
                </p>
              )}
              <p className="mt-2 text-xs font-medium text-blue-700">Essai gratuit de 14 jours</p>
            </header>

            {currentPlan === "elite" ? (
              <button
                onClick={handleManageSubscription}
                disabled={isManaging}
                className="w-full rounded-lg bg-amber-500 py-3 font-semibold text-white transition-colors hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isManaging ? "Chargement..." : "Gérer mon abonnement"}
              </button>
            ) : (
              <button
                onClick={() => handleUpgrade("elite")}
                disabled={isLoading}
                className="w-full rounded-lg bg-amber-500 py-3 font-semibold text-white shadow-md transition-colors hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isLoading && selectedPlan === "elite" ? "Redirection..." : "Commencer l’essai gratuit"}
              </button>
            )}
          </article>
        </section>

        {/* Comparison */}
        <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-6 text-center text-xl font-bold text-gray-900">
            Comparaison des fonctionnalités
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Fonctionnalité</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Essential</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-blue-700 bg-blue-50">Pro</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-amber-700 bg-amber-50">Elite</th>
                </tr>
              </thead>
              <tbody>
                {/* Base features */}
                <tr>
                  <td colSpan={4} className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-600 bg-gray-50">
                    Fonctionnalités de base
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">16 langues supportées</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
                        <Check className="h-4 w-4 text-emerald-600" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center bg-blue-50/30">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
                        <Check className="h-4 w-4 text-emerald-600" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center bg-amber-50/30">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
                        <Check className="h-4 w-4 text-emerald-600" />
                      </div>
                    </div>
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">Adaptation au rôle</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
                        <Check className="h-4 w-4 text-emerald-600" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center bg-blue-50/30">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
                        <Check className="h-4 w-4 text-emerald-600" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center bg-amber-50/30">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100">
                        <Check className="h-4 w-4 text-emerald-600" />
                      </div>
                    </div>
                  </td>
                </tr>

                {/* Capacités */}
                <tr>
                  <td colSpan={4} className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-600 bg-gray-50">
                    Capacités et performances
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">Requêtes / mois</td>
                  <td className="px-4 py-3 text-center text-sm text-gray-600">100</td>
                  <td className="px-4 py-3 text-center text-sm font-semibold text-blue-700 bg-blue-50/30">Illimitées*</td>
                  <td className="px-4 py-3 text-center text-sm font-semibold text-amber-700 bg-amber-50/30">Illimitées*</td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">Historique</td>
                  <td className="px-4 py-3 text-center text-sm text-gray-600">30 jours</td>
                  <td className="px-4 py-3 text-center text-sm font-semibold text-blue-700 bg-blue-50/30">Illimité</td>
                  <td className="px-4 py-3 text-center text-sm font-semibold text-amber-700 bg-amber-50/30">Illimité</td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">Export PDF</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
                        <X className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center bg-blue-50/30">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100">
                        <Check className="h-4 w-4 text-blue-700" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center bg-amber-50/30">
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
                    Fonctionnalités IA
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">Analyse d'images</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
                        <X className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center text-sm font-semibold text-blue-700 bg-blue-50/30">25/mois</td>
                  <td className="px-4 py-3 text-center text-sm font-semibold text-amber-700 bg-amber-50/30">Illimité*</td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">Saisie vocale</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
                        <X className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center bg-blue-50/30">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100">
                        <Check className="h-4 w-4 text-blue-700" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center bg-amber-50/30">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100">
                        <Check className="h-4 w-4 text-amber-700" />
                      </div>
                    </div>
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">Assistant vocal</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
                        <X className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center bg-blue-50/30">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100">
                        <Check className="h-4 w-4 text-blue-700" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center bg-amber-50/30">
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
                    Expérience
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="px-4 py-3 text-sm text-gray-900">Sans publicité</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
                        <X className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center bg-blue-50/30">
                    <div className="flex justify-center">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-100">
                        <X className="h-4 w-4 text-gray-400" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center bg-amber-50/30">
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
          <div className="mt-6 grid gap-3 text-xs text-gray-500 md:grid-cols-3">
            <div className="rounded-lg bg-gray-50 p-3">
              <span className="font-semibold text-gray-700">Essai gratuit 14 jours</span>
              <div className="mt-1">Annule à tout moment sans frais.</div>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <span className="font-semibold text-gray-700">Paiement sécurisé</span>
              <div className="mt-1">Transactions protégées par Stripe.</div>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <span className="font-semibold text-gray-700">Support prioritaire</span>
              <div className="mt-1">Inclus avec Pro et Elite.</div>
            </div>
          </div>

          <p className="mt-4 text-[11px] leading-5 text-gray-500">
            * “Illimité” signifie usage illimité dans le cadre d’une utilisation normale et raisonnable. Nous nous
            réservons le droit de limiter les abus manifestes.
          </p>
        </section>
      </div>
    </BaseDialog>
  );
};

export default AccountModal;
