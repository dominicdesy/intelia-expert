"use client";

import { useState, useCallback } from "react";
import { startRegistration, startAuthentication } from "@simplewebauthn/browser";
import { useAuthStore } from "./useAuthStore";

interface PasskeyDevice {
  id: string;
  device_name: string;
  device_type: "platform" | "cross-platform";
  created_at: string;
  last_used_at: string | null;
  backup_eligible: boolean;
  backup_state: boolean;
  transports: string[];
}

export function usePasskey() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuthStore();

  /**
   * Check if WebAuthn is supported in the current browser
   */
  const isSupported = useCallback(() => {
    return (
      window?.PublicKeyCredential !== undefined &&
      typeof window.PublicKeyCredential === "function"
    );
  }, []);

  /**
   * Get auth token from localStorage
   */
  const getAuthToken = useCallback(() => {
    try {
      const authData = localStorage.getItem("intelia-expert-auth");
      if (authData) {
        const parsed = JSON.parse(authData);
        return parsed?.access_token || null;
      }
    } catch (error) {
      console.error("[Passkey] Failed to get auth token:", error);
    }
    return null;
  }, []);

  /**
   * Register a new passkey/credential
   */
  const registerPasskey = useCallback(
    async (deviceName?: string) => {
      if (!user) {
        throw new Error("User must be authenticated to register a passkey");
      }

      if (!isSupported()) {
        throw new Error("WebAuthn is not supported in this browser");
      }

      setIsLoading(true);
      setError(null);

      try {
        // Get auth token
        const token = getAuthToken();
        if (!token) {
          throw new Error("No authentication token found");
        }

        // Step 1: Get registration options from backend
        const optionsRes = await fetch("/api/v1/webauthn/register/start", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          credentials: "include",
          body: JSON.stringify({ device_name: deviceName }),
        });

        if (!optionsRes.ok) {
          const errorData = await optionsRes.json();
          throw new Error(errorData.detail || "Failed to start registration");
        }

        const response = await optionsRes.json();
        const options = response.options; // Extract options from response wrapper

        // Step 2: Prompt user for biometric authentication
        const credential = await startRegistration(options);

        // Step 3: Send credential to backend for verification
        const verifyRes = await fetch("/api/v1/webauthn/register/finish", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          credentials: "include",
          body: JSON.stringify({
            credential,
            device_name: deviceName || "Unknown Device",
          }),
        });

        if (!verifyRes.ok) {
          const errorData = await verifyRes.json();
          throw new Error(errorData.detail || "Failed to verify registration");
        }

        const result = await verifyRes.json();
        return result;
      } catch (err: any) {
        const errorMessage =
          err.name === "NotAllowedError"
            ? "Registration was cancelled"
            : err.message || "Failed to register passkey";
        setError(errorMessage);
        throw new Error(errorMessage);
      } finally {
        setIsLoading(false);
      }
    },
    [user, isSupported, getAuthToken]
  );

  /**
   * Authenticate using a passkey
   */
  const authenticateWithPasskey = useCallback(async () => {
    if (!isSupported()) {
      throw new Error("WebAuthn is not supported in this browser");
    }

    setIsLoading(true);
    setError(null);

    try {
      // Step 1: Get authentication options from backend
      const optionsRes = await fetch("/api/v1/webauthn/authenticate/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
      });

      if (!optionsRes.ok) {
        const errorData = await optionsRes.json();
        throw new Error(
          errorData.detail || "Failed to start authentication"
        );
      }

      const response = await optionsRes.json();
      const options = response.options;
      const challenge_id = response.challenge_id;

      if (!options || !challenge_id) {
        throw new Error("Invalid response from backend");
      }

      // Step 2: Prompt user for biometric authentication
      const credential = await startAuthentication(options);

      // Add challenge_id to credential before sending to backend
      credential.challenge_id = challenge_id;

      // Step 3: Send credential to backend for verification
      const verifyRes = await fetch("/api/v1/webauthn/authenticate/finish", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ credential }),
      });

      if (!verifyRes.ok) {
        const errorData = await verifyRes.json();
        throw new Error(
          errorData.detail || "Failed to verify authentication"
        );
      }

      const result = await verifyRes.json();
      return result;
    } catch (err: any) {
      const errorMessage =
        err.name === "NotAllowedError"
          ? "Authentication was cancelled"
          : err.message || "Failed to authenticate with passkey";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [isSupported]);

  /**
   * Get list of registered passkeys for current user
   */
  const getPasskeys = useCallback(async (): Promise<PasskeyDevice[]> => {
    if (!user) {
      return [];
    }

    try {
      const token = getAuthToken();
      if (!token) {
        console.error("[Passkey] No auth token for getPasskeys");
        return [];
      }

      const res = await fetch("/api/v1/webauthn/credentials", {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
        credentials: "include",
      });

      if (!res.ok) {
        throw new Error("Failed to fetch passkeys");
      }

      const data = await res.json();
      return data.credentials || [];
    } catch (err: any) {
      setError(err.message || "Failed to fetch passkeys");
      return [];
    }
  }, [user, getAuthToken]);

  /**
   * Delete a passkey
   */
  const deletePasskey = useCallback(
    async (credentialId: string) => {
      if (!user) {
        throw new Error("User must be authenticated");
      }

      setIsLoading(true);
      setError(null);

      try {
        const token = getAuthToken();
        if (!token) {
          throw new Error("No authentication token found");
        }

        const res = await fetch(
          `/api/v1/webauthn/credentials/${credentialId}`,
          {
            method: "DELETE",
            headers: {
              "Authorization": `Bearer ${token}`,
            },
            credentials: "include",
          }
        );

        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(errorData.detail || "Failed to delete passkey");
        }

        return await res.json();
      } catch (err: any) {
        setError(err.message || "Failed to delete passkey");
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [user, getAuthToken]
  );

  return {
    isSupported,
    isLoading,
    error,
    registerPasskey,
    authenticateWithPasskey,
    getPasskeys,
    deletePasskey,
  };
}
