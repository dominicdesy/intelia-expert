/**
 * Service API pour le monitoring de qualité Q&A
 * Utilise apiClient pour une gestion cohérente des requêtes
 */

import { apiClient } from "../api/client";
import type {
  ProblematicQAResponse,
  QualityStats,
  AnalyzeBatchResponse,
  ReviewQARequest,
  ReviewQAResponse,
  CoTAnalysisResponse,
} from "../../types/qa-quality";

/**
 * Récupère les Q&A problématiques avec filtres et pagination
 */
export async function getProblematicQA(params?: {
  page?: number;
  limit?: number;
  category?: string;
  reviewed?: boolean;
  min_score?: number;
  max_score?: number;
}): Promise<ProblematicQAResponse> {
  const queryParams = new URLSearchParams();

  if (params?.page) queryParams.append("page", params.page.toString());
  if (params?.limit) queryParams.append("limit", params.limit.toString());
  if (params?.category) queryParams.append("category", params.category);
  if (params?.reviewed !== undefined) queryParams.append("reviewed", params.reviewed.toString());
  if (params?.min_score !== undefined) queryParams.append("min_score", params.min_score.toString());
  if (params?.max_score !== undefined) queryParams.append("max_score", params.max_score.toString());

  const response = await apiClient.getSecure<ProblematicQAResponse>(
    `qa-quality/problematic?${queryParams.toString()}`
  );

  if (!response.success) {
    throw new Error(response.error?.message || "Error fetching problematic Q&A");
  }

  return response.data!;
}

/**
 * Lance une analyse batch de Q&A
 */
export async function analyzeBatch(params?: {
  limit?: number;
  force_recheck?: boolean;
}): Promise<AnalyzeBatchResponse> {
  const queryParams = new URLSearchParams();

  if (params?.limit) queryParams.append("limit", params.limit.toString());
  if (params?.force_recheck) queryParams.append("force_recheck", "true");

  const response = await apiClient.postSecure<AnalyzeBatchResponse>(
    `qa-quality/analyze-batch?${queryParams.toString()}`
  );

  if (!response.success) {
    throw new Error(response.error?.message || "Error analyzing batch");
  }

  return response.data!;
}

/**
 * Marque une Q&A comme reviewée ou faux positif
 */
export async function reviewQA(params: {
  checkId: string;
  data: ReviewQARequest;
}): Promise<ReviewQAResponse> {
  const response = await apiClient.patchSecure<ReviewQAResponse>(
    `qa-quality/${params.checkId}/review`,
    params.data
  );

  if (!response.success) {
    throw new Error(response.error?.message || "Error reviewing Q&A");
  }

  return response.data!;
}

/**
 * Récupère les statistiques de qualité Q&A
 */
export async function getQualityStats(params?: {
  days?: number;
}): Promise<QualityStats> {
  const queryParams = new URLSearchParams();

  if (params?.days) queryParams.append("days", params.days.toString());

  const response = await apiClient.getSecure<QualityStats>(
    `qa-quality/stats?${queryParams.toString()}`
  );

  if (!response.success) {
    throw new Error(response.error?.message || "Error fetching quality stats");
  }

  return response.data!;
}

/**
 * Analyze QA with Claude Extended Thinking (CoT) for debugging
 * Admin-only feature to understand WHY the system gave a problematic response
 */
export async function analyzeCoT(checkId: number): Promise<CoTAnalysisResponse> {
  const response = await apiClient.postSecure<CoTAnalysisResponse>(
    `qa-quality/analyze-cot/${checkId}`
  );

  if (!response.success) {
    throw new Error(response.error?.message || "Error analyzing with CoT");
  }

  return response.data!;
}

/**
 * Delete a QA quality check permanently
 * Admin-only feature to remove false positives or irrelevant anomalies
 */
export async function deleteQA(checkId: string): Promise<{ id: string; message: string }> {
  const response = await apiClient.deleteSecure<{ id: string; message: string }>(
    `qa-quality/${checkId}`
  );

  if (!response.success) {
    throw new Error(response.error?.message || "Error deleting QA check");
  }

  return response.data!;
}
