import React, { useState, useEffect, useRef, useMemo } from "react";
import { useAuthStore } from "@/lib/stores/auth"; // ✅ Store unifié uniquement
import { apiClient } from "@/lib/api/client";
import { StatisticsDashboard } from "./StatisticsDashboard";
import { QuestionsTab } from "./QuestionsTab";
import { InvitationStatsComponent } from "./InvitationStats";
import { QualityIssuesTab } from "./QualityIssuesTab";
import { SatisfactionStatsTab } from "./SatisfactionStatsTab";
import { secureLog } from "@/lib/utils/secureLogger";

// ✅ HOOK SIMPLIFIÉ - Plus de fallback localStorage/Supabase
const useRobustAuth = () => {
  const { user } = useAuthStore();

  return useMemo(() => {
    // UNIQUEMENT le store unifié - plus de fallback
    if (user?.email && user?.user_type) {
      secureLog.log(`[useRobustAuth] Utilisateur trouvé dans le store unifié: ${user.email} ${user.user_type} `);
      return user;
    }

    secureLog.log("[useRobustAuth] Aucun utilisateur dans le store unifié");
    return null;
  }, [user]);
};

// Types pour le système de cache ultra-rapide (conservés)
interface CacheStatus {
  is_available: boolean;
  last_update: string | null;
  cache_age_minutes: number;
  performance_gain: string | number;
  next_update: string | null;
}

interface FastDashboardStats {
  cache_info: CacheStatus;
  system_stats: SystemStats;
  usage_stats: UsageStats;
  billing_stats: BillingStats;
  performance_stats: PerformanceStats;
  systemStats?: SystemStats;
  usageStats?: UsageStats;
  billingStats?: BillingStats;
  performanceStats?: PerformanceStats & { performance_gain: number };
}

interface FastQuestionsResponse {
  cache_info: CacheStatus;
  questions: QuestionLog[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
    has_next?: boolean;
    has_prev?: boolean;
  };
  meta?: {
    retrieved: number;
    user_role: string;
    timestamp: string;
  };
}

interface FastInvitationStats {
  cache_info: CacheStatus;
  invitation_stats: InvitationStats;
}

interface GlobalInvitationStats {
  total_invitations: number;
  total_accepted: number;
  total_pending: number;
  global_acceptance_rate: number;
  active_inviters: number;
  unique_inviters: number;
  top_inviters_by_sent: Array<{
    inviter_email: string;
    inviter_name: string;
    invitations_sent: number;
    invitations_accepted: number;
    acceptance_rate: number;
  }>;
  top_inviters_by_accepted: Array<{
    inviter_email: string;
    inviter_name: string;
    invitations_sent: number;
    invitations_accepted: number;
    acceptance_rate: number;
  }>;
}

// Types pour les données de statistiques (conservés)
interface SystemStats {
  system_health: {
    uptime_hours: number;
    total_requests: number;
    error_rate: number;
    rag_status: {
      global: boolean;
      broiler: boolean;
      layer: boolean;
    };
  };
  billing_stats: {
    plans_available: number;
    plan_names: string[];
  };
  features_enabled: {
    analytics: boolean;
    billing: boolean;
    authentication: boolean;
    openai_fallback: boolean;
  };
}

interface UsageStats {
  unique_users: number;
  total_questions: number;
  questions_today: number;
  questions_this_month: number;
  source_distribution: {
    rag_retriever: number;
    openai_fallback: number;
    perfstore: number;
  };
  monthly_breakdown: {
    [month: string]: number;
  };
}

interface BillingStats {
  plans: {
    [planName: string]: {
      user_count: number;
      revenue: number;
    };
  };
  total_revenue: number;
  top_users: Array<{
    email: string;
    question_count: number;
    plan: string;
  }>;
}

interface PerformanceStats {
  avg_response_time: number;
  median_response_time: number;
  min_response_time: number;
  max_response_time: number;
  response_time_count: number;
  openai_costs: number;
  error_count: number;
  cache_hit_rate: number;
  performance_gain?: number;
}

interface InvitationStats {
  total_invitations_sent: number;
  total_invitations_accepted: number;
  acceptance_rate: number;
  unique_inviters: number;
  top_inviters: Array<{
    inviter_email: string;
    inviter_name: string;
    invitations_sent: number;
    invitations_accepted: number;
    acceptance_rate: number;
  }>;
  top_accepted: Array<{
    inviter_email: string;
    inviter_name: string;
    invitations_accepted: number;
    invitations_sent: number;
    acceptance_rate: number;
  }>;
}

