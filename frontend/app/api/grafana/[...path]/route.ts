// app/api/grafana/[...path]/route.ts

import { type NextRequest } from "next/server";
import { secureLog } from "@/lib/utils/secureLogger";
import { createClient } from "@/lib/supabase/server";

/**
 * SÉCURITÉ: Proxy sécurisé pour Grafana
 * - Vérifie l'authentification utilisateur
 * - Vérifie les permissions super_admin
 * - Proxy vers http://grafana:3000 (réseau interne uniquement)
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const GRAFANA_INTERNAL_URL =
  process.env.GRAFANA_INTERNAL_URL ?? "http://grafana:3000";

/**
 * Vérifie que l'utilisateur est authentifié et super_admin
 */
async function checkAuth(req: NextRequest): Promise<{ authorized: boolean; error?: string }> {
  try {
    const supabase = await createClient();

    // Vérifier l'authentification Supabase
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      secureLog.warn("[grafana-proxy] User not authenticated");
      return { authorized: false, error: "Authentication required" };
    }

    // Récupérer le user_type depuis la table users
    const { data: userData, error: userError } = await supabase
      .from("users")
      .select("user_type")
      .eq("email", user.email)
      .single();

    if (userError || !userData) {
      secureLog.warn(`[grafana-proxy] User data not found for ${user.email}`);
      return { authorized: false, error: "User data not found" };
    }

    // Vérifier que l'utilisateur est super_admin
    if (userData.user_type !== "super_admin") {
      secureLog.warn(`[grafana-proxy] Access denied for ${user.email} (role: ${userData.user_type})`);
      return { authorized: false, error: "Super admin access required" };
    }

    secureLog.log(`[grafana-proxy] Access granted for ${user.email}`);
    return { authorized: true };
  } catch (error) {
    secureLog.error(`[grafana-proxy] Auth check failed: ${error}`);
    return { authorized: false, error: "Authentication check failed" };
  }
}

/**
 * Proxy générique pour toutes les méthodes HTTP vers Grafana
 */
async function proxyToGrafana(req: NextRequest, params: { path: string[] }) {
  // Vérifier l'authentification et les permissions
  const authCheck = await checkAuth(req);
  if (!authCheck.authorized) {
    return new Response(
      JSON.stringify({
        error: "Access denied",
        detail: authCheck.error,
      }),
      {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }
    );
  }

  const { path } = params;
  const targetPath = path.join("/");
  const targetUrl = `${GRAFANA_INTERNAL_URL}/${targetPath}`;

  // Copier les query params
  const searchParams = req.nextUrl.searchParams.toString();
  const fullUrl = searchParams ? `${targetUrl}?${searchParams}` : targetUrl;

  secureLog.log(`[grafana-proxy] ${req.method} ${fullUrl}`);

  try {
    // Copier le body si présent
    let body: BodyInit | undefined = undefined;
    if (req.method !== "GET" && req.method !== "HEAD") {
      const contentType = req.headers.get("content-type");
      if (contentType?.includes("application/json")) {
        const json = await req.json();
        body = JSON.stringify(json);
      } else {
        body = await req.text();
      }
    }

    // Appel à Grafana interne
    const response = await fetch(fullUrl, {
      method: req.method,
      headers: {
        "Content-Type": req.headers.get("content-type") ?? "application/json",
        Accept: req.headers.get("accept") ?? "*/*",
      },
      body,
    });

    // Copier les headers de la réponse
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      // Ne pas copier les headers de sécurité qui pourraient interférer
      if (!["x-frame-options", "content-security-policy"].includes(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    });

    // Pour les réponses HTML/JSON
    const responseBody = await response.arrayBuffer();
    return new Response(responseBody, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error) {
    secureLog.error(`[grafana-proxy] Error: ${error}`);
    return new Response(
      JSON.stringify({
        error: "Grafana service temporarily unavailable",
        detail: String(error),
      }),
      {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

export async function GET(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToGrafana(req, params);
}

export async function POST(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToGrafana(req, params);
}

export async function PUT(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToGrafana(req, params);
}

export async function DELETE(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToGrafana(req, params);
}

export async function PATCH(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToGrafana(req, params);
}

export async function OPTIONS(req: NextRequest) {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Accept",
    },
  });
}
