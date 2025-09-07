// types/index.ts - VERSION UNIFIÉE COMPLÈTE (37K+ caractères)

// ==================== INTERFACE MESSAGE ÉTENDUE AVEC CONCISION ET RESPONSE_VERSIONS ====================

export interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  feedback?: 'positive' | 'negative' | null
  conversation_id?: string
  feedbackComment?: string  // ✅ CONSERVÉ: Commentaire associé au feedback
  
  // ✅ CONSERVÉS: CHAMPS POUR CLARIFICATION
  is_clarification_request?: boolean       // Pour les messages du bot qui demandent des clarifications
  is_clarification_response?: boolean      // Pour les messages utilisateur qui répondent aux clarifications
  clarification_questions?: string[]       // Questions de clarification du bot
  clarification_answers?: Record<string, string>  // Réponses de clarification de l'utilisateur (optionnel)
  original_question?: string               // Question originale avant clarification
  clarification_entities?: Record<string, any>    // Entités extraites des réponses de clarification
  
  // 🚀 NOUVEAU: Champs pour le système de concision backend
  response_versions?: {
    ultra_concise: string
    concise: string
    standard: string
    detailed: string
  }
  
  // ✅ CONSERVÉS: Champs pour compatibilité (peuvent être supprimés plus tard)
  originalResponse?: string  // Réponse originale avant concision
  processedResponse?: string // Réponse après traitement de concision
  concisionLevel?: ConcisionLevel // Niveau de concision appliqué
  
  // ✅ COMPATIBILITY: Champs du petit fichier
  role?: 'user' | 'assistant'
  sources?: DocumentSource[]
  metadata?: MessageMetadata
}

// ==================== TYPES POUR CONCISION BACKEND ====================

export enum ConcisionLevel {
  ULTRA_CONCISE = 'ultra_concise',  // Réponse minimale
  CONCISE = 'concise',              // Réponse courte  
  STANDARD = 'standard',            // Réponse normale
  DETAILED = 'detailed'             // Réponse complète
}

export interface ConcisionConfig {
  level: ConcisionLevel;
  autoDetect: boolean;  // Détection automatique selon le type de question
  userPreference: boolean; // Sauvegarder préférence utilisateur
}

export interface ConcisionControlProps {
  className?: string;
  compact?: boolean;
}

// 🚀 NOUVEAU: Interface pour sélection de versions backend
export interface ResponseVersionSelection {
  selectedVersion: string;
  availableVersions: Record<string, string>;
  selectedLevel: ConcisionLevel;
}

// ✅ CONSERVÉ: Interface pour traitement legacy (compatibilité)
export interface ResponseProcessingResult {
  processedContent: string;
  originalContent: string;
  levelUsed: ConcisionLevel;
  wasProcessed: boolean;
}

// ==================== TYPES EXISTANTS CONSERVÉS ====================

export interface ExpertApiResponse {
  question: string
  response: string
  full_text?: string  // ✅ plein texte non tronqué (si fourni par l'API)
  conversation_id: string
  rag_used: boolean
  rag_score?: number
  timestamp: string
  language: string
  response_time_ms: number
  mode: string
  user?: string
  logged: boolean
  validation_passed?: boolean
  validation_confidence?: number
  // ✅ CONSERVÉS: CHAMPS POUR CLARIFICATION
  is_clarification_request?: boolean
  clarification_questions?: string[]
  // 🚀 NOUVEAU: Champs pour versions backend
  response_versions?: {
    ultra_concise: string
    concise: string
    standard: string
    detailed: string
  }
}

// ✅ CONSERVÉ: INTERFACE ConversationData ÉTENDUE AVEC FEEDBACK
export interface ConversationData {
  user_id: string
  question: string
  response: string
  full_text?: string  // ✅ plein texte non tronqué (si fourni par l'API)
  conversation_id: string
  confidence_score?: number
  response_time_ms?: number
  language?: string
  rag_used?: boolean
  feedback?: 1 | -1 | null          // ✅ CONSERVÉ: Feedback numérique pour le backend
  feedback_comment?: string          // ✅ CONSERVÉ: Commentaire feedback
}

export interface ConversationItem {
  id: string
  title: string
  messages: Array<{
    id: string
    role: string
    content: string
  }>
  updated_at: string
  created_at: string
  feedback?: number | null
  feedback_comment?: string  // ✅ CONSERVÉ: Commentaire dans l'historique
}

// ==================== CONSERVÉS: TYPES POUR CONVERSATIONS STYLE CLAUDE.AI ====================

// ✅ CONSERVÉ: Structure complète d'une conversation
export interface Conversation {
  id: string
  title: string
  preview: string  // Premier message ou résumé
  message_count: number
  created_at: string
  updated_at: string
  feedback?: number | null
  language?: string
  last_message_preview?: string
  status?: 'active' | 'archived'
  // ✅ COMPATIBILITY: Champs du petit fichier
  user_id?: string
  messages?: Message[]
}

// ✅ CONSERVÉ: Conversation complète avec tous ses messages
export interface ConversationWithMessages extends Conversation {
  messages: Message[]
}

// ✅ CONSERVÉ: Structure pour l'historique groupé
export interface ConversationGroup {
  title: string  // "Aujourd'hui", "Hier", "Cette semaine", etc.
  conversations: Conversation[]
}

// ✅ CONSERVÉ: Réponse API pour l'historique
export interface ConversationHistoryResponse {
  success: boolean
  conversations: Conversation[]
  groups?: ConversationGroup[]
  total_count: number
  user_id: string
  timestamp: string
}

