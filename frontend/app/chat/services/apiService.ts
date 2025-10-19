// app/chat/services/apiService.ts - VERSION CORRIGÉE: Nouvelle architecture conversations

import { getSupabaseClient } from "@/lib/supabase/singleton";
import { secureLog } from "@/lib/utils/secureLogger";

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
  EndEvent,
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
      secureLog.log("[apiService] Session ID already stored");
      return;
    }

    // Ajouter en tête de liste
    const updated = [sessionId, ...existing];

    // Limiter le nombre de sessions
    const limited = updated.slice(0, MAX_SESSIONS);

    // Sauvegarder
    localStorage.setItem(STORAGE_KEY, JSON.stringify(limited));

    secureLog.log("[apiService] Session ID stored", { total: limited.length });
  } catch (error) {
    secureLog.error("[apiService] Session ID storage error", error);
  }
}

// Fonction d'authentification pour le backend métier (conservée)
const getAuthToken = async (): Promise<string | null> => {
  secureLog.log("[apiService] Retrieving auth token...");

  try {
    // Méthode 1: Récupérer depuis intelia-expert-auth (PRIORITÉ)
    const authData = localStorage.getItem("intelia-expert-auth");
    if (authData) {
      const parsed = JSON.parse(authData);
      if (parsed.access_token) {
        secureLog.log("[apiService] Token retrieved from intelia-expert-auth");

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

    secureLog.error("[apiService] No token found");
    return null;
  } catch (error) {
    secureLog.error("[apiService] Token retrieval error", error);
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
    secureLog.warn("Erreur formatage date:", error);
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
    secureLog.warn("Erreur formatage date simple:", error);
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

// ✅ CORRECTION 1: Interface pour le résultat de streaming
interface StreamResult {
  response: string;
  agentMetadata: AgentMetadata;
}

/**
 * FONCTION STREAMING SSE AGENT - VERSION ENRICHIE COMPLÈTE
 * Gère l'appel vers /llm/chat avec support complet des événements Agent
 */
async function streamAIResponseInternal(
  tenant_id: string,
  lang: string,
  message: string,
  conversation_id: string,
  user_context?: any,
  callbacks?: StreamCallbacks,
  abortSignal?: AbortSignal, // ✅ NOUVEAU: Support pour annulation
): Promise<StreamResult> {
  const payload = {
    tenant_id,
    lang,
    message,
    conversation_id,
    user_context,
  };

  secureLog.log("[apiService] Streaming Agent vers /llm/chat:", {
    tenant_id,
    lang,
    message_preview: message.substring(0, 50) + "...",
    has_callbacks: !!callbacks,
    agent_callbacks: !!(callbacks?.onAgentStart || callbacks?.onAgentThinking),
  });

  // Headers SSE complets avec Cache-Control + AbortSignal
  const response = await fetch("/llm/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      "Cache-Control": "no-cache",
    },
    body: JSON.stringify(payload),
    signal: abortSignal, // ✅ NOUVEAU: Propagation du signal d'annulation
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

    secureLog.error("[apiService] Erreur streaming Agent:", errorInfo);
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
        secureLog.log("[apiService] Stream Agent terminé:", {
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
              secureLog.log(`[apiService] Agent démarré: ${agentStartEvent.complexity} sous-requêtes: ${agentStartEvent.sub_queries_count} `);
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
              secureLog.log(`[apiService] Agent réflexion: ${agentThinkingEvent.decisions?.length || 0} décisions `);
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
              secureLog.log(`[apiService] Agent progression: ${agentProgressEvent.step} ${agentProgressEvent.progress + "%"} `);
              callbacks?.onAgentProgress?.(
                agentProgressEvent.step,
                agentProgressEvent.progress,
              );
              break;

            case "agent_end":
              const agentEndEvent = event as AgentEndEvent;
              secureLog.log(`[apiService] Agent terminé: ${agentEndEvent.synthesis_method} sources: ${agentEndEvent.sources_used} `);
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
              secureLog.error(
                "[apiService] Erreur Agent:",
                agentErrorEvent.error,
              );
              callbacks?.onAgentError?.(agentErrorEvent.error);
              break;

            // ✅ CORRECTION 2: Gestion de l'événement "end"
            case "end":
              const endEvent = event as EndEvent;
              secureLog.log("[apiService] Stream terminé (end event):", endEvent);
              // Extraire les métadonnées de fin si disponibles
              if (endEvent.documents_used !== undefined) {
                agentMetadata.sources_used = endEvent.documents_used;
              }
              if (endEvent.confidence !== undefined) {
                // Stocker la confidence finale pour référence
                (agentMetadata as any).final_confidence = endEvent.confidence;
              }
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
                secureLog.log(`[apiService] Relance proactive reçue: ${followupEvent.suggestion} `);
                callbacks?.onFollowup?.(followupEvent.suggestion);
              }
              break;

            case "error":
              const errorEvent = event as ErrorEvent;
              secureLog.error("[apiService] Erreur dans le stream:", errorEvent);
              throw new Error(errorEvent.message || "Erreur de streaming");

            default:
              secureLog.log(`[apiService] Événement SSE non géré: ${(event as any).type} ${event} `);
          }
        } catch (parseError) {
          // Ignore les lignes JSON malformées (chunks partiels)
          secureLog.debug(
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

  // ✅ CORRECTION 3: Retourner un objet au lieu d'essayer d'attacher des propriétés à une string
  return {
    response: finalAnswer,
    agentMetadata: agentMetadata,
  };
}

/**
 * Vérifie le quota de l'utilisateur AVANT d'appeler le LLM
 *
 * @throws Error avec message "QUOTA_EXCEEDED" si le quota est dépassé
 * @returns quota info si OK
 */
export const checkUserQuota = async (): Promise<any> => {
  const headers = await getAuthHeaders();

  try {
    const response = await fetch(`${API_BASE_URL}/usage/check`, {
      method: "GET",
      headers,
    });

    if (!response.ok) {
      // Si erreur serveur, on laisse passer (fail-open) pour ne pas bloquer le service
      secureLog.warn("[apiService] Erreur vérification quota, on laisse passer");
      return { can_ask: true };
    }

    const data = await response.json();

    // Si quota dépassé
    if (data.status === "quota_exceeded") {
      const quotaInfo = data.quota || {};
      const error = new Error("QUOTA_EXCEEDED");
      (error as any).quotaInfo = quotaInfo;
      throw error;
    }

    return data.quota;
  } catch (error: any) {
    // Si c'est notre erreur QUOTA_EXCEEDED, on la re-lance
    if (error.message === "QUOTA_EXCEEDED") {
      throw error;
    }

    // Pour les autres erreurs (réseau, etc.), on laisse passer
    secureLog.warn("[apiService] Erreur vérification quota:", error);
    return { can_ask: true };
  }
};

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
  abortSignal?: AbortSignal, // ✅ NOUVEAU: Support pour annulation
): Promise<EnhancedAIResponse> => {
  if (!question || question.trim() === "") {
    throw new Error("Question requise");
  }

  if (!user || !user.id) {
    throw new Error("Utilisateur requis");
  }

  const finalConversationId = conversationId || generateUUID();

  secureLog.log("[apiService] AGENT: Génération AI avec streaming enrichi:", {
    question: question.substring(0, 50) + "...",
    session_id: finalConversationId.substring(0, 8) + "...",
    user_id: user.id,
    system: "LLM Backend Agent",
    has_agent_callbacks: !!(
      callbacks?.onAgentStart || callbacks?.onAgentThinking
    ),
  });

  try {
    // ✅ Récupération du tenant_id via endpoint backend (pas de Supabase direct)
    let tenant_id = "ten_demo"; // Fallback par défaut

    try {
      // Appel endpoint backend au lieu de Supabase directement
      const authHeaders = await getAuthHeaders();
      const profileResponse = await fetch(`${API_BASE_URL}/users/profile`, {
        method: "GET",
        headers: authHeaders,
      });

      if (!profileResponse.ok) {
        secureLog.warn(
          "[apiService] Erreur récupération profil backend:",
          profileResponse.status,
        );
        tenant_id = `user_${user.id}`;
      } else {
        const profileData = await profileResponse.json();
        secureLog.log("[apiService] Profil reçu du backend:", profileData);

        // Prioriser tenant_id, puis organization_id, sinon user.id
        tenant_id =
          profileData.tenant_id ||
          profileData.organization_id ||
          `user_${user.id}`;

        secureLog.log(`[apiService] tenant_id extrait du backend: ${tenant_id} `);
      }
    } catch (error) {
      secureLog.error(
        "[apiService] Exception récupération tenant_id via backend:",
        error,
      );
      // Fallback: utiliser user.id comme tenant
      tenant_id = `user_${user.id}`;
    }

    // Enrichissement clarification (conservé de l'ancien système)
    let finalQuestion = question.trim();

    if (isClarificationResponse && originalQuestion) {
      secureLog.log("[apiService] Mode clarification - enrichissement question");

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
        secureLog.log("[apiService] Question enrichie:", finalQuestion);
      }
    }

    // ✅ CORRECTION 4: Appel au service de streaming Agent avec gestion correcte du résultat
    const streamResult = await streamAIResponseInternal(
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
      abortSignal, // ✅ NOUVEAU: Propagation du signal d'annulation
    );

    const finalResponse = streamResult.response;
    const agentMetadata = streamResult.agentMetadata;

    secureLog.log("[apiService] Streaming Agent terminé:", {
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
    } catch (saveError: any) {
      secureLog.warn("[apiService] Erreur sauvegarde conversation:", saveError);

      // Propager l'erreur de quota dépassé pour que l'UI puisse l'afficher
      if (saveError.message === "QUOTA_EXCEEDED") {
        throw saveError;
      }

      // Pour les autres erreurs, ne pas faire échouer la réponse
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

    secureLog.log("[apiService] Réponse Agent traitée:", {
      response_length: processedResponse.response.length,
      conversation_id: processedResponse.conversation_id,
      agent_metadata: processedResponse.agent_metadata,
    });

    return processedResponse;
  } catch (error) {
    secureLog.error("[apiService] Erreur génération AI Agent:", error);

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

    secureLog.log("[apiService] Sauvegarde vers nouvelle architecture:", {
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
      // Gérer spécifiquement les quotas dépassés
      if (response_save.status === 429) {
        const errorData = await response_save.json();
        const quotaInfo = errorData.detail?.quota_info || {};
        secureLog.warn("[apiService] Quota dépassé:", quotaInfo);

        const error = new Error("QUOTA_EXCEEDED");
        (error as any).quotaInfo = quotaInfo;
        throw error;
      }

      const errorText = await response_save.text();
      secureLog.error("[apiService] Erreur sauvegarde conversation:", errorText);
      throw new Error(`Erreur sauvegarde: ${response_save.status}`);
    }

    const result = await response_save.json();
    secureLog.log("[apiService] Conversation sauvegardée avec succès:", {
      status: result.status,
      action: result.action,
    });
  } catch (error) {
    secureLog.error("[apiService] Erreur lors de la sauvegarde:", error);
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

  secureLog.log("[apiService] Génération AI publique Agent:", {
    question: question.substring(0, 50) + "...",
    session_id: finalConversationId.substring(0, 8) + "...",
    has_agent_callbacks: !!(
      callbacks?.onAgentStart || callbacks?.onAgentThinking
    ),
  });

  try {
    // ✅ CORRECTION 5: Même correction pour la fonction publique
    const streamResult = await streamAIResponseInternal(
      "ten_public",
      language,
      question.trim(),
      finalConversationId,
      undefined,
      callbacks, // PROPAGATION DES CALLBACKS AGENT
    );

    const finalResponse = streamResult.response;
    const agentMetadata = streamResult.agentMetadata;

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
    secureLog.error("[apiService] Erreur génération AI publique Agent:", error);
    throw error;
  }
};

// ===== FONCTIONS MÉTIER MODIFIÉES POUR NOUVELLE ARCHITECTURE =====

/**
 * ✅ MODIFIÉ: Chargement des conversations utilisateur (nouvelle architecture)
 * CORRECTION: Ajout du paramètre limit pour charger 100 conversations au lieu de 20
 */
export const loadUserConversations = async (
  userId: string,
  limit: number = 999, // ← LIGNE AJOUTÉE: Paramètre limit avec valeur par défaut 999
): Promise<any> => {
  if (!userId) {
    throw new Error("User ID requis");
  }

  // ← LIGNE MODIFIÉE: Ajout du log pour limit
  secureLog.log(`[apiService] Chargement conversations (nouvelle architecture): ${userId}, limit: ${limit}`);

  try {
    const headers = await getAuthHeaders();
    // ✅ LIGNE MODIFIÉE: Ajout de ?limit=${limit} dans l'URL
    const url = `${API_BASE_URL}/conversations/user/${userId}?limit=${limit}`;

    const response = await fetch(url, {
      method: "GET",
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text();
      secureLog.error("[apiService] Erreur conversations:", errorText);

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
    secureLog.log(`[apiService] Conversations chargées (nouvelle architecture): ${{
        total_count: data.total_count,
        conversations_count: data.conversations?.length || 0,
        source: data.source,
      }} `);

    return data;
  } catch (error) {
    secureLog.error("[apiService] Erreur chargement conversations:", error);

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

  secureLog.log("[apiService] Envoi feedback (nouvelle architecture):", feedback);

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
      secureLog.error("[apiService] Erreur feedback:", errorText);

      if (response.status === 401) {
        throw new Error("Session expirée. Veuillez vous reconnecter.");
      }

      throw new Error(`Erreur envoi feedback: ${response.status}`);
    }

    secureLog.log(
      "[apiService] Feedback envoyé avec succès (nouvelle architecture)",
    );
  } catch (error) {
    secureLog.error("[apiService] Erreur feedback:", error);
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

  secureLog.log(`[apiService] Suppression conversation (nouvelle architecture): ${conversationId} `);

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
        secureLog.warn("[apiService] Conversation déjà supprimée ou inexistante");
        return;
      }

      const errorText = await response.text();
      secureLog.error("[apiService] Erreur delete conversation:", errorText);

      if (response.status === 401) {
        throw new Error("Session expirée. Veuillez vous reconnecter.");
      }

      throw new Error(`Erreur suppression conversation: ${response.status}`);
    }

    const result = await response.json();
    secureLog.log(`[apiService] Conversation supprimée (nouvelle architecture): ${result.message || "Succès"} `);
  } catch (error) {
    secureLog.error("[apiService] Erreur suppression conversation:", error);
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

  secureLog.log(`[apiService] Suppression toutes conversations (nouvelle architecture): ${userId} `);

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
      secureLog.error("[apiService] Erreur clear all conversations:", errorText);

      if (response.status === 401) {
        throw new Error("Session expirée. Veuillez vous reconnecter.");
      }

      throw new Error(`Erreur suppression conversations: ${response.status}`);
    }

    const result = await response.json();
    secureLog.log(`[apiService] Toutes conversations supprimées (nouvelle architecture): ${{
        message: result.message,
        deleted_count: result.deleted_count || 0,
      }} `);
  } catch (error) {
    secureLog.error(
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
  secureLog.log("[apiService] Récupération suggestions sujets:", language);

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
      secureLog.warn("[apiService] Erreur récupération sujets:", response.status);

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
    secureLog.log("[apiService] Sujets récupérés:", data.topics?.length || 0);

    return Array.isArray(data.topics) ? data.topics : [];
  } catch (error) {
    secureLog.error("[apiService] Erreur sujets:", error);

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
    secureLog.log(`[apiService] API Health (nouvelle architecture): ${isHealthy ? "OK" : "KO"} `);

    return isHealthy;
  } catch (error) {
    secureLog.error("[apiService] Erreur health check:", error);
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
    secureLog.log("[apiService] LLM Health:", data.status);

    return data;
  } catch (error) {
    secureLog.error("[apiService] Erreur LLM health check:", error);
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
    secureLog.log("[apiService] LLM Diagnostic terminé");

    return data;
  } catch (error) {
    secureLog.error("[apiService] Erreur LLM diagnostic:", error);
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

  secureLog.log("[apiService] Entités construites:", entities);
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

/**
 * NOUVELLE FONCTION: Analyse d'image(s) médicale(s) avec Claude Vision API
 * Flux d'accumulation : Accepte 1 ou plusieurs images pour analyse comparative
 */
export const generateVisionResponse = async (
  imageFiles: File[],
  message: string,
  user: any,
  language: string = "fr",
  conversationId?: string,
): Promise<EnhancedAIResponse> => {
  if (!imageFiles || imageFiles.length === 0) {
    throw new Error("Au moins une image est requise");
  }

  if (!user || !user.id) {
    throw new Error("Utilisateur requis");
  }

  const finalConversationId = conversationId || generateUUID();

  secureLog.log("[apiService] VISION: Analyse d'image(s) médicale(s):", {
    images_count: imageFiles.length,
    images_names: imageFiles.map(f => f.name).join(", "),
    total_size: imageFiles.reduce((sum, f) => sum + f.size, 0),
    message_preview: message.substring(0, 50) + "...",
    session_id: finalConversationId.substring(0, 8) + "...",
    user_id: user.id,
  });

  try {
    // Récupérer tenant_id
    let tenant_id = "ten_demo";

    try {
      const authHeaders = await getAuthHeaders();
      const profileResponse = await fetch(`${API_BASE_URL}/users/profile`, {
        method: "GET",
        headers: authHeaders,
      });

      if (profileResponse.ok) {
        const profileData = await profileResponse.json();
        tenant_id =
          profileData.tenant_id ||
          profileData.organization_id ||
          `user_${user.id}`;
      } else {
        tenant_id = `user_${user.id}`;
      }
    } catch (error) {
      secureLog.warn("[apiService] Erreur récupération tenant_id:", error);
      tenant_id = `user_${user.id}`;
    }

    // Enrichir le message avec l'instruction de langue
    const languageInstruction = language === "fr"
      ? "Répondez en français."
      : "Answer in English.";
    const enrichedMessage = message ? `${message}\n\n${languageInstruction}` : languageInstruction;

    // Créer FormData pour l'upload multipart (support multi-images)
    const formData = new FormData();
    // Ajouter toutes les images avec le même nom de champ "files"
    imageFiles.forEach((image) => {
      formData.append("files", image);
    });
    formData.append("message", enrichedMessage);
    formData.append("tenant_id", tenant_id);
    formData.append("language", language);
    formData.append("use_rag_context", "true");

    secureLog.log(`[apiService] Envoi de ${imageFiles.length} image(s) vers /llm/chat-with-image...`);

    // Appel API Vision
    const response = await fetch("/llm/chat-with-image", {
      method: "POST",
      body: formData, // Pas de Content-Type header - le navigateur le gère automatiquement
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

      secureLog.error("[apiService] Erreur Vision API:", errorInfo);
      throw new Error(errorInfo?.detail || errorInfo?.message || `Erreur ${response.status}`);
    }

    const visionData = await response.json();
    secureLog.log("[apiService] Vision API - Réponse reçue:", {
      success: visionData.success,
      analysis_length: visionData.analysis?.length || 0,
      model: visionData.metadata?.model,
      tokens: visionData.metadata?.usage?.total_tokens,
    });

    if (!visionData.success || !visionData.analysis) {
      throw new Error("Erreur d'analyse d'image");
    }

    const finalResponse = visionData.analysis;

    // Sauvegarder la conversation (avec les images en métadonnées)
    try {
      const headers = await getAuthHeaders();
      const payload = {
        conversation_id: finalConversationId,
        question: message.trim(),
        response: finalResponse,
        user_id: user.id,
        timestamp: new Date().toISOString(),
        source: "llm_vision",
        metadata: {
          mode: "vision",
          backend: "llm_backend_vision",
          images_count: imageFiles.length,
          images_names: imageFiles.map(img => img.name),
          total_size: imageFiles.reduce((sum, img) => sum + img.size, 0),
          model: visionData.metadata?.model,
          tokens: visionData.metadata?.usage,
        },
      };

      const response_save = await fetch(`${API_BASE_URL}/conversations/save`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (response_save.ok) {
        secureLog.log("[apiService] Conversation vision sauvegardée");
      }
    } catch (saveError) {
      secureLog.warn("[apiService] Erreur sauvegarde conversation vision:", saveError);
    }

    // Stocker le session ID
    storeRecentSessionId(finalConversationId);

    // Construire la réponse dans le format attendu
    const processedResponse: EnhancedAIResponse = {
      response: finalResponse,
      conversation_id: finalConversationId,
      language: language,
      timestamp: new Date().toISOString(),
      mode: "streaming",
      source: "llm_backend",
      final_response: finalResponse,

      type: "answer",
      requires_clarification: false,
      rag_used: visionData.metadata?.rag_context_used || false,
      sources: [],
      confidence_score: 0.9,
      note: "Généré via Claude Vision API",
      full_text: finalResponse,

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

    return processedResponse;
  } catch (error) {
    secureLog.error("[apiService] Erreur Vision API:", error);

    if (error instanceof Error) {
      throw error;
    }

    throw new Error("Erreur d'analyse d'image avec Claude Vision");
  }
};

// ===== FONCTIONS UPLOAD PROGRESSIF D'IMAGES =====

/**
 * Upload une image dans le stockage temporaire
 * Retourne image_id pour référence
 */
export const uploadTempImage = async (
  imageFile: File,
  sessionId: string,
): Promise<{
  success: boolean;
  image_id?: string;
  filename?: string;
  size?: number;
  error?: string;
}> => {
  try {
    const formData = new FormData();
    formData.append("file", imageFile);
    formData.append("session_id", sessionId);

    secureLog.log(`[apiService] Upload temp image - Session: ${sessionId}, File: ${imageFile.name}`);

    const response = await fetch("/llm/upload-temp-image", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: "Upload failed" }));
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }

    const data = await response.json();
    secureLog.log(`[apiService] Temp image uploaded - ID: ${data.image_id}`);

    return data;
  } catch (error) {
    secureLog.error("[apiService] Erreur upload temp image:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Upload failed",
    };
  }
};

/**
 * Récupère la liste des images accumulées pour une session
 */
export const getTempImages = async (
  sessionId: string,
): Promise<{
  success: boolean;
  images?: any[];
  count?: number;
  error?: string;
}> => {
  try {
    secureLog.log(`[apiService] Get temp images - Session: ${sessionId}`);

    const response = await fetch(`/llm/temp-images/${sessionId}`, {
      method: "GET",
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    secureLog.log(`[apiService] Temp images retrieved - Count: ${data.count}`);

    return data;
  } catch (error) {
    secureLog.error("[apiService] Erreur get temp images:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to get images",
    };
  }
};

/**
 * Analyse toutes les images accumulées dans une session
 */
export const analyzeSessionImages = async (
  sessionId: string,
  message: string,
  user: any,
  language: string = "fr",
  conversationId?: string,
  cleanupAfter: boolean = true,
): Promise<EnhancedAIResponse> => {
  if (!sessionId) {
    throw new Error("Session ID requis");
  }

  if (!user || !user.id) {
    throw new Error("Utilisateur requis");
  }

  const finalConversationId = conversationId || generateUUID();

  secureLog.log("[apiService] VISION SESSION: Analyse d'images accumulées:", {
    session_id: sessionId,
    message_preview: message.substring(0, 50) + "...",
    conversation_id: finalConversationId.substring(0, 8) + "...",
    user_id: user.id,
  });

  try {
    // Récupérer tenant_id
    let tenant_id = "ten_demo";

    try {
      const authHeaders = await getAuthHeaders();
      const profileResponse = await fetch(`${API_BASE_URL}/users/profile`, {
        method: "GET",
        headers: authHeaders,
      });

      if (profileResponse.ok) {
        const profileData = await profileResponse.json();
        tenant_id =
          profileData.tenant_id ||
          profileData.organization_id ||
          `user_${user.id}`;
      } else {
        tenant_id = `user_${user.id}`;
      }
    } catch (error) {
      secureLog.warn("[apiService] Erreur récupération tenant_id:", error);
      tenant_id = `user_${user.id}`;
    }

    // Enrichir le message avec l'instruction de langue
    const languageInstruction =
      language === "fr" ? "Répondez en français." : "Answer in English.";
    const enrichedMessage = message
      ? `${message}\n\n${languageInstruction}`
      : languageInstruction;

    // Créer FormData pour l'analyse
    const formData = new FormData();
    formData.append("session_id", sessionId);
    formData.append("message", enrichedMessage);
    formData.append("tenant_id", tenant_id);
    formData.append("language", language);
    formData.append("use_rag_context", "true");
    formData.append("cleanup_after", cleanupAfter.toString());

    secureLog.log(`[apiService] Envoi requête analyse session ${sessionId}...`);

    // Appel API Vision Session
    const response = await fetch("/llm/analyze-session-images", {
      method: "POST",
      body: formData,
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

      secureLog.error("[apiService] Erreur Vision Session API:", errorInfo);
      throw new Error(
        errorInfo?.detail || errorInfo?.message || `Erreur ${response.status}`,
      );
    }

    const visionData = await response.json();
    secureLog.log("[apiService] Vision Session API - Réponse reçue:", {
      success: visionData.success,
      analysis_length: visionData.analysis?.length || 0,
      images_count: visionData.metadata?.images_count,
      model: visionData.metadata?.model,
      tokens: visionData.metadata?.usage?.total_tokens,
    });

    if (!visionData.success || !visionData.analysis) {
      throw new Error("Erreur d'analyse d'images de session");
    }

    const finalResponse = visionData.analysis;

    // Sauvegarder la conversation
    try {
      const headers = await getAuthHeaders();
      const payload = {
        conversation_id: finalConversationId,
        question: message.trim(),
        response: finalResponse,
        user_id: user.id,
        timestamp: new Date().toISOString(),
        source: "llm_vision_session",
        metadata: {
          mode: "vision_session",
          backend: "llm_backend_vision",
          session_id: sessionId,
          images_count: visionData.metadata?.images_count,
          model: visionData.metadata?.model,
          tokens: visionData.metadata?.usage,
        },
      };

      const response_save = await fetch(`${API_BASE_URL}/conversations/save`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (response_save.ok) {
        secureLog.log("[apiService] Conversation vision session sauvegardée");
      }
    } catch (saveError) {
      secureLog.warn(
        "[apiService] Erreur sauvegarde conversation vision session:",
        saveError,
      );
    }

    // Stocker le session ID
    storeRecentSessionId(finalConversationId);

    // Construire la réponse
    const processedResponse: EnhancedAIResponse = {
      response: finalResponse,
      conversation_id: finalConversationId,
      language: language,
      timestamp: new Date().toISOString(),
      mode: "streaming",
      source: "llm_backend",
      final_response: finalResponse,

      type: "answer",
      requires_clarification: false,
      rag_used: visionData.metadata?.rag_context_used || false,
      sources: [],
      confidence_score: 0.9,
      note: `Généré via Claude Vision API - ${visionData.metadata?.images_count} image(s)`,
      full_text: finalResponse,

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

    return processedResponse;
  } catch (error) {
    secureLog.error("[apiService] Erreur Vision Session API:", error);

    if (error instanceof Error) {
      throw error;
    }

    throw new Error("Erreur d'analyse d'images de session avec Claude Vision");
  }
};

/**
 * Supprime les images temporaires d'une session
 */
export const deleteTempImages = async (
  sessionId: string,
): Promise<{
  success: boolean;
  deleted_count?: number;
  error?: string;
}> => {
  try {
    secureLog.log(`[apiService] Delete temp images - Session: ${sessionId}`);

    const response = await fetch(`/llm/temp-images/${sessionId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    secureLog.log(
      `[apiService] Temp images deleted - Count: ${data.deleted_count}`,
    );

    return data;
  } catch (error) {
    secureLog.error("[apiService] Erreur delete temp images:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to delete images",
    };
  }
};

// Export par défaut
export default generateAIResponse;