"use client";

import { useRouter } from "next/navigation";
import { LogOut, ShieldCheck } from "lucide-react";
import { useAuthStore } from "@/lib/store";

export default function SecurityLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    router.push("/login");
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-dark)" }}>
      <header className="flex items-center justify-between px-5 pt-12 pb-4">
        <div className="flex items-center gap-2">
          <ShieldCheck size={22} className="text-white" />
          <span className="text-white font-bold text-lg">Agent Sécurité</span>
          <span className="text-white/40 text-sm">· Fiissa</span>
        </div>
        <button onClick={handleLogout} className="text-white/50 p-2">
          <LogOut size={18} />
        </button>
      </header>
      {children}
    </div>
  );
}
