// app/chat/hooks/useChatStream.ts
import { useCallback, useMemo, useRef, useState } from "react";
import {
  streamAIResponse,
  getErrorMessage,
  type ChatStreamBody,
} from "../services/aiStream";

export interface ChatStreamState {
  isStreaming: boolean;
  partial: string;
  error: string | null;
  isConnected: boolean;
}

export interface ChatStreamActions {
  send: (message: string, options?: Partial<ChatStreamBody>) => Promise<string>;
  stop: () => void;
  clearError: () => void;
  reset: () => void;
}

export type UseChatStreamReturn = ChatStreamState & ChatStreamActions;

/**
 * Hook principal pour gérer le streaming AI avec SSE
 * Fournit état et actions pour l'interface de chat
 */
export function useChatStream(
  tenant_id: string,
  lang: string = "fr",
): UseChatStreamReturn {
  // État du streaming
  const [isStreaming, setIsStreaming] = useState(false);
  const [partial, setPartial] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(true);

  // Référence pour l'abort controller
  const abortRef = useRef<AbortController | null>(null);

  // Référence pour éviter les appels multiples
  const processingRef = useRef(false);

  /**
   * Fonction principale pour envoyer un message et streamer la réponse
   */
  const send = useCallback(
    async (
      message: string,
      options: Partial<ChatStreamBody> = {},
    ): Promise<string> => {
      // Éviter les appels multiples simultanés
      if (processingRef.current || isStreaming) {
        console.warn("[useChatStream] Tentative d'envoi multiple ignorée");
        return "";
      }

      // Validation
      if (!message?.trim()) {
        setError("Message vide");
        return "";
      }

      if (!tenant_id) {
        setError("Tenant ID manquant");
        return "";
      }

      // Initialisation
      processingRef.current = true;
      setPartial("");
      setError(null);
      setIsStreaming(true);
      setIsConnected(true);

      // Nouvel AbortController pour ce stream
      abortRef.current = new AbortController();

      const requestBody: ChatStreamBody = {
        tenant_id,
        lang,
        message: message.trim(),
        ...options, // Merge avec les options additionnelles
      };

      console.log("[useChatStream] Démarrage stream:", {
        tenant_id,
        lang,
        message_length: message.length,
        has_options: Object.keys(options).length > 0,
      });

      try {
        const finalResponse = await streamAIResponse(
          requestBody,
          (deltaText: string) => {
            // Callback pour chaque delta reçu
            setPartial((prev) => prev + deltaText);
            setIsConnected(true);
          },
          abortRef.current.signal,
        );

        console.log("[useChatStream] Stream terminé:", {
          final_length: finalResponse.length,
          partial_length: partial.length,
        });

        return finalResponse;
      } catch (streamError: any) {
        console.error("[useChatStream] Erreur stream:", streamError);

        // Gestion spéciale pour l'arrêt volontaire
        if (
          streamError?.name === "AbortError" ||
          abortRef.current?.signal.aborted
        ) {
          console.log("[useChatStream] Stream arrêté par l'utilisateur");
          return partial; // Retourne ce qui a été reçu jusqu'ici
        }

        // Gestion des erreurs réseau/connexion
        if (streamError?.message?.includes("fetch")) {
          setIsConnected(false);
          setError("Problème de connexion. Vérifiez votre réseau.");
        } else {
          setError(getErrorMessage(streamError));
        }

        // En cas d'erreur, retourne le partiel si disponible
        return partial || "";
      } finally {
        // Nettoyage
        setIsStreaming(false);
        processingRef.current = false;
        abortRef.current = null;
      }
    },
    [tenant_id, lang, isStreaming, partial],
  );

  /**
   * Arrête le streaming en cours
   */
  const stop = useCallback(() => {
    if (abortRef.current && !abortRef.current.signal.aborted) {
      console.log("[useChatStream] Arrêt du stream demandé");
      abortRef.current.abort();
    }
  }, []);

  /**
   * Efface l'erreur courante
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Reset complet de l'état
   */
  const reset = useCallback(() => {
    // Arrêter le stream en cours s'il y en a un
    stop();

    // Reset de tous les états
    setPartial("");
    setError(null);
    setIsStreaming(false);
    setIsConnected(true);
    processingRef.current = false;
  }, [stop]);

  // Nettoyage automatique au démontage
  useMemo(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, []);

  // Retour memoïsé pour éviter les re-renders inutiles
  return useMemo(
    () => ({
      // État
      isStreaming,
      partial,
      error,
      isConnected,

      // Actions
      send,
      stop,
      clearError,
      reset,
    }),
    [isStreaming, partial, error, isConnected, send, stop, clearError, reset],
  );
}

