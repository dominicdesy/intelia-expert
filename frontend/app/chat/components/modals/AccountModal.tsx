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
      maxWidth="max-w-7xl"
    >
      <div className="space-y-8" style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 2rem' }}>
        {/* Currency Selector */}
        {user && <CurrencySelector user={user} />}

        {/* Compact Billing Toggle */}
        <div className="flex items-center justify-center gap-4 py-2 text-sm">
          <span className={`font-medium transition-colors ${billingCycle === "monthly" ? "text-gray-900" : "text-gray-500"}`}>
            Mensuel
          </span>
          <button
            onClick={() => setBillingCycle(billingCycle === "monthly" ? "yearly" : "monthly")}
            className="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
            style={{ backgroundColor: billingCycle === "yearly" ? "#10B981" : "#D1D5DB" }}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                billingCycle === "yearly" ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
          <span className={`font-medium transition-colors ${billingCycle === "yearly" ? "text-gray-900" : "text-gray-500"}`}>
            Annuel
          </span>
          {billingCycle === "yearly" && (
            <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-700">
              -15%
            </span>
          )}
        </div>

        {/* Plans Grid - Fixed Width Cards */}
        <div className="flex justify-center gap-8 flex-wrap">
          {/* Plan Essential */}
          <div className="relative rounded-2xl border border-gray-300 p-6 transition-all duration-200 hover:-translate-y-1" style={{ flex: '1 1 340px', maxWidth: '360px', minWidth: '300px', background: '#f8f9fa', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <span className="inline-flex items-center rounded-full bg-gray-200 px-4 py-1 text-xs font-semibold text-gray-700 uppercase" style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                Gratuit
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
              className="w-full py-3 px-6 rounded-lg bg-gray-100 text-gray-700 font-semibold cursor-not-allowed"
            >
              {currentPlan === "essential" ? "Plan actuel" : "Plan gratuit"}
            </button>
          </div>

          {/* Plan Pro */}
          <div className="relative rounded-2xl border-2 border-blue-500 p-6 transition-all duration-200 hover:-translate-y-1" style={{ flex: '1 1 340px', maxWidth: '380px', minWidth: '300px', background: '#eff6ff', boxShadow: '0 4px 12px rgba(37,99,235,0.15)' }}>
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <span className="inline-flex items-center rounded-full px-4 py-1 text-xs font-semibold text-white uppercase" style={{ background: 'linear-gradient(90deg, #2563eb, #3b82f6)', boxShadow: '0 2px 6px rgba(37,99,235,0.3)' }}>
                Populaire
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
                className="w-full py-3 px-6 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isManaging ? "Chargement..." : "⚙️ Gérer mon abonnement"}
              </button>
            ) : (
              <button
                onClick={() => handleUpgrade("pro")}
                disabled={isLoading}
                className="w-full py-3 px-6 rounded-lg text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: '#2563eb', boxShadow: '0 2px 8px rgba(37,99,235,0.25)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#1d4ed8'}
                onMouseLeave={(e) => e.currentTarget.style.background = '#2563eb'}
              >
                {isLoading && selectedPlan === "pro" ? "Redirection..." : "🎁 Commencer l'essai gratuit"}
              </button>
            )}
          </div>

          {/* Plan Elite */}
          <div className="relative rounded-2xl border-2 p-6 transition-all duration-200 hover:-translate-y-1 animate-pulse-subtle" style={{ flex: '1 1 340px', maxWidth: '360px', minWidth: '300px', background: '#fffbeb', borderColor: '#facc15', boxShadow: '0 4px 12px rgba(250,204,21,0.2)' }}>
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <span className="inline-flex items-center rounded-full px-4 py-1 text-xs font-semibold text-white uppercase" style={{ background: 'linear-gradient(90deg, #facc15, #eab308)', boxShadow: '0 2px 6px rgba(250,204,21,0.4)' }}>
                ⭐ Recommandé
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
                className="w-full py-3 px-6 rounded-lg bg-gradient-to-r from-yellow-500 to-yellow-600 text-white font-bold hover:from-yellow-600 hover:to-yellow-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isManaging ? "Chargement..." : "⚙️ Gérer mon abonnement"}
              </button>
            ) : (
              <button
                onClick={() => handleUpgrade("elite")}
                disabled={isLoading}
                className="w-full py-3 px-6 rounded-lg text-white font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: 'linear-gradient(90deg, #facc15, #eab308)', boxShadow: '0 3px 10px rgba(250,204,21,0.3)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'linear-gradient(90deg, #eab308, #ca8a04)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'linear-gradient(90deg, #facc15, #eab308)'}
              >
                {isLoading && selectedPlan === "elite" ? "Redirection..." : "🎁 Commencer l'essai gratuit"}
              </button>
            )}
          </div>
        </div>

        {/* Feature Comparison Grid */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6" style={{ boxShadow: '0 1px 6px rgba(0,0,0,0.08)' }}>
          <h3 className="text-xl font-bold text-gray-900 text-center mb-6">
            Comparaison des fonctionnalités
          </h3>

          <div className="space-y-6">
            {/* 🧩 Fonctionnalités de base */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 uppercase mb-3 flex items-center gap-2" style={{ fontWeight: 600 }}>
                <span>🧩</span> Fonctionnalités de base
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="flex items-start gap-3 p-3 rounded-lg transition-colors hover:bg-gray-100" style={{ background: '#f9fafb' }}>
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                    <Check className="w-4 h-4 text-green-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">16 langues supportées</p>
                    <p className="text-xs text-gray-600">Tous les plans</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-lg transition-colors hover:bg-gray-100" style={{ background: '#fff' }}>
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                    <Check className="w-4 h-4 text-green-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">Adaptation au rôle</p>
                    <p className="text-xs text-gray-600">Tous les plans</p>
                  </div>
                </div>
              </div>
            </div>

            {/* ⚙️ Capacités et performances */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 uppercase mb-3 flex items-center gap-2" style={{ fontWeight: 600 }}>
                <span>⚙️</span> Capacités et performances
              </h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between p-3 rounded-lg transition-colors hover:bg-gray-100" style={{ background: '#f9fafb' }}>
                  <span className="font-medium text-gray-900">Requêtes / mois</span>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-gray-600">Essential: 100</span>
                    <span className="font-semibold text-blue-600">Pro: Illimitées*</span>
                    <span className="font-semibold text-yellow-600">Elite: Illimitées*</span>
                  </div>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg transition-colors hover:bg-gray-100" style={{ background: '#fff' }}>
                  <span className="font-medium text-gray-900">Historique</span>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-gray-600">Essential: 30 jours</span>
                    <span className="font-semibold text-blue-600">Pro: Illimité</span>
                    <span className="font-semibold text-yellow-600">Elite: Illimité</span>
                  </div>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg transition-colors hover:bg-gray-100" style={{ background: '#f9fafb' }}>
                  <span className="font-medium text-gray-900">Export PDF</span>
                  <div className="flex items-center gap-4">
                    <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
                      <X className="w-4 h-4 text-gray-400" />
                    </div>
                    <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                      <Check className="w-4 h-4 text-blue-600" />
                    </div>
                    <div className="w-6 h-6 rounded-full bg-yellow-100 flex items-center justify-center">
                      <Check className="w-4 h-4 text-yellow-600" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 💬 Fonctionnalités IA */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 uppercase mb-3 flex items-center gap-2" style={{ fontWeight: 600 }}>
                <span>💬</span> Fonctionnalités IA
              </h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between p-3 rounded-lg transition-colors hover:bg-gray-100" style={{ background: '#fff' }}>
                  <span className="font-medium text-gray-900">Analyse d'images</span>
                  <div className="flex items-center gap-4 text-sm">
                    <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
                      <X className="w-4 h-4 text-gray-400" />
                    </div>
                    <span className="font-semibold text-blue-600">Pro: 25/mois</span>
                    <span className="font-semibold text-yellow-600">Elite: Illimité*</span>
                  </div>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg transition-colors hover:bg-gray-100" style={{ background: '#f9fafb' }}>
                  <span className="font-medium text-gray-900">Saisie vocale</span>
                  <div className="flex items-center gap-4">
                    <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
                      <X className="w-4 h-4 text-gray-400" />
                    </div>
                    <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                      <Check className="w-4 h-4 text-blue-600" />
                    </div>
                    <div className="w-6 h-6 rounded-full bg-yellow-100 flex items-center justify-center">
                      <Check className="w-4 h-4 text-yellow-600" />
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg transition-colors hover:bg-gray-100" style={{ background: '#fff' }}>
                  <span className="font-medium text-gray-900">Assistant vocal</span>
                  <div className="flex items-center gap-4">
                    <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
                      <X className="w-4 h-4 text-gray-400" />
                    </div>
                    <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
                      <X className="w-4 h-4 text-gray-400" />
                    </div>
                    <div className="w-6 h-6 rounded-full bg-yellow-100 flex items-center justify-center">
                      <Check className="w-4 h-4 text-yellow-600" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 📊 Expérience */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 uppercase mb-3 flex items-center gap-2" style={{ fontWeight: 600 }}>
                <span>📊</span> Expérience
              </h4>
              <div className="flex items-center justify-between p-3 rounded-lg transition-colors hover:bg-gray-100" style={{ background: '#f9fafb' }}>
                <span className="font-medium text-gray-900">Sans publicité</span>
                <div className="flex items-center gap-4">
                  <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
                    <X className="w-4 h-4 text-gray-400" />
                  </div>
                  <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
                    <X className="w-4 h-4 text-gray-400" />
                  </div>
                  <div className="w-6 h-6 rounded-full bg-yellow-100 flex items-center justify-center">
                    <Check className="w-4 h-4 text-yellow-600" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Trust Elements Footer */}
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-2xl p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                <Check className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="font-semibold text-gray-900 mb-1">✅ Essai gratuit 14 jours</p>
                <p className="text-xs text-gray-600">Annulez à tout moment sans frais</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                <span className="text-xl">🔒</span>
              </div>
              <div>
                <p className="font-semibold text-gray-900 mb-1">Paiement sécurisé</p>
                <p className="text-xs text-gray-600">Transactions protégées par Stripe</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                <span className="text-xl">💬</span>
              </div>
              <div>
                <p className="font-semibold text-gray-900 mb-1">Support prioritaire</p>
                <p className="text-xs text-gray-600">Assistance incluse avec Pro et Elite</p>
              </div>
            </div>
          </div>

          <div className="border-t border-blue-200 pt-4">
            <p className="text-xs text-gray-700 mb-2">
              <strong>Illimité*:</strong> Usage illimité dans le cadre d'une utilisation normale et raisonnable. Nous nous réservons le droit de limiter les abus manifestes.
            </p>
            <p className="text-xs text-gray-700">
              <strong>Adaptation au rôle:</strong> Le système adapte ses réponses selon votre profil professionnel (éleveur, vétérinaire, nutritionniste, etc.).
            </p>
          </div>
        </div>
      </div>
    </BaseDialog>
  );
};
