import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PREFIXES = ["/superadmin", "/merchant", "/security"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isProtected = PROTECTED_PREFIXES.some((prefix) =>
    pathname.startsWith(prefix)
  );
  if (!isProtected) return NextResponse.next();

  // Le cookie fiissa-session est posé côté client lors de la connexion.
  // En l'absence de ce cookie, on redirige vers /login avec le retour URL.
  const session = request.cookies.get("fiissa-session");
  if (!session?.value) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/superadmin/:path*", "/merchant/:path*", "/security/:path*"],
};
