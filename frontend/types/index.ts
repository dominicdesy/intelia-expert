// types/index.ts - SOLUTION FINALE

// ============================================================================
// USER & AUTHENTICATION TYPES - ALIGNÉS AVEC LE BACKEND
// ============================================================================

export interface User {
  id: string
  email: string
  name?: string                    // ✅ Optionnel (peut venir de full_name ou être undefined)
  full_name?: string              // ✅ Correspondance backend
  avatar_url?: string
  user_type?: 'producer' | 'professional' | 'super_admin' | 'user' | 'admin'  // ✅ Aligné backend
  language?: Language             // ✅ Optionnel car peut ne pas être défini
  created_at?: string            // ✅ Optionnel
  updated_at?: string            // ✅ Optionnel
  consent_given?: boolean        // ✅ Optionnel
  consent_date?: string
  plan?: string                  // ✅ Pour les abonnements
  
  // ✅ NOUVEAUX CHAMPS DU BACKEND
  user_id?: string               // Backend utilise user_id
  profile_id?: string            // ID du profil Supabase
  preferences?: Record<string, any>  // Préférences utilisateur
  is_admin?: boolean             // Rétrocompatibilité backend
}

// ✅ INTERFACE SÉPARÉE POUR LES DONNÉES REÇUES DU BACKEND
export interface BackendUserData {
  user_id: string
  email: string
  user_type: string
  full_name?: string
  is_admin: boolean
  preferences?: Record<string, any>
  profile_id?: string
  iss?: string
  aud?: string
  exp?: number
  jwt_secret_used?: string
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

// ============================================================================
// UTILITY FUNCTIONS POUR CONVERSION BACKEND -> FRONTEND
// ============================================================================

/**
 * ✅ Fonction utilitaire pour convertir les données backend en User frontend
 */
export function mapBackendUserToUser(backendUser: BackendUserData): User {
  return {
    id: backendUser.user_id,
    email: backendUser.email,
    name: backendUser.full_name || backendUser.email,
    full_name: backendUser.full_name,
    user_type: backendUser.user_type as User['user_type'],
    profile_id: backendUser.profile_id,
    preferences: backendUser.preferences,
    is_admin: backendUser.is_admin,
    language: 'fr', // Défaut - à récupérer des préférences si disponible
    created_at: new Date().toISOString(), // Défaut
    updated_at: new Date().toISOString(), // Défaut
    consent_given: true // Défaut - à ajuster selon vos besoins
  }
}