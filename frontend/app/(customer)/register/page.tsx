"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import {
  ChevronLeft, Lock, Mail, Phone, User, Building2, Store,
  Stethoscope, ShoppingCart, Pill, UtensilsCrossed, ArrowRight,
} from "lucide-react";
import { toast } from "sonner";

import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

type AccountType = "customer" | "company";
type Step = "type" | "info" | "otp";

const COMPANY_TYPES = [
  { value: "pharmacy",     label: "Pharmacie",       icon: Pill },
  { value: "supermarket",  label: "Supermarché",     icon: ShoppingCart },
  { value: "restaurant",   label: "Restaurant",      icon: UtensilsCrossed },
  { value: "clinic",       label: "Clinique / Lab",  icon: Stethoscope },
  { value: "retail",       label: "Commerce retail", icon: Store },
  { value: "other",        label: "Autre",           icon: Building2 },
];

export default function RegisterPage() {
  const router = useRouter();
  const { setUser } = useAuthStore();

  const [accountType, setAccountType] = useState<AccountType>("customer");
  const [step, setStep]               = useState<Step>("type");

  const [firstName,    setFirstName]    = useState("");
  const [lastName,     setLastName]     = useState("");
  const [email,        setEmail]        = useState("");
  const [phone,        setPhone]        = useState("");
  const [password,     setPassword]     = useState("");
  const [companyName,  setCompanyName]  = useState("");
  const [companyType,  setCompanyType]  = useState("");
  const [otp,          setOtp]          = useState("");

  const registerMutation = useMutation({
    mutationFn: () =>
      authApi.register({
        phone: phone.trim(),
        email: email.trim(),
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        account_type: accountType,
        ...(accountType === "company" && {
          company_name: companyName.trim(),
          company_type: companyType,
        }),
      }),
    onSuccess: () => {
      toast.success("Code de vérification envoyé par email");
      setStep("otp");
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.message || "Erreur lors de l'inscription");
    },
  });

  const verifyMutation = useMutation({
    mutationFn: () => authApi.verifyOTP(email.trim(), otp),
    onSuccess: (response) => {
      const { access_token, refresh_token, user } = response.data;
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);
      if (user.company_id) {
        localStorage.setItem("company_id", user.company_id);
        document.cookie = "fiissa-session=1; path=/; SameSite=Strict; max-age=2592000";
      }
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
      if (user.role === "company_owner") {
        router.push("/merchant/dashboard");
      } else {
        router.push("/");
      }
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.message || "Code incorrect");
      setOtp("");
    },
  });

  const canSubmit = Boolean(
    firstName.trim() && lastName.trim() && email.trim() && phone.trim() && password.length >= 8 &&
    (accountType === "customer" || (companyName.trim() && companyType))
  );

  const goBack = () => {
    if (step === "otp")  { setStep("info"); setOtp(""); return; }
    if (step === "info")  { setStep("type"); return; }
    router.back();
  };

  return (
    <div className="flex min-h-screen flex-col" style={{ background: "var(--bg-app)" }}>
      {/* Header */}
      <div className="px-5 pt-12 pb-4 flex items-center gap-4" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <button onClick={goBack} style={{ color: "var(--tx-muted)" }}>
          <ChevronLeft size={26} />
        </button>
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center text-white font-semibold"
            style={{ background: "var(--fiissa-gradient)" }}
          >
            F
          </div>
          <span className="font-semibold text-lg" style={{ color: "var(--tx-head)" }}>Fiissa</span>
        </div>
        {/* Étapes */}
        <div className="ml-auto flex items-center gap-1.5">
          {(["type", "info", "otp"] as Step[]).map((s, idx) => (
            <div
              key={s}
              className="rounded-full transition-all"
              style={{
                width: step === s ? 20 : 6,
                height: 6,
                background: step === s ? "var(--p-500)" : (["type","info","otp"].indexOf(step) > idx ? "var(--p-500)" : "var(--bd)"),
                opacity: step === s ? 1 : (["type","info","otp"].indexOf(step) > idx ? 0.4 : 0.4),
              }}
            />
          ))}
        </div>
      </div>

      <div className="flex-1 px-5 py-6 space-y-5">

        {/* ── ÉTAPE 1 : Choisir le type de compte ── */}
        {step === "type" && (
          <>
            <div>
              <h1 className="text-2xl font-semibold" style={{ color: "var(--tx-head)" }}>
                Créer un compte
              </h1>
              <p className="mt-1 text-sm" style={{ color: "var(--tx-muted)" }}>
                Quel type de compte souhaitez-vous ouvrir ?
              </p>
            </div>

            <div className="space-y-3">
              {/* Client */}
              <button
                onClick={() => setAccountType("customer")}
                className="w-full rounded-2xl p-5 text-left transition-all"
                style={{
                  background: accountType === "customer" ? "rgba(34,87,255,0.05)" : "var(--bg-card)",
                  border: `2px solid ${accountType === "customer" ? "var(--p-500)" : "var(--bd)"}`,
                }}
              >
                <div className="flex items-center gap-4">
                  <div
                    className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
                    style={{ background: accountType === "customer" ? "var(--p-500)" : "var(--bg-app)" }}
                  >
                    <User size={22} style={{ color: accountType === "customer" ? "#fff" : "var(--tx-muted)" }} />
                  </div>
                  <div>
                    <p className="font-semibold text-base" style={{ color: "var(--tx-head)" }}>
                      Compte Client
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                      Achetez, scannez, suivez vos commandes et reçus
                    </p>
                  </div>
                  <div
                    className="ml-auto w-5 h-5 rounded-full shrink-0 border-2 flex items-center justify-center"
                    style={{
                      borderColor: accountType === "customer" ? "var(--p-500)" : "var(--bd)",
                      background: accountType === "customer" ? "var(--p-500)" : "transparent",
                    }}
                  >
                    {accountType === "customer" && <span className="text-white text-[10px] font-semibold">✓</span>}
                  </div>
                </div>
              </button>

              {/* Entreprise */}
              <button
                onClick={() => setAccountType("company")}
                className="w-full rounded-2xl p-5 text-left transition-all"
                style={{
                  background: accountType === "company" ? "rgba(0,214,143,0.05)" : "var(--bg-card)",
                  border: `2px solid ${accountType === "company" ? "var(--s-500)" : "var(--bd)"}`,
                }}
              >
                <div className="flex items-center gap-4">
                  <div
                    className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
                    style={{ background: accountType === "company" ? "var(--s-500)" : "var(--bg-app)" }}
                  >
                    <Building2 size={22} style={{ color: accountType === "company" ? "#fff" : "var(--tx-muted)" }} />
                  </div>
                  <div>
                    <p className="font-semibold text-base" style={{ color: "var(--tx-head)" }}>
                      Compte Entreprise
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--tx-muted)" }}>
                      Pharmacie, supermarché, boutique — gérez vos ventes avec Fiissa
                    </p>
                  </div>
                  <div
                    className="ml-auto w-5 h-5 rounded-full shrink-0 border-2 flex items-center justify-center"
                    style={{
                      borderColor: accountType === "company" ? "var(--s-500)" : "var(--bd)",
                      background: accountType === "company" ? "var(--s-500)" : "transparent",
                    }}
                  >
                    {accountType === "company" && <span className="text-white text-[10px] font-semibold">✓</span>}
                  </div>
                </div>
              </button>
            </div>

            {accountType === "company" && (
              <div className="rounded-2xl p-4" style={{ background: "rgba(0,214,143,0.06)", border: "1px solid rgba(0,214,143,0.15)" }}>
                <p className="text-sm font-semibold" style={{ color: "var(--s-600)" }}>
                  Votre demande sera examinée par l'équipe Fiissa sous 24h.
                  Vous recevrez vos accès complets par email.
                </p>
              </div>
            )}

            <button
              onClick={() => setStep("info")}
              className="btn-primary"
            >
              Continuer <ArrowRight size={18} />
            </button>

            <p className="text-center text-sm" style={{ color: "var(--tx-muted)" }}>
              Déjà un compte ?{" "}
              <Link href="/login" className="font-semibold" style={{ color: "var(--p-500)" }}>
                Se connecter
              </Link>
            </p>
          </>
        )}

        {/* ── ÉTAPE 2 : Informations personnelles + entreprise ── */}
        {step === "info" && (
          <>
            <div>
              <h1 className="text-2xl font-semibold" style={{ color: "var(--tx-head)" }}>
                {accountType === "customer" ? "Vos informations" : "Informations de l'entreprise"}
              </h1>
              <p className="mt-1 text-sm" style={{ color: "var(--tx-muted)" }}>
                {accountType === "customer"
                  ? "Ces informations resteront confidentielles."
                  : "Le responsable du compte entreprise."}
              </p>
            </div>

            {/* Champs entreprise */}
            {accountType === "company" && (
              <>
                <div>
                  <label className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--tx-muted)" }}>
                    Nom de l'entreprise *
                  </label>
                  <div className="relative">
                    <Building2 size={18} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: "var(--tx-muted)" }} />
                    <input
                      type="text"
                      placeholder="Pharmacie du Plateau, Carrefour Dakar..."
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      className="input-mobile pl-11"
                      autoFocus
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--tx-muted)" }}>
                    Type d'activité *
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {COMPANY_TYPES.map(({ value, label, icon: Icon }) => {
                      const selected = companyType === value;
                      return (
                        <button
                          key={value}
                          onClick={() => setCompanyType(value)}
                          className="rounded-xl px-3 py-3 flex items-center gap-2 text-left transition-all"
                          style={{
                            background: selected ? "rgba(0,214,143,0.08)" : "var(--bg-card)",
                            border: `2px solid ${selected ? "var(--s-500)" : "var(--bd)"}`,
                          }}
                        >
                          <Icon size={16} style={{ color: selected ? "var(--s-500)" : "var(--tx-muted)" }} />
                          <span className="text-xs font-bold" style={{ color: selected ? "var(--s-600)" : "var(--tx-body)" }}>
                            {label}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div
                  className="h-px w-full"
                  style={{ background: "var(--bd)" }}
                />
                <p className="text-xs font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--tx-muted)" }}>
                  Responsable du compte
                </p>
              </>
            )}

            {/* Champs communs */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-xs font-semibold" style={{ color: "var(--tx-body)" }}>Prénom</label>
                <input
                  type="text"
                  placeholder={accountType === "company" ? "Oumar" : "Fatou"}
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="input-mobile"
                  autoFocus={accountType === "customer"}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold" style={{ color: "var(--tx-body)" }}>Nom</label>
                <input
                  type="text"
                  placeholder={accountType === "company" ? "Diallo" : "Diallo"}
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="input-mobile"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold" style={{ color: "var(--tx-body)" }}>Email</label>
              <div className="relative">
                <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: "var(--tx-muted)" }} />
                <input
                  type="email"
                  placeholder="vous@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-mobile pl-11"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold" style={{ color: "var(--tx-body)" }}>Téléphone</label>
              <div className="relative">
                <Phone size={18} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: "var(--tx-muted)" }} />
                <input
                  type="tel"
                  placeholder="+221 77 123 45 67"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="input-mobile pl-11"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold" style={{ color: "var(--tx-body)" }}>Mot de passe</label>
              <div className="relative">
                <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: "var(--tx-muted)" }} />
                <input
                  type="password"
                  placeholder="Au moins 8 caractères"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-mobile pl-11"
                />
              </div>
              {password.length > 0 && password.length < 8 && (
                <p className="mt-1 text-xs" style={{ color: "#DC2626" }}>8 caractères minimum</p>
              )}
            </div>

            <button
              onClick={() => registerMutation.mutate()}
              disabled={!canSubmit || registerMutation.isPending}
              className="btn-primary"
            >
              {registerMutation.isPending ? (
                <><span className="spinner border-white border-t-transparent" /> Envoi...</>
              ) : (
                <>{accountType === "company" ? "Soumettre la demande" : "Créer mon compte"} <ArrowRight size={18} /></>
              )}
            </button>
          </>
        )}

        {/* ── ÉTAPE 3 : Vérification OTP ── */}
        {step === "otp" && (
          <>
            <div>
              <h1 className="text-2xl font-semibold" style={{ color: "var(--tx-head)" }}>
                Vérifiez votre email
              </h1>
              <p className="mt-2 text-sm leading-6" style={{ color: "var(--tx-muted)" }}>
                Un code à 6 chiffres a été envoyé à <strong style={{ color: "var(--tx-head)" }}>{email}</strong>
              </p>
            </div>

            <div
              className="rounded-2xl p-4 flex items-center gap-4"
              style={{ background: "rgba(34,87,255,0.05)", border: "1px solid rgba(34,87,255,0.12)" }}
            >
              <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: "var(--p-500)" }}>
                <Mail size={18} className="text-white" />
              </div>
              <p className="text-sm font-semibold" style={{ color: "var(--p-500)" }}>
                Vérifiez votre boîte de réception et vos spams.
              </p>
            </div>

            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--tx-muted)" }}>
                Code à 6 chiffres
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
              onClick={() => verifyMutation.mutate()}
              disabled={otp.length !== 6 || verifyMutation.isPending}
              className="btn-primary"
            >
              {verifyMutation.isPending ? (
                <><span className="spinner border-white border-t-transparent" /> Vérification...</>
              ) : (
                "Valider et créer mon compte"
              )}
            </button>

            <button
              onClick={() => { setOtp(""); setStep("info"); }}
              className="w-full py-3 text-center text-sm font-semibold"
              style={{ color: "var(--tx-muted)" }}
            >
              Modifier mes informations
            </button>
          </>
        )}
      </div>

      <div className="px-5 pb-10 text-center">
        <p className="text-xs" style={{ color: "var(--tx-muted)" }}>
          En créant un compte vous acceptez les{" "}
          <span className="underline" style={{ color: "var(--p-500)" }}>Conditions d'utilisation</span>{" "}
          de Fiissa.
        </p>
      </div>
    </div>
  );
}
