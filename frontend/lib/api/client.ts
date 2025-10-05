// lib/api/client.ts - CLIENT API CORRIGÉ avec gestion d'erreurs harmonisée

interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    message: string;
    status?: number;
    details?: any;
  };
}

export class APIClient {
  private baseURL: string;
  private headers: Record<string, string>;

  constructor() {
    // Correction: Utiliser la variable d'environnement DigitalOcean sans ajouter /api
    this.baseURL =
      process.env.NEXT_PUBLIC_API_BASE_URL || "https://expert.intelia.com/api";

    this.headers = {
      "Content-Type": "application/json",
      Origin: "https://expert.intelia.com",
    };

    console.log("[APIClient] Initialisé avec baseURL:", this.baseURL);
  }

  // CORRECTION CRITIQUE: Construction URL propre
  private buildURL(endpoint: string): string {
    // Enlever leading slash si présent
    const cleanEndpoint = endpoint.startsWith("/")
      ? endpoint.slice(1)
      : endpoint;

    // IMPORTANT: Enlever /api s'il est déjà présent dans baseURL
    const cleanBaseUrl = this.baseURL.replace(/\/api\/?$/, "");

    // Construire l'URL avec /api/v1 une seule fois
    const version = process.env.NEXT_PUBLIC_API_VERSION || "v1";
    const fullUrl = `${cleanBaseUrl}/api/${version}/${cleanEndpoint}`;

    console.log("[APIClient] URL construite:", fullUrl);
    return fullUrl;
  }