/**
 * Hook simplifié pour des cas d'usage basiques
 * Masque la complexité de la gestion d'erreurs
 */
export function useSimpleChatStream(tenant_id: string, lang: string = "fr") {
  const stream = useChatStream(tenant_id, lang);

  return {
    isLoading: stream.isStreaming,
    response: stream.partial,
    sendMessage: stream.send,
    stopGeneration: stream.stop,
    hasError: !!stream.error,
    errorMessage: stream.error,
  };
}

/**
 * Hook pour intégration avec l'état global (ex: Zustand store)
 */
export function useChatStreamWithStore<T>(
  tenant_id: string,
  lang: string,
  store: {
    addMessage: (message: T) => void;
    updateLastMessage: (update: Partial<T>) => void;
    setLoading: (loading: boolean) => void;
  },
  messageFactory: {
    createUserMessage: (content: string) => T;
    createAssistantMessage: (content: string, isPartial?: boolean) => T;
  },
) {
  const stream = useChatStream(tenant_id, lang);

  const sendWithStore = useCallback(
    async (message: string) => {
      // Ajouter le message utilisateur au store
      store.addMessage(messageFactory.createUserMessage(message));

      // Ajouter un message assistant vide qui sera mis à jour
      store.addMessage(messageFactory.createAssistantMessage("", true));
      store.setLoading(true);

      try {
        const finalResponse = await stream.send(message);

        // Mettre à jour avec la réponse finale
        store.updateLastMessage(
          messageFactory.createAssistantMessage(
            finalResponse || stream.partial,
          ),
        );
      } catch (error) {
        // En cas d'erreur, garder le partiel si disponible
        const content = stream.partial || "Erreur lors de la génération.";
        store.updateLastMessage(messageFactory.createAssistantMessage(content));
      } finally {
        store.setLoading(false);
      }
    },
    [stream, store, messageFactory],
  );

  return {
    ...stream,
    sendWithStore,
  };
}

/**
 * Hook pour tester la connexion
 * ✅ CORRECTION: Maintenant c'est un vrai hook React
 */
export function useTestConnection(tenant_id: string, lang: string = "fr") {
  const stream = useChatStream(tenant_id, lang);

  const testConnection = useCallback(async (): Promise<boolean> => {
    console.log("[useChatStream] Test de connexion...");

    try {
      const result = await stream.send("Test");
      console.log("[useChatStream] Test réussi:", result.length, "caractères");
      return true;
    } catch (error) {
      console.error("[useChatStream] Test échoué:", error);
      return false;
    }
  }, [stream]);

  return {
    testConnection,
    isTestingConnection: stream.isStreaming,
    connectionError: stream.error,
  };
}

/**
 * Utilitaires pour le debugging
 */
export const chatStreamDebug = {
  logState: (stream: UseChatStreamReturn) => {
    console.group("[useChatStream] État actuel");
    console.log("isStreaming:", stream.isStreaming);
    console.log("partial length:", stream.partial.length);
    console.log("has error:", !!stream.error);
    console.log("is connected:", stream.isConnected);
    console.groupEnd();
  },

  // ✅ CORRECTION: Fonction non-hook pour les tests simples
  testConnectionSimple: async (
    tenant_id: string,
    lang: string = "fr",
  ): Promise<boolean> => {
    console.log("[useChatStream] Test de connexion simple...");

    try {
      // Utiliser directement streamAIResponse sans hooks
      const result = await streamAIResponse(
        { tenant_id, lang, message: "Test" },
        () => {}, // callback vide
      );
      console.log(
        "[useChatStream] Test simple réussi:",
        result.length,
        "caractères",
      );
      return true;
    } catch (error) {
      console.error("[useChatStream] Test simple échoué:", error);
      return false;
    }
  },
};
