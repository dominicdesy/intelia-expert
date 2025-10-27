/**
 * SÉCURITÉ: Proxy générique pour tous les endpoints LLM
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
// app/api/llm/[...path]/route.ts

import { type NextRequest } from "next/server";
import { secureLog } from "@/lib/utils/secureLogger";

/**
 * SÉCURITÉ: Proxy générique pour tous les endpoints LLM
 * Redirige les requêtes /api/llm/* vers http://intelia-llm:8080/* (réseau interne)
 * Permet de bloquer l'accès public au service LLM pour une sécurité accrue
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const LLM_INTERNAL_URL =
  process.env.LLM_INTERNAL_URL ?? "https://expert.intelia.com/llm";

/**
 * Proxy générique pour toutes les méthodes HTTP vers le LLM
 */
async function proxyToLLM(req: NextRequest, params: { path: string[] }) {
  const { path } = params;
  const targetPath = path.join("/");
  const targetUrl = `${LLM_INTERNAL_URL}/${targetPath}`;

  // Copier les query params
  const searchParams = req.nextUrl.searchParams.toString();
  const fullUrl = searchParams ? `${targetUrl}?${searchParams}` : targetUrl;

  secureLog.log(`[llm-proxy] ${req.method} ${fullUrl}`);

  try {
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

    // Appel au LLM interne
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
    secureLog.error(`[llm-proxy] Erreur: ${error}`);
    return new Response(
      JSON.stringify({
        error: "Service LLM temporairement indisponible",
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
  return proxyToLLM(req, params);
}

export async function POST(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToLLM(req, params);
}

export async function PUT(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToLLM(req, params);
}

export async function DELETE(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToLLM(req, params);
}

export async function PATCH(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToLLM(req, params);
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
