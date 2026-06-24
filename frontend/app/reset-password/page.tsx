"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { Lock } from "lucide-react";
import { toast } from "sonner";

import { authApi } from "@/lib/api";

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" style={{ background: "var(--bg-app)" }} />}>
      <ResetPasswordContent />
    </Suspense>
  );
}

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");

  const mutation = useMutation({
    mutationFn: () => authApi.resetPassword(token, password),
    onSuccess: () => {
      toast.success("Mot de passe reinitialise");
      router.push("/login");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || "Lien invalide ou expire");
    },
  });

  return (
    <div className="min-h-screen flex items-center justify-center px-5" style={{ background: "var(--bg-app)" }}>
      <div className="w-full max-w-md rounded-3xl p-6 shadow-lg" style={{ background: "var(--bg-card)" }}>
        <h1 className="text-2xl font-black mb-2" style={{ color: "var(--tx-head)" }}>Nouveau mot de passe</h1>
        <p className="text-sm mb-5" style={{ color: "var(--tx-muted)" }}>
          Choisissez un nouveau mot de passe pour votre compte Fiissa.
        </p>
        <div className="relative mb-4">
          <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: "var(--tx-muted)" }} />
          <input
            type="password"
            placeholder="Au moins 8 caracteres"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-mobile pl-11"
          />
        </div>
        <button
          onClick={() => mutation.mutate()}
          disabled={!token || password.length < 8 || mutation.isPending}
          className="btn-primary"
        >
          {mutation.isPending ? "Mise a jour..." : "Reinitialiser"}
        </button>
        <Link href="/login" className="block text-center mt-4 text-sm font-semibold" style={{ color: "var(--p-500)" }}>
          Retour a la connexion
        </Link>
      </div>
    </div>
  );
}
