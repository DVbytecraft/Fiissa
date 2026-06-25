"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { authApi, notificationsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import {
  BadgePercent,
  Bell,
  ChevronRight,
  Gift,
  HelpCircle,
  LogOut,
  Mail,
  PencilLine,
  Phone,
  Save,
  Tag,
  User,
  WalletCards,
  Check,
} from "lucide-react";
import { toast } from "sonner";

export default function AccountPage() {
  const router = useRouter();
  const { user, isAuthenticated, setUser } = useAuthStore();
  const [firstName, setFirstName]               = useState("");
  const [lastName, setLastName]                 = useState("");
  const [preferredLanguage, setPreferredLanguage] = useState("fr");
  const [marketingOptIn, setMarketingOptIn]     = useState(false);
  const [editMode, setEditMode]                 = useState(false);

  const { data: notificationSummary } = useQuery({
    queryKey: ["notification-summary"],
    queryFn: () => notificationsApi.getSummary().then((r) => r.data),
    enabled: isAuthenticated,
  });

  useEffect(() => {
    setFirstName(user?.firstName || "");
    setLastName(user?.lastName || "");
  }, [user]);

  const requestVerificationMutation = useMutation({
    mutationFn: () => authApi.requestEmailVerification(),
    onSuccess: () => toast.success("Email de vérification envoyé"),
    onError: (error: any) =>
      toast.error(error.response?.data?.message || "Impossible d'envoyer l'email"),
  });

  const updateProfileMutation = useMutation({
    mutationFn: () =>
      authApi.updateMe({
        first_name: firstName,
        last_name: lastName,
        preferred_language: preferredLanguage,
        marketing_opt_in: marketingOptIn,
      }),
    onSuccess: () => {
      if (user) setUser({ ...user, firstName, lastName });
      setEditMode(false);
      toast.success("Profil mis à jour");
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || error.response?.data?.message || "Erreur"),
  });

  const handleLogout = async () => {
    try {
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) await authApi.logout(refreshToken);
    } catch {}
    localStorage.clear();
    setUser(null);
    router.push("/login");
  };

  /* ── Non connecté ── */
  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-6">
        <div
          className="w-20 h-20 rounded-full flex items-center justify-center mb-5"
          style={{ background: "var(--n-100)" }}
        >
          <User size={36} style={{ color: "var(--n-400)" }} />
        </div>
        <h2 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>
          Mon compte
        </h2>
        <p className="mt-2 text-sm text-center" style={{ color: "var(--tx-muted)" }}>
          Connecte-toi pour accéder à ton compte
        </p>
        <button
          onClick={() => router.push("/login")}
          className="mt-6 flex items-center justify-center gap-2 px-8 py-2.5 rounded-lg text-sm font-semibold text-white active:scale-95 transition-all"
          style={{ background: "#0F172A" }}
        >
          Se connecter
        </button>
        <p className="mt-3 text-xs" style={{ color: "#64748B" }}>
          Pas encore de compte ?{" "}
          <a href="/register" className="font-semibold underline" style={{ color: "var(--p-500)" }}>
            Créer un compte
          </a>
        </p>
      </div>
    );
  }

  const initials =
    [user?.firstName?.[0], user?.lastName?.[0]].filter(Boolean).join("").toUpperCase() || "?";

  const unreadCount = notificationSummary?.unread_count ?? 0;

  const menuSections = [
    {
      title: "Mon activité",
      items: [
        {
          icon: Bell,
          iconBg: "#EEF2FF",
          iconColor: "#4F46E5",
          label: "Notifications",
          value: unreadCount > 0 ? `${unreadCount} non lue${unreadCount > 1 ? "s" : ""}` : "Tout est lu",
          href: "/account/notifications",
        },
        {
          icon: WalletCards,
          iconBg: "#FFF7ED",
          iconColor: "#EA580C",
          label: "Portefeuille",
          value: "Mes moyens de paiement",
          href: "/account/wallet",
        },
      ],
    },
    {
      title: "Avantages",
      items: [
        {
          icon: BadgePercent,
          iconBg: "#F0FDF4",
          iconColor: "#16A34A",
          label: "Fidélité",
          value: "Mes cartes et points",
          href: "/account/loyalty",
        },
        {
          icon: Tag,
          iconBg: "#FEF9C3",
          iconColor: "#CA8A04",
          label: "Coupons",
          value: "Mes réductions",
          href: "/account/coupons",
        },
        {
          icon: Gift,
          iconBg: "#FDF2F8",
          iconColor: "#9333EA",
          label: "Récompenses",
          value: "Échanger mes points",
          href: "/account/rewards",
        },
      ],
    },
    {
      title: "Support",
      items: [
        {
          icon: HelpCircle,
          iconBg: "var(--n-100)",
          iconColor: "var(--tx-muted)",
          label: "Aide & Support",
          value: "Contacter le support",
          href: "/support",
        },
      ],
    },
  ];

  return (
    <div style={{ background: "var(--bg-layout)", minHeight: "100vh" }}>

      {/* ── Hero profil Apple style ── */}
      <div
        className="px-5 pt-8 pb-6"
        style={{ background: "#FFFFFF", borderBottom: "1px solid var(--bd)" }}
      >
        <div className="flex items-center gap-4">
          {/* Avatar initiales */}
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center font-black text-2xl flex-shrink-0"
            style={{ background: "var(--n-100)", color: "var(--tx-head)" }}
          >
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="font-semibold text-lg truncate" style={{ color: "var(--tx-head)" }}>
              {user?.firstName} {user?.lastName}
            </h2>
            <p className="text-sm mt-0.5" style={{ color: "var(--tx-muted)" }}>
              {user?.phone || user?.email || "—"}
            </p>
          </div>
          <button
            onClick={() => setEditMode((v) => !v)}
            className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 transition-colors"
            style={{ background: editMode ? "var(--tx-head)" : "var(--n-100)" }}
          >
            <PencilLine size={16} style={{ color: editMode ? "white" : "var(--tx-muted)" }} />
          </button>
        </div>

        {/* Infos contact */}
        <div className="mt-4 flex gap-3">
          {user?.email && (
            <div className="flex items-center gap-1.5 flex-1 min-w-0">
              <Mail size={13} style={{ color: "var(--tx-muted)" }} />
              <span className="text-xs truncate" style={{ color: "var(--tx-muted)" }}>{user.email}</span>
            </div>
          )}
          {user?.phone && (
            <div className="flex items-center gap-1.5">
              <Phone size={13} style={{ color: "var(--tx-muted)" }} />
              <span className="text-xs" style={{ color: "var(--tx-muted)" }}>{user.phone}</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Formulaire d'édition (collapsed par défaut) ── */}
      {editMode && (
        <div className="px-5 py-4" style={{ background: "#FFFFFF", borderBottom: "1px solid var(--bd)" }}>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="field-label">Prénom</label>
              <input value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="Prénom" className="input-mobile" />
            </div>
            <div>
              <label className="field-label">Nom</label>
              <input value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="Nom" className="input-mobile" />
            </div>
          </div>

          <div className="mb-3">
            <label className="field-label">Langue</label>
            <select value={preferredLanguage} onChange={(e) => setPreferredLanguage(e.target.value)} className="input-mobile">
              <option value="fr">Français</option>
              <option value="en">English</option>
            </select>
          </div>

          <button
            onClick={() => setMarketingOptIn((v) => !v)}
            className="w-full flex items-center justify-between rounded-xl px-4 py-3 mb-4 transition-colors"
            style={{ background: "var(--n-50)", border: "1.5px solid var(--bd)" }}
          >
            <div>
              <p className="text-sm font-semibold text-left" style={{ color: "var(--tx-head)" }}>Communications marketing</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                {marketingOptIn ? "Activées" : "Désactivées"}
              </p>
            </div>
            <div
              className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
              style={{ background: marketingOptIn ? "var(--tx-head)" : "var(--n-200)" }}
            >
              {marketingOptIn && <Check size={12} className="text-white" />}
            </div>
          </button>

          <button
            onClick={() => updateProfileMutation.mutate()}
            disabled={!firstName.trim() || !lastName.trim() || updateProfileMutation.isPending}
            className="btn-primary"
          >
            <Save size={18} />
            {updateProfileMutation.isPending ? "Sauvegarde…" : "Sauvegarder"}
          </button>

          {user?.email && (
            <button
              onClick={() => requestVerificationMutation.mutate()}
              disabled={requestVerificationMutation.isPending}
              className="w-full flex items-center justify-center gap-2 mt-3 py-3 rounded-xl text-sm font-semibold"
              style={{ background: "var(--n-50)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }}
            >
              <Mail size={15} />
              {requestVerificationMutation.isPending ? "Envoi…" : "Renvoyer l'email de vérification"}
            </button>
          )}
        </div>
      )}

      {/* ── Sections menu Apple Settings ── */}
      <div className="px-5 py-5 space-y-6">
        {menuSections.map((section) => (
          <div key={section.title}>
            <p className="section-label px-1 mb-2">{section.title}</p>
            <div className="ios-list">
              {section.items.map(({ icon: Icon, iconBg, iconColor, label, value, href }, index) => (
                <button
                  key={label}
                  onClick={() => href && router.push(href)}
                  className="ios-list-item w-full text-left"
                >
                  <div className="ios-list-icon" style={{ background: iconBg }}>
                    <Icon size={18} style={{ color: iconColor }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>{label}</p>
                    {value && (
                      <p className="text-xs mt-0.5 truncate" style={{ color: "var(--tx-muted)" }}>{value}</p>
                    )}
                  </div>
                  {unreadCount > 0 && label === "Notifications" && (
                    <span
                      className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black text-white mr-2"
                      style={{ background: "var(--color-action)" }}
                    >
                      {unreadCount}
                    </span>
                  )}
                  <ChevronRight size={16} style={{ color: "var(--n-300)" }} />
                </button>
              ))}
            </div>
          </div>
        ))}

        {/* ── Déconnexion ── */}
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-all active:scale-95"
          style={{ background: "#FEF2F2", color: "#DC2626", border: "1px solid #FCA5A5" }}
        >
          <LogOut size={18} />
          Se déconnecter
        </button>

        <p className="text-center text-xs pb-2" style={{ color: "var(--n-400)" }}>
          Fiissa v1.0 · Commerce UEMOA
        </p>
      </div>
    </div>
  );
}
