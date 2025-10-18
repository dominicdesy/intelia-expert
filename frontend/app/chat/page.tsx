"use client";

import { useSearchParams } from "next/navigation";
import { useRouter } from "next/navigation";
import React, {
  useState,
  useEffect,
  useRef,
  useMemo,
  useCallback,
  Suspense,
} from "react";
import ReactMarkdown from "react-markdown";
import { Message } from "../../types";
import { useAuthStore } from "@/lib/stores/auth";
import { useTranslation } from "@/lib/languages/i18n";
import { useChatStore } from "./hooks/useChatStore";
import {
  generateAIResponse,
  generateVisionResponse,
  checkUserQuota,
} from "./services/apiService";
import { conversationService } from "./services/conversationService";

import {
  PaperAirplaneIcon,
  UserIcon,
  PlusIcon,
  InteliaLogo,
  ArrowDownIcon,
  ThumbUpIcon,
  ThumbDownIcon,
  CameraIcon,
  XMarkIcon,
} from "./utils/icons";
import { HistoryMenu } from "./components/HistoryMenu";
import { UserMenuButton } from "./components/UserMenuButton";
import { ZohoSalesIQ } from "./components/ZohoSalesIQ";
import { FeedbackModal } from "./components/modals/FeedbackModal";
import { LoadingMessage } from "./components/LoadingMessage";
import ShareConversationButton from "./components/ShareConversationButton";
import { HelpButton, HelpTour } from "./components/HelpTour";
import { secureLog } from "@/lib/utils/secureLogger";
import { VoiceInput } from "./components/VoiceInput";

// Composant ChatInput optimisé avec React.memo
const ChatInput = React.memo(
  ({
    inputMessage,
    setInputMessage,
    onSendMessage,
    isLoadingChat,
    clarificationState,
    isMobileDevice,
    inputRef,
    selectedImages,
    onImagesSelect,
    onImageRemove,
    fileInputRef,
    t,
  }: {
    inputMessage: string;
    setInputMessage: (value: string) => void;
    onSendMessage: () => void;
    isLoadingChat: boolean;
    clarificationState: any;
    isMobileDevice: boolean;
    inputRef: React.RefObject<HTMLInputElement>;
    selectedImages: File[];
    onImagesSelect: (files: File[]) => void;
    onImageRemove: (index: number) => void;
    fileInputRef: React.RefObject<HTMLInputElement>;
    t: (key: string) => string;
  }) => {
    const [previewUrls, setPreviewUrls] = React.useState<string[]>([]);
    const [imageErrors, setImageErrors] = React.useState<boolean[]>([]);

    // Créer les URLs de prévisualisation quand les images changent
    React.useEffect(() => {
      if (selectedImages.length > 0) {
        try {
          const urls = selectedImages.map(img => URL.createObjectURL(img));
          setPreviewUrls(urls);
          setImageErrors(new Array(selectedImages.length).fill(false));

          // Nettoyer les URLs lors du démontage
          return () => {
            urls.forEach(url => URL.revokeObjectURL(url));
          };
        } catch (error) {
          console.error("Error creating preview URLs:", error);
          setImageErrors(new Array(selectedImages.length).fill(true));
        }
      } else {
        setPreviewUrls([]);
        setImageErrors([]);
      }
    }, [selectedImages]);

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          onSendMessage();
        }
      },
      [onSendMessage],
    );

    const handleChange = useCallback(
      (e: React.ChangeEvent<HTMLInputElement>) => {
        setInputMessage(e.target.value);
      },
      [setInputMessage],
    );

    const handleButtonClick = useCallback(
      (e: React.MouseEvent) => {
        e.preventDefault();
        onSendMessage();
      },
      [onSendMessage],
    );

    const handleVoiceTranscript = useCallback(
      (transcript: string) => {
        // Append voice transcript to existing input message
        const currentText = inputMessage.trim();
        const newText = currentText
          ? `${currentText} ${transcript}`
          : transcript;
        setInputMessage(newText);

        // Focus input field after voice input
        inputRef.current?.focus();
      },
      [inputMessage, setInputMessage, inputRef],
    );

    return (
      <div className="w-full space-y-2">
        {/* Images Preview Grid */}
        {selectedImages.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 p-2 bg-blue-50 border border-blue-200 rounded-lg">
            {selectedImages.map((image, index) => (
              <div key={index} className="relative group">
                {previewUrls[index] && !imageErrors[index] ? (
                  <img
                    src={previewUrls[index]}
                    alt={`Preview ${index + 1}`}
                    className="w-full h-24 object-cover rounded"
                    onError={() => {
                      const newErrors = [...imageErrors];
                      newErrors[index] = true;
                      setImageErrors(newErrors);
                    }}
                  />
                ) : (
                  <div className="w-full h-24 bg-gray-200 rounded flex items-center justify-center">
                    <CameraIcon className="w-8 h-8 text-gray-400" />
                  </div>
                )}
                <button
                  onClick={() => onImageRemove(index)}
                  className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                  title="Retirer l'image"
                >
                  <XMarkIcon className="w-4 h-4" />
                </button>
                <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-1 rounded-b truncate">
                  {image.name} ({(image.size / 1024).toFixed(1)} KB)
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Input Area */}
        <div
          className={`flex items-center min-h-[48px] w-full ${isMobileDevice ? "mobile-input-container" : "space-x-2"}`}
        >
          <div
            className={`flex-1 ${isMobileDevice ? "mobile-input-wrapper" : ""}`}
          >
            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              placeholder={
                clarificationState
                  ? t("chat.clarificationPlaceholder")
                  : selectedImages.length > 0
                    ? "Décrivez ce que vous voulez savoir..."
                    : isMobileDevice
                      ? t("chat.placeholderMobile")
                      : t("chat.placeholder")
              }
              className={`w-full h-12 px-4 bg-gray-100 border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none text-sm flex items-center ${isMobileDevice ? "ios-input-fix" : ""}`}
              disabled={isLoadingChat}
              aria-label={t("chat.placeholder")}
              style={{
                fontSize: isMobileDevice ? "16px" : "14px",
                WebkitAppearance: "none",
                borderRadius: isMobileDevice ? "25px" : "9999px",
              }}
            />
          </div>

          {/* Send Button */}
          <button
            onClick={handleButtonClick}
            disabled={isLoadingChat || (!inputMessage.trim() && selectedImages.length === 0)}
            className={`flex-shrink-0 h-12 w-12 flex items-center justify-center text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors rounded-full hover:bg-blue-50 ${isMobileDevice ? "mobile-send-button" : ""}`}
            title={isLoadingChat ? t("chat.sending") : t("chat.send")}
            aria-label={isLoadingChat ? t("chat.sending") : t("chat.send")}
            style={{
              minWidth: "48px",
              width: "48px",
              height: "48px",
            }}
          >
            <PaperAirplaneIcon />
          </button>

          {/* Camera Button - Visible uniquement sur desktop */}
          {!isMobileDevice && (
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoadingChat}
              className={`flex-shrink-0 h-12 w-12 flex items-center justify-center text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors rounded-full hover:bg-blue-50 ${selectedImages.length > 0 ? "bg-blue-50" : ""}`}
              title={selectedImages.length > 0 ? `${selectedImages.length} image(s)` : "Ajouter des images"}
              aria-label={selectedImages.length > 0 ? `${selectedImages.length} image(s)` : "Ajouter des images"}
              style={{
                minWidth: "48px",
                width: "48px",
                height: "48px",
              }}
            >
              <CameraIcon />
              {selectedImages.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-blue-600 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center">
                  {selectedImages.length}
                </span>
              )}
            </button>
          )}

          {/* Voice Input Button */}
          <VoiceInput
            onTranscript={handleVoiceTranscript}
            disabled={isLoadingChat}
          />
        </div>
      </div>
    );
  },
);

