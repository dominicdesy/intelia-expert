// types/index.ts

// ============================================================================
// USER & AUTHENTICATION TYPES
// ============================================================================

export interface User {
  id: string
  email: string
  name: string
  avatar_url?: string
  user_type: 'producer' | 'professional'
  language: Language
  created_at: string
  updated_at: string
  consent_given: boolean
  consent_date?: string
}

export interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
}

// ============================================================================
// LANGUAGE & INTERNATIONALIZATION
// ============================================================================

export type Language = 'fr' | 'en' | 'es' | 'pt' | 'de' | 'nl' | 'pl'

export interface LanguageOption {
  code: Language
  name: string
  flag: string
}

// ============================================================================
// CHAT & RAG TYPES
// ============================================================================

export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: string
  feedback?: 'positive' | 'negative'
  sources?: DocumentSource[]
  metadata?: MessageMetadata
}

export interface MessageMetadata {
  response_time?: number
  model_used?: string
  confidence_score?: number
  language_detected?: Language
}

export interface DocumentSource {
  id: string
  title: string
  excerpt: string
  relevance_score: number
  document_type: string
  url?: string
}

export interface Conversation {
  id: string
  user_id: string
  title?: string
  messages: Message[]
  created_at: string
  updated_at: string
  language: Language
}

// ============================================================================
// RAG SYSTEM TYPES
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

// ============================================================================
// FEEDBACK & ANALYTICS
// ============================================================================

export interface FeedbackData {
  message_id: string
  rating: 'positive' | 'negative'
  comment?: string
  category?: 'accuracy' | 'relevance' | 'completeness' | 'other'
}

export interface UsageAnalytics {
  daily_questions: number
  satisfaction_rate: number
  avg_response_time: number
  popular_topics: string[]
  user_retention: number
}

// ============================================================================
// API RESPONSE TYPES
// ============================================================================

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

// ============================================================================
// RGPD & DATA PROTECTION
// ============================================================================

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

// ============================================================================
// ERROR HANDLING
// ============================================================================

export interface AppError {
  code: string
  message: string
  details?: any
  timestamp: string
  user_id?: string
  context?: string
}