// types/index.ts - VERSION COMPLÈTE AVEC SUPPORT AGENT LLM + TOUT LE CONTENU ORIGINAL

// ==================== NOUVEAUX TYPES AGENT LLM ====================

export interface AgentMetadata {
  complexity: string;
  sub_queries_count: number;
  synthesis_method: string;
  sources_used: number;
  processing_time?: number;
  decisions?: string[];
}

export interface StreamCallbacks {
  onStart?: (data: any) => void;
  onDelta?: (text: string) => void;
  onFinal?: (text: string) => void;
  onError?: (error: any) => void;
  onFollowup?: (msg: string) => void;

  // 🆕 NOUVEAUX CALLBACKS AGENT
  onAgentStart?: (complexity: string, subQueries: number) => void;
  onAgentThinking?: (decisions: string[]) => void;
  onChunk?: (content: string, confidence: number, source?: string) => void;
  onAgentEnd?: (synthesisMethod: string, sourcesUsed: number) => void;
  onAgentError?: (error: string) => void;
  onAgentProgress?: (step: string, progress: number) => void;
}

// Types d'événements SSE Agent
export type AgentStartEvent = {
  type: "agent_start";
  complexity: string;
  sub_queries_count: number;
};

export type AgentThinkingEvent = {
  type: "agent_thinking";
  decisions: string[];
};

export type ChunkEvent = {
  type: "chunk";
  content: string;
  confidence: number;
  source?: string;
};

export type AgentProgressEvent = {
  type: "agent_progress";
  step: string;
  progress: number;
};

export type AgentEndEvent = {
  type: "agent_end";
  synthesis_method: string;
  sources_used: number;
};

export type AgentErrorEvent = {
  type: "agent_error";
  error: string;
};

export type ProactiveFollowupEvent = {
  type: "proactive_followup";
  suggestion: string;
};

export type DeltaEvent = {
  type: "delta";
  text: string;
};

export type FinalEvent = {
  type: "final";
  answer: string;
};

export type ErrorEvent = {
  type: "error";
  code?: string;
  message?: string;
};

export type StreamEvent =
  | DeltaEvent
  | FinalEvent
  | ErrorEvent
  | AgentStartEvent
  | AgentThinkingEvent
  | ChunkEvent
  | AgentProgressEvent
  | AgentEndEvent
  | AgentErrorEvent
  | ProactiveFollowupEvent;

// ==================== INTERFACE MESSAGE ÉTENDUE AVEC CONCISION ET RESPONSE_VERSIONS ====================

export interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  feedback?: "positive" | "negative" | null;
  conversation_id?: string;
  feedbackComment?: string; // Commentaire associé au feedback

  // CHAMPS POUR CLARIFICATION
  is_clarification_request?: boolean; // Pour les messages du bot qui demandent des clarifications
  is_clarification_response?: boolean; // Pour les messages utilisateur qui répondent aux clarifications
  clarification_questions?: string[]; // Questions de clarification du bot
  clarification_answers?: Record<string, string>; // Réponses de clarification de l'utilisateur (optionnel)
  original_question?: string; // Question originale avant clarification
  clarification_entities?: Record<string, any>; // Entités extraites des réponses de clarification

  // NOUVEAU: Champs pour le système de concision backend
  response_versions?: {
    ultra_concise: string;
    concise: string;
    standard: string;
    detailed: string;
  };

  // 🆕 AGENT METADATA
  agent_metadata?: AgentMetadata;

  // Champs pour compatibilité (peuvent être supprimés plus tard)
  originalResponse?: string; // Réponse originale avant concision
  processedResponse?: string; // Réponse après traitement de concision
  concisionLevel?: ConcisionLevel; // Niveau de concision appliqué

  // COMPATIBILITY: Champs du petit fichier
  role?: "user" | "assistant";
  sources?: DocumentSource[];
  metadata?: MessageMetadata;
}

// ==================== NOUVEAUX TYPES POUR SESSION TRACKING ====================

export interface UserSession {
  id?: number;
  user_email: string;
  session_id: string;
  login_time: string;
  logout_time?: string;
  last_activity: string;
  session_duration_seconds?: number;
  ip_address?: string;
  user_agent?: string;
  logout_type?: "manual" | "browser_close" | "timeout" | "forced";
  created_at?: string;
  updated_at?: string;
}

export interface SessionAnalytics {
  user_email: string;
  period_days: number;
  total_sessions: number;
  total_connection_time_seconds: number;
  average_session_duration_seconds: number;
  longest_session_seconds: number;
  shortest_session_seconds: number;
  most_active_day: string;
  most_active_hour: number;
  sessions_per_day: number;
  active_days: number;
  logout_type_breakdown: {
    manual: number;
    browser_close: number;
    timeout: number;
    forced: number;
  };
  daily_patterns: Array<{
    date: string;
    sessions: number;
    total_time_seconds: number;
    average_duration: number;
  }>;
  hourly_patterns: Array<{
    hour: number;
    sessions: number;
    average_duration: number;
  }>;
}

export interface HeartbeatResponse {
  status: "ok" | "error";
  timestamp: string;
  session_active?: boolean;
  message?: string;
}

export interface LogoutRequest {
  logout_type?: "manual" | "browser_close" | "timeout";
  session_duration?: number;
}

export interface LogoutResponse {
  status: "success" | "error";
  message: string;
  session_duration_seconds?: number;
  session_id?: string;
  timestamp: string;
}

export interface SessionState {
  sessionId: string | null;
  isActive: boolean;
  loginTime: Date | null;
  lastActivity: Date | null;
  duration: number; // en secondes
}

export interface SessionStore {
  session: SessionState | null;
  isTracking: boolean;
  startSession: (sessionId: string) => void;
  endSession: (
    logoutType?: "manual" | "browser_close" | "timeout",
  ) => Promise<void>;
  updateActivity: () => Promise<void>;
  getSessionDuration: () => number;
  resetSession: () => void;
}

// ==================== NOUVEAUX TYPES POUR AD SYSTEM ====================

export interface AdData {
  id: string;
  title: string;
  description: string;
  imageUrl: string;
  ctaText: string;
  ctaUrl: string;
  company: string;
  rating?: number;
  users?: string;
  duration?: string;
  features: string[];
}

export interface UserSessionStats {
  totalSessions: number;
  averageSessionDuration: number;
  lastAdShown?: string;
  qualifiesForAd: boolean;
}

export interface AdTriggerCriteria {
  MIN_SESSIONS: number;
  MIN_DURATION_PER_SESSION: number; // en secondes
  COOLDOWN_PERIOD: number; // en heures
  CHECK_INTERVAL?: number; // optionnel
  INITIAL_CHECK_DELAY?: number; // optionnel
}

export interface AdModalProps {
  isOpen: boolean;
  onClose: () => void;
  adData: AdData;
  onAdClick: (adId: string) => void;
}

export interface AdProviderProps {
  children: React.ReactNode;
}

export interface AdSystemHookReturn {
  sessionStats: UserSessionStats | null;
  showAd: boolean;
  currentAd: AdData | null;
  handleAdClose: () => void;
  handleAdClick: (adId: string) => void;
  checkAdEligibility: () => Promise<void>;
  triggerAd: () => Promise<void>;
}

export interface AdEventData {
  event: "ad_shown" | "ad_clicked" | "ad_closed" | "ad_error";
  ad_id?: string;
  timestamp: string;
  user_agent?: string;
  session_data?: {
    totalSessions: number;
    averageSessionDuration: number;
  };
}

// ==================== TYPES POUR CONCISION BACKEND ====================

export enum ConcisionLevel {
  ULTRA_CONCISE = "ultra_concise", // Réponse minimale
  CONCISE = "concise", // Réponse courte
  STANDARD = "standard", // Réponse normale
  DETAILED = "detailed", // Réponse complète
}

export interface ConcisionConfig {
  level: ConcisionLevel;
  autoDetect: boolean; // Détection automatique selon le type de question
  userPreference: boolean; // Sauvegarder préférence utilisateur
}

export interface ConcisionControlProps {
  className?: string;
  compact?: boolean;
}

// NOUVEAU: Interface pour sélection de versions backend
export interface ResponseVersionSelection {
  selectedVersion: string;
  availableVersions: Record<string, string>;
  selectedLevel: ConcisionLevel;
}

// Interface pour traitement legacy (compatibilité)
export interface ResponseProcessingResult {
  processedContent: string;
  originalContent: string;
  levelUsed: ConcisionLevel;
  wasProcessed: boolean;
}

// ==================== TYPES EXISTANTS CONSERVÉS ====================

export interface ExpertApiResponse {
  question: string;
  response: string;
  full_text?: string; // plein texte non tronqué (si fourni par l'API)
  conversation_id: string;
  rag_used: boolean;
  rag_score?: number;
  timestamp: string;
  language: string;
  response_time_ms: number;
  mode: string;
  user?: string;
  logged: boolean;
  validation_passed?: boolean;
  validation_confidence?: number;
  // CHAMPS POUR CLARIFICATION
  is_clarification_request?: boolean;
  clarification_questions?: string[];
  // NOUVEAU: Champs pour versions backend
  response_versions?: {
    ultra_concise: string;
    concise: string;
    standard: string;
    detailed: string;
  };
  // 🆕 AGENT METADATA
  agent_metadata?: AgentMetadata;
}

