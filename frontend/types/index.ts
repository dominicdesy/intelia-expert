import { secureLog } from "@/lib/utils/secureLogger";

// types/index.ts - VERSION COMPLÈTE AVEC SUPPORT RAG JSON + TOUT LE CONTENU ORIGINAL

// ==================== NOUVEAUX TYPES RAG JSON AVICOLE ====================

// Types pour les données avicoles structurées
export interface GeneticLineData {
  line: 'ross308' | 'ross308ap' | 'cobb500' | 'cobb700' | 'hubbard' | 'aviagen' | 'other';
  variant?: string;
  region?: 'global' | 'na' | 'eu' | 'asia' | 'latam' | 'mena';
  standard?: string;
}

export interface PerformanceMetric {
  type: 'weight' | 'fcr' | 'mortality' | 'egg_production' | 'feed_intake' | 'growth_rate';
  value: number;
  unit: string;
  age_days?: number;
  sex?: 'male' | 'female' | 'mixed';
  confidence?: number;
}

export interface AvicultureDocument {
  id: string;
  title: string;
  text: string;
  metadata: {
    genetic_line?: GeneticLineData;
    document_type: 'performance_guide' | 'feeding_guide' | 'management_guide' | 'health_guide' | 'technical_data';
    effective_date?: string;
    language: string;
    region?: string;
    source?: string;
  };
  tables?: PerformanceTable[];
  figures?: DocumentFigure[];
  performance_records?: PerformanceMetric[];
}

export interface PerformanceTable {
  id?: string;
  title: string;
  headers: string[];
  rows: string[][];
  metadata?: {
    genetic_line?: string;
    age_range?: { min: number; max: number };
    sex?: 'male' | 'female' | 'mixed';
    metric_types?: string[];
  };
}

export interface DocumentFigure {
  id?: string;
  title: string;
  description?: string;
  url?: string;
  caption?: string;
  metadata?: {
    figure_type: 'chart' | 'table' | 'image' | 'diagram';
    genetic_line?: string;
    metrics?: string[];
  };
}

// Types pour la validation JSON
export interface JSONValidationRequest {
  json_data: AvicultureDocument;
  strict_mode?: boolean;
  auto_enrich?: boolean;
  validate_performance_data?: boolean;
}

export interface JSONValidationResult {
  is_valid: boolean;
  enriched_data?: AvicultureDocument;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  metadata: {
    validation_version: string;
    processing_time_ms: number;
    genetic_lines_detected: string[];
    performance_metrics_count: number;
    tables_processed: number;
    figures_processed: number;
  };
}

export interface ValidationError {
  field: string;
  code: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
  suggestions?: string[];
}

export interface ValidationWarning {
  field: string;
  code: string;
  message: string;
  auto_fix_applied?: boolean;
  original_value?: any;
  corrected_value?: any;
}

// Types pour l'ingestion JSON
export interface JSONIngestionRequest {
  json_files: AvicultureDocument[];
  batch_size?: number;
  force_reprocess?: boolean;
  validation_config?: {
    strict_mode: boolean;
    auto_enrich: boolean;
    skip_invalid: boolean;
    validate_performance_data: boolean;
  };
}

export interface JSONIngestionResult {
  success: boolean;
  processed_count: number;
  total_count: number;
  errors: IngestionError[];
  warnings: IngestionWarning[];
  metadata: {
    processing_time_ms: number;
    genetic_lines_processed: string[];
    performance_records_created: number;
    documents_indexed: number;
    batch_size_used: number;
  };
}

export interface IngestionError {
  document_index: number;
  document_title?: string;
  error_code: string;
  error_message: string;
  details?: any;
}

export interface IngestionWarning {
  document_index: number;
  document_title?: string;
  warning_code: string;
  warning_message: string;
  auto_corrected?: boolean;
}

// Types pour la recherche JSON avancée
export interface JSONSearchRequest {
  query: string;
  filters?: {
    genetic_line?: string | string[];
    document_type?: string | string[];
    performance_metrics?: string | string[];
    age_range?: { min: number; max: number };
    sex?: 'male' | 'female' | 'mixed';
    region?: string | string[];
    language?: string;
    effective_date_range?: { start: string; end: string };
  };
  search_config?: {
    use_semantic_search: boolean;
    use_bm25_search: boolean;
    hybrid_alpha?: number;
    top_k?: number;
    confidence_threshold?: number;
    include_performance_data: boolean;
    include_tables: boolean;
    include_figures: boolean;
  };
}

export interface JSONSearchResult {
  success: boolean;
  results: AvicultureSearchResult[];
  total_found: number;
  search_metadata: {
    query_processed: string;
    search_type: 'semantic' | 'bm25' | 'hybrid';
    processing_time_ms: number;
    filters_applied: string[];
    genetic_lines_searched: string[];
    performance_data_included: boolean;
  };
}

export interface AvicultureSearchResult {
  document: AvicultureDocument;
  score: number;
  relevance_explanation?: string;
  matched_sections?: {
    text_matches: string[];
    table_matches: PerformanceTable[];
    figure_matches: DocumentFigure[];
    performance_matches: PerformanceMetric[];
  };
}

// Types pour l'API Chat étendue avec JSON
export interface JSONEnhancedChatRequest {
  message: string;
  language?: string;
  tenant_id?: string;
  // Paramètres JSON spécifiques
  genetic_line_filter?: string;
  use_json_search?: boolean;
  performance_context?: {
    metrics?: string[];
    age_range?: { min: number; max: number };
    sex?: 'male' | 'female' | 'mixed';
    focus_areas?: string[];
  };
  response_preferences?: {
    include_performance_data: boolean;
    include_tables: boolean;
    include_figures: boolean;
    detailed_explanations: boolean;
  };
}

export interface JSONEnhancedChatResponse {
  question: string;
  response: string;
  conversation_id: string;
  rag_used: boolean;
  rag_score?: number;
  timestamp: string;
  language: string;
  response_time_ms: number;
  mode: string;
  user?: string;
  logged: boolean;
  
  // Métadonnées JSON spécifiques
  json_system_metadata?: {
    json_search_used: boolean;
    json_results_count: number;
    genetic_lines_detected: string[];
    performance_data_included: boolean;
    tables_included: number;
    figures_included: number;
    confidence_score: number;
  };
  
  // Sources de données avicoles
  aviculture_sources?: {
    documents_used: AvicultureDocument[];
    performance_metrics: PerformanceMetric[];
    tables_referenced: PerformanceTable[];
    figures_referenced: DocumentFigure[];
  };
  
