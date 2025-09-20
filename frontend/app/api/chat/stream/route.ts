// app/api/chat/stream/route.ts

import type { NextRequest } from "next/server";

/**
 * Forcer un vrai streaming côté Next.js
 * - Node runtime (évite certains buffers de l'Edge runtime)
 * - Pas de cache sur cette route
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * CORRECTION: Utilisation de la variable d'environnement LLM_BACKEND_URL
 * qui pointe vers https://expert.intelia.com/llm
 * Construction dynamique de l'URL du streaming endpoint
 */
const LLM_BACKEND_URL = process.env.NEXT_PUBLIC_LLM_BACKEND_URL ?? "https://expert.intelia.com/llm";
const LLM_STREAM_URL = `${LLM_BACKEND_URL}/chat/stream`;

/**
 * En-têtes SSE conseillés pour éviter tout buffering intermédiaire.
 * - no-transform : empêche certains proxies/CDN de « réécrire » le flux
 * - X-Accel-Buffering: no : clé avec Nginx/ingress
 */
const SSE_HEADERS: HeadersInit = {
  "Content-Type": "text/event-stream; charset=utf-8",
  "Cache-Control": "no-cache, no-transform",
  Connection: "keep-alive",
  "X-Accel-Buffering": "no",
  // CORS basique si la route est appelée depuis un autre domaine
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Accept",
  "Access-Control-Expose-Headers": "Content-Type",
};

/** Réponse à la préflight CORS */
export async function OPTIONS() {
  return new Response(null, { status: 204, headers: SSE_HEADERS });
}

/**
 * Proxy SSE → "pipe" *chaque* chunk immédiatement au navigateur.
 * Lecture en `start()` avec boucle push() récursive.
 */
export async function POST(req: NextRequest) {
  // Récupère le payload JSON tel quel (lang, message, tenant, etc.)
  const payload = await req.json().catch(() => ({}));

  // CORRECTION: URL construite dynamiquement avec la variable d'environnement
  console.log(`[route.ts] Appel vers: ${LLM_STREAM_URL}`);

  // Appel du backend LLM (FastAPI) qui renvoie un flux text/event-stream
  const controller = new AbortController();
  const upstream = await fetch(LLM_STREAM_URL, {
    method: "POST",
    signal: controller.signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      // Évite certains caches intermédiaires côté fetch()
      "Cache-Control": "no-cache",
    },
    body: JSON.stringify(payload),
  }).catch((err) => {
    // Si le backend est injoignable, on renvoie un flux SSE avec une erreur
    console.error(`[route.ts] Erreur connexion vers ${LLM_STREAM_URL}:`, err);
    const errEvent = `data: ${JSON.stringify({
      type: "error",
      message:
        "Le service de génération est momentanément indisponible. Réessayez dans un instant.",
      detail: String(err),
    })}\n\n`;
    return new Response(
      new ReadableStream({
        start(c) {
          c.enqueue(new TextEncoder().encode(errEvent));
          c.close();
        },
      }),
    );
  });

  // Si pas de body, on renvoie une erreur SSE et on termine
  if (!upstream.body) {
    const errEvent = `data: ${JSON.stringify({
      type: "error",
      message: "Pas de flux renvoyé par le backend.",
    })}\n\n`;
    const rs = new ReadableStream({
      start(c) {
        c.enqueue(new TextEncoder().encode(errEvent));
        c.close();
      },
    });
    return new Response(rs, { headers: SSE_HEADERS, status: 502 });
  }

  // Transform stream: lit en amont et "pousse" les chunks tels quels au client
  const transformed = new ReadableStream({
    start(controller) {
      const reader = upstream.body!.getReader();
      const decoder = new TextDecoder();
      const encoder = new TextEncoder();

      // Heartbeat (facultatif) pour garder certaines connexions vivantes
      const heartbeat = setInterval(() => {
        try {
          controller.enqueue(encoder.encode(":ping\n\n"));
        } catch {
          /* noop */
        }
      }, 15000);

      function push(): void {
        reader
          .read()
          .then(({ done, value }) => {
            if (done) {
              clearInterval(heartbeat);
              controller.close();
              return;
            }

            // (Optionnel) petit hook de debug si vous voulez tracer des relances
            try {
              const chunkText = decoder.decode(value, { stream: true });
              if (chunkText.includes('"type":"proactive_followup"')) {
                // eslint-disable-next-line no-console
                console.log("[chat/stream] 🚀 RELANCE PROACTIVE détectée");
              }
            } catch {
              /* ignore decode errors */
            }

            controller.enqueue(value);
            push();
          })
          .catch((err) => {
            clearInterval(heartbeat);
            const errorEvent = `data: ${JSON.stringify({
              type: "error",
              message: "Erreur de streaming vers le client.",
              detail: String(err),
            })}\n\n`;
            controller.enqueue(encoder.encode(errorEvent));
            controller.close();
          });
      }

      push();
    },
    cancel() {
      // Annule l'appel amont si le client ferme la connexion
      try {
        controller.abort();
      } catch {
        /* noop */
      }
    },
  });

  return new Response(transformed, {
    status: 200,
    headers: SSE_HEADERS,
  });
}