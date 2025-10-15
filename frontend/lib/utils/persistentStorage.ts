/**
 * Système de stockage persistant multi-méthodes
 * Essaie plusieurs méthodes pour garantir la persistance même si localStorage est effacé
 *
 * Ordre de priorité:
 * 1. Cookie (le plus persistant)
 * 2. localStorage (rapide mais peut être effacé)
 * 3. sessionStorage (fallback temporaire)
 */

import { secureLog } from "./secureLogger";

const COOKIE_EXPIRY_DAYS = 365; // 1 an

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

    // Méthode 1: Cookie (priorité absolue - le plus persistant)
    setCookie(this.key, value);

    // Méthode 2: localStorage (rapide, mais peut être effacé)
    try {
      localStorage.setItem(this.key, value);
      secureLog.log(`[PersistentStorage] localStorage saved: ${this.key}`);
    } catch (error) {
      secureLog.warn(`[PersistentStorage] localStorage save failed:`, error);
    }

    // Méthode 3: sessionStorage (fallback temporaire)
    try {
      sessionStorage.setItem(this.key, value);
      secureLog.log(`[PersistentStorage] sessionStorage saved: ${this.key}`);
    } catch (error) {
      secureLog.warn(`[PersistentStorage] sessionStorage save failed:`, error);
    }
  }

  /**
   * Récupère une valeur en essayant toutes les méthodes
   * Priorité: Cookie > localStorage > sessionStorage
   */
  get(): string | null {
    // Méthode 1: Cookie (priorité absolue)
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

    // Méthode 3: sessionStorage (dernier recours)
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

    secureLog.log(`[PersistentStorage] No value found for: ${this.key}`);
    return null;
  }

  /**
   * Supprime la valeur de tous les storages
   */
  remove(): void {
    secureLog.log(`[PersistentStorage] Removing ${this.key}`);

    deleteCookie(this.key);

    try {
      localStorage.removeItem(this.key);
    } catch (error) {
      // Ignorer
    }

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