// ✅ CONSERVÉ: Réponse API pour une conversation complète
export interface ConversationDetailResponse {
  success: boolean
  conversation: ConversationWithMessages
  timestamp: string
}

// ✅ CONSERVÉ: Options pour le groupement des conversations
export interface ConversationGroupingOptions {
  groupBy: 'date' | 'topic' | 'none'
  sortBy: 'updated_at' | 'created_at' | 'message_count'
  sortOrder: 'desc' | 'asc'
  limit?: number
  offset?: number
}

// ✅ CONSERVÉ: Statistiques de conversation
export interface ConversationStats {
  total_conversations: number
  total_messages: number
  avg_messages_per_conversation: number
  most_active_day: string
  favorite_topics: string[]
  satisfaction_rate: number
}

// ==================== CONSERVÉS: TYPES POUR CLARIFICATIONS INLINE ====================

// ✅ CONSERVÉ: Interface simplifiée pour clarifications inline
export interface ClarificationInlineProps {
  questions: string[]
  originalQuestion: string
  language: string
  onSubmit: (answers: Record<string, string>) => Promise<void>
  onSkip: () => Promise<void>
  isSubmitting?: boolean
  conversationId?: string
}

// ✅ CONSERVÉ: Interface pour les réponses de clarification
export interface ClarificationResponse {
  needs_clarification: boolean
  questions?: string[]
  confidence_score?: number
  processing_time_ms?: number
  model_used?: string
}

// ✅ CONSERVÉ: Interface pour l'état des clarifications
export interface ClarificationState {
  pendingClarification: ExpertApiResponse | null
  isProcessingClarification: boolean
  clarificationHistory: Array<{
    original_question: string
    clarification_questions: string[]
    answers: Record<string, string>
    final_response: string
    timestamp: string
  }>
}

// ==================== CONSERVÉS: TYPES UTILISATEUR AVEC CHAMPS TÉLÉPHONE ====================

export interface User {
  id: string
  email: string
  name: string
  firstName: string
  lastName: string
  phone: string  // ⚠️ CONSERVÉ: Champ existant - gardé pour compatibilité
  country: string
  linkedinProfile: string
  companyName: string
  companyWebsite: string
  linkedinCorporate: string
  user_type: string
  language: string
  created_at: string
  plan: string
  
  // ✅ CONSERVÉS: NOUVEAUX CHAMPS TÉLÉPHONE SÉPARÉS POUR SUPABASE
  country_code?: string    // Code pays (ex: +1, +33, +32)
  area_code?: string       // Code régional (ex: 514, 04, 2)
  phone_number?: string    // Numéro principal (ex: 1234567, 12345678)
  
  // ✅ COMPATIBILITY: Champs du petit fichier
  full_name?: string
  avatar_url?: string
  consent_given?: boolean
  consent_date?: string
  updated_at?: string
  user_id?: string
  profile_id?: string
  preferences?: Record<string, any>
  is_admin?: boolean
}

export interface ProfileUpdateData {
  firstName: string
  lastName: string
  email: string
  phone?: string  // ✅ CONSERVÉ: Maintenant optionnel pour éviter les conflits
  country: string
  linkedinProfile: string
  companyName: string
  companyWebsite: string
  linkedinCorporate: string
  language?: string
  
  // ✅ CONSERVÉS: NOUVEAUX CHAMPS TÉLÉPHONE SÉPARÉS
  country_code?: string
  area_code?: string
  phone_number?: string
}

// ==================== CONSERVÉS: TYPES SPÉCIFIQUES AU COMPOSANT PHONE ====================

export interface PhoneData {
  country_code: string
  area_code: string
  phone_number: string
}

export interface PhoneValidationResult {
  isValid: boolean
  errors: string[]
  isValidCountry: boolean
  isValidArea: boolean
  isValidNumber: boolean
}

// ==================== CONSERVÉS: NOUVEAUX TYPES FEEDBACK ET COMMENTAIRES ====================

// ✅ CONSERVÉ: Interface pour les données feedback enrichies
export interface FeedbackData {
  conversation_id: string
  feedback: 'positive' | 'negative'
  comment?: string
  timestamp: string
  user_id?: string
  // ✅ COMPATIBILITY: Champs du petit fichier
  message_id?: string
  rating?: 'positive' | 'negative'
  category?: 'accuracy' | 'relevance' | 'completeness' | 'other'
}

// ✅ CONSERVÉ: Props pour la modal feedback
export interface FeedbackModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (feedback: 'positive' | 'negative', comment?: string) => Promise<void>
  feedbackType: 'positive' | 'negative'
  isSubmitting?: boolean
}

// ✅ CONSERVÉ: Interface pour les analytics feedback
export interface FeedbackAnalytics {
  period_days: number
  total_conversations: number
  total_feedback: number
  satisfaction_rate: number
  feedback_rate: number
  comment_rate: number
  feedback_breakdown: {
    positive: number
    negative: number
    with_comment: number
  }
  recent_comments: Array<{
    conversation_id: string
    feedback: 'positive' | 'negative'
    comment: string
    timestamp: string
    question_preview: string
  }>
}