  // Recommandations basées sur les données
  recommendations?: {
    next_questions: string[];
    related_topics: string[];
    performance_insights: string[];
    best_practices: string[];
  };
}

// Types pour les extracteurs spécialisés
export interface TableExtractionResult {
  success: boolean;
  tables: PerformanceTable[];
  metadata: {
    extraction_method: string;
    confidence_score: number;
    processing_time_ms: number;
    errors: string[];
    warnings: string[];
  };
}

export interface GeneticLineExtractionResult {
  success: boolean;
  genetic_lines: GeneticLineData[];
  confidence_scores: Record<string, number>;
  metadata: {
    extraction_method: string;
    processing_time_ms: number;
    ambiguous_references: string[];
    auto_corrections: Array<{
      original: string;
      corrected: string;
      confidence: number;
    }>;
  };
}

export interface PerformanceExtractionResult {
  success: boolean;
  performance_metrics: PerformanceMetric[];
  metadata: {
    extraction_method: string;
    total_metrics_found: number;
    validated_metrics: number;
    processing_time_ms: number;
    unit_conversions: Array<{
      original_unit: string;
      converted_unit: string;
      conversion_factor: number;
    }>;
  };
}

// ==================== TYPES EXISTANTS ÉTENDUS ====================

// Extension de ExpertApiResponse pour support JSON
export interface ExpertApiResponse {
  question: string;
  response: string;
  full_text?: string;
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
  
  // CHAMPS POUR VERSIONS BACKEND
  response_versions?: {
    ultra_concise: string;
    concise: string;
    standard: string;
    detailed: string;
  };
  
  // AGENT METADATA
  agent_metadata?: AgentMetadata;
  
  // NOUVEAU: MÉTADONNÉES JSON
  json_system_metadata?: {
    json_search_used: boolean;
    json_results_count: number;
    genetic_lines_detected: string[];
    performance_data_included: boolean;
    extraction_stats: {
      tables_processed: number;
      figures_processed: number;
      performance_metrics: number;
    };
  };
}

// Extension de Message pour support JSON
export interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  feedback?: "positive" | "negative" | null;
  conversation_id?: string;
  feedbackComment?: string;

  // CHAMPS POUR CLARIFICATION
  is_clarification_request?: boolean;
  is_clarification_response?: boolean;
  clarification_questions?: string[];
  clarification_answers?: Record<string, string>;
  original_question?: string;
  clarification_entities?: Record<string, any>;

  // CHAMPS POUR CONCISION BACKEND
  response_versions?: {
    ultra_concise: string;
    concise: string;
    standard: string;
    detailed: string;
  };

  // AGENT METADATA
  agent_metadata?: AgentMetadata;

  // NOUVEAU: MÉTADONNÉES JSON AVICOLE
  json_metadata?: {
    genetic_lines_mentioned: string[];
    performance_metrics_discussed: PerformanceMetric[];
    tables_referenced: PerformanceTable[];
    figures_referenced: DocumentFigure[];
    aviculture_topics: string[];
  };

  // Champs pour compatibilité
  originalResponse?: string;
  processedResponse?: string;
  concisionLevel?: ConcisionLevel;
  role?: "user" | "assistant";
  sources?: DocumentSource[];
  metadata?: MessageMetadata;

  // Images attachées au message
  imageUrl?: string; // Deprecated: use imageUrls instead
  imageUrls?: string[]; // Support for multiple images
}

// ==================== NOUVEAUX TYPES AGENT LLM ====================

export interface AgentMetadata {
  complexity: string;
  sub_queries_count: number;
  synthesis_method: string;
  sources_used: number;
  processing_time?: number;
  decisions?: string[];
  response_source?: string; // 🆕 Source réelle de la réponse (PostgreSQL/Weaviate/External LLM)
}

export interface StreamCallbacks {
  onStart?: (data: any) => void;
  onDelta?: (text: string) => void;
  onFinal?: (text: string) => void;
  onError?: (error: any) => void;
  onFollowup?: (msg: string) => void;

  // NOUVEAUX CALLBACKS AGENT
  onAgentStart?: (complexity: string, subQueries: number) => void;
  onAgentThinking?: (decisions: string[]) => void;
  onChunk?: (content: string, confidence: number, source?: string) => void;
  onAgentEnd?: (synthesisMethod: string, sourcesUsed: number) => void;
  onAgentError?: (error: string) => void;
  onAgentProgress?: (step: string, progress: number) => void;
  
  // NOUVEAUX CALLBACKS JSON
  onJSONSearchStart?: (filters: any) => void;
  onJSONResults?: (results: AvicultureSearchResult[]) => void;
  onPerformanceData?: (metrics: PerformanceMetric[]) => void;
  onGeneticLineDetected?: (lines: string[]) => void;
}

// Types d'événements SSE Agent étendus avec JSON
export type AgentStartEvent = {
  type: "agent_start";
  complexity: string;
  sub_queries_count: number;
};

export type JSONSearchStartEvent = {
  type: "json_search_start";
  filters: Record<string, any>;
  genetic_lines: string[];
};

export type JSONResultsEvent = {
  type: "json_results";
  results_count: number;
  genetic_lines_found: string[];
  performance_data_included: boolean;
};

