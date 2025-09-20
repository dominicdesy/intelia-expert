import React from "react";

// Types pour les données
interface QuestionLog {
  id: string;
  timestamp: string;
  user_email: string;
  user_name: string;
  question: string;
  response: string;
  response_source:
    | "rag"
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

// Props du composant
interface QuestionsTabProps {
  questionLogs: QuestionLog[];
  questionFilters: {
    search: string;
    source: string;
    confidence: string;
    feedback: string;
    user: string;
  };
  setQuestionFilters: React.Dispatch<
    React.SetStateAction<{
      search: string;
      source: string;
      confidence: string;
      feedback: string;
      user: string;
    }>
  >;
  selectedTimeRange: "day" | "week" | "month" | "year";
  setSelectedTimeRange: React.Dispatch<
    React.SetStateAction<"day" | "week" | "month" | "year">
  >;
  currentPage: number;
  setCurrentPage: React.Dispatch<React.SetStateAction<number>>;
  questionsPerPage: number;
  setSelectedQuestion: React.Dispatch<React.SetStateAction<QuestionLog | null>>;
  isLoading?: boolean;
  totalQuestions?: number;
  cacheStatus?: {
    is_available: boolean;
    last_update: string | null;
    cache_age_minutes: number;
    performance_gain: string;
  } | null;
}

// Interface pour l'export CSV
interface ConversationExport {
  session_id: string;
  user_email: string;
  user_name: string;
  start_time: string;
  end_time: string;
  total_questions: number;
  questions: string[];
  responses: string[];
  sources: string[];
  confidence_scores: number[];
  response_times: number[];
  feedback_scores: (number | null)[];
  feedback_comments: (string | null)[];
}

export const QuestionsTab: React.FC<QuestionsTabProps> = ({
  questionLogs,
  questionFilters,
  setQuestionFilters,
  selectedTimeRange,
  setSelectedTimeRange,
  currentPage,
  setCurrentPage,
  questionsPerPage,
  setSelectedQuestion,
  isLoading = false,
  totalQuestions = 0,
  cacheStatus = null,
}) => {
  // Fonctions utilitaires pour le styling
  const getConfidenceColor = (score: number) => {
    if (score >= 0.9) return "text-green-600 bg-green-100";
    if (score >= 0.7) return "text-yellow-600 bg-yellow-100";
    return "text-red-600 bg-red-100";
  };

  const getSourceColor = (source: string) => {
    switch (source) {
      case "rag":
        return "text-blue-600 bg-blue-100";
      case "openai_fallback":
        return "text-purple-600 bg-purple-100";
      case "table_lookup":
        return "text-green-600 bg-green-100";
      case "validation_rejected":
        return "text-red-600 bg-red-100";
      case "quota_exceeded":
        return "text-orange-600 bg-orange-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  const getSourceLabel = (source: string) => {
    switch (source) {
      case "rag":
        return "RAG";
      case "openai_fallback":
        return "OpenAI";
      case "table_lookup":
        return "Table";
      case "validation_rejected":
        return "Rejeté";
      case "quota_exceeded":
        return "Quota";
      default:
        return "Inconnu";
    }
  };

  const getFeedbackIcon = (feedback: number | null) => {
    if (feedback === 1) return "👍";
    if (feedback === -1) return "👎";
    return "❓";
  };

  // Fonction CSV avancée - Conversations en lignes
  const groupQuestionsByConversation = (
    questions: QuestionLog[],
  ): ConversationExport[] => {
    const conversationMap = new Map<string, QuestionLog[]>();

    questions.forEach((question) => {
      const sessionId = question.session_id;
      if (!conversationMap.has(sessionId)) {
        conversationMap.set(sessionId, []);
      }
      conversationMap.get(sessionId)!.push(question);
    });

    const conversations: ConversationExport[] = [];

    conversationMap.forEach((sessionQuestions, sessionId) => {
      sessionQuestions.sort(
        (a, b) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      );

      const firstQuestion = sessionQuestions[0];
      const lastQuestion = sessionQuestions[sessionQuestions.length - 1];

      conversations.push({
        session_id: sessionId,
        user_email: firstQuestion.user_email,
        user_name: firstQuestion.user_name,
        start_time: firstQuestion.timestamp,
        end_time: lastQuestion.timestamp,
        total_questions: sessionQuestions.length,
        questions: sessionQuestions.map((q) => q.question),
        responses: sessionQuestions.map((q) => q.response),
        sources: sessionQuestions.map((q) => getSourceLabel(q.response_source)),
        confidence_scores: sessionQuestions.map((q) => q.confidence_score),
        response_times: sessionQuestions.map((q) => q.response_time),
        feedback_scores: sessionQuestions.map((q) => q.feedback),
        feedback_comments: sessionQuestions.map((q) => q.feedback_comment),
      });
    });

    return conversations;
  };

  // Export CSV Conversations avec choix de scope
  const exportConversationsToCSV = () => {
    try {
      const shouldExportAll = window.confirm(
        `🤔 Choix de l'export :\n\n` +
          `• OUI = Exporter TOUTES les ${totalQuestions} questions de la base\n` +
          `• NON = Exporter seulement les ${filteredQuestions.length} questions affichées\n\n` +
          `Voulez-vous exporter TOUTES les questions ?`,
      );

      let questionsToExport: QuestionLog[];
      let exportScope: string;

      if (shouldExportAll) {
        questionsToExport = questionLogs;
        exportScope = "TOUTES";

        if (questionLogs.length < totalQuestions) {
          const proceed = window.confirm(
            `⚠️ Attention :\n\n` +
              `• Total questions dans la base : ${totalQuestions}\n` +
              `• Questions actuellement chargées : ${questionLogs.length}\n\n` +
              `L'export contiendra seulement les ${questionLogs.length} questions chargées.\n\n` +
              `Continuer l'export ?`,
          );
          if (!proceed) return;
        }
      } else {
        questionsToExport = filteredQuestions;
        exportScope = "FILTRÉES";
      }

      if (questionsToExport.length === 0) {
        alert("❌ Aucune question à exporter dans la sélection");
        return;
      }

      const conversations = groupQuestionsByConversation(questionsToExport);
      const maxQuestions = Math.max(
        ...conversations.map((c) => c.total_questions),
      );

      console.log(
        `📊 Export CSV ${exportScope} de ${conversations.length} conversations, max ${maxQuestions} questions`,
      );

      const headers = [
        "N°",
        "Session ID",
        "Utilisateur",
        "Email",
        "Début",
        "Fin",
        "Nb Questions",
        "Durée (min)",
      ];

      for (let i = 0; i < maxQuestions; i++) {
        headers.push(
          `Q${i + 1}`,
          `R${i + 1}`,
          `Source${i + 1}`,
          `Confiance${i + 1}`,
          `Temps${i + 1}`,
          `Feedback${i + 1}`,
          `Commentaire${i + 1}`,
        );
      }

      const escapeCSV = (value: any): string => {
        if (value === null || value === undefined) return "";
        const str = String(value);
        if (
          str.includes('"') ||
          str.includes(",") ||
          str.includes("\n") ||
          str.includes("\r")
        ) {
          return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
      };

      let csvContent = headers.map(escapeCSV).join(",") + "\n";

      conversations.forEach((conv, index) => {
        const rowData: any[] = [
          index + 1,
          conv.session_id.substring(0, 12) + "...",
          conv.user_name,
          conv.user_email,
          new Date(conv.start_time).toLocaleString("fr-FR"),
          new Date(conv.end_time).toLocaleString("fr-FR"),
          conv.total_questions,
          Math.max(
            1,
            Math.round(
              (new Date(conv.end_time).getTime() -
                new Date(conv.start_time).getTime()) /
                60000,
            ),
          ),
        ];

        for (let i = 0; i < maxQuestions; i++) {
          rowData.push(
            conv.questions[i] || "",
            conv.responses[i] || "",
            conv.sources[i] || "",
            conv.confidence_scores[i]
              ? `${(conv.confidence_scores[i] * 100).toFixed(1)}%`
              : "",
            conv.response_times[i] ? `${conv.response_times[i]}s` : "",
            conv.feedback_scores[i] !== null
              ? conv.feedback_scores[i] === 1
                ? "Positif"
                : "Négatif"
              : "",
            conv.feedback_comments[i] || "",
          );
        }

        csvContent += rowData.map(escapeCSV).join(",") + "\n";
      });

      const scopeSuffix = shouldExportAll ? "TOUTES" : "FILTREES";
      const fileName = `conversations_${scopeSuffix}_${new Date().toISOString().split("T")[0]}_${Date.now()}.csv`;

      const bom = "\uFEFF";
      const blob = new Blob([bom + csvContent], {
        type: "text/csv;charset=utf-8",
      });
      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      console.log(
        `✅ Export CSV conversations ${exportScope} réussi: ${fileName}`,
      );

      const uniqueUsers = new Set(questionsToExport.map((q) => q.user_email))
        .size;
      const summary = `✅ Export CSV ${exportScope} réussi !

📊 Scope: ${exportScope} les questions
• ${conversations.length} conversations (lignes)
• ${questionsToExport.length} questions au total
• ${uniqueUsers} utilisateurs uniques
• ${maxQuestions} questions max par conversation

📄 Fichier: ${fileName}

📋 Format: Une ligne par conversation
• Colonnes fixes: Session, Utilisateur, Dates...
• Colonnes dynamiques: Q1, R1, Q2, R2, Q3, R3...

💡 Ouvrir avec Excel pour format tabulaire !`;

      alert(summary);
    } catch (error) {
      console.error("❌ Erreur export CSV conversations:", error);
      alert(`❌ Erreur export CSV: ${error}`);
    }
  };

  // Filtrage côté client
  const filteredQuestions = questionLogs.filter((q) => {
    if (
      questionFilters.search &&
      !q.question
        .toLowerCase()
        .includes(questionFilters.search.toLowerCase()) &&
      !q.response
        .toLowerCase()
        .includes(questionFilters.search.toLowerCase()) &&
      !q.user_email.toLowerCase().includes(questionFilters.search.toLowerCase())
    ) {
      return false;
    }
    if (
      questionFilters.source !== "all" &&
      q.response_source !== questionFilters.source
    )
      return false;
    if (questionFilters.confidence !== "all") {
      const score = q.confidence_score;
      if (questionFilters.confidence === "high" && score < 0.9) return false;
      if (
        questionFilters.confidence === "medium" &&
        (score < 0.7 || score >= 0.9)
      )
        return false;
      if (questionFilters.confidence === "low" && score >= 0.7) return false;
    }
    if (questionFilters.feedback !== "all") {
      if (questionFilters.feedback === "positive" && q.feedback !== 1)
        return false;
      if (questionFilters.feedback === "negative" && q.feedback !== -1)
        return false;
      if (questionFilters.feedback === "none" && q.feedback !== null)
        return false;
      if (questionFilters.feedback === "with_comments" && !q.feedback_comment)
        return false;
      if (questionFilters.feedback === "no_comments" && q.feedback_comment)
        return false;
    }
    if (questionFilters.user !== "all" && q.user_email !== questionFilters.user)
      return false;
    return true;
  });

  // Calculs statistiques
  const uniqueUsers = Array.from(
    new Set(questionLogs.map((q) => q.user_email)),
  );
  const feedbackStats = {
    total: questionLogs.filter((q) => q.feedback !== null).length,
    positive: questionLogs.filter((q) => q.feedback === 1).length,
    negative: questionLogs.filter((q) => q.feedback === -1).length,
    withComments: questionLogs.filter((q) => q.feedback_comment).length,
    satisfactionRate:
      questionLogs.filter((q) => q.feedback !== null).length > 0
        ? (questionLogs.filter((q) => q.feedback === 1).length /
            questionLogs.filter((q) => q.feedback !== null).length) *
          100
        : 0,
  };

  const sourceStats = questionLogs.reduce(
    (acc, q) => {
      acc[q.response_source] = (acc[q.response_source] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  // Affichage spécial si chargement
  if (isLoading && questionLogs.length === 0) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement des questions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header simple */}
      <div className="bg-white border-b border-gray-200">
        <div className="flex items-center space-x-8 px-4 py-3">
          <div className="flex items-center space-x-2">
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
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
            <h2 className="text-lg font-medium text-gray-900">
              Questions & Réponses
            </h2>
          </div>

          {isLoading && (
            <div className="flex items-center text-blue-600 ml-auto">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              <span className="text-sm">Chargement...</span>
            </div>
          )}
        </div>
      </div>

      {/* Filtres */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-base font-medium text-gray-900">Filtres</h3>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Recherche
              </label>
              <input
                type="text"
                value={questionFilters.search}
                onChange={(e) =>
                  setQuestionFilters((prev) => ({
                    ...prev,
                    search: e.target.value,
                  }))
                }
                placeholder="Rechercher..."
                className="w-full border border-gray-300 px-3 py-1 text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Source
              </label>
              <select
                value={questionFilters.source}
                onChange={(e) =>
                  setQuestionFilters((prev) => ({
                    ...prev,
                    source: e.target.value,
                  }))
                }
                className="w-full border border-gray-300 px-3 py-1 text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">Toutes les sources</option>
                <option value="rag">RAG</option>
                <option value="openai_fallback">OpenAI Fallback</option>
                <option value="table_lookup">Table Lookup</option>
                <option value="validation_rejected">Rejeté</option>
                <option value="quota_exceeded">Quota Dépassé</option>
                <option value="unknown">Inconnu</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Confiance
              </label>
              <select
                value={questionFilters.confidence}
                onChange={(e) =>
                  setQuestionFilters((prev) => ({
                    ...prev,
                    confidence: e.target.value,
                  }))
                }
                className="w-full border border-gray-300 px-3 py-1 text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">Tous niveaux</option>
                <option value="high">Élevée (≥90%)</option>
                <option value="medium">Moyenne (70-89%)</option>
                <option value="low">Faible (&lt;70%)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Feedback
              </label>
              <select
                value={questionFilters.feedback}
                onChange={(e) =>
                  setQuestionFilters((prev) => ({
                    ...prev,
                    feedback: e.target.value,
                  }))
                }
                className="w-full border border-gray-300 px-3 py-1 text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">Tous feedback</option>
                <option value="positive">Positif 👍</option>
                <option value="negative">Négatif 👎</option>
                <option value="none">Aucun feedback</option>
                <option value="with_comments">Avec commentaires</option>
                <option value="no_comments">Sans commentaires</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Utilisateur
              </label>
              <select
                value={questionFilters.user}
                onChange={(e) =>
                  setQuestionFilters((prev) => ({
                    ...prev,
                    user: e.target.value,
                  }))
                }
                className="w-full border border-gray-300 px-3 py-1 text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">Tous utilisateurs</option>
                {uniqueUsers.map((email) => (
                  <option key={email} value={email}>
                    {email.length > 25 ? email.substring(0, 25) + "..." : email}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Période
              </label>
              <select
                value={selectedTimeRange}
                onChange={(e) => setSelectedTimeRange(e.target.value as any)}
                className="w-full border border-gray-300 px-3 py-1 text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="day">Aujourd'hui</option>
                <option value="week">Cette semaine</option>
                <option value="month">Ce mois</option>
                <option value="year">Cette année</option>
              </select>
            </div>
          </div>

          <div className="mt-3 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <p className="text-sm text-gray-600">
                <span className="font-medium">{filteredQuestions.length}</span>{" "}
                question(s) trouvée(s) sur{" "}
                <span className="font-medium">{questionLogs.length}</span>{" "}
                affichées
                {totalQuestions > questionLogs.length && (
                  <span className="text-blue-600">
                    {" "}
                    (Total: {totalQuestions})
                  </span>
                )}
              </p>
              {filteredQuestions.length !== questionLogs.length && (
                <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800">
                  Filtré
                </span>
              )}
            </div>
            <button
              onClick={() => {
                setQuestionFilters({
                  search: "",
                  source: "all",
                  confidence: "all",
                  feedback: "all",
                  user: "all",
                });
                setCurrentPage(1);
              }}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              Réinitialiser les filtres
            </button>
          </div>
        </div>
      </div>

      {/* Analyse côte à côte */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Feedback Analysis */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-base font-medium text-gray-900">
              Analyse des Commentaires
            </h3>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="text-center p-3 bg-green-50 border border-green-200">
                <div className="text-xl font-semibold text-green-600">
                  {feedbackStats.positive}
                </div>
                <div className="text-xs text-green-700">Feedback Positifs</div>
              </div>
              <div className="text-center p-3 bg-red-50 border border-red-200">
                <div className="text-xl font-semibold text-red-600">
                  {feedbackStats.negative}
                </div>
                <div className="text-xs text-red-700">Feedback Négatifs</div>
              </div>
            </div>

            <div className="space-y-2 mb-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Total des feedback:</span>
                <span className="font-medium">{feedbackStats.total}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Avec commentaires:</span>
                <span className="font-medium">
                  {feedbackStats.withComments}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Taux de satisfaction:</span>
                <span
                  className={`font-medium ${feedbackStats.satisfactionRate >= 80 ? "text-green-600" : feedbackStats.satisfactionRate >= 60 ? "text-yellow-600" : "text-red-600"}`}
                >
                  {feedbackStats.satisfactionRate.toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Barre de progression */}
            <div className="w-full bg-gray-200 h-2 mb-4">
              <div
                className={`h-2 transition-all duration-300 ${
                  feedbackStats.satisfactionRate >= 80
                    ? "bg-green-500"
                    : feedbackStats.satisfactionRate >= 60
                      ? "bg-yellow-500"
                      : "bg-red-500"
                }`}
                style={{ width: `${feedbackStats.satisfactionRate}%` }}
              ></div>
            </div>

            {/* Commentaires récents */}
            <div className="border-t border-gray-200 pt-3">
              <h4 className="text-sm font-medium text-gray-800 mb-2">
                Commentaires Récents
              </h4>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {questionLogs
                  .filter((q) => q.feedback_comment)
                  .sort(
                    (a, b) =>
                      new Date(b.timestamp).getTime() -
                      new Date(a.timestamp).getTime(),
                  )
                  .slice(0, 3)
                  .map((question) => (
                    <div
                      key={question.id}
                      className="border border-gray-200 p-2 hover:bg-gray-50"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-gray-500">
                          {question.user_email}
                        </span>
                        <span className="text-sm">
                          {getFeedbackIcon(question.feedback)}
                        </span>
                      </div>
                      <p className="text-xs text-gray-700 italic line-clamp-2">
                        "{question.feedback_comment}"
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(question.timestamp).toLocaleDateString(
                          "fr-FR",
                        )}
                      </p>
                    </div>
                  ))}

                {questionLogs.filter((q) => q.feedback_comment).length ===
                  0 && (
                  <p className="text-sm text-gray-500 italic text-center py-4">
                    Aucun commentaire disponible
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Sources Distribution */}
        <div className="bg-white border border-gray-200">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-base font-medium text-gray-900">
              Distribution des Sources
            </h3>
          </div>
          <div className="p-4">
            <div className="space-y-3">
              {Object.entries(sourceStats)
                .sort(([, a], [, b]) => b - a)
                .map(([source, count]) => {
                  const percentage =
                    questionLogs.length > 0
                      ? (count / questionLogs.length) * 100
                      : 0;

                  return (
                    <div
                      key={source}
                      className="flex items-center justify-between"
                    >
                      <div className="flex items-center space-x-2">
                        <span
                          className={`inline-flex items-center px-2 py-1 text-xs font-medium ${getSourceColor(source)}`}
                        >
                          {getSourceLabel(source)}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-gray-200 h-2">
                          <div
                            className={`h-2 transition-all duration-300 ${
                              source === "rag"
                                ? "bg-blue-500"
                                : source === "openai_fallback"
                                  ? "bg-purple-500"
                                  : source === "table_lookup"
                                    ? "bg-green-500"
                                    : source === "validation_rejected"
                                      ? "bg-red-500"
                                      : source === "quota_exceeded"
                                        ? "bg-orange-500"
                                        : "bg-gray-500"
                            }`}
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-medium text-gray-900 w-12 text-right">
                          {count}
                        </span>
                      </div>
                    </div>
                  );
                })}
            </div>

            {/* Métriques de qualité */}
            <div className="mt-4 pt-3 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-800 mb-2">
                Métriques de Qualité
              </h4>
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center p-2 bg-blue-50 border border-blue-200">
                  <div className="text-lg font-semibold text-blue-600">
                    {questionLogs.length > 0
                      ? (
                          (questionLogs.reduce(
                            (sum, q) => sum + q.confidence_score,
                            0,
                          ) /
                            questionLogs.length) *
                          100
                        ).toFixed(1)
                      : "0.0"}
                    %
                  </div>
                  <div className="text-xs text-blue-700">Confiance Moyenne</div>
                </div>
                <div className="text-center p-2 bg-green-50 border border-green-200">
                  <div className="text-lg font-semibold text-green-600">
                    {questionLogs.length > 0
                      ? (
                          questionLogs.reduce(
                            (sum, q) => sum + q.response_time,
                            0,
                          ) / questionLogs.length
                        ).toFixed(1)
                      : "0.0"}
                    s
                  </div>
                  <div className="text-xs text-green-700">Temps Moyen</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Export Section */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-base font-medium text-gray-900">
            Export des Données
          </h3>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-stretch">
            {/* Carte 1: Conversations */}
            <div className="bg-white border border-gray-200 p-4 flex flex-col justify-between h-full">
              <div>
                <h4 className="text-base font-medium text-gray-900 mb-1">
                  Conversations
                </h4>
                <p className="text-sm text-gray-600 mb-3">
                  Format ligne par conversation, compatible Excel
                </p>
                <div className="text-xs text-gray-500 mb-4">
                  <p>
                    • Choix automatique: Filtrées ({filteredQuestions.length})
                    ou toutes ({totalQuestions})
                  </p>
                  <p>• Colonnes: Q1, R1, Source1, Q2, R2, Source2...</p>
                </div>
              </div>
              <button
                onClick={() => exportConversationsToCSV()}
                disabled={questionLogs.length === 0}
                className="w-full bg-blue-600 text-white px-4 py-2 text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Exporter CSV
              </button>
            </div>

            {/* Carte 2: Commentaires */}
            <div className="bg-white border border-gray-200 p-4 flex flex-col justify-between h-full">
              <div>
                <h4 className="text-base font-medium text-gray-900 mb-1">
                  Commentaires
                </h4>
                <p className="text-sm text-gray-600 mb-3">
                  Feedback et commentaires utilisateurs
                </p>
                <div className="text-xs text-gray-500 mb-4">
                  <p>• Feedback positifs et négatifs</p>
                  <p>• Commentaires avec contexte question</p>
                </div>
              </div>
              <button
                onClick={() => {
                  const commentsData = questionLogs
                    .filter((q) => q.feedback_comment)
                    .map((q) => ({
                      date: new Date(q.timestamp).toLocaleDateString("fr-FR"),
                      user: q.user_email,
                      question: q.question.substring(0, 100) + "...",
                      feedback: q.feedback === 1 ? "Positif" : "Négatif",
                      comment: q.feedback_comment,
                      source: getSourceLabel(q.response_source),
                      confidence: (q.confidence_score * 100).toFixed(1) + "%",
                    }));

                  const csvContent =
                    "data:text/csv;charset=utf-8," +
                    "Date,Utilisateur,Question,Feedback,Commentaire,Source,Confiance\n" +
                    commentsData
                      .map((row) =>
                        Object.values(row)
                          .map((field) => `"${field}"`)
                          .join(","),
                      )
                      .join("\n");

                  const encodedUri = encodeURI(csvContent);
                  const link = document.createElement("a");
                  link.setAttribute("href", encodedUri);
                  link.setAttribute(
                    "download",
                    `commentaires_feedback_${new Date().toISOString().split("T")[0]}.csv`,
                  );
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);
                }}
                className="w-full bg-blue-600 text-white px-4 py-2 text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Exporter CSV
              </button>
            </div>

            {/* Carte 3: Questions Filtrées */}
            <div className="bg-white border border-gray-200 p-4 flex flex-col justify-between h-full">
              <div>
                <h4 className="text-base font-medium text-gray-900 mb-1">
                  Questions Filtrées
                </h4>
                <p className="text-sm text-gray-600 mb-3">
                  Questions actuellement affichées
                </p>
                <div className="text-xs text-gray-500 mb-4">
                  <p>• {filteredQuestions.length} questions sélectionnées</p>
                  <p>• Données complètes avec réponses</p>
                </div>
              </div>
              <button
                onClick={() => {
                  const questionsData = filteredQuestions.map((q) => ({
                    date: new Date(q.timestamp).toLocaleDateString("fr-FR"),
                    user: q.user_email,
                    question: q.question,
                    response: q.response.substring(0, 200) + "...",
                    source: getSourceLabel(q.response_source),
                    confidence: (q.confidence_score * 100).toFixed(1) + "%",
                    response_time: q.response_time + "s",
                    feedback:
                      q.feedback === 1
                        ? "Positif"
                        : q.feedback === -1
                          ? "Négatif"
                          : "Aucun",
                  }));

                  const csvContent =
                    "data:text/csv;charset=utf-8," +
                    "Date,Utilisateur,Question,Réponse,Source,Confiance,Temps,Feedback\n" +
                    questionsData
                      .map((row) =>
                        Object.values(row)
                          .map((field) => `"${field}"`)
                          .join(","),
                      )
                      .join("\n");

                  const encodedUri = encodeURI(csvContent);
                  const link = document.createElement("a");
                  link.setAttribute("href", encodedUri);
                  link.setAttribute(
                    "download",
                    `questions_export_${new Date().toISOString().split("T")[0]}.csv`,
                  );
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);
                }}
                className="w-full bg-blue-600 text-white px-4 py-2 text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Exporter CSV
              </button>
            </div>

            {/* Carte 4: Statistiques */}
            <div className="bg-white border border-gray-200 p-4 flex flex-col justify-between h-full">
              <div>
                <h4 className="text-base font-medium text-gray-900 mb-1">
                  Statistiques
                </h4>
                <p className="text-sm text-gray-600 mb-3">
                  Données d'analyse et métriques
                </p>
                <div className="text-xs text-gray-500 mb-4">
                  <p>• Métriques de satisfaction et performance</p>
                  <p>• Format JSON pour analyse avancée</p>
                </div>
              </div>
              <button
                onClick={() => {
                  const statsData = {
                    export_date: new Date().toISOString(),
                    total_questions: totalQuestions,
                    displayed_questions: questionLogs.length,
                    filtered_questions: filteredQuestions.length,
                    unique_users: uniqueUsers.length,
                    feedback_stats: feedbackStats,
                    source_distribution: sourceStats,
                    filters_applied: questionFilters,
                  };

                  const dataStr =
                    "data:text/json;charset=utf-8," +
                    encodeURIComponent(JSON.stringify(statsData, null, 2));
                  const link = document.createElement("a");
                  link.setAttribute("href", dataStr);
                  link.setAttribute(
                    "download",
                    `stats_export_${new Date().toISOString().split("T")[0]}.json`,
                  );
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);
                }}
                className="w-full bg-blue-600 text-white px-4 py-2 text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Exporter JSON
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Table des Questions */}
      <div className="bg-white border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-base font-medium text-gray-900">
            Questions et Réponses
          </h3>
          <span className="text-sm text-gray-500">
            {filteredQuestions.length} questions affichées
          </span>
        </div>

        {filteredQuestions.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-gray-400 text-4xl mb-4">🔍</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Aucune question trouvée
            </h3>
            <p className="text-gray-500 mb-4">
              {questionFilters.search ||
              questionFilters.source !== "all" ||
              questionFilters.confidence !== "all" ||
              questionFilters.feedback !== "all" ||
              questionFilters.user !== "all"
                ? "Essayez de modifier vos filtres pour voir plus de résultats."
                : "Il n'y a pas encore de questions dans cette période."}
            </p>
            {(questionFilters.search ||
              questionFilters.source !== "all" ||
              questionFilters.confidence !== "all" ||
              questionFilters.feedback !== "all" ||
              questionFilters.user !== "all") && (
              <button
                onClick={() => {
                  setQuestionFilters({
                    search: "",
                    source: "all",
                    confidence: "all",
                    feedback: "all",
                    user: "all",
                  });
                }}
                className="bg-blue-600 text-white px-4 py-2 hover:bg-blue-700 transition-colors"
              >
                Réinitialiser les filtres
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredQuestions.map((question) => (
              <div
                key={question.id}
                className="p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    {/* En-tête condensé */}
                    <div className="flex items-center space-x-3 mb-3">
                      <div className="w-8 h-8 bg-blue-600 flex items-center justify-center text-white text-xs font-bold">
                        {question.user_name
                          .split(" ")
                          .map((n) => n[0])
                          .join("")
                          .toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900">
                          {question.user_name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {question.user_email}
                        </p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span
                          className={`inline-flex items-center px-2 py-1 text-xs font-medium ${getSourceColor(question.response_source)}`}
                        >
                          {getSourceLabel(question.response_source)}
                        </span>
                        <span
                          className={`inline-flex items-center px-2 py-1 text-xs font-medium ${getConfidenceColor(question.confidence_score)}`}
                        >
                          {(question.confidence_score * 100).toFixed(0)}%
                        </span>
                        <span className="text-lg">
                          {getFeedbackIcon(question.feedback)}
                        </span>
                        {question.feedback_comment && (
                          <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-purple-100 text-purple-800">
                            💬
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Question */}
                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-900 mb-1">
                        Question:
                      </p>
                      <p className="text-sm text-gray-700 bg-blue-50 p-3 border-l-4 border-blue-400">
                        {question.question}
                      </p>
                    </div>

                    {/* Réponse */}
                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-900 mb-1">
                        Réponse:
                      </p>
                      <div className="text-sm text-gray-700 bg-gray-50 p-3 max-h-32 overflow-y-auto border border-gray-200">
                        {question.response.split("\n").map((line, index) => (
                          <p
                            key={index}
                            className={
                              line.startsWith("**") ? "font-semibold" : ""
                            }
                          >
                            {line}
                          </p>
                        ))}
                      </div>
                    </div>

                    {/* Métadonnées */}
                    <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
                      <div className="flex items-center space-x-4">
                        <span>
                          {new Date(question.timestamp).toLocaleString("fr-FR")}
                        </span>
                        <span>{question.response_time}s</span>
                        <span>{question.language.toUpperCase()}</span>
                        <span>{question.session_id.substring(0, 8)}...</span>
                      </div>
                      <button
                        onClick={() => setSelectedQuestion(question)}
                        className="text-blue-600 hover:text-blue-800 font-medium bg-blue-50 px-2 py-1 border border-blue-200"
                      >
                        Voir détails →
                      </button>
                    </div>

                    {/* Commentaire de feedback */}
                    {question.feedback_comment && (
                      <div className="mt-3 p-3 bg-blue-50 border-l-4 border-blue-400">
                        <div className="flex items-start space-x-2">
                          <span className="text-lg">
                            {getFeedbackIcon(question.feedback)}
                          </span>
                          <div className="flex-1">
                            <p className="text-sm font-medium text-blue-900 mb-1">
                              Commentaire utilisateur:
                            </p>
                            <p className="text-sm text-blue-800 italic">
                              "{question.feedback_comment}"
                            </p>
                            <p className="text-xs text-blue-600 mt-1">
                              Feedback{" "}
                              {question.feedback === 1 ? "positif" : "négatif"}{" "}
                              •{" "}
                              {new Date(question.timestamp).toLocaleDateString(
                                "fr-FR",
                              )}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {filteredQuestions.length > 0 && (
          <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between bg-gray-50">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 border border-gray-300 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
              >
                ← Précédent
              </button>
              <span className="text-sm text-gray-600 px-2 py-1 bg-white border border-gray-300">
                Page {currentPage}
              </span>
              <button
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={filteredQuestions.length < questionsPerPage}
                className="px-3 py-1 border border-gray-300 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
              >
                Suivant →
              </button>
            </div>
            <div className="text-sm text-gray-600">
              {filteredQuestions.length} question(s) affichée(s)
              {totalQuestions > questionLogs.length && (
                <span className="text-blue-600">
                  {" "}
                  sur {totalQuestions} au total
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
