// ==================== TYPES PRINCIPAUX ====================

// ✅ INTERFACE MESSAGE ÉTENDUE AVEC COMMENTAIRES FEEDBACK
export interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  feedback?: 'positive' | 'negative' | null
  conversation_id?: string
  feedbackComment?: string  // ✅ NOUVEAU: Commentaire associé au feedback
}

export interface ExpertApiResponse {
  question: string
  response: string
  conversation_id: string
  rag_used: boolean
  rag_score?: number
  timestamp: string
  language: string
  response_time_ms: number
  mode: string
  user?: string
}

// ✅ INTERFACE ConversationData ÉTENDUE AVEC FEEDBACK
export interface ConversationData {
  user_id: string
  question: string
  response: string
  conversation_id: string
  confidence_score?: number
  response_time_ms?: number
  language?: string
  rag_used?: boolean
  feedback?: 1 | -1 | null          // ✅ NOUVEAU: Feedback numérique pour le backend
  feedback_comment?: string          // ✅ NOUVEAU: Commentaire feedback
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
  feedback_comment?: string  // ✅ NOUVEAU: Commentaire dans l'historique
}

// ==================== NOUVEAUX TYPES POUR CONVERSATIONS STYLE CLAUDE.AI ====================

// ✅ NOUVEAU: Structure complète d'une conversation
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
}

// ✅ NOUVEAU: Conversation complète avec tous ses messages
export interface ConversationWithMessages extends Conversation {
  messages: Message[]
}

// ✅ NOUVEAU: Structure pour l'historique groupé
export interface ConversationGroup {
  title: string  // "Aujourd'hui", "Hier", "Cette semaine", etc.
  conversations: Conversation[]
}

// ✅ NOUVEAU: Réponse API pour l'historique
export interface ConversationHistoryResponse {
  success: boolean
  conversations: Conversation[]
  groups?: ConversationGroup[]
  total_count: number
  user_id: string
  timestamp: string
}

// ✅ NOUVEAU: Réponse API pour une conversation complète
export interface ConversationDetailResponse {
  success: boolean
  conversation: ConversationWithMessages
  timestamp: string
}

// ✅ NOUVEAU: Options pour le groupement des conversations
export interface ConversationGroupingOptions {
  groupBy: 'date' | 'topic' | 'none'
  sortBy: 'updated_at' | 'created_at' | 'message_count'
  sortOrder: 'desc' | 'asc'
  limit?: number
  offset?: number
}

// ✅ NOUVEAU: Statistiques de conversation
export interface ConversationStats {
  total_conversations: number
  total_messages: number
  avg_messages_per_conversation: number
  most_active_day: string
  favorite_topics: string[]
  satisfaction_rate: number
}

// ==================== TYPES UTILISATEUR AVEC CHAMPS TÉLÉPHONE ====================

export interface User {
  id: string
  email: string
  name: string
  firstName: string
  lastName: string
  phone: string  // ⚠️ Champ existant - gardé pour compatibilité
  country: string
  linkedinProfile: string
  companyName: string
  companyWebsite: string
  linkedinCorporate: string
  user_type: string
  language: string
  created_at: string
  plan: string
  
  // ✅ NOUVEAUX CHAMPS TÉLÉPHONE SÉPARÉS POUR SUPABASE
  country_code?: string    // Code pays (ex: +1, +33, +32)
  area_code?: string       // Code régional (ex: 514, 04, 2)
  phone_number?: string    // Numéro principal (ex: 1234567, 12345678)
}

export interface ProfileUpdateData {
  firstName: string
  lastName: string
  email: string
  phone?: string  // ✅ CORRIGÉ : Maintenant optionnel pour éviter les conflits
  country: string
  linkedinProfile: string
  companyName: string
  companyWebsite: string
  linkedinCorporate: string
  language?: string
  
  // ✅ NOUVEAUX CHAMPS TÉLÉPHONE SÉPARÉS
  country_code?: string
  area_code?: string
  phone_number?: string
}

// ==================== TYPES SPÉCIFIQUES AU COMPOSANT PHONE ====================

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

// ==================== NOUVEAUX TYPES FEEDBACK ET COMMENTAIRES ====================

// ✅ NOUVEAU: Interface pour les données feedback enrichies
export interface FeedbackData {
  conversation_id: string
  feedback: 'positive' | 'negative'
  comment?: string
  timestamp: string
  user_id?: string
}

// ✅ NOUVEAU: Props pour la modal feedback
export interface FeedbackModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (feedback: 'positive' | 'negative', comment?: string) => Promise<void>
  feedbackType: 'positive' | 'negative'
  isSubmitting?: boolean
}

// ✅ NOUVEAU: Interface pour les analytics feedback
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

