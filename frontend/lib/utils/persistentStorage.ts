/**
 * Système de stockage persistant multi-méthodes
 * Essaie plusieurs méthodes pour garantir la persistance même si localStorage est effacé
 *
 * Ordre de priorité:
 * 1. Backend (Supabase users table) - ULTIMATE persistence, survit à navigation privée
 * 2. IndexedDB (très persistant - mais effacé en mode privé)
 * 3. Cookie (persistant - 365 jours, mais effacé en mode privé)
 * 4. localStorage (rapide mais effacé en mode privé)
 * 5. sessionStorage (fallback temporaire)
 */

import { secureLog } from "./secureLogger";

const COOKIE_EXPIRY_DAYS = 365; // 1 an
const INDEXEDDB_NAME = "InteliaStorage";
const INDEXEDDB_STORE = "KeyValueStore";
const INDEXEDDB_VERSION = 1;

/**
 * Initialise IndexedDB (appelé une seule fois)
 */
let indexedDBPromise: Promise<IDBDatabase> | null = null;

function initIndexedDB(): Promise<IDBDatabase> {
  if (indexedDBPromise) {
    return indexedDBPromise;
  }

  indexedDBPromise = new Promise((resolve, reject) => {
    if (typeof window === "undefined" || !window.indexedDB) {
      reject(new Error("IndexedDB not available"));
      return;
    }

    const request = indexedDB.open(INDEXEDDB_NAME, INDEXEDDB_VERSION);

    request.onerror = () => {
      secureLog.error("[IndexedDB] Error opening database:", request.error);
      reject(request.error);
    };

    request.onsuccess = () => {
      secureLog.log("[IndexedDB] Database opened successfully");
      resolve(request.result);
    };

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;

      // Créer le store si il n'existe pas
      if (!db.objectStoreNames.contains(INDEXEDDB_STORE)) {
        db.createObjectStore(INDEXEDDB_STORE);
        secureLog.log("[IndexedDB] Object store created");
      }
    };
  });

  return indexedDBPromise;
}

/**
 * Écrit dans IndexedDB
 */
async function setIndexedDB(key: string, value: string): Promise<void> {
  try {
    const db = await initIndexedDB();
    const transaction = db.transaction([INDEXEDDB_STORE], "readwrite");
    const store = transaction.objectStore(INDEXEDDB_STORE);

    store.put(value, key);

    await new Promise<void>((resolve, reject) => {
      transaction.oncomplete = () => {
        secureLog.log(`[IndexedDB] Saved: ${key}`);
        resolve();
      };
      transaction.onerror = () => {
        secureLog.error(`[IndexedDB] Save error:`, transaction.error);
        reject(transaction.error);
      };
    });
  } catch (error) {
    secureLog.warn(`[IndexedDB] Save failed:`, error);
  }
}

/**
 * Lit depuis IndexedDB
 */
async function getIndexedDB(key: string): Promise<string | null> {
  try {
    const db = await initIndexedDB();
    const transaction = db.transaction([INDEXEDDB_STORE], "readonly");
    const store = transaction.objectStore(INDEXEDDB_STORE);
    const request = store.get(key);

    return new Promise((resolve, reject) => {
      request.onsuccess = () => {
        const value = request.result;
        if (value) {
          secureLog.log(`[IndexedDB] Retrieved: ${key}`);
          resolve(value);
        } else {
          resolve(null);
        }
      };
      request.onerror = () => {
        secureLog.error(`[IndexedDB] Get error:`, request.error);
        reject(request.error);
      };
    });
  } catch (error) {
    secureLog.warn(`[IndexedDB] Get failed:`, error);
    return null;
  }
}

/**
 * Supprime de IndexedDB
 */
