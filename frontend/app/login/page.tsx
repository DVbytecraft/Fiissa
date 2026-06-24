"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Lock, Mail, ShieldCheck, Sparkles } from "lucide-react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { toast } from "sonner";

type LoginMode = "customer" | "staff";
type CustomerStep = "credentials" | "otp";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" style={{ background: "var(--bg-app)" }} />}>
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
      toast.success("Code de connexion envoye par email");
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
    <div
      className="min-h-screen"
      style={{
        background:
          "radial-gradient(circle at top left, rgba(34,87,255,0.1), transparent 24%), radial-gradient(circle at bottom right, rgba(0,214,143,0.12), transparent 22%), var(--bg-app)",
      }}
    >
      <div className="mx-auto grid min-h-screen max-w-6xl lg:grid-cols-[1.05fr_0.95fr]">
        <section className="relative hidden overflow-hidden px-10 py-12 lg:flex lg:flex-col">
          <div
            className="absolute inset-6 rounded-[40px]"
            style={{
              background: "linear-gradient(145deg, #0D1227 0%, #1333B3 48%, #00AB72 100%)",
              boxShadow: "0 24px 60px rgba(13,18,39,0.18)",
            }}
          />
          <div className="absolute left-24 top-20 h-40 w-40 rounded-full bg-white/10 blur-2xl" />
          <div className="absolute right-16 bottom-16 h-48 w-48 rounded-full bg-white/10 blur-2xl" />

          <div className="relative z-10 flex h-full flex-col justify-between text-white">
            <div>
              <div className="inline-flex h-16 w-16 items-center justify-center rounded-[24px] bg-white/18 text-3xl font-black shadow-lg backdrop-blur">
                F
              </div>
              <div className="mt-8 inline-flex items-center gap-2 rounded-full bg-white/12 px-3 py-1 text-xs font-black uppercase tracking-[0.16em]">
                <Sparkles size={14} />
                Smart commerce
              </div>
              <h1 className="mt-6 max-w-xl text-5xl font-black leading-[1.05]">
                La couche d'identite et d'operations qui donne du style au retail.
              </h1>
              <p className="mt-5 max-w-lg text-base leading-7 text-white/78">
                Fiissa relie clients, equipes terrain, paiement, recus et fidelite dans une experience nette, rapide et rassurante.
              </p>
            </div>

            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "OTP email", value: "Securise" },
                { label: "Paiements", value: "Fluides" },
                { label: "Fidelite", value: "Activee" },
              ].map((item) => (
                <div key={item.label} className="rounded-[24px] bg-white/10 p-4 backdrop-blur-sm">
                  <p className="text-sm font-black">{item.value}</p>
                  <p className="mt-1 text-xs text-white/65">{item.label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="flex items-center justify-center px-5 py-8 lg:px-10">
          <div
            className="w-full max-w-xl rounded-[32px] border p-5 shadow-sm md:p-7"
            style={{ background: "var(--bg-card)", borderColor: "rgba(13,18,39,0.06)" }}
          >
            <div className="lg:hidden">
              <div
                className="mx-auto flex h-16 w-16 items-center justify-center rounded-[24px] text-3xl font-black text-white"
                style={{ background: "var(--fiissa-gradient)" }}
              >
                F
              </div>
              <p className="mt-4 text-center text-xs font-black uppercase tracking-[0.18em]" style={{ color: "var(--p-500)" }}>
                Smart commerce
              </p>
            </div>

            <div className="mt-3 text-center lg:mt-0 lg:text-left">
              <h2 className="text-3xl font-black leading-tight" style={{ color: "var(--tx-head)" }}>
                Connexion Fiissa
              </h2>
              <p className="mt-2 text-sm leading-6" style={{ color: "var(--tx-muted)" }}>
                Choisis ton espace puis connecte-toi avec un parcours clair et protege.
              </p>
            </div>

            <div
              className="mt-6 grid grid-cols-2 gap-2 rounded-[24px] p-1"
              style={{ background: "var(--n-100)" }}
            >
              {(["customer", "staff"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => switchMode(m)}
                  className="rounded-[20px] px-4 py-3 text-sm font-black transition-all"
                  style={
                    mode === m
                      ? { background: "var(--bg-card)", color: "var(--tx-head)", boxShadow: "var(--sh-sm)" }
                      : { background: "transparent", color: "var(--tx-muted)" }
                  }
                >
                  {m === "customer" ? "Client" : "Employe / Admin"}
                </button>
              ))}
            </div>

            {mode === "customer" && step === "otp" && (
              <div
                className="mt-5 rounded-[24px] p-4"
                style={{ background: "rgba(34,87,255,0.06)", border: "1px solid rgba(34,87,255,0.1)" }}
              >
                <div className="flex items-start gap-3">
                  <div
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl"
                    style={{ background: "rgba(34,87,255,0.1)", color: "var(--p-500)" }}
                  >
                    <ShieldCheck size={18} />
                  </div>
                  <div>
                    <p className="text-sm font-black" style={{ color: "var(--tx-head)" }}>
                      Verification en cours
                    </p>
                    <p className="mt-1 text-sm leading-6" style={{ color: "var(--tx-muted)" }}>
                      Un code a 6 chiffres vient d'etre envoye a <strong>{email}</strong>.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="mt-6 space-y-4">
              {(mode === "staff" || step === "credentials") && (
                <>
                  <div>
                    <label className="mb-2 block text-xs font-black uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
                      Email
                    </label>
                    <div className="relative">
                      <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: "var(--tx-muted)" }} />
                      <input
                        type="email"
                        placeholder="vous@email.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="input-mobile pl-11"
                        autoFocus
                      />
                    </div>
                  </div>

                  <div>
                    <label className="mb-2 block text-xs font-black uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
                      Mot de passe
                    </label>
                    <div className="relative">
                      <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: "var(--tx-muted)" }} />
                      <input
                        type="password"
                        placeholder="Entrez votre mot de passe"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="input-mobile pl-11"
                      />
                    </div>
                  </div>
                </>
              )}

              {mode === "customer" && step === "credentials" && (
                <>
                  <button
                    onClick={() => requestOTPMutation.mutate()}
                    disabled={!email.trim() || password.length < 8 || requestOTPMutation.isPending}
                    className="btn-primary"
                  >
                    {requestOTPMutation.isPending ? (
                      <>
                        <span className="spinner border-white border-t-transparent" /> Envoi...
                      </>
                    ) : (
                      <>
                        Recevoir mon code <ArrowRight size={18} />
                      </>
                    )}
                  </button>

                  <div className="flex items-center justify-between gap-3 text-sm">
                    <Link href="/register" className="font-black" style={{ color: "var(--p-500)" }}>
                      Creer un compte
                    </Link>
                    <Link href="/forgot-password" className="font-semibold" style={{ color: "var(--tx-muted)" }}>
                      Mot de passe oublie ?
                    </Link>
                  </div>
                </>
              )}

              {mode === "customer" && step === "otp" && (
                <>
                  <div>
                    <label className="mb-2 block text-xs font-black uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
                      Code a 6 chiffres
                    </label>
                    <input
                      type="tel"
                      inputMode="numeric"
                      maxLength={6}
                      placeholder="------"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                      autoFocus
                      style={{
                        letterSpacing: "0.5em",
                        fontSize: "2rem",
                        fontWeight: 900,
                        textAlign: "center",
                        fontFamily: "monospace",
                      }}
                      className="input-mobile"
                    />
                  </div>
                  <button
                    onClick={() => verifyOTPMutation.mutate()}
                    disabled={otp.length !== 6 || verifyOTPMutation.isPending}
                    className="btn-primary"
                  >
                    {verifyOTPMutation.isPending ? (
                      <>
                        <span className="spinner border-white border-t-transparent" /> Verification...
                      </>
                    ) : (
                      "Valider le code"
                    )}
                  </button>
                  <button
                    onClick={() => {
                      setStep("credentials");
                      setOtp("");
                    }}
                    className="w-full py-3 text-center text-sm font-bold"
                    style={{ color: "var(--p-500)" }}
                  >
                    Modifier mes identifiants
                  </button>
                </>
              )}

              {mode === "staff" && (
                <button
                  onClick={() => staffLoginMutation.mutate()}
                  disabled={!email.trim() || !password || staffLoginMutation.isPending}
                  className="btn-primary"
                >
                  {staffLoginMutation.isPending ? (
                    <>
                      <span className="spinner border-white border-t-transparent" /> Connexion...
                    </>
                  ) : (
                    <>
                      Se connecter <ArrowRight size={18} />
                    </>
                  )}
                </button>
              )}
            </div>

            <p className="mt-6 text-center text-xs" style={{ color: "var(--tx-muted)" }}>
              Fiissa SaaS · Commerce UEMOA
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
