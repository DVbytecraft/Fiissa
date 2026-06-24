"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { Mail } from "lucide-react";
import { toast } from "sonner";

import { authApi } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");

  const mutation = useMutation({
    mutationFn: () => authApi.forgotPassword(email.trim()),
    onSuccess: () => {
      toast.success("Si le compte existe, un email a ete envoye");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || "Impossible d'envoyer l'email");
    },
  });

  return (
    <div className="min-h-screen flex items-center justify-center px-5" style={{ background: "var(--bg-app)" }}>
      <div className="w-full max-w-md rounded-3xl p-6 shadow-lg" style={{ background: "var(--bg-card)" }}>
        <h1 className="text-2xl font-black mb-2" style={{ color: "var(--tx-head)" }}>Mot de passe oublie</h1>
        <p className="text-sm mb-5" style={{ color: "var(--tx-muted)" }}>
          Saisissez votre email pour recevoir un lien de reinitialisation.
        </p>
        <div className="relative mb-4">
          <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: "var(--tx-muted)" }} />
          <input
            type="email"
            placeholder="vous@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input-mobile pl-11"
          />
        </div>
        <button
          onClick={() => mutation.mutate()}
          disabled={!email.trim() || mutation.isPending}
          className="btn-primary"
        >
          {mutation.isPending ? "Envoi..." : "Envoyer le lien"}
        </button>
        <Link href="/login" className="block text-center mt-4 text-sm font-semibold" style={{ color: "var(--p-500)" }}>
          Retour a la connexion
        </Link>
      </div>
    </div>
  );
}
