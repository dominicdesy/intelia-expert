// middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { createMiddlewareClient } from "@supabase/auth-helpers-nextjs";

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();
  const supabase = createMiddlewareClient({ req, res });
  // Rafraîchit la session si nécessaire — aucune redirection ici
  await supabase.auth.getSession();
  return res;
}

// N'agit que sur /chat (et sous-routes)
export const config = {
  matcher: ["/chat/:path*"],
};