async function deleteIndexedDB(key: string): Promise<void> {
  try {
    const db = await initIndexedDB();
    const transaction = db.transaction([INDEXEDDB_STORE], "readwrite");
    const store = transaction.objectStore(INDEXEDDB_STORE);

    store.delete(key);

    await new Promise<void>((resolve, reject) => {
      transaction.oncomplete = () => {
        secureLog.log(`[IndexedDB] Deleted: ${key}`);
        resolve();
      };
      transaction.onerror = () => {
        secureLog.error(`[IndexedDB] Delete error:`, transaction.error);
        reject(transaction.error);
      };
    });
  } catch (error) {
    secureLog.warn(`[IndexedDB] Delete failed:`, error);
  }
}

/**
 * Écrit dans un cookie persistant
 */
function setCookie(name: string, value: string, days: number = COOKIE_EXPIRY_DAYS): void {
  try {
    const date = new Date();
    date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
    const expires = `expires=${date.toUTCString()}`;

    // SameSite=Lax pour la sécurité, Secure en production
    const secure = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `${name}=${encodeURIComponent(value)}; ${expires}; path=/; SameSite=Lax${secure}`;

    secureLog.log(`[PersistentStorage] Cookie set: ${name}`);
  } catch (error) {
    secureLog.error(`[PersistentStorage] Cookie set error:`, error);
  }
}

/**
 * Lit depuis un cookie
 */
function getCookie(name: string): string | null {
  try {
    const nameEQ = `${name}=`;
    const cookies = document.cookie.split(';');

    for (let cookie of cookies) {
      let c = cookie.trim();
      if (c.indexOf(nameEQ) === 0) {
        const value = c.substring(nameEQ.length);
        return decodeURIComponent(value);
      }
    }
    return null;
  } catch (error) {
    secureLog.error(`[PersistentStorage] Cookie get error:`, error);
    return null;
  }
}

/**
 * Supprime un cookie
 */
function deleteCookie(name: string): void {
  try {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    secureLog.log(`[PersistentStorage] Cookie deleted: ${name}`);
  } catch (error) {
    secureLog.error(`[PersistentStorage] Cookie delete error:`, error);
  }
}

/**
 * Classe de stockage persistant multi-méthodes
 */
export class PersistentStorage {
  private key: string;

  constructor(key: string) {
    this.key = key;
  }

  /**
   * Sauvegarde une valeur avec toutes les méthodes disponibles
   */
  set(value: string): void {
    secureLog.log(`[PersistentStorage] Saving ${this.key}:`, value);

    // Méthode 1: IndexedDB (priorité absolue - survit à tout)
    setIndexedDB(this.key, value).catch((error) => {
      secureLog.warn(`[PersistentStorage] IndexedDB save failed:`, error);
    });

    // Méthode 2: Cookie (très persistant - 365 jours)
    setCookie(this.key, value);

    // Méthode 3: localStorage (rapide, mais peut être effacé)
    try {
      localStorage.setItem(this.key, value);
      secureLog.log(`[PersistentStorage] localStorage saved: ${this.key}`);
    } catch (error) {
      secureLog.warn(`[PersistentStorage] localStorage save failed:`, error);
    }

    // Méthode 4: sessionStorage (fallback temporaire)
    try {
      sessionStorage.setItem(this.key, value);
      secureLog.log(`[PersistentStorage] sessionStorage saved: ${this.key}`);
    } catch (error) {
      secureLog.warn(`[PersistentStorage] sessionStorage save failed:`, error);
    }
  }

