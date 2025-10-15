/**
 * Stockage backend pour l'historique des publicités
 * Synchronise avec la table users.ad_history dans Supabase
 * Fonctionne même en mode navigation privée
 */

import { secureLog } from "./secureLogger";
import { PersistentJSONStorage } from "./persistentStorage";
import { apiClient } from "../api/client";

const AD_HISTORY_KEY = "intelia_ad_history";
const MAX_HISTORY_SIZE = 10;

/**
 * Sauvegarde l'historique des pubs dans le backend (Supabase)
 */
async function saveAdHistoryToBackend(history: string[]): Promise<void> {
  try {
    secureLog.log("[BackendAdStorage] Saving to backend:", history);

    // Utiliser apiClient pour la cohérence des URLs
    const response = await apiClient.putSecure("users/profile", {
      ad_history: history,
    });

    if (response.success) {
      secureLog.log("[BackendAdStorage] Ad history saved to backend:", history);
    } else {
      secureLog.warn("[BackendAdStorage] Backend save failed:", response.error);
    }
  } catch (error) {
    secureLog.warn("[BackendAdStorage] Backend save error:", error);
  }
}

/**
 * Récupère l'historique des pubs depuis le backend (Supabase)
 */
async function loadAdHistoryFromBackend(): Promise<string[] | null> {
  try {
    console.log("[BackendAdStorage] 📡 Loading from backend...");

    // Utiliser apiClient pour la cohérence des URLs
    const response = await apiClient.getSecure<any>("auth/me");

    console.log("[BackendAdStorage] 📡 Response:", response);

    if (response.success && response.data) {
      const history = response.data.ad_history;

      console.log("[BackendAdStorage] 📡 ad_history field:", history);

      if (Array.isArray(history) && history.length > 0) {
        console.log(
          "[BackendAdStorage] ✅ Ad history loaded from backend:",
          history
        );
        return history;
      } else {
        console.log("[BackendAdStorage] ⚠️ No ad_history in user profile");
      }
    } else {
      console.warn("[BackendAdStorage] ❌ Backend load failed:", response.error);
    }

    return null;
  } catch (error) {
    console.error("[BackendAdStorage] ❌ Backend load error:", error);
    return null;
  }
}

/**
 * Classe de stockage spécialisée pour l'historique des publicités
 * Combine stockage local (rapide) et backend (persistant)
 */
export class BackendAdStorage {
  private localStorage: PersistentJSONStorage<string[]>;
  private backendSyncPending: boolean = false;
  private initPromise: Promise<void> | null = null;
  private isInitialized: boolean = false;

  constructor() {
    this.localStorage = new PersistentJSONStorage<string[]>(AD_HISTORY_KEY);
  }

  /**
   * Charge l'historique depuis le backend au démarrage
   * Restaure dans tous les storages locaux
   */
  async init(): Promise<void> {
    // Si déjà initialisé ou en cours, retourner la promesse existante
    if (this.isInitialized) {
      return Promise.resolve();
    }

    if (this.initPromise) {
      return this.initPromise;
    }

    this.initPromise = (async () => {
      try {
        console.log("[BackendAdStorage] 🔄 Initializing...");

        // Charger depuis le backend
        const backendHistory = await loadAdHistoryFromBackend();

        if (backendHistory && backendHistory.length > 0) {
          console.log(
            "[BackendAdStorage] ✅ Restoring from backend:",
            backendHistory
          );

          // Restaurer dans le stockage local
          this.localStorage.set(backendHistory);
        } else {
          console.log("[BackendAdStorage] ⚠️ No backend history found");
        }

        this.isInitialized = true;
        console.log("[BackendAdStorage] ✅ Initialization complete");
      } catch (error) {
        console.error("[BackendAdStorage] ❌ Init error:", error);
        // Marquer comme initialisé quand même pour ne pas bloquer
        this.isInitialized = true;
      }
    })();

    return this.initPromise;
  }

  /**
   * Attend que l'initialisation soit terminée
   */
  async waitForInit(): Promise<void> {
    if (this.isInitialized) {
      return Promise.resolve();
    }

    if (this.initPromise) {
      await this.initPromise;
    }
  }

  /**
   * Récupère l'historique (priorité: local storage)
   */
  get(): string[] {
    const history = this.localStorage.get();
    return history || [];
  }

  /**
   * Ajoute une pub à l'historique
   * Sauvegarde dans le local ET le backend
   */
  addToHistory(adId: string): void {
    try {
      const history = this.get();

      // Ajouter au début
      history.unshift(adId);

      // Garder seulement les N dernières
      const trimmedHistory = history.slice(0, MAX_HISTORY_SIZE);

      // Sauvegarder localement (synchrone, rapide)
      this.localStorage.set(trimmedHistory);

      secureLog.log("[BackendAdStorage] Ad added to history:", adId);

      // Sauvegarder dans le backend (asynchrone, en arrière-plan)
      if (!this.backendSyncPending) {
        this.backendSyncPending = true;

        // Debounce: attendre 2 secondes avant de sauvegarder au backend
        setTimeout(() => {
          this.syncToBackend();
        }, 2000);
      }
    } catch (error) {
      secureLog.error("[BackendAdStorage] Add error:", error);
    }
  }

  /**
   * Synchronise l'historique avec le backend
   */
  private async syncToBackend(): Promise<void> {
    try {
      const history = this.get();
      await saveAdHistoryToBackend(history);
    } catch (error) {
      secureLog.error("[BackendAdStorage] Sync error:", error);
    } finally {
      this.backendSyncPending = false;
    }
  }

  /**
   * Efface l'historique (local ET backend)
   */
  async clear(): Promise<void> {
    try {
      // Effacer localement
      this.localStorage.remove();

      // Effacer dans le backend
      await saveAdHistoryToBackend([]);

      secureLog.log("[BackendAdStorage] History cleared");
    } catch (error) {
      secureLog.error("[BackendAdStorage] Clear error:", error);
    }
  }
}

// Export une instance singleton
export const adStorage = new BackendAdStorage();
