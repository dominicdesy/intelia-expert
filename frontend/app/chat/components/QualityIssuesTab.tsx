/**
 * Onglet Anomalies potentielles pour le monitoring de qualité Q&A
 * Affiche les Q&A problématiques détectées par l'IA
 */

"use client";

import React, { useState, useEffect } from "react";
import type { ProblematicQA, ProblemCategory } from "../../../types/qa-quality";
import {
  getProblematicQA,
  analyzeBatch,
  reviewQA,
  getQualityStats,
  analyzeCoT,
} from "../../../lib/services/qaQualityService";
import type { CoTAnalysisResponse } from "../../../types/qa-quality";
import { secureLog } from "@/lib/utils/secureLogger";

interface QualityIssuesTabProps {
  token: string;
}

export const QualityIssuesTab: React.FC<QualityIssuesTabProps> = ({ token }) => {
  // États
  const [problematicQA, setProblematicQA] = useState<ProblematicQA[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedQA, setSelectedQA] = useState<ProblematicQA | null>(null);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const limit = 20;

  // Filtres
  const [filters, setFilters] = useState<{
    category: string;
    reviewed: string;
    min_score: number | null;
    max_score: number | null;
  }>({
    category: "all",
    reviewed: "all",
    min_score: null,
    max_score: null,
  });

  // Stats
  const [stats, setStats] = useState<{
    total_problematic: number;
    problematic_rate: number;
    avg_quality_score: number;
  } | null>(null);

  // Batch analysis
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // CoT Analysis
  const [cotResult, setCotResult] = useState<CoTAnalysisResponse | null>(null);
  const [isAnalyzingCoT, setIsAnalyzingCoT] = useState(false);
  const [cotError, setCotError] = useState<string | null>(null);

  // Charger les données
  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const params: any = {
        page: currentPage,
        limit,
      };

      if (filters.category !== "all") params.category = filters.category;
      if (filters.reviewed !== "all") params.reviewed = filters.reviewed === "reviewed";
      if (filters.min_score !== null) params.min_score = filters.min_score;
      if (filters.max_score !== null) params.max_score = filters.max_score;

      const [qaData, statsData] = await Promise.all([
        getProblematicQA(params),
        getQualityStats({ days: 30 }),
      ]);

      setProblematicQA(qaData.problematic_qa);
      setTotalPages(qaData.pagination.pages);
      setTotalCount(qaData.pagination.total);
      setStats({
        total_problematic: statsData.total_problematic,
        problematic_rate: statsData.problematic_rate,
        avg_quality_score: statsData.avg_quality_score,
      });
    } catch (err: any) {
      secureLog.error("Error loading QA quality data:", err);
      setError(err.message || "Erreur de chargement");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [currentPage, filters]);

  // Fonctions utilitaires
  const getCategoryLabel = (category: string) => {
    const labels: Record<string, string> = {
      incorrect: "Incorrect",
      incomplete: "Incomplet",
      off_topic: "Hors sujet",
      generic: "Générique",
      contradictory: "Contradictoire",
      hallucination: "Hallucination",
      none: "Aucun",
    };
    return labels[category] || category;
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      incorrect: "bg-red-100 text-red-800 border-red-200",
      incomplete: "bg-yellow-100 text-yellow-800 border-yellow-200",
      off_topic: "bg-purple-100 text-purple-800 border-purple-200",
      generic: "bg-gray-100 text-gray-800 border-gray-200",
      contradictory: "bg-orange-100 text-orange-800 border-orange-200",
      hallucination: "bg-red-100 text-red-900 border-red-300",
    };
    return colors[category] || "bg-gray-100 text-gray-800";
  };

  const getScoreColor = (score: number | null) => {
    if (score === null) return "text-gray-500";
    if (score >= 7) return "text-green-600";
    if (score >= 5) return "text-yellow-600";
    return "text-red-600";
  };

  // Analyse batch
  const handleAnalyzeBatch = async () => {
    if (!confirm("Lancer une analyse de 50 Q&A? Coût estimé: ~$0.10")) return;

    try {
      setIsAnalyzing(true);
      const result = await analyzeBatch({ limit: 50 });
      alert(
        `Analyse terminée!\n\n` +
          `✅ ${result.analyzed_count} Q&A analysées\n` +
          `⚠️ ${result.problematic_found} problèmes détectés\n` +
          `❌ ${result.errors} erreurs`
      );
      loadData(); // Recharger les données
    } catch (err: any) {
      alert(`Erreur: ${err.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Marquer comme revu
  const handleReview = async (qa: ProblematicQA, falsePositive: boolean = false) => {
    try {
      await reviewQA({
        checkId: qa.id,
        data: {
          reviewed: true,
          false_positive: falsePositive,
          reviewer_notes: falsePositive ? "Marqué comme faux positif" : "Revu et confirmé",
        },
      });
      loadData(); // Recharger les données
    } catch (err: any) {
      alert(`Erreur: ${err.message}`);
    }
  };

  const handleAnalyzeCoT = async (checkId: string) => {
    try {
      setIsAnalyzingCoT(true);
      setCotError(null);
      const result = await analyzeCoT(parseInt(checkId));
      setCotResult(result);
    } catch (err: any) {
      secureLog.error("Error analyzing CoT:", err);
      setCotError(err.message || "Erreur lors de l'analyse CoT");
    } finally {
      setIsAnalyzingCoT(false);
    }
  };

  // Affichage
  if (isLoading && problematicQA.length === 0) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement des problèmes de qualité...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
        <p className="text-red-800 font-medium">Erreur de chargement</p>
        <p className="text-red-600 text-sm mt-1">{error}</p>
        <button
          onClick={loadData}
          className="mt-3 bg-red-600 text-white px-4 py-2 text-sm rounded hover:bg-red-700"
        >
          Réessayer
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header avec stats */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <svg
              className="w-5 h-5 text-red-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <h2 className="text-lg font-medium text-gray-900">Anomalies potentielles</h2>
          </div>
          <button
            onClick={handleAnalyzeBatch}
            disabled={isAnalyzing}
            className="bg-blue-600 text-white px-4 py-2 text-sm rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isAnalyzing ? "Analyse en cours..." : "🔍 Analyser 50 Q&A"}
          </button>
        </div>

        {stats && (
          <div className="grid grid-cols-3 gap-4 p-4">
            <div className="text-center p-3 bg-red-50 border border-red-200 rounded">
              <div className="text-2xl font-bold text-red-600">{stats.total_problematic}</div>
              <div className="text-xs text-red-700">Q&A problématiques</div>
            </div>
            <div className="text-center p-3 bg-yellow-50 border border-yellow-200 rounded">
              <div className="text-2xl font-bold text-yellow-600">
                {stats.problematic_rate.toFixed(1)}%
              </div>
              <div className="text-xs text-yellow-700">Taux de problèmes</div>
            </div>
            <div className="text-center p-3 bg-blue-50 border border-blue-200 rounded">
              <div className="text-2xl font-bold text-blue-600">
                {stats.avg_quality_score.toFixed(1)}/10
              </div>
              <div className="text-xs text-blue-700">Score qualité moyen</div>
            </div>
          </div>
        )}
      </div>

      {/* Filtres */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Catégorie</label>
            <select
              value={filters.category}
              onChange={(e) => {
                setFilters({ ...filters, category: e.target.value });
                setCurrentPage(1);
              }}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            >
              <option value="all">Toutes</option>
              <option value="incorrect">Incorrect</option>
              <option value="incomplete">Incomplet</option>
              <option value="off_topic">Hors sujet</option>
              <option value="generic">Générique</option>
              <option value="contradictory">Contradictoire</option>
              <option value="hallucination">Hallucination</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Statut</label>
            <select
              value={filters.reviewed}
              onChange={(e) => {
                setFilters({ ...filters, reviewed: e.target.value });
                setCurrentPage(1);
              }}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            >
              <option value="all">Tous</option>
              <option value="not_reviewed">Non revu</option>
              <option value="reviewed">Revu</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Score min</label>
            <input
              type="number"
              min="0"
              max="10"
              step="0.1"
              value={filters.min_score ?? ""}
              onChange={(e) => {
                setFilters({
                  ...filters,
                  min_score: e.target.value ? parseFloat(e.target.value) : null,
                });
                setCurrentPage(1);
              }}
              placeholder="0"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Score max</label>
            <input
              type="number"
              min="0"
              max="10"
              step="0.1"
              value={filters.max_score ?? ""}
              onChange={(e) => {
                setFilters({
                  ...filters,
                  max_score: e.target.value ? parseFloat(e.target.value) : null,
                });
                setCurrentPage(1);
              }}
              placeholder="10"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
        </div>
      </div>

      {/* Liste des Q&A problématiques */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-base font-medium text-gray-900">
            {totalCount} Q&A problématique{totalCount > 1 ? "s" : ""}
          </h3>
        </div>

        {problematicQA.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-gray-400 text-4xl mb-4">✅</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Aucune anomalie détectée</h3>
            <p className="text-gray-500">
              Toutes les Q&A analysées sont de bonne qualité!
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {problematicQA.map((qa) => (
              <div key={qa.id} className="p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
                      {qa.user_name.split(" ").map((n) => n[0]).join("").toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{qa.user_name}</p>
                      <p className="text-xs text-gray-500">{qa.user_email}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span
                      className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded border ${getCategoryColor(qa.problem_category)}`}
                    >
                      {getCategoryLabel(qa.problem_category)}
                    </span>
                    <span className={`text-lg font-bold ${getScoreColor(qa.quality_score)}`}>
                      {qa.quality_score?.toFixed(1) ?? "N/A"}/10
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <div>
                    <p className="text-xs font-medium text-gray-700 mb-1">Question:</p>
                    <p className="text-sm text-gray-900 bg-blue-50 p-2 rounded border-l-4 border-blue-400">
                      {qa.question}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs font-medium text-gray-700 mb-1">Problèmes détectés:</p>
                    <ul className="space-y-1">
                      {qa.problems.map((problem, idx) => (
                        <li key={idx} className="text-sm text-red-600 flex items-start">
                          <span className="mr-2">•</span>
                          <span>{problem}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {qa.recommendation && (
                    <div>
                      <p className="text-xs font-medium text-gray-700 mb-1">Recommandation:</p>
                      <p className="text-sm text-blue-700 bg-blue-50 p-2 rounded italic">
                        {qa.recommendation}
                      </p>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-200">
                  <div className="flex items-center space-x-4 text-xs text-gray-500">
                    <span>{new Date(qa.analyzed_at).toLocaleString("fr-FR")}</span>
                    <span>Confiance: {((qa.analysis_confidence ?? 0) * 100).toFixed(0)}%</span>
                    {qa.reviewed && (
                      <span className="text-green-600 font-medium">✓ Revu</span>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setSelectedQA(qa)}
                      className="text-blue-600 hover:text-blue-800 text-sm font-medium px-3 py-1 border border-blue-200 rounded hover:bg-blue-50"
                    >
                      Voir détails →
                    </button>
                    {!qa.reviewed && (
                      <>
                        <button
                          onClick={() => handleReview(qa, false)}
                          className="text-green-600 hover:text-green-800 text-sm font-medium px-3 py-1 border border-green-200 rounded hover:bg-green-50"
                        >
                          ✓ Revu
                        </button>
                        <button
                          onClick={() => handleReview(qa, true)}
                          className="text-gray-600 hover:text-gray-800 text-sm font-medium px-3 py-1 border border-gray-300 rounded hover:bg-gray-50"
                        >
                          Faux positif
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between bg-gray-50">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 border border-gray-300 text-sm rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white"
            >
              ← Précédent
            </button>
            <span className="text-sm text-gray-600">
              Page {currentPage} sur {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 border border-gray-300 text-sm rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white"
            >
              Suivant →
            </button>
          </div>
        )}
      </div>

      {/* Modal de détails */}
      {selectedQA && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-gray-900">Détails de l'anomalie</h3>
                <button
                  onClick={() => setSelectedQA(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              <div className="space-y-4">
                <div className="flex items-center space-x-4">
                  <span
                    className={`inline-flex items-center px-3 py-1 text-sm font-medium rounded border ${getCategoryColor(selectedQA.problem_category)}`}
                  >
                    {getCategoryLabel(selectedQA.problem_category)}
                  </span>
                  <span className={`text-2xl font-bold ${getScoreColor(selectedQA.quality_score)}`}>
                    {selectedQA.quality_score?.toFixed(1) ?? "N/A"}/10
                  </span>
                  <span className="text-sm text-gray-600">
                    Confiance: {((selectedQA.analysis_confidence ?? 0) * 100).toFixed(0)}%
                  </span>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">Question:</p>
                  <div className="bg-blue-50 p-4 rounded border-l-4 border-blue-400">
                    <p className="text-gray-900">{selectedQA.question}</p>
                  </div>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">Réponse:</p>
                  <div className="bg-gray-50 p-4 rounded border border-gray-200 max-h-64 overflow-y-auto">
                    <p className="text-gray-900 whitespace-pre-wrap">{selectedQA.response}</p>
                  </div>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">Problèmes détectés:</p>
                  <ul className="space-y-2">
                    {selectedQA.problems.map((problem, idx) => (
                      <li key={idx} className="flex items-start bg-red-50 p-3 rounded">
                        <span className="text-red-600 mr-2">⚠️</span>
                        <span className="text-red-800">{problem}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {selectedQA.recommendation && (
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-2">Recommandation:</p>
                    <div className="bg-blue-50 p-4 rounded border-l-4 border-blue-400">
                      <p className="text-blue-900 italic">{selectedQA.recommendation}</p>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
                  <div>
                    <p className="text-xs text-gray-500">Utilisateur</p>
                    <p className="text-sm font-medium">{selectedQA.user_name}</p>
                    <p className="text-xs text-gray-600">{selectedQA.user_email}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Date d'analyse</p>
                    <p className="text-sm font-medium">
                      {new Date(selectedQA.analyzed_at).toLocaleString("fr-FR")}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Source de réponse</p>
                    <p className="text-sm font-medium">{selectedQA.response_source || "N/A"}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Confiance système</p>
                    <p className="text-sm font-medium">
                      {selectedQA.response_confidence
                        ? `${(selectedQA.response_confidence * 100).toFixed(0)}%`
                        : "N/A"}
                    </p>
                  </div>
                </div>

                <div className="flex justify-between pt-4 border-t border-gray-200">
                  <button
                    onClick={() => handleAnalyzeCoT(selectedQA.id)}
                    disabled={isAnalyzingCoT}
                    className="px-4 py-2 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    {isAnalyzingCoT ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                        <span>Analyse en cours...</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <span>🧠 Analyser le raisonnement</span>
                      </>
                    )}
                  </button>

                  <div className="flex space-x-3">
                    {!selectedQA.reviewed && (
                      <>
                        <button
                          onClick={() => {
                            handleReview(selectedQA, true);
                            setSelectedQA(null);
                          }}
                          className="px-4 py-2 border border-gray-300 text-sm rounded hover:bg-gray-50"
                        >
                          Marquer comme faux positif
                        </button>
                        <button
                          onClick={() => {
                            handleReview(selectedQA, false);
                            setSelectedQA(null);
                          }}
                          className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                        >
                          Marquer comme revu
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => setSelectedQA(null)}
                      className="px-4 py-2 bg-gray-600 text-white text-sm rounded hover:bg-gray-700"
                    >
                      Fermer
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CoT Analysis Modal */}
      {cotResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-purple-900 flex items-center space-x-2">
                  <span>🧠</span>
                  <span>Analyse du raisonnement (Claude Extended Thinking)</span>
                </h3>
                <button
                  onClick={() => setCotResult(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              <div className="space-y-6">
                {/* Metadata */}
                <div className="bg-purple-50 p-4 rounded-lg border-l-4 border-purple-500">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-purple-700 font-medium">Tokens de raisonnement</p>
                      <p className="text-purple-900 font-bold">{cotResult.thinking_tokens.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-purple-700 font-medium">Tokens d'entrée</p>
                      <p className="text-purple-900 font-bold">{cotResult.input_tokens.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-purple-700 font-medium">Tokens de sortie</p>
                      <p className="text-purple-900 font-bold">{cotResult.output_tokens.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-purple-700 font-medium">Coût</p>
                      <p className="text-purple-900 font-bold">${cotResult.cost_usd.toFixed(4)}</p>
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-purple-200">
                    <p className="text-xs text-purple-700">
                      Analysé par <strong>{cotResult.analyzed_by}</strong> le{" "}
                      {new Date(cotResult.analyzed_at).toLocaleString("fr-FR")}
                    </p>
                  </div>
                </div>

                {/* Original Question */}
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">Question originale:</p>
                  <div className="bg-blue-50 p-4 rounded border-l-4 border-blue-400">
                    <p className="text-gray-900">{cotResult.original_question}</p>
                  </div>
                </div>

                {/* Thinking Blocks - The REASON for this analysis */}
                <div>
                  <p className="text-sm font-medium text-purple-700 mb-2 flex items-center space-x-2">
                    <span>🧠</span>
                    <span>Raisonnement de Claude (Extended Thinking):</span>
                  </p>
                  <div className="bg-purple-50 p-6 rounded border-2 border-purple-300 max-h-96 overflow-y-auto">
                    <pre className="text-sm text-purple-900 whitespace-pre-wrap font-mono">
                      {cotResult.thinking}
                    </pre>
                  </div>
                  <p className="text-xs text-purple-600 mt-2 italic">
                    ⚠️ Cette section montre la logique interne de Claude. Utilisez-la pour identifier
                    les données manquantes, les prompts à améliorer ou les problèmes de contexte.
                  </p>
                </div>

                {/* Claude's Response */}
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">Réponse de Claude:</p>
                  <div className="bg-green-50 p-4 rounded border-l-4 border-green-400 max-h-64 overflow-y-auto">
                    <p className="text-gray-900 whitespace-pre-wrap">{cotResult.response}</p>
                  </div>
                </div>

                {/* Original Response Comparison */}
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">Réponse originale (système):</p>
                  <div className="bg-gray-50 p-4 rounded border border-gray-200 max-h-64 overflow-y-auto">
                    <p className="text-gray-900 whitespace-pre-wrap">{cotResult.original_response}</p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(cotResult.thinking);
                      alert("Raisonnement copié dans le presse-papiers !");
                    }}
                    className="px-4 py-2 border border-purple-300 text-purple-700 text-sm rounded hover:bg-purple-50"
                  >
                    📋 Copier le raisonnement
                  </button>
                  <button
                    onClick={() => setCotResult(null)}
                    className="px-4 py-2 bg-gray-600 text-white text-sm rounded hover:bg-gray-700"
                  >
                    Fermer
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CoT Error Toast */}
      {cotError && (
        <div className="fixed bottom-4 right-4 bg-red-100 border-2 border-red-400 text-red-800 px-6 py-4 rounded-lg shadow-lg z-50 max-w-md">
          <div className="flex items-start space-x-3">
            <span className="text-2xl">⚠️</span>
            <div className="flex-1">
              <p className="font-bold">Erreur d'analyse CoT</p>
              <p className="text-sm mt-1">{cotError}</p>
            </div>
            <button
              onClick={() => setCotError(null)}
              className="text-red-600 hover:text-red-800"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