  /**
   * Récupère une valeur en essayant toutes les méthodes
   * Priorité: IndexedDB > Cookie > localStorage > sessionStorage
   *
   * NOTE: Cette méthode retourne null en premier, puis la valeur IndexedDB
   * arrivera de manière asynchrone. Pour une lecture synchrone immédiate,
   * on utilise les autres méthodes (cookie, localStorage, sessionStorage).
   */
  get(): string | null {
    // Méthode 1: Cookie (lecture synchrone la plus fiable)
    const cookieValue = getCookie(this.key);
    if (cookieValue) {
      secureLog.log(`[PersistentStorage] Retrieved from cookie: ${this.key}`);

      // Synchroniser avec les autres storages
      try {
        localStorage.setItem(this.key, cookieValue);
        sessionStorage.setItem(this.key, cookieValue);
      } catch (error) {
        // Ignorer les erreurs de sync
      }

      return cookieValue;
    }

    // Méthode 2: localStorage
    try {
      const localValue = localStorage.getItem(this.key);
      if (localValue) {
        secureLog.log(`[PersistentStorage] Retrieved from localStorage: ${this.key}`);

        // Restaurer dans le cookie
        setCookie(this.key, localValue);
        return localValue;
      }
    } catch (error) {
      secureLog.warn(`[PersistentStorage] localStorage get failed:`, error);
    }

    // Méthode 3: sessionStorage
    try {
      const sessionValue = sessionStorage.getItem(this.key);
      if (sessionValue) {
        secureLog.log(`[PersistentStorage] Retrieved from sessionStorage: ${this.key}`);

        // Restaurer dans le cookie et localStorage
        setCookie(this.key, sessionValue);
        localStorage.setItem(this.key, sessionValue);
        return sessionValue;
      }
    } catch (error) {
      secureLog.warn(`[PersistentStorage] sessionStorage get failed:`, error);
    }

    // Méthode 4: IndexedDB (asynchrone - restauration en arrière-plan)
    // On lance la récupération depuis IndexedDB en arrière-plan
    // Si une valeur existe, elle sera restaurée dans les autres storages
    getIndexedDB(this.key).then((indexedValue) => {
      if (indexedValue) {
        secureLog.log(`[PersistentStorage] Retrieved from IndexedDB (async): ${this.key}`);

        // Restaurer dans tous les autres storages
        setCookie(this.key, indexedValue);
        try {
          localStorage.setItem(this.key, indexedValue);
          sessionStorage.setItem(this.key, indexedValue);
        } catch (error) {
          // Ignorer
        }
      }
    }).catch((error) => {
      secureLog.warn(`[PersistentStorage] IndexedDB get failed:`, error);
    });

    secureLog.log(`[PersistentStorage] No value found for: ${this.key}`);
    return null;
  }

  /**
   * Supprime la valeur de tous les storages
   */
  remove(): void {
    secureLog.log(`[PersistentStorage] Removing ${this.key}`);

    // Supprimer de IndexedDB
    deleteIndexedDB(this.key).catch((error) => {
      secureLog.warn(`[PersistentStorage] IndexedDB delete failed:`, error);
    });

    // Supprimer du cookie
    deleteCookie(this.key);

    // Supprimer de localStorage
    try {
      localStorage.removeItem(this.key);
    } catch (error) {
      // Ignorer
    }

    // Supprimer de sessionStorage
    try {
      sessionStorage.removeItem(this.key);
    } catch (error) {
      // Ignorer
    }
  }

  /**
   * Vérifie si une valeur existe
   */
  exists(): boolean {
    return this.get() !== null;
  }
}

/**
 * Fonction utilitaire pour stocker/récupérer des objets JSON
 */
export class PersistentJSONStorage<T = any> {
  private storage: PersistentStorage;

  constructor(key: string) {
    this.storage = new PersistentStorage(key);
  }

  set(value: T): void {
    try {
      const json = JSON.stringify(value);
      this.storage.set(json);
    } catch (error) {
      secureLog.error(`[PersistentJSONStorage] JSON stringify error:`, error);
    }
  }

  get(): T | null {
    try {
      const raw = this.storage.get();
      if (!raw) return null;

      return JSON.parse(raw) as T;
    } catch (error) {
      secureLog.error(`[PersistentJSONStorage] JSON parse error:`, error);
      return null;
    }
  }

  remove(): void {
    this.storage.remove();
  }

  exists(): boolean {
    return this.storage.exists();
  }
}
