"use client";

import { Suspense, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import { api } from "@/lib/api";

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" style={{ background: "var(--bg-app)" }} />}>
      <VerifyEmailContent />
    </Suspense>
  );
}

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const mutation = useMutation({
    mutationFn: () => api.post("/auth/verify-email", { token }),
    onSuccess: () => {
      toast.success("Email verifie avec succes");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || "Verification impossible");
    },
  });

  useEffect(() => {
    if (token) {
      mutation.mutate();
    }
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center px-5" style={{ background: "var(--bg-app)" }}>
      <div className="w-full max-w-md rounded-3xl p-6 shadow-lg text-center" style={{ background: "var(--bg-card)" }}>
        <h1 className="text-2xl font-black mb-2" style={{ color: "var(--tx-head)" }}>Verification email</h1>
        <p className="text-sm mb-5" style={{ color: "var(--tx-muted)" }}>
          {mutation.isPending
            ? "Verification en cours..."
            : mutation.isSuccess
            ? "Votre adresse email a ete confirmee."
            : "Le lien est invalide ou expire."}
        </p>
        <Link href="/login" className="font-semibold" style={{ color: "var(--p-500)" }}>
          Aller a la connexion
        </Link>
      </div>
    </div>
  );
}
