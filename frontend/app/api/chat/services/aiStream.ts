// app/chat/services/aiStream.ts

// Types pour les événements SSE
export type DeltaEvent = { 
  type: "delta"; 
  text: string 
};

export type FinalEvent = { 
  type: "final"; 
  answer: string 
};

export type ErrorEvent = { 
  type: "error"; 
  code?: string; 
  message?: string 
};

export type StreamEvent = DeltaEvent | FinalEvent | ErrorEvent;

// Type pour le payload de chat
export type ChatStreamBody = { 
  tenant_id: string; 
  lang: string; 
  message: string;
  // Optionnels pour extensions futures
  conversation_id?: string;
  user_context?: Record<string, any>;
};

/**
 * Service principal pour le streaming AI via SSE
 * Gère la communication avec l'endpoint /api/chat/stream
 */
export async function streamAIResponse(
  body: ChatStreamBody,
  onDelta: (text: string) => void,
  signal?: AbortSignal,
): Promise<string> {
  
  console.log('[aiStream] Démarrage du stream:', {
    tenant: body.tenant_id,
    lang: body.lang,
    message_preview: body.message.substring(0, 50) + '...'
  });

  try {
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
      },
      body: JSON.stringify(body),
      signal,
    });

    console.log('[aiStream] Response status:', res.status);

    // Si l'API retourne une erreur non-SSE (ex. 402 quota, 401 auth), on la propage
    if (!res.ok) {
      let errorInfo: any = null;
      try { 
        const text = await res.text();
        errorInfo = JSON.parse(text); 
      } catch { 
        errorInfo = { error: `http_${res.status}`, message: `Erreur HTTP ${res.status}` };
      }
      
      console.error('[aiStream] Erreur HTTP:', errorInfo);
      
      const err: ErrorEvent = { 
        type: "error", 
        code: errorInfo?.error || `${res.status}`, 
        message: errorInfo?.message || `Erreur ${res.status}`
      };
      throw err;
    }

    if (!res.body) {
      throw new Error("Pas de flux de données reçu");
    }

    return await processSSEStream(res.body, onDelta, signal);

  } catch (error) {
    console.error('[aiStream] Erreur stream:', error);
    
    // Si c'est une ErrorEvent, on la relance telle quelle
    if (error && typeof error === 'object' && 'type' in error && error.type === 'error') {
      throw error;
    }
    
    // Si c'est une AbortError (stop volontaire), on retourne silencieusement
    if (error instanceof Error && error.name === 'AbortError') {
      console.log('[aiStream] Stream arrêté par l\'utilisateur');
      return '';
    }
    
    // Autres erreurs
    const fallbackError: ErrorEvent = {
      type: "error",
      code: "stream_error",
      message: error instanceof Error ? error.message : "Erreur de streaming inconnue"
    };
    throw fallbackError;
  }
}

/**
 * Traite le flux SSE ligne par ligne
 * Parser tolérant pour gérer les coupures/buffers partiels
 */
async function processSSEStream(
  body: ReadableStream<Uint8Array>, 
  onDelta: (text: string) => void,
  signal?: AbortSignal
): Promise<string> {
  
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let finalAnswer = "";
  let buffer = "";
  let deltaCount = 0;

  try {
    while (true) {
      // Vérification du signal d'arrêt
      if (signal?.aborted) {
        console.log('[aiStream] Stream interrompu par signal');
        break;
      }

      const { value, done } = await reader.read();
      
      if (done) {
        console.log('[aiStream] Stream terminé, deltas reçus:', deltaCount);
        break;
      }

      // Décodage progressif des chunks
      buffer += decoder.decode(value, { stream: true });

      // Traitement ligne par ligne (format SSE)
      let newlineIndex: number;
      while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 1);
        
        // Ignore les lignes vides et non-SSE
        if (!line || !line.startsWith("data:")) {
          continue;
        }
        
        const jsonStr = line.slice(5).trim(); // Enlève "data:"
        if (!jsonStr || jsonStr === "[DONE]") {
          continue;
        }
        
        try {
          const event = JSON.parse(jsonStr) as StreamEvent;
          
          switch (event.type) {
            case "delta":
              if (typeof event.text === "string" && event.text) {
                onDelta(event.text);
                deltaCount++;
              }
              break;
              
            case "final":
              finalAnswer = event.answer || "";
              console.log('[aiStream] Réponse finale reçue, taille:', finalAnswer.length);
              break;
              
            case "error":
              console.error('[aiStream] Erreur dans le stream:', event);
              throw event;
              
            default:
              console.warn('[aiStream] Type d\'événement inconnu:', event);
          }
          
        } catch (parseError) {
          // Ignore les lignes JSON malformées (chunks partiels)
          // En mode debug, on pourrait logger
          // console.debug('[aiStream] Ligne JSON ignorée:', jsonStr.substring(0, 100));
        }
      }
    }
    
  } finally {
    // Nettoyage
    try {
      reader.cancel();
    } catch {
      // Ignore les erreurs de cancel
    }
  }

  return finalAnswer;
}

/**
 * Version simplifiée pour tests rapides
 */
export async function testStreamConnection(
  tenant_id: string = "ten_demo", 
  lang: string = "fr"
): Promise<boolean> {
  try {
    let received = false;
    
    await streamAIResponse(
      { 
        tenant_id, 
        lang, 
        message: "Test de connexion" 
      },
      () => { received = true; },
      AbortSignal.timeout(5000) // Timeout 5s
    );
    
    return received;
    
  } catch (error) {
    console.error('[aiStream] Test de connexion échoué:', error);
    return false;
  }
}

/**
 * Utilitaire pour gérer les erreurs côté UI
 */
export function getErrorMessage(error: any): string {
  if (error && typeof error === 'object' && error.type === 'error') {
    const errorEvent = error as ErrorEvent;
    
    switch (errorEvent.code) {
      case "quota_exceeded":
      case "402":
        return "Quota de tokens dépassé. Veuillez patienter ou upgrader votre plan.";
      
      case "unauthorized":
      case "401":
        return "Session expirée. Veuillez vous reconnecter.";
      
      case "invalid_payload":
      case "400":
        return "Données de la requête invalides.";
      
      case "upstream_error":
      case "server_configuration":
      case "500":
        return "Erreur serveur temporaire. Veuillez réessayer.";
      
      case "stream_error":
        return "Erreur de streaming. Connexion interrompue.";
      
      default:
        return errorEvent.message || "Une erreur inattendue s'est produite.";
    }
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return "Erreur inconnue lors de la génération.";
}

/**
 * Helpers pour le debug
 */
export const aiStreamDebug = {
  logConfig: () => {
    console.group('[aiStream] Configuration');
    console.log('Endpoint:', '/api/chat/stream');
    console.log('Mode:', 'SSE (Server-Sent Events)');
    console.log('Encoding:', 'UTF-8');
    console.log('Parser:', 'Tolérant aux coupures');
    console.groupEnd();
  },
  
  testPayload: (tenant_id: string = "ten_demo") => ({
    tenant_id,
    lang: "fr",
    message: "Bonjour, pouvez-vous me donner des conseils sur l'élevage de poulets de chair ?"
  })
};