// app/api/chat/stream/route.ts
import { NextRequest } from "next/server";

export const runtime = "nodejs"; // Edge supporte aussi, mais Node est plus simple pour SSE

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    
    // Validation minimale des données requises
    if (!payload?.tenant_id || !payload?.message) {
      return new Response(
        JSON.stringify({ 
          error: "invalid_payload",
          message: "tenant_id et message sont requis" 
        }), 
        { 
          status: 400,
          headers: { "Content-Type": "application/json" }
        }
      );
    }

    // Validation de l'URL backend
    const backendUrl = process.env.LLM_BACKEND_URL;
    if (!backendUrl) {
      console.error('[chat/stream] LLM_BACKEND_URL non configurée');
      return new Response(
        JSON.stringify({ 
          error: "server_configuration",
          message: "Configuration serveur manquante" 
        }), 
        { 
          status: 500,
          headers: { "Content-Type": "application/json" }
        }
      );
    }

    console.log('[chat/stream] Proxying vers:', `${backendUrl}/chat/stream`);
    console.log('[chat/stream] Payload:', {
      tenant_id: payload.tenant_id,
      lang: payload.lang,
      message_length: payload.message?.length || 0
    });

    // Appel vers l'API LLM backend
    const upstream = await fetch(`${backendUrl}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Frontend-Origin": "intelia",
        "User-Agent": "Intelia-Frontend/1.0",
      },
      body: JSON.stringify(payload),
    });

    console.log('[chat/stream] Upstream status:', upstream.status);

    // Si erreur HTTP (quota, auth, etc.), forward la réponse JSON
    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text();
      console.error('[chat/stream] Upstream error:', text);
      
      return new Response(
        text || JSON.stringify({ 
          error: "upstream_error",
          status: upstream.status 
        }), 
        { 
          status: upstream.status,
          headers: { "Content-Type": "application/json" }
        }
      );
    }

    console.log('[chat/stream] Streaming SSE démarré');

    // Proxy du flux SSE tel quel
    return new Response(upstream.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });

  } catch (error) {
    console.error('[chat/stream] Erreur proxy:', error);
    return new Response(
      JSON.stringify({ 
        error: "proxy_error",
        message: "Erreur interne du proxy" 
      }), 
      { 
        status: 500,
        headers: { "Content-Type": "application/json" }
      }
    );
  }
}

// Gestion CORS pour les requêtes OPTIONS
export async function OPTIONS() {
  return new Response(null, {
    status: 200,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}