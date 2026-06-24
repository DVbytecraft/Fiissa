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
} from "lucide-react";
import { toast } from "sonner";

export default function AccountPage() {
  const router = useRouter();
  const { user, isAuthenticated, setUser } = useAuthStore();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [preferredLanguage, setPreferredLanguage] = useState("fr");
  const [marketingOptIn, setMarketingOptIn] = useState(false);

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
    onSuccess: () => toast.success("Email de verification envoye"),
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
      if (user) {
        setUser({
          ...user,
          firstName,
          lastName,
        });
      }
      toast.success("Profil mis a jour");
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.detail || error.response?.data?.message || "Erreur mise a jour"),
  });

  const handleLogout = async () => {
    try {
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        await authApi.logout(refreshToken);
      }
    } catch {
      // token deja invalide
    }

    localStorage.clear();
    setUser(null);
    router.push("/login");
    toast.success("Deconnexion reussie");
  };

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-6">
        <div
          className="w-20 h-20 rounded-full flex items-center justify-center mb-4"
          style={{ background: "var(--fiissa-gradient)" }}
        >
          <User size={36} className="text-white" />
        </div>
        <h2 className="text-xl font-bold" style={{ color: "var(--tx-head)" }}>
          Mon compte
        </h2>
        <p className="mt-2 text-center" style={{ color: "var(--tx-muted)" }}>
          Connectez-vous pour acceder a votre compte
        </p>
        <button className="btn-primary mt-6 max-w-xs" onClick={() => router.push("/login")}>
          Se connecter
        </button>
        <button
          className="mt-3 text-sm font-semibold"
          style={{ color: "var(--p-500)" }}
          onClick={() => router.push("/register")}
        >
          Creer un compte gratuit
        </button>
      </div>
    );
  }

  const initials =
    [user?.firstName?.[0], user?.lastName?.[0]].filter(Boolean).join("").toUpperCase() || "?";

  const menuItems = [
    {
      icon: Bell,
      label: "Notifications",
      value:
        notificationSummary?.unread_count > 0
          ? `${notificationSummary.unread_count} non lue${notificationSummary.unread_count > 1 ? "s" : ""}`
          : "Tout est lu",
      href: "/account/notifications",
    },
    { icon: WalletCards, label: "Wallet", value: "Mes moyens de paiement", href: "/account/wallet" },
    { icon: BadgePercent, label: "Fidelite", value: "Mes cartes et points", href: "/account/loyalty" },
    { icon: Tag, label: "Coupons", value: "Mes coupons de reduction", href: "/account/coupons" },
    { icon: Gift, label: "Recompenses", value: "Echanger mes points", href: "/account/rewards" },
    { icon: HelpCircle, label: "Aide & Support", value: "Contacter le support", href: "/support" },
  ];

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      <div className="px-5 pt-6 pb-6 text-center" style={{ background: "var(--fiissa-gradient)" }}>
        <div
          className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-3 font-black text-3xl text-white"
          style={{ background: "rgba(255,255,255,0.2)" }}
        >
          {initials}
        </div>
        <h2 className="text-white font-black text-xl">
          {user?.firstName} {user?.lastName}
        </h2>
        <p className="text-white/70 text-sm mt-1">{user?.phone}</p>
      </div>

      <div className="px-4 py-5 space-y-4">
        <div
          className="rounded-3xl p-5 space-y-4"
          style={{ background: "var(--bg-card)", border: "1px solid var(--bd)", boxShadow: "var(--sh-sm)" }}
        >
          <div className="flex items-center gap-2">
            <PencilLine size={18} style={{ color: "var(--p-500)" }} />
            <h3 className="text-base font-black" style={{ color: "var(--tx-head)" }}>
              Profil
            </h3>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="Prenom" className="input-mobile" />
            <input value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="Nom" className="input-mobile" />
          </div>

          <div className="grid grid-cols-1 gap-3">
            <div className="rounded-2xl px-4 py-3" style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}>
              <div className="flex items-center gap-2">
                <Mail size={16} style={{ color: "var(--p-500)" }} />
                <p className="text-sm font-semibold" style={{ color: "var(--tx-head)" }}>
                  {user?.email || "Aucun email"}
                </p>
              </div>
            </div>
            <div className="rounded-2xl px-4 py-3" style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}>
              <div className="flex items-center gap-2">
                <Phone size={16} style={{ color: "var(--p-500)" }} />
                <p className="text-sm font-semibold" style={{ color: "var(--tx-head)" }}>
                  {user?.phone || "Aucun telephone"}
                </p>
              </div>
            </div>
          </div>

          <select value={preferredLanguage} onChange={(e) => setPreferredLanguage(e.target.value)} className="input-mobile">
            <option value="fr">Francais</option>
            <option value="en">English</option>
          </select>

          <button
            onClick={() => setMarketingOptIn((current) => !current)}
            className="w-full rounded-2xl px-4 py-3 text-left"
            style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
          >
            <p className="text-sm font-semibold" style={{ color: "var(--tx-head)" }}>
              Communications marketing
            </p>
            <p className="text-xs mt-1" style={{ color: "var(--tx-muted)" }}>
              {marketingOptIn ? "Activees" : "Desactivees"}
            </p>
          </button>

          <button
            onClick={() => updateProfileMutation.mutate()}
            disabled={!firstName.trim() || !lastName.trim() || updateProfileMutation.isPending}
            className="btn-primary"
          >
            <Save size={18} />
            {updateProfileMutation.isPending ? "Sauvegarde..." : "Sauvegarder le profil"}
          </button>
        </div>

        {!!user?.email && (
          <button
            onClick={() => requestVerificationMutation.mutate()}
            disabled={requestVerificationMutation.isPending}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl font-bold text-sm"
            style={{
              background: "rgba(34,87,255,0.08)",
              color: "var(--p-500)",
              border: "1px solid rgba(34,87,255,0.15)",
            }}
          >
            <Mail size={16} />
            {requestVerificationMutation.isPending ? "Envoi..." : "Renvoyer l'email de verification"}
          </button>
        )}

        <div
          className="rounded-2xl overflow-hidden"
          style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
        >
          {menuItems.map(({ icon: Icon, label, value, href }, index) => (
            <button
              key={label}
              onClick={() => href && router.push(href)}
              className="w-full flex items-center gap-3 px-4 py-4 text-left active:opacity-70"
              style={{ borderBottom: index < menuItems.length - 1 ? `1px solid var(--bg-app)` : "none" }}
            >
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center"
                style={{ background: "rgba(34,87,255,0.08)" }}
              >
                <Icon size={18} style={{ color: "var(--p-500)" }} />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>
                  {label}
                </p>
                {value && (
                  <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                    {value}
                  </p>
                )}
              </div>
              {href && <ChevronRight size={16} style={{ color: "var(--bd)" }} />}
            </button>
          ))}
        </div>

        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 py-4 rounded-2xl font-bold"
          style={{ background: "#FEF2F2", color: "#DC2626", border: "1px solid #FCA5A5" }}
        >
          <LogOut size={18} />
          Se deconnecter
        </button>

        <p className="text-center text-xs" style={{ color: "var(--tx-muted)" }}>
          Fiissa v1.0 · Commerce UEMOA
        </p>
      </div>
    </div>
  );
}
