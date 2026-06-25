"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Package, Receipt, ScanLine, User } from "lucide-react";
import { useCartStore } from "@/lib/store";

const NAV = [
  { href: "/",        icon: Home,    label: "Accueil"   },
  { href: "/orders",  icon: Package, label: "Commandes" },
  { href: "/scan",    icon: ScanLine, label: "Scan & Go", accent: true },
  { href: "/receipts",icon: Receipt, label: "Reçus"     },
  { href: "/account", icon: User,    label: "Compte"    },
];

export default function CustomerLayout({ children }: { children: React.ReactNode }) {
  const pathname  = usePathname();
  const itemCount = useCartStore((s) => s.itemCount());

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-app)" }}>

      {/* ─── Header glassmorphism ─── */}
      <header
        className="sticky top-0 z-40 flex items-center justify-between px-5"
        style={{
          height: 56,
          background: "rgba(255,255,255,0.92)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--bd)",
        }}
      >
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center"
            style={{ background: "var(--fiissa-gradient)" }}
          >
            <span className="text-white font-semibold text-sm">F</span>
          </div>
          <span className="font-semibold text-lg tracking-tight" style={{ color: "var(--tx-head)" }}>
            Fiissa
          </span>
        </Link>

        {/* Panier — pilule arrondie */}
        <Link
          href="/cart"
          className="relative flex items-center gap-1.5 px-4 rounded-full text-sm font-semibold text-white transition-all active:scale-95"
          style={{
            height: 34,
            background: "var(--p-500)",
            boxShadow: "0 4px 12px rgba(34,87,255,0.28)",
          }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>
          </svg>
          Panier
          {itemCount > 0 && (
            <span
              className="absolute -top-1.5 -right-1.5 min-w-[20px] h-5 px-1 rounded-full flex items-center justify-center text-[10px] font-semibold text-white"
              style={{ background: "#111111" }}
            >
              {itemCount > 9 ? "9+" : itemCount}
            </span>
          )}
        </Link>
      </header>

      {/* ─── Contenu ─── */}
      <main className="pb-nav">{children}</main>

      {/* ─── Bottom navigation ─── */}
      <nav className="bottom-nav">
        {NAV.map(({ href, icon: Icon, label, accent }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);

          /* Bouton Scan & Go — Jaune Ambré, toujours visible */
          if (accent) {
            return (
              <Link key={href} href={href} className="nav-item">
                <div
                  className="flex items-center justify-center rounded-2xl transition-all active:scale-90"
                  style={{
                    width: 48, height: 48,
                    marginTop: -18,
                    background: "var(--p-500)",
                    boxShadow: "0 6px 18px rgba(34,87,255,0.32)",
                  }}
                >
                  <Icon size={22} strokeWidth={2.5} className="text-white" />
                </div>
                <span
                  className="text-[10px] mt-0.5 font-bold"
                  style={{ color: active ? "var(--p-500)" : "var(--tx-muted)" }}
                >
                  {label}
                </span>
              </Link>
            );
          }

          return (
            <Link
              key={href}
              href={href}
              className={`nav-item ${active ? "active" : ""}`}
            >
              <Icon size={22} strokeWidth={active ? 2.5 : 1.8} />
              <span className={active ? "font-bold" : "font-medium"}>{label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