export type PerformanceDataEvent = {
  type: "performance_data";
  metrics: PerformanceMetric[];
  tables_count: number;
  figures_count: number;
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

export type EndEvent = {
  type: "end";
  total_time?: number;
  confidence?: number;
  documents_used?: number;
  source?: string;
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
  | ProactiveFollowupEvent
  | JSONSearchStartEvent
  | JSONResultsEvent
  | PerformanceDataEvent
  | EndEvent;

// ==================== NOUVEAUX ENDPOINTS JSON ====================

export const JSON_ENDPOINTS = {
  // Validation et ingestion
  VALIDATE_JSON: "/json/validate",
  INGEST_JSON: "/json/ingest",
  UPLOAD_JSON: "/json/upload",
  
  // Recherche avancée
  SEARCH_JSON: "/json/search",
  SEARCH_PERFORMANCE: "/json/search/performance",
  SEARCH_BY_GENETIC_LINE: "/json/search/genetic-line",
  
  // Extraction spécialisée
  EXTRACT_TABLES: "/json/extract/tables",
  EXTRACT_GENETIC_LINES: "/json/extract/genetic-lines",
  EXTRACT_PERFORMANCE: "/json/extract/performance",
  
  // Analytics et monitoring
  JSON_SYSTEM_STATUS: "/json/status",
  JSON_ANALYTICS: "/json/analytics",
  JSON_HEALTH_CHECK: "/json/health",
  
  // Chat étendu
  CHAT_WITH_JSON: "/chat/json-enhanced",
  EXPERT_CHAT_JSON: "/chat/expert-json",
  
  // Tests spécialisés
  TEST_JSON_SYSTEM: "/chat/test-json-system",
  TEST_GENETIC_LINES: "/chat/test-genetic-lines",
  TEST_PERFORMANCE_DATA: "/chat/test-performance-data",
} as const;

// ==================== CONFIGURATION JSON SYSTEM ====================

export const JSON_SYSTEM_CONFIG = {
  // Types de documents supportés
  DOCUMENT_TYPES: {
    PERFORMANCE_GUIDE: "performance_guide",
    FEEDING_GUIDE: "feeding_guide", 
    MANAGEMENT_GUIDE: "management_guide",
    HEALTH_GUIDE: "health_guide",
    TECHNICAL_DATA: "technical_data",
  },
  
  // Lignées génétiques supportées
  GENETIC_LINES: {
    ROSS308: "ross308",
    ROSS308AP: "ross308ap", 
    COBB500: "cobb500",
    COBB700: "cobb700",
    HUBBARD: "hubbard",
    AVIAGEN: "aviagen",
    OTHER: "other",
  },
  
  // Métriques de performance
  PERFORMANCE_METRICS: {
    WEIGHT: "weight",
    FCR: "fcr",
    MORTALITY: "mortality", 
    EGG_PRODUCTION: "egg_production",
    FEED_INTAKE: "feed_intake",
    GROWTH_RATE: "growth_rate",
  },
  
  // Unités standardisées
  UNITS: {
    WEIGHT: ["g", "kg", "lb", "oz"],
    TEMPERATURE: ["°C", "°F", "K"],
    VOLUME: ["ml", "l", "gal", "fl oz"],
    PERCENTAGE: ["%", "percent"],
    RATIO: ["ratio", ":1", "to 1"],
  },
  
  // Configuration de validation
  VALIDATION: {
    MAX_DOCUMENT_SIZE_MB: 10,
    MAX_TABLES_PER_DOCUMENT: 50,
    MAX_FIGURES_PER_DOCUMENT: 20,
    MAX_PERFORMANCE_RECORDS: 1000,
    REQUIRED_FIELDS: ["title", "text", "metadata"],
    OPTIONAL_FIELDS: ["tables", "figures", "performance_records"],
  },
  
  // Configuration de recherche
  SEARCH: {
    DEFAULT_TOP_K: 10,
    MAX_TOP_K: 50,
    DEFAULT_CONFIDENCE_THRESHOLD: 0.7,
    HYBRID_ALPHA_DEFAULT: 0.5,
    ENABLE_SEMANTIC_SEARCH: true,
    ENABLE_BM25_SEARCH: true,
    ENABLE_HYBRID_SEARCH: true,
  },
  
  // Configuration de cache
  CACHE: {
    VALIDATION_CACHE_TTL: 3600, // 1 heure
    SEARCH_CACHE_TTL: 1800, // 30 minutes
    EXTRACTION_CACHE_TTL: 7200, // 2 heures
    MAX_CACHED_DOCUMENTS: 1000,
  },
} as const;

// ==================== UTILITAIRES JSON SYSTEM ====================

export const JSONSystemUtils = {
  // Validation des données avicoles
  validateGeneticLine: (line: string): boolean => {
    const validLines: string[] = Object.values(JSON_SYSTEM_CONFIG.GENETIC_LINES);
    return validLines.includes(line);
  },
  
  validatePerformanceMetric: (metric: PerformanceMetric): ValidationError[] => {
    const errors: ValidationError[] = [];
    
    if (!metric.type || !Object.values(JSON_SYSTEM_CONFIG.PERFORMANCE_METRICS).includes(metric.type)) {
      errors.push({
        field: "type",
        code: "INVALID_METRIC_TYPE",
        message: `Type de métrique invalide: ${metric.type}`,
        severity: "error",
      });
    }
    
    if (typeof metric.value !== "number" || metric.value < 0) {
      errors.push({
        field: "value", 
        code: "INVALID_METRIC_VALUE",
        message: "Valeur métrique doit être un nombre positif",
        severity: "error",
      });
    }
    
    if (!metric.unit || typeof metric.unit !== "string") {
      errors.push({
        field: "unit",
        code: "MISSING_UNIT",
        message: "Unité requise pour la métrique",
        severity: "error",
      });
    }
    
    return errors;
  },
  
  // Normalisation des unités
  normalizeUnit: (value: number, fromUnit: string, toUnit: string): number => {
    const conversionTable: Record<string, Record<string, number | ((val: number) => number)>> = {
      // Poids
      "g": { "kg": 0.001, "lb": 0.00220462, "oz": 0.035274 },
      "kg": { "g": 1000, "lb": 2.20462, "oz": 35.274 },
      "lb": { "g": 453.592, "kg": 0.453592, "oz": 16 },
      "oz": { "g": 28.3495, "kg": 0.0283495, "lb": 0.0625 },
      
      // Température
      "°C": { 
        "°F": (c: number) => (c * 9/5) + 32, 
        "K": (c: number) => c + 273.15 
      },
      "°F": { 
        "°C": (f: number) => (f - 32) * 5/9, 
        "K": (f: number) => ((f - 32) * 5/9) + 273.15 
      },
      "K": { 
        "°C": (k: number) => k - 273.15, 
        "°F": (k: number) => ((k - 273.15) * 9/5) + 32 
      },
    };
    
    if (fromUnit === toUnit) return value;
    
    const conversion = conversionTable[fromUnit]?.[toUnit];
    if (typeof conversion === "number") {
      return value * conversion;
    } else if (typeof conversion === "function") {
      return conversion(value);
    }
    
    return value; // Pas de conversion disponible
  },
  
  // Détection automatique de lignée génétique
  detectGeneticLine: (text: string): { line: string; confidence: number }[] => {
    const patterns = {
      ross308: /ross\s*308/gi,
      ross308ap: /ross\s*308\s*ap/gi,
      cobb500: /cobb\s*500/gi,
      cobb700: /cobb\s*700/gi,
      hubbard: /hubbard/gi,
      aviagen: /aviagen/gi,
    };
    
    const detections: { line: string; confidence: number }[] = [];
    
    Object.entries(patterns).forEach(([line, pattern]) => {
      const matches = text.match(pattern);
      if (matches) {
        const confidence = Math.min(0.95, 0.5 + (matches.length * 0.1));
        detections.push({ line, confidence });
      }
    });
    
    return detections.sort((a, b) => b.confidence - a.confidence);
  },
  
  // Extraction de métriques de performance du texte
  extractPerformanceMetrics: (text: string): PerformanceMetric[] => {
    const metrics: PerformanceMetric[] = [];
    
    // Patterns pour différentes métriques
    const patterns = {
      weight: /(\d+(?:\.\d+)?)\s*(g|kg|lb|oz)(?:\s*(?:at|à)\s*(\d+)\s*(?:days?|jours?))?/gi,
      fcr: /fcr\s*:?\s*(\d+(?:\.\d+)?)/gi,
      mortality: /mortalit[éy]\s*:?\s*(\d+(?:\.\d+)?)\s*%?/gi,
    };
    
    // Extraction poids
    let match;
    while ((match = patterns.weight.exec(text)) !== null) {
      metrics.push({
        type: "weight",
        value: parseFloat(match[1]),
        unit: match[2],
        age_days: match[3] ? parseInt(match[3]) : undefined,
      });
    }
    
    // Extraction FCR
    patterns.fcr.lastIndex = 0;
    while ((match = patterns.fcr.exec(text)) !== null) {
      metrics.push({
        type: "fcr",
        value: parseFloat(match[1]),
        unit: "ratio",
      });
    }
    
    // Extraction mortalité
    patterns.mortality.lastIndex = 0;
    while ((match = patterns.mortality.exec(text)) !== null) {
      metrics.push({
        type: "mortality",
        value: parseFloat(match[1]),
        unit: "%",
      });
    }
    
    return metrics;
  },
  
  // Validation de document avicole complet
  validateAvicultureDocument: (doc: AvicultureDocument): JSONValidationResult => {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];
    
    // Validation des champs requis
    if (!doc.title || doc.title.trim().length < 5) {
      errors.push({
        field: "title",
        code: "INVALID_TITLE",
        message: "Titre requis (minimum 5 caractères)",
        severity: "error",
      });
    }
    
    if (!doc.text || doc.text.trim().length < 50) {
      errors.push({
        field: "text", 
        code: "INVALID_TEXT",
        message: "Texte requis (minimum 50 caractères)",
        severity: "error",
      });
    }
    
    if (!doc.metadata || !doc.metadata.document_type) {
      errors.push({
        field: "metadata.document_type",
        code: "MISSING_DOCUMENT_TYPE",
        message: "Type de document requis",
        severity: "error",
      });
    }
    
    // Validation des métriques de performance
    if (doc.performance_records) {
      doc.performance_records.forEach((metric, index) => {
        const metricErrors = JSONSystemUtils.validatePerformanceMetric(metric);
        errors.push(...metricErrors.map(error => ({
          ...error,
          field: `performance_records[${index}].${error.field}`,
        })));
      });
    }
    
    // Détection automatique de lignée génétique
    const detectedLines = JSONSystemUtils.detectGeneticLine(doc.text);
    
    return {
      is_valid: errors.length === 0,
      errors,
      warnings,
      metadata: {
        validation_version: "4.0",
        processing_time_ms: 0, // À remplir par le processeur
        genetic_lines_detected: detectedLines.map(d => d.line),
        performance_metrics_count: doc.performance_records?.length || 0,
        tables_processed: doc.tables?.length || 0,
        figures_processed: doc.figures?.length || 0,
      },
    };
  },
  
  // Formatage pour affichage
  formatPerformanceMetric: (metric: PerformanceMetric): string => {
    const ageStr = metric.age_days ? ` à ${metric.age_days} jours` : "";
    const sexStr = metric.sex ? ` (${metric.sex})` : "";
    return `${metric.value}${metric.unit}${ageStr}${sexStr}`;
  },
  
  formatGeneticLine: (line: string): string => {
    const formatMap: Record<string, string> = {
      ross308: "Ross 308",
      ross308ap: "Ross 308 AP",
      cobb500: "Cobb 500", 
      cobb700: "Cobb 700",
      hubbard: "Hubbard",
      aviagen: "Aviagen",
      other: "Autre",
    };
    return formatMap[line] || line;
  },
  
  // Debug et logging
  debugValidationResult: (result: JSONValidationResult): void => {
    console.group("🔍 [JSON Validation] Résultat");
    secureLog.log(`Statut: ${result.is_valid ? "✅ Valide" : "❌ Invalide"}`);
    secureLog.log(`Erreurs: ${result.errors.length}`);
    secureLog.log(`Avertissements: ${result.warnings.length}`);
    secureLog.log(`Lignées détectées: ${result.metadata.genetic_lines_detected.join(", ")}`);
    secureLog.log(`Métriques: ${result.metadata.performance_metrics_count}`);
    
    if (result.errors.length > 0) {
      console.group("Erreurs:");
      result.errors.forEach(error => {
        secureLog.error(`${error.field}: ${error.message}`);
      });
      console.groupEnd();
    }
    
    console.groupEnd();
  },
} as const;

// ==================== TYPES EXISTANTS CONSERVÉS (SUITE) ====================

// Continuer avec tous les types existants du fichier original...
// (Le reste du contenu original reste identique)

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
  // Nouvelles propriétés pour le système multi-langue
  headerTitle?: string;
  ctaSubtext?: string;
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

export enum ConcisionLevel {
  ULTRA_CONCISE = "ultra_concise",
  CONCISE = "concise",
  STANDARD = "standard", 
  DETAILED = "detailed",
}

export interface ConcisionConfig {
  level: ConcisionLevel;
  autoDetect: boolean;
  userPreference: boolean;
}

export interface ConcisionControlProps {
  className?: string;
  compact?: boolean;
}

export interface ResponseVersionSelection {
  selectedVersion: string;
  availableVersions: Record<string, string>;
  selectedLevel: ConcisionLevel;
}

export interface ResponseProcessingResult {
  processedContent: string;
  originalContent: string;
  levelUsed: ConcisionLevel;
  wasProcessed: boolean;
}

export interface ConversationData {
  user_id: string;
  question: string;
  response: string;
  full_text?: string;
  conversation_id: string;
  confidence_score?: number;
  response_time_ms?: number;
  language?: string;
  rag_used?: boolean;
  feedback?: 1 | -1 | null;
  feedback_comment?: string;
  agent_metadata?: AgentMetadata;
  // NOUVEAU: Métadonnées JSON
  json_metadata?: {
    genetic_lines_mentioned: string[];
    performance_metrics_discussed: PerformanceMetric[];
    tables_referenced: PerformanceTable[];
  };
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
  feedback_comment?: string;
}

export interface Conversation {
  id: string;
  title: string;
  preview: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  feedback?: number | null;
  language?: string;
  last_message_preview?: string;
  status?: "active" | "archived";
  user_id?: string;
  messages?: Message[];
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

export interface ConversationGroup {
  title: string;
  conversations: Conversation[];
}

export interface ConversationHistoryResponse {
  success: boolean;
  conversations: Conversation[];
  groups?: ConversationGroup[];
  total_count: number;
  user_id: string;
  timestamp: string;
}

export interface ConversationDetailResponse {
  success: boolean;
  conversation: ConversationWithMessages;
  timestamp: string;
}

export interface ConversationGroupingOptions {
  groupBy: "date" | "topic" | "none";
  sortBy: "updated_at" | "created_at" | "message_count";
  sortOrder: "desc" | "asc";
  limit?: number;
  offset?: number;
}

export interface ConversationStats {
  total_conversations: number;
  total_messages: number;
  avg_messages_per_conversation: number;
  most_active_day: string;
  favorite_topics: string[];
  satisfaction_rate: number;
}

export interface ClarificationInlineProps {
  questions: string[];
  originalQuestion: string;
  language: string;
  onSubmit: (answers: Record<string, string>) => Promise<void>;
  onSkip: () => Promise<void>;
  isSubmitting?: boolean;
  conversationId?: string;
}

export interface ClarificationResponse {
  needs_clarification: boolean;
  questions?: string[];
  confidence_score?: number;
  processing_time_ms?: number;
  model_used?: string;
}

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

export interface User {
  id: string;
  email: string;
  name: string;
  firstName: string;
  lastName: string;
  phone: string;
  country: string;
  linkedinProfile: string;
  facebookProfile?: string;
  companyName: string;
  companyWebsite: string;
  linkedinCorporate: string;
  user_type: string;
  language: string;
  created_at: string;
  plan: string;

  country_code?: string;
  area_code?: string;
  phone_number?: string;

  full_name?: string;
  avatar_url?: string;
  consent_given?: boolean;
  consent_date?: string;
  updated_at?: string;
  user_id?: string;
  profile_id?: string;
  preferences?: Record<string, any>;
  is_admin?: boolean;
  preferredLanguage?: string;
}

export interface ProfileUpdateData {
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  country: string;
  linkedinProfile: string;
  companyName: string;
  companyWebsite: string;
  linkedinCorporate: string;
  language?: string;

  country_code?: string;
  area_code?: string;
  phone_number?: string;
}

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

export interface FeedbackData {
  conversation_id: string;
  feedback: "positive" | "negative";
  comment?: string;
  timestamp: string;
  user_id?: string;
  message_id?: string;
  rating?: "positive" | "negative";
  category?: "accuracy" | "relevance" | "completeness" | "other";
}

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

export interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  hasHydrated: boolean;
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

  startSessionTracking: (sessionId: string) => void;
  endSessionTracking: (
    logoutType?: "manual" | "browser_close" | "timeout",
  ) => Promise<void>;
  updateSessionActivity: () => Promise<void>;
}

export interface ChatStore {
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

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export interface UserInfoModalProps {
  isOpen: boolean;
  user: User | null;
  onClose: () => void;
}

export interface IconProps {
  className?: string;
}

export type Language = "fr" | "en" | "es" | "pt" | "de" | "nl" | "pl";

export interface LanguageOption {
  code: Language;
  name: string;
  flag: string;
}

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

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  hasHydrated: boolean;
}

export interface BackendUserData {
  id?: string;
  user_id?: string;
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
  const userId = backendUser.user_id || backendUser.id || "";

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

// Configuration API mise à jour avec endpoints JSON
const getApiConfig = () => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const version = process.env.NEXT_PUBLIC_API_VERSION || "v1";

  if (!baseUrl) {
    secureLog.error("NEXT_PUBLIC_API_BASE_URL environment variable missing");
    return {
      BASE_URL: "https://expert.intelia.com",
      TIMEOUT: 30000,
      LOGGING_BASE_URL: "https://expert.intelia.com/api/v1",
      LLM_BASE_URL: "https://expert.intelia.com/llm",
      JSON_BASE_URL: "https://expert.intelia.com/api/v1", // NOUVEAU: URL JSON
    };
  }

  const cleanBaseUrl = baseUrl.replace(/\/api\/?$/, "");

  return {
    BASE_URL: cleanBaseUrl,
    TIMEOUT: 30000,
    LOGGING_BASE_URL: `${cleanBaseUrl}/api/${version}`,
    LLM_BASE_URL: `${cleanBaseUrl}/llm`,
    JSON_BASE_URL: `${cleanBaseUrl}/api/${version}`, // NOUVEAU: URL JSON
  };
};

export const API_CONFIG = getApiConfig();

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

export const SESSION_ENDPOINTS = {
  HEARTBEAT: "/auth/heartbeat",
  LOGOUT: "/auth/logout",
  MY_SESSION_ANALYTICS: "/logging/analytics/my-sessions",
  SESSION_STATS: "/logging/analytics/session-stats",
  DAILY_PATTERNS: "/logging/analytics/daily-patterns",
} as const;

export const PLAN_CONFIGS = {
  essential: {
    name: "Essential",
    price: 0,
    currency: "USD",
    color: "text-green-600",
    bgColor: "bg-green-50",
    borderColor: "border-green-200",
    popular: false,
    features: [
      "plan.essential.feature1", // 50 questions par mois
      "plan.essential.feature2", // Accès aux documents publics
      "plan.essential.feature3", // Support par email
      "plan.essential.feature4", // Interface web
    ],
  },
  pro: {
    name: "Pro",
    price: 18,
    currency: "USD",
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
    popular: true,
    features: [
      "plan.pro.feature1", // Questions illimitées
      "plan.pro.feature2", // Accès documents confidentiels
      "plan.pro.feature3", // Support prioritaire
      "plan.pro.feature4", // Interface web + mobile
      "plan.pro.feature5", // Analytics avancées
    ],
  },
  elite: {
    name: "Elite",
    price: 28,
    currency: "USD",
    color: "text-purple-600",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-200",
    popular: false,
    features: [
      "plan.elite.feature1", // Tout du plan Pro
      "plan.elite.feature2", // Questions illimitées prioritaires
      "plan.elite.feature3", // Analyse de photos
      "plan.elite.feature4", // Support dédié 24/7
      "plan.elite.feature5", // Intégrations personnalisées
    ],
  },
  corporate: {
    name: "Corporate",
    price: null, // Prix sur demande
    currency: "USD",
    color: "text-orange-600",
    bgColor: "bg-orange-50",
    borderColor: "border-orange-200",
    popular: false,
    features: [
      "plan.corporate.feature1", // Tout du plan Elite
      "plan.corporate.feature2", // Knowledge base personnalisée
      "plan.corporate.feature3", // Intégration documents privés
      "plan.corporate.feature4", // Formation équipe dédiée
      "plan.corporate.feature5", // SLA garanti
      "plan.corporate.feature6", // Support dédié 24/7
    ],
  },
} as const;

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
  REQUIRED_ANSWER_PERCENTAGE: 0.5,
  AUTO_SCROLL_DELAY: 300,
  VALIDATION_DEBOUNCE: 500,
} as const;

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

