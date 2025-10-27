/**
 * Route
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
import { type NextRequest, NextResponse } from "next/server";
import { secureLog } from "@/lib/utils/secureLogger";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const PROMETHEUS_INTERNAL_URL =
  process.env.PROMETHEUS_INTERNAL_URL ?? "http://intelia-prometheus:9090";

/**
 * API Route pour requêter Prometheus directement
 * Endpoint: /api/prometheus/query?query=YOUR_PROMQL_QUERY
 */
export async function GET(req: NextRequest) {
  try {
    const searchParams = req.nextUrl.searchParams;
    const query = searchParams.get("query");

    if (!query) {
      return NextResponse.json(
        { error: "Missing 'query' parameter" },
        { status: 400 }
      );
    }

    const prometheusUrl = `${PROMETHEUS_INTERNAL_URL}/api/v1/query?query=${encodeURIComponent(query)}`;

    secureLog.log(`[prometheus-query] Querying: ${query}`);

    const response = await fetch(prometheusUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      secureLog.error(
        `[prometheus-query] Error: ${response.status} ${response.statusText}`
      );
      return NextResponse.json(
        {
          error: "Prometheus query failed",
          status: response.status,
          statusText: response.statusText,
        },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json(data, {
      status: 200,
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
      },
    });
  } catch (error) {
    secureLog.error(`[prometheus-query] Exception: ${error}`);
    return NextResponse.json(
      {
        error: "Failed to query Prometheus",
        detail: String(error),
      },
      { status: 502 }
    );
  }
}
