"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, ShoppingBag, Receipt, User, QrCode } from "lucide-react";

const NAV = [
  { href: "/",         icon: Home,       label: "Accueil"   },
  { href: "/orders",   icon: ShoppingBag, label: "Commandes" },
  { href: "/scan",     icon: QrCode,      label: "Scanner",  accent: true },
  { href: "/receipts", icon: Receipt,     label: "Reçus"     },
  { href: "/account",  icon: User,        label: "Compte"    },
];

export default function CustomerLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-app)" }}>
      {/* Header */}
      <header
        className="sticky top-0 z-40 flex items-center justify-between px-5 py-3"
        style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
      >
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center"
            style={{ background: "var(--fiissa-gradient)" }}
          >
            <span className="text-white font-black text-sm">F</span>
          </div>
          <span className="font-black text-lg" style={{ color: "var(--tx-head)" }}>
            Fiissa
          </span>
        </div>
        <Link
          href="/cart"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-semibold transition-colors"
          style={{ background: "var(--p-50)", color: "var(--p-600)" }}
        >
          <ShoppingBag size={15} />
          Panier
        </Link>
      </header>

      {/* Contenu page */}
      <main className="pb-nav">{children}</main>

      {/* Bottom navigation */}
      <nav className="bottom-nav">
        {NAV.map(({ href, icon: Icon, label, accent }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);

          if (accent) {
            return (
              <Link key={href} href={href} className="nav-item relative" style={{ color: active ? "var(--p-500)" : "var(--tx-muted)" }}>
                <div
                  className="-mt-4 w-12 h-12 rounded-2xl flex items-center justify-center shadow-md transition-transform active:scale-95"
                  style={{ background: active ? "var(--p-500)" : "var(--bg-dark)" }}
                >
                  <Icon size={22} strokeWidth={2} className="text-white" />
                </div>
                <span className="text-[10px] mt-1">{label}</span>
              </Link>
            );
          }

          return (
            <Link key={href} href={href} className={`nav-item ${active ? "active" : ""}`}>
              <Icon size={22} strokeWidth={active ? 2.5 : 1.8} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