export const AD_CONFIG = {
  TRIGGERS: {
    MIN_SESSIONS: 10,
    MIN_DURATION_PER_SESSION: 60,
    COOLDOWN_PERIOD: 168,
    CHECK_INTERVAL: 5 * 60 * 1000,
    INITIAL_CHECK_DELAY: 120000,
  },

  DISPLAY: {
    MIN_SHOW_TIME: 15,
    FADE_DURATION: 200,
    Z_INDEX: 50,
  },

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

  STORAGE: {
    LAST_AD_SHOWN_KEY: "lastAdShown",
    USER_PREFERENCES_KEY: "adPreferences",
    SESSION_TRACKING_KEY: "sessionTracking",
  },

  ENDPOINTS: {
    SESSION_ANALYTICS: "/analytics/my-sessions",
    AD_EVENTS: "/logging/ad-events",
  },
} as const;

export const SESSION_CONFIG = {
  HEARTBEAT_INTERVAL: 2 * 60 * 1000,
  SESSION_TIMEOUT: 30 * 60,
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
    const requiredCount = Math.ceil(questions.length * 0.5);

    return {
      isValid: answeredCount >= requiredCount,
      requiredCount,
      answeredCount,
    };
  },
} as const;

export const ConcisionUtils = {
  selectVersionFromResponse: (
    responseVersions: Record<string, string>,
    level: ConcisionLevel,
  ): string => {
    if (responseVersions[level]) {
      return responseVersions[level];
    }

    const fallbackOrder: ConcisionLevel[] = [
      ConcisionLevel.DETAILED,
      ConcisionLevel.STANDARD,
      ConcisionLevel.CONCISE,
      ConcisionLevel.ULTRA_CONCISE,
    ];

    for (const fallbackLevel of fallbackOrder) {
      if (responseVersions[fallbackLevel]) {
        secureLog.warn(
          `⚠️ [ConcisionUtils] Fallback vers ${fallbackLevel} (${level} manquant)`,
        );
        return responseVersions[fallbackLevel];
      }
    }

    const firstAvailable = Object.values(responseVersions)[0];
    secureLog.warn(
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

    const hasAnyVersion = requiredLevels.some(
      (level) =>
        responseVersions[level] && typeof responseVersions[level] === "string",
    );

    return hasAnyVersion;
  },

  detectOptimalLevel: (question: string): ConcisionLevel => {
    const questionLower = question.toLowerCase();

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
      secureLog.log(`${level}: ${content?.length || 0} caractères`);
      if (content) {
        secureLog.log(`  Aperçu: "${content.substring(0, 50)}..."`);
      }
    });
    console.groupEnd();
  },
} as const;

