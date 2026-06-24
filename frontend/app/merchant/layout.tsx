"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard, ShoppingBag, CreditCard, Package,
  BarChart2, Settings, LogOut, Receipt, Users, Heart,
  Puzzle, Star, HelpCircle, X, Menu, Bell, ChevronRight,
} from "lucide-react";
import { useAuthStore } from "@/lib/store";

const PRIMARY_NAV = [
  { href: "/merchant/dashboard",  icon: LayoutDashboard, label: "Dashboard"  },
  { href: "/merchant/orders",     icon: ShoppingBag,     label: "Commandes"  },
  { href: "/merchant/payments",   icon: CreditCard,      label: "Paiements"  },
  { href: "/merchant/products",   icon: Package,         label: "Produits"   },
];

const SECONDARY_NAV = [
  { href: "/merchant/reports",       icon: BarChart2,   label: "Rapports"      },
  { href: "/merchant/notifications", icon: Bell,        label: "Notifications" },
  { href: "/merchant/receipts",      icon: Receipt,     label: "Reçus"         },
  { href: "/merchant/customers",     icon: Users,       label: "Clients"       },
  { href: "/merchant/loyalty",       icon: Heart,       label: "Fidélité",     v2: true },
  { href: "/merchant/employees",     icon: Users,       label: "Équipe"        },
  { href: "/merchant/integrations",  icon: Puzzle,      label: "Intégrations"  },
  { href: "/merchant/subscription",  icon: Star,        label: "Abonnement"    },
  { href: "/merchant/support",       icon: HelpCircle,  label: "Support"       },
  { href: "/merchant/settings",      icon: Settings,    label: "Paramètres"    },
];

const ALL_MOBILE_NAV   = PRIMARY_NAV;
const ALL_DRAWER_NAV   = SECONDARY_NAV;

function SidebarLink({ href, icon: Icon, label, pathname, v2 }: { href: string; icon: any; label: string; pathname: string; v2?: boolean }) {
  const active = pathname.startsWith(href);
  return (
    <Link
      href={href}
      className="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all text-sm font-medium"
      style={
        active
          ? { background: "var(--p-50)", color: "var(--p-600)" }
          : { color: "var(--tx-muted)" }
      }
    >
      <Icon size={17} strokeWidth={active ? 2.5 : 1.8} />
      <span>{label}</span>
      {v2 && !active && (
        <span
          className="ml-auto text-[9px] font-black px-1.5 py-0.5 rounded-full"
          style={{ background: "rgba(245,158,11,0.12)", color: "#D97706" }}
        >
          V2
        </span>
      )}
      {active && <div className="ml-auto w-1.5 h-1.5 rounded-full" style={{ background: "var(--p-500)" }} />}
    </Link>
  );
}