// ✅ CONSERVÉ: Interface pour le rapport admin feedback
export interface AdminFeedbackReport {
  period_days: number
  generated_at: string
  summary: {
    total_conversations: number
    total_feedback: number
    satisfaction_rate: number
    feedback_rate: number
    comment_rate: number
    avg_response_time_ms?: number
  }
  feedback_breakdown: {
    positive: number
    negative: number
    with_comment: number
  }
  language_stats: Array<{
    language: string
    total: number
    positive: number
    negative: number
    with_comment: number
    satisfaction_rate: number
  }>
  top_negative_feedback: Array<{
    question: string
    comment: string
    timestamp: string
    language: string
  }>
  top_positive_feedback: Array<{
    question: string
    comment: string
    timestamp: string
    language: string
  }>
  most_active_users: Array<{
    user_id: string
    total_conversations: number
    feedback_given: number
    comments_given: number
    engagement_rate: number
  }>
}

// ✅ CONSERVÉ: Interface pour les statistiques utilisateur
export interface UserFeedbackStats {
  user_id: string
  total_conversations: number
  feedback_given: number
  comments_given: number
  positive_feedback: number
  negative_feedback: number
  engagement_rate: number
  avg_comment_length?: number
  last_feedback_date?: string
}

// ==================== CONSERVÉS: TYPES HOOKS AVEC CONVERSATIONS ====================

// ✅ CONSERVÉ: INTERFACE AuthStore COMPLÈTE AVEC TOUTES LES PROPRIÉTÉS
export interface AuthStore {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  hasHydrated: boolean  // ✅ CONSERVÉ: Pour éviter l'erreur TypeScript
  logout: () => Promise<void>
  login: (email: string, password: string) => Promise<void>  // ✅ CONSERVÉ
  register: (email: string, password: string, userData?: Partial<User>) => Promise<void>  // ✅ CONSERVÉ
  updateProfile: (data: ProfileUpdateData) => Promise<{ success: boolean; error?: string }>
  initializeSession: () => Promise<boolean>  // ✅ CONSERVÉ
}

// ✅ CONSERVÉ: ChatStore pour gérer les conversations
export interface ChatStore {
  // ✅ CONSERVÉES: PROPRIÉTÉS EXISTANTES 
  conversations: ConversationItem[]
  isLoading: boolean
  loadConversations: (userId: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  clearAllConversations: (userId?: string) => Promise<void>
  refreshConversations: (userId: string) => Promise<void>
  addConversation: (conversationId: string, question: string, response: string) => void

  // ✅ CONSERVÉES: PROPRIÉTÉS POUR CONVERSATIONS STYLE CLAUDE.AI
  conversationGroups: ConversationGroup[]
  currentConversation: ConversationWithMessages | null
  isLoadingHistory: boolean
  isLoadingConversation: boolean
  loadConversation: (conversationId: string) => Promise<void>
  createNewConversation: () => void
  addMessage: (message: Message) => void
  updateMessage: (messageId: string, updates: Partial<Message>) => void
  setCurrentConversation: (conversation: ConversationWithMessages | null) => void
}

export interface Translation {
  t: (key: string) => string
  changeLanguage: (lang: string) => void
  currentLanguage: string
}

// ==================== CONSERVÉS: TYPES COMPOSANTS ====================

export interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}

export interface UserInfoModalProps {
  user: User | null
  onClose: () => void
}

export interface IconProps {
  className?: string
}

// ============================================================================
// LANGUAGE & INTERNATIONALIZATION - UNIFIÉ
// ============================================================================

export type Language = 'fr' | 'en' | 'es' | 'pt' | 'de' | 'nl' | 'pl'

export interface LanguageOption {
  code: Language
  name: string
  flag: string
}

// ============================================================================
// PETIT FICHIER - TYPES EXPERT SYSTEM
// ============================================================================

export interface ExpertQuestion {
  content: string
  language: Language
  context?: string
  conversation_id?: string
}

export interface ExpertResponse {
  id: string
  content: string
  sources: DocumentSource[]
  confidence_score: number
  response_time: number
  model_used: string
  suggestions?: string[]
  clarification_needed?: boolean
}

export interface TopicSuggestion {
  id: string
  title: string
  description: string
  category: 'health' | 'nutrition' | 'environment' | 'general'
  icon: string
  popular: boolean
}

export interface DocumentSource {
  id: string
  title: string
  excerpt: string
  relevance_score: number
  document_type: string
  url?: string
}

export interface MessageMetadata {
  response_time?: number
  model_used?: string
  confidence_score?: number
  language_detected?: Language
}

export interface UsageAnalytics {
  daily_questions: number
  satisfaction_rate: number
  avg_response_time: number
  popular_topics: string[]
  user_retention: number
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
    details?: any
  }
  metadata?: {
    pagination?: {
      page: number
      per_page: number
      total: number
      total_pages: number
    }
    timestamp: string
  }
}

export interface RGPDConsent {
  analytics: boolean
  marketing: boolean
  functional: boolean
  given_at: string
  ip_address?: string
}

export interface DataExportRequest {
  user_id: string
  request_date: string
  status: 'pending' | 'processing' | 'ready' | 'expired'
  download_url?: string
  expires_at?: string
}

export interface DataDeletionRequest {
  user_id: string
  request_date: string
  scheduled_deletion: string
  status: 'pending' | 'confirmed' | 'completed'
}

export interface AppError {
  code: string
  message: string
  details?: any
  timestamp: string
  user_id?: string
  context?: string
}

// ==================== CONSERVÉS: TYPES API ====================

export interface ApiError extends Error {
  status?: number
}

export class AuthError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AuthError'
  }
}

export class TimeoutError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'TimeoutError'
  }
}

// ==================== TYPES MANQUANTS POUR useAuthStore ====================

export interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  hasHydrated: boolean
}

export interface BackendUserData {
  id?: string                    // Version gros fichier
  user_id?: string              // Version petit fichier
  email: string
  name?: string
  full_name?: string
  firstName?: string
  lastName?: string
  user_type?: string
  created_at?: string
  updated_at?: string
  language?: string
  plan?: string
  country_code?: string
  area_code?: string
  phone_number?: string
  country?: string
  linkedinProfile?: string
  companyName?: string
  companyWebsite?: string
  linkedinCorporate?: string
  avatar_url?: string
  consent_given?: boolean
  consent_date?: string
  profile_id?: string
  preferences?: Record<string, any>
  is_admin?: boolean
  iss?: string
  aud?: string
  exp?: number
  jwt_secret_used?: string
}

export const mapBackendUserToUser = (backendUser: BackendUserData): User => {
  // Récupérer l'ID (priorité user_id puis id)
  const userId = backendUser.user_id || backendUser.id || ''
  
  // Récupérer le nom (priorité name, puis full_name, puis construction firstName+lastName)
  const userName = backendUser.name || 
                   backendUser.full_name || 
                   `${backendUser.firstName || ''} ${backendUser.lastName || ''}`.trim() || 
                   backendUser.email || ''

  return {
    id: userId,
    email: backendUser.email || '',
    name: userName,
    firstName: backendUser.firstName || '',
    lastName: backendUser.lastName || '',
    phone: `${backendUser.country_code || ''}${backendUser.area_code || ''}${backendUser.phone_number || ''}`,
    country: backendUser.country || '',
    linkedinProfile: backendUser.linkedinProfile || '',
    companyName: backendUser.companyName || '',
    companyWebsite: backendUser.companyWebsite || '',
    linkedinCorporate: backendUser.linkedinCorporate || '',
    user_type: backendUser.user_type || 'producer',
    language: (backendUser.language as Language) || 'fr',
    created_at: backendUser.created_at || new Date().toISOString(),
    plan: backendUser.plan || 'essential',
    
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
    is_admin: backendUser.is_admin || false
  }
}

// ==================== CONSERVÉES: CONSTANTES API SÉCURISÉES ====================
// 🔧 CONFIGURATION API CORRIGÉE - Configuration API dynamique depuis environnement
const getApiConfig = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
  const version = process.env.NEXT_PUBLIC_API_VERSION || 'v1'
  
  if (!baseUrl) {
    console.error('❌ NEXT_PUBLIC_API_BASE_URL environment variable missing')
    return {
      BASE_URL: 'http://localhost:8000', // Fallback développement
      TIMEOUT: 30000,
      LOGGING_BASE_URL: 'http://localhost:8000/api/v1'
    }
  }
  
  // 🔧 CORRECTION: Enlever /api s'il est déjà présent pour éviter /api/api/
  const cleanBaseUrl = baseUrl.replace(/\/api\/?$/, '')
  
  return {
    BASE_URL: cleanBaseUrl, // 🔧 URL de base nettoyée
    TIMEOUT: 30000,
    LOGGING_BASE_URL: `${cleanBaseUrl}/api/${version}` // 🔧 Construction correcte
  }
}

export const API_CONFIG = getApiConfig()

// ✅ CONSERVÉS: ENDPOINTS FEEDBACK
export const FEEDBACK_ENDPOINTS = {
  SAVE_CONVERSATION: '/logging/conversation',
  UPDATE_FEEDBACK: '/logging/conversation/{id}/feedback',
  UPDATE_COMMENT: '/logging/conversation/{id}/comment',
  UPDATE_FEEDBACK_WITH_COMMENT: '/logging/conversation/{id}/feedback-with-comment',
  GET_USER_CONVERSATIONS: '/logging/user/{id}/conversations',
  DELETE_CONVERSATION: '/logging/conversation/{id}',
  DELETE_ALL_USER_CONVERSATIONS: '/logging/user/{id}/conversations',
  GET_FEEDBACK_ANALYTICS: '/logging/analytics/feedback',
  GET_CONVERSATIONS_WITH_COMMENTS: '/logging/conversations/with-comments',
  GET_ADMIN_FEEDBACK_REPORT: '/logging/admin/feedback-report',
  EXPORT_FEEDBACK_DATA: '/logging/admin/export-feedback',
  TEST_COMMENT_SUPPORT: '/logging/test-comments'
} as const

export const PLAN_CONFIGS = {
  essential: {
    name: 'Essentiel',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    features: [
      '50 questions par mois',
      'Accès aux documents publics',
      'Support par email',
      'Interface web'
    ]
  },
  pro: {
    name: 'Pro',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    features: [
      'Questions illimitées',
      'Accès documents confidentiels',
      'Support prioritaire',
      'Interface web + mobile',
      'Analytics avancées'
    ]
  }
} as const

// ✅ CONSERVÉE: CONFIGURATION FEEDBACK
export const FEEDBACK_CONFIG = {
  TYPES: {
    POSITIVE: {
      value: 'positive' as const,
      label: 'Utile',
      icon: '👍',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      description: 'Cette réponse m\'a été utile'
    },
    NEGATIVE: {
      value: 'negative' as const, 
      label: 'Pas utile',
      icon: '👎',
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      description: 'Cette réponse pourrait être améliorée'
    }
  },
  COMMENT_PLACEHOLDERS: {
    positive: 'Qu\'avez-vous apprécié dans cette réponse ?',
    negative: 'Dans quelle mesure cette réponse était-elle satisfaisante ?'
  },
  MODAL_TITLES: {
    positive: 'Merci pour votre feedback positif !',
    negative: 'Aidez-nous à améliorer'
  },
  MAX_COMMENT_LENGTH: 500,
  MIN_COMMENT_LENGTH: 0,
  PRIVACY_POLICY_URL: 'https://intelia.com/privacy-policy/'
} as const