export const AdSystemUtils = {
  checkAdEligibility: (
    sessionStats: UserSessionStats,
    criteria: AdTriggerCriteria,
  ): boolean => {
    const meetsSessionCriteria =
      sessionStats.totalSessions >= criteria.MIN_SESSIONS;
    const meetsDurationCriteria =
      sessionStats.averageSessionDuration >= criteria.MIN_DURATION_PER_SESSION;

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

  generatePersonalizedAd: (userProfile?: User): AdData => {
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

  validateSessionStats: (data: any): data is UserSessionStats => {
    return (
      typeof data === "object" &&
      data !== null &&
      typeof data.totalSessions === "number" &&
      typeof data.averageSessionDuration === "number" &&
      typeof data.qualifiesForAd === "boolean"
    );
  },

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

    secureLog.log("📊 [AdSystem] Event:", eventData);

    try {
      const existingLogs = localStorage.getItem("adEventLogs");
      const logs = existingLogs ? JSON.parse(existingLogs) : [];
      logs.push(eventData);

      if (logs.length > 100) {
        logs.splice(0, logs.length - 100);
      }

      localStorage.setItem("adEventLogs", JSON.stringify(logs));
    } catch (error) {
      secureLog.warn("Erreur lors du stockage des logs publicitaires:", error);
    }
  },

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

export const SessionUtils = {
  generateSessionId: (): string => {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  },

  calculateSessionDuration: (
    loginTime: string,
    logoutTime?: string,
  ): number => {
    const start = new Date(loginTime);
    const end = logoutTime ? new Date(logoutTime) : new Date();
    return Math.floor((end.getTime() - start.getTime()) / 1000);
  },

  detectLogoutType: (
    userAgent: string,
    sessionDuration: number,
  ): "manual" | "browser_close" | "timeout" => {
    if (sessionDuration < 30) {
      return "browser_close";
    }

    if (sessionDuration > SESSION_CONFIG.SESSION_TIMEOUT) {
      return "timeout";
    }

    return "manual";
  },

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

export const TypeGuards = {
  isFeedbackType: (value: any): value is "positive" | "negative" => {
    return (
      typeof value === "string" && ["positive", "negative"].includes(value)
    );
  },

  isConcisionLevel: (value: any): value is ConcisionLevel => {
    return (
      typeof value === "string" &&
      Object.values(ConcisionLevel).includes(value as ConcisionLevel)
    );
  },

  isValidResponseVersions: (value: any): value is Record<string, string> => {
    if (!value || typeof value !== "object") return false;
    return Object.values(ConcisionLevel).some(
      (level) => value[level] && typeof value[level] === "string",
    );
  },

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

  // NOUVEAUX TYPE GUARDS POUR JSON SYSTEM
  isValidGeneticLineData: (value: any): value is GeneticLineData => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.line === "string" &&
      Object.values(JSON_SYSTEM_CONFIG.GENETIC_LINES).includes(value.line)
    );
  },

  isValidPerformanceMetric: (value: any): value is PerformanceMetric => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.type === "string" &&
      Object.values(JSON_SYSTEM_CONFIG.PERFORMANCE_METRICS).includes(value.type) &&
      typeof value.value === "number" &&
      typeof value.unit === "string"
    );
  },

  isValidAvicultureDocument: (value: any): value is AvicultureDocument => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.id === "string" &&
      typeof value.title === "string" &&
      typeof value.text === "string" &&
      typeof value.metadata === "object" &&
      value.metadata !== null
    );
  },

  isValidJSONValidationResult: (value: any): value is JSONValidationResult => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.is_valid === "boolean" &&
      Array.isArray(value.errors) &&
      Array.isArray(value.warnings) &&
      typeof value.metadata === "object"
    );
  },

  isValidJSONSearchRequest: (value: any): value is JSONSearchRequest => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.query === "string"
    );
  },

  isValidAvicultureSearchResult: (value: any): value is AvicultureSearchResult => {
    return (
      typeof value === "object" &&
      value !== null &&
      TypeGuards.isValidAvicultureDocument(value.document) &&
      typeof value.score === "number"
    );
  },

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

  isValidClarificationResponse: (
    value: any,
  ): value is ClarificationResponse => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.needs_clarification === "boolean"
    );
  },

  isValidStreamCallbacks: (value: any): value is StreamCallbacks => {
    return typeof value === "object" && value !== null;
  },

  isValidStreamEvent: (value: any): value is StreamEvent => {
    return (
      typeof value === "object" &&
      value !== null &&
      typeof value.type === "string"
    );
  },
} as const;

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
    SIDEBAR_WIDTH: "w-96",
    MAX_TITLE_LENGTH: 60,
    MAX_PREVIEW_LENGTH: 150,
    MESSAGES_PER_PAGE: 50,
    AUTO_SCROLL_DELAY: 100,
  },
  CACHE: {
    CONVERSATION_LIST_TTL: 5 * 60 * 1000,
    CONVERSATION_DETAIL_TTL: 10 * 60 * 1000,
    MAX_CACHED_CONVERSATIONS: 100,
  },
} as const;

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

    return groups.filter((group) => group.conversations.length > 0);
  },
} as const;

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
    PROCESSING_TIMEOUT: 30000,
  },
} as const;

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