// INTERFACE ConversationData ÉTENDUE AVEC FEEDBACK
export interface ConversationData {
  user_id: string;
  question: string;
  response: string;
  full_text?: string; // plein texte non tronqué (si fourni par l'API)
  conversation_id: string;
  confidence_score?: number;
  response_time_ms?: number;
  language?: string;
  rag_used?: boolean;
  feedback?: 1 | -1 | null; // Feedback numérique pour le backend
  feedback_comment?: string; // Commentaire feedback
  // 🆕 AGENT SUPPORT
  agent_metadata?: AgentMetadata;
}

export interface ConversationItem {
  id: string;
  title: string;
  messages: Array<{
    id: string;
    role: string;
    content: string;
  }>;
  updated_at: string;
  created_at: string;
  feedback?: number | null;
  feedback_comment?: string; // Commentaire dans l'historique
}

// ==================== TYPES POUR CONVERSATIONS STYLE CLAUDE.AI ====================

// Structure complète d'une conversation
export interface Conversation {
  id: string;
  title: string;
  preview: string; // Premier message ou résumé
  message_count: number;
  created_at: string;
  updated_at: string;
  feedback?: number | null;
  language?: string;
  last_message_preview?: string;
  status?: "active" | "archived";
  // COMPATIBILITY: Champs du petit fichier
  user_id?: string;
  messages?: Message[];
}

// Conversation complète avec tous ses messages
export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

// Structure pour l'historique groupé
export interface ConversationGroup {
  title: string; // "Aujourd'hui", "Hier", "Cette semaine", etc.
  conversations: Conversation[];
}

// Réponse API pour l'historique
export interface ConversationHistoryResponse {
  success: boolean;
  conversations: Conversation[];
  groups?: ConversationGroup[];
  total_count: number;
  user_id: string;
  timestamp: string;
}

// Réponse API pour une conversation complète
export interface ConversationDetailResponse {
  success: boolean;
  conversation: ConversationWithMessages;
  timestamp: string;
}

// Options pour le groupement des conversations
export interface ConversationGroupingOptions {
  groupBy: "date" | "topic" | "none";
  sortBy: "updated_at" | "created_at" | "message_count";
  sortOrder: "desc" | "asc";
  limit?: number;
  offset?: number;
}

// Statistiques de conversation
export interface ConversationStats {
  total_conversations: number;
  total_messages: number;
  avg_messages_per_conversation: number;
  most_active_day: string;
  favorite_topics: string[];
  satisfaction_rate: number;
}

// ==================== TYPES POUR CLARIFICATIONS INLINE ====================

// Interface simplifiée pour clarifications inline
export interface ClarificationInlineProps {
  questions: string[];
  originalQuestion: string;
  language: string;
  onSubmit: (answers: Record<string, string>) => Promise<void>;
  onSkip: () => Promise<void>;
  isSubmitting?: boolean;
  conversationId?: string;
}

// Interface pour les réponses de clarification
export interface ClarificationResponse {
  needs_clarification: boolean;
  questions?: string[];
  confidence_score?: number;
  processing_time_ms?: number;
  model_used?: string;
}

// Interface pour l'état des clarifications
export interface ClarificationState {
  pendingClarification: ExpertApiResponse | null;
  isProcessingClarification: boolean;
  clarificationHistory: Array<{
    original_question: string;
    clarification_questions: string[];
    answers: Record<string, string>;
    final_response: string;
    timestamp: string;
  }>;
}

// ==================== TYPES UTILISATEUR AVEC CHAMPS TÉLÉPHONE ====================

export interface User {
  id: string;
  email: string;
  name: string;
  firstName: string;
  lastName: string;
  phone: string; // Champ existant - gardé pour compatibilité
  country: string;
  linkedinProfile: string;
  companyName: string;
  companyWebsite: string;
  linkedinCorporate: string;
  user_type: string;
  language: string;
  created_at: string;
  plan: string;

  // NOUVEAUX CHAMPS TÉLÉPHONE SÉPARÉS POUR SUPABASE
  country_code?: string; // Code pays (ex: +1, +33, +32)
  area_code?: string; // Code régional (ex: 514, 04, 2)
  phone_number?: string; // Numéro principal (ex: 1234567, 12345678)

  // COMPATIBILITY: Champs du petit fichier
  full_name?: string;
  avatar_url?: string;
  consent_given?: boolean;
  consent_date?: string;
  updated_at?: string;
  user_id?: string;
  profile_id?: string;
  preferences?: Record<string, any>;
  is_admin?: boolean;
}

export interface ProfileUpdateData {
  firstName: string;
  lastName: string;
  email: string;
  phone?: string; // Maintenant optionnel pour éviter les conflits
  country: string;
  linkedinProfile: string;
  companyName: string;
  companyWebsite: string;
  linkedinCorporate: string;
  language?: string;

  // NOUVEAUX CHAMPS TÉLÉPHONE SÉPARÉS
  country_code?: string;
  area_code?: string;
  phone_number?: string;
}

// ==================== TYPES SPÉCIFIQUES AU COMPOSANT PHONE ====================

export interface PhoneData {
  country_code: string;
  area_code: string;
  phone_number: string;
}

export interface PhoneValidationResult {
  isValid: boolean;
  errors: string[];
  isValidCountry: boolean;
  isValidArea: boolean;
  isValidNumber: boolean;
}

// ==================== NOUVEAUX TYPES FEEDBACK ET COMMENTAIRES ====================

// Interface pour les données feedback enrichies
export interface FeedbackData {
  conversation_id: string;
  feedback: "positive" | "negative";
  comment?: string;
  timestamp: string;
  user_id?: string;
  // COMPATIBILITY: Champs du petit fichier
  message_id?: string;
  rating?: "positive" | "negative";
  category?: "accuracy" | "relevance" | "completeness" | "other";
}

// Props pour la modal feedback
export interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (
    feedback: "positive" | "negative",
    comment?: string,
  ) => Promise<void>;
  feedbackType: "positive" | "negative";
  isSubmitting?: boolean;
}

// Interface pour les analytics feedback
export interface FeedbackAnalytics {
  period_days: number;
  total_conversations: number;
  total_feedback: number;
  satisfaction_rate: number;
  feedback_rate: number;
  comment_rate: number;
  feedback_breakdown: {
    positive: number;
    negative: number;
    with_comment: number;
  };
  recent_comments: Array<{
    conversation_id: string;
    feedback: "positive" | "negative";
    comment: string;
    timestamp: string;
    question_preview: string;
  }>;
}

// Interface pour le rapport admin feedback
export interface AdminFeedbackReport {
  period_days: number;
  generated_at: string;
  summary: {
    total_conversations: number;
    total_feedback: number;
    satisfaction_rate: number;
    feedback_rate: number;
    comment_rate: number;
    avg_response_time_ms?: number;
  };
  feedback_breakdown: {
    positive: number;
    negative: number;
    with_comment: number;
  };
  language_stats: Array<{
    language: string;
    total: number;
    positive: number;
    negative: number;
    with_comment: number;
    satisfaction_rate: number;
  }>;
  top_negative_feedback: Array<{
    question: string;
    comment: string;
    timestamp: string;
    language: string;
  }>;
  top_positive_feedback: Array<{
    question: string;
    comment: string;
    timestamp: string;
    language: string;
  }>;
  most_active_users: Array<{
    user_id: string;
    total_conversations: number;
    feedback_given: number;
    comments_given: number;
    engagement_rate: number;
  }>;
}

// Interface pour les statistiques utilisateur
export interface UserFeedbackStats {
  user_id: string;
  total_conversations: number;
  feedback_given: number;
  comments_given: number;
  positive_feedback: number;
  negative_feedback: number;
  engagement_rate: number;
  avg_comment_length?: number;
  last_feedback_date?: string;
}

// ==================== TYPES HOOKS AVEC CONVERSATIONS ====================

// INTERFACE AuthStore COMPLÈTE AVEC TOUTES LES PROPRIÉTÉS
export interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  hasHydrated: boolean; // Pour éviter l'erreur TypeScript
  logout: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    userData?: Partial<User>,
  ) => Promise<void>;
  updateProfile: (
    data: ProfileUpdateData,
  ) => Promise<{ success: boolean; error?: string }>;
  initializeSession: () => Promise<boolean>;

  // NOUVEAU: Méthodes pour session tracking
  startSessionTracking: (sessionId: string) => void;
  endSessionTracking: (
    logoutType?: "manual" | "browser_close" | "timeout",
  ) => Promise<void>;
  updateSessionActivity: () => Promise<void>;
}