// ✅ CONSERVÉE: CONFIGURATION DES CLARIFICATIONS
export const CLARIFICATION_TEXTS = {
  fr: {
    title: "Informations supplémentaires requises",
    subtitle: "Pour vous donner la meilleure réponse, veuillez répondre à ces questions :",
    placeholder: "Tapez votre réponse ici...",
    submit: "Obtenir ma réponse",
    skip: "Passer et obtenir une réponse générale",
    optional: "(optionnel)",
    required: "Répondez à au moins la moitié des questions",
    processing: "Traitement en cours...",
    validationError: "Veuillez répondre à au moins {count} questions"
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
    validationError: "Please answer at least {count} questions"
  },
  es: {
    title: "Información adicional requerida",
    subtitle: "Para darle la mejor respuesta, por favor responda estas preguntas:",
    placeholder: "Escriba su respuesta aquí...",
    submit: "Obtener mi respuesta",
    skip: "Omitir y obtener una respuesta general",
    optional: "(opcional)",
    required: "Responda al menos la mitad de las preguntas",
    processing: "Procesando...",
    validationError: "Por favor responda al menos {count} preguntas"
  }
} as const

export const CLARIFICATION_CONFIG = {
  MAX_QUESTIONS: 4,
  MIN_ANSWER_LENGTH: 0,
  MAX_ANSWER_LENGTH: 200,
  REQUIRED_ANSWER_PERCENTAGE: 0.5, // 50% des questions doivent être répondues
  AUTO_SCROLL_DELAY: 300,
  VALIDATION_DEBOUNCE: 500
} as const

// 🚀 NOUVELLE: CONFIGURATION POUR CONCISION BACKEND
export const CONCISION_CONFIG = {
  LEVELS: {
    ULTRA_CONCISE: {
      value: 'ultra_concise' as const,
      label: 'Minimal',
      icon: '⚡',
      description: 'Juste l\'essentiel',
      example: 'Données clés uniquement'
    },
    CONCISE: {
      value: 'concise' as const,
      label: 'Concis', 
      icon: '🎯',
      description: 'Information principale avec contexte',
      example: 'Réponse courte avec explication essentielle'
    },
    STANDARD: {
      value: 'standard' as const,
      label: 'Standard',
      icon: '📄', 
      description: 'Réponse équilibrée avec conseils',
      example: 'Réponse complète sans détails techniques'
    },
    DETAILED: {
      value: 'detailed' as const,
      label: 'Détaillé',
      icon: '📚',
      description: 'Réponse complète avec explications',
      example: 'Réponse exhaustive avec conseils détaillés'
    }
  },
  DEFAULT_LEVEL: 'concise' as const,
  AUTO_DETECT: true,
  SAVE_PREFERENCE: true,
  STORAGE_KEY: 'intelia_concision_level'
} as const

// ✅ CONSERVÉS: UTILITAIRES ANALYTICS
export const ANALYTICS_UTILS = {
  calculateSatisfactionRate: (positive: number, negative: number): number => {
    const total = positive + negative
    return total > 0 ? Math.round((positive / total) * 1000) / 1000 : 0
  },
  
  calculateEngagementRate: (feedbackGiven: number, totalConversations: number): number => {
    return totalConversations > 0 ? Math.round((feedbackGiven / totalConversations) * 1000) / 1000 : 0
  },
  
  calculateCommentRate: (withComments: number, totalFeedback: number): number => {
    return totalFeedback > 0 ? Math.round((withComments / totalFeedback) * 1000) / 1000 : 0
  },
  
  formatPercentage: (rate: number): string => {
    return `${(rate * 100).toFixed(1)}%`
  },
  
  truncateText: (text: string, maxLength: number): string => {
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
  },
  
  formatTimestamp: (timestamp: string): string => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleDateString('fr-FR', { 
        day: 'numeric', 
        month: 'short', 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    } catch {
      return timestamp
    }
  }
} as const

// ✅ CONSERVÉS: UTILITAIRES POUR CLARIFICATIONS
export const ClarificationUtils = {
  isClarificationResponse: (response: ExpertApiResponse): boolean => {
    return (
      response.mode?.includes("clarification_needed") ||
      response.response?.includes("❓") ||
      response.response?.includes("précisions") ||
      response.response?.includes("clarification") ||
      response.response?.includes("aclaraciones") ||
      response.is_clarification_request === true
    )
  },

  extractClarificationQuestions: (response: ExpertApiResponse): string[] => {
    if (response.clarification_questions) {
      return response.clarification_questions
    }
    
    const questions: string[] = []
    const lines = response.response.split('\n')
    
    for (const line of lines) {
      const cleaned = line.trim()
      if (cleaned.startsWith('• ') || cleaned.startsWith('- ')) {
        const question = cleaned.replace(/^[•-]\s*/, '').trim()
        if (question.length > 5) {
          questions.push(question)
        }
      }
    }
    
    return questions
  },

  buildEnrichedQuestion: (
    originalQuestion: string, 
    clarificationAnswers: Record<string, string>, 
    clarificationQuestions: string[]
  ): string => {
    let enrichedQuestion = originalQuestion + "\n\nInformations supplémentaires :"
    
    Object.entries(clarificationAnswers).forEach(([index, answer]) => {
      if (answer && answer.trim()) {
        try {
          const questionIndex = parseInt(index)
          if (questionIndex >= 0 && questionIndex < clarificationQuestions.length) {
            const question = clarificationQuestions[questionIndex]
            enrichedQuestion += `\n- ${question}: ${answer.trim()}`
          }
        } catch {
          // Ignorer les index invalides
        }
      }
    })
    
    return enrichedQuestion
  },

  validateClarificationAnswers: (
    answers: Record<string, string>, 
    questions: string[]
  ): { isValid: boolean; requiredCount: number; answeredCount: number } => {
    const answeredCount = Object.values(answers).filter(a => a && a.trim().length > 0).length
    const requiredCount = Math.ceil(questions.length * 0.5) // Au moins 50% des questions
    
    return {
      isValid: answeredCount >= requiredCount,
      requiredCount,
      answeredCount
    }
  }
} as const

