// lib/api/stripe.ts
/**
 * Stripe API Helper Functions
 * Gestion des abonnements et paiements avec Stripe Link
 * Version: 1.0
 */

import { API_CONFIG } from "@/lib/api/config";

// ==================== TYPES ====================

export interface SubscriptionStatus {
  has_subscription: boolean;
  plan_name?: string;
  status?: string;
  current_period_end?: string;
  cancel_at_period_end?: boolean;
  price_monthly?: number;
  currency?: string;
}

export interface CheckoutSessionResponse {
  success: boolean;
  checkout_url?: string;
  session_id?: string;
  error?: string;
}

export interface CustomerPortalResponse {
  success: boolean;
  portal_url?: string;
  error?: string;
}

// ==================== API FUNCTIONS ====================

/**
 * Crée une session Stripe Checkout pour upgrade de plan
 * @param planName - "pro" ou "elite"
 * @param token - JWT token d'authentification
 * @param locale - Code de langue optionnel (ex: "fr", "en", "es")
 * @returns URL de redirection vers Stripe Checkout
 */
export async function createCheckoutSession(
  planName: string,
  token: string,
  locale?: string
): Promise<CheckoutSessionResponse> {
  try {
    const response = await fetch(
      `${API_CONFIG.BASE_URL}/stripe/create-checkout-session`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          plan_name: planName,
          success_url: `${window.location.origin}/billing/success`,
          cancel_url: `${window.location.origin}/billing/cancel`,
          locale: locale, // Passer la langue de l'utilisateur
        }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Erreur création session checkout");
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("[Stripe] Erreur création checkout:", error);
    return {
      success: false,
      error:
        error instanceof Error
          ? error.message
          : "Erreur lors de la création de la session de paiement",
    };
  }
}

/**
 * Récupère le statut d'abonnement de l'utilisateur actuel
 * @param token - JWT token d'authentification
 * @returns Statut de l'abonnement
 */
export async function getSubscriptionStatus(
  token: string
): Promise<SubscriptionStatus> {
  try {
    const response = await fetch(
      `${API_CONFIG.BASE_URL}/stripe/subscription-status`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      console.error("[Stripe] Erreur récupération statut");
      return { has_subscription: false };
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("[Stripe] Erreur statut subscription:", error);
    return { has_subscription: false };
  }
}

/**
 * Génère l'URL du Stripe Customer Portal pour gérer l'abonnement
 * @param token - JWT token d'authentification
 * @returns URL du portail client Stripe
 */
export async function getCustomerPortalUrl(
  token: string
): Promise<CustomerPortalResponse> {
  try {
    const response = await fetch(
      `${API_CONFIG.BASE_URL}/stripe/customer-portal`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Erreur création portail client");
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("[Stripe] Erreur portail client:", error);
    return {
      success: false,
      error:
        error instanceof Error
          ? error.message
          : "Erreur lors de l'accès au portail client",
    };
  }
}

/**
 * Helper: Redirige l'utilisateur vers Stripe Checkout
 * @param planName - "pro" ou "elite"
 * @param token - JWT token
 * @param locale - Code de langue optionnel (ex: "fr", "en", "es")
 */
export async function redirectToCheckout(
  planName: string,
  token: string,
  locale?: string
): Promise<void> {
  const result = await createCheckoutSession(planName, token, locale);

  if (result.success && result.checkout_url) {
    // Redirection vers Stripe Checkout
    window.location.href = result.checkout_url;
  } else {
    throw new Error(result.error || "Impossible de créer la session");
  }
}

/**
 * Helper: Redirige l'utilisateur vers le portail client Stripe
 * @param token - JWT token
 */
export async function redirectToCustomerPortal(token: string): Promise<void> {
  const result = await getCustomerPortalUrl(token);

  if (result.success && result.portal_url) {
    // Redirection vers Stripe Customer Portal
    window.location.href = result.portal_url;
  } else {
    throw new Error(
      result.error || "Impossible d'accéder au portail client"
    );
  }
}

// ==================== PLAN HELPERS ====================

/**
 * Retourne le prix d'un plan en USD (par défaut)
 * @param planName - "essential", "pro", ou "elite"
 * @returns Prix mensuel en USD
 */
export function getPlanPrice(planName: string): number {
  const prices: Record<string, number> = {
    essential: 0,
    pro: 18,
    elite: 28,
  };
  return prices[planName.toLowerCase()] || 0;
}

/**
 * Retourne le nom formaté d'un plan
 * @param planName - "essential", "pro", ou "elite"
 * @returns Nom formaté
 */
export function getPlanDisplayName(planName: string): string {
  const names: Record<string, string> = {
    essential: "Essential",
    pro: "Pro",
    elite: "Elite",
  };
  return names[planName.toLowerCase()] || planName;
}

/**
 * Vérifie si un plan est payant
 * @param planName - Nom du plan
 * @returns true si payant
 */
export function isPaidPlan(planName: string): boolean {
  return ["pro", "elite"].includes(planName.toLowerCase());
}

/**
 * Retourne la couleur du plan pour l'UI
 * @param planName - Nom du plan
 * @returns Classe Tailwind de couleur
 */
export function getPlanColor(planName: string): string {
  const colors: Record<string, string> = {
    essential: "text-green-600",
    pro: "text-blue-600",
    elite: "text-purple-600",
  };
  return colors[planName.toLowerCase()] || "text-gray-600";
}

/**
 * Retourne la couleur de fond du plan pour l'UI
 * @param planName - Nom du plan
 * @returns Classe Tailwind de couleur de fond
 */
export function getPlanBgColor(planName: string): string {
  const colors: Record<string, string> = {
    essential: "bg-green-50",
    pro: "bg-blue-50",
    elite: "bg-purple-50",
  };
  return colors[planName.toLowerCase()] || "bg-gray-50";
}

/**
 * Retourne la couleur de bordure du plan pour l'UI
 * @param planName - Nom du plan
 * @returns Classe Tailwind de couleur de bordure
 */
export function getPlanBorderColor(planName: string): string {
  const colors: Record<string, string> = {
    essential: "border-green-200",
    pro: "border-blue-200",
    elite: "border-purple-200",
  };
  return colors[planName.toLowerCase()] || "border-gray-200";
}
