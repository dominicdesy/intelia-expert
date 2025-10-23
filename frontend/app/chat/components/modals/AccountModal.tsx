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

  // Map "free" to "essential" for backwards compatibility
  const currentPlan = user?.plan === "free" ? "essential" : (user?.plan || "essential");

  // Prix mensuels
  const monthlyPrices = {
    essential: 0,
    pro: 18,
    elite: 28,
  };

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
      console.error("[AccountModal] Erreur portail:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : t("stripe.portal.error")
      );
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
          console.error("[AccountModal] Erreur parse:", e);
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

      // Ajouter le suffixe yearly si nécessaire
      const fullPlanName = billingCycle === "yearly" ? `${planName}_yearly` : planName;

      await redirectToCheckout(fullPlanName, accessToken, currentLanguage);
    } catch (error) {
      console.error("[AccountModal] Erreur:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : "Erreur lors de la redirection"
      );
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
      maxWidth="max-w-6xl"
    >
      <div className="space-y-6 max-h-[80vh] overflow-y-auto">
        {/* Currency Selector */}
        {user && <CurrencySelector user={user} />}

        {/* Toggle Mensuel / Annuel */}
        <div className="flex items-center justify-center gap-3 py-2">
          <span className={`text-sm font-medium ${billingCycle === "monthly" ? "text-gray-900" : "text-gray-500"}`}>
            Mensuel
          </span>
          <button
            onClick={() => setBillingCycle(billingCycle === "monthly" ? "yearly" : "monthly")}
            className="relative inline-flex h-5 w-10 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
            style={{ backgroundColor: billingCycle === "yearly" ? "#10B981" : "#D1D5DB" }}
          >
            <span
              className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                billingCycle === "yearly" ? "translate-x-5.5" : "translate-x-0.5"
              }`}
            />
          </button>
          <span className={`text-sm font-medium ${billingCycle === "yearly" ? "text-gray-900" : "text-gray-500"}`}>
            Annuel
          </span>
          {billingCycle === "yearly" && (
            <span className="inline-flex items-center rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-800">
              ÉCONOMISEZ 15%
            </span>
          )}
        </div>

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Plan Essential */}
          <div className="relative bg-white rounded-xl shadow-sm border-2 border-gray-200 p-6">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <span className="inline-flex items-center rounded-full bg-gray-100 px-4 py-1 text-xs font-semibold text-gray-700">
                GRATUIT
              </span>
            </div>

            <div className="text-center mb-6 mt-4">
              <h3 className="text-2xl font-bold text-gray-900 mb-2">Essential</h3>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-4xl font-bold text-gray-900">0</span>
                <span className="text-xl text-gray-600">$</span>
                <span className="text-sm text-gray-500">/ mois</span>
              </div>
            </div>

            <button
              disabled
              className="w-full py-3 px-6 rounded-lg bg-gray-100 text-gray-700 font-semibold mb-6 cursor-not-allowed"
            >
              {currentPlan === "essential" ? "Plan actuel" : "Plan gratuit"}
            </button>
          </div>

          {/* Plan Pro */}
          <div className="relative bg-white rounded-xl shadow-md border-2 border-blue-500 p-6">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <span className="inline-flex items-center rounded-full bg-blue-500 px-4 py-1 text-xs font-semibold text-white">
                POPULAIRE
              </span>
            </div>

            <div className="text-center mb-6 mt-4">
              <h3 className="text-2xl font-bold text-blue-600 mb-2">Pro</h3>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-4xl font-bold text-gray-900">
                  {billingCycle === "monthly" ? prices.pro.toFixed(2) : (prices.pro / 12).toFixed(2)}
                </span>
                <span className="text-xl text-gray-600">$</span>
                <span className="text-sm text-gray-500">
                  / {billingCycle === "monthly" ? "mois" : "an"}
                </span>
              </div>
              {billingCycle === "yearly" && (
                <p className="text-xs text-green-600 mt-1">
                  Soit {(prices.pro / 12).toFixed(2)}$/mois
                </p>
              )}
              <p className="text-xs text-blue-600 mt-2 font-medium">
                🎁 Essai gratuit de 14 jours
              </p>
            </div>

            {currentPlan === "pro" ? (
              <button
                onClick={handleManageSubscription}
                disabled={isManaging}
                className="w-full py-3 px-6 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mb-6"
              >
                {isManaging ? "Chargement..." : "⚙️ Gérer mon abonnement"}
              </button>
            ) : (
              <div className="space-y-2 mb-6">
                <button
                  onClick={() => handleUpgrade("pro")}
                  disabled={isLoading}
                  className="w-full py-2.5 px-4 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  {isLoading && selectedPlan === "pro" ? "Redirection..." : "🎁 Essai gratuit 14 jours"}
                </button>
                <button
                  onClick={() => handleUpgrade("pro")}
                  disabled={isLoading}
                  className="w-full py-2 px-4 rounded-lg border-2 border-blue-600 text-blue-600 font-medium hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  Choisir ce plan
                </button>
              </div>
            )}
          </div>

          {/* Plan Elite */}
          <div className="relative bg-white rounded-xl shadow-lg border-2 border-yellow-500 p-6 transform scale-105">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <span className="inline-flex items-center rounded-full bg-gradient-to-r from-yellow-400 to-yellow-600 px-4 py-1 text-xs font-semibold text-white">
                ⭐ RECOMMANDÉ
              </span>
            </div>

            <div className="text-center mb-6 mt-4">
              <h3 className="text-2xl font-bold text-yellow-600 mb-2">Elite</h3>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-4xl font-bold text-gray-900">
                  {billingCycle === "monthly" ? prices.elite.toFixed(2) : (prices.elite / 12).toFixed(2)}
                </span>
                <span className="text-xl text-gray-600">$</span>
                <span className="text-sm text-gray-500">
                  / {billingCycle === "monthly" ? "mois" : "an"}
                </span>
              </div>
              {billingCycle === "yearly" && (
                <p className="text-xs text-green-600 mt-1">
                  Soit {(prices.elite / 12).toFixed(2)}$/mois
                </p>
              )}
              <p className="text-xs text-blue-600 mt-2 font-medium">
                🎁 Essai gratuit de 14 jours
              </p>
            </div>

            {currentPlan === "elite" ? (
              <button
                onClick={handleManageSubscription}
                disabled={isManaging}
                className="w-full py-3 px-6 rounded-lg bg-gradient-to-r from-yellow-500 to-yellow-600 text-white font-bold hover:from-yellow-600 hover:to-yellow-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed mb-6 shadow-md"
              >
                {isManaging ? "Chargement..." : "⚙️ Gérer mon abonnement"}
              </button>
            ) : (
              <div className="space-y-2 mb-6">
                <button
                  onClick={() => handleUpgrade("elite")}
                  disabled={isLoading}
                  className="w-full py-2.5 px-4 rounded-lg bg-gradient-to-r from-yellow-500 to-yellow-600 text-white font-bold hover:from-yellow-600 hover:to-yellow-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm shadow-md"
                >
                  {isLoading && selectedPlan === "elite" ? "Redirection..." : "🎁 Essai gratuit 14 jours"}
                </button>
                <button
                  onClick={() => handleUpgrade("elite")}
                  disabled={isLoading}
                  className="w-full py-2 px-4 rounded-lg border-2 border-yellow-600 text-yellow-600 font-medium hover:bg-yellow-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  Choisir ce plan
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Tableau de comparaison */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 text-center">
              Comparaison des fonctionnalités
            </h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-3 py-2 text-left font-semibold text-gray-900 w-1/2">
                    Fonctionnalités
                  </th>
                  <th className="px-2 py-2 text-center font-semibold text-gray-700 w-1/6">Essential</th>
                  <th className="px-2 py-2 text-center font-semibold text-blue-600 bg-blue-50 w-1/6">Pro</th>
                  <th className="px-2 py-2 text-center font-semibold text-yellow-600 bg-yellow-50 w-1/6">Elite</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-200">
                {/* Base features */}
                <tr className="bg-gray-50">
                  <td colSpan={4} className="px-3 py-1.5 text-xs font-semibold text-gray-700 uppercase">
                    Fonctionnalités de base
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Langues supportées</td>
                  <td className="px-2 py-2 text-center">16</td>
                  <td className="px-2 py-2 text-center bg-blue-50/30">16</td>
                  <td className="px-2 py-2 text-center bg-yellow-50/30">16</td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Adaptation au rôle</td>
                  <td className="px-2 py-2 text-center"><Check className="w-4 h-4 text-green-600 mx-auto" /></td>
                  <td className="px-2 py-2 text-center bg-blue-50/30"><Check className="w-4 h-4 text-green-600 mx-auto" /></td>
                  <td className="px-2 py-2 text-center bg-yellow-50/30"><Check className="w-4 h-4 text-green-600 mx-auto" /></td>
                </tr>

                {/* Capacities */}
                <tr className="bg-gray-50">
                  <td colSpan={4} className="px-3 py-1.5 text-xs font-semibold text-gray-700 uppercase">
                    Capacités
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Requêtes / mois</td>
                  <td className="px-2 py-2 text-center text-xs">100</td>
                  <td className="px-2 py-2 text-center font-semibold text-blue-600 bg-blue-50/30 text-xs">
                    Illimitées*
                  </td>
                  <td className="px-2 py-2 text-center font-semibold text-yellow-600 bg-yellow-50/30 text-xs">
                    Illimitées*
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Historique</td>
                  <td className="px-2 py-2 text-center text-xs">30 jours</td>
                  <td className="px-2 py-2 text-center font-semibold text-blue-600 bg-blue-50/30 text-xs">
                    Illimité
                  </td>
                  <td className="px-2 py-2 text-center font-semibold text-yellow-600 bg-yellow-50/30 text-xs">
                    Illimité
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Export PDF</td>
                  <td className="px-2 py-2 text-center"><X className="w-4 h-4 text-gray-400 mx-auto" /></td>
                  <td className="px-2 py-2 text-center bg-blue-50/30"><Check className="w-4 h-4 text-green-600 mx-auto" /></td>
                  <td className="px-2 py-2 text-center bg-yellow-50/30"><Check className="w-4 h-4 text-green-600 mx-auto" /></td>
                </tr>

                {/* AI Features */}
                <tr className="bg-gray-50">
                  <td colSpan={4} className="px-3 py-1.5 text-xs font-semibold text-gray-700 uppercase">
                    Fonctionnalités IA
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Analyse d'images</td>
                  <td className="px-2 py-2 text-center"><X className="w-4 h-4 text-gray-400 mx-auto" /></td>
                  <td className="px-2 py-2 text-center bg-blue-50/30 text-xs">25/mois</td>
                  <td className="px-2 py-2 text-center font-semibold text-yellow-600 bg-yellow-50/30 text-xs">
                    Illimité*
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Saisie vocale</td>
                  <td className="px-2 py-2 text-center"><X className="w-4 h-4 text-gray-400 mx-auto" /></td>
                  <td className="px-2 py-2 text-center bg-blue-50/30"><Check className="w-4 h-4 text-green-600 mx-auto" /></td>
                  <td className="px-2 py-2 text-center bg-yellow-50/30"><Check className="w-4 h-4 text-green-600 mx-auto" /></td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Assistant vocal</td>
                  <td className="px-2 py-2 text-center"><X className="w-4 h-4 text-gray-400 mx-auto" /></td>
                  <td className="px-2 py-2 text-center bg-blue-50/30"><X className="w-4 h-4 text-gray-400 mx-auto" /></td>
                  <td className="px-2 py-2 text-center bg-yellow-50/30"><Check className="w-4 h-4 text-green-600 mx-auto" /></td>
                </tr>

                {/* Experience */}
                <tr className="bg-gray-50">
                  <td colSpan={4} className="px-3 py-1.5 text-xs font-semibold text-gray-700 uppercase">
                    Expérience
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-2">Sans publicité</td>
                  <td className="px-2 py-2 text-center"><X className="w-4 h-4 text-gray-400 mx-auto" /></td>
                  <td className="px-2 py-2 text-center bg-blue-50/30"><X className="w-4 h-4 text-gray-400 mx-auto" /></td>
                  <td className="px-2 py-2 text-center bg-yellow-50/30"><Check className="w-4 h-4 text-green-600 mx-auto" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Définitions */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm">
          <h4 className="font-semibold text-gray-900 mb-2">
            Définitions
          </h4>
          <div className="space-y-2 text-gray-700">
            <p>
              <strong>Illimité*:</strong>{" "}
              Usage illimité dans le cadre d'une utilisation normale et raisonnable. Nous nous réservons le droit de limiter les abus manifestes.
            </p>
            <p>
              <strong>Adaptation au rôle:</strong>{" "}
              Le système adapte ses réponses selon votre profil professionnel (éleveur, vétérinaire, nutritionniste, etc.).
            </p>
          </div>
        </div>

        {/* Informations supplémentaires */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start">
            <span className="text-blue-600 text-xl mr-3">ℹ️</span>
            <div className="text-sm text-blue-900">
              <p className="font-medium mb-1">Paiement sécurisé</p>
              <ul className="list-disc list-inside space-y-1 text-blue-800">
                <li>Paiements traités par Stripe</li>
                <li>Annulation possible à tout moment</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </BaseDialog>
  );
};
