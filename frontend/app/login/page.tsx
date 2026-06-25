"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Lock, Mail, ShieldCheck } from "lucide-react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { toast } from "sonner";

type LoginMode = "customer" | "staff";
type CustomerStep = "credentials" | "otp";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-white" />}>
      <LoginPageContent />
    </Suspense>
  );
}

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") || "/";
  const { setUser } = useAuthStore();

  const [mode, setMode] = useState<LoginMode>("customer");
  const [step, setStep] = useState<CustomerStep>("credentials");
  const [otp, setOtp] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const persistSession = (res: any) => {
    const { access_token, refresh_token, user } = res.data;
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    if (user.company_id) {
      localStorage.setItem("company_id", user.company_id);
    } else {
      localStorage.removeItem("company_id");
    }
    document.cookie = "fiissa-session=1; path=/; SameSite=Strict; max-age=2592000";
    setUser({
      id: user.id,
      phone: user.phone,
      email: user.email,
      firstName: user.first_name,
      lastName: user.last_name,
      role: user.role,
      companyId: user.company_id,
    });
    toast.success(`Bienvenue ${user.first_name} !`);
  };

  const requestOTPMutation = useMutation({
    mutationFn: () => authApi.requestOTP(email.trim(), password),
    onSuccess: () => {
      toast.success("Code de connexion envoyé par email");
      setStep("otp");
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Identifiants incorrects"),
  });

  const verifyOTPMutation = useMutation({
    mutationFn: () => authApi.verifyOTP(email.trim(), otp),
    onSuccess: (res) => {
      persistSession(res);
      router.push(redirect);
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.message || "Code incorrect");
      setOtp("");
    },
  });

  const staffLoginMutation = useMutation({
    mutationFn: () => authApi.staffLogin(email.trim(), password),
    onSuccess: (res) => {
      persistSession(res);
      const role = res.data.user.role;
      const roleRedirects: Record<string, string> = {
        super_admin: "/superadmin/companies",
        company_owner: "/merchant/dashboard",
        store_manager: "/merchant/dashboard",
        cashier: "/merchant/payments",
        accountant: "/merchant/reports",
        preparer: "/merchant/orders",
        security_agent: "/security/verify",
        support_agent: "/support",
      };
      router.push(roleRedirects[role] || redirect);
    },
    onError: (e: any) => toast.error(e.response?.data?.message || "Identifiants incorrects"),
  });

  const switchMode = (nextMode: LoginMode) => {
    setMode(nextMode);
    setStep("credentials");
    setOtp("");
  };

  return (
    <div className="min-h-screen flex lg:grid lg:grid-cols-[1fr_1fr]" style={{ background: "#FFFFFF" }}>

      {/* ══════════════════════════════════════════
          GAUCHE — Manifeste Fiissa (desktop only)
      ══════════════════════════════════════════ */}
      <aside
        className="hidden lg:flex flex-col items-center justify-center px-14"
        style={{ background: "#0F172A" }}
      >
        <div className="w-full max-w-sm flex flex-col items-center text-center">

          {/* Logo app icon — fond sombre intégré, flotte sur le panel */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/icons/2.png" alt="Fiissa" style={{ width: 160, height: 160 }} />

          {/* Divider */}
          <div className="mt-10 w-10 h-px" style={{ background: "rgba(255,255,255,0.15)" }} />

          {/* Titre B2B */}
          <h1 className="mt-8 text-xl font-semibold leading-snug" style={{ color: "#FFFFFF" }}>
            Gérez vos flux de vente en toute simplicité.
          </h1>

          {/* Fonctionnalités clés — texte jaune, sans fond */}
          <div className="mt-5 flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
            {["Scan & Go", "Click & Collect", "Contrôle sécurité"].map((f) => (
              <span key={f} className="text-xs font-medium" style={{ color: "#FF9F00" }}>
                {f}
              </span>
            ))}
          </div>
        </div>
      </aside>

      {/* ══════════════════════════════════════════
          DROITE — Formulaire de connexion
      ══════════════════════════════════════════ */}
      <main className="flex flex-col items-center justify-center px-5 py-10 lg:px-12">
        <div className="w-full max-w-sm">

          {/* Logo mobile uniquement */}
          <div className="lg:hidden flex flex-col items-center mb-8">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/icons/2.png" alt="Fiissa" style={{ width: 72, height: 72 }} />
            <p className="mt-3 text-xl font-semibold tracking-tight" style={{ color: "#0F172A" }}>fiissa</p>
            <p className="text-[10px] font-medium tracking-[0.14em] mt-0.5" style={{ color: "#94A3B8" }}>
              Shop faster, live better
            </p>
          </div>

          {/* Étiquette Connexion */}
          <p
            className="text-[10px] font-semibold tracking-[0.20em] uppercase mb-5"
            style={{ color: "#94A3B8" }}
          >
            Connexion
          </p>

          {/* Sélecteur d'espace — style underline minimaliste */}
          <div className="flex gap-6 mb-6" style={{ borderBottom: "1px solid #E2E8F0" }}>
            {(["customer", "staff"] as const).map((m) => (
              <button
                key={m}
                onClick={() => switchMode(m)}
                className="pb-2.5 text-sm font-medium transition-all"
                style={{
                  color: mode === m ? "#0F172A" : "#94A3B8",
                  borderBottom: mode === m ? "2px solid #0F172A" : "2px solid transparent",
                  marginBottom: -1,
                }}
              >
                {m === "customer" ? "Client" : "Employé / Admin"}
              </button>
            ))}
          </div>

          {/* Alerte OTP */}
          {mode === "customer" && step === "otp" && (
            <div
              className="mb-5 flex items-start gap-3 rounded-xl p-3.5"
              style={{ background: "#EFF6FF", border: "1px solid #BFDBFE" }}
            >
              <ShieldCheck size={16} style={{ color: "#2257FF", marginTop: 1, flexShrink: 0 }} />
              <div>
                <p className="text-xs font-semibold" style={{ color: "#1E40AF" }}>Vérification en cours</p>
                <p className="text-xs mt-0.5 leading-5" style={{ color: "#3B82F6" }}>
                  Code envoyé à <strong>{email}</strong>
                </p>
              </div>
            </div>
          )}

          {/* Champs email + mot de passe */}
          <div className="space-y-3">
            {(mode === "staff" || step === "credentials") && (
              <>
                <div>
                  <label className="block text-xs font-medium mb-1.5" style={{ color: "#64748B" }}>
                    Adresse e-mail
                  </label>
                  <div className="relative">
                    <Mail size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: "#94A3B8" }} />
                    <input
                      type="email"
                      placeholder="vous@email.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoFocus
                      className="w-full pl-9 pr-3.5 py-2.5 text-sm rounded-lg outline-none transition-all"
                      style={{
                        border: "1px solid #E2E8F0",
                        color: "#0F172A",
                        background: "#F8FAFC",
                      }}
                      onFocus={(e) => (e.target.style.borderColor = "#2257FF")}
                      onBlur={(e) => (e.target.style.borderColor = "#E2E8F0")}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-medium" style={{ color: "#64748B" }}>
                      Mot de passe
                    </label>
                    <Link href="/forgot-password" className="text-xs font-medium" style={{ color: "#2257FF" }}>
                      Oublié ?
                    </Link>
                  </div>
                  <div className="relative">
                    <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: "#94A3B8" }} />
                    <input
                      type="password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full pl-9 pr-3.5 py-2.5 text-sm rounded-lg outline-none transition-all"
                      style={{
                        border: "1px solid #E2E8F0",
                        color: "#0F172A",
                        background: "#F8FAFC",
                      }}
                      onFocus={(e) => (e.target.style.borderColor = "#2257FF")}
                      onBlur={(e) => (e.target.style.borderColor = "#E2E8F0")}
                    />
                  </div>
                </div>
              </>
            )}

            {/* Mode client — étape OTP */}
            {mode === "customer" && step === "otp" && (
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: "#64748B" }}>
                  Code à 6 chiffres
                </label>
                <input
                  type="tel"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="——————"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                  autoFocus
                  className="w-full py-2.5 text-center rounded-lg outline-none transition-all"
                  style={{
                    letterSpacing: "0.5em",
                    fontSize: "1.5rem",
                    fontWeight: 700,
                    fontFamily: "monospace",
                    border: "1px solid #E2E8F0",
                    color: "#0F172A",
                    background: "#F8FAFC",
                  }}
                  onFocus={(e) => (e.target.style.borderColor = "#2257FF")}
                  onBlur={(e) => (e.target.style.borderColor = "#E2E8F0")}
                />
              </div>
            )}

            {/* ── CTA Bouton ── */}
            {mode === "customer" && step === "credentials" && (
              <button
                onClick={() => requestOTPMutation.mutate()}
                disabled={!email.trim() || password.length < 8 || requestOTPMutation.isPending}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all active:scale-[0.98] disabled:opacity-40 mt-1"
                style={{ background: "#FF9F00", color: "#0F172A" }}
              >
                {requestOTPMutation.isPending ? (
                  <><span className="spinner border-current border-t-transparent" /> Envoi…</>
                ) : (
                  <>Recevoir mon code <ArrowRight size={15} /></>
                )}
              </button>
            )}

            {mode === "customer" && step === "otp" && (
              <>
                <button
                  onClick={() => verifyOTPMutation.mutate()}
                  disabled={otp.length !== 6 || verifyOTPMutation.isPending}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all active:scale-[0.98] disabled:opacity-40 mt-1"
                  style={{ background: "#FF9F00", color: "#0F172A" }}
                >
                  {verifyOTPMutation.isPending ? (
                    <><span className="spinner border-current border-t-transparent" /> Vérification…</>
                  ) : (
                    "Valider le code"
                  )}
                </button>
                <button
                  onClick={() => { setStep("credentials"); setOtp(""); }}
                  className="w-full py-2 text-center text-xs font-medium"
                  style={{ color: "#94A3B8" }}
                >
                  ← Modifier mes identifiants
                </button>
              </>
            )}

            {mode === "staff" && (
              <button
                onClick={() => staffLoginMutation.mutate()}
                disabled={!email.trim() || !password || staffLoginMutation.isPending}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all active:scale-[0.98] disabled:opacity-40 mt-1"
                style={{ background: "#0F172A", color: "#FFFFFF" }}
              >
                {staffLoginMutation.isPending ? (
                  <><span className="spinner border-white border-t-transparent" /> Connexion…</>
                ) : (
                  <>Se connecter <ArrowRight size={15} /></>
                )}
              </button>
            )}
          </div>

          {/* Créer un compte */}
          {mode === "customer" && step === "credentials" && (
            <p className="mt-5 text-center text-xs" style={{ color: "#94A3B8" }}>
              Pas encore de compte ?{" "}
              <Link href="/register" className="font-semibold" style={{ color: "#2257FF" }}>
                Créer un compte
              </Link>
            </p>
          )}

          <p className="mt-8 text-center text-[10px]" style={{ color: "#CBD5E1" }}>
            Fiissa SaaS · Commerce UEMOA
          </p>
        </div>
      </main>
    </div>
  );
}