// ChatStore pour gérer les conversations
export interface ChatStore {
  // PROPRIÉTÉS EXISTANTES
  conversations: ConversationItem[];
  isLoading: boolean;
  loadConversations: (userId: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  clearAllConversations: (userId?: string) => Promise<void>;
  refreshConversations: (userId: string) => Promise<void>;
  addConversation: (
    conversationId: string,
    question: string,
    response: string,
  ) => void;

  // PROPRIÉTÉS POUR CONVERSATIONS STYLE CLAUDE.AI
  conversationGroups: ConversationGroup[];
  currentConversation: ConversationWithMessages | null;
  isLoadingHistory: boolean;
  isLoadingConversation: boolean;
  loadConversation: (conversationId: string) => Promise<void>;
  createNewConversation: () => void;
  addMessage: (message: Message) => void;
  updateMessage: (messageId: string, updates: Partial<Message>) => void;
  setCurrentConversation: (
    conversation: ConversationWithMessages | null,
  ) => void;
}

export interface Translation {
  t: (key: string) => string;
  changeLanguage: (lang: string) => void;
  currentLanguage: string;
}

// ==================== TYPES COMPOSANTS ====================

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export interface UserInfoModalProps {
  user: User | null;
  onClose: () => void;
}

export interface IconProps {
  className?: string;
}

// ============================================================================
// LANGUAGE & INTERNATIONALIZATION - UNIFIÉ
// ============================================================================

export type Language = "fr" | "en" | "es" | "pt" | "de" | "nl" | "pl";

export interface LanguageOption {
  code: Language;
  name: string;
  flag: string;
}

// ============================================================================
// PETIT FICHIER - TYPES EXPERT SYSTEM
// ============================================================================

export interface ExpertQuestion {
  content: string;
  language: Language;
  context?: string;
  conversation_id?: string;
}

export interface ExpertResponse {
  id: string;
  content: string;
  sources: DocumentSource[];
  confidence_score: number;
  response_time: number;
  model_used: string;
  suggestions?: string[];
  clarification_needed?: boolean;
}

export interface TopicSuggestion {
  id: string;
  title: string;
  description: string;
  category: "health" | "nutrition" | "environment" | "general";
  icon: string;
  popular: boolean;
}

export interface DocumentSource {
  id: string;
  title: string;
  excerpt: string;
  relevance_score: number;
  document_type: string;
  url?: string;
}

export interface MessageMetadata {
  response_time?: number;
  model_used?: string;
  confidence_score?: number;
  language_detected?: Language;
}

export interface UsageAnalytics {
  daily_questions: number;
  satisfaction_rate: number;
  avg_response_time: number;
  popular_topics: string[];
  user_retention: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  metadata?: {
    pagination?: {
      page: number;
      per_page: number;
      total: number;
      total_pages: number;
    };
    timestamp: string;
  };
}

export interface RGPDConsent {
  analytics: boolean;
  marketing: boolean;
  functional: boolean;
  given_at: string;
  ip_address?: string;
}

export interface DataExportRequest {
  user_id: string;
  request_date: string;
  status: "pending" | "processing" | "ready" | "expired";
  download_url?: string;
  expires_at?: string;
}

export interface DataDeletionRequest {
  user_id: string;
  request_date: string;
  scheduled_deletion: string;
  status: "pending" | "confirmed" | "completed";
}

export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
  user_id?: string;
  context?: string;
}

// ==================== TYPES API ====================

export interface ApiError extends Error {
  status?: number;
}

export class AuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthError";
  }
}

export class TimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TimeoutError";
  }
}

// ==================== TYPES MANQUANTS POUR useAuthStore ====================

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  hasHydrated: boolean;
}

export interface BackendUserData {
  id?: string; // Version gros fichier
  user_id?: string; // Version petit fichier
  email: string;
  name?: string;
  full_name?: string;
  firstName?: string;
  lastName?: string;
  user_type?: string;
  created_at?: string;
  updated_at?: string;
  language?: string;
  plan?: string;
  country_code?: string;
  area_code?: string;
  phone_number?: string;
  country?: string;
  linkedinProfile?: string;
  companyName?: string;
  companyWebsite?: string;
  linkedinCorporate?: string;
  avatar_url?: string;
  consent_given?: boolean;
  consent_date?: string;
  profile_id?: string;
  preferences?: Record<string, any>;
  is_admin?: boolean;
  iss?: string;
  aud?: string;
  exp?: number;
  jwt_secret_used?: string;
}

export const mapBackendUserToUser = (backendUser: BackendUserData): User => {
  // Récupérer l'ID (priorité user_id puis id)
  const userId = backendUser.user_id || backendUser.id || "";

  // Récupérer le nom (priorité name, puis full_name, puis construction firstName+lastName)
  const userName =
    backendUser.name ||
    backendUser.full_name ||
    `${backendUser.firstName || ""} ${backendUser.lastName || ""}`.trim() ||
    backendUser.email ||
    "";

  return {
    id: userId,
    email: backendUser.email || "",
    name: userName,
    firstName: backendUser.firstName || "",
    lastName: backendUser.lastName || "",
    phone: `${backendUser.country_code || ""}${backendUser.area_code || ""}${backendUser.phone_number || ""}`,
    country: backendUser.country || "",
    linkedinProfile: backendUser.linkedinProfile || "",
    companyName: backendUser.companyName || "",
    companyWebsite: backendUser.companyWebsite || "",
    linkedinCorporate: backendUser.linkedinCorporate || "",
    user_type: backendUser.user_type || "producer",
    language: (backendUser.language as Language) || "fr",
    created_at: backendUser.created_at || new Date().toISOString(),
    plan: backendUser.plan || "essential",

    // Champs optionnels
    country_code: backendUser.country_code,
    area_code: backendUser.area_code,
    phone_number: backendUser.phone_number,
    full_name: backendUser.full_name,
    avatar_url: backendUser.avatar_url,
    consent_given: backendUser.consent_given ?? true,
    consent_date: backendUser.consent_date,
    updated_at: backendUser.updated_at,
    user_id: backendUser.user_id,
    profile_id: backendUser.profile_id,
    preferences: backendUser.preferences,
    is_admin: backendUser.is_admin || false,
  };
};

// ==================== CONSTANTES API SÉCURISÉES ====================
// Configuration API dynamique depuis environnement
const getApiConfig = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const version = process.env.NEXT_PUBLIC_API_VERSION || "v1";

  if (!baseUrl) {
    console.error("NEXT_PUBLIC_API_BASE_URL environment variable missing");
    return {
      BASE_URL: "https://expert.intelia.com", // Fallback développement
      TIMEOUT: 30000,
      LOGGING_BASE_URL: "https://expert.intelia.com/api/v1",
      LLM_BASE_URL: "https://expert.intelia.com/llm", // ✅ NOUVEAU: URL directe LLM
    };
  }

  // CORRECTION: Enlever /api s'il est déjà présent pour éviter /api/api/
  const cleanBaseUrl = baseUrl.replace(/\/api\/?$/, "");

  return {
    BASE_URL: cleanBaseUrl, // URL de base nettoyée
    TIMEOUT: 30000,
    LOGGING_BASE_URL: `${cleanBaseUrl}/api/${version}`, // Construction correcte
    LLM_BASE_URL: `${cleanBaseUrl}/llm`, // ✅ NOUVEAU: URL directe LLM
  };
};

export const API_CONFIG = getApiConfig();

// ENDPOINTS FEEDBACK
export const FEEDBACK_ENDPOINTS = {
  SAVE_CONVERSATION: "/logging/conversation",
  UPDATE_FEEDBACK: "/logging/conversation/{id}/feedback",
  UPDATE_COMMENT: "/logging/conversation/{id}/comment",
  UPDATE_FEEDBACK_WITH_COMMENT:
    "/logging/conversation/{id}/feedback-with-comment",
  GET_USER_CONVERSATIONS: "/logging/user/{id}/conversations",
  DELETE_CONVERSATION: "/logging/conversation/{id}",
  DELETE_ALL_USER_CONVERSATIONS: "/logging/user/{id}/conversations",
  GET_FEEDBACK_ANALYTICS: "/logging/analytics/feedback",
  GET_CONVERSATIONS_WITH_COMMENTS: "/logging/conversations/with-comments",
  GET_ADMIN_FEEDBACK_REPORT: "/logging/admin/feedback-report",
  EXPORT_FEEDBACK_DATA: "/logging/admin/export-feedback",
  TEST_COMMENT_SUPPORT: "/logging/test-comments",
} as const;

// NOUVEAU: ENDPOINTS SESSION TRACKING
export const SESSION_ENDPOINTS = {
  HEARTBEAT: "/auth/heartbeat",
  LOGOUT: "/auth/logout",
  MY_SESSION_ANALYTICS: "/logging/analytics/my-sessions",
  SESSION_STATS: "/logging/analytics/session-stats",
  DAILY_PATTERNS: "/logging/analytics/daily-patterns",
} as const;

export const PLAN_CONFIGS = {
  essential: {
    name: "Essentiel",
    color: "text-green-600",
    bgColor: "bg-green-50",
    borderColor: "border-green-200",
    features: [
      "50 questions par mois",
      "Accès aux documents publics",
      "Support par email",
      "Interface web",
    ],
  },
  pro: {
    name: "Pro",
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
    features: [
      "Questions illimitées",
      "Accès documents confidentiels",
      "Support prioritaire",
      "Interface web + mobile",
      "Analytics avancées",
    ],
  },
} as const;

