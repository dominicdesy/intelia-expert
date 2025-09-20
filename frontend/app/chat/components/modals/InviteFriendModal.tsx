import React, { useState, useMemo, useEffect, useRef } from "react";
import { useTranslation } from "@/lib/languages/i18n";
import { useAuthStore } from "@/lib/stores/auth"; // ✅ Store unifié uniquement
import { apiClient } from "@/lib/api/client";

interface InviteFriendModalProps {
  onClose: () => void;
}

// Types pour les réponses API (conservés)
interface InvitationResult {
  email: string;
  success: boolean;
  status: "sent" | "resent" | "skipped" | "failed";
  reason?: string;
  message: string;
  details?: {
    registered_since?: string;
    last_login?: string;
    invited_by?: string;
    invited_at?: string;
    hours_remaining?: number;
  };
}

interface InvitationResponse {
  success: boolean;
  sent_count: number;
  resent_count: number;
  skipped_count: number;
  failed_count: number;
  message: string;
  results: InvitationResult[];
}

export const InviteFriendModal: React.FC<InviteFriendModalProps> = ({
  onClose,
}) => {
  const { t } = useTranslation();
  const { user } = useAuthStore(); // ✅ Store unifié uniquement
  const [emails, setEmails] = useState("");
  const [personalMessage, setPersonalMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [results, setResults] = useState<InvitationResponse | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  // Forcer les styles au montage (conservé)
  useEffect(() => {
    const overlay = overlayRef.current;

    if (overlay) {
      overlay.style.setProperty("width", "100vw", "important");
      overlay.style.setProperty("height", "100vh", "important");
      overlay.style.setProperty("top", "0", "important");
      overlay.style.setProperty("left", "0", "important");
      overlay.style.setProperty(
        "background-color",
        "rgba(0, 0, 0, 0.5)",
        "important",
      );
      overlay.style.setProperty("backdrop-filter", "blur(2px)", "important");
      overlay.style.setProperty("display", "flex", "important");
      overlay.style.setProperty("align-items", "center", "important");
      overlay.style.setProperty("justify-content", "center", "important");
      overlay.style.setProperty("padding", "16px", "important");

      const content = overlay.querySelector(".bg-white") as HTMLElement;
      if (content) {
        content.style.setProperty("width", "95vw", "important");
        content.style.setProperty("max-width", "700px", "important");
        content.style.setProperty("max-height", "85vh", "important");
        content.style.setProperty("min-width", "320px", "important");
      }
    }
  }, []);

  // ✅ CALCUL CURRENTUSER SIMPLIFIÉ - Store unifié uniquement
  const currentUser = useMemo(() => {
    // UNIQUEMENT le store unifié - plus de fallback
    if (user?.email) {
      console.log(
        "[InviteFriendModal] Utilisateur trouvé dans le store unifié:",
        user.email,
      );
      return {
        email: user.email,
        name: user.name || user.firstName || user.email.split("@")[0],
        id: user.id || user.user_id,
        language: user.language || "fr",
      };
    }

    console.log("[InviteFriendModal] Aucun utilisateur dans le store unifié");
    return null;
  }, [user]);

  // Validation side effect (conservé)
  useEffect(() => {
    if (!currentUser?.email) {
      setErrors(["Vous devez être connecté pour envoyer des invitations"]);
    } else {
      setErrors([]);
    }
  }, [currentUser, t]);

  // Validation des emails (conservée)
  const validateEmails = (
    emailString: string,
  ): { valid: string[]; invalid: string[] } => {
    const emailList = emailString
      .split(",")
      .map((email) => email.trim())
      .filter((email) => email.length > 0);

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const valid: string[] = [];
    const invalid: string[] = [];

    emailList.forEach((email) => {
      if (emailRegex.test(email)) {
        valid.push(email);
      } else {
        invalid.push(email);
      }
    });

    return { valid, invalid };
  };

  // ✅ FONCTION D'ENVOI SIMPLIFIÉE - Plus de vérifications complexes
  const handleSendInvitations = async () => {
    console.log(
      '🖱️ [InviteFriendModal] Bouton "Envoyer" cliqué (version store unifié)',
    );

    setErrors([]);
    setResults(null);

    if (!currentUser?.email) {
      setErrors(["Vous devez être connecté pour envoyer des invitations"]);
      return;
    }

    if (!emails.trim()) {
      setErrors(["Au moins une adresse email est requise"]);
      return;
    }

    const { valid, invalid } = validateEmails(emails);

    if (invalid.length > 0) {
      setErrors([
        `Adresses email invalides : ${invalid.join(", ")}`,
        "Format attendu : email@exemple.com",
      ]);
      return;
    }

    if (valid.length === 0) {
      setErrors(["Aucune adresse email valide trouvée"]);
      return;
    }

    if (valid.length > 10) {
      setErrors(["Maximum 10 invitations à la fois"]);
      return;
    }

    setIsLoading(true);

    try {
      const payload = {
        emails: valid,
        personal_message: personalMessage.trim(),
        inviter_name:
          currentUser.name ||
          currentUser.email?.split("@")[0] ||
          "Utilisateur Intelia",
        inviter_email: currentUser.email,
        language: currentUser.language || "fr",
        force_send: false,
      };

      console.log(
        "🚀 [InviteFriendModal] Appel API avec store unifié:",
        payload,
      );

      // ✅ UTILISE APILIENT.POSTSECURE() - plus d'appels directs
      const response = await apiClient.postSecure<InvitationResponse>(
        "/invitations/send",
        payload,
      );

      if (!response.success) {
        throw new Error(
          response.error?.message || "Erreur lors de l'envoi des invitations",
        );
      }

      if (!response.data) {
        throw new Error("Réponse vide du serveur");
      }

      console.log(
        "✅ [InviteFriendModal] Résultat reçu avec store unifié:",
        response.data,
      );
      setResults(response.data);
    } catch (error) {
      console.error("❌ [InviteFriendModal] Erreur envoi:", error);

      let errorMessage = "Erreur lors de l'envoi des invitations";

      if (error instanceof Error) {
        errorMessage = error.message;
      }

      // ✅ GESTION D'ERREUR SIMPLIFIÉE - Plus de vérifications spécifiques Supabase
      if (
        errorMessage.includes("Session expirée") ||
        errorMessage.includes("Token expired") ||
        errorMessage.includes("Unauthorized")
      ) {
        setErrors([
          "Session expirée",
          "Veuillez vous reconnecter et réessayer",
        ]);
      } else {
        setErrors([errorMessage, "Veuillez réessayer ou contactez le support"]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const getEmailCount = () => {
    const { valid } = validateEmails(emails);
    return valid.length;
  };

  const getFriendlyMessage = (result: InvitationResult) => {
    if (result.status === "sent") {
      return `Invitation envoyée : ${result.email}`;
    }

    if (result.status === "resent") {
      return `Invitation renvoyée : ${result.email}`;
    }

    if (result.status === "skipped") {
      if (result.reason === "user_exists") {
        if (result.details?.registered_since) {
          const registeredDate = new Date(
            result.details.registered_since,
          ).toLocaleDateString("fr-FR");
          return `Utilisateur existant : ${result.email} (inscrit le ${registeredDate})`;
        }
        return `Utilisateur existant : ${result.email}`;
      }

      if (result.reason === "already_invited_by_you") {
        return `Déjà invité par vous : ${result.email}`;
      }

      if (result.reason === "already_invited_by_other") {
        return `Déjà invité par quelqu'un d'autre : ${result.email}`;
      }

      return result.message || `Invitation ignorée : ${result.email}`;
    }

    if (result.status === "failed") {
      if (result.reason?.includes("Invalid email")) {
        return `Email invalide : ${result.email}`;
      }
      if (result.reason?.includes("rate limit")) {
        return "Limite de débit atteinte";
      }
      return `Échec d'envoi : ${result.email}`;
    }

    return result.message;
  };

  // ✅ AFFICHAGE SIMPLIFIÉ - Plus d'utilisateur connecté via store unifié
  if (!currentUser?.email) {
    return (
      <>
        <style jsx>{`
          @keyframes fadeIn {
            from {
              opacity: 0;
            }
            to {
              opacity: 1;
            }
          }

          @keyframes modalSlideIn {
            from {
              opacity: 0;
              transform: translateY(-20px) scale(0.95);
            }
            to {
              opacity: 1;
              transform: translateY(0) scale(1);
            }
          }
        `}</style>

        <div ref={overlayRef} className="fixed inset-0 z-50" onClick={onClose}>
          <div
            className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">
                Inviter des amis
              </h2>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 text-2xl transition-colors hover:bg-gray-100 rounded-full w-8 h-8 flex items-center justify-center"
              >
                ×
              </button>
            </div>
            <div className="p-6">
              <div className="text-center">
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-8 h-8 text-red-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
                    />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  Connexion requise
                </h2>
                <p className="text-sm text-gray-600 mb-4">
                  Vous devez être connecté avec le système unifié pour envoyer
                  des invitations
                </p>
                <button
                  onClick={onClose}
                  className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  Fermer
                </button>
              </div>
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        @keyframes modalSlideIn {
          from {
            opacity: 0;
            transform: translateY(-20px) scale(0.95);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
      `}</style>

      <div ref={overlayRef} className="fixed inset-0 z-50" onClick={onClose}>
        <div
          className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">
              Inviter des amis
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl transition-colors hover:bg-gray-100 rounded-full w-8 h-8 flex items-center justify-center"
            >
              ×
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            <div className="space-y-6">
              {/* Header avec icône */}
              <div className="text-center">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-8 h-8 text-blue-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M18 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zM3 19.235v-.11a6.375 6.375 0 0112.75 0v.109A12.318 12.318 0 019.374 21c-2.331 0-4.512-.645-6.374-1.766z"
                    />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  Partagez Intelia Expert
                </h2>
                <p className="text-sm text-gray-600">
                  Invitez vos collègues à découvrir l'assistant IA spécialisé en
                  agriculture
                </p>
              </div>

              {/* Résultats */}
              {results && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Statut d'envoi
                  </h3>

                  <div className="space-y-3">
                    {results.results.map((result, index) => (
                      <div
                        key={index}
                        className={`p-4 rounded-lg border-l-4 ${
                          result.success &&
                          (result.status === "sent" ||
                            result.status === "resent")
                            ? "bg-green-50 border-green-400"
                            : result.status === "skipped"
                              ? "bg-blue-50 border-blue-400"
                              : "bg-red-50 border-red-400"
                        }`}
                      >
                        <div className="flex items-start space-x-3">
                          <span className="text-2xl mt-1">
                            {result.success &&
                            (result.status === "sent" ||
                              result.status === "resent")
                              ? "✅"
                              : result.status === "skipped"
                                ? "👤"
                                : "❌"}
                          </span>
                          <div className="flex-1">
                            <p className="text-sm text-gray-800 font-medium">
                              {getFriendlyMessage(result)}
                            </p>
                            {result.details?.last_login && (
                              <p className="text-xs text-gray-500 mt-1">
                                Dernière connexion :{" "}
                                {new Date(
                                  result.details.last_login,
                                ).toLocaleDateString("fr-FR")}
                              </p>
                            )}
                            {result.details?.hours_remaining && (
                              <p className="text-xs text-gray-500 mt-1">
                                Prochain renvoi possible dans :{" "}
                                {result.details.hours_remaining}h
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="flex space-x-3 mt-6">
                    <button
                      onClick={() => {
                        setResults(null);
                        setEmails("");
                        setPersonalMessage("");
                      }}
                      className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-200 transition-colors"
                    >
                      Inviter d'autres personnes
                    </button>
                    <button
                      onClick={onClose}
                      className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors"
                    >
                      Fermer
                    </button>
                  </div>
                </div>
              )}

              {/* Messages d'erreur */}
              {errors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="text-red-800">
                    <p className="font-medium mb-2 flex items-center">
                      <svg
                        className="w-5 h-5 mr-2"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
                        />
                      </svg>
                      Erreur de validation
                    </p>
                    <ul className="list-disc list-inside space-y-1 text-sm">
                      {errors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Formulaire principal */}
              {!results && (
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-2">
                      Adresses email
                      {getEmailCount() > 0 && (
                        <span className="ml-2 text-blue-600 font-normal">
                          ({getEmailCount()} destinataire
                          {getEmailCount() > 1 ? "s" : ""})
                        </span>
                      )}
                    </label>
                    <textarea
                      value={emails}
                      onChange={(e) => setEmails(e.target.value)}
                      placeholder="email1@exemple.com, email2@exemple.com, ..."
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                      rows={3}
                      disabled={isLoading}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Séparez les adresses par des virgules. Maximum 10
                      invitations.
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-2">
                      Message personnel
                      <span className="text-gray-500 font-normal">
                        (optionnel)
                      </span>
                    </label>
                    <textarea
                      value={personalMessage}
                      onChange={(e) => setPersonalMessage(e.target.value)}
                      placeholder="Ajouter un message personnel à votre invitation..."
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                      rows={4}
                      maxLength={500}
                      disabled={isLoading}
                    />
                    <div className="flex justify-between items-center mt-1">
                      <p className="text-xs text-gray-500">
                        Ce message sera inclus dans l'email d'invitation
                      </p>
                      <span className="text-xs text-gray-400">
                        {personalMessage.length}/500
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Boutons d'action */}
              <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                {!results && (
                  <button
                    onClick={handleSendInvitations}
                    disabled={isLoading || getEmailCount() === 0}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center space-x-2"
                  >
                    {isLoading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>Envoi en cours...</span>
                      </>
                    ) : (
                      <>
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth={1.5}
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
                          />
                        </svg>
                        <span>
                          Envoyer{" "}
                          {getEmailCount() > 0 ? `(${getEmailCount()})` : ""}
                        </span>
                      </>
                    )}
                  </button>
                )}
              </div>

              {/* Footer */}
              <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-100">
                Les invitations sont gérées de manière sécurisée via le système
                unifié. Vos contacts ne recevront qu'un seul email d'invitation.
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
