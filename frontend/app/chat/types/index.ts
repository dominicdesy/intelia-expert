// ==================== TYPES PRINCIPAUX ====================

export interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  feedback?: 'positive' | 'negative' | null
  conversation_id?: string
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

export interface ConversationData {
  user_id: string
  question: string
  response: string
  conversation_id: string
  confidence_score?: number
  response_time_ms?: number
  language?: string
  rag_used?: boolean
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
}

// ==================== TYPES UTILISATEUR ====================

export interface User {
  id: string
  email: string
  name: string
  firstName: string
  lastName: string
  phone: string
  country: string
  linkedinProfile: string
  companyName: string
  companyWebsite: string
  linkedinCorporate: string
  user_type: string
  language: string
  created_at: string
  plan: string
}

export interface ProfileUpdateData {
  firstName: string
  lastName: string
  email: string
  phone: string
  country: string
  linkedinProfile: string
  companyName: string
  companyWebsite: string
  linkedinCorporate: string
  language?: string
}

// ==================== TYPES HOOKS ====================

export interface AuthStore {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  logout: () => Promise<void>
  updateProfile: (data: ProfileUpdateData) => Promise<{ success: boolean; error?: string }>
}

export interface ChatStore {
  conversations: ConversationItem[]
  isLoading: boolean
  loadConversations: (userId: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  clearAllConversations: (userId?: string) => Promise<void>
  refreshConversations: (userId: string) => Promise<void>
  addConversation: (conversationId: string, question: string, response: string) => void
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

// ==================== CONSTANTES ====================

export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'https://expert-app-cngws.ondigitalocean.app',
  TIMEOUT: 30000,
  LOGGING_BASE_URL: 'https://expert-app-cngws.ondigitalocean.app/api/v1'
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