// CONFIGURATION FEEDBACK
export const FEEDBACK_CONFIG = {
  TYPES: {
    POSITIVE: {
      value: "positive" as const,
      label: "Utile",
      icon: "👍",
      color: "text-green-600",
      bgColor: "bg-green-50",
      description: "Cette réponse m'a été utile",
    },
    NEGATIVE: {
      value: "negative" as const,
      label: "Pas utile",
      icon: "👎",
      color: "text-red-600",
      bgColor: "bg-red-50",
      description: "Cette réponse pourrait être améliorée",
    },
  },
  COMMENT_PLACEHOLDERS: {
    positive: "Qu'avez-vous apprécié dans cette réponse ?",
    negative: "Dans quelle mesure cette réponse était-elle satisfaisante ?",
  },
  MODAL_TITLES: {
    positive: "Merci pour votre feedback positif !",
    negative: "Aidez-nous à améliorer",
  },
  MAX_COMMENT_LENGTH: 500,
  MIN_COMMENT_LENGTH: 0,
  PRIVACY_POLICY_URL: "https://intelia.com/privacy-policy/",
} as const;

// CONFIGURATION DES CLARIFICATIONS
export const CLARIFICATION_TEXTS = {
  fr: {
    title: "Informations supplémentaires requises",
    subtitle:
      "Pour vous donner la meilleure réponse, veuillez répondre à ces questions :",
    placeholder: "Tapez votre réponse ici...",
    submit: "Obtenir ma réponse",
    skip: "Passer et obtenir une réponse générale",
    optional: "(optionnel)",
    required: "Répondez à au moins la moitié des questions",
    processing: "Traitement en cours...",
    validationError: "Veuillez répondre à au moins {count} questions",
  },
  en: {
    title: "Additional information required",
    subtitle: "To give you the best answer, please answer these questions:",
    placeholder: "Type your answer here...",
    submit: "Get my answer",
    skip: "Skip and get a general answer",
    optional: "(optional)",
    required: "Answer at least half of the questions",
    processing: "Processing...",
    validationError: "Please answer at least {count} questions",
  },
  es: {
    title: "Información adicional requerida",
    subtitle:
      "Para darle la mejor respuesta, por favor responda estas preguntas:",
    placeholder: "Escriba su respuesta aquí...",
    submit: "Obtener mi respuesta",
    skip: "Omitir y obtener una respuesta general",
    optional: "(opcional)",
    required: "Responda al menos la mitad de las preguntas",
    processing: "Procesando...",
    validationError: "Por favor responda al menos {count} preguntas",
  },
} as const;

export const CLARIFICATION_CONFIG = {
  MAX_QUESTIONS: 4,
  MIN_ANSWER_LENGTH: 0,
  MAX_ANSWER_LENGTH: 200,
  REQUIRED_ANSWER_PERCENTAGE: 0.5, // 50% des questions doivent être répondues
  AUTO_SCROLL_DELAY: 300,
  VALIDATION_DEBOUNCE: 500,
} as const;

// NOUVELLE: CONFIGURATION POUR CONCISION BACKEND
export const CONCISION_CONFIG = {
  LEVELS: {
    ULTRA_CONCISE: {
      value: "ultra_concise" as const,
      label: "Minimal",
      icon: "⚡",
      description: "Juste l'essentiel",
      example: "Données clés uniquement",
    },
    CONCISE: {
      value: "concise" as const,
      label: "Concis",
      icon: "🎯",
      description: "Information principale avec contexte",
      example: "Réponse courte avec explication essentielle",
    },
    STANDARD: {
      value: "standard" as const,
      label: "Standard",
      icon: "📄",
      description: "Réponse équilibrée avec conseils",
      example: "Réponse complète sans détails techniques",
    },
    DETAILED: {
      value: "detailed" as const,
      label: "Détaillé",
      icon: "📚",
      description: "Réponse complète avec explications",
      example: "Réponse exhaustive avec conseils détaillés",
    },
  },
  DEFAULT_LEVEL: "concise" as const,
  AUTO_DETECT: true,
  SAVE_PREFERENCE: true,
  STORAGE_KEY: "intelia_concision_level",
} as const;

// NOUVELLE: CONFIGURATION POUR AD SYSTEM
export const AD_CONFIG = {
  // Critères de déclenchement
  TRIGGERS: {
    MIN_SESSIONS: 2,
    MIN_DURATION_PER_SESSION: 60, // 1 minute en secondes
    COOLDOWN_PERIOD: 24, // 24 heures
    CHECK_INTERVAL: 5 * 60 * 1000, // 5 minutes en ms
    INITIAL_CHECK_DELAY: 3000, // 3 secondes après connexion
  },

  // Configuration de l'affichage
  DISPLAY: {
    MIN_SHOW_TIME: 15, // 15 secondes minimum
    FADE_DURATION: 200, // Animation en ms
    Z_INDEX: 50, // z-index de la modal
  },

  // Types de publicités disponibles
  AD_TYPES: {
    FARMING_TOOLS: {
      id: "farming-tools",
      weight: 40,
      targetAudience: "agricultural",
      category: "productivity",
    },
    BUSINESS_SOFTWARE: {
      id: "business-software",
      weight: 30,
      targetAudience: "professional",
      category: "software",
    },
    EDUCATIONAL: {
      id: "educational",
      weight: 20,
      targetAudience: "learning",
      category: "education",
    },
    PREMIUM_FEATURES: {
      id: "premium-features",
      weight: 10,
      targetAudience: "power-user",
      category: "upgrade",
    },
  },

  // Configuration de stockage
  STORAGE: {
    LAST_AD_SHOWN_KEY: "lastAdShown",
    USER_PREFERENCES_KEY: "adPreferences",
    SESSION_TRACKING_KEY: "sessionTracking",
  },

  // URLs et endpoints
  ENDPOINTS: {
    SESSION_ANALYTICS: "/analytics/my-sessions",
    AD_EVENTS: "/logging/ad-events", // Optionnel
  },
} as const;

// NOUVELLE: CONFIGURATION POUR SESSION TRACKING
export const SESSION_CONFIG = {
  HEARTBEAT_INTERVAL: 2 * 60 * 1000, // 2 minutes en ms
  SESSION_TIMEOUT: 30 * 60, // 30 minutes en secondes
  TRACK_IP_ADDRESS: true,
  TRACK_USER_AGENT: true,
  AUTO_CLEANUP_OLD_SESSIONS: true,
  CLEANUP_AFTER_DAYS: 90,
  STORAGE_KEY: "intelia_session_data",

  LOGOUT_TYPES: {
    MANUAL: "manual" as const,
    BROWSER_CLOSE: "browser_close" as const,
    TIMEOUT: "timeout" as const,
    FORCED: "forced" as const,
  },
} as const;

// UTILITAIRES ANALYTICS
export const ANALYTICS_UTILS = {
  calculateSatisfactionRate: (positive: number, negative: number): number => {
    const total = positive + negative;
    return total > 0 ? Math.round((positive / total) * 1000) / 1000 : 0;
  },

  calculateEngagementRate: (
    feedbackGiven: number,
    totalConversations: number,
  ): number => {
    return totalConversations > 0
      ? Math.round((feedbackGiven / totalConversations) * 1000) / 1000
      : 0;
  },

  calculateCommentRate: (
    withComments: number,
    totalFeedback: number,
  ): number => {
    return totalFeedback > 0
      ? Math.round((withComments / totalFeedback) * 1000) / 1000
      : 0;
  },

  formatPercentage: (rate: number): string => {
    return `${(rate * 100).toFixed(1)}%`;
  },

  truncateText: (text: string, maxLength: number): string => {
    return text.length > maxLength
      ? text.substring(0, maxLength) + "..."
      : text;
  },

  formatTimestamp: (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return timestamp;
    }
  },

  // NOUVEAU: Utilitaires pour sessions
  formatSessionDuration: (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      return `${remainingSeconds}s`;
    }
  },

  calculateAverageSessionDuration: (sessions: UserSession[]): number => {
    if (sessions.length === 0) return 0;
    const totalDuration = sessions.reduce(
      (sum, session) => sum + (session.session_duration_seconds || 0),
      0,
    );
    return Math.round(totalDuration / sessions.length);
  },
} as const;