interface QuestionLog {
  id: string;
  timestamp: string;
  user_email: string;
  user_name: string;
  question: string;
  response: string;
  response_source:
    | "rag"
    | "rag_success"
    | "rag_knowledge"
    | "rag_verified"
    | "retrieval_success"
    | "fallback_needed"
    | "ood_filtered"
    | "no_results"
    | "no_documents_found"
    | "insufficient_context"
    | "needs_clarification"
    | "awaiting_user_input"
    | "embedding_failed"
    | "search_failed"
    | "low_confidence"
    | "generation_failed"
    | "internal_error"
    | "error"
    | "openai_fallback"
    | "table_lookup"
    | "validation_rejected"
    | "quota_exceeded"
    | "unknown";
  confidence_score: number;
  response_time: number;
  language: string;
  session_id: string;
  feedback: number | null;
  feedback_comment: string | null;
}

export const StatisticsPage: React.FC = () => {
  const currentUser = useRobustAuth(); // ✅ Hook simplifié
  const { isAuthenticated, hasHydrated, getAuthToken } = useAuthStore(); // ✅ Store unifié

  const [authStatus, setAuthStatus] = useState<
    "initializing" | "checking" | "ready" | "unauthorized" | "forbidden"
  >("initializing");
  const [statsLoading, setStatsLoading] = useState(false);
  const [questionsLoading, setQuestionsLoading] = useState(false);
  const [invitationLoading, setInvitationLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // États pour le cache ultra-rapide - SÉPARÉS par onglet
  const [dashboardCacheStatus, setDashboardCacheStatus] =
    useState<CacheStatus | null>(null);
  const [questionsCacheStatus, setQuestionsCacheStatus] =
    useState<CacheStatus | null>(null);
  const [invitationCacheStatus, setInvitationCacheStatus] =
    useState<CacheStatus | null>(null);
  const [performanceGain, setPerformanceGain] = useState<string>("");

  // États pour les données
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null);
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [billingStats, setBillingStats] = useState<BillingStats | null>(null);
  const [performanceStats, setPerformanceStats] =
    useState<PerformanceStats | null>(null);
  const [invitationStats, setInvitationStats] =
    useState<InvitationStats | null>(null);
  const [questionLogs, setQuestionLogs] = useState<QuestionLog[]>([]);
  const [totalQuestions, setTotalQuestions] = useState(0);

  // États UI
  const [selectedTimeRange, setSelectedTimeRange] = useState<
    "day" | "week" | "month" | "year"
  >("month");
  const [activeTab, setActiveTab] = useState<
    "dashboard" | "questions" | "invitations" | "quality" | "satisfaction" | "metrics"
  >("dashboard");
  const [questionFilters, setQuestionFilters] = useState({
    search: "",
    source: "all",
    confidence: "all",
    feedback: "all",
    user: "all",
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [questionsPerPage] = useState(20);
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionLog | null>(
    null,
  );
  const [authToken, setAuthToken] = useState<string>("");

  // Références pour éviter les chargements multiples
  const authCheckRef = useRef<boolean>(false);
  const stabilityCounterRef = useRef<number>(0);
  const dashboardLoadedRef = useRef<boolean>(false);
  const questionsLoadedRef = useRef<Map<string, boolean>>(new Map());
  const invitationsLoadedRef = useRef<boolean>(false);

  // Reset forcé des références à chaque mount
  useEffect(() => {
    secureLog.log("[StatisticsPage] Reset forcé des références au mount");
    dashboardLoadedRef.current = false;
    authCheckRef.current = false;
    stabilityCounterRef.current = 0;
    questionsLoadedRef.current.clear();
    invitationsLoadedRef.current = false;
  }, []);

  // ✅ Récupérer le token pour QualityIssuesTab
  useEffect(() => {
    const fetchToken = async () => {
      if (isAuthenticated) {
        const token = await getAuthToken();
        setAuthToken(token || "");
      }
    };
    fetchToken();
  }, [isAuthenticated, getAuthToken]);

  // ✅ LOGIQUE D'AUTHENTIFICATION SIMPLIFIÉE - Store unifié uniquement
  useEffect(() => {
    secureLog.log("[StatisticsPage] Auth check unifié:", {
      hasHydrated,
      isAuthenticated,
      hasUser: !!currentUser,
      email: currentUser?.email,
      userType: currentUser?.user_type,
    });

    if (!hasHydrated) {
      secureLog.log("[StatisticsPage] Store pas encore hydraté...");
      setAuthStatus("initializing");
    } else if (!isAuthenticated || !currentUser) {
      secureLog.log("[StatisticsPage] Utilisateur non connecté");
      setAuthStatus("unauthorized");
      setError("Vous devez être connecté pour accéder à cette page");
    } else if (currentUser.user_type !== "super_admin") {
      secureLog.log(`[StatisticsPage] Permissions insuffisantes: ${currentUser.user_type} `);
      setAuthStatus("forbidden");
      setError("Accès refusé - Permissions super_admin requises");
    } else {
      secureLog.log(`[StatisticsPage] Authentification réussie: ${currentUser.email} `);
      setAuthStatus("ready");
      setError(null);
    }
  }, [hasHydrated, isAuthenticated, currentUser]);

  // ✅ CHARGEMENT STATS - Avec délai pour stabilité
  useEffect(() => {
    if (authStatus === "ready" && !statsLoading && !systemStats) {
      secureLog.log("[StatisticsPage] Lancement chargement des statistiques");

      const timeoutId = setTimeout(() => {
        loadAllStatistics();
      }, 100); // Délai réduit car plus besoin d'attendre Supabase

      return () => clearTimeout(timeoutId);
    }
  }, [authStatus, statsLoading, systemStats]);

  // Chargement des questions - SEULEMENT SI NÉCESSAIRE
  useEffect(() => {
    if (
      authStatus === "ready" &&
      activeTab === "questions" &&
      !questionsLoading
    ) {
      const pageKey = `${currentPage}-${questionsPerPage}`;
      if (!questionsLoadedRef.current.get(pageKey)) {
        secureLog.log(`[StatisticsPage] Lancement chargement des questions pour page: ${pageKey} `);
        questionsLoadedRef.current.set(pageKey, true);
        loadQuestionLogs();
      }
    }
  }, [authStatus, activeTab, currentPage]);

  // Chargement des invitations - UNE SEULE FOIS PAR VISITE
  useEffect(() => {
    if (
      authStatus === "ready" &&
      activeTab === "invitations" &&
      !invitationLoading &&
      !invitationsLoadedRef.current
    ) {
      secureLog.log("[StatisticsPage] Lancement chargement des invitations");
      invitationsLoadedRef.current = true;
      loadInvitationStats();
    }
  }, [authStatus, activeTab]);

  // Reset des références quand on change d'onglet
  const handleTabChange = (
    newTab: "dashboard" | "questions" | "invitations" | "quality" | "satisfaction" | "metrics",
  ) => {
    if (newTab !== activeTab) {
      secureLog.log(`[StatisticsPage] Changement onglet: ${activeTab} -> ${newTab} `);

      if (newTab === "questions") {
        questionsLoadedRef.current.clear();
      }

      setActiveTab(newTab);
    }
  };

  // ✅ MÉTHODE UNIFIÉE : Utiliser apiClient.getSecure() uniquement
  const loadAllStatistics = async () => {
    if (statsLoading) {
      secureLog.log("[StatisticsPage] Chargement déjà en cours, annulation...");
      return;
    }

    secureLog.log(
      "[StatisticsPage] DÉBUT chargement statistiques avec store unifié",
    );
    setStatsLoading(true);
    setError(null);

    const startTime = performance.now();

    try {
      // ✅ UTILISE APILIENT.GETSECURE() - plus d'appels directs
      secureLog.log(
        "[StatisticsPage] Appel apiClient.getSecure() pour stats-fast/dashboard",
      );

      const response = await apiClient.getSecure<FastDashboardStats>(
        "stats-fast/dashboard",
      );

      if (!response.success) {
        throw new Error(
          response.error?.message ||
            "Erreur lors du chargement des statistiques",
        );
      }

      if (!response.data) {
        throw new Error("Réponse vide du serveur");
      }

      const fastData = response.data;
      secureLog.log("✅ Statistiques chargées avec store unifié!", fastData);

      const loadTime = performance.now() - startTime;
      secureLog.log(`Performance: ${loadTime.toFixed(0)}ms`);

      const performanceGainValue =
        fastData.performanceStats?.performance_gain ||
        fastData.performance_stats?.performance_gain ||
        fastData.cache_info?.performance_gain ||
        0;

      const performanceGainString =
        typeof performanceGainValue === "number"
          ? `${performanceGainValue}%`
          : performanceGainValue?.toString() || "0%";

      const updatedCacheStatus = {
        ...fastData.cache_info,
        performance_gain: performanceGainString,
      };
      setDashboardCacheStatus(updatedCacheStatus);
      setPerformanceGain(
        `${loadTime.toFixed(0)}ms (vs ${performanceGainString})`,
      );

      const systemStatsData = fastData.systemStats || fastData.system_stats;
      const usageStatsData = fastData.usageStats || fastData.usage_stats;
      const billingStatsData = fastData.billingStats || fastData.billing_stats;
      const performanceStatsData =
        fastData.performanceStats || fastData.performance_stats;

      const safeSystemStats = systemStatsData
        ? {
            ...systemStatsData,
            system_health: systemStatsData.system_health
              ? {
                  ...systemStatsData.system_health,
                  error_rate:
                    typeof systemStatsData.system_health.error_rate === "string"
                      ? parseFloat(systemStatsData.system_health.error_rate) ||
                        0
                      : systemStatsData.system_health.error_rate || 0,
                }
              : systemStatsData.system_health,
          }
        : null;

      const safeBillingStats = billingStatsData
        ? {
            ...billingStatsData,
            total_revenue:
              typeof billingStatsData.total_revenue === "string"
                ? parseFloat(billingStatsData.total_revenue) || 0
                : billingStatsData.total_revenue || 0,
          }
        : null;

      const safePerformanceStats = performanceStatsData
        ? {
            ...performanceStatsData,
            avg_response_time:
              typeof performanceStatsData.avg_response_time === "string"
                ? parseFloat(performanceStatsData.avg_response_time) || 0
                : performanceStatsData.avg_response_time || 0,
            median_response_time:
              typeof performanceStatsData.median_response_time === "string"
                ? parseFloat(performanceStatsData.median_response_time) || 0
                : performanceStatsData.median_response_time || 0,
            min_response_time:
              typeof performanceStatsData.min_response_time === "string"
                ? parseFloat(performanceStatsData.min_response_time) || 0
                : performanceStatsData.min_response_time || 0,
            max_response_time:
              typeof performanceStatsData.max_response_time === "string"
                ? parseFloat(performanceStatsData.max_response_time) || 0
                : performanceStatsData.max_response_time || 0,
            response_time_count:
              typeof performanceStatsData.response_time_count === "string"
                ? parseInt(performanceStatsData.response_time_count) || 0
                : performanceStatsData.response_time_count || 0,
            openai_costs:
              typeof performanceStatsData.openai_costs === "string"
                ? parseFloat(performanceStatsData.openai_costs) || 0
                : performanceStatsData.openai_costs || 0,
            error_count:
              typeof performanceStatsData.error_count === "string"
                ? parseInt(performanceStatsData.error_count) || 0
                : performanceStatsData.error_count || 0,
            cache_hit_rate:
              typeof performanceStatsData.cache_hit_rate === "string"
                ? parseFloat(performanceStatsData.cache_hit_rate) || 0
                : performanceStatsData.cache_hit_rate || 0,
            performance_gain:
              typeof performanceStatsData.performance_gain === "string"
                ? parseFloat(performanceStatsData.performance_gain) || 0
                : performanceStatsData.performance_gain || 0,
          }
        : null;

      setSystemStats(safeSystemStats);
      setUsageStats(usageStatsData);
      setBillingStats(safeBillingStats);
      setPerformanceStats(safePerformanceStats);

      secureLog.log("Toutes les statistiques chargées via store unifié!");
    } catch (err) {
      secureLog.error("[StatisticsPage] Erreur chargement statistiques:", err);
      setError(`Erreur lors du chargement des statistiques: ${err}`);
    } finally {
      setStatsLoading(false);
    }
  };

  // ✅ MÉTHODE UNIFIÉE : Charger les questions avec apiClient.getSecure
  const loadQuestionLogs = async () => {
    if (questionsLoading) {
      secureLog.log("[Questions] Chargement déjà en cours, annulation...");
      return;
    }

    secureLog.log("[Questions] Chargement avec store unifié");
    setQuestionsLoading(true);
    const startTime = performance.now();

    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: questionsPerPage.toString(),
      });

      // ✅ UTILISE APILIENT.GETSECURE() avec URL relative
      const response = await apiClient.getSecure<FastQuestionsResponse>(
        `stats-fast/questions?${params}`,
      );

      if (!response.success) {
        throw new Error(
          response.error?.message || "Erreur lors du chargement des questions",
        );
      }

      if (!response.data) {
        throw new Error("Réponse vide du serveur");
      }

      const fastData = response.data;
      secureLog.log("Questions chargées avec store unifié!", fastData);

      const loadTime = performance.now() - startTime;
      secureLog.log(`Questions Performance: ${loadTime.toFixed(0)}ms`);

      const realCacheInfo = fastData.cache_info || {
        is_available: false,
        last_update: null,
        cache_age_minutes: 0,
        performance_gain: `${loadTime.toFixed(0)}ms`,
        next_update: null,
      };

      const enrichedCacheInfo = {
        ...realCacheInfo,
        performance_gain: realCacheInfo.is_available
          ? realCacheInfo.performance_gain
          : `${loadTime.toFixed(0)}ms (direct)`,
      };

      setQuestionsCacheStatus(enrichedCacheInfo);

      const adaptedQuestions: QuestionLog[] = fastData.questions.map((q) => ({
        id: q.id,
        timestamp: q.timestamp,
        user_email: q.user_email,
        user_name:
          q.user_name ||
          (q.user_email || "")
            .split("@")[0]
            .replace(".", " ")
            .replace(/\b\w/g, (l) => l.toUpperCase()),
        question: q.question,
        response: q.response,
        response_source: mapResponseSource(q.response_source),
        confidence_score: q.confidence_score,
        response_time: q.response_time,
        language: q.language,
        session_id: q.session_id,
        feedback: q.feedback,
        feedback_comment: q.feedback_comment,
      }));

      setQuestionLogs(adaptedQuestions);
      setTotalQuestions(fastData.pagination.total);
    } catch (err) {
      secureLog.error("Erreur chargement questions:", err);
      setError(`Erreur chargement questions: ${err}`);
      setQuestionLogs([]);
      const pageKey = `${currentPage}-${questionsPerPage}`;
      questionsLoadedRef.current.delete(pageKey);
    } finally {
      setQuestionsLoading(false);
    }
  };

  // ✅ MÉTHODE UNIFIÉE : Charger les invitations avec l'endpoint fonctionnel
  const loadInvitationStats = async () => {
    if (invitationLoading) {
      secureLog.log("[Invitations] Chargement déjà en cours, annulation...");
      return;
    }

    secureLog.log("[Invitations] Chargement avec store unifié");
    setInvitationLoading(true);
    setError(null);
    const startTime = performance.now();

    try {
      secureLog.log(
        "Utilisation endpoint fonctionnel: invitations/stats/global-enhanced",
      );

      // ✅ UTILISE APILIENT.GETSECURE() - plus d'appels directs
      const response = await apiClient.getSecure<GlobalInvitationStats>(
        "invitations/stats/global-enhanced",
      );

      if (!response.success) {
        throw new Error(
          response.error?.message ||
            "Erreur lors du chargement des invitations",
        );
      }

      if (!response.data) {
        throw new Error("Réponse vide du serveur");
      }

      const globalData = response.data;
      secureLog.log("Invitations chargées avec store unifié!", globalData);

      const loadTime = performance.now() - startTime;
      secureLog.log(`Invitations Performance: ${loadTime.toFixed(0)}ms`);

      const adaptedCacheStatus: CacheStatus = {
        is_available: false,
        last_update: new Date().toISOString(),
        cache_age_minutes: 0,
        performance_gain: `${loadTime.toFixed(0)}ms (direct)`,
        next_update: null,
      };

      const adaptedInvitationStats: InvitationStats = {
        total_invitations_sent: globalData.total_invitations,
        total_invitations_accepted: globalData.total_accepted,
        acceptance_rate: globalData.global_acceptance_rate,
        unique_inviters: globalData.unique_inviters,
        top_inviters: globalData.top_inviters_by_sent || [],
        top_accepted: globalData.top_inviters_by_accepted || [],
      };

      setInvitationCacheStatus(adaptedCacheStatus);
      setInvitationStats(adaptedInvitationStats);

      secureLog.log("Données d'invitations adaptées:", adaptedInvitationStats);
    } catch (err) {
      secureLog.error(
        "[StatisticsPage] Erreur chargement stats invitations:",
        err,
      );
      setError(
        `Erreur lors du chargement des statistiques d'invitations: ${err}`,
      );

      invitationsLoadedRef.current = false;

      setInvitationStats({
        total_invitations_sent: 0,
        total_invitations_accepted: 0,
        acceptance_rate: 0,
        unique_inviters: 0,
        top_inviters: [],
        top_accepted: [],
      });
    } finally {
      setInvitationLoading(false);
    }
  };

  // Fonctions helpers - IDENTIQUES
  const mapResponseSource = (
    source: string,
  ): QuestionLog["response_source"] => {
    // Map all possible RAGSource enum values from LLM backend
    switch (source) {
      // Success sources
      case "rag":
        return "rag";
      case "rag_success":
        return "rag_success";
      case "rag_knowledge":
        return "rag_knowledge";
      case "rag_verified":
        return "rag_verified";
      case "retrieval_success":
        return "retrieval_success";

      // Fallback sources
      case "fallback_needed":
        return "fallback_needed";
      case "ood_filtered":
        return "ood_filtered";

      // No results sources
      case "no_results":
        return "no_results";
      case "no_documents_found":
        return "no_documents_found";

      // Clarification sources
      case "insufficient_context":
        return "insufficient_context";
      case "needs_clarification":
        return "needs_clarification";
      case "awaiting_user_input":
        return "awaiting_user_input";

      // Error sources
      case "embedding_failed":
        return "embedding_failed";
      case "search_failed":
        return "search_failed";
      case "low_confidence":
        return "low_confidence";
      case "generation_failed":
        return "generation_failed";
      case "internal_error":
        return "internal_error";
      case "error":
        return "error";

      // Legacy sources
      case "openai_fallback":
        return "openai_fallback";
      case "table_lookup":
        return "table_lookup";
      case "validation_rejected":
        return "validation_rejected";
      case "quota_exceeded":
        return "quota_exceeded";

      default:
        return "unknown";
    }
  };

  const getFeedbackIcon = (feedback: number | null): string => {
    if (feedback === 1) return "👍";
    if (feedback === -1) return "👎";
    return "❓";
  };

  // ✅ RENDU CONDITIONNEL SIMPLIFIÉ - Plus de vérifications Supabase

  if (authStatus === "initializing") {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Initialisation du store unifié...</p>
        </div>
      </div>
    );
  }

  if (authStatus === "checking") {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Vérification des permissions...</p>
        </div>
      </div>
    );
  }

  if (authStatus === "unauthorized") {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white border border-gray-200 max-w-md w-full text-center p-8">
          <div className="text-red-600 text-6xl mb-4">🔒</div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">
            Connexion requise
          </h2>
          <p className="text-gray-600 mb-6">
            Vous devez être connecté pour accéder à cette page.
          </p>
          <div className="flex space-x-3">
            <button
              onClick={() => (window.location.href = "/")}
              className="flex-1 bg-blue-600 text-white px-6 py-2 hover:bg-blue-700 transition-colors"
            >
              Se connecter
            </button>
            <button
              onClick={() => window.history.back()}
              className="flex-1 bg-gray-100 text-gray-700 px-6 py-2 hover:bg-gray-200 transition-colors border border-gray-300"
            >
              Retour
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (authStatus === "forbidden") {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white border border-gray-200 max-w-md w-full text-center p-8">
          <div className="text-red-600 text-6xl mb-4">🚫</div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">
            Accès refusé
          </h2>
          <p className="text-gray-600 mb-2">
            Cette page est réservée aux super administrateurs.
          </p>
          <p className="text-sm text-gray-500 mb-6">
            Votre rôle actuel :{" "}
            <span className="font-medium">
              {currentUser?.user_type || "non défini"}
            </span>
          </p>
          <button
            onClick={() => window.history.back()}
            className="w-full bg-blue-600 text-white px-6 py-2 hover:bg-blue-700 transition-colors"
          >
            Retour
          </button>
        </div>
      </div>
    );
  }

  // Chargement des données
  if (statsLoading && !systemStats) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">
            Chargement des statistiques avec store unifié...
          </p>
        </div>
      </div>
    );
  }

  // Erreur dans le chargement des données
  if (error && authStatus === "ready" && !systemStats) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white border border-gray-200 max-w-md w-full text-center p-8">
          <div className="text-amber-600 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Erreur</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => {
              setSystemStats(null);
              setError(null);
              loadAllStatistics();
            }}
            className="w-full bg-blue-600 text-white px-6 py-2 hover:bg-blue-700 transition-colors"
          >
            Réessayer
          </button>
        </div>
      </div>
    );
  }

  // PAGE PRINCIPALE - AVEC GESTION CORRECTE DES ONGLETS
  return (
    <div className="min-h-screen bg-gray-100">
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-8">
              <div className="flex items-center">
                <img src="/images/logo.png" alt="Logo" className="h-8 w-auto" />
              </div>

              <div className="flex items-center space-x-8">
                <button
                  onClick={() => handleTabChange("dashboard")}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === "dashboard"
                      ? "text-blue-600 border-b-2 border-blue-600"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  Tableau de bord
                </button>
                <button
                  onClick={() => handleTabChange("questions")}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === "questions"
                      ? "text-blue-600 border-b-2 border-blue-600"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  Questions & Réponses
                </button>
                <button
                  onClick={() => handleTabChange("quality")}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === "quality"
                      ? "text-blue-600 border-b-2 border-blue-600"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  Anomalies
                </button>
                <button
                  onClick={() => handleTabChange("invitations")}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === "invitations"
                      ? "text-blue-600 border-b-2 border-blue-600"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  Invitations
                </button>
                <button
                  onClick={() => handleTabChange("satisfaction")}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === "satisfaction"
                      ? "text-blue-600 border-b-2 border-blue-600"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  Satisfaction
                </button>
                <button
                  onClick={() => handleTabChange("metrics")}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === "metrics"
                      ? "text-blue-600 border-b-2 border-blue-600"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  Métriques
                </button>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {activeTab === "dashboard" && (
                <button
                  onClick={() => {
                    setSystemStats(null);
                    setError(null);
                    loadAllStatistics();
                  }}
                  disabled={statsLoading}
                  className="bg-blue-600 text-white px-3 py-1 text-sm hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center space-x-1"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  <span>{statsLoading ? "Loading..." : "Refresh"}</span>
                </button>
              )}

              {activeTab === "questions" && (
                <button
                  onClick={() => {
                    questionsLoadedRef.current.clear();
                    loadQuestionLogs();
                  }}
                  disabled={questionsLoading}
                  className="bg-blue-600 text-white px-3 py-1 text-sm hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center space-x-1"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  <span>{questionsLoading ? "Loading..." : "Refresh"}</span>
                </button>
              )}

              {activeTab === "invitations" && (
                <button
                  onClick={() => {
                    invitationsLoadedRef.current = false;
                    loadInvitationStats();
                  }}
                  disabled={invitationLoading}
                  className="bg-blue-600 text-white px-3 py-1 text-sm hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center space-x-1"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  <span>{invitationLoading ? "Loading..." : "Refresh"}</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === "dashboard" ? (
          <StatisticsDashboard
            systemStats={systemStats}
            usageStats={usageStats}
            billingStats={billingStats}
            performanceStats={performanceStats}
            cacheStatus={
              dashboardCacheStatus
                ? {
                    ...dashboardCacheStatus,
                    performance_gain:
                      typeof dashboardCacheStatus.performance_gain === "string"
                        ? dashboardCacheStatus.performance_gain
                        : `${dashboardCacheStatus.performance_gain}%`,
                  }
                : null
            }
            isLoading={statsLoading}
          />
        ) : activeTab === "questions" ? (
          <QuestionsTab
            questionLogs={questionLogs}
            questionFilters={questionFilters}
            setQuestionFilters={setQuestionFilters}
            selectedTimeRange={selectedTimeRange}
            setSelectedTimeRange={setSelectedTimeRange}
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
            questionsPerPage={questionsPerPage}
            setSelectedQuestion={setSelectedQuestion}
            isLoading={questionsLoading}
            totalQuestions={totalQuestions}
            cacheStatus={
              questionsCacheStatus
                ? {
                    ...questionsCacheStatus,
                    performance_gain:
                      typeof questionsCacheStatus.performance_gain === "string"
                        ? questionsCacheStatus.performance_gain
                        : `${questionsCacheStatus.performance_gain}%`,
                  }
                : null
            }
          />
        ) : activeTab === "quality" ? (
          <QualityIssuesTab token={authToken} />
        ) : activeTab === "invitations" ? (
          <>
            {invitationLoading && !invitationStats ? (
              <div className="bg-white border border-gray-200 p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">
                  Chargement des statistiques d'invitations...
                </p>
              </div>
            ) : (
              <InvitationStatsComponent
                invitationStats={invitationStats}
                cacheStatus={
                  invitationCacheStatus
                    ? {
                        ...invitationCacheStatus,
                        performance_gain:
                          typeof invitationCacheStatus.performance_gain ===
                          "string"
                            ? invitationCacheStatus.performance_gain
                            : `${invitationCacheStatus.performance_gain}%`,
                      }
                    : null
                }
                isLoading={invitationLoading}
              />
            )}
          </>
        ) : activeTab === "satisfaction" ? (
          <SatisfactionStatsTab timeRange={selectedTimeRange} />
        ) : activeTab === "metrics" ? (
          <div className="bg-white border border-gray-200 p-6">
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Métriques Système</h2>
              <p className="text-sm text-gray-600">
                Dashboards Grafana pour le monitoring en temps réel
              </p>
            </div>
            <div className="border border-gray-300 rounded-lg overflow-hidden">
              <iframe
                src="https://inteliacognito.grafana.net/d/dorfxct/intelia-llm-monitoring?orgId=1&kiosk=tv&theme=light"
                width="100%"
                height="800"
                frameBorder="0"
                title="Grafana Metrics Dashboard"
                className="w-full"
              />
            </div>
            <div className="mt-4 text-xs text-gray-500">
              <p>📊 Dashboard mis à jour en temps réel depuis Grafana Cloud</p>
            </div>
          </div>
        ) : null}

        {/* Modal de détail de question */}
        {selectedQuestion && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-gray-200">
              <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <svg
                    className="w-5 h-5 text-blue-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <h3 className="text-base font-medium text-gray-900">
                    Détails de la Question
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedQuestion(null)}
                  className="text-gray-400 hover:text-gray-600 p-1"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              <div className="p-4">
                <div className="space-y-4">
                  <div className="bg-blue-50 p-4 border border-blue-200">
                    <h4 className="font-medium text-gray-900 mb-2 flex items-center space-x-2">
                      <span>❓</span>
                      <span>Question:</span>
                    </h4>
                    <p className="text-gray-700">{selectedQuestion.question}</p>
                  </div>

                  <div className="bg-gray-50 p-4 border border-gray-200">
                    <h4 className="font-medium text-gray-900 mb-2 flex items-center space-x-2">
                      <span>💬</span>
                      <span>Réponse:</span>
                    </h4>
                    <div className="text-gray-700 whitespace-pre-wrap">
                      {selectedQuestion.response}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="bg-white p-4 border border-gray-200">
                      <h4 className="font-medium text-gray-900 mb-3 flex items-center space-x-2">
                        <span>📊</span>
                        <span>Métadonnées:</span>
                      </h4>
                      <table className="w-full text-sm">
                        <tbody className="space-y-2">
                          <tr>
                            <td className="text-gray-600 py-1">Source:</td>
                            <td className="font-medium py-1">
                              {selectedQuestion.response_source}
                            </td>
                          </tr>
                          <tr>
                            <td className="text-gray-600 py-1">Confiance:</td>
                            <td className="font-medium py-1">
                              {(
                                selectedQuestion.confidence_score * 100
                              ).toFixed(1)}
                              %
                            </td>
                          </tr>
                          <tr>
                            <td className="text-gray-600 py-1">Temps:</td>
                            <td className="font-medium py-1">
                              {selectedQuestion.response_time}s
                            </td>
                          </tr>
                          <tr>
                            <td className="text-gray-600 py-1">Langue:</td>
                            <td className="font-medium py-1">
                              {selectedQuestion.language}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    <div className="bg-white p-4 border border-gray-200">
                      <h4 className="font-medium text-gray-900 mb-3 flex items-center space-x-2">
                        <span>👤</span>
                        <span>Utilisateur:</span>
                      </h4>
                      <table className="w-full text-sm">
                        <tbody className="space-y-2">
                          <tr>
                            <td className="text-gray-600 py-1">Email:</td>
                            <td className="font-medium py-1">
                              {selectedQuestion.user_email}
                            </td>
                          </tr>
                          <tr>
                            <td className="text-gray-600 py-1">Session:</td>
                            <td className="font-medium py-1">
                              {selectedQuestion.session_id.substring(0, 12)}...
                            </td>
                          </tr>
                          <tr>
                            <td className="text-gray-600 py-1">Date:</td>
                            <td className="font-medium py-1">
                              {new Date(
                                selectedQuestion.timestamp,
                              ).toLocaleString("fr-FR")}
                            </td>
                          </tr>
                          <tr>
                            <td className="text-gray-600 py-1">Feedback:</td>
                            <td className="text-lg py-1">
                              {getFeedbackIcon(selectedQuestion.feedback)}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {selectedQuestion.feedback_comment && (
                    <div className="bg-purple-50 p-4 border border-purple-200">
                      <h4 className="font-medium text-gray-900 mb-2 flex items-center space-x-2">
                        <span>💭</span>
                        <span>Commentaire:</span>
                      </h4>
                      <p className="text-gray-700 italic">
                        "{selectedQuestion.feedback_comment}"
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