// 🚀 NOUVEAUX: UTILITAIRES POUR CONCISION BACKEND
export const ConcisionUtils = {
  selectVersionFromResponse: (
    responseVersions: Record<string, string>,
    level: ConcisionLevel
  ): string => {
    // Retourner la version demandée si elle existe
    if (responseVersions[level]) {
      return responseVersions[level]
    }
    
    // Fallback intelligent si version manquante
    const fallbackOrder: ConcisionLevel[] = [
      ConcisionLevel.DETAILED,
      ConcisionLevel.STANDARD, 
      ConcisionLevel.CONCISE,
      ConcisionLevel.ULTRA_CONCISE
    ]
    
    for (const fallbackLevel of fallbackOrder) {
      if (responseVersions[fallbackLevel]) {
        console.warn(`⚠️ [ConcisionUtils] Fallback vers ${fallbackLevel} (${level} manquant)`)
        return responseVersions[fallbackLevel]
      }
    }
    
    // Ultime fallback - première version disponible
    const firstAvailable = Object.values(responseVersions)[0]
    console.warn('⚠️ [ConcisionUtils] Aucune version standard - utilisation première disponible')
    return firstAvailable || 'Réponse non disponible'
  },

  validateResponseVersions: (responseVersions: any): boolean => {
    if (!responseVersions || typeof responseVersions !== 'object') {
      return false
    }
    
    const requiredLevels = [
      ConcisionLevel.ULTRA_CONCISE,
      ConcisionLevel.CONCISE,
      ConcisionLevel.STANDARD,
      ConcisionLevel.DETAILED
    ]
    
    // Vérifier qu'au moins une version est présente
    const hasAnyVersion = requiredLevels.some(level => 
      responseVersions[level] && typeof responseVersions[level] === 'string'
    )
    
    return hasAnyVersion
  },

  detectOptimalLevel: (question: string): ConcisionLevel => {
    const questionLower = question.toLowerCase()
    
    // Questions ultra-concises (poids, température, mesures simples)
    const ultraConciseKeywords = [
      'poids', 'weight', 'peso',
      'température', 'temperature', 'temperatura', 
      'combien', 'how much', 'cuánto',
      'quel est', 'what is', 'cuál es',
      'quelle est', 'âge', 'age'
    ]
    
    if (ultraConciseKeywords.some(keyword => questionLower.includes(keyword))) {
      return ConcisionLevel.ULTRA_CONCISE
    }

    // Questions complexes (comment, pourquoi, procédures)
    const complexKeywords = [
      'comment', 'how to', 'cómo',
      'pourquoi', 'why', 'por qué', 
      'expliquer', 'explain', 'explicar',
      'procédure', 'procedure', 'procedimiento',
      'diagnostic', 'diagnosis', 'diagnóstico',
      'traitement', 'treatment', 'tratamiento'
    ]

    if (complexKeywords.some(keyword => questionLower.includes(keyword))) {
      return ConcisionLevel.DETAILED
    }

    // Par défaut: concis pour questions générales
    return ConcisionLevel.CONCISE
  },

  analyzeResponseComplexity: (response: string): {
    wordCount: number
    sentenceCount: number
    hasNumbers: boolean
    hasAdvice: boolean
    complexity: 'simple' | 'moderate' | 'complex'
  } => {
    const wordCount = response.split(/\s+/).length
    const sentenceCount = response.split('.').filter(s => s.trim().length > 0).length
    const hasNumbers = /\d+/.test(response)
    
    const adviceKeywords = [
      'recommandé', 'essentiel', 'important', 'devrait', 'doit',
      'recommended', 'essential', 'important', 'should', 'must',
      'recomendado', 'esencial', 'importante', 'debería', 'debe'
    ]
    const hasAdvice = adviceKeywords.some(keyword => 
      response.toLowerCase().includes(keyword)
    )
    
    let complexity: 'simple' | 'moderate' | 'complex' = 'simple'
    if (wordCount > 100 || sentenceCount > 3) complexity = 'moderate'
    if (wordCount > 200 || sentenceCount > 6) complexity = 'complex'
    
    return {
      wordCount,
      sentenceCount,
      hasNumbers,
      hasAdvice,
      complexity
    }
  },

  debugResponseVersions: (responseVersions: Record<string, string>): void => {
    console.group('🔍 [ConcisionUtils] Versions disponibles')
    Object.entries(responseVersions).forEach(([level, content]) => {
      console.log(`${level}: ${content?.length || 0} caractères`)
      if (content) {
        console.log(`  Aperçu: "${content.substring(0, 50)}..."`)
      }
    })
    console.groupEnd()
  }
} as const