export const VALIDATION_RULES = {
  FEEDBACK: {
    COMMENT_MIN_LENGTH: 0,
    COMMENT_MAX_LENGTH: 500,
    REQUIRED_FIELDS: [] as string[],
    ALLOWED_FEEDBACK_TYPES: ["positive", "negative"] as const,
  },
  PHONE: {
    COUNTRY_CODE_PATTERN: /^\+\d{1,4}$/,
    AREA_CODE_PATTERN: /^\d{1,4}$/,
    PHONE_NUMBER_PATTERN: /^\d{4,12}$/,
  },
  CONVERSATION: {
    TITLE_MAX_LENGTH: 60,
    PREVIEW_MAX_LENGTH: 150,
    MESSAGE_MAX_LENGTH: 5000,
    MAX_CONVERSATIONS_PER_USER: 1000,
    AUTO_DELETE_DAYS: 30,
  },
  CLARIFICATION: {
    MIN_ANSWER_LENGTH: 0,
    MAX_ANSWER_LENGTH: 200,
    MAX_QUESTIONS: 4,
    REQUIRED_ANSWER_PERCENTAGE: 0.5,
  },
  CONCISION: {
    MIN_RESPONSE_LENGTH: 10,
    MAX_ULTRA_CONCISE_LENGTH: 50,
    MAX_CONCISE_LENGTH: 200,
    MAX_STANDARD_LENGTH: 500,
    AUTO_DETECT_ENABLED: true,
  },
  AD_SYSTEM: {
    MIN_SESSIONS_FOR_AD: 2,
    MIN_SESSION_DURATION: 60,
    COOLDOWN_HOURS: 24,
    MIN_DISPLAY_TIME: 15,
    MAX_TITLE_LENGTH: 60,
    MAX_DESCRIPTION_LENGTH: 200,
    MAX_FEATURES_COUNT: 8,
  },
  SESSION_TRACKING: {
    MIN_SESSION_DURATION: 5,
    MAX_SESSION_DURATION: 8 * 60 * 60,
    HEARTBEAT_TOLERANCE: 5 * 60,
    MAX_SESSIONS_PER_DAY: 20,
    SESSION_ID_LENGTH: 32,
  },
  AGENT: {
    MIN_PROCESSING_TIME: 100,
    MAX_PROCESSING_TIME: 60000,
    MAX_SUB_QUERIES: 10,
    MAX_SOURCES: 20,
    MAX_DECISIONS: 50,
    MIN_CONFIDENCE: 0.0,
    MAX_CONFIDENCE: 1.0,
  },
  // NOUVEAU: RÈGLES POUR JSON SYSTEM
  JSON_SYSTEM: {
    MIN_TITLE_LENGTH: 5,
    MAX_TITLE_LENGTH: 200,
    MIN_TEXT_LENGTH: 50,
    MAX_TEXT_LENGTH: 100000,
    MAX_TABLES_PER_DOCUMENT: 50,
    MAX_FIGURES_PER_DOCUMENT: 20,
    MAX_PERFORMANCE_RECORDS: 1000,
    MAX_DOCUMENT_SIZE_MB: 10,
    REQUIRED_METADATA_FIELDS: ["document_type", "language"],
    SUPPORTED_LANGUAGES: ["fr", "en", "es", "pt", "de"],
    MAX_GENETIC_LINES_PER_DOCUMENT: 5,
    MIN_CONFIDENCE_SCORE: 0.0,
    MAX_CONFIDENCE_SCORE: 1.0,
  },
} as const;

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
  CONVERSATION: {
    LOAD_FAILED: "Erreur lors du chargement de la conversation",
    DELETE_FAILED: "Erreur lors de la suppression de la conversation",
    NOT_FOUND: "Conversation non trouvée",
    EMPTY_MESSAGE: "Le message ne peut pas être vide",
    MESSAGE_TOO_LONG: `Le message ne peut pas dépasser ${VALIDATION_RULES.CONVERSATION.MESSAGE_MAX_LENGTH} caractères`,
    CREATION_FAILED: "Erreur lors de la création de la conversation",
  },
  CLARIFICATION: {
    PROCESSING_FAILED: "Erreur lors du traitement des clarifications",
    INVALID_ANSWERS: "Réponses invalides. Veuillez vérifier vos réponses.",
    SUBMISSION_FAILED: "Erreur lors de l'envoi des clarifications",
    TIMEOUT: "Timeout lors du traitement des clarifications",
  },
  CONCISION: {
    VERSION_NOT_FOUND: "Version de réponse non trouvée",
    INVALID_LEVEL: "Niveau de concision invalide",
    BACKEND_ERROR: "Erreur lors de la génération des versions de réponse",
    FALLBACK_USED: "Version de secours utilisée",
  },
  AD_SYSTEM: {
    LOAD_FAILED: "Erreur lors du chargement de la publicité",
    SESSION_CHECK_FAILED: "Erreur lors de la vérification de l'éligibilité",
    INVALID_AD_DATA: "Données publicitaires invalides",
    TRACKING_FAILED: "Erreur lors du suivi publicitaire",
    COOLDOWN_ACTIVE: "Publicité en période d'attente",
  },
  SESSION_TRACKING: {
    START_FAILED: "Erreur lors du démarrage du tracking de session",
    HEARTBEAT_FAILED: "Erreur lors de la mise à jour de l'activité",
    END_FAILED: "Erreur lors de la fermeture de session",
    INVALID_SESSION: "Session invalide ou expirée",
    ANALYTICS_FAILED: "Erreur lors du chargement des analytics de session",
  },
  AGENT: {
    PROCESSING_FAILED: "Erreur lors du traitement par l'Agent",
    TIMEOUT: "L'Agent a mis trop de temps à répondre",
    COMPLEXITY_ERROR: "Erreur dans l'analyse de complexité",
    SYNTHESIS_FAILED: "Erreur lors de la synthèse des sources",
    INVALID_METADATA: "Métadonnées Agent invalides",
  },
  // NOUVEAUX: MESSAGES POUR JSON SYSTEM
  JSON_SYSTEM: {
    VALIDATION_FAILED: "Erreur lors de la validation du document JSON",
    INVALID_DOCUMENT_STRUCTURE: "Structure de document invalide",
    MISSING_REQUIRED_FIELDS: "Champs requis manquants",
    INVALID_GENETIC_LINE: "Lignée génétique non reconnue",
    INVALID_PERFORMANCE_METRIC: "Métrique de performance invalide",
    EXTRACTION_FAILED: "Erreur lors de l'extraction des données",
    SEARCH_FAILED: "Erreur lors de la recherche JSON",
    UPLOAD_FAILED: "Erreur lors de l'upload des fichiers",
    INGESTION_FAILED: "Erreur lors de l'ingestion des documents",
    DOCUMENT_TOO_LARGE: `Document trop volumineux (max ${VALIDATION_RULES.JSON_SYSTEM.MAX_DOCUMENT_SIZE_MB}MB)`,
    UNSUPPORTED_FORMAT: "Format de fichier non supporté",
    INVALID_JSON_FORMAT: "Format JSON invalide",
    PERFORMANCE_DATA_INVALID: "Données de performance invalides",
    TABLE_EXTRACTION_FAILED: "Erreur lors de l'extraction des tableaux",
    GENETIC_LINE_DETECTION_FAILED: "Erreur lors de la détection de lignée génétique",
  },
  GENERAL: {
    UNAUTHORIZED: "Session expirée - reconnexion nécessaire",
    FORBIDDEN: "Accès non autorisé",
    NOT_FOUND: "Ressource non trouvée",
    GENERIC: "Une erreur inattendue s'est produite",
  },
} as const;

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

