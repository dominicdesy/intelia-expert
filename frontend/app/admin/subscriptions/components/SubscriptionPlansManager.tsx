"use client";

import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { buildApiUrl } from "@/lib/api/config";

interface BillingPlan {
  plan_name: string;
  display_name: string;
  monthly_quota: number;
  price_per_month: number;
  features: string[];
  active: boolean;
}

interface TierPrice {
  tier_level: number;
  price_usd: number;
}

interface SubscriptionPlansManagerProps {
  accessToken: string;
}

export default function SubscriptionPlansManager({
  accessToken,
}: SubscriptionPlansManagerProps) {
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editingQuota, setEditingQuota] = useState<string | null>(null);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [quotaValue, setQuotaValue] = useState<number>(0);
  const [nameValue, setNameValue] = useState<string>("");
  const [tierPrices, setTierPrices] = useState<Record<string, TierPrice[]>>({});
  const [editingTierPrice, setEditingTierPrice] = useState<string | null>(null);
  const [tierPriceValue, setTierPriceValue] = useState<number>(0);

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(buildApiUrl("/billing/admin/plans"), {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error("Erreur lors du chargement des plans");
      }

      const data = await response.json();
      const loadedPlans = data.plans || [];
      setPlans(loadedPlans);

      // Fetch tier prices for each plan
      await fetchAllTierPrices(loadedPlans);
    } catch (error) {
      console.error("[PlansManager] Erreur fetch plans:", error);
      toast.error("Erreur lors du chargement des plans");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchAllTierPrices = async (plansList: BillingPlan[]) => {
    try {
      const tierPricesMap: Record<string, TierPrice[]> = {};

      for (const plan of plansList) {
        const response = await fetch(
          buildApiUrl(`/billing/admin/plans/${plan.plan_name}/tier-prices`),
          {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          tierPricesMap[plan.plan_name] = data.tier_prices || [];
        }
      }

      setTierPrices(tierPricesMap);
    } catch (error) {
      console.error("[PlansManager] Erreur fetch tier prices:", error);
    }
  };

  const handleUpdateTierPrice = async (planName: string, tierLevel: number) => {
    try {
      const response = await fetch(
        buildApiUrl(`/billing/admin/plans/${planName}/tier-prices/${tierLevel}`),
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            price_usd: tierPriceValue,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Erreur lors de la mise à jour");
      }

      const data = await response.json();
      toast.success(
        `Prix Tier ${tierLevel} modifié: $${data.old_price_usd} → $${data.new_price_usd}`
      );

      setEditingTierPrice(null);
      await fetchPlans();

      // Demander si on veut recalculer tous les prix des pays
      if (confirm("Voulez-vous recalculer automatiquement les prix marketing de tous les pays avec ce nouveau prix tier ?")) {
        await handleRecalculatePrices();
      }
    } catch (error: any) {
      console.error("[PlansManager] Erreur update tier price:", error);
      toast.error(error.message || "Erreur lors de la mise à jour du prix");
    }
  };

  const handleRecalculatePrices = async () => {
    try {
      const response = await fetch(
        buildApiUrl("/billing/admin/recalculate-prices"),
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Erreur lors du recalcul");
      }

      const data = await response.json();
      toast.success(
        `Prix marketing recalculés! ${data.auto_prices_count} prix automatiques mis à jour`
      );
    } catch (error: any) {
      console.error("[PlansManager] Erreur recalculate prices:", error);
      toast.error(error.message || "Erreur lors du recalcul des prix");
    }
  };

  const handleUpdateQuota = async (planName: string) => {
    try {
      const response = await fetch(
        buildApiUrl(`/billing/admin/plans/${planName}/quota`),
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            monthly_quota: quotaValue,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Erreur lors de la mise à jour");
      }

      const data = await response.json();
      toast.success(
        `Quota modifié: ${data.old_quota} → ${data.new_quota} questions/mois`
      );

      setEditingQuota(null);
      await fetchPlans();
    } catch (error: any) {
      console.error("[PlansManager] Erreur update quota:", error);
      toast.error(error.message || "Erreur lors de la mise à jour du quota");
    }
  };

  const handleUpdateName = async (planName: string) => {
    try {
      const response = await fetch(
        buildApiUrl(`/billing/admin/plans/${planName}/display_name`),
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            display_name: nameValue,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Erreur lors de la mise à jour");
      }

      const data = await response.json();
      toast.success(
        `Nom modifié: "${data.old_name}" → "${data.new_name}"`
      );

      setEditingName(null);
      await fetchPlans();
    } catch (error: any) {
      console.error("[PlansManager] Erreur update name:", error);
      toast.error(error.message || "Erreur lors de la mise à jour du nom");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              Gestion des Plans d'Abonnement
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              Modifier les quotas et les noms d'affichage des plans
            </p>
          </div>
          <button
            onClick={fetchPlans}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            🔄 Actualiser
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Plan
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Nom d'affichage
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Quota Mensuel
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Statut
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {plans.map((plan) => (
              <tr key={plan.plan_name} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div
                      className={`w-2 h-2 rounded-full mr-3 ${
                        plan.plan_name === "free"
                          ? "bg-green-500"
                          : plan.plan_name === "essential"
                          ? "bg-blue-500"
                          : plan.plan_name === "pro"
                          ? "bg-purple-500"
                          : "bg-orange-500"
                      }`}
                    ></div>
                    <span className="text-sm font-medium text-gray-900">
                      {plan.plan_name}
                    </span>
                  </div>
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  {editingName === plan.plan_name ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={nameValue}
                        onChange={(e) => setNameValue(e.target.value)}
                        className="w-32 px-2 py-1 border border-gray-300 rounded text-sm"
                        autoFocus
                      />
                      <button
                        onClick={() => handleUpdateName(plan.plan_name)}
                        className="px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                      >
                        ✓
                      </button>
                      <button
                        onClick={() => setEditingName(null)}
                        className="px-2 py-1 bg-gray-400 text-white text-xs rounded hover:bg-gray-500"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <span className="text-sm text-gray-900">
                      {plan.display_name}
                    </span>
                  )}
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  {editingQuota === plan.plan_name ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={quotaValue}
                        onChange={(e) =>
                          setQuotaValue(parseInt(e.target.value) || 0)
                        }
                        className="w-24 px-2 py-1 border border-gray-300 rounded text-sm"
                        min="0"
                        max="100000"
                        autoFocus
                      />
                      <button
                        onClick={() => handleUpdateQuota(plan.plan_name)}
                        className="px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                      >
                        ✓
                      </button>
                      <button
                        onClick={() => setEditingQuota(null)}
                        className="px-2 py-1 bg-gray-400 text-white text-xs rounded hover:bg-gray-500"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <span className="text-sm text-gray-900">
                      {plan.monthly_quota.toLocaleString()} questions
                    </span>
                  )}
                </td>

                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      plan.active
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {plan.active ? "Actif" : "Inactif"}
                  </span>
                </td>

                <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                  <div className="flex items-center justify-end gap-2">
                    {editingQuota !== plan.plan_name && (
                      <button
                        onClick={() => {
                          setEditingQuota(plan.plan_name);
                          setQuotaValue(plan.monthly_quota);
                        }}
                        className="px-3 py-1 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"
                        title="Modifier le quota"
                      >
                        📊 Quota
                      </button>
                    )}
                    {editingName !== plan.plan_name && (
                      <button
                        onClick={() => {
                          setEditingName(plan.plan_name);
                          setNameValue(plan.display_name);
                        }}
                        className="px-3 py-1 text-purple-600 hover:text-purple-800 hover:bg-purple-50 rounded transition-colors"
                        title="Modifier le nom"
                      >
                        ✏️ Nom
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {plans.length === 0 && (
        <div className="px-6 py-12 text-center text-gray-500">
          Aucun plan trouvé
        </div>
      )}

      {/* Tier Prices Section */}
      {plans.length > 0 && (
        <div className="border-t border-gray-200">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-gray-900">
                Prix par Tier (Tier 1-4)
              </span>
              <span className="text-xs text-gray-500">
                Définir les prix USD pour chaque niveau de marché
              </span>
            </div>
          </div>

          <div className="px-6 py-4 bg-white">
              <div className="grid grid-cols-1 gap-6">
                {plans.map((plan) => {
                  const planTierPrices = tierPrices[plan.plan_name] || [];

                  return (
                    <div
                      key={plan.plan_name}
                      className="border border-gray-200 rounded-lg overflow-hidden"
                    >
                      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                        <h4 className="text-sm font-semibold text-gray-900">
                          {plan.display_name} ({plan.plan_name})
                        </h4>
                      </div>
                      <div className="p-4">
                        <div className="grid grid-cols-4 gap-4">
                          {[1, 2, 3, 4].map((tierLevel) => {
                            const tierPrice = planTierPrices.find(
                              (tp) => tp.tier_level === tierLevel
                            );
                            const editKey = `${plan.plan_name}-tier${tierLevel}`;
                            const isEditing = editingTierPrice === editKey;

                            return (
                              <div
                                key={tierLevel}
                                className="border border-gray-200 rounded-md p-3"
                              >
                                <div className="text-xs font-medium text-gray-500 mb-2">
                                  Tier {tierLevel}
                                  <span className="ml-1 text-gray-400">
                                    {tierLevel === 1
                                      ? "(Émergent)"
                                      : tierLevel === 2
                                      ? "(Intermédiaire)"
                                      : tierLevel === 3
                                      ? "(Développé)"
                                      : "(Premium)"}
                                  </span>
                                </div>

                                {isEditing ? (
                                  <div className="flex items-center gap-1">
                                    <span className="text-sm text-gray-600">$</span>
                                    <input
                                      type="number"
                                      value={tierPriceValue}
                                      onChange={(e) =>
                                        setTierPriceValue(
                                          parseFloat(e.target.value) || 0
                                        )
                                      }
                                      className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                                      step="0.01"
                                      min="0"
                                      autoFocus
                                    />
                                    <button
                                      onClick={() =>
                                        handleUpdateTierPrice(
                                          plan.plan_name,
                                          tierLevel
                                        )
                                      }
                                      className="px-1.5 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                                    >
                                      ✓
                                    </button>
                                    <button
                                      onClick={() => setEditingTierPrice(null)}
                                      className="px-1.5 py-1 bg-gray-400 text-white text-xs rounded hover:bg-gray-500"
                                    >
                                      ✕
                                    </button>
                                  </div>
                                ) : (
                                  <div
                                    onClick={() => {
                                      setEditingTierPrice(editKey);
                                      setTierPriceValue(
                                        tierPrice?.price_usd || 0
                                      );
                                    }}
                                    className="cursor-pointer hover:bg-gray-50 p-2 rounded transition-colors"
                                  >
                                    <div className="text-lg font-semibold text-gray-900">
                                      ${tierPrice?.price_usd.toFixed(2) || "0.00"}
                                    </div>
                                    <div className="text-xs text-gray-500 mt-1">
                                      Cliquer pour modifier
                                    </div>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
                <p className="text-xs text-blue-800">
                  <strong>Note:</strong> Ces prix USD sont utilisés comme base pour calculer
                  automatiquement les prix dans toutes les devises (CAD, EUR, etc.) pour
                  chaque pays selon leur tier. Vous pouvez ensuite personnaliser
                  individuellement chaque pays dans l'onglet "Prix par pays".
                </p>
              </div>
            </div>
        </div>
      )}
    </div>
  );
}