// ✅ CONSERVÉES: CONSTANTES DE VALIDATION
export const VALIDATION_RULES = {
  FEEDBACK: {
    COMMENT_MIN_LENGTH: 0,
    COMMENT_MAX_LENGTH: 500,
    REQUIRED_FIELDS: [] as string[], // Aucun champ requis pour le feedback
    ALLOWED_FEEDBACK_TYPES: ['positive', 'negative'] as const
  },
  PHONE: {
    COUNTRY_CODE_PATTERN: /^\+\d{1,4}$/,
    AREA_CODE_PATTERN: /^\d{1,4}$/,
    PHONE_NUMBER_PATTERN: /^\d{4,12}$/
  },
  // ✅ CONSERVÉES: RÈGLES POUR CONVERSATIONS
  CONVERSATION: {
    TITLE_MAX_LENGTH: 60,
    PREVIEW_MAX_LENGTH: 150,
    MESSAGE_MAX_LENGTH: 5000,
    MAX_CONVERSATIONS_PER_USER: 1000,
    AUTO_DELETE_DAYS: 30
  },
  // ✅ CONSERVÉES: RÈGLES POUR CLARIFICATIONS
  CLARIFICATION: {
    MIN_ANSWER_LENGTH: 0,
    MAX_ANSWER_LENGTH: 200,
    MAX_QUESTIONS: 4,
    REQUIRED_ANSWER_PERCENTAGE: 0.5
  },
  // 🚀 NOUVELLES: RÈGLES POUR CONCISION
  CONCISION: {
    MIN_RESPONSE_LENGTH: 10,
    MAX_ULTRA_CONCISE_LENGTH: 50,
    MAX_CONCISE_LENGTH: 200,
    MAX_STANDARD_LENGTH: 500,
    // Pas de limite pour DETAILED
    AUTO_DETECT_ENABLED: true
  }
} as const

// ✅ CONSERVÉS: MESSAGES D'ERREUR LOCALISÉS
export const ERROR_MESSAGES = {
  FEEDBACK: {
    SUBMISSION_FAILED: 'Erreur lors de l\'envoi du feedback. Veuillez réessayer.',
    INVALID_CONVERSATION_ID: 'Impossible d\'enregistrer le feedback - ID de conversation manquant',
    COMMENT_TOO_LONG: `Le commentaire ne peut pas dépasser ${VALIDATION_RULES.FEEDBACK.COMMENT_MAX_LENGTH} caractères`,
    NETWORK_ERROR: 'Problème de connexion réseau. Vérifiez votre connexion internet.',
    SERVER_ERROR: 'Erreur serveur. Veuillez réessayer plus tard.',
    TIMEOUT_ERROR: 'Timeout - le serveur met trop de temps à répondre'
  },
  // ✅ CONSERVÉS: MESSAGES POUR CONVERSATIONS
  CONVERSATION: {
    LOAD_FAILED: 'Erreur lors du chargement de la conversation',
    DELETE_FAILED: 'Erreur lors de la suppression de la conversation',
    NOT_FOUND: 'Conversation non trouvée',
    EMPTY_MESSAGE: 'Le message ne peut pas être vide',
    MESSAGE_TOO_LONG: `Le message ne peut pas dépasser ${VALIDATION_RULES.CONVERSATION.MESSAGE_MAX_LENGTH} caractères`,
    CREATION_FAILED: 'Erreur lors de la création de la conversation'
  },
  // ✅ CONSERVÉS: MESSAGES POUR CLARIFICATIONS
  CLARIFICATION: {
    PROCESSING_FAILED: 'Erreur lors du traitement des clarifications',
    INVALID_ANSWERS: 'Réponses invalides. Veuillez vérifier vos réponses.',
    SUBMISSION_FAILED: 'Erreur lors de l\'envoi des clarifications',
    TIMEOUT: 'Timeout lors du traitement des clarifications'
  },
  // 🚀 NOUVEAUX: MESSAGES POUR CONCISION
  CONCISION: {
    VERSION_NOT_FOUND: 'Version de réponse non trouvée',
    INVALID_LEVEL: 'Niveau de concision invalide',
    BACKEND_ERROR: 'Erreur lors de la génération des versions de réponse',
    FALLBACK_USED: 'Version de secours utilisée'
  },
  GENERAL: {
    UNAUTHORIZED: 'Session expirée - reconnexion nécessaire',
    FORBIDDEN: 'Accès non autorisé',
    NOT_FOUND: 'Ressource non trouvée',
    GENERIC: 'Une erreur inattendue s\'est produite'
  }
} as const

// ✅ CONSERVÉS: TYPES POUR LES RÉPONSES D'API FEEDBACK
export interface FeedbackApiResponse {
  status: 'success' | 'error'
  message: string
  conversation_id: string
  feedback?: number
  comment?: string
  timestamp: string
}

export interface ConversationApiResponse {
  status: 'success' | 'error'
  message: string
  conversation_id: string
  timestamp: string
}

export interface AnalyticsApiResponse {
  status: 'success' | 'error'
  timestamp: string
  analytics: FeedbackAnalytics
  message: string
}