// ✅ NOUVEAU: Interface pour le rapport admin feedback
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

// ✅ NOUVEAU: Interface pour les statistiques utilisateur
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

// ==================== TYPES HOOKS AVEC CONVERSATIONS ====================

export interface AuthStore {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  logout: () => Promise<void>
  updateProfile: (data: ProfileUpdateData) => Promise<{ success: boolean; error?: string }>
}

// ✅ MISE À JOUR: ChatStore pour gérer les conversations
export interface ChatStore {
  // ✅ PROPRIÉTÉS EXISTANTES CONSERVÉES
  conversations: ConversationItem[]
  isLoading: boolean
  loadConversations: (userId: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  clearAllConversations: (userId?: string) => Promise<void>
  refreshConversations: (userId: string) => Promise<void>
  addConversation: (conversationId: string, question: string, response: string) => void

  // ✅ NOUVELLES PROPRIÉTÉS POUR CONVERSATIONS STYLE CLAUDE.AI
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

// ==================== TYPES COMPOSANTS ====================

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

// ==================== TYPES API ====================

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

// ==================== CONSTANTES API ====================

export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'https://expert-app-cngws.ondigitalocean.app',
  TIMEOUT: 30000,
  LOGGING_BASE_URL: 'https://expert-app-cngws.ondigitalocean.app/api/v1'
} as const

// ✅ NOUVEAUX ENDPOINTS FEEDBACK
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

// ✅ NOUVELLE CONFIGURATION FEEDBACK
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

// ✅ UTILITAIRES ANALYTICS
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

// ✅ CONSTANTES DE VALIDATION
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
  // ✅ NOUVELLES RÈGLES POUR CONVERSATIONS
  CONVERSATION: {
    TITLE_MAX_LENGTH: 60,
    PREVIEW_MAX_LENGTH: 150,
    MESSAGE_MAX_LENGTH: 5000,
    MAX_CONVERSATIONS_PER_USER: 1000,
    AUTO_DELETE_DAYS: 30
  }
} as const

// ✅ MESSAGES D'ERREUR LOCALISÉS
export const ERROR_MESSAGES = {
  FEEDBACK: {
    SUBMISSION_FAILED: 'Erreur lors de l\'envoi du feedback. Veuillez réessayer.',
    INVALID_CONVERSATION_ID: 'Impossible d\'enregistrer le feedback - ID de conversation manquant',
    COMMENT_TOO_LONG: `Le commentaire ne peut pas dépasser ${VALIDATION_RULES.FEEDBACK.COMMENT_MAX_LENGTH} caractères`,
    NETWORK_ERROR: 'Problème de connexion réseau. Vérifiez votre connexion internet.',
    SERVER_ERROR: 'Erreur serveur. Veuillez réessayer plus tard.',
    TIMEOUT_ERROR: 'Timeout - le serveur met trop de temps à répondre'
  },
  // ✅ NOUVEAUX MESSAGES POUR CONVERSATIONS
  CONVERSATION: {
    LOAD_FAILED: 'Erreur lors du chargement de la conversation',
    DELETE_FAILED: 'Erreur lors de la suppression de la conversation',
    NOT_FOUND: 'Conversation non trouvée',
    EMPTY_MESSAGE: 'Le message ne peut pas être vide',
    MESSAGE_TOO_LONG: `Le message ne peut pas dépasser ${VALIDATION_RULES.CONVERSATION.MESSAGE_MAX_LENGTH} caractères`,
    CREATION_FAILED: 'Erreur lors de la création de la conversation'
  },
  GENERAL: {
    UNAUTHORIZED: 'Session expirée - reconnexion nécessaire',
    FORBIDDEN: 'Accès non autorisé',
    NOT_FOUND: 'Ressource non trouvée',
    GENERIC: 'Une erreur inattendue s\'est produite'
  }
} as const

// ✅ TYPES POUR LES RÉPONSES D'API FEEDBACK
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

// ✅ TYPE GUARDS POUR LA VALIDATION
export const TypeGuards = {
  isFeedbackType: (value: any): value is 'positive' | 'negative' => {
    return typeof value === 'string' && ['positive', 'negative'].includes(value)
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

  // ✅ NOUVEAUX TYPE GUARDS POUR CONVERSATIONS
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

  isValidConversationWithMessages: (value: any): value is ConversationWithMessages => {
    return (
      TypeGuards.isValidConversation(value) &&
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
  }
} as const

// ✅ CONFIGURATION DES CONVERSATIONS
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

// ✅ UTILITAIRES POUR CONVERSATIONS
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
          return b.message_count - a.message_count
        case 'created_at':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'updated_at':
        default:
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      }
    })
  }
} as const