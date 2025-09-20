// app/chat/services/apiService.ts - VERSION AGENT: Streaming LLM + Agent Callbacks
//

import { getSupabaseClient } from '@/lib/supabase/singleton'

// Types enrichis pour les callbacks de streaming Agent
type StreamCallbacks = {
  onDelta?: (text: string) => void;
  onFinal?: (full: string) => void;
  onFollowup?: (msg: string) => void;
  
  // 🆕 NOUVEAUX CALLBACKS AGENT
  onAgentStart?: (complexity: string, subQueriesCount: number) => void;
  onAgentThinking?: (decisions: string[]) => void;
  onChunk?: (content: string, confidence: number, source?: string) => void;
  onAgentEnd?: (synthesisMethod: string, sourcesUsed: number) => void;
  onAgentError?: (error: string) => void;
  onAgentProgress?: (step: string, progress: number) => void;
};

// Configuration API pour le backend métier (stats, billing, etc.)
const getApiConfig = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
  const version = process.env.NEXT_PUBLIC_API_VERSION || 'v1'
  
  const cleanBaseUrl = baseUrl?.replace(/\/api\/?$/, '') || ''
  const finalUrl = `${cleanBaseUrl}/api/${version}`
  
  return finalUrl
}

const API_BASE_URL = getApiConfig()

// 🔧 FIX: Stockage direct des session IDs sans dépendance externe
function storeRecentSessionId(sessionId: string): void {
  try {
    const STORAGE_KEY = 'recent_session_ids';
    const MAX_SESSIONS = 50;
    
    // Récupérer les sessions existantes
    const existing = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    
    // Éviter les doublons
    if (existing.includes(sessionId)) {
      console.log('[apiService] Session ID déjà stocké:', sessionId.substring(0, 8) + '...');
      return;
    }
    
    // Ajouter en tête de liste
    const updated = [sessionId, ...existing];
    
    // Limiter le nombre de sessions
    const limited = updated.slice(0, MAX_SESSIONS);
    
    // Sauvegarder
    localStorage.setItem(STORAGE_KEY, JSON.stringify(limited));
    
    console.log('[apiService] ✅ Session ID stocké:', sessionId.substring(0, 8) + '...', 'Total:', limited.length);
    
  } catch (error) {
    console.error('[apiService] Erreur stockage session ID:', error);
  }
}

// Fonction d'authentification pour le backend métier (conservée)
const getAuthToken = async (): Promise<string | null> => {
  console.log('[apiService] Récupération token auth...');
  
  try {
    // Méthode 1: Récupérer depuis intelia-expert-auth (PRIORITÉ)
    const authData = localStorage.getItem('intelia-expert-auth');
    if (authData) {
      const parsed = JSON.parse(authData);
      if (parsed.access_token) {
        console.log('[apiService] Token récupéré depuis intelia-expert-auth');
        
        // Vérifier que le token n'est pas expiré
        try {
          const tokenParts = parsed.access_token.split('.');
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
    const supabaseStore = localStorage.getItem('supabase-auth-store');
    if (supabaseStore) {
      const parsed = JSON.parse(supabaseStore);
      const possibleTokens = [
        parsed.state?.session?.access_token,
        parsed.state?.user?.access_token,
        parsed.access_token
      ];
      
      for (const token of possibleTokens) {
        if (token && typeof token === 'string' && token.length > 20) {
          return token;
        }
      }
    }
    
    console.error('[apiService] Aucun token trouvé');
    return null;
    
  } catch (error) {
    console.error('[apiService] Erreur récupération token:', error);
    return null;
  }
}

// Headers pour les appels au backend métier
const getAuthHeaders = async (): Promise<Record<string, string>> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Origin': 'https://expert.intelia.com',
  }

  const authToken = await getAuthToken()
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }

  return headers
}

// Génération UUID (conservée)
const generateUUID = (): string => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