// ✅ CONSERVÉS: TYPE GUARDS POUR LA VALIDATION
export const TypeGuards = {
  isFeedbackType: (value: any): value is 'positive' | 'negative' => {
    return typeof value === 'string' && ['positive', 'negative'].includes(value)
  },

  // 🚀 NOUVEAU: Type guard pour ConcisionLevel
  isConcisionLevel: (value: any): value is ConcisionLevel => {
    return typeof value === 'string' && Object.values(ConcisionLevel).includes(value as ConcisionLevel)
  },

  // 🚀 NOUVEAU: Type guard pour response_versions
  isValidResponseVersions: (value: any): value is Record<string, string> => {
    if (!value || typeof value !== 'object') return false
    return Object.values(ConcisionLevel).some(level => 
      value[level] && typeof value[level] === 'string'
    )
  },
  
  isValidMessage: (value: any): value is Message => {
    return (
      typeof value === 'object' &&
      value !== null &&
      typeof value.id === 'string' &&
      typeof value.content === 'string' &&
      typeof value.isUser === 'boolean' &&
      value.timestamp instanceof Date
    )
  },
  
  isValidUser: (value: any): value is User => {
    return (
      typeof value === 'object' &&
      value !== null &&
      typeof value.id === 'string' &&
      typeof value.email === 'string'
    )
  },

  // ✅ CONSERVÉ: TYPE GUARD POUR CONVERSATION DE BASE
  isValidConversation: (value: any): value is Conversation => {
    return (
      typeof value === 'object' &&
      value !== null &&
      typeof value.id === 'string' &&
      typeof value.title === 'string' &&
      typeof value.preview === 'string' &&
      typeof value.message_count === 'number'
    )
  },

  // ✅ CONSERVÉ: Type guard pour ConversationWithMessages
  isValidConversationWithMessages: (value: any): value is ConversationWithMessages => {
    return (
      typeof value === 'object' &&
      value !== null &&
      typeof value.id === 'string' &&
      typeof value.title === 'string' &&
      typeof value.preview === 'string' &&
      typeof value.message_count === 'number' &&
      Array.isArray(value.messages) &&
      value.messages.every((msg: any) => TypeGuards.isValidMessage(msg))
    )
  },

  isValidConversationGroup: (value: any): value is ConversationGroup => {
    return (
      typeof value === 'object' &&
      value !== null &&
      typeof value.title === 'string' &&
      Array.isArray(value.conversations) &&
      value.conversations.every((conv: any) => TypeGuards.isValidConversation(conv))
    )
  },

  // ✅ CONSERVÉ: Type guard pour clarifications
  isValidClarificationResponse: (value: any): value is ClarificationResponse => {
    return (
      typeof value === 'object' &&
      value !== null &&
      typeof value.needs_clarification === 'boolean'
    )
  }
} as const

// ✅ CONSERVÉE: CONFIGURATION DES CONVERSATIONS
export const CONVERSATION_CONFIG = {
  GROUPING: {
    DEFAULT_OPTIONS: {
      groupBy: 'date' as const,
      sortBy: 'updated_at' as const,
      sortOrder: 'desc' as const,
      limit: 50
    },
    TIME_PERIODS: {
      TODAY: 'Aujourd\'hui',
      YESTERDAY: 'Hier',
      THIS_WEEK: 'Cette semaine',
      THIS_MONTH: 'Ce mois-ci',
      OLDER: 'Plus ancien'
    }
  },
  UI: {
    SIDEBAR_WIDTH: 'w-96', // 384px
    MAX_TITLE_LENGTH: 60,
    MAX_PREVIEW_LENGTH: 150,
    MESSAGES_PER_PAGE: 50,
    AUTO_SCROLL_DELAY: 100
  },
  CACHE: {
    CONVERSATION_LIST_TTL: 5 * 60 * 1000, // 5 minutes
    CONVERSATION_DETAIL_TTL: 10 * 60 * 1000, // 10 minutes
    MAX_CACHED_CONVERSATIONS: 100
  }
} as const

// ✅ CONSERVÉS: UTILITAIRES POUR CONVERSATIONS
export const CONVERSATION_UTILS = {
  generateTitle: (firstMessage: string): string => {
    const maxLength = CONVERSATION_CONFIG.UI.MAX_TITLE_LENGTH
    return firstMessage.length > maxLength 
      ? firstMessage.substring(0, maxLength) + '...' 
      : firstMessage
  },

  generatePreview: (firstMessage: string): string => {
    const maxLength = CONVERSATION_CONFIG.UI.MAX_PREVIEW_LENGTH
    return firstMessage.length > maxLength 
      ? firstMessage.substring(0, maxLength) + '...' 
      : firstMessage
  },

  formatRelativeTime: (timestamp: string): string => {
    const now = new Date()
    const date = new Date(timestamp)
    const diffMs = now.getTime() - date.getTime()
    const diffMinutes = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffMinutes < 1) return 'À l\'instant'
    if (diffMinutes < 60) return `Il y a ${diffMinutes}m`
    if (diffHours < 24) return `Il y a ${diffHours}h`
    if (diffDays < 7) return `Il y a ${diffDays}j`
    
    return ANALYTICS_UTILS.formatTimestamp(timestamp)
  },

  sortConversations: (conversations: Conversation[], sortBy: 'updated_at' | 'created_at' | 'message_count' = 'updated_at'): Conversation[] => {
    return [...conversations].sort((a, b) => {
      switch (sortBy) {
        case 'message_count':
          return b.message_count! - a.message_count!
        case 'created_at':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'updated_at':
        default:
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      }
    })
  }
} as const