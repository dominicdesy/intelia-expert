// app/chat/services/apiService.ts - VERSION MODIFIÉE: Nouvelle architecture conversations

import { getSupabaseClient } from "@/lib/supabase/singleton";

// Import des nouveaux types Agent depuis index.ts
import type {
  StreamCallbacks,
  AgentMetadata,
  StreamEvent,
  AgentStartEvent,
  AgentThinkingEvent,
  ChunkEvent,
  AgentProgressEvent,
  AgentEndEvent,
  AgentErrorEvent,
  ProactiveFollowupEvent,
  DeltaEvent,
  FinalEvent,
  ErrorEvent,
} from "../../../types";

// Configuration API pour le backend métier (stats, billing, etc.)
const getApiConfig = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const version = process.env.NEXT_PUBLIC_API_VERSION || "v1";

  const cleanBaseUrl = baseUrl?.replace(/\/api\/?$/, "") || "";
  const finalUrl = `${cleanBaseUrl}/api/${version}`;

  return finalUrl;
};

// MODIFICATION: URL API corrigée
const API_BASE_URL = "https://expert.intelia.com/api/v1";

// FIX: Stockage direct des session IDs sans dépendance externe
function storeRecentSessionId(sessionId: string): void {
  try {
    const STORAGE_KEY = "recent_session_ids";
    const MAX_SESSIONS = 50;

    // Récupérer les sessions existantes
    const existing = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");

    // Éviter les doublons
    if (existing.includes(sessionId)) {
      console.log(
        "[apiService] Session ID déjà stocké:",
        sessionId.substring(0, 8) + "...",
      );
      return;
    }

    // Ajouter en tête de liste
    const updated = [sessionId, ...existing];

    // Limiter le nombre de sessions
    const limited = updated.slice(0, MAX_SESSIONS);

    // Sauvegarder
    localStorage.setItem(STORAGE_KEY, JSON.stringify(limited));

    console.log(
      "[apiService] Session ID stocké:",
      sessionId.substring(0, 8) + "...",
      "Total:",
      limited.length,
    );
  } catch (error) {
    console.error("[apiService] Erreur stockage session ID:", error);
  }
}

// Fonction d'authentification pour le backend métier (conservée)
const getAuthToken = async (): Promise<string | null> => {
  console.log("[apiService] Récupération token auth...");

  try {
    // Méthode 1: Récupérer depuis intelia-expert-auth (PRIORITÉ)
    const authData = localStorage.getItem("intelia-expert-auth");
    if (authData) {
      const parsed = JSON.parse(authData);
      if (parsed.access_token) {
        console.log("[apiService] Token récupéré depuis intelia-expert-auth");

        // Vérifier que le token n'est pas expiré
        try {
          const tokenParts = parsed.access_token.split(".");
          if (tokenParts.length === 3) {
            const payload = JSON.parse(atob(tokenParts[1]));
            const now = Math.floor(Date.now() / 1000);
            const isExpired = payload.exp < now;

            if (!isExpired) {
              return parsed.access_token;
            }
          }
        } catch (decodeError) {
          return parsed.access_token;
        }
      }
    }

    // Méthode 2: Fallback vers Supabase store
    const supabaseStore = localStorage.getItem("supabase-auth-store");
    if (supabaseStore) {
      const parsed = JSON.parse(supabaseStore);
      const possibleTokens = [
        parsed.state?.session?.access_token,
        parsed.state?.user?.access_token,
        parsed.access_token,
      ];

      for (const token of possibleTokens) {
        if (token && typeof token === "string" && token.length > 20) {
          return token;
        }
      }
    }

    console.error("[apiService] Aucun token trouvé");
    return null;
  } catch (error) {
    console.error("[apiService] Erreur récupération token:", error);
    return null;
  }
};

// Headers pour les appels au backend métier
const getAuthHeaders = async (): Promise<Record<string, string>> => {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Origin: "https://expert.intelia.com",
  };

  const authToken = await getAuthToken();
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  return headers;
};

