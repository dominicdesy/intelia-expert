"use client";

import React, { useState } from "react";
import { useTranslation } from "@/lib/languages/i18n";
import { redirectToCheckout } from "@/lib/api/stripe";
import { Check, X } from "lucide-react";
import toast from "react-hot-toast";

export default function SubscriptionPage() {
  const { t, currentLanguage } = useTranslation();
  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">("monthly");
  const [isLoading, setIsLoading] = useState<string | null>(null);

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

  const handleSubscribe = async (planName: string) => {
    if (planName === "essential") {
      // Plan gratuit, pas besoin de Stripe
      toast.success("Vous utilisez déjà le plan Essential gratuit!");
      return;
    }

    setIsLoading(planName);

    try {
      const authData = localStorage.getItem("intelia-expert-auth");
      if (!authData) {
        toast.error("Veuillez vous connecter pour continuer");
        setIsLoading(null);
        return;
      }

      const { access_token } = JSON.parse(authData);

      // Ajouter le suffixe pour le cycle de facturation
      const fullPlanName = billingCycle === "yearly" ? `${planName}_yearly` : planName;

      await redirectToCheckout(fullPlanName, access_token, currentLanguage);
    } catch (error) {
      console.error("Erreur abonnement:", error);
      toast.error("Erreur lors de la redirection vers le paiement");
      setIsLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Choisissez votre plan
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Sélectionnez le plan qui convient le mieux à vos besoins
          </p>

          {/* Toggle Mensuel / Annuel */}
          <div className="flex items-center justify-center gap-4 mb-8">
            <span className={`text-sm font-medium ${billingCycle === "monthly" ? "text-gray-900" : "text-gray-500"}`}>
              Mensuel
            </span>
            <button
              onClick={() => setBillingCycle(billingCycle === "monthly" ? "yearly" : "monthly")}
              className="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              style={{ backgroundColor: billingCycle === "yearly" ? "#3B82F6" : "#D1D5DB" }}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  billingCycle === "yearly" ? "translate-x-6" : "translate-x-1"
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
        </div>

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
          {/* Plan Essential */}
          <div className="relative bg-white rounded-2xl shadow-sm border-2 border-gray-200 p-8">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <span className="inline-flex items-center rounded-full bg-gray-100 px-4 py-1 text-xs font-semibold text-gray-700">
                GRATUIT
              </span>
            </div>

            <div className="text-center mb-8 mt-4">
              <h3 className="text-2xl font-bold text-gray-900 mb-2">Essential</h3>
              <p className="text-sm text-gray-600 mb-4">
                Idéal pour découvrir la puissance de notre GPT
              </p>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-5xl font-bold text-gray-900">0</span>
                <span className="text-xl text-gray-600">$</span>
                <span className="text-sm text-gray-500">/ mois</span>
              </div>
            </div>

            <button
              onClick={() => handleSubscribe("essential")}
              className="w-full py-3 px-6 rounded-lg bg-gray-100 text-gray-700 font-semibold hover:bg-gray-200 transition-colors mb-8"
            >
              Plan actuel
            </button>
          </div>

          {/* Plan Pro */}
          <div className="relative bg-white rounded-2xl shadow-sm border-2 border-blue-200 p-8">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <span className="inline-flex items-center rounded-full bg-blue-500 px-4 py-1 text-xs font-semibold text-white">
                POPULAIRE
              </span>
            </div>

            <div className="text-center mb-8 mt-4">
              <h3 className="text-2xl font-bold text-gray-900 mb-2">Pro</h3>
              <p className="text-sm text-gray-600 mb-4">
                Pensé pour un usage professionnel régulier
              </p>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-5xl font-bold text-gray-900">
                  {billingCycle === "monthly" ? prices.pro : Math.round(prices.pro / 12 * 100) / 100}
                </span>
                <span className="text-xl text-gray-600">$</span>
                <span className="text-sm text-gray-500">
                  / {billingCycle === "monthly" ? "mois" : "an"}
                </span>
              </div>
              {billingCycle === "yearly" && (
                <p className="text-xs text-green-600 mt-1">
                  Soit {Math.round(prices.pro / 12 * 100) / 100}$/mois
                </p>
              )}
              <p className="text-xs text-blue-600 mt-2 font-medium">
                🎁 Essai gratuit de 14 jours
              </p>
            </div>

            <button
              onClick={() => handleSubscribe("pro")}
              disabled={isLoading === "pro"}
              className="w-full py-3 px-6 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mb-8"
            >
              {isLoading === "pro" ? "Redirection..." : "Commencer l'essai"}
            </button>
          </div>

          {/* Plan Elite */}
          <div className="relative bg-white rounded-2xl shadow-lg border-2 border-yellow-500 p-8 transform scale-105">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <span className="inline-flex items-center rounded-full bg-gradient-to-r from-yellow-400 to-yellow-600 px-4 py-1 text-xs font-semibold text-white">
                ⭐ RECOMMANDÉ
              </span>
            </div>

            <div className="text-center mb-8 mt-4">
              <h3 className="text-2xl font-bold text-gray-900 mb-2">Elite</h3>
              <p className="text-sm text-gray-600 mb-4">
                La solution complète pour les utilisateurs avancés
              </p>
              <div className="flex items-baseline justify-center gap-1">
                <span className="text-5xl font-bold text-gray-900">
                  {billingCycle === "monthly" ? prices.elite : Math.round(prices.elite / 12 * 100) / 100}
                </span>
                <span className="text-xl text-gray-600">$</span>
                <span className="text-sm text-gray-500">
                  / {billingCycle === "monthly" ? "mois" : "an"}
                </span>
              </div>
              {billingCycle === "yearly" && (
                <p className="text-xs text-green-600 mt-1">
                  Soit {Math.round(prices.elite / 12 * 100) / 100}$/mois
                </p>
              )}
              <p className="text-xs text-blue-600 mt-2 font-medium">
                🎁 Essai gratuit de 14 jours
              </p>
            </div>

            <button
              onClick={() => handleSubscribe("elite")}
              disabled={isLoading === "elite"}
              className="w-full py-3 px-6 rounded-lg bg-gradient-to-r from-yellow-500 to-yellow-600 text-white font-bold hover:from-yellow-600 hover:to-yellow-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed mb-8 shadow-md"
            >
              {isLoading === "elite" ? "Redirection..." : "OBTENIR ELITE"}
            </button>
          </div>
        </div>

        {/* Tableau de comparaison détaillé */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h2 className="text-2xl font-bold text-gray-900 text-center">
              Comparaison détaillée des fonctionnalités
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b-2 border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Fonctionnalités
                  </th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-gray-900">
                    Essential
                  </th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-blue-600 bg-blue-50">
                    Pro
                  </th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-yellow-600 bg-yellow-50">
                    Elite ⭐
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-200">
                {/* Section: Fonctionnalités de base */}
                <tr className="bg-gray-100">
                  <td colSpan={4} className="px-6 py-3 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Fonctionnalités incluses (tous plans)
                  </td>
                </tr>

                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Langues supportées</td>
                  <td className="px-6 py-4 text-center text-sm text-gray-700">16</td>
                  <td className="px-6 py-4 text-center text-sm text-gray-700 bg-blue-50/30">16</td>
                  <td className="px-6 py-4 text-center text-sm text-gray-700 bg-yellow-50/30">16</td>
                </tr>

                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">
                    Adaptation au rôle de l'utilisateur*
                  </td>
                  <td className="px-6 py-4 text-center">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-blue-50/30">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-yellow-50/30">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                </tr>

                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Partage des conversations</td>
                  <td className="px-6 py-4 text-center">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-blue-50/30">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-yellow-50/30">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                </tr>

                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Aide en ligne interactive</td>
                  <td className="px-6 py-4 text-center">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-blue-50/30">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-yellow-50/30">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                </tr>

                {/* Section: Capacités & Limites */}
                <tr className="bg-gray-100">
                  <td colSpan={4} className="px-6 py-3 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Capacités & Limites
                  </td>
                </tr>

                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Requêtes / mois</td>
                  <td className="px-6 py-4 text-center text-sm text-gray-700">100</td>
                  <td className="px-6 py-4 text-center text-sm font-semibold text-blue-600 bg-blue-50/30">
                    ILLIMITÉES*
                  </td>
                  <td className="px-6 py-4 text-center text-sm font-semibold text-yellow-600 bg-yellow-50/30">
                    ILLIMITÉES*
                  </td>
                </tr>

                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Historique conversations</td>
                  <td className="px-6 py-4 text-center text-sm text-gray-700">30 jours</td>
                  <td className="px-6 py-4 text-center text-sm font-semibold text-blue-600 bg-blue-50/30">
                    Illimité
                  </td>
                  <td className="px-6 py-4 text-center text-sm font-semibold text-yellow-600 bg-yellow-50/30">
                    Illimité
                  </td>
                </tr>

                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Exportation PDF conversations</td>
                  <td className="px-6 py-4 text-center">
                    <X className="w-5 h-5 text-gray-400 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-blue-50/30">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-yellow-50/30">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                </tr>

                {/* Section: Fonctionnalités avancées IA */}
                <tr className="bg-gray-100">
                  <td colSpan={4} className="px-6 py-3 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Fonctionnalités avancées IA
                  </td>
                </tr>

                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Analyse d'images par IA</td>
                  <td className="px-6 py-4 text-center">
                    <X className="w-5 h-5 text-gray-400 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center text-sm text-gray-700 bg-blue-50/30">
                    25 / mois
                  </td>
                  <td className="px-6 py-4 text-center text-sm font-semibold text-yellow-600 bg-yellow-50/30">
                    Illimité*
                  </td>
                </tr>

                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Saisie vocale</td>
                  <td className="px-6 py-4 text-center">
                    <X className="w-5 h-5 text-gray-400 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-blue-50/30">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-yellow-50/30">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                </tr>

                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Assistant vocal intelligent</td>
                  <td className="px-6 py-4 text-center">
                    <X className="w-5 h-5 text-gray-400 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-blue-50/30">
                    <X className="w-5 h-5 text-gray-400 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-yellow-50/30">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                </tr>

                {/* Section: Expérience utilisateur */}
                <tr className="bg-gray-100">
                  <td colSpan={4} className="px-6 py-3 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Expérience utilisateur
                  </td>
                </tr>

                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">Expérience sans publicité</td>
                  <td className="px-6 py-4 text-center">
                    <X className="w-5 h-5 text-gray-400 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-blue-50/30">
                    <X className="w-5 h-5 text-gray-400 mx-auto" />
                  </td>
                  <td className="px-6 py-4 text-center bg-yellow-50/30">
                    <Check className="w-5 h-5 text-green-600 mx-auto" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Définitions */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Définitions</h3>

          <div className="space-y-4 text-sm text-gray-700">
            <div>
              <strong className="text-gray-900">Illimité* :</strong> Usage illimité dans le cadre d'une utilisation normale et raisonnable.
              Nous nous réservons le droit de limiter les abus manifestes ou l'utilisation automatisée excessive qui pourrait
              affecter la qualité du service pour les autres utilisateurs.
            </div>

            <div>
              <strong className="text-gray-900">Adaptation au rôle de l'utilisateur :</strong> Le système adapte automatiquement
              ses réponses et son niveau de détail selon votre profil professionnel (éleveur, vétérinaire, nutritionniste,
              technicien, gestionnaire, etc.). Cela permet d'obtenir des réponses pertinentes et adaptées à votre contexte
              et niveau d'expertise.
            </div>
          </div>
        </div>

        {/* Footer CTA */}
        <div className="mt-12 text-center">
          <p className="text-sm text-gray-600">
            Des questions sur nos plans ? <a href="mailto:support@intelia.com" className="text-blue-600 hover:underline">Contactez-nous</a>
          </p>
        </div>
      </div>
    </div>
  );
}
