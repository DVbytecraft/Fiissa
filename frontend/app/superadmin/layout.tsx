"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Building2, BarChart2, Users, Settings, LogOut, Shield, ChevronRight, CreditCard, Activity } from "lucide-react";
import { useAuthStore } from "@/lib/store";

const NAV = [
  { href: "/superadmin/companies",  icon: Building2,  label: "Entreprises"  },
  { href: "/superadmin/stats",      icon: BarChart2,  label: "Statistiques" },
  { href: "/superadmin/users",      icon: Users,      label: "Utilisateurs" },
  { href: "/superadmin/plans",      icon: CreditCard, label: "Plans"        },
  { href: "/superadmin/audit-logs", icon: Activity,   label: "Audit Logs"   },
  { href: "/superadmin/settings",   icon: Settings,   label: "Paramètres"  },
];

export default function SuperAdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router   = useRouter();
  const { logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    localStorage.clear();
    router.push("/login");
  };

  return (
    <div className="min-h-screen flex" style={{ background: "var(--bg-app)" }}>

      {/* ── Sidebar desktop ──────────────────────────────────────────── */}
      <aside
        className="hidden md:flex md:flex-col md:fixed md:inset-y-0 md:left-0 md:w-56 z-30"
        style={{ background: "var(--bg-dark)", borderRight: "1px solid rgba(255,255,255,0.07)" }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 h-16" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: "var(--fiissa-gradient)" }}
          >
            <span className="text-white font-black text-base">F</span>
          </div>
          <div className="min-w-0">
            <p className="text-white font-black text-sm leading-none">Fiissa</p>
            <span
              className="mt-1 inline-block text-[10px] font-black px-2 py-0.5 rounded-full"
              style={{ background: "#EAB308", color: "#713F12" }}
            >
              Super Admin
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          <p className="px-3 mb-3 text-[10px] font-black uppercase tracking-[0.18em]" style={{ color: "rgba(255,255,255,0.3)" }}>
            Plateforme
          </p>
          {NAV.map(({ href, icon: Icon, label }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all"
                style={
                  active
                    ? { background: "rgba(255,255,255,0.12)", color: "white" }
                    : { color: "rgba(255,255,255,0.55)" }
                }
              >
                <Icon size={18} strokeWidth={active ? 2.5 : 1.8} />
                <span className="text-sm font-semibold">{label}</span>
                {active && <ChevronRight size={14} className="ml-auto opacity-60" />}
              </Link>
            );
          })}
        </nav>

        {/* Logout */}
        <div className="p-4" style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all"
            style={{ color: "rgba(255,255,255,0.45)" }}
          >
            <LogOut size={18} strokeWidth={1.8} />
            <span className="text-sm font-semibold">Déconnexion</span>
          </button>
        </div>
      </aside>

      {/* ── Zone principale ──────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 md:pl-56">

        {/* Header mobile uniquement */}
        <header
          className="md:hidden sticky top-0 z-40 flex items-center justify-between px-5 py-3"
          style={{ background: "var(--bg-dark)", borderBottom: "1px solid rgba(255,255,255,0.08)" }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center"
              style={{ background: "var(--fiissa-gradient)" }}
            >
              <span className="text-white font-black text-sm">F</span>
            </div>
            <div>
              <span className="text-white font-black text-base">Fiissa</span>
              <span
                className="ml-2 text-[10px] font-black px-2 py-0.5 rounded-full"
                style={{ background: "#EAB308", color: "#713F12" }}
              >
                Super Admin
              </span>
            </div>
          </div>
          <button onClick={handleLogout} className="p-2" style={{ color: "rgba(255,255,255,0.5)" }}>
            <LogOut size={18} />
          </button>
        </header>

        {/* Contenu */}
        <main className="flex-1 pb-24 md:pb-0">{children}</main>

        {/* Bottom nav mobile */}
        <nav className="md:hidden bottom-nav">
          {NAV.map(({ href, icon: Icon, label }) => {
            const active = pathname.startsWith(href);
            return (
              <Link key={href} href={href} className={`nav-item ${active ? "active" : ""}`}>
                <Icon size={20} strokeWidth={active ? 2.5 : 1.8} />
                <span className="text-[10px]">{label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