export default function MerchantLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router   = useRouter();
  const { logout } = useAuthStore();
  const [showMore, setShowMore] = useState(false);

  const isMoreActive = ALL_DRAWER_NAV.some((item) => pathname.startsWith(item.href));

  const handleLogout = () => {
    logout();
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("company_id");
    document.cookie = "fiissa-session=; path=/; max-age=0";
    router.push("/login");
  };

  return (
    <div className="min-h-screen flex" style={{ background: "var(--bg-app)" }}>

      {/* ── Sidebar desktop ───────────────────────────────────────────── */}
      <aside
        className="hidden md:flex md:flex-col md:fixed md:inset-y-0 md:left-0 md:w-60 z-30"
        style={{ background: "var(--bg-card)", borderRight: "1px solid var(--bd)" }}
      >
        {/* Logo + badge */}
        <div
          className="flex items-center gap-3 px-5 h-16"
          style={{ borderBottom: "1px solid var(--bd)" }}
        >
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: "var(--fiissa-gradient)" }}
          >
            <span className="text-white font-black text-base">F</span>
          </div>
          <div className="min-w-0">
            <p className="font-black text-sm leading-none" style={{ color: "var(--tx-head)" }}>Fiissa</p>
            <span
              className="mt-1 inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full"
              style={{ background: "var(--p-50)", color: "var(--p-600)" }}
            >
              Pro
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
          <p className="px-3 mb-2 text-[10px] font-black uppercase tracking-[0.18em]" style={{ color: "var(--tx-muted)" }}>
            Principal
          </p>
          {PRIMARY_NAV.map((item) => (
            <SidebarLink key={item.href} {...item} pathname={pathname} />
          ))}

          <div className="my-4 mx-3" style={{ borderTop: "1px solid var(--bd)" }} />

          <p className="px-3 mb-2 text-[10px] font-black uppercase tracking-[0.18em]" style={{ color: "var(--tx-muted)" }}>
            Gestion
          </p>
          {SECONDARY_NAV.map((item) => (
            <SidebarLink key={item.href} {...item} pathname={pathname} v2={item.v2} />
          ))}
        </nav>

        {/* Logout */}
        <div className="p-4" style={{ borderTop: "1px solid var(--bd)" }}>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors text-sm font-medium"
            style={{ color: "var(--tx-muted)" }}
          >
            <LogOut size={17} strokeWidth={1.8} />
            <span>Déconnexion</span>
          </button>
        </div>
      </aside>

      {/* ── Zone principale ───────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 md:pl-60">

        {/* Header mobile uniquement */}
        <header
          className="md:hidden sticky top-0 z-40 flex items-center justify-between px-5 py-3"
          style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
        >
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center"
              style={{ background: "var(--fiissa-gradient)" }}
            >
              <span className="text-white font-black text-sm">F</span>
            </div>
            <div>
              <span className="font-black text-base" style={{ color: "var(--tx-head)" }}>Fiissa</span>
              <span
                className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full"
                style={{ background: "var(--p-50)", color: "var(--p-600)" }}
              >
                Pro
              </span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="p-2 rounded-xl"
            style={{ color: "var(--tx-muted)" }}
          >
            <LogOut size={18} />
          </button>
        </header>

        {/* Contenu */}
        <main className="flex-1 pb-24 md:pb-0">{children}</main>

        {/* Drawer "Plus" — mobile uniquement */}
        {showMore && (
          <>
            <div
              className="md:hidden fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
              onClick={() => setShowMore(false)}
            />
            <div
              className="md:hidden fixed bottom-[4.5rem] left-0 right-0 z-50 rounded-t-3xl p-5"
              style={{ background: "var(--bg-card)", boxShadow: "0 -8px 32px rgba(0,0,0,0.12)" }}
            >
              <div className="flex items-center justify-between mb-4">
                <span className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>Navigation</span>
                <button
                  onClick={() => setShowMore(false)}
                  className="w-8 h-8 flex items-center justify-center rounded-full"
                  style={{ background: "var(--n-100)", color: "var(--tx-muted)" }}
                >
                  <X size={16} />
                </button>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {ALL_DRAWER_NAV.map(({ href, icon: Icon, label, v2 }) => {
                  const active = pathname.startsWith(href);
                  return (
                    <Link
                      key={href}
                      href={href}
                      onClick={() => setShowMore(false)}
                      className="relative flex flex-col items-center gap-1.5 py-3 px-2 rounded-2xl transition-colors"
                      style={{
                        background: active ? "var(--p-50)" : "var(--bg-app)",
                        color:      active ? "var(--p-600)" : "var(--tx-muted)",
                      }}
                    >
                      <Icon size={22} strokeWidth={active ? 2.5 : 1.8} />
                      <span className="text-[10px] font-semibold text-center leading-tight">{label}</span>
                      {v2 && !active && (
                        <span
                          className="absolute top-1.5 right-1.5 text-[8px] font-black px-1 py-0.5 rounded-full"
                          style={{ background: "rgba(245,158,11,0.15)", color: "#D97706" }}
                        >
                          V2
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
          </>
        )}

        {/* Bottom nav mobile */}
        <nav className="md:hidden bottom-nav">
          {ALL_MOBILE_NAV.map(({ href, icon: Icon, label }) => {
            const active = pathname.startsWith(href);
            return (
              <Link key={href} href={href} className={`nav-item ${active ? "active" : ""}`}>
                <Icon size={21} strokeWidth={active ? 2.5 : 1.8} />
                <span className="text-[10px]">{label}</span>
              </Link>
            );
          })}
          <button
            onClick={() => setShowMore((v) => !v)}
            className={`nav-item ${isMoreActive || showMore ? "active" : ""}`}
          >
            <Menu size={21} strokeWidth={isMoreActive || showMore ? 2.5 : 1.8} />
            <span className="text-[10px]">Plus</span>
          </button>
        </nav>
      </div>
    </div>
  );
}
