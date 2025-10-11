/**
 * Service API pour le monitoring de qualité Q&A
 */

import type {
  ProblematicQAResponse,
  QualityStats,
  AnalyzeBatchResponse,
  ReviewQARequest,
  ReviewQAResponse,
} from "../../types/qa-quality";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "https://api.expert.intelia.com";

/**
 * Récupère les Q&A problématiques avec filtres et pagination
 */
export async function getProblematicQA(params: {
  page?: number;
  limit?: number;
  category?: string;
  reviewed?: boolean;
  min_score?: number;
  max_score?: number;
  token: string;
}): Promise<ProblematicQAResponse> {
  const queryParams = new URLSearchParams();

  if (params.page) queryParams.append("page", params.page.toString());
  if (params.limit) queryParams.append("limit", params.limit.toString());
  if (params.category) queryParams.append("category", params.category);
  if (params.reviewed !== undefined) queryParams.append("reviewed", params.reviewed.toString());
  if (params.min_score !== undefined) queryParams.append("min_score", params.min_score.toString());
  if (params.max_score !== undefined) queryParams.append("max_score", params.max_score.toString());

  const response = await fetch(
    `${API_BASE_URL}/api/v1/qa-quality/problematic?${queryParams.toString()}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${params.token}`,
      },
      credentials: "include",
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Lance une analyse batch de Q&A
 */
export async function analyzeBatch(params: {
  limit?: number;
  force_recheck?: boolean;
  token: string;
}): Promise<AnalyzeBatchResponse> {
  const queryParams = new URLSearchParams();

  if (params.limit) queryParams.append("limit", params.limit.toString());
  if (params.force_recheck) queryParams.append("force_recheck", "true");

  const response = await fetch(
    `${API_BASE_URL}/api/v1/qa-quality/analyze-batch?${queryParams.toString()}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${params.token}`,
      },
      credentials: "include",
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Marque une Q&A comme reviewée ou faux positif
 */
export async function reviewQA(params: {
  checkId: string;
  data: ReviewQARequest;
  token: string;
}): Promise<ReviewQAResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/qa-quality/${params.checkId}/review`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${params.token}`,
      },
      credentials: "include",
      body: JSON.stringify(params.data),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Récupère les statistiques de qualité Q&A
 */
export async function getQualityStats(params: {
  days?: number;
  token: string;
}): Promise<QualityStats> {
  const queryParams = new URLSearchParams();

  if (params.days) queryParams.append("days", params.days.toString());

  const response = await fetch(
    `${API_BASE_URL}/api/v1/qa-quality/stats?${queryParams.toString()}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${params.token}`,
      },
      credentials: "include",
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}
