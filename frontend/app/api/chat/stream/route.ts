// app/api/chat/stream/route.ts - VERSION CORRIGÉE
import { NextRequest } from "next/server";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    
    // Validation minimale des données requises
    if (!payload?.tenant_id || !payload?.message) {
      console.error('[chat/stream] Paramètres manquants:', { 
        tenant_id: !!payload?.tenant_id, 
        message: !!payload?.message 
      });
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

    // Configuration backend avec fallbacks multiples
    const backendUrl = 
      process.env.LLM_BACKEND_URL || 
      process.env.NEXT_PUBLIC_LLM_BACKEND_URL || 
      'http://localhost:8007';

    if (!backendUrl) {
      console.error('[chat/stream] Aucune URL backend configurée');
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

    // URL correcte pour le backend LLM
    const targetUrl = `${backendUrl}/api/chat/stream`;
    
    console.log('[chat/stream] Proxying vers:', targetUrl);
    console.log('[chat/stream] Payload:', {
      tenant_id: payload.tenant_id,
      lang: payload.lang,
      message_preview: payload.message?.substring(0, 50) + '...',
      conversation_id: payload.conversation_id?.substring(0, 8) + '...',
      user_context: !!payload.user_context
    });

    // Appel vers l'API LLM backend avec timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

    const upstream = await fetch(targetUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "X-Frontend-Origin": "intelia-expert",
        "User-Agent": "Intelia-Frontend/1.0",
        "Cache-Control": "no-cache",
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    console.log('[chat/stream] Upstream status:', upstream.status);
    console.log('[chat/stream] Upstream headers:', Object.fromEntries(upstream.headers.entries()));

    // Si erreur HTTP, forward la réponse JSON
    if (!upstream.ok) {
      const text = await upstream.text();
      console.error('[chat/stream] Upstream error:', {
        status: upstream.status,
        statusText: upstream.statusText,
        body: text.substring(0, 500)
      });
      
      return new Response(
        text || JSON.stringify({ 
          error: "upstream_error",
          status: upstream.status,
          message: `Backend LLM error: ${upstream.statusText}`
        }), 
        { 
          status: upstream.status,
          headers: { "Content-Type": "application/json" }
        }
      );
    }

    if (!upstream.body) {
      console.error('[chat/stream] Pas de body dans la réponse upstream');
      return new Response(
        JSON.stringify({ 
          error: "no_stream_body",
          message: "Pas de flux de données reçu du backend" 
        }), 
        { 
          status: 502,
          headers: { "Content-Type": "application/json" }
        }
      );
    }

    console.log('[chat/stream] Streaming SSE démarré - proxying vers frontend');

    // Headers optimisés pour SSE
    const headers = new Headers({
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-store, must-revalidate",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no", // Nginx
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Accept",
      "Access-Control-Expose-Headers": "Content-Type",
    });

    // Créer un stream transformé pour debug et gestion d'erreurs
    const transformedStream = new ReadableStream({
      start(controller) {
        console.log('[chat/stream] Transform stream started');
      },
      
      async pull(controller) {
        try {
          const reader = upstream.body!.getReader();
          const decoder = new TextDecoder();
          
          while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
              console.log('[chat/stream] Upstream stream completed');
              controller.close();
              break;
            }
            
            // Décoder et logger les chunks pour debug
            const chunk = decoder.decode(value, { stream: true });
            
            // Logger les événements spéciaux (relances proactives)
            if (chunk.includes('"type":"proactive_followup"')) {
              console.log('[chat/stream] 🚀 RELANCE PROACTIVE détectée:', 
                chunk.substring(0, 100) + '...'
              );
            }
            
            if (chunk.includes('"type":"delta"')) {
              console.log('[chat/stream] 📝 Delta reçu:', chunk.length, 'bytes');
            }
            
            if (chunk.includes('"type":"final"')) {
              console.log('[chat/stream] ✅ Réponse finale reçue');
            }
            
            if (chunk.includes('"type":"error"')) {
              console.log('[chat/stream] ❌ Erreur dans le stream:', chunk);
            }
            
            // Forward le chunk tel quel
            controller.enqueue(value);
          }
          
        } catch (error) {
          console.error('[chat/stream] Erreur dans transform stream:', error);
          
          // Envoyer un événement d'erreur au frontend
          const errorEvent = `data: ${JSON.stringify({
            type: "error",
            message: "Erreur de streaming",
            error: error instanceof Error ? error.message : "Erreur inconnue"
          })}\n\n`;
          
          controller.enqueue(new TextEncoder().encode(errorEvent));
          controller.close();
        }
      },
      
      cancel() {
        console.log('[chat/stream] Transform stream cancelled');
      }
    });

    return new Response(transformedStream, { headers });

  } catch (error) {
    console.error('[chat/stream] Erreur proxy générale:', error);
    
    // Retourner une erreur JSON lisible
    return new Response(
      JSON.stringify({ 
        error: "proxy_error",
        message: error instanceof Error ? error.message : "Erreur interne du proxy",
        details: "Vérifiez la configuration LLM_BACKEND_URL et la disponibilité du backend"
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
      "Access-Control-Allow-Headers": "Content-Type, Accept, Authorization",
      "Access-Control-Max-Age": "86400",
    },
  });
}