ChatInput.displayName = "ChatInput";

// Composant MessageList optimisé avec React.memo
const MessageList = React.memo(
  ({
    processedMessages,
    isLoadingChat,
    handleFeedbackClick,
    getUserInitials,
    user,
    t,
    currentLanguage,
  }: {
    processedMessages: any[];
    isLoadingChat: boolean;
    handleFeedbackClick: (
      messageId: string,
      feedback: "positive" | "negative",
    ) => void;
    getUserInitials: (user: any) => string;
    user: any;
    t: (key: string) => string;
    currentLanguage: string;
  }) => {
    const messageComponents = useMemo(() => {
      return processedMessages.map((message, index) => (
        <div key={`${message.id}-${index}`}>
          <div
            className={`flex items-start space-x-3 min-w-0 ${message.isUser ? "justify-end" : "justify-start"}`}
          >
            {!message.isUser && (
              <div className="flex-shrink-0 w-10 h-10 grid place-items-center">
                <InteliaLogo className="h-8 w-auto" />
              </div>
            )}

            <div
              className={`px-3 sm:px-4 py-2 rounded-2xl max-w-[85%] sm:max-w-none break-words ${message.isUser ? "bg-blue-600 text-white ml-auto" : "bg-white border border-gray-200 text-gray-900"}`}
            >
              {message.isUser ? (
                <div className="space-y-2">
                  {/* Support multiple images */}
                  {message.imageUrls && message.imageUrls.length > 0 ? (
                    message.imageUrls.length === 1 ? (
                      <img
                        src={message.imageUrls[0]}
                        alt="Image envoyée"
                        className="max-w-[200px] max-h-[200px] rounded-lg object-cover"
                      />
                    ) : (
                      <div className="grid grid-cols-2 gap-2 max-w-[400px]">
                        {message.imageUrls.map((url, idx) => (
                          <img
                            key={idx}
                            src={url}
                            alt={`Image ${idx + 1}`}
                            className="w-full h-32 rounded-lg object-cover"
                          />
                        ))}
                      </div>
                    )
                  ) : message.imageUrl ? (
                    <img
                      src={message.imageUrl}
                      alt="Image envoyée"
                      className="max-w-[200px] max-h-[200px] rounded-lg object-cover"
                    />
                  ) : null}
                  {message.content && (
                    <p className="whitespace-pre-wrap leading-relaxed text-sm">
                      {message.content}
                    </p>
                  )}
                </div>
              ) : (
                <>
                  <ReactMarkdown
                    className="prose prose-sm max-w-none break-words prose-p:my-3 prose-li:my-1 prose-ul:my-4 prose-strong:text-gray-900 prose-headings:font-bold prose-headings:text-gray-900"
                    components={{
                      h2: ({ node, ...props }) => (
                        <h2
                          className="text-xl font-bold text-blue-900 mt-8 mb-6 border-b-2 border-blue-200 pb-3 bg-blue-50 px-4 py-2 rounded-t-lg"
                          {...props}
                        />
                      ),
                      h3: ({ node, ...props }) => (
                        <h3
                          className="text-lg font-semibold text-gray-800 mt-6 mb-4 border-l-4 border-blue-400 pl-4 bg-gray-50 py-2"
                          {...props}
                        />
                      ),
                      p: ({ node, ...props }) => (
                        <p
                          className="leading-relaxed text-gray-800 my-4 text-justify"
                          {...props}
                        />
                      ),
                      ul: ({ node, ...props }) => (
                        <ul
                          className="list-disc list-outside space-y-3 text-gray-800 my-6 ml-6 pl-2"
                          {...props}
                        />
                      ),
                      li: ({ node, ...props }) => (
                        <li className="leading-relaxed pl-2 my-2" {...props} />
                      ),
                      strong: ({ node, ...props }) => (
                        <strong
                          className="font-bold text-blue-800 bg-blue-50 px-1 rounded"
                          {...props}
                        />
                      ),
                      table: ({ node, ...props }) => (
                        <div className="overflow-x-auto my-6 -mx-1 sm:mx-0">
                          <table
                            className="min-w-full border border-gray-300 rounded-lg shadow-sm"
                            {...props}
                          />
                        </div>
                      ),
                      th: ({ node, ...props }) => (
                        <th
                          className="border border-gray-300 px-4 py-3 bg-blue-100 font-bold text-left text-blue-900"
                          {...props}
                        />
                      ),
                      td: ({ node, ...props }) => (
                        <td
                          className="border border-gray-300 px-4 py-3 hover:bg-gray-50"
                          {...props}
                        />
                      ),
                    }}
                  >
                    {message.processedContent}
                  </ReactMarkdown>

                  {/* Feedback buttons inside the message bubble at the bottom */}
                  {!message.isUser && index > 0 && message.conversation_id && (
                    <div className="flex items-center space-x-2 mt-3 pt-2 border-t border-gray-100">
                      <button
                        onClick={() => handleFeedbackClick(message.id, "positive")}
                        className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${
                          message.feedback === "positive"
                            ? "text-green-600 bg-green-50"
                            : "text-gray-400"
                        }`}
                        title={t("chat.helpfulResponse")}
                        aria-label={t("chat.helpfulResponse")}
                      >
                        <ThumbUpIcon />
                      </button>
                      <button
                        onClick={() => handleFeedbackClick(message.id, "negative")}
                        className={`p-1.5 rounded-full hover:bg-gray-100 transition-colors ${
                          message.feedback === "negative"
                            ? "text-red-600 bg-red-50"
                            : "text-gray-400"
                        }`}
                        title={t("chat.notHelpfulResponse")}
                        aria-label={t("chat.notHelpfulResponse")}
                      >
                        <ThumbDownIcon />
                      </button>

                      {message.feedback && (
                        <div className="flex items-center space-x-2">
                          <span className="text-xs text-gray-500">
                            {t("chat.feedbackThanks")}
                          </span>
                          {message.feedbackComment && (
                            <span
                              className="text-xs text-blue-600"
                              title={`${t("chat.feedbackComment")}: ${message.feedbackComment}`}
                            >
                              💬
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>

            {message.isUser && (
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                <span className="text-white text-sm font-medium">
                  {getUserInitials(user)}
                </span>
              </div>
            )}
          </div>
        </div>
      ));
    }, [processedMessages, handleFeedbackClick, getUserInitials, user, t]);

    return (
      <>
        {processedMessages.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <div className="text-sm">{t("chat.noMessages")}</div>
          </div>
        ) : (
          messageComponents
        )}

        {isLoadingChat && (
          <div className="flex items-start space-x-3">
            <div className="w-10 h-10 grid place-items-center flex-shrink-0">
              <InteliaLogo className="h-8 w-auto" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl px-3 sm:px-4 py-3 max-w-[85%] sm:max-w-none break-words">
              <LoadingMessage language={currentLanguage} />
            </div>
          </div>
        )}
      </>
    );
  },
);

MessageList.displayName = "MessageList";

// Composant principal ChatInterface
function ChatInterface() {
  const {
    user,
    isAuthenticated,
    isLoading,
    hasHydrated,
    checkAuth,
    handleOAuthTokenFromURL,
  } = useAuthStore();
  const { t, currentLanguage } = useTranslation();
  const searchParams = useSearchParams();
  const router = useRouter();

  // Stores Zustand
  const currentConversation = useChatStore(
    (state) => state.currentConversation,
  );
  const setCurrentConversation = useChatStore(
    (state) => state.setCurrentConversation,
  );
  const addMessage = useChatStore((state) => state.addMessage);
  const updateMessage = useChatStore((state) => state.updateMessage);
  const createNewConversation = useChatStore(
    (state) => state.createNewConversation,
  );
  const loadConversations = useChatStore((state) => state.loadConversations);

  // États séparés pour éviter les cascades de re-renders
  const [inputMessage, setInputMessage] = useState("");
  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const [isLoadingChat, setIsLoadingChat] = useState(false);
  const [isMobileDevice, setIsMobileDevice] = useState(false);
  const [isKeyboardVisible, setIsKeyboardVisible] = useState(false);
  const [keyboardHeight, setKeyboardHeight] = useState(0);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [viewportHeight, setViewportHeight] = useState(0);
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  const [clarificationState, setClarificationState] = useState<{
    messageId: string;
    originalQuestion: string;
    clarificationQuestions: string[];
  } | null>(null);

  const [feedbackModal, setFeedbackModal] = useState<{
    isOpen: boolean;
    messageId: string | null;
    feedbackType: "positive" | "negative" | null;
  }>({
    isOpen: false,
    messageId: null,
    feedbackType: null,
  });

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const lastMessageCountRef = useRef(0);
  const isMountedRef = useRef(true);
  const inputRef = useRef<HTMLInputElement>(null);
  const hasLoadedConversationsRef = useRef(false);

  // Mémorisation stable des données
  const messages: Message[] = useMemo(() => {
    return currentConversation?.messages || [];
  }, [currentConversation?.messages]);

  const hasMessages = useMemo(() => {
    return messages.length > 0;
  }, [messages.length]);

  // Gestion d'erreur unifiée
  const handleAuthError = useCallback(
    (error: any) => {
      secureLog.error("[Chat] Auth error détectée:", error);

      const isSessionExpired =
        error?.status === 401 ||
        error?.status === 403 ||
        error?.message?.includes("Token expired") ||
        error?.message?.includes("Auth session missing") ||
        error?.message?.includes("Unauthorized") ||
        error?.message?.includes("Forbidden") ||
        error?.message?.includes("authentication_failed") ||
        error?.message?.includes("Session expirée") ||
        error?.detail === "Token expired";

      if (isSessionExpired) {
        secureLog.log(
          "[Chat] Session expirée détectée - déconnexion automatique",
        );

        if (isMountedRef.current) {
          setCurrentConversation(null);
          setClarificationState(null);
          setInputMessage("");
          setIsLoadingChat(false);
        }

        import("@/lib/services/logoutService")
          .then(({ logoutService }) => {
            logoutService.performLogout(user);
          })
          .catch((err) => {
            secureLog.warn("[Chat] Fallback - redirection directe:", err);
            setTimeout(() => {
              window.location.href = "/";
            }, 100);
          });

        return;
      }

      secureLog.warn("[Chat] Erreur non-auth (pas de redirection):", error);
    },
    [user, setCurrentConversation],
  );

  // Fonctions utilitaires
  const getUserInitials = useCallback((user: any): string => {
    if (!user) return "U";

    if (user.name) {
      const names = user.name.trim().split(" ");
      if (names.length >= 2) {
        return (names[0][0] + names[names.length - 1][0]).toUpperCase();
      }
      return names[0][0].toUpperCase();
    }

    if (user.email) {
      const emailPart = user.email.split("@")[0];
      if (emailPart.includes(".")) {
        const parts = emailPart.split(".");
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return emailPart.substring(0, 2).toUpperCase();
    }

    return "U";
  }, []);

  const preprocessMarkdown = useCallback((content: string): string => {
    if (!content) return "";

    let processed = content;
    processed = processed.replace(
      /(#{1,6})\s*([^#\n]+?)([A-Z][a-z])/g,
      "$1 $2\n\n$3",
    );
    processed = processed.replace(/^(#{1,6}[^\n]+)(?!\n)/gm, "$1\n");
    processed = processed.replace(/([a-z])([A-Z])/g, "$1, $2");
    processed = processed.replace(/([.!?:])([A-Z])/g, "$1 $2");
    processed = processed.replace(/([a-z])(\*\*[A-Z])/g, "$1 $2");
    processed = processed.replace(/([.!?:])\s*(\*\*[^*]+\*\*)/g, "$1\n\n$2");
    processed = processed.replace(
      /([.!?:])\s*-\s*([A-Z][^:]+:)/g,
      "$1\n\n### $2",
    );
    processed = processed.replace(/([.!?:])\s*-\s*([A-Z][^-]+)/g, "$1\n\n- $2");
    processed = processed.replace(/([^.\n])\n([•\-\*]\s)/g, "$1\n\n$2");
    processed = processed.replace(
      /([•\-\*]\s[^\n]+)\n([A-Z][^•\-\*])/g,
      "$1\n\n$2",
    );
    processed = processed.replace(
      /(Causes Possibles|Recommandations|Prevention|Court terme|Long terme|Immediat)([^-:])/g,
      "\n\n### $1\n\n$2",
    );
    processed = processed.replace(/[ \t]+/g, " ");
    processed = processed.replace(/\n\n\n+/g, "\n\n");
    processed = processed.trim();

    return processed;
  }, []);

  const cleanResponseText = useCallback((text: string): string => {
    if (!text) return "";
    if (text.length < 100) return text.trim();

    let cleaned = text;
    cleaned = cleaned.replace(/\*\*Source:\s*[^*]+\*\*/g, "");
    cleaned = cleaned.replace(/Source:\s*[^\n]+/g, "");
    cleaned = cleaned.replace(
      /protection, regardless of the species involved[^.]+\./g,
      "",
    );
    cleaned = cleaned.replace(/^\d+\.\s+[A-Z][^:]+:\s*$/gm, "");
    cleaned = cleaned.replace(/^\w\.\s+[A-Z][^:]+:\s*$/gm, "");
    cleaned = cleaned.replace(/^INTRODUCTION[^\n]*$/gm, "");
    cleaned = cleaned.replace(/^[A-Z\s]{10,}:?\s*$/gm, "");
    cleaned = cleaned.replace(/Page\s+\d+\s+of\s+\d+/gi, "");
    cleaned = cleaned.replace(/\bDOI:\s*[^\s]+/gi, "");
    cleaned = cleaned.replace(/\s+/g, " ");
    cleaned = cleaned.replace(/\n\s*\n\s*\n/g, "\n\n");
    cleaned = cleaned.replace(/^\s*\n+/, "");
    cleaned = cleaned.replace(/\n+\s*$/, "");

    return cleaned.trim();
  }, []);

  // Handlers pour les images
  const handleImagesSelect = useCallback((files: File[]) => {
    setSelectedImages(files);
  }, []);

  const handleImageRemove = useCallback((index: number) => {
    setSelectedImages((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // Ref pour le file input (partagé entre header et input bar)
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleCameraClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const processedMessages = useMemo(() => {
    return messages.map((message) => ({
      ...message,
      processedContent: message.isUser
        ? message.content
        : preprocessMarkdown(message.content),
    }));
  }, [messages, preprocessMarkdown]);

  // Effet de nettoyage au démontage
  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;
      document.body.classList.remove("keyboard-open");
      hasLoadedConversationsRef.current = false;

      // Cleanup: Retirer les styles mobiles quand on quitte la page chat
      if (isMobileDevice) {
        document.body.style.position = '';
        document.body.style.width = '';
        document.body.style.height = '';
        document.body.style.overflow = '';
      }
    };
  }, [isMobileDevice]);

  // OAuth via store unifié
  useEffect(() => {
    const processOAuth = async () => {
      try {
        const handled = await handleOAuthTokenFromURL();
        if (handled) {
          secureLog.log("[Chat] Token OAuth traité par le store unifié");
        }
      } catch (error) {
        secureLog.error("[Chat] Erreur traitement OAuth:", error);
      }
    };

    processOAuth();
  }, [handleOAuthTokenFromURL]);

  // Détection de device mobile
  useEffect(() => {
    if (!isMountedRef.current) return;

    const detectMobileDevice = () => {
      const userAgent = navigator.userAgent.toLowerCase();
      const isMobileUA =
        /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(
          userAgent,
        );
      const isTabletScreen = window.innerWidth <= 1024;
      const hasTouchScreen =
        "ontouchstart" in window || navigator.maxTouchPoints > 0;
      const isIPadOS =
        navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1;
      const isDesktopTouchscreen =
        window.innerWidth > 1200 && navigator.maxTouchPoints > 0 && !isIPadOS;

      return (
        (isMobileUA || isIPadOS || (isTabletScreen && hasTouchScreen)) &&
        !isDesktopTouchscreen
      );
    };

    setIsMobileDevice(detectMobileDevice());

    const handleResize = () => {
      if (isMountedRef.current) {
        setIsMobileDevice(detectMobileDevice());
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Gestion clavier mobile
  useEffect(() => {
    if (!isMobileDevice || !isMountedRef.current) return;

    let initialViewportHeight =
      window.visualViewport?.height || window.innerHeight;
    let isCancelled = false;

    setViewportHeight(initialViewportHeight);

    const handleViewportChange = () => {
      if (isCancelled || !isMountedRef.current) return;

      if (window.visualViewport) {
        const currentHeight = window.visualViewport.height;
        const heightDifference = initialViewportHeight - currentHeight;

        setViewportHeight(currentHeight);
        setIsKeyboardVisible(heightDifference > 150);
        setKeyboardHeight(heightDifference > 150 ? heightDifference : 0);

        if (heightDifference > 150) {
          document.body.classList.add("keyboard-open");
        } else {
          document.body.classList.remove("keyboard-open");
        }
      }
    };

    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", handleViewportChange);
    }

    return () => {
      isCancelled = true;
      if (window.visualViewport) {
        window.visualViewport.removeEventListener(
          "resize",
          handleViewportChange,
        );
      }
      document.body.classList.remove("keyboard-open");
    };
  }, [isMobileDevice]);

  // Auto-scroll
  useEffect(() => {
    if (!isMountedRef.current) return;

    if (
      messages.length > lastMessageCountRef.current &&
      shouldAutoScroll &&
      !isUserScrolling
    ) {
      const timeoutId = setTimeout(() => {
        if (isMountedRef.current && messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
      }, 100);

      return () => clearTimeout(timeoutId);
    }

    lastMessageCountRef.current = messages.length;
  }, [messages.length, shouldAutoScroll, isUserScrolling]);

  // Gestion du scroll
  useEffect(() => {
    const chatContainer = chatContainerRef.current;
    if (!chatContainer || !isMountedRef.current) return;

    let scrollTimeout: NodeJS.Timeout;
    let isScrolling = false;
    let isCancelled = false;

    const handleScroll = () => {
      if (!isMountedRef.current || isCancelled) return;

      const { scrollTop, scrollHeight, clientHeight } = chatContainer;
      const isAtBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 50;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;

      if (!isScrolling) {
        setIsUserScrolling(true);
        isScrolling = true;
      }

      setShowScrollButton(!isNearBottom && messages.length > 3);

      if (isAtBottom) {
        setShouldAutoScroll(true);
      } else {
        setShouldAutoScroll(false);
      }

      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        if (isMountedRef.current && !isCancelled) {
          setIsUserScrolling(false);
          isScrolling = false;
        }
      }, 150);
    };

    chatContainer.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      isCancelled = true;
      chatContainer.removeEventListener("scroll", handleScroll);
      clearTimeout(scrollTimeout);
    };
  }, [messages.length]);

  // Message de bienvenue
  useEffect(() => {
    if (
      isAuthenticated &&
      !currentConversation &&
      !hasMessages &&
      isMountedRef.current
    ) {
      const welcomeMessage: Message = {
        id: "welcome",
        content: t("chat.welcome"),
        isUser: false,
        timestamp: new Date(),
      };

      const welcomeConversation = {
        id: "welcome",
        title: t("chat.newConversation"),
        preview: t("chat.startQuestion"),
        message_count: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        language: currentLanguage,
        status: "active" as const,
        messages: [welcomeMessage],
      };

      setCurrentConversation(welcomeConversation);
      lastMessageCountRef.current = 1;
    }
  }, [
    isAuthenticated,
    currentConversation,
    hasMessages,
    t,
    currentLanguage,
    setCurrentConversation,
  ]);

  // useEffect pour les changements de langue
  useEffect(() => {
    if (
      currentConversation?.id === "welcome" &&
      currentConversation.messages.length === 1 &&
      currentConversation.messages[0].content !== t("chat.welcome") &&
      isMountedRef.current
    ) {
      const updatedMessage: Message = {
        ...currentConversation.messages[0],
        content: t("chat.welcome"),
      };

      const updatedConversation = {
        ...currentConversation,
        messages: [updatedMessage],
      };

      setCurrentConversation(updatedConversation);
    }
  }, [currentLanguage, t, currentConversation, setCurrentConversation]);


// Chargement initial unique
  useEffect(() => {
    if (
      isAuthenticated &&
      user?.id &&
      !hasLoadedConversationsRef.current &&
      isMountedRef.current
    ) {
      secureLog.log("[Chat] Chargement initial UNIQUE pour:", user.id);
      hasLoadedConversationsRef.current = true;

      const userId = user.id;

      const performInitialLoad = async () => {
        try {
          const { loadConversations: loadFn } = useChatStore.getState();
          await loadFn(userId);
          secureLog.log("[Chat] Chargement initial terminé avec succès");
        } catch (error) {
          secureLog.error("[Chat] Erreur chargement initial:", error);

          if (error?.status === 401 || error?.status === 403) {
            secureLog.log("[Chat] Session expirée détectée - redirection");
            hasLoadedConversationsRef.current = false;
            setTimeout(() => {
              window.location.href = "/";
            }, 1000);
          } else {
            hasLoadedConversationsRef.current = false;
          }
        }
      };

      setTimeout(performInitialLoad, 100);
    }
  }, [isAuthenticated, user?.id]);





	// FONCTION POUR CHAT (texte + images)
	const handleSendMessage = useCallback(async () => {
	  const safeText = inputMessage;
	  const imagesToSend = selectedImages;

	  // Allow send if there's either text or images
	  if ((!safeText.trim() && imagesToSend.length === 0) || !isMountedRef.current) return;

	  // Créer les URLs des images pour l'affichage dans la bulle
	  let imageUrls: string[] = [];
	  if (imagesToSend.length > 0) {
		try {
		  imageUrls = imagesToSend.map(img => URL.createObjectURL(img));
		} catch (error) {
		  console.error("Error creating image URLs:", error);
		}
	  }

	  const userMessage: Message = {
		id: Date.now().toString(),
		content: safeText.trim(),
		isUser: true,
		timestamp: new Date(),
		imageUrls: imageUrls.length > 0 ? imageUrls : undefined,
		imageUrl: imageUrls.length > 0 ? imageUrls[0] : undefined, // Backward compatibility
	  };

	  let conversationIdToSend: string | undefined = undefined;

	  if (
		currentConversation &&
		currentConversation.id !== "welcome" &&
		!currentConversation.id.startsWith("temp-")
	  ) {
		conversationIdToSend = currentConversation.id;
	  }

	  // Ajouter le message utilisateur
	  addMessage(userMessage);
	  setInputMessage("");
	  setSelectedImages([]); // Clear the selected images
	  setIsLoadingChat(true);
	  setShouldAutoScroll(true);
	  setIsUserScrolling(false);

	  // Variables pour le streaming
	  let assistantId: string | null = null;
	  let messageCreated = false;

	  try {
		// 🔒 VÉRIFICATION QUOTA AVANT D'APPELER LE LLM
		await checkUserQuota();

		let response;

		// IMAGE ANALYSIS PATH
		if (imagesToSend.length > 0) {
		  secureLog.log(`[Chat] Sending ${imagesToSend.length} image(s) for analysis`);

		  // Enrichir le message avec le nombre d'images si plusieurs
		  let enrichedMessage = safeText.trim() || t("chat.analyzeImageDefault");
		  if (imagesToSend.length > 1) {
		    enrichedMessage = `[${imagesToSend.length} images fournies] ${enrichedMessage}`;
		  }

		  // Envoyer toutes les images pour analyse
		  response = await generateVisionResponse(
			imagesToSend,
			enrichedMessage,
			user,
			currentLanguage,
			conversationIdToSend,
		  );

		  // Create assistant message immediately with the response
		  assistantId = `ai-${Date.now()}`;
		  addMessage({
			id: assistantId,
			content: response.response,
			isUser: false,
			timestamp: new Date(),
			conversation_id: response.conversation_id,
		  });
		  messageCreated = true;

		// REGULAR TEXT CHAT PATH
		} else {
		  let finalQuestionOrSafeText: string;

		  if (clarificationState) {
			finalQuestionOrSafeText =
			  clarificationState.originalQuestion + " " + safeText.trim();
			setClarificationState(null);
		  } else {
			finalQuestionOrSafeText = safeText.trim();
		  }

		  const optimalLevel = undefined;

		  // APPEL AVEC CALLBACKS DE STREAMING
		  response = await generateAIResponse(
			finalQuestionOrSafeText,
			user,
			currentLanguage,
			conversationIdToSend,
			optimalLevel,
			clarificationState !== null,
			clarificationState?.originalQuestion,
			clarificationState ? { answer: safeText.trim() } : undefined,
			{
			  onDelta: (chunk: string) => {
				if (!messageCreated) {
				  assistantId = `ai-${Date.now()}`;
				  addMessage({
					id: assistantId,
					content: chunk,
					isUser: false,
					timestamp: new Date(),
				  });
				  messageCreated = true;
				  setIsLoadingChat(false);
				} else if (assistantId) {
				  const currentMessage = useChatStore
					.getState()
					.currentConversation?.messages.find(
					  (m) => m.id === assistantId,
					);
				  if (currentMessage) {
					updateMessage(assistantId, {
					  content: (currentMessage.content || "") + chunk,
					});
				  }
				}
			  },
			  onFinal: (fullText: string) => {
				if (assistantId) {
				  updateMessage(assistantId, {
					content: fullText,
				  });
				}
			  },
			  onFollowup: (followupMessage: string) => {
				addMessage({
				  id: `followup-${Date.now()}`,
				  content: followupMessage,
				  isUser: false,
				  timestamp: new Date(),
				});
			  },
			},
		  );
		}

		if (!isMountedRef.current) return;

		// Vérification des erreurs d'authentification
		if (
		  response?.response?.includes?.("Session expirée") ||
		  response?.response?.includes?.("Token expired") ||
		  response?.response?.includes?.("authentication_failed") ||
		  response?.response?.includes?.("Unauthorized") ||
		  response?.response?.includes?.("401") ||
		  response?.note?.includes?.("Session expirée") ||
		  response?.note?.includes?.("Token expired")
		) {
		  handleAuthError({
			status: 401,
			message: "Token expired from API response",
			detail: "Token expired",
		  });
		  return;
		}

		const needsClarification =
		  response.clarification_result?.clarification_requested === true;

		if (needsClarification && assistantId) {
		  const clarificationText =
			(response.full_text || response.response) +
			`\n\n${t("chat.clarificationInstruction")}`;

		  updateMessage(assistantId, {
			content: clarificationText,
			conversation_id: response.conversation_id,
		  });

		  setClarificationState({
			messageId: assistantId,
			originalQuestion: safeText.trim(),
			clarificationQuestions: response.clarification_questions || [],
		  });
		} else if (assistantId) {
		  const safeResponseVersions = response.response_versions
			? {
				ultra_concise:
				  response.response_versions.ultra_concise || response.response,
				concise: response.response_versions.concise || response.response,
				standard:
				  response.response_versions.standard || response.response,
				detailed:
				  response.response_versions.detailed || response.response,
			  }
			: undefined;

		  updateMessage(assistantId, {
			conversation_id: response.conversation_id,
			...(safeResponseVersions && {
			  response_versions: safeResponseVersions,
			}),
			originalResponse: response.response,
		  });
		}

		// ✅ AJOUT: Refresh automatique si nouvelle conversation créée
		if (response?.conversation_id && user?.id && isMountedRef.current) {
		  const { conversationGroups } = useChatStore.getState();
		  const isNewConversation = !conversationGroups.some(g => 
			g.conversations.some(c => c.id === response.conversation_id)
		  );
		  
		  if (isNewConversation) {
		    secureLog.log("🔄 [Chat] Nouvelle conversation créée, refresh dans 2s");
		    setTimeout(async () => {
			  if (!isMountedRef.current) return;
			  try {
			    // ✅ Utiliser refreshConversations qui force le bypass de la protection
			    const { refreshConversations } = useChatStore.getState();
			    await refreshConversations(user.id);
			    secureLog.log("✅ [Chat] Historique rafraîchi automatiquement avec bypass");
			  } catch (error) {
			    secureLog.warn("⚠️ [Chat] Erreur refresh auto:", error);
			  }
		    }, 2000);
		  }		  
		}
		// ✅ FIN DE L'AJOUT

	  } catch (error: any) {
		secureLog.error(t("chat.sendError"), error);

		// Gérer spécifiquement l'erreur de quota dépassé
		if (error.message === "QUOTA_EXCEEDED") {
		  const quotaInfo = error.quotaInfo || {};

		  // Message structuré avec les clés de traduction
		  const quotaMessage = [
			`**${t("chat.quotaExceeded")}**`,
			"",
			`**${t("chat.questionsUsed")}:** ${quotaInfo.questions_used || 0}/${quotaInfo.monthly_quota || 0}`,
			`**${t("chat.planName")}:** ${quotaInfo.plan_name || "free"}`,
			"",
			t("chat.upgradePrompt")
		  ].join("\n");

		  if (isMountedRef.current) {
			addMessage({
			  id: `quota-error-${Date.now()}`,
			  content: quotaMessage,
			  isUser: false,
			  timestamp: new Date(),
			});
		  }
		  return; // Ne pas appeler handleAuthError pour les quotas
		}

		handleAuthError(error);

		if (isMountedRef.current) {
		  if (!messageCreated && assistantId) {
			addMessage({
			  id: `error-${Date.now()}`,
			  content:
				error instanceof Error ? error.message : t("chat.errorMessage"),
			  isUser: false,
			  timestamp: new Date(),
			});
		  } else if (assistantId) {
			const errorContent =
			  error instanceof Error ? error.message : t("chat.errorMessage");
			updateMessage(assistantId, {
			  content: errorContent,
			});
		  }
		}
	  } finally {
		if (isMountedRef.current) {
		  setIsLoadingChat(false);
		}
	  }
	}, [
	  inputMessage,
	  selectedImages,
	  currentConversation,
	  addMessage,
	  updateMessage,
	  clarificationState,
	  user,
	  currentLanguage,
	  handleAuthError,
	  t,
	  loadConversations,
	]);


  // Fonctions de feedback
  const handleFeedbackClick = useCallback(
    (messageId: string, feedback: "positive" | "negative") => {
      if (!isMountedRef.current) return;

      setFeedbackModal({
        isOpen: true,
        messageId,
        feedbackType: feedback,
      });
    },
    [],
  );

  const handleFeedbackSubmit = useCallback(
    async (feedback: "positive" | "negative", comment?: string) => {
      const { messageId } = feedbackModal;
      if (!messageId || !isMountedRef.current) return;

      const message = messages.find((msg) => msg.id === messageId);
      if (!message || !message.conversation_id) {
        return;
      }

      setIsSubmittingFeedback(true);

      try {
        updateMessage(messageId, {
          feedback,
          feedbackComment: comment,
        });

        const feedbackValue = feedback === "positive" ? 1 : -1;

        try {
          await conversationService.sendFeedback(
            message.conversation_id,
            feedbackValue,
          );

          if (comment && comment.trim()) {
            try {
              await conversationService.sendFeedbackComment(
                message.conversation_id,
                comment.trim(),
              );
            } catch (commentError) {
              secureLog.warn(t("chat.commentNotSent"), commentError);
            }
          }
        } catch (feedbackError) {
          secureLog.error(t("chat.feedbackSendError"), feedbackError);
          handleAuthError(feedbackError);

          if (isMountedRef.current) {
            updateMessage(messageId, {
              feedback: null,
              feedbackComment: undefined,
            });
          }
          throw feedbackError;
        }
      } catch (error) {
        secureLog.error(t("chat.feedbackGeneralError"), error);
        throw error;
      } finally {
        if (isMountedRef.current) {
          setIsSubmittingFeedback(false);
        }
      }
    },
    [feedbackModal, messages, updateMessage, handleAuthError, t],
  );

  const handleFeedbackModalClose = useCallback(() => {
    if (!isMountedRef.current) return;

    setFeedbackModal({
      isOpen: false,
      messageId: null,
      feedbackType: null,
    });
  }, []);

  const handleNewConversation = useCallback(() => {
    if (!isMountedRef.current) return;

    createNewConversation();
    setClarificationState(null);

    const welcomeMessage: Message = {
      id: "welcome",
      content: t("chat.welcome"),
      isUser: false,
      timestamp: new Date(),
    };

    const welcomeConversation = {
      id: "welcome",
      title: t("chat.newConversation"),
      preview: t("chat.startQuestion"),
      message_count: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      language: currentLanguage,
      status: "active" as const,
      messages: [welcomeMessage],
    };

    setCurrentConversation(welcomeConversation);
    lastMessageCountRef.current = 1;

    setShouldAutoScroll(true);
    setIsUserScrolling(false);
    setShowScrollButton(false);
  }, [createNewConversation, t, currentLanguage, setCurrentConversation]);

  const scrollToBottom = useCallback(() => {
    if (!isMountedRef.current) return;

    setShouldAutoScroll(true);
    setIsUserScrolling(false);
    setShowScrollButton(false);
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Calcul des styles dynamiques pour mobile - 100dvh pour fullscreen
  const containerStyle = useMemo(() => {
    return isMobileDevice
      ? {
          height: "100dvh", // Dynamic viewport height pour fullscreen
          minHeight: "100dvh",
          maxHeight: "100dvh",
        }
      : {};
  }, [isMobileDevice]);

  const chatScrollStyle = useMemo(() => {
    return isMobileDevice
      ? {
          height: isKeyboardVisible
            ? `calc(100dvh - 140px - ${keyboardHeight}px)` // Dynamic viewport height
            : "calc(100dvh - 140px)",
          maxHeight: isKeyboardVisible
            ? `calc(100dvh - 140px - ${keyboardHeight}px)`
            : "calc(100dvh - 140px)",
          overflow: "auto",
          paddingBottom: "1rem",
        }
      : {
          scrollPaddingBottom: "7rem",
        };
  }, [isMobileDevice, isKeyboardVisible, keyboardHeight]);

  // États de chargement simplifiés
  if (!hasHydrated) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600">{t("chat.loading")}</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">{t("chat.loading")}</p>
        </div>
      </div>
    );
  }

  // Condition de rendu simplifiée
  if (!isAuthenticated || !user) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">{t("chat.loading")}</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* ✅ Styles mobiles maintenant consolidés dans globals.css @layer mobile */}
      <ZohoSalesIQ user={user} />
      <div
        className={`bg-gray-50 flex flex-col relative z-0 ${isMobileDevice ? "chat-main-container" : "min-h-dvh h-screen"}`}
        style={containerStyle}
      >
        <header className="bg-white border-b border-gray-100 px-2 sm:px-4 py-3 flex-shrink-0">
          <div className="flex items-center justify-between">
            {/* Left side - Adaptatif mobile/desktop */}
            <div className={`flex items-center ${isMobileDevice ? 'space-x-1' : 'space-x-2'}`}>
              <button
                onClick={handleNewConversation}
                className="w-10 h-10 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors flex items-center justify-center border border-gray-200 flex-shrink-0"
                title={t("nav.newConversation")}
                aria-label={t("nav.newConversation")}
              >
                <PlusIcon className="w-5 h-5" />
              </button>

              <div className="header-icon-container history-menu-container flex-shrink-0">
                <HistoryMenu />
              </div>

              {/* Camera Button - Visible uniquement sur iPhone */}
              {isMobileDevice && (
                <button
                  onClick={handleCameraClick}
                  disabled={isLoadingChat}
                  className={`flex-shrink-0 w-10 h-10 flex items-center justify-center text-blue-600 hover:text-blue-700 disabled:text-gray-300 transition-colors rounded-lg hover:bg-blue-50 border border-gray-200 ${selectedImages.length > 0 ? "bg-blue-50" : ""}`}
                  title={selectedImages.length > 0 ? `${selectedImages.length} image(s)` : t("chat.uploadImages")}
                  aria-label={selectedImages.length > 0 ? `${selectedImages.length} image(s)` : t("chat.uploadImages")}
                >
                  <CameraIcon className="w-5 h-5" />
                  {selectedImages.length > 0 && (
                    <span className="absolute -top-1 -right-1 bg-blue-600 text-white text-xs w-4 h-4 rounded-full flex items-center justify-center font-bold">
                      {selectedImages.length}
                    </span>
                  )}
                </button>
              )}

              {/* Logo - masqué sur iPhone, visible sur desktop */}
              {!isMobileDevice && (
                <div className="flex items-center space-x-2 ml-1">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 grid place-items-center flex-shrink-0">
                    <InteliaLogo className="h-6 sm:h-8 w-auto" />
                  </div>
                  <h1 className="text-base sm:text-lg font-medium text-gray-900 truncate hidden sm:block">
                    {t("common.appName")}
                  </h1>
                </div>
              )}
            </div>

            {/* Right side - Toujours visible sur mobile */}
            <div className="flex items-center space-x-1 sm:space-x-2">
              {/* Share button - Visible uniquement desktop quand conversation active */}
              {currentConversation &&
               currentConversation.id !== "welcome" &&
               !currentConversation.id.startsWith("temp-") && (
                <div className={isMobileDevice ? 'hidden' : 'block'}>
                  <ShareConversationButton conversationId={currentConversation.id} />
                </div>
              )}

              {/* Help button - Toujours visible */}
              <div className="flex-shrink-0">
                <HelpButton onClick={() => setIsHelpOpen(true)} />
              </div>

              {/* User menu - Toujours visible, priorité maximale */}
              <div className="header-icon-container user-menu-container flex-shrink-0">
                <UserMenuButton />
              </div>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-hidden flex flex-col min-h-0">
          <div
            ref={chatContainerRef}
            className={`flex-1 overflow-y-auto px-2 sm:px-4 py-6 pb-28 overscroll-contain ${isMobileDevice ? "chat-scroll-area" : ""}`}
            style={chatScrollStyle}
          >
            <div className="max-w-full sm:max-w-4xl mx-auto space-y-6 px-2 sm:px-4">
              <MessageList
                processedMessages={processedMessages}
                isLoadingChat={isLoadingChat}
                handleFeedbackClick={handleFeedbackClick}
                getUserInitials={getUserInitials}
                user={user}
                t={t}
                currentLanguage={currentLanguage}
              />

              <div ref={messagesEndRef} />
            </div>
          </div>

          {showScrollButton && (
            <div className="fixed bottom-24 right-8 z-10">
              <button
                onClick={scrollToBottom}
                className="bg-blue-600 text-white p-3 rounded-full shadow-lg hover:bg-blue-700 transition-colors"
                title={t("chat.scrollToBottom")}
                aria-label={t("chat.scrollToBottom")}
              >
                <ArrowDownIcon />
              </button>
            </div>
          )}

          <div
            className={`px-2 sm:px-4 py-2 bg-white border-t border-gray-100 z-20 ${isMobileDevice ? "chat-input-fixed" : "sticky bottom-0"}`}
            style={{
              paddingBottom: isMobileDevice
                ? `calc(env(safe-area-inset-bottom) + 8px)`
                : "calc(env(safe-area-inset-bottom) + 8px)",
              position: isMobileDevice ? "fixed" : "sticky",
              bottom: 0,
              left: 0,
              right: 0,
              backgroundColor: "white",
              borderTop: "1px solid rgb(243 244 246)",
              zIndex: 1000,
              minHeight: isMobileDevice ? "70px" : "auto",
              display: "flex",
              alignItems: "center",
            }}
          >
            <div className="max-w-full sm:max-w-4xl lg:max-w-5xl xl:max-w-6xl mx-auto w-full sm:w-[90%] lg:w-[75%] xl:w-[60%]">
              {clarificationState && (
                <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-blue-700 text-sm font-medium">
                      {t("chat.clarificationMode")}
                    </span>
                    <button
                      onClick={() => setClarificationState(null)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      {t("modal.cancel")}
                    </button>
                  </div>
                </div>
              )}

              {/* Hidden File Input - Partagé entre header et input bar */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => {
                  const files = e.target.files;
                  if (files && files.length > 0) {
                    const imageFiles = Array.from(files).filter(file => file.type.startsWith("image/"));
                    if (imageFiles.length > 0) {
                      handleImagesSelect([...selectedImages, ...imageFiles]);
                    }
                  }
                  e.target.value = ""; // Reset pour permettre la re-sélection
                }}
                className="hidden"
                multiple
                aria-label={t("chat.uploadImages")}
              />

              <ChatInput
                inputMessage={inputMessage}
                setInputMessage={setInputMessage}
                onSendMessage={handleSendMessage}
                isLoadingChat={isLoadingChat}
                clarificationState={clarificationState}
                isMobileDevice={isMobileDevice}
                inputRef={inputRef}
                selectedImages={selectedImages}
                onImagesSelect={handleImagesSelect}
                onImageRemove={handleImageRemove}
                fileInputRef={fileInputRef}
                t={t}
              />

              <div className="text-center mt-2">
                <p className="text-xs text-gray-500">{t("chat.disclaimer")}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <FeedbackModal
        isOpen={feedbackModal.isOpen}
        onClose={handleFeedbackModalClose}
        onSubmit={handleFeedbackSubmit}
        feedbackType={feedbackModal.feedbackType ?? undefined}
        isSubmitting={isSubmittingFeedback}
      />

      <HelpTour
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
      />
    </>
  );
}

// Composant de chargement
function ChatLoading() {
  return (
    <div className="h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Chargement du chat...</p>
      </div>
    </div>
  );
}

// Export par défaut avec Suspense
export default function ChatPage() {
  return (
    <Suspense fallback={<ChatLoading />}>
      <ChatInterface />
    </Suspense>
  );
}