// Formatage heure locale (conservée)
export const formatToLocalTime = (utcTimestamp: string): string => {
  try {
    const date = new Date(utcTimestamp);
    const options: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      hour12: false
    };
    return date.toLocaleString('fr-CA', options);
  } catch (error) {
    console.warn('Erreur formatage date:', error);
    return utcTimestamp;
  }
}

export const simpleLocalTime = (utcTimestamp: string): string => {
  try {
    return new Date(utcTimestamp).toLocaleString('fr-CA', {
      year: 'numeric',
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  } catch (error) {
    console.warn('Erreur formatage date simple:', error);
    return utcTimestamp;
  }
}

// Interface pour les réponses Agent (adaptée au streaming enrichi)
interface EnhancedAIResponse {
  response: string
  conversation_id: string
  language: string
  timestamp: string
  mode: 'streaming'
  source: 'llm_backend'
  final_response: string
  
  // Propriétés compatibles avec l'ancien format
  type?: 'answer' | 'clarification' | 'partial_answer' | 'validation_rejected'
  requires_clarification?: boolean
  clarification_questions?: string[]
  clarification_result?: any
  response_versions?: {
    ultra_concise?: string
    concise?: string
    standard?: string
    detailed?: string
  }
  full_text?: string
  rag_used?: boolean
  sources?: any[]
  confidence_score?: number
  note?: string
  
  // 🆕 NOUVELLES PROPRIÉTÉS AGENT
  agent_metadata?: {
    complexity: string
    sub_queries_count: number
    synthesis_method: string
    sources_used: number
    processing_time?: number
    decisions?: string[]
  }
}

/**
 * 🤖 FONCTION STREAMING SSE AGENT - VERSION ENRICHIE
 * Gère l'appel vers /api/chat/stream avec support complet des événements Agent
 */
async function streamAIResponseInternal(
  tenant_id: string,
  lang: string,
  message: string,
  conversation_id: string,
  user_context?: any,
  callbacks?: StreamCallbacks
): Promise<string> {
  
  const payload = {
    tenant_id,
    lang,
    message,
    conversation_id,
    user_context
  };

  console.log('[apiService] 🤖 Streaming Agent vers /api/chat/stream:', {
    tenant_id,
    lang,
    message_preview: message.substring(0, 50) + '...',
    has_callbacks: !!callbacks,
    agent_callbacks: !!(callbacks?.onAgentStart || callbacks?.onAgentThinking)
  });

  // Headers SSE complets avec Cache-Control
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    let errorInfo: any = null;
    try { 
      const text = await response.text();
      errorInfo = JSON.parse(text); 
    } catch { 
      errorInfo = { error: `http_${response.status}`, message: `Erreur HTTP ${response.status}` };
    }
    
    console.error('[apiService] Erreur streaming Agent:', errorInfo);
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
  let agentMetadata = {
    complexity: 'simple',
    sub_queries_count: 0,
    synthesis_method: 'direct',
    sources_used: 0,
    processing_time: Date.now(),
    decisions: [] as string[]
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      
      if (done) {
        // Calculer le temps de traitement final
        agentMetadata.processing_time = Date.now() - agentMetadata.processing_time;
        console.log('[apiService] 🤖 Stream Agent terminé:', {
          final_length: finalAnswer.length,
          agent_metadata: agentMetadata
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
          const event = JSON.parse(jsonStr);
          
          // 🤖 GESTION DES NOUVEAUX ÉVÉNEMENTS AGENT
          switch (event.type) {
            case "agent_start":
              console.log('[apiService] 🤖 Agent démarré:', event.complexity, 'sous-requêtes:', event.sub_queries_count);
              agentMetadata.complexity = event.complexity || 'simple';
              agentMetadata.sub_queries_count = event.sub_queries_count || 0;
              callbacks?.onAgentStart?.(event.complexity, event.sub_queries_count);
              break;
              
            case "agent_thinking":
              console.log('[apiService] 🧠 Agent réflexion:', event.decisions?.length || 0, 'décisions');
              if (event.decisions && Array.isArray(event.decisions)) {
                agentMetadata.decisions.push(...event.decisions);
                callbacks?.onAgentThinking?.(event.decisions);
              }
              break;
              
            case "chunk":
              // Nouveau format chunk avec métadonnées
              const chunkContent = event.content || event.text || '';
              const confidence = event.confidence || 0.8;
              const source = event.source || 'unknown';
              
              if (chunkContent) {
                finalAnswer += chunkContent;
                callbacks?.onChunk?.(chunkContent, confidence, source);
                // Fallback vers onDelta pour compatibilité
                callbacks?.onDelta?.(chunkContent);
              }
              break;
              
            case "agent_progress":
              console.log('[apiService] 📊 Agent progression:', event.step, event.progress + '%');
              callbacks?.onAgentProgress?.(event.step, event.progress);
              break;
              
            case "agent_end":
              console.log('[apiService] 🏁 Agent terminé:', event.synthesis_method, 'sources:', event.sources_used);
              agentMetadata.synthesis_method = event.synthesis_method || 'direct';
              agentMetadata.sources_used = event.sources_used || 0;
              callbacks?.onAgentEnd?.(event.synthesis_method, event.sources_used);
              break;
              
            case "agent_error":
              console.error('[apiService] ❌ Erreur Agent:', event.error);
              callbacks?.onAgentError?.(event.error);
              break;
              
            // 📦 ÉVÉNEMENTS LEGACY MAINTENUS
            case "delta":
              if (typeof event.text === "string" && event.text) {
                finalAnswer += event.text;
                callbacks?.onDelta?.(event.text);
              }
              break;
              
            case "final":
              if (event.answer) {
                finalAnswer = event.answer;
                callbacks?.onFinal?.(finalAnswer);
              }
              break;
              
            case "proactive_followup":
              if (event.answer) {
                console.log('[apiService] 🔄 Relance proactive reçue:', event.answer);
                callbacks?.onFollowup?.(event.answer);
              }
              break;
              
            case "error":
              console.error('[apiService] ❌ Erreur dans le stream:', event);
              throw new Error(event.message || 'Erreur de streaming');
              
            default:
              console.log('[apiService] 📡 Événement SSE non géré:', event.type, event);
          }
          
        } catch (parseError) {
          // Ignore les lignes JSON malformées (chunks partiels)
          console.debug('[apiService] Ligne SSE malformée ignorée:', jsonStr.substring(0, 100));
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
 * 🤖 NOUVELLE FONCTION generateAIResponse avec support Agent complet
 * Interface compatible avec l'ancien système + nouvelles capacités Agent
 */
export const generateAIResponse = async (
  question: string,
  user: any,
  language: string = 'fr',
  conversationId?: string,
  concisionLevel: 'ultra_concise' | 'concise' | 'standard' | 'detailed' = 'concise',
  isClarificationResponse = false,
  originalQuestion?: string,
  clarificationEntities?: Record<string, any>,
  callbacks?: StreamCallbacks
): Promise<EnhancedAIResponse> => {
  
  if (!question || question.trim() === '') {
    throw new Error('Question requise')
  }

  if (!user || !user.id) {
    throw new Error('Utilisateur requis')
  }

  const finalConversationId = conversationId || generateUUID()

  console.log('[apiService] 🤖 AGENT: Génération AI avec streaming enrichi:', {
    question: question.substring(0, 50) + '...',
    session_id: finalConversationId.substring(0, 8) + '...',
    user_id: user.id,
    system: 'LLM Backend Agent',
    has_agent_callbacks: !!(callbacks?.onAgentStart || callbacks?.onAgentThinking)
  })

  try {
    // Récupération du tenant_id depuis le profil utilisateur
    let tenant_id = 'ten_demo'; // Fallback
    
    // TODO: Récupérer le vrai tenant_id depuis Supabase
    // const supabase = getSupabaseClient()
    // const { data: profile } = await supabase
    //   .from('profiles')
    //   .select('tenant_id, organization_id')
    //   .eq('id', user.id)
    //   .single()
    // tenant_id = profile?.tenant_id || profile?.organization_id || 'ten_demo'

    // Enrichissement clarification (conservé de l'ancien système)
    let finalQuestion = question.trim()
    
    if (isClarificationResponse && originalQuestion) {
      console.log('[apiService] Mode clarification - enrichissement question')
      
      const breedMatch = finalQuestion.match(/(ross\s*308|cobb\s*500|hubbard)/i)
      const sexMatch = finalQuestion.match(/(male|mâle|femelle|female|mixte|mixed)/i)
      
      const breed = breedMatch ? breedMatch[0] : ''
      const sex = sexMatch ? sexMatch[0] : ''
      
      if (breed && sex) {
        finalQuestion = `${originalQuestion} pour ${breed} ${sex}`
        console.log('[apiService] Question enrichie:', finalQuestion)
      }
    }

    // 🤖 Appel au service de streaming Agent avec callbacks enrichis
    const finalResponse = await streamAIResponseInternal(
      tenant_id,
      language,
      finalQuestion,
      finalConversationId,
      {
        user_id: user.id,
        concision_level: concisionLevel,
        ...(clarificationEntities && { clarification_entities: clarificationEntities })
      },
      callbacks  // <<< PROPAGATION DES CALLBACKS AGENT
    );

    // Récupération des métadonnées Agent
    const agentMetadata = (finalResponse as any).__agentMetadata || {
      complexity: 'simple',
      sub_queries_count: 0,
      synthesis_method: 'direct',
      sources_used: 0,
      processing_time: 0,
      decisions: []
    };

    console.log('[apiService] 🤖 Streaming Agent terminé:', {
      final_length: finalResponse.length,
      conversation_id: finalConversationId,
      agent_complexity: agentMetadata.complexity,
      agent_sources: agentMetadata.sources_used
    })

    // Enregistrement de la conversation via le backend métier
    try {
      await saveConversationToBackend(finalConversationId, finalQuestion, finalResponse, user.id)
    } catch (saveError) {
      console.warn('[apiService] Erreur sauvegarde conversation:', saveError)
      // Ne pas faire échouer la réponse pour une erreur de sauvegarde
    }

    // 🔧 FIX: Stockage du session ID pour l'historique
    storeRecentSessionId(finalConversationId)

    // Construction de la réponse dans le format attendu par l'interface
    const processedResponse: EnhancedAIResponse = {
      response: finalResponse,
      conversation_id: finalConversationId,
      language: language,
      timestamp: new Date().toISOString(),
      mode: 'streaming',
      source: 'llm_backend',
      final_response: finalResponse,
      
      // Propriétés compatibles avec l'ancien format
      type: 'answer',
      requires_clarification: false,
      rag_used: true,
      sources: [],
      confidence_score: 0.9,
      note: 'Généré via streaming LLM Agent',
      full_text: finalResponse,
      
      // 🤖 NOUVELLES MÉTADONNÉES AGENT
      agent_metadata: agentMetadata,
      
      // Génération automatique des versions de réponse
      response_versions: {
        ultra_concise: finalResponse.length > 200 ? 
          finalResponse.substring(0, 150) + '...' : finalResponse,
        concise: finalResponse.length > 400 ? 
          finalResponse.substring(0, 300) + '...' : finalResponse,
        standard: finalResponse,
        detailed: finalResponse
      }
    }

    console.log('[apiService] 🤖 Réponse Agent traitée:', {
      response_length: processedResponse.response.length,
      conversation_id: processedResponse.conversation_id,
      agent_metadata: processedResponse.agent_metadata
    })

    return processedResponse

  } catch (error) {
    console.error('[apiService] Erreur génération AI Agent:', error)
    
    // Gestion des erreurs avec messages appropriés
    if (error instanceof Error) {
      throw error
    }
    
    throw new Error('Erreur de génération avec le service LLM Agent')
  }
}

/**
 * Sauvegarde de la conversation via le backend métier
 * Utilise l'ancien endpoint pour maintenir la compatibilité des stats/billing
 */
async function saveConversationToBackend(
  conversationId: string,
  question: string,
  response: string,
  userId: string
): Promise<void> {
  
  try {
    const headers = await getAuthHeaders()
    
    const payload = {
      conversation_id: conversationId,
      question: question.trim(),
      response: response,
      user_id: userId,
      timestamp: new Date().toISOString(),
      source: 'llm_streaming_agent',
      metadata: {
        mode: 'streaming',
        backend: 'llm_backend_agent'
      }
    }

    const response_save = await fetch(`${API_BASE_URL}/conversations/save`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    })

    if (!response_save.ok) {
      const errorText = await response_save.text()
      console.error('[apiService] Erreur sauvegarde conversation:', errorText)
      throw new Error(`Erreur sauvegarde: ${response_save.status}`)
    }

    console.log('[apiService] Conversation sauvegardée avec succès')

  } catch (error) {
    console.error('[apiService] Erreur lors de la sauvegarde:', error)
    throw error
  }
}

/**
 * 🤖 VERSION PUBLIQUE AGENT avec streaming (remplace l'ancienne)
 */
export const generateAIResponsePublic = async (
  question: string,
  language: string = 'fr',
  conversationId?: string,
  concisionLevel: 'ultra_concise' | 'concise' | 'standard' | 'detailed' = 'concise',
  callbacks?: StreamCallbacks
): Promise<EnhancedAIResponse> => {
  
  if (!question || question.trim() === '') {
    throw new Error('Question requise')
  }

  const finalConversationId = conversationId || generateUUID()

  console.log('[apiService] 🤖 Génération AI publique Agent:', {
    question: question.substring(0, 50) + '...',
    session_id: finalConversationId.substring(0, 8) + '...',
    has_agent_callbacks: !!(callbacks?.onAgentStart || callbacks?.onAgentThinking)
  })

  try {
    const finalResponse = await streamAIResponseInternal(
      'ten_public',
      language,
      question.trim(),
      finalConversationId,
      undefined,
      callbacks  // <<< PROPAGATION DES CALLBACKS AGENT
    );

    // Récupération des métadonnées Agent
    const agentMetadata = (finalResponse as any).__agentMetadata || {
      complexity: 'simple',
      sub_queries_count: 0,
      synthesis_method: 'direct',
      sources_used: 0,
      processing_time: 0,
      decisions: []
    };

    // 🔧 FIX: Stockage du session ID
    storeRecentSessionId(finalConversationId)

    return {
      response: finalResponse,
      conversation_id: finalConversationId,
      language: language,
      timestamp: new Date().toISOString(),
      mode: 'streaming',
      source: 'llm_backend',
      final_response: finalResponse,
      
      type: 'answer',
      requires_clarification: false,
      rag_used: true,
      sources: [],
      confidence_score: 0.9,
      note: 'Généré via streaming LLM Agent (public)',
      full_text: finalResponse,
      
      // 🤖 MÉTADONNÉES AGENT
      agent_metadata: agentMetadata,
      
      response_versions: {
        ultra_concise: finalResponse.length > 200 ? 
          finalResponse.substring(0, 150) + '...' : finalResponse,
        concise: finalResponse.length > 400 ? 
          finalResponse.substring(0, 300) + '...' : finalResponse,
        standard: finalResponse,
        detailed: finalResponse
      }
    }

  } catch (error) {
    console.error('[apiService] Erreur génération AI publique Agent:', error)
    throw error
  }
}

// ===== FONCTIONS MÉTIER CONSERVÉES INTÉGRALEMENT (backend Digital Ocean) =====

/**
 * Chargement des conversations utilisateur (backend métier)
 */
export const loadUserConversations = async (userId: string): Promise<any> => {
  if (!userId) {
    throw new Error('User ID requis')
  }

  console.log('[apiService] Chargement conversations:', userId)

  try {
    const headers = await getAuthHeaders()
    const url = `${API_BASE_URL}/conversations/user/${userId}`

    const response = await fetch(url, {
      method: 'GET',
      headers
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[apiService] Erreur conversations:', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expirée. Veuillez vous reconnecter.')
      }
      
      if (response.status === 405 || response.status === 404) {
        return {
          count: 0,
          conversations: [],
          user_id: userId,
          note: "Fonctionnalité en cours de développement"
        }
      }
      
      throw new Error(`Erreur chargement conversations: ${response.status}`)
    }

    const data = await response.json()
    console.log('[apiService] Conversations chargées:', {
      count: data.count,
      conversations: data.conversations?.length || 0
    })

    return data

  } catch (error) {
    console.error('[apiService] Erreur chargement conversations:', error)
    
    if (error instanceof Error && error.message.includes('Failed to fetch')) {
      return {
        count: 0,
        conversations: [],
        user_id: userId,
        note: "Erreur de connexion - réessayez plus tard"
      }
    }
    
    throw error
  }
}

/**
 * ENVOI DE FEEDBACK (backend métier)
 */
export const sendFeedback = async (
  conversationId: string,
  feedback: 1 | -1,
  comment?: string
): Promise<void> => {
  if (!conversationId) {
    throw new Error('ID de conversation requis')
  }

  console.log('[apiService] Envoi feedback:', feedback)

  try {
    const requestBody = {
      conversation_id: conversationId,
      rating: feedback === 1 ? 'positive' : 'negative',
      ...(comment && { comment: comment.trim() })
    }

    const headers = await getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/expert/feedback`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody)
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[apiService] Erreur feedback:', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expirée. Veuillez vous reconnecter.')
      }
      
      throw new Error(`Erreur envoi feedback: ${response.status}`)
    }

    console.log('[apiService] Feedback envoyé avec succès')

  } catch (error) {
    console.error('[apiService] Erreur feedback:', error)
    throw error
  }
}

/**
 * SUPPRESSION DE CONVERSATION (backend métier)
 */
export const deleteConversation = async (conversationId: string): Promise<void> => {
  if (!conversationId) {
    throw new Error('ID de conversation requis')
  }

  console.log('[apiService] Suppression conversation:', conversationId)

  try {
    const headers = await getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}`, {
      method: 'DELETE',
      headers
    })

    if (!response.ok) {
      if (response.status === 404) {
        console.warn('[apiService] Conversation déjà supprimée ou inexistante')
        return
      }
      
      const errorText = await response.text()
      console.error('[apiService] Erreur delete conversation:', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expirée. Veuillez vous reconnecter.')
      }
      
      throw new Error(`Erreur suppression conversation: ${response.status}`)
    }

    const result = await response.json()
    console.log('[apiService] Conversation supprimée:', result.message || 'Succès')

  } catch (error) {
    console.error('[apiService] Erreur suppression conversation:', error)
    throw error
  }
}

/**
 * SUPPRESSION DE TOUTES LES CONVERSATIONS (backend métier)
 */
export const clearAllUserConversations = async (userId: string): Promise<void> => {
  if (!userId) {
    throw new Error('User ID requis')
  }

  console.log('[apiService] Suppression toutes conversations:', userId)

  try {
    const headers = await getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/conversations/user/${userId}`, {
      method: 'DELETE',
      headers
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('[apiService] Erreur clear all conversations:', errorText)
      
      if (response.status === 401) {
        throw new Error('Session expirée. Veuillez vous reconnecter.')
      }
      
      throw new Error(`Erreur suppression conversations: ${response.status}`)
    }

    const result = await response.json()
    console.log('[apiService] Toutes conversations supprimées:', {
      message: result.message,
      deleted_count: result.deleted_count || 0
    })

  } catch (error) {
    console.error('[apiService] Erreur suppression toutes conversations:', error)
    throw error
  }
}

/**
 * SUGGESTIONS DE SUJETS (backend métier)
 */
export const getTopicSuggestions = async (language: string = 'fr'): Promise<string[]> => {
  console.log('[apiService] Récupération suggestions sujets:', language)

  try {
    const headers = await getAuthHeaders()

    const response = await fetch(`${API_BASE_URL}/expert/topics?language=${language}`, {
      method: 'GET',
      headers
    })

    if (!response.ok) {
      console.warn('[apiService] Erreur récupération sujets:', response.status)
      
      return [
        "Problèmes de croissance poulets",
        "Conditions environnementales optimales",
        "Protocoles de vaccination",
        "Diagnostic problèmes de santé",
        "Nutrition et alimentation",
        "Gestion de la mortalité"
      ]
    }

    const data = await response.json()
    console.log('[apiService] Sujets récupérés:', data.topics?.length || 0)

    return Array.isArray(data.topics) ? data.topics : []

  } catch (error) {
    console.error('[apiService] Erreur sujets:', error)
    
    return [
      "Problèmes de croissance poulets",
      "Conditions environnementales optimales", 
      "Protocoles de vaccination",
      "Diagnostic problèmes de santé",
      "Nutrition et alimentation",
      "Gestion de la mortalité"
    ]
  }
}

/**
 * HEALTH CHECK (backend métier)
 */
export const checkAPIHealth = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${API_BASE_URL}/system/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Origin': 'https://expert.intelia.com'
      }
    })

    const isHealthy = response.ok
    console.log('[apiService] API Health:', isHealthy ? 'OK' : 'KO')
    
    return isHealthy

  } catch (error) {
    console.error('[apiService] Erreur health check:', error)
    return false
  }
}

// ===== FONCTIONS UTILITAIRES CONSERVÉES =====

export const buildClarificationEntities = (
  clarificationAnswers: Record<string, string>,
  clarificationQuestions: string[]
): Record<string, any> => {
  const entities: Record<string, any> = {}
  
  Object.entries(clarificationAnswers).forEach(([index, answer]) => {
    if (answer && answer.trim()) {
      try {
        const questionIndex = parseInt(index)
        if (questionIndex >= 0 && questionIndex < clarificationQuestions.length) {
          const question = clarificationQuestions[questionIndex].toLowerCase()
          
          if (question.includes('race') || question.includes('breed') || question.includes('souche')) {
            entities.breed = answer.trim()
          } else if (question.includes('sexe') || question.includes('sex') || question.includes('male') || question.includes('femelle')) {
            entities.sex = answer.trim()
          } else if (question.includes('age') || question.includes('âge') || question.includes('jour') || question.includes('semaine')) {
            entities.age = answer.trim()
          } else if (question.includes('poids') || question.includes('weight')) {
            entities.weight = answer.trim()
          } else if (question.includes('temperature') || question.includes('température')) {
            entities.temperature = answer.trim()
          } else if (question.includes('nombre') || question.includes('quantite') || question.includes('effectif')) {
            entities.quantity = answer.trim()
          } else {
            entities[`answer_${questionIndex}`] = answer.trim()
          }
        }
      } catch {
        // Ignorer les index invalides
      }
    }
  })
  
  console.log('[apiService] Entités construites:', entities)
  return entities
}

export const handleEnhancedNetworkError = (error: any): string => {
  if (error?.message?.includes('Failed to fetch')) {
    return 'Problème de connexion. Vérifiez votre connexion internet.'
  }
  
  if (error?.message?.includes('Session expirée')) {
    return 'Votre session a expiré. Veuillez vous reconnecter.'
  }
  
  if (error?.message?.includes('Accès non autorisé')) {
    return 'Vous n\'avez pas l\'autorisation d\'effectuer cette action.'
  }
  
  return error?.message || 'Une erreur inattendue s\'est produite.'
}

// Export par défaut
export default generateAIResponse