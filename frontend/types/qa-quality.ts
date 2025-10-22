/**
 * Types pour le système de monitoring de qualité Q&A
 */

export interface ProblematicQA {
  id: string;
  conversation_id: string;
  message_id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  question: string;
  response: string;
  response_source: string | null;
  response_confidence: number | null;
  quality_score: number | null;
  problem_category: ProblemCategory;
  problems: string[];
  recommendation: string;
  analysis_confidence: number | null;
  language: string;
  analyzed_at: string;
  conversation_created_at: string;
  reviewed: boolean;
  reviewed_at: string | null;
  reviewed_by: string | null;
  reviewer_notes: string | null;
}

export type ProblemCategory =
  | "incorrect"
  | "incomplete"
  | "off_topic"
  | "generic"
  | "contradictory"
  | "hallucination"
  | "none";

export interface QualityStats {
  period_days: number;
  total_analyzed: number;
  total_problematic: number;
  problematic_rate: number;
  total_reviewed: number;
  total_false_positives: number;
  avg_quality_score: number;
  avg_confidence: number;
  category_distribution: Record<string, number>;
  timeline: Array<{
    date: string;
    total: number;
    problematic: number;
  }>;
}

export interface ProblematicQAResponse {
  problematic_qa: ProblematicQA[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
  filters_applied: {
    category: string | null;
    reviewed: boolean | null;
    min_score: number | null;
    max_score: number | null;
  };
}

export interface AnalyzeBatchResponse {
  status: string;
  analyzed_count: number;
  problematic_found: number;
  errors: number;
  timestamp: string;
}

export interface ReviewQARequest {
  reviewed: boolean;
  false_positive: boolean;
  reviewer_notes?: string;
}

export interface ReviewQAResponse {
  id: string;
  reviewed: boolean;
  false_positive: boolean;
  message: string;
}

export interface CoTAnalysisResponse {
  check_id: number;
  response: string;
  thinking: string;
  thinking_tokens: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  analyzed_at: string;
  analyzed_by: string;
  original_question: string;
  original_response: string;
}