// Génération UUID (conservée)
const generateUUID = (): string => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

// Formatage heure locale (conservée)
export const formatToLocalTime = (utcTimestamp: string): string => {
  try {
    const date = new Date(utcTimestamp);
    const options: Intl.DateTimeFormatOptions = {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      hour12: false,
    };
    return date.toLocaleString("fr-CA", options);
  } catch (error) {
    console.warn("Erreur formatage date:", error);
    return utcTimestamp;
  }
};

export const simpleLocalTime = (utcTimestamp: string): string => {
  try {
    return new Date(utcTimestamp).toLocaleString("fr-CA", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch (error) {
    console.warn("Erreur formatage date simple:", error);
    return utcTimestamp;
  }
};

// Interface pour les réponses Agent (adaptée au streaming enrichi)
interface EnhancedAIResponse {
  response: string;
  conversation_id: string;
  language: string;
  timestamp: string;
  mode: "streaming";
  source: "llm_backend";
  final_response: string;

  // Propriétés compatibles avec l'ancien format
  type?: "answer" | "clarification" | "partial_answer" | "validation_rejected";
  requires_clarification?: boolean;
  clarification_questions?: string[];
  clarification_result?: any;
  response_versions?: {
    ultra_concise?: string;
    concise?: string;
    standard?: string;
    detailed?: string;
  };
  full_text?: string;
  rag_used?: boolean;
  sources?: any[];
  confidence_score?: number;
  note?: string;

  // NOUVELLES PROPRIÉTÉS AGENT
  agent_metadata?: AgentMetadata;
}

/**
 * FONCTION STREAMING SSE AGENT - VERSION ENRICHIE COMPLÈTE
 * Gère l'appel vers /api/chat avec support complet des événements Agent
 */
async function streamAIResponseInternal(
  tenant_id: string,
  lang: string,
  message: string,
  conversation_id: string,
  user_context?: any,
  callbacks?: StreamCallbacks,
): Promise<string> {
  const payload = {
    tenant_id,
    lang,
    message,
    conversation_id,
    user_context,
  };

  console.log("[apiService] Streaming Agent vers /api/chat:", {
    tenant_id,
    lang,
    message_preview: message.substring(0, 50) + "...",
    has_callbacks: !!callbacks,
    agent_callbacks: !!(callbacks?.onAgentStart || callbacks?.onAgentThinking),
  });

  // Headers SSE complets avec Cache-Control
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      "Cache-Control": "no-cache",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorInfo: any = null;
    try {
      const text = await response.text();
      errorInfo = JSON.parse(text);
    } catch {
      errorInfo = {
        error: `http_${response.status}`,
        message: `Erreur HTTP ${response.status}`,
      };
    }

    console.error("[apiService] Erreur streaming Agent:", errorInfo);
    throw new Error(errorInfo?.message || `Erreur ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Pas de flux de données reçu");
  }

  // Traitement du flux SSE avec callbacks Agent enrichis
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let finalAnswer = "";
  let buffer = "";

  // Variables de suivi Agent
  let agentMetadata: AgentMetadata = {
    complexity: "simple",
    sub_queries_count: 0,
    synthesis_method: "direct",
    sources_used: 0,
    processing_time: Date.now(),
    decisions: [],
  };

  try {
    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        // Calculer le temps de traitement final
        agentMetadata.processing_time =
          Date.now() - agentMetadata.processing_time;
        console.log("[apiService] Stream Agent terminé:", {
          final_length: finalAnswer.length,
          agent_metadata: agentMetadata,
        });
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Traitement ligne par ligne (format SSE)
      let newlineIndex: number;
      while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 1);

        if (!line || !line.startsWith("data:")) {
          continue;
        }

        const jsonStr = line.slice(5).trim();
        if (!jsonStr || jsonStr === "[DONE]") {
          continue;
        }

        try {
          const event = JSON.parse(jsonStr) as StreamEvent;

          // GESTION COMPLÈTE DES ÉVÉNEMENTS AGENT
          switch (event.type) {
            case "agent_start":
              const agentStartEvent = event as AgentStartEvent;
              console.log(
                "[apiService] Agent démarré:",
                agentStartEvent.complexity,
                "sous-requêtes:",
                agentStartEvent.sub_queries_count,
              );
              agentMetadata.complexity = agentStartEvent.complexity || "simple";
              agentMetadata.sub_queries_count =
                agentStartEvent.sub_queries_count || 0;
              callbacks?.onAgentStart?.(
                agentStartEvent.complexity,
                agentStartEvent.sub_queries_count,
              );
              break;

            case "agent_thinking":
              const agentThinkingEvent = event as AgentThinkingEvent;
              console.log(
                "[apiService] Agent réflexion:",
                agentThinkingEvent.decisions?.length || 0,
                "décisions",
              );
              if (
                agentThinkingEvent.decisions &&
                Array.isArray(agentThinkingEvent.decisions)
              ) {
                agentMetadata.decisions.push(...agentThinkingEvent.decisions);
                callbacks?.onAgentThinking?.(agentThinkingEvent.decisions);
              }
              break;

            case "chunk":
              const chunkEvent = event as ChunkEvent;
              // Nouveau format chunk avec métadonnées
              const chunkContent = chunkEvent.content || "";
              const confidence = chunkEvent.confidence || 0.8;
              const source = chunkEvent.source || "unknown";

              if (chunkContent) {
                finalAnswer += chunkContent;
                callbacks?.onChunk?.(chunkContent, confidence, source);
                // Fallback vers onDelta pour compatibilité
                callbacks?.onDelta?.(chunkContent);
              }
              break;

            case "agent_progress":
              const agentProgressEvent = event as AgentProgressEvent;
              console.log(
                "[apiService] Agent progression:",
                agentProgressEvent.step,
                agentProgressEvent.progress + "%",
              );
              callbacks?.onAgentProgress?.(
                agentProgressEvent.step,
                agentProgressEvent.progress,
              );
              break;

            case "agent_end":
              const agentEndEvent = event as AgentEndEvent;
              console.log(
                "[apiService] Agent terminé:",
                agentEndEvent.synthesis_method,
                "sources:",
                agentEndEvent.sources_used,
              );
              agentMetadata.synthesis_method =
                agentEndEvent.synthesis_method || "direct";
              agentMetadata.sources_used = agentEndEvent.sources_used || 0;
              callbacks?.onAgentEnd?.(
                agentEndEvent.synthesis_method,
                agentEndEvent.sources_used,
              );
              break;

            case "agent_error":
              const agentErrorEvent = event as AgentErrorEvent;
              console.error(
                "[apiService] Erreur Agent:",
                agentErrorEvent.error,
              );
              callbacks?.onAgentError?.(agentErrorEvent.error);
              break;

            // ÉVÉNEMENTS LEGACY MAINTENUS
            case "delta":
              const deltaEvent = event as DeltaEvent;
              if (typeof deltaEvent.text === "string" && deltaEvent.text) {
                finalAnswer += deltaEvent.text;
                callbacks?.onDelta?.(deltaEvent.text);
              }
              break;

            case "final":
              const finalEvent = event as FinalEvent;
              if (finalEvent.answer) {
                finalAnswer = finalEvent.answer;
                callbacks?.onFinal?.(finalAnswer);
              }
              break;

            case "proactive_followup":
              const followupEvent = event as ProactiveFollowupEvent;
              if (followupEvent.suggestion) {
                console.log(
                  "[apiService] Relance proactive reçue:",
                  followupEvent.suggestion,
                );
                callbacks?.onFollowup?.(followupEvent.suggestion);
              }
              break;

            case "error":
              const errorEvent = event as ErrorEvent;
              console.error("[apiService] Erreur dans le stream:", errorEvent);
              throw new Error(errorEvent.message || "Erreur de streaming");

            default:
              console.log(
                "[apiService] Événement SSE non géré:",
                (event as any).type,
                event,
              );
          }
        } catch (parseError) {
          // Ignore les lignes JSON malformées (chunks partiels)
          console.debug(
            "[apiService] Ligne SSE malformée ignorée:",
            jsonStr.substring(0, 100),
          );
        }
      }
    }
  } finally {
    try {
      reader.cancel();
    } catch {
      // Ignore les erreurs de cancel
    }
  }

  // Attacher les métadonnées Agent à la réponse
  (finalAnswer as any).__agentMetadata = agentMetadata;

  return finalAnswer;
}

/**
 * NOUVELLE FONCTION generateAIResponse avec support Agent complet
 * Interface compatible avec l'ancien système + nouvelles capacités Agent
 */
export const generateAIResponse = async (
  question: string,
  user: any,
  language: string = "fr",
  conversationId?: string,
  concisionLevel:
    | "ultra_concise"
    | "concise"
    | "standard"
    | "detailed" = "concise",
  isClarificationResponse = false,
  originalQuestion?: string,
  clarificationEntities?: Record<string, any>,
  callbacks?: StreamCallbacks,
): Promise<EnhancedAIResponse> => {
  if (!question || question.trim() === "") {
    throw new Error("Question requise");
  }

  if (!user || !user.id) {
    throw new Error("Utilisateur requis");
  }

  const finalConversationId = conversationId || generateUUID();

  console.log("[apiService] AGENT: Génération AI avec streaming enrichi:", {
    question: question.substring(0, 50) + "...",
    session_id: finalConversationId.substring(0, 8) + "...",
    user_id: user.id,
    system: "LLM Backend Agent",
    has_agent_callbacks: !!(
      callbacks?.onAgentStart || callbacks?.onAgentThinking
    ),
  });

  try {
    // Récupération du tenant_id depuis le profil utilisateur
    let tenant_id = "ten_demo"; // Fallback

    // TODO: Récupérer le vrai tenant_id depuis Supabase
    // const supabase = getSupabaseClient()
    // const { data: profile } = await supabase
    //   .from('profiles')
    //   .select('tenant_id, organization_id')
    //   .eq('id', user.id)
    //   .single()
    // tenant_id = profile?.tenant_id || profile?.organization_id || 'ten_demo'

    // Enrichissement clarification (conservé de l'ancien système)
    let finalQuestion = question.trim();

    if (isClarificationResponse && originalQuestion) {
      console.log("[apiService] Mode clarification - enrichissement question");

      const breedMatch = finalQuestion.match(
        /(ross\s*308|cobb\s*500|hubbard)/i,
      );
      const sexMatch = finalQuestion.match(
        /(male|mâle|femelle|female|mixte|mixed)/i,
      );

      const breed = breedMatch ? breedMatch[0] : "";
      const sex = sexMatch ? sexMatch[0] : "";

      if (breed && sex) {
        finalQuestion = `${originalQuestion} pour ${breed} ${sex}`;
        console.log("[apiService] Question enrichie:", finalQuestion);
      }
    }

    // Appel au service de streaming Agent avec callbacks enrichis
    const finalResponse = await streamAIResponseInternal(
      tenant_id,
      language,
      finalQuestion,
      finalConversationId,
      {
        user_id: user.id,
        concision_level: concisionLevel,
        ...(clarificationEntities && {
          clarification_entities: clarificationEntities,
        }),
      },
      callbacks, // PROPAGATION DES CALLBACKS AGENT
    );

    // Récupération des métadonnées Agent
    const agentMetadata = (finalResponse as any).__agentMetadata || {
      complexity: "simple",
      sub_queries_count: 0,
      synthesis_method: "direct",
      sources_used: 0,
      processing_time: 0,
      decisions: [],
    };

    console.log("[apiService] Streaming Agent terminé:", {
      final_length: finalResponse.length,
      conversation_id: finalConversationId,
      agent_complexity: agentMetadata.complexity,
      agent_sources: agentMetadata.sources_used,
    });

    // MODIFICATION: Utilisation de la nouvelle structure de sauvegarde
    try {
      await saveConversationToBackend(
        finalConversationId,
        finalQuestion,
        finalResponse,
        user.id,
        agentMetadata,
      );
    } catch (saveError) {
      console.warn("[apiService] Erreur sauvegarde conversation:", saveError);
      // Ne pas faire échouer la réponse pour une erreur de sauvegarde
    }

    // FIX: Stockage du session ID pour l'historique
    storeRecentSessionId(finalConversationId);

    // Construction de la réponse dans le format attendu par l'interface
    const processedResponse: EnhancedAIResponse = {
      response: finalResponse,
      conversation_id: finalConversationId,
      language: language,
      timestamp: new Date().toISOString(),
      mode: "streaming",
      source: "llm_backend",
      final_response: finalResponse,

      // Propriétés compatibles avec l'ancien format
      type: "answer",
      requires_clarification: false,
      rag_used: true,
      sources: [],
      confidence_score: 0.9,
      note: "Généré via streaming LLM Agent",
      full_text: finalResponse,

      // NOUVELLES MÉTADONNÉES AGENT
      agent_metadata: agentMetadata,

      // Génération automatique des versions de réponse
      response_versions: {
        ultra_concise:
          finalResponse.length > 200
            ? finalResponse.substring(0, 150) + "..."
            : finalResponse,
        concise:
          finalResponse.length > 400
            ? finalResponse.substring(0, 300) + "..."
            : finalResponse,
        standard: finalResponse,
        detailed: finalResponse,
      },
    };

    console.log("[apiService] Réponse Agent traitée:", {
      response_length: processedResponse.response.length,
      conversation_id: processedResponse.conversation_id,
      agent_metadata: processedResponse.agent_metadata,
    });

    return processedResponse;
  } catch (error) {
    console.error("[apiService] Erreur génération AI Agent:", error);

    // Gestion des erreurs avec messages appropriés
    if (error instanceof Error) {
      throw error;
    }

    throw new Error("Erreur de génération avec le service LLM Agent");
  }
};

/**
 * MODIFIÉ: Sauvegarde pour nouvelle architecture
 * Utilise le nouvel endpoint /conversations/save
 */
async function saveConversationToBackend(
  conversationId: string,
  question: string,
  response: string,
  userId: string,
  agentMetadata?: AgentMetadata,
): Promise<void> {
  try {
    const headers = await getAuthHeaders();

    const payload = {
      conversation_id: conversationId,
      question: question.trim(),
      response: response,
      user_id: userId,
      timestamp: new Date().toISOString(),
      source: "llm_streaming_agent",
      metadata: {
        mode: "streaming",
        backend: "llm_backend_agent",
        // Support agent_metadata
        ...(agentMetadata && { agent_metadata: agentMetadata }),
      },
    };

    console.log("[apiService] Sauvegarde vers nouvelle architecture:", {
      conversation_id: conversationId.substring(0, 8) + "...",
      user_id: userId,
      question_length: question.length,
      response_length: response.length,
    });

    const response_save = await fetch(`${API_BASE_URL}/conversations/save`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (!response_save.ok) {
      const errorText = await response_save.text();
      console.error("[apiService] Erreur sauvegarde conversation:", errorText);
      throw new Error(`Erreur sauvegarde: ${response_save.status}`);
    }

    const result = await response_save.json();
    console.log("[apiService] Conversation sauvegardée avec succès:", {
      status: result.status,
      action: result.action,
    });
  } catch (error) {
    console.error("[apiService] Erreur lors de la sauvegarde:", error);
    throw error;
  }
}

/**
 * VERSION PUBLIQUE AGENT avec streaming (remplace l'ancienne)
 */
export const generateAIResponsePublic = async (
  question: string,
  language: string = "fr",
  conversationId?: string,
  concisionLevel:
    | "ultra_concise"
    | "concise"
    | "standard"
    | "detailed" = "concise",
  callbacks?: StreamCallbacks,
): Promise<EnhancedAIResponse> => {
  if (!question || question.trim() === "") {
    throw new Error("Question requise");
  }

  const finalConversationId = conversationId || generateUUID();

  console.log("[apiService] Génération AI publique Agent:", {
    question: question.substring(0, 50) + "...",
    session_id: finalConversationId.substring(0, 8) + "...",
    has_agent_callbacks: !!(
      callbacks?.onAgentStart || callbacks?.onAgentThinking
    ),
  });

  try {
    const finalResponse = await streamAIResponseInternal(
      "ten_public",
      language,
      question.trim(),
      finalConversationId,
      undefined,
      callbacks, // PROPAGATION DES CALLBACKS AGENT
    );

    // Récupération des métadonnées Agent
    const agentMetadata = (finalResponse as any).__agentMetadata || {
      complexity: "simple",
      sub_queries_count: 0,
      synthesis_method: "direct",
      sources_used: 0,
      processing_time: 0,
      decisions: [],
    };

    // FIX: Stockage du session ID
    storeRecentSessionId(finalConversationId);

    return {
      response: finalResponse,
      conversation_id: finalConversationId,
      language: language,
      timestamp: new Date().toISOString(),
      mode: "streaming",
      source: "llm_backend",
      final_response: finalResponse,

      type: "answer",
      requires_clarification: false,
      rag_used: true,
      sources: [],
      confidence_score: 0.9,
      note: "Généré via streaming LLM Agent (public)",
      full_text: finalResponse,

      // MÉTADONNÉES AGENT
      agent_metadata: agentMetadata,

      response_versions: {
        ultra_concise:
          finalResponse.length > 200
            ? finalResponse.substring(0, 150) + "..."
            : finalResponse,
        concise:
          finalResponse.length > 400
            ? finalResponse.substring(0, 300) + "..."
            : finalResponse,
        standard: finalResponse,
        detailed: finalResponse,
      },
    };
  } catch (error) {
    console.error("[apiService] Erreur génération AI publique Agent:", error);
    throw error;
  }
};

// ===== FONCTIONS MÉTIER MODIFIÉES POUR NOUVELLE ARCHITECTURE =====

/**
 * MODIFIÉ: Chargement des conversations utilisateur (nouvelle architecture)
 */
export const loadUserConversations = async (userId: string): Promise<any> => {
  if (!userId) {
    throw new Error("User ID requis");
  }

  console.log(
    "[apiService] Chargement conversations (nouvelle architecture):",
    userId,
  );

  try {
    const headers = await getAuthHeaders();
    const url = `${API_BASE_URL}/conversations/user/${userId}`;

    const response = await fetch(url, {
      method: "GET",
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("[apiService] Erreur conversations:", errorText);

      if (response.status === 401) {
        throw new Error("Session expirée. Veuillez vous reconnecter.");
      }

      if (response.status === 404) {
        return {
          status: "success",
          user_id: userId,
          conversations: [],
          total_count: 0,
          message: "Aucune conversation trouvée",
        };
      }

      throw new Error(`Erreur chargement conversations: ${response.status}`);
    }

    const data = await response.json();
    console.log(
      "[apiService] Conversations chargées (nouvelle architecture):",
      {
        total_count: data.total_count,
        conversations_count: data.conversations?.length || 0,
        source: data.source,
      },
    );

    return data;
  } catch (error) {
    console.error("[apiService] Erreur chargement conversations:", error);

    if (error instanceof Error && error.message.includes("Failed to fetch")) {
      return {
        status: "error",
        user_id: userId,
        conversations: [],
        total_count: 0,
        message: "Erreur de connexion - réessayez plus tard",
      };
    }

    throw error;
  }
};

/**
 * MODIFIÉ: Envoi de feedback (nouvelle architecture)
 */
export const sendFeedback = async (
  conversationId: string,
  feedback: 1 | -1,
  comment?: string,
): Promise<void> => {
  if (!conversationId) {
    throw new Error("ID de conversation requis");
  }

  console.log("[apiService] Envoi feedback (nouvelle architecture):", feedback);

  try {
    const headers = await getAuthHeaders();

    // Utiliser l'endpoint de mise à jour des conversations
    const payload = {
      feedback: feedback,
      ...(comment && { feedback_comment: comment.trim() }),
    };

    const response = await fetch(
      `${API_BASE_URL}/conversations/${conversationId}/feedback`,
      {
        method: "PATCH",
        headers,
        body: JSON.stringify(payload),
      },
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error("[apiService] Erreur feedback:", errorText);

      if (response.status === 401) {
        throw new Error("Session expirée. Veuillez vous reconnecter.");
      }

      throw new Error(`Erreur envoi feedback: ${response.status}`);
    }

    console.log(
      "[apiService] Feedback envoyé avec succès (nouvelle architecture)",
    );
  } catch (error) {
    console.error("[apiService] Erreur feedback:", error);
    throw error;
  }
};

/**
 * MODIFIÉ: Suppression de conversation (nouvelle architecture)
 */
export const deleteConversation = async (
  conversationId: string,
): Promise<void> => {
  if (!conversationId) {
    throw new Error("ID de conversation requis");
  }

  console.log(
    "[apiService] Suppression conversation (nouvelle architecture):",
    conversationId,
  );

  try {
    const headers = await getAuthHeaders();

    const response = await fetch(
      `${API_BASE_URL}/conversations/${conversationId}`,
      {
        method: "DELETE",
        headers,
      },
    );

    if (!response.ok) {
      if (response.status === 404) {
        console.warn("[apiService] Conversation déjà supprimée ou inexistante");
        return;
      }

      const errorText = await response.text();
      console.error("[apiService] Erreur delete conversation:", errorText);

      if (response.status === 401) {
        throw new Error("Session expirée. Veuillez vous reconnecter.");
      }

      throw new Error(`Erreur suppression conversation: ${response.status}`);
    }

    const result = await response.json();
    console.log(
      "[apiService] Conversation supprimée (nouvelle architecture):",
      result.message || "Succès",
    );
  } catch (error) {
    console.error("[apiService] Erreur suppression conversation:", error);
    throw error;
  }
};

/**
 * MODIFIÉ: Suppression de toutes les conversations (nouvelle architecture)
 */
export const clearAllUserConversations = async (
  userId: string,
): Promise<void> => {
  if (!userId) {
    throw new Error("User ID requis");
  }

  console.log(
    "[apiService] Suppression toutes conversations (nouvelle architecture):",
    userId,
  );

  try {
    const headers = await getAuthHeaders();

    const response = await fetch(
      `${API_BASE_URL}/conversations/user/${userId}`,
      {
        method: "DELETE",
        headers,
      },
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error("[apiService] Erreur clear all conversations:", errorText);

      if (response.status === 401) {
        throw new Error("Session expirée. Veuillez vous reconnecter.");
      }

      throw new Error(`Erreur suppression conversations: ${response.status}`);
    }

    const result = await response.json();
    console.log(
      "[apiService] Toutes conversations supprimées (nouvelle architecture):",
      {
        message: result.message,
        deleted_count: result.deleted_count || 0,
      },
    );
  } catch (error) {
    console.error(
      "[apiService] Erreur suppression toutes conversations:",
      error,
    );
    throw error;
  }
};

// ===== FONCTIONS UTILITAIRES CONSERVÉES =====

export const getTopicSuggestions = async (
  language: string = "fr",
): Promise<string[]> => {
  console.log("[apiService] Récupération suggestions sujets:", language);

  try {
    const headers = await getAuthHeaders();

    const response = await fetch(
      `${API_BASE_URL}/expert/topics?language=${language}`,
      {
        method: "GET",
        headers,
      },
    );

    if (!response.ok) {
      console.warn("[apiService] Erreur récupération sujets:", response.status);

      return [
        "Problèmes de croissance poulets",
        "Conditions environnementales optimales",
        "Protocoles de vaccination",
        "Diagnostic problèmes de santé",
        "Nutrition et alimentation",
        "Gestion de la mortalité",
      ];
    }

    const data = await response.json();
    console.log("[apiService] Sujets récupérés:", data.topics?.length || 0);

    return Array.isArray(data.topics) ? data.topics : [];
  } catch (error) {
    console.error("[apiService] Erreur sujets:", error);

    return [
      "Problèmes de croissance poulets",
      "Conditions environnementales optimales",
      "Protocoles de vaccination",
      "Diagnostic problèmes de santé",
      "Nutrition et alimentation",
      "Gestion de la mortalité",
    ];
  }
};

export const checkAPIHealth = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${API_BASE_URL}/conversations/health`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Origin: "https://expert.intelia.com",
      },
    });

    const isHealthy = response.ok;
    console.log(
      "[apiService] API Health (nouvelle architecture):",
      isHealthy ? "OK" : "KO",
    );

    return isHealthy;
  } catch (error) {
    console.error("[apiService] Erreur health check:", error);
    return false;
  }
};