// NOUVEAUX: TYPES POUR LES RÉPONSES D'API JSON SYSTEM
export interface JSONValidationApiResponse {
  status: "success" | "error";
  data?: JSONValidationResult;
  error?: string;
  timestamp: string;
}

export interface JSONIngestionApiResponse {
  status: "success" | "error";
  data?: JSONIngestionResult;
  error?: string;
  timestamp: string;
}

export interface JSONSearchApiResponse {
  status: "success" | "error";
  data?: JSONSearchResult;
  error?: string;
  timestamp: string;
}

export interface JSONSystemStatusResponse {
  status: "healthy" | "degraded" | "unhealthy";
  components: {
    json_validator: boolean;
    json_extractor: boolean;
    table_extractor: boolean;
    genetic_line_extractor: boolean;
    ingestion_pipeline: boolean;
    hybrid_search_engine: boolean;
  };
  statistics: {
    documents_indexed: number;
    genetic_lines_detected: number;
    performance_metrics_processed: number;
    tables_extracted: number;
    figures_processed: number;
  };
  timestamp: string;
}

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
  // NOUVEAU: Préférences JSON system
  json_preferences?: {
    auto_detect_genetic_lines: boolean;
    include_performance_data: boolean;
    preferred_search_type: "semantic" | "bm25" | "hybrid";
    confidence_threshold: number;
  };
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
  json_preferences?: {
    auto_detect_genetic_lines?: boolean;
    include_performance_data?: boolean;
    preferred_search_type?: "semantic" | "bm25" | "hybrid";
    confidence_threshold?: number;
  };
}

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

