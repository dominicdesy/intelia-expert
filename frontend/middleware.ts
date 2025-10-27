/**
 * Middleware
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
// middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { createMiddlewareClient } from "@supabase/auth-helpers-nextjs";

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();
  const supabase = createMiddlewareClient({ req, res });
  // Rafraîchit la session si nécessaire — aucune redirection ici
  await supabase.auth.getSession();

  // Add security headers
  res.headers.set('X-Content-Type-Options', 'nosniff');
  res.headers.set('X-Frame-Options', 'DENY');
  res.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');

  return res;
}

// N'agit que sur /chat (et sous-routes)
export const config = {
  matcher: ["/chat/:path*"],
};