// UTILITAIRES POUR CLARIFICATIONS
export const ClarificationUtils = {
  isClarificationResponse: (response: ExpertApiResponse): boolean => {
    return (
      response.mode?.includes("clarification_needed") ||
      response.response?.includes("❓") ||
      response.response?.includes("précisions") ||
      response.response?.includes("clarification") ||
      response.response?.includes("aclaraciones") ||
      response.is_clarification_request === true
    );
  },

  extractClarificationQuestions: (response: ExpertApiResponse): string[] => {
    if (response.clarification_questions) {
      return response.clarification_questions;
    }

    const questions: string[] = [];
    const lines = response.response.split("\n");

    for (const line of lines) {
      const cleaned = line.trim();
      if (cleaned.startsWith("• ") || cleaned.startsWith("- ")) {
        const question = cleaned.replace(/^[•-]\s*/, "").trim();
        if (question.length > 5) {
          questions.push(question);
        }
      }
    }

    return questions;
  },

  buildEnrichedQuestion: (
    originalQuestion: string,
    clarificationAnswers: Record<string, string>,
    clarificationQuestions: string[],
  ): string => {
    let enrichedQuestion =
      originalQuestion + "\n\nInformations supplémentaires :";

    Object.entries(clarificationAnswers).forEach(([index, answer]) => {
      if (answer && answer.trim()) {
        try {
          const questionIndex = parseInt(index);
          if (
            questionIndex >= 0 &&
            questionIndex < clarificationQuestions.length
          ) {
            const question = clarificationQuestions[questionIndex];
            enrichedQuestion += `\n- ${question}: ${answer.trim()}`;
          }
        } catch {
          // Ignorer les index invalides
        }
      }
    });

    return enrichedQuestion;
  },

  validateClarificationAnswers: (
    answers: Record<string, string>,
    questions: string[],
  ): { isValid: boolean; requiredCount: number; answeredCount: number } => {
    const answeredCount = Object.values(answers).filter(
      (a) => a && a.trim().length > 0,
    ).length;
    const requiredCount = Math.ceil(questions.length * 0.5); // Au moins 50% des questions

    return {
      isValid: answeredCount >= requiredCount,
      requiredCount,
      answeredCount,
    };
  },
} as const;

// NOUVEAUX: UTILITAIRES POUR CONCISION BACKEND
export const ConcisionUtils = {
  selectVersionFromResponse: (
    responseVersions: Record<string, string>,
    level: ConcisionLevel,
  ): string => {
    // Retourner la version demandée si elle existe
    if (responseVersions[level]) {
      return responseVersions[level];
    }

    // Fallback intelligent si version manquante
    const fallbackOrder: ConcisionLevel[] = [
      ConcisionLevel.DETAILED,
      ConcisionLevel.STANDARD,
      ConcisionLevel.CONCISE,
      ConcisionLevel.ULTRA_CONCISE,
    ];

    for (const fallbackLevel of fallbackOrder) {
      if (responseVersions[fallbackLevel]) {
        console.warn(
          `⚠️ [ConcisionUtils] Fallback vers ${fallbackLevel} (${level} manquant)`,
        );
        return responseVersions[fallbackLevel];
      }
    }

    // Ultime fallback - première version disponible
    const firstAvailable = Object.values(responseVersions)[0];
    console.warn(
      "⚠️ [ConcisionUtils] Aucune version standard - utilisation première disponible",
    );
    return firstAvailable || "Réponse non disponible";
  },

  validateResponseVersions: (responseVersions: any): boolean => {
    if (!responseVersions || typeof responseVersions !== "object") {
      return false;
    }

    const requiredLevels = [
      ConcisionLevel.ULTRA_CONCISE,
      ConcisionLevel.CONCISE,
      ConcisionLevel.STANDARD,
      ConcisionLevel.DETAILED,
    ];

    // Vérifier qu'au moins une version est présente
    const hasAnyVersion = requiredLevels.some(
      (level) =>
        responseVersions[level] && typeof responseVersions[level] === "string",
    );

    return hasAnyVersion;
  },

  detectOptimalLevel: (question: string): ConcisionLevel => {
    const questionLower = question.toLowerCase();

    // Questions ultra-concises (poids, température, mesures simples)
    const ultraConciseKeywords = [
      "poids",
      "weight",
      "peso",
      "température",
      "temperature",
      "temperatura",
      "combien",
      "how much",
      "cuánto",
      "quel est",
      "what is",
      "cuál es",
      "quelle est",
      "âge",
      "age",
    ];

    if (
      ultraConciseKeywords.some((keyword) => questionLower.includes(keyword))
    ) {
      return ConcisionLevel.ULTRA_CONCISE;
    }

    // Questions complexes (comment, pourquoi, procédures)
    const complexKeywords = [
      "comment",
      "how to",
      "cómo",
      "pourquoi",
      "why",
      "por qué",
      "expliquer",
      "explain",
      "explicar",
      "procédure",
      "procedure",
      "procedimiento",
      "diagnostic",
      "diagnosis",
      "diagnóstico",
      "traitement",
      "treatment",
      "tratamiento",
    ];

    if (complexKeywords.some((keyword) => questionLower.includes(keyword))) {
      return ConcisionLevel.DETAILED;
    }

    // Par défaut: concis pour questions générales
    return ConcisionLevel.CONCISE;
  },

  analyzeResponseComplexity: (
    response: string,
  ): {
    wordCount: number;
    sentenceCount: number;
    hasNumbers: boolean;
    hasAdvice: boolean;
    complexity: "simple" | "moderate" | "complex";
  } => {
    const wordCount = response.split(/\s+/).length;
    const sentenceCount = response
      .split(".")
      .filter((s) => s.trim().length > 0).length;
    const hasNumbers = /\d+/.test(response);

    const adviceKeywords = [
      "recommandé",
      "essentiel",
      "important",
      "devrait",
      "doit",
      "recommended",
      "essential",
      "important",
      "should",
      "must",
      "recomendado",
      "esencial",
      "importante",
      "debería",
      "debe",
    ];
    const hasAdvice = adviceKeywords.some((keyword) =>
      response.toLowerCase().includes(keyword),
    );

    let complexity: "simple" | "moderate" | "complex" = "simple";
    if (wordCount > 100 || sentenceCount > 3) complexity = "moderate";
    if (wordCount > 200 || sentenceCount > 6) complexity = "complex";

    return {
      wordCount,
      sentenceCount,
      hasNumbers,
      hasAdvice,
      complexity,
    };
  },

  debugResponseVersions: (responseVersions: Record<string, string>): void => {
    console.group("🔍 [ConcisionUtils] Versions disponibles");
    Object.entries(responseVersions).forEach(([level, content]) => {
      console.log(`${level}: ${content?.length || 0} caractères`);
      if (content) {
        console.log(`  Aperçu: "${content.substring(0, 50)}..."`);
      }
    });
    console.groupEnd();
  },
} as const;

