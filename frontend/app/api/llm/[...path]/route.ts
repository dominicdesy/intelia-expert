/**
 * SÉCURITÉ: Proxy générique pour tous les endpoints RAG Service
 * Version: 1.7.0
 * Last modified: 2025-10-30
 * Updated: Pass Authorization header for Compass integration
 */
// app/api/llm/[...path]/route.ts

import { type NextRequest } from "next/server";
import { secureLog } from "@/lib/utils/secureLogger";
import { createRouteHandlerClient } from "@supabase/auth-helpers-nextjs";
import { cookies } from "next/headers";

/**
 * SÉCURITÉ: Proxy générique pour tous les endpoints RAG Service
 * Redirige les requêtes /api/llm/* vers http://rag:8080/* (réseau interne)
 * Permet de bloquer l'accès public au service RAG pour une sécurité accrue
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const RAG_SERVICE_INTERNAL_URL =
  process.env.RAG_INTERNAL_URL ?? "https://expert.intelia.com/api/llm";

/**
 * Proxy générique pour toutes les méthodes HTTP vers le RAG Service
 */
async function proxyToRAGService(req: NextRequest, params: { path: string[] }) {
  const { path } = params;
  const targetPath = path.join("/");
  const targetUrl = `${RAG_SERVICE_INTERNAL_URL}/${targetPath}`;

  // Copier les query params
  const searchParams = req.nextUrl.searchParams.toString();
  const fullUrl = searchParams ? `${targetUrl}?${searchParams}` : targetUrl;

  secureLog.log(`[rag-service-proxy] ${req.method} ${fullUrl}`);

  try {
    // 🆕 Get Supabase JWT token for Compass API authentication
    let authToken: string | null = null;
    try {
      const supabase = createRouteHandlerClient({ cookies });
      const {
        data: { session },
      } = await supabase.auth.getSession();
      authToken = session?.access_token ?? null;

      if (authToken) {
        secureLog.log(`[rag-service-proxy] ✅ Auth token obtained for user`);
      } else {
        secureLog.warn(`[rag-service-proxy] ⚠️ No auth token available - user not authenticated`);
      }
    } catch (authError) {
      secureLog.warn(`[rag-service-proxy] Auth token retrieval failed: ${authError}`);
    }

    // Copier le body si présent
    let body: BodyInit | undefined = undefined;
    if (req.method !== "GET" && req.method !== "HEAD") {
      const contentType = req.headers.get("content-type");
      if (contentType?.includes("application/json")) {
        const json = await req.json();
        body = JSON.stringify(json);
      } else if (contentType?.includes("multipart/form-data")) {
        body = await req.formData();
      } else {
        body = await req.text();
      }
    }

    // 🆕 Build headers with Authorization token
    const headers: HeadersInit = {
      "Content-Type": req.headers.get("content-type") ?? "application/json",
      Accept: req.headers.get("accept") ?? "*/*",
    };

    // Add Authorization header if token available
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    // Appel au RAG Service interne
    const response = await fetch(fullUrl, {
      method: req.method,
      headers,
      body,
    });

    // Copier les headers de la réponse
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      responseHeaders.set(key, value);
    });

    // Pour les réponses streaming (SSE)
    if (response.headers.get("content-type")?.includes("text/event-stream")) {
      return new Response(response.body, {
        status: response.status,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache, no-transform",
          Connection: "keep-alive",
          "X-Accel-Buffering": "no",
        },
      });
    }

    // Pour les autres réponses
    const responseBody = await response.text();
    return new Response(responseBody, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error) {
    secureLog.error(`[rag-service-proxy] Erreur: ${error}`);
    return new Response(
      JSON.stringify({
        error: "Service RAG temporairement indisponible",
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
  return proxyToRAGService(req, params);
}

export async function POST(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToRAGService(req, params);
}

export async function PUT(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToRAGService(req, params);
}

export async function DELETE(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToRAGService(req, params);
}

export async function PATCH(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToRAGService(req, params);
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