export const APP_CONFIG = {
  NAME: "Intelia Expert",
  VERSION: "4.0.0", // Version JSON System
  DESCRIPTION: "Plateforme IA spécialisée en élevage avicole avec système RAG JSON avancé",
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
    ENABLE_AGENT_LLM: true,
    ENABLE_AGENT_METADATA: true,
    ENABLE_PROACTIVE_FOLLOWUP: true,
    ENABLE_STREAMING_ENHANCED: true,
    // NOUVELLES FEATURES JSON
    ENABLE_JSON_SYSTEM: true,
    ENABLE_JSON_VALIDATION: true,
    ENABLE_JSON_INGESTION: true,
    ENABLE_JSON_SEARCH: true,
    ENABLE_PERFORMANCE_EXTRACTION: true,
    ENABLE_GENETIC_LINE_DETECTION: true,
    ENABLE_TABLE_EXTRACTION: true,
  },

  LIMITS: {
    MAX_MESSAGE_LENGTH: 5000,
    MAX_CONVERSATIONS: 1000,
    MAX_FEEDBACK_COMMENT_LENGTH: 500,
    SESSION_TIMEOUT_MINUTES: 30,
    HEARTBEAT_INTERVAL_MINUTES: 2,
    MAX_AGENT_PROCESSING_TIME: 60000,
    MAX_AGENT_SUB_QUERIES: 5,
    MAX_AGENT_SOURCES: 10,
    // NOUVELLES LIMITES JSON
    MAX_JSON_DOCUMENT_SIZE_MB: 10,
    MAX_JSON_FILES_PER_UPLOAD: 50,
    MAX_JSON_BATCH_SIZE: 20,
    MAX_JSON_SEARCH_RESULTS: 50,
    MAX_PERFORMANCE_RECORDS_PER_DOCUMENT: 1000,
  },
} as const;