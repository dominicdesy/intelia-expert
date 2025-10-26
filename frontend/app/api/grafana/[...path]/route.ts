// app/api/grafana/[...path]/route.ts

import { type NextRequest } from "next/server";
import { secureLog } from "@/lib/utils/secureLogger";

/**
 * SÉCURITÉ: Proxy pour Grafana (réseau interne uniquement)
 * - Proxy vers http://grafana:3000 (réseau interne)
 * - Protection par auth anonyme Grafana (role Viewer read-only)
 * - Page /admin/statistics vérifie déjà super_admin côté React
 *
 * Build: 2025-01-26
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const GRAFANA_INTERNAL_URL =
  process.env.GRAFANA_INTERNAL_URL ?? "http://grafana:3000";

/**
 * Proxy générique pour toutes les méthodes HTTP vers Grafana
 */
async function proxyToGrafana(req: NextRequest, params: { path: string[] }) {

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
