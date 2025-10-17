"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { buildApiUrl } from "@/lib/api/config";

interface SubscriptionStats {
  total_subscriptions: number;
  active_subscriptions: number;
  total_revenue_monthly: number;
  by_plan: {
    plan_name: string;
    count: number;
    revenue: number;
  }[];
}

export default function SubscriptionsAdminPage() {
  const router = useRouter();
  const [stats, setStats] = useState<SubscriptionStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    // Vérifier que l'utilisateur est super admin
    const checkAuth = async () => {
      try {
        // Récupérer le token JWT depuis localStorage (comme UpgradePlanModal)
        let accessToken: string | null = null;

        // Méthode 1: Récupérer depuis intelia-expert-auth (PRIORITÉ)
        const authData = localStorage.getItem("intelia-expert-auth");
        if (authData) {
          try {
            const parsed = JSON.parse(authData);
            accessToken = parsed.access_token;
            console.log("[SubscriptionsAdmin] Token trouvé dans intelia-expert-auth");
          } catch (e) {
            console.error("[SubscriptionsAdmin] Erreur parse intelia-expert-auth:", e);
          }
        }

        // Méthode 2: Fallback vers ancien format
        if (!accessToken) {
          accessToken = localStorage.getItem("access_token");
          console.log("[SubscriptionsAdmin] Fallback vers access_token");
        }

        if (!accessToken) {
          console.error("[SubscriptionsAdmin] Aucun token trouvé");
          router.push("/");
          return;
        }

        // TODO: Récupérer infos utilisateur et vérifier is_admin/user_type
        // Pour l'instant, on suppose que l'accès est autorisé si token existe

        await fetchStats(accessToken);
      } catch (error) {
        console.error("[SubscriptionsAdmin] Erreur auth:", error);
        router.push("/");
      }
    };

    checkAuth();
  }, [router]);

  const fetchStats = async (token: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(
        buildApiUrl("/billing/admin"),
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Accès refusé");
      }

      const data = await response.json();

      // Adapter les données du backend
      const adaptedStats: SubscriptionStats = {
        total_subscriptions: data.user_overview?.total_billing_users || 0,
        active_subscriptions: data.user_overview?.paid_users || 0,
        total_revenue_monthly: data.revenue_metrics?.monthly_recurring_revenue || 0,
        by_plan: (data.plan_distribution || []).map((plan: any) => ({
          plan_name: plan.display_name || plan.plan_name,
          count: plan.user_count || 0,
          revenue: (plan.price_per_month || 0) * (plan.user_count || 0),
        })),
      };

      setStats(adaptedStats);
    } catch (error) {
      console.error("[SubscriptionsAdmin] Erreur fetch stats:", error);
      toast.error("Erreur lors du chargement des statistiques");
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Chargement des statistiques...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                📊 Gestion des Abonnements
              </h1>
              <p className="mt-2 text-gray-600">
                Vue d'ensemble des abonnements Stripe
              </p>
            </div>
            <button
              onClick={() => router.push("/chat")}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              ← Retour
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  Total Abonnements
                </p>
                <p className="mt-2 text-3xl font-bold text-gray-900">
                  {stats?.total_subscriptions || 0}
                </p>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <svg
                  className="w-8 h-8 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                  />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  Abonnements Actifs
                </p>
                <p className="mt-2 text-3xl font-bold text-green-600">
                  {stats?.active_subscriptions || 0}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <svg
                  className="w-8 h-8 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  Revenu Mensuel
                </p>
                <p className="mt-2 text-3xl font-bold text-purple-600">
                  ${stats?.total_revenue_monthly?.toFixed(2) || "0.00"}
                </p>
              </div>
              <div className="p-3 bg-purple-100 rounded-full">
                <svg
                  className="w-8 h-8 text-purple-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Plans Breakdown */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Répartition par Plan
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Plan
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Abonnés
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Revenu Mensuel
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    %
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {stats?.by_plan.map((plan) => {
                  const percentage =
                    stats.total_subscriptions > 0
                      ? ((plan.count / stats.total_subscriptions) * 100).toFixed(1)
                      : "0";

                  return (
                    <tr key={plan.plan_name}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div
                            className={`w-2 h-2 rounded-full mr-3 ${
                              plan.plan_name === "Essential" || plan.plan_name === "free"
                                ? "bg-green-500"
                                : plan.plan_name === "Pro"
                                ? "bg-blue-500"
                                : "bg-purple-500"
                            }`}
                          ></div>
                          <span className="text-sm font-medium text-gray-900">
                            {plan.plan_name}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {plan.count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${plan.revenue.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <span className="text-sm text-gray-900 mr-2">
                            {percentage}%
                          </span>
                          <div className="w-16 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{ width: `${percentage}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Actions Rapides
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <a
              href="https://dashboard.stripe.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center px-4 py-3 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              <span className="mr-2">🔗</span>
              Ouvrir Stripe Dashboard
            </a>
            <button
              onClick={() => {
                // Récupérer le token depuis intelia-expert-auth (comme checkAuth)
                let accessToken: string | null = null;
                const authData = localStorage.getItem("intelia-expert-auth");
                if (authData) {
                  try {
                    const parsed = JSON.parse(authData);
                    accessToken = parsed.access_token;
                  } catch (e) {
                    console.error("Erreur parse token:", e);
                  }
                }
                if (!accessToken) {
                  accessToken = localStorage.getItem("access_token");
                }
                if (accessToken) fetchStats(accessToken);
              }}
              className="flex items-center justify-center px-4 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              <span className="mr-2">🔄</span>
              Actualiser les données
            </button>
            <button
              onClick={() => toast("Export à venir...")}
              className="flex items-center justify-center px-4 py-3 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              <span className="mr-2">📥</span>
              Exporter les données
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