  // Méthode pour rafraîchir le token si nécessaire
  private async refreshTokenIfNeeded(): Promise<void> {
    try {
      const authData = localStorage.getItem('intelia-expert-auth');
      if (!authData) return;
      
      const parsed = JSON.parse(authData);
      const expiresAt = new Date(parsed.expires_at || 0).getTime();
      const now = Date.now();
      const tenMinutes = 10 * 60 * 1000;
      
      // Si le token expire dans moins de 10 minutes, le rafraîchir
      if (expiresAt - now < tenMinutes) {
        console.log('[APIClient] Token proche expiration, rafraîchissement...');
        
        const url = this.buildURL('auth/refresh-token');
        const token = await this.getAuthToken();
        
        if (!token) return;
        
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });
        
        if (response.ok) {
          const data = await response.json();
          const newAuthData = {
            access_token: data.access_token,
            token_type: 'bearer',
            expires_at: data.expires_at,
            synced_at: Date.now(),
          };
          
          localStorage.setItem('intelia-expert-auth', JSON.stringify(newAuthData));
          console.log('[APIClient] Token rafraîchi avec succès');
        }
      }
    } catch (error) {
      console.error('[APIClient] Erreur rafraîchissement token:', error);
    }
  }

  // Méthode de base pour les requêtes avec gestion d'erreurs améliorée
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    useAuth: boolean = false,
  ): Promise<APIResponse<T>> {
    try {
      // AJOUT: Rafraîchir le token avant chaque requête si nécessaire
      await this.refreshTokenIfNeeded();
      
      const url = this.buildURL(endpoint);
      console.log(`[APIClient] URL construite: ${url}`);

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...((options.headers as Record<string, string>) || {}),
      };

      if (useAuth) {
        const token = await this.getAuthToken();
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
          console.log("[APIClient] Token ajouté à la requête");
        } else {
          console.warn(
            "[APIClient] Aucun token disponible pour requête authentifiée",
          );
        }
      }

      const config: RequestInit = {
        ...options,
        headers,
        credentials: "include",
      };

      console.log(`[APIClient] Requête: ${options.method || "GET"} ${url}`);

      const response = await fetch(url, config);

      // Logging détaillé du statut
      console.log(
        `[APIClient] Réponse: ${response.status} ${response.statusText}`,
      );

      // Gestion spécifique des erreurs HTTP
      if (!response.ok) {
        let errorDetails: any = null;
        let errorMessage = `Request failed with status ${response.status}`;

        try {
          // Essayer de lire le corps de la réponse pour plus de détails
          const contentType = response.headers.get("content-type");

          if (contentType?.includes("application/json")) {
            errorDetails = await response.json();
            console.log("[APIClient] Détails erreur JSON:", errorDetails);

            // Extraire le message d'erreur du backend
            if (errorDetails.detail) {
              errorMessage = errorDetails.detail;
            } else if (errorDetails.message) {
              errorMessage = errorDetails.message;
            } else if (errorDetails.error) {
              errorMessage = errorDetails.error;
            }
          } else {
            // Si ce n'est pas du JSON, lire comme texte
            const textError = await response.text();
            console.log("[APIClient] Détails erreur texte:", textError);
            if (textError && textError.trim()) {
              errorMessage = textError;
            }
          }
        } catch (parseError) {
          console.warn(
            "[APIClient] Impossible de parser la réponse d'erreur:",
            parseError,
          );
        }

        // Messages d'erreurs spécifiques par code de statut
        let friendlyMessage = errorMessage;

        switch (response.status) {
          case 400:
            if (
              !errorMessage ||
              errorMessage === `Request failed with status ${response.status}`
            ) {
              friendlyMessage = "Données de requête invalides";
            }
            break;
          case 401:
            if (
              !errorMessage ||
              errorMessage === `Request failed with status ${response.status}`
            ) {
              friendlyMessage = "Non autorisé - vérifiez vos identifiants";
            }
            break;
          case 403:
            if (
              !errorMessage ||
              errorMessage === `Request failed with status ${response.status}`
            ) {
              friendlyMessage = "Accès refusé";
            }
            break;
          case 404:
            if (
              !errorMessage ||
              errorMessage === `Request failed with status ${response.status}`
            ) {
              friendlyMessage = "Service non trouvé";
            }
            break;
          case 429:
            if (
              !errorMessage ||
              errorMessage === `Request failed with status ${response.status}`
            ) {
              friendlyMessage = "Trop de requêtes - veuillez ralentir";
            }
            break;
          case 500:
            if (
              !errorMessage ||
              errorMessage === `Request failed with status ${response.status}`
            ) {
              friendlyMessage = "Erreur interne du serveur";
            }
            break;
          case 502:
            friendlyMessage =
              "Passerelle défaillante - serveur temporairement indisponible";
            break;
          case 503:
            friendlyMessage = "Service temporairement indisponible";
            break;
          case 504:
            friendlyMessage = "Délai de connexion dépassé";
            break;
          default:
            if (
              !errorMessage ||
              errorMessage === `Request failed with status ${response.status}`
            ) {
              friendlyMessage = `Erreur HTTP ${response.status}`;
            }
        }

        console.error(`[APIClient] HTTP ${response.status}:`, friendlyMessage);

        // Créer un objet d'erreur enrichi
        const apiError = new Error(friendlyMessage);
        (apiError as any).status = response.status;
        (apiError as any).statusText = response.statusText;
        (apiError as any).details = errorDetails;
        (apiError as any).originalMessage = errorMessage;

        return {
          success: false,
          data: null as T,
          error: {
            message: friendlyMessage,
            status: response.status,
            details: errorDetails,
          },
        };
      }

      // Gestion de la réponse réussie améliorée
      let data: T;
      try {
        const contentType = response.headers.get("content-type");

        if (contentType?.includes("application/json")) {
          data = await response.json();
          console.log("[APIClient] Réponse JSON parsée avec succès");
        } else {
          // Si ce n'est pas du JSON, retourner comme texte
          const textData = await response.text();
          data = textData as unknown as T;
          console.log("[APIClient] Réponse texte reçue");
        }
      } catch (parseError) {
        console.error("[APIClient] Erreur parsing réponse:", parseError);
        throw new Error("Erreur de traitement de la réponse du serveur");
      }

      return {
        success: true,
        data,
        error: null,
      };
    } catch (error: any) {
      console.error("[APIClient] Erreur requête:", error);

      // Gestion des erreurs réseau
      let errorMessage = "Erreur de connexion";

      if (error.name === "TypeError" && error.message.includes("fetch")) {
        errorMessage =
          "Impossible de contacter le serveur - vérifiez votre connexion internet";
      } else if (error.name === "AbortError") {
        errorMessage = "Requête annulée";
      } else if (error.message.includes("timeout")) {
        errorMessage = "Délai de connexion dépassé";
      } else if (error.message) {
        errorMessage = error.message;
      }

      return {
        success: false,
        data: null as T,
        error: {
          message: errorMessage,
          status: error.status || 0,
          details: error,
        },
      };
    }
  }

  // Méthodes GET
  async get<T>(endpoint: string): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  async getSecure<T>(endpoint: string): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: "GET" }, true);
  }

  // Méthodes POST
  async post<T>(endpoint: string, data?: any): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async postSecure<T>(endpoint: string, data?: any): Promise<APIResponse<T>> {
    return this.request<T>(
      endpoint,
      {
        method: "POST",
        body: data ? JSON.stringify(data) : undefined,
      },
      true,
    );
  }

  // Méthodes PUT
  async put<T>(endpoint: string, data?: any): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async putSecure<T>(endpoint: string, data?: any): Promise<APIResponse<T>> {
    return this.request<T>(
      endpoint,
      {
        method: "PUT",
        body: data ? JSON.stringify(data) : undefined,
      },
      true,
    );
  }

  // Méthodes DELETE
  async delete<T>(endpoint: string): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: "DELETE" });
  }

  async deleteSecure<T>(endpoint: string): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: "DELETE" }, true);
  }

  // Récupération du token d'authentification
  private async getAuthToken(): Promise<string | null> {
    try {
      const authData = localStorage.getItem("intelia-expert-auth");
      if (!authData) {
        console.warn("[APIClient] Aucun token d'authentification trouvé");
        return null;
      }

      const parsed = JSON.parse(authData);
      const token = parsed.access_token;

      if (!token) {
        console.warn("[APIClient] Token invalide dans localStorage");
        return null;
      }

      return token;
    } catch (error) {
      console.error("[APIClient] Erreur récupération token:", error);
      return null;
    }
  }
}

// Export: Instance unique exportée
export const apiClient = new APIClient();

// Export par défaut de la classe pour les cas spéciaux si nécessaire
export default APIClient;