export const checkLLMHealth = async (): Promise<any> => {
  try {
    const response = await fetch("/llm/health/complete", {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    console.log("[apiService] LLM Health:", data.status);

    return data;
  } catch (error) {
    console.error("[apiService] Erreur LLM health check:", error);
    return { status: "unhealthy", error: error.message };
  }
};

export const runLLMDiagnostic = async (): Promise<any> => {
  try {
    const response = await fetch("/llm/diagnostic", {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    console.log("[apiService] LLM Diagnostic terminé");

    return data;
  } catch (error) {
    console.error("[apiService] Erreur LLM diagnostic:", error);
    return { success: false, error: error.message };
  }
};

export const buildClarificationEntities = (
  clarificationAnswers: Record<string, string>,
  clarificationQuestions: string[],
): Record<string, any> => {
  const entities: Record<string, any> = {};

  Object.entries(clarificationAnswers).forEach(([index, answer]) => {
    if (answer && answer.trim()) {
      try {
        const questionIndex = parseInt(index);
        if (
          questionIndex >= 0 &&
          questionIndex < clarificationQuestions.length
        ) {
          const question = clarificationQuestions[questionIndex].toLowerCase();

          if (
            question.includes("race") ||
            question.includes("breed") ||
            question.includes("souche")
          ) {
            entities.breed = answer.trim();
          } else if (
            question.includes("sexe") ||
            question.includes("sex") ||
            question.includes("male") ||
            question.includes("femelle")
          ) {
            entities.sex = answer.trim();
          } else if (
            question.includes("age") ||
            question.includes("âge") ||
            question.includes("jour") ||
            question.includes("semaine")
          ) {
            entities.age = answer.trim();
          } else if (
            question.includes("poids") ||
            question.includes("weight")
          ) {
            entities.weight = answer.trim();
          } else if (
            question.includes("temperature") ||
            question.includes("température")
          ) {
            entities.temperature = answer.trim();
          } else if (
            question.includes("nombre") ||
            question.includes("quantite") ||
            question.includes("effectif")
          ) {
            entities.quantity = answer.trim();
          } else {
            entities[`answer_${questionIndex}`] = answer.trim();
          }
        }
      } catch {
        // Ignorer les index invalides
      }
    }
  });

  console.log("[apiService] Entités construites:", entities);
  return entities;
};

export const handleEnhancedNetworkError = (error: any): string => {
  if (error?.message?.includes("Failed to fetch")) {
    return "Problème de connexion. Vérifiez votre connexion internet.";
  }

  if (error?.message?.includes("Session expirée")) {
    return "Votre session a expiré. Veuillez vous reconnecter.";
  }

  if (error?.message?.includes("Accès non autorisé")) {
    return "Vous n'avez pas l'autorisation d'effectuer cette action.";
  }

  return error?.message || "Une erreur inattendue s'est produite.";
};

// Export par défaut
export default generateAIResponse;