// NOUVEAUX: UTILITAIRES POUR AD SYSTEM
export const AdSystemUtils = {
  // Vérifier l'éligibilité pour les publicités
  checkAdEligibility: (
    sessionStats: UserSessionStats,
    criteria: AdTriggerCriteria,
  ): boolean => {
    // Vérifier les critères de sessions
    const meetsSessionCriteria =
      sessionStats.totalSessions >= criteria.MIN_SESSIONS;
    const meetsDurationCriteria =
      sessionStats.averageSessionDuration >= criteria.MIN_DURATION_PER_SESSION;

    // Vérifier le cooldown
    const lastAdTime = sessionStats.lastAdShown
      ? new Date(sessionStats.lastAdShown)
      : null;
    const now = new Date();
    const cooldownExpired =
      !lastAdTime ||
      now.getTime() - lastAdTime.getTime() >
        criteria.COOLDOWN_PERIOD * 60 * 60 * 1000;

    return meetsSessionCriteria && meetsDurationCriteria && cooldownExpired;
  },

  // Générer une publicité personnalisée selon le profil utilisateur
  generatePersonalizedAd: (userProfile?: User): AdData => {
    // Logic basique de personnalisation - en production, serait plus sophistiquée
    const baseAd: AdData = {
      id: "farming-pro-2024",
      title: "FarmPro Analytics",
      description:
        "Optimisez vos performances agricoles avec notre plateforme IA spécialisée en élevage avicole. Analyses prédictives, suivi en temps réel et conseils personnalisés pour maximiser vos rendements.",
      imageUrl: "/images/logo.png",
      ctaText: "Essai gratuit 30 jours",
      ctaUrl: "https://farmpro-analytics.com/trial?ref=intelia",
      company: "FarmPro Solutions",
      rating: 4.8,
      users: "10K+",
      duration: "Essai gratuit",
      features: [
        "Analyses prédictives IA",
        "Suivi temps réel",
        "Rapports automatisés",
        "Support expert 24/7",
        "Intégration IoT",
        "Mobile & desktop",
      ],
    };

    // Personnalisation selon le type d'utilisateur
    if (userProfile?.user_type === "veterinary") {
      baseAd.title = "VetPro Clinical";
      baseAd.description =
        "Plateforme de diagnostic vétérinaire avicole avec IA. Aide au diagnostic, base de données médicamenteuse et suivi clinique intégré.";
      baseAd.features = [
        "Aide au diagnostic IA",
        "Base médicamenteuse",
        "Dossiers patients",
        "Analyses laboratoire",
        "Protocoles standards",
        "Téléconsultation",
      ];
    }

    return baseAd;
  },

  // Valider les données de session
  validateSessionStats: (data: any): data is UserSessionStats => {
    return (
      typeof data === "object" &&
      data !== null &&
      typeof data.totalSessions === "number" &&
      typeof data.averageSessionDuration === "number" &&
      typeof data.qualifiesForAd === "boolean"
    );
  },

  // Logger les événements publicitaires (version locale)
  logAdEvent: (
    event: string,
    adId?: string,
    sessionData?: UserSessionStats,
  ): void => {
    const eventData: AdEventData = {
      event: event as AdEventData["event"],
      ad_id: adId,
      timestamp: new Date().toISOString(),
      user_agent: navigator.userAgent,
      session_data: sessionData
        ? {
            totalSessions: sessionData.totalSessions,
            averageSessionDuration: sessionData.averageSessionDuration,
          }
        : undefined,
    };

    // Log local pour debug
    console.log("📊 [AdSystem] Event:", eventData);

    // En production, pourrait envoyer à un service d'analytics
    try {
      const existingLogs = localStorage.getItem("adEventLogs");
      const logs = existingLogs ? JSON.parse(existingLogs) : [];
      logs.push(eventData);

      // Garder seulement les 100 derniers événements
      if (logs.length > 100) {
        logs.splice(0, logs.length - 100);
      }

      localStorage.setItem("adEventLogs", JSON.stringify(logs));
    } catch (error) {
      console.warn("Erreur lors du stockage des logs publicitaires:", error);
    }
  },

  // Calculer le temps restant avant la prochaine publicité
  getTimeUntilNextAd: (
    lastAdShown?: string,
    cooldownHours: number = 24,
  ): number => {
    if (!lastAdShown) return 0;

    const lastAdTime = new Date(lastAdShown);
    const now = new Date();
    const cooldownMs = cooldownHours * 60 * 60 * 1000;
    const elapsed = now.getTime() - lastAdTime.getTime();

    return Math.max(0, cooldownMs - elapsed);
  },

  // Formater le temps restant en format lisible
  formatTimeRemaining: (milliseconds: number): string => {
    const hours = Math.floor(milliseconds / (1000 * 60 * 60));
    const minutes = Math.floor((milliseconds % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m`;
    } else {
      return "Bientôt disponible";
    }
  },
} as const;

// NOUVEAUX: UTILITAIRES POUR SESSION TRACKING
export const SessionUtils = {
  // Générer un ID de session unique
  generateSessionId: (): string => {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  },

  // Calculer la durée d'une session
  calculateSessionDuration: (
    loginTime: string,
    logoutTime?: string,
  ): number => {
    const start = new Date(loginTime);
    const end = logoutTime ? new Date(logoutTime) : new Date();
    return Math.floor((end.getTime() - start.getTime()) / 1000);
  },

  // Détecter le type de déconnexion selon le contexte
  detectLogoutType: (
    userAgent: string,
    sessionDuration: number,
  ): "manual" | "browser_close" | "timeout" => {
    // Session très courte = probablement fermeture navigateur
    if (sessionDuration < 30) {
      return "browser_close";
    }

    // Session très longue = probablement timeout
    if (sessionDuration > SESSION_CONFIG.SESSION_TIMEOUT) {
      return "timeout";
    }

    // Par défaut: déconnexion manuelle
    return "manual";
  },

  // Nettoyer les sessions expirées
  cleanupExpiredSessions: (sessions: UserSession[]): UserSession[] => {
    const cutoffDate = new Date();
    cutoffDate.setDate(
      cutoffDate.getDate() - SESSION_CONFIG.CLEANUP_AFTER_DAYS,
    );

    return sessions.filter((session) => {
      const sessionDate = new Date(session.login_time);
      return sessionDate > cutoffDate;
    });
  },

  // Valider les données de session
  validateSessionData: (session: any): session is UserSession => {
    return (
      typeof session === "object" &&
      session !== null &&
      typeof session.user_email === "string" &&
      typeof session.session_id === "string" &&
      typeof session.login_time === "string" &&
      typeof session.last_activity === "string"
    );
  },

  // Grouper les sessions par période
  groupSessionsByPeriod: (
    sessions: UserSession[],
  ): Record<string, UserSession[]> => {
    const groups: Record<string, UserSession[]> = {
      today: [],
      yesterday: [],
      thisWeek: [],
      thisMonth: [],
      older: [],
    };

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const thisWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    const thisMonth = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

    sessions.forEach((session) => {
      const sessionDate = new Date(session.login_time);

      if (sessionDate >= today) {
        groups.today.push(session);
      } else if (sessionDate >= yesterday) {
        groups.yesterday.push(session);
      } else if (sessionDate >= thisWeek) {
        groups.thisWeek.push(session);
      } else if (sessionDate >= thisMonth) {
        groups.thisMonth.push(session);
      } else {
        groups.older.push(session);
      }
    });

    return groups;
  },
} as const;

// TYPE GUARDS POUR LA VALIDATION
export const TypeGuards = {
  isFeedbackType: (value: any): value is "positive" | "negative" => {
    return (
      typeof value === "string" && ["positive", "negative"].includes(value)
    );
  },

  // NOUVEAU: Type guard pour ConcisionLevel
  isConcisionLevel: (value: any): value is ConcisionLevel => {
    return (
      typeof value === "string" &&
      Object.values(ConcisionLevel).includes(value as ConcisionLevel)
    );
  },

  // NOUVEAU: Type guard pour response_versions
  isValidResponseVersions: (value: any): value is Record<string, string> => {
    if (!value || typeof value !== "object") return false;
    return Object.values(ConcisionLevel).some(
      (level) => value[level] && typeof value[level] === "string",
    );
  },

  // NOUVEAU: Type guard pour AgentMetadata
  isValidAgentMetadata: (value: any): value is AgentMetadata => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.complexity === "string" &&
      typeof value.sub_queries_count === "number" &&
      typeof value.synthesis_method === "string" &&
      typeof value.sources_used === "number"
    );
  },

  // NOUVEAUX: Type guards pour Ad System
  isValidAdData: (value: any): value is AdData => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.id === "string" &&
      typeof value.title === "string" &&
      typeof value.description === "string" &&
      typeof value.ctaText === "string" &&
      typeof value.ctaUrl === "string" &&
      typeof value.company === "string" &&
      Array.isArray(value.features)
    );
  },

  isValidUserSessionStats: (value: any): value is UserSessionStats => {
    return AdSystemUtils.validateSessionStats(value);
  },

  isValidAdEventData: (value: any): value is AdEventData => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.event === "string" &&
      typeof value.timestamp === "string" &&
      ["ad_shown", "ad_clicked", "ad_closed", "ad_error"].includes(value.event)
    );
  },

  // NOUVEAUX: Type guards pour Session Tracking
  isValidUserSession: (value: any): value is UserSession => {
    return SessionUtils.validateSessionData(value);
  },

  isValidSessionAnalytics: (value: any): value is SessionAnalytics => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.user_email === "string" &&
      typeof value.period_days === "number" &&
      typeof value.total_sessions === "number" &&
      typeof value.total_connection_time_seconds === "number" &&
      typeof value.average_session_duration_seconds === "number"
    );
  },

  isValidLogoutType: (
    value: any,
  ): value is "manual" | "browser_close" | "timeout" | "forced" => {
    return (
      typeof value === "string" &&
      ["manual", "browser_close", "timeout", "forced"].includes(value)
    );
  },

  isValidMessage: (value: any): value is Message => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.id === "string" &&
      typeof value.content === "string" &&
      typeof value.isUser === "boolean" &&
      value.timestamp instanceof Date
    );
  },

  isValidUser: (value: any): value is User => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.id === "string" &&
      typeof value.email === "string"
    );
  },

  // TYPE GUARD POUR CONVERSATION DE BASE
  isValidConversation: (value: any): value is Conversation => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.id === "string" &&
      typeof value.title === "string" &&
      typeof value.preview === "string" &&
      typeof value.message_count === "number"
    );
  },

  // Type guard pour ConversationWithMessages
  isValidConversationWithMessages: (
    value: any,
  ): value is ConversationWithMessages => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.id === "string" &&
      typeof value.title === "string" &&
      typeof value.preview === "string" &&
      typeof value.message_count === "number" &&
      Array.isArray(value.messages) &&
      value.messages.every((msg: any) => TypeGuards.isValidMessage(msg))
    );
  },

  isValidConversationGroup: (value: any): value is ConversationGroup => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.title === "string" &&
      Array.isArray(value.conversations) &&
      value.conversations.every((conv: any) =>
        TypeGuards.isValidConversation(conv),
      )
    );
  },

  // Type guard pour clarifications
  isValidClarificationResponse: (
    value: any,
  ): value is ClarificationResponse => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.needs_clarification === "boolean"
    );
  },

  // Type guard pour StreamCallbacks
  isValidStreamCallbacks: (value: any): value is StreamCallbacks => {
    return typeof value === "object" && value !== null;
  },

  // Type guard pour StreamEvent
  isValidStreamEvent: (value: any): value is StreamEvent => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.type === "string"
    );
  },
} as const;

// CONFIGURATION DES CONVERSATIONS
export const CONVERSATION_CONFIG = {
  GROUPING: {
    DEFAULT_OPTIONS: {
      groupBy: "date" as const,
      sortBy: "updated_at" as const,
      sortOrder: "desc" as const,
      limit: 50,
    },
    TIME_PERIODS: {
      TODAY: "Aujourd'hui",
      YESTERDAY: "Hier",
      THIS_WEEK: "Cette semaine",
      THIS_MONTH: "Ce mois-ci",
      OLDER: "Plus ancien",
    },
  },
  UI: {
    SIDEBAR_WIDTH: "w-96", // 384px
    MAX_TITLE_LENGTH: 60,
    MAX_PREVIEW_LENGTH: 150,
    MESSAGES_PER_PAGE: 50,
    AUTO_SCROLL_DELAY: 100,
  },
  CACHE: {
    CONVERSATION_LIST_TTL: 5 * 60 * 1000, // 5 minutes
    CONVERSATION_DETAIL_TTL: 10 * 60 * 1000, // 10 minutes
    MAX_CACHED_CONVERSATIONS: 100,
  },
} as const;

// UTILITAIRES POUR CONVERSATIONS
export const CONVERSATION_UTILS = {
  generateTitle: (firstMessage: string): string => {
    const maxLength = CONVERSATION_CONFIG.UI.MAX_TITLE_LENGTH;
    return firstMessage.length > maxLength
      ? firstMessage.substring(0, maxLength) + "..."
      : firstMessage;
  },

  generatePreview: (firstMessage: string): string => {
    const maxLength = CONVERSATION_CONFIG.UI.MAX_PREVIEW_LENGTH;
    return firstMessage.length > maxLength
      ? firstMessage.substring(0, maxLength) + "..."
      : firstMessage;
  },

  formatRelativeTime: (timestamp: string): string => {
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMinutes < 1) return "À l'instant";
    if (diffMinutes < 60) return `Il y a ${diffMinutes}m`;
    if (diffHours < 24) return `Il y a ${diffHours}h`;
    if (diffDays < 7) return `Il y a ${diffDays}j`;
    return ANALYTICS_UTILS.formatTimestamp(timestamp);
  },

  sortConversations: (
    conversations: Conversation[],
    sortBy: "updated_at" | "created_at" | "message_count" = "updated_at",
  ): Conversation[] => {
    return [...conversations].sort((a, b) => {
      switch (sortBy) {
        case "message_count":
          return b.message_count! - a.message_count!;
        case "created_at":
          return (
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          );
        case "updated_at":
        default:
          return (
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
          );
      }
    });
  },

  groupConversationsByDate: (
    conversations: Conversation[],
  ): ConversationGroup[] => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const thisWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    const thisMonth = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

    const groups: ConversationGroup[] = [
      {
        title: CONVERSATION_CONFIG.GROUPING.TIME_PERIODS.TODAY,
        conversations: [],
      },
      {
        title: CONVERSATION_CONFIG.GROUPING.TIME_PERIODS.YESTERDAY,
        conversations: [],
      },
      {
        title: CONVERSATION_CONFIG.GROUPING.TIME_PERIODS.THIS_WEEK,
        conversations: [],
      },
      {
        title: CONVERSATION_CONFIG.GROUPING.TIME_PERIODS.THIS_MONTH,
        conversations: [],
      },
      {
        title: CONVERSATION_CONFIG.GROUPING.TIME_PERIODS.OLDER,
        conversations: [],
      },
    ];

    conversations.forEach((conversation) => {
      const convDate = new Date(conversation.updated_at);

      if (convDate >= today) {
        groups[0].conversations.push(conversation);
      } else if (convDate >= yesterday) {
        groups[1].conversations.push(conversation);
      } else if (convDate >= thisWeek) {
        groups[2].conversations.push(conversation);
      } else if (convDate >= thisMonth) {
        groups[3].conversations.push(conversation);
      } else {
        groups[4].conversations.push(conversation);
      }
    });

    // Retourner seulement les groupes non vides
    return groups.filter((group) => group.conversations.length > 0);
  },
} as const;

// NOUVEAUX: TYPES POUR LES RÉPONSES D'API AGENT
export interface AgentApiResponse {
  status: "success" | "error";
  response?: string;
  conversation_id?: string;
  agent_metadata?: AgentMetadata;
  processing_time_ms?: number;
  message?: string;
  timestamp: string;
}

export interface LLMHealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  services: {
    rag_engine: boolean;
    embedder: boolean;
    weaviate: boolean;
    llm_backend: boolean;
  };
  diagnostics?: Record<string, any>;
  timestamp: string;
}

// NOUVELLES CONSTANTES POUR AGENT LLM
export const AGENT_CONFIG = {
  COMPLEXITY_LEVELS: {
    SIMPLE: "simple",
    MODERATE: "moderate",
    COMPLEX: "complex",
    ADVANCED: "advanced",
  },
  SYNTHESIS_METHODS: {
    DIRECT: "direct",
    MULTI_SOURCE: "multi_source",
    ITERATIVE: "iterative",
    COLLABORATIVE: "collaborative",
  },
  DEFAULT_SETTINGS: {
    MAX_SUB_QUERIES: 5,
    CONFIDENCE_THRESHOLD: 0.7,
    SOURCES_LIMIT: 10,
    PROCESSING_TIMEOUT: 30000, // 30 secondes
  },
} as const;

// NOUVEAUX: UTILITAIRES POUR AGENT
export const AgentUtils = {
  formatComplexity: (complexity: string): string => {
    const complexityMap: Record<string, string> = {
      simple: "Simple",
      moderate: "Modéré",
      complex: "Complexe",
      advanced: "Avancé",
    };
    return complexityMap[complexity] || complexity;
  },

  formatSynthesisMethod: (method: string): string => {
    const methodMap: Record<string, string> = {
      direct: "Direct",
      multi_source: "Multi-sources",
      iterative: "Itératif",
      collaborative: "Collaboratif",
    };
    return methodMap[method] || method;
  },

  validateAgentMetadata: (metadata: any): metadata is AgentMetadata => {
    return TypeGuards.isValidAgentMetadata(metadata);
  },

  getProcessingTimeDisplay: (processingTime?: number): string => {
    if (!processingTime) return "N/A";
    if (processingTime < 1000) return `${processingTime}ms`;
    return `${(processingTime / 1000).toFixed(1)}s`;
  },

  getComplexityColor: (complexity: string): string => {
    const colorMap: Record<string, string> = {
      simple: "text-green-600",
      moderate: "text-yellow-600",
      complex: "text-orange-600",
      advanced: "text-red-600",
    };
    return colorMap[complexity] || "text-gray-600";
  },
} as const;

// CONSTANTES UI
export const UI_CONSTANTS = {
  COLORS: {
    PRIMARY: "blue",
    SUCCESS: "green",
    WARNING: "yellow",
    ERROR: "red",
    INFO: "gray",
  },
  ANIMATIONS: {
    FADE_DURATION: 200,
    SLIDE_DURATION: 300,
    BOUNCE_DURATION: 150,
  },
  BREAKPOINTS: {
    SM: "640px",
    MD: "768px",
    LG: "1024px",
    XL: "1280px",
  },
  Z_INDEX: {
    DROPDOWN: 10,
    STICKY: 20,
    MODAL_BACKDROP: 40,
    MODAL: 50,
    TOAST: 60,
    TOOLTIP: 70,
  },
} as const;

// CONSTANTES DE VALIDATION
export const VALIDATION_RULES = {
  FEEDBACK: {
    COMMENT_MIN_LENGTH: 0,
    COMMENT_MAX_LENGTH: 500,
    REQUIRED_FIELDS: [] as string[], // Aucun champ requis pour le feedback
    ALLOWED_FEEDBACK_TYPES: ["positive", "negative"] as const,
  },
  PHONE: {
    COUNTRY_CODE_PATTERN: /^\+\d{1,4}$/,
    AREA_CODE_PATTERN: /^\d{1,4}$/,
    PHONE_NUMBER_PATTERN: /^\d{4,12}$/,
  },
  // RÈGLES POUR CONVERSATIONS
  CONVERSATION: {
    TITLE_MAX_LENGTH: 60,
    PREVIEW_MAX_LENGTH: 150,
    MESSAGE_MAX_LENGTH: 5000,
    MAX_CONVERSATIONS_PER_USER: 1000,
    AUTO_DELETE_DAYS: 30,
  },
  // RÈGLES POUR CLARIFICATIONS
  CLARIFICATION: {
    MIN_ANSWER_LENGTH: 0,
    MAX_ANSWER_LENGTH: 200,
    MAX_QUESTIONS: 4,
    REQUIRED_ANSWER_PERCENTAGE: 0.5,
  },
  // NOUVELLES: RÈGLES POUR CONCISION
  CONCISION: {
    MIN_RESPONSE_LENGTH: 10,
    MAX_ULTRA_CONCISE_LENGTH: 50,
    MAX_CONCISE_LENGTH: 200,
    MAX_STANDARD_LENGTH: 500,
    // Pas de limite pour DETAILED
    AUTO_DETECT_ENABLED: true,
  },
  // NOUVELLES: RÈGLES POUR AD SYSTEM
  AD_SYSTEM: {
    MIN_SESSIONS_FOR_AD: 2,
    MIN_SESSION_DURATION: 60, // secondes
    COOLDOWN_HOURS: 24,
    MIN_DISPLAY_TIME: 15, // secondes
    MAX_TITLE_LENGTH: 60,
    MAX_DESCRIPTION_LENGTH: 200,
    MAX_FEATURES_COUNT: 8,
  },
  // NOUVELLES: RÈGLES POUR SESSION TRACKING
  SESSION_TRACKING: {
    MIN_SESSION_DURATION: 5, // secondes
    MAX_SESSION_DURATION: 8 * 60 * 60, // 8 heures
    HEARTBEAT_TOLERANCE: 5 * 60, // 5 minutes de tolérance
    MAX_SESSIONS_PER_DAY: 20,
    SESSION_ID_LENGTH: 32,
  },
  // NOUVELLES: RÈGLES POUR AGENT LLM
  AGENT: {
    MIN_PROCESSING_TIME: 100, // ms
    MAX_PROCESSING_TIME: 60000, // 60 secondes
    MAX_SUB_QUERIES: 10,
    MAX_SOURCES: 20,
    MAX_DECISIONS: 50,
    MIN_CONFIDENCE: 0.0,
    MAX_CONFIDENCE: 1.0,
  },
} as const;

// MESSAGES D'ERREUR LOCALISÉS
export const ERROR_MESSAGES = {
  FEEDBACK: {
    SUBMISSION_FAILED:
      "Erreur lors de l'envoi du feedback. Veuillez réessayer.",
    INVALID_CONVERSATION_ID:
      "Impossible d'enregistrer le feedback - ID de conversation manquant",
    COMMENT_TOO_LONG: `Le commentaire ne peut pas dépasser ${VALIDATION_RULES.FEEDBACK.COMMENT_MAX_LENGTH} caractères`,
    NETWORK_ERROR:
      "Problème de connexion réseau. Vérifiez votre connexion internet.",
    SERVER_ERROR: "Erreur serveur. Veuillez réessayer plus tard.",
    TIMEOUT_ERROR: "Timeout - le serveur met trop de temps à répondre",
  },
  // MESSAGES POUR CONVERSATIONS
  CONVERSATION: {
    LOAD_FAILED: "Erreur lors du chargement de la conversation",
    DELETE_FAILED: "Erreur lors de la suppression de la conversation",
    NOT_FOUND: "Conversation non trouvée",
    EMPTY_MESSAGE: "Le message ne peut pas être vide",
    MESSAGE_TOO_LONG: `Le message ne peut pas dépasser ${VALIDATION_RULES.CONVERSATION.MESSAGE_MAX_LENGTH} caractères`,
    CREATION_FAILED: "Erreur lors de la création de la conversation",
  },
  // MESSAGES POUR CLARIFICATIONS
  CLARIFICATION: {
    PROCESSING_FAILED: "Erreur lors du traitement des clarifications",
    INVALID_ANSWERS: "Réponses invalides. Veuillez vérifier vos réponses.",
    SUBMISSION_FAILED: "Erreur lors de l'envoi des clarifications",
    TIMEOUT: "Timeout lors du traitement des clarifications",
  },
  // NOUVEAUX: MESSAGES POUR CONCISION
  CONCISION: {
    VERSION_NOT_FOUND: "Version de réponse non trouvée",
    INVALID_LEVEL: "Niveau de concision invalide",
    BACKEND_ERROR: "Erreur lors de la génération des versions de réponse",
    FALLBACK_USED: "Version de secours utilisée",
  },
  // NOUVEAUX: MESSAGES POUR AD SYSTEM
  AD_SYSTEM: {
    LOAD_FAILED: "Erreur lors du chargement de la publicité",
    SESSION_CHECK_FAILED: "Erreur lors de la vérification de l'éligibilité",
    INVALID_AD_DATA: "Données publicitaires invalides",
    TRACKING_FAILED: "Erreur lors du suivi publicitaire",
    COOLDOWN_ACTIVE: "Publicité en période d'attente",
  },
  // NOUVEAUX: MESSAGES POUR SESSION TRACKING
  SESSION_TRACKING: {
    START_FAILED: "Erreur lors du démarrage du tracking de session",
    HEARTBEAT_FAILED: "Erreur lors de la mise à jour de l'activité",
    END_FAILED: "Erreur lors de la fermeture de session",
    INVALID_SESSION: "Session invalide ou expirée",
    ANALYTICS_FAILED: "Erreur lors du chargement des analytics de session",
  },
  // NOUVEAUX: MESSAGES POUR AGENT LLM
  AGENT: {
    PROCESSING_FAILED: "Erreur lors du traitement par l'Agent",
    TIMEOUT: "L'Agent a mis trop de temps à répondre",
    COMPLEXITY_ERROR: "Erreur dans l'analyse de complexité",
    SYNTHESIS_FAILED: "Erreur lors de la synthèse des sources",
    INVALID_METADATA: "Métadonnées Agent invalides",
  },
  GENERAL: {
    UNAUTHORIZED: "Session expirée - reconnexion nécessaire",
    FORBIDDEN: "Accès non autorisé",
    NOT_FOUND: "Ressource non trouvée",
    GENERIC: "Une erreur inattendue s'est produite",
  },
} as const;

// TYPES POUR LES RÉPONSES D'API FEEDBACK
export interface FeedbackApiResponse {
  status: "success" | "error";
  message: string;
  conversation_id: string;
  feedback?: number;
  comment?: string;
  timestamp: string;
}

export interface ConversationApiResponse {
  status: "success" | "error";
  message: string;
  conversation_id: string;
  timestamp: string;
}

export interface AnalyticsApiResponse {
  status: "success" | "error";
  timestamp: string;
  analytics: FeedbackAnalytics;
  message: string;
}

// NOUVEAUX: TYPES POUR LES RÉPONSES D'API AD SYSTEM
export interface AdEligibilityResponse {
  status: "success" | "error";
  qualifiesForAd: boolean;
  sessionStats: UserSessionStats;
  timeUntilNextAd?: number;
  message?: string;
}

export interface AdEventResponse {
  status: "success" | "error";
  message: string;
  event_id?: string;
  timestamp: string;
}

// NOUVEAUX: TYPES POUR LES RÉPONSES D'API SESSION TRACKING
export interface SessionAnalyticsApiResponse {
  status: "success" | "error";
  data?: SessionAnalytics;
  error?: string;
  timestamp: string;
}

export interface SessionStatsApiResponse {
  status: "success" | "error";
  data?: {
    user_email: string;
    sessions: UserSession[];
    analytics: SessionAnalytics;
  };
  error?: string;
  timestamp: string;
}

// TYPES POUR LES PRÉFÉRENCES UTILISATEUR
export interface UserPreferences {
  language: Language;
  concision_level: ConcisionLevel;
  enable_notifications: boolean;
  enable_analytics_tracking: boolean;
  enable_ad_personalization: boolean;
  theme: "light" | "dark" | "auto";
  timezone: string;
  date_format: "dd/mm/yyyy" | "mm/dd/yyyy" | "yyyy-mm-dd";
  time_format: "12h" | "24h";
}

export interface UserPreferencesUpdate {
  language?: Language;
  concision_level?: ConcisionLevel;
  enable_notifications?: boolean;
  enable_analytics_tracking?: boolean;
  enable_ad_personalization?: boolean;
  theme?: "light" | "dark" | "auto";
  timezone?: string;
  date_format?: "dd/mm/yyyy" | "mm/dd/yyyy" | "yyyy-mm-dd";
  time_format?: "12h" | "24h";
}

// TYPES POUR LES NOTIFICATIONS
export interface NotificationData {
  id: string;
  type: "info" | "success" | "warning" | "error";
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  action_url?: string;
  action_text?: string;
}

export interface NotificationSettings {
  email_notifications: boolean;
  push_notifications: boolean;
  feedback_responses: boolean;
  system_updates: boolean;
  feature_announcements: boolean;
  maintenance_alerts: boolean;
}

// CONSTANTES DE CONFIGURATION GLOBALE
export const APP_CONFIG = {
  NAME: "Intelia Expert",
  VERSION: "2.1.0", // Incrémenté pour support Agent
  DESCRIPTION: "Plateforme IA spécialisée en élevage avicole avec Agent LLM",
  COMPANY: "Intelia",
  SUPPORT_EMAIL: "support@intelia.com",
  PRIVACY_URL: "https://intelia.com/privacy",
  TERMS_URL: "https://intelia.com/terms",

  FEATURES: {
    ENABLE_FEEDBACK: true,
    ENABLE_CLARIFICATIONS: true,
    ENABLE_CONCISION: true,
    ENABLE_AD_SYSTEM: true,
    ENABLE_SESSION_TRACKING: true,
    ENABLE_CONVERSATIONS: true,
    ENABLE_ANALYTICS: true,
    // 🆕 NOUVELLES FEATURES AGENT
    ENABLE_AGENT_LLM: true,
    ENABLE_AGENT_METADATA: true,
    ENABLE_PROACTIVE_FOLLOWUP: true,
    ENABLE_STREAMING_ENHANCED: true,
  },

  LIMITS: {
    MAX_MESSAGE_LENGTH: 5000,
    MAX_CONVERSATIONS: 1000,
    MAX_FEEDBACK_COMMENT_LENGTH: 500,
    SESSION_TIMEOUT_MINUTES: 30,
    HEARTBEAT_INTERVAL_MINUTES: 2,
    // 🆕 LIMITES AGENT
    MAX_AGENT_PROCESSING_TIME: 60000, // 60 secondes
    MAX_AGENT_SUB_QUERIES: 5,
    MAX_AGENT_SOURCES: 10,
  },
} as const;

// Note: Les utilitaires sont déjà exportés via 'export const' dans leurs déclarations respectives
// Pas besoin d'export supplémentaire ici
