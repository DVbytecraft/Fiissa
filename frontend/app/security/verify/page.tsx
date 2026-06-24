"use client";

import { useState, useEffect } from "react";
import { CheckCircle, XCircle, AlertCircle, Wifi } from "lucide-react";
import { receiptsApi } from "@/lib/api";

type VerifyStatus = "idle" | "loading" | "valid" | "invalid" | "already_used" | "error";

const STATUS_CONFIG: Record<string, { bg: string; icon: any; title: string }> = {
  valid: { bg: "var(--s-500)", icon: CheckCircle, title: "✓ REÇU VALIDE" },
  already_used: { bg: "#F97316", icon: AlertCircle, title: "⚠ DÉJÀ UTILISÉ" },
  invalid: { bg: "#EF4444", icon: XCircle, title: "✗ REÇU INVALIDE" },
  error: { bg: "#6B7280", icon: Wifi, title: "Connexion impossible" },
  loading: { bg: "var(--p-500)", icon: AlertCircle, title: "Vérification..." },
  idle: { bg: "#1C2540", icon: CheckCircle, title: "Prêt à vérifier" },
};

export default function SecurityVerifyPage() {
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<VerifyStatus>("idle");
  const [receiptData, setReceiptData] = useState<any>(null);

  const verifyCode = async (verificationCode: string) => {
    if (!verificationCode.trim()) return;
    setStatus("loading");
    setReceiptData(null);

    try {
      const res = await receiptsApi.verify(verificationCode.trim());
      const data = res.data;
      setStatus(data.valid ? "valid" : "invalid");
      setReceiptData(data);
    } catch (err: any) {
      if (err.code === "ERR_NETWORK" || err.code === "ECONNABORTED") {
        setStatus("error");
      } else if (err.response?.status === 404) {
        setStatus("invalid");
        setReceiptData({ valid: false });
      } else {
        setStatus("error");
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    verifyCode(code);
  };

  const handleReset = () => {
    setCode("");
    setStatus("idle");
    setReceiptData(null);
  };

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const codeFromUrl = urlParams.get("code");
    if (codeFromUrl) {
      setCode(codeFromUrl);
      verifyCode(codeFromUrl);
    }
  }, []);

  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  const bgColor = status !== "idle" ? config.bg : "#1C2540";

  return (
    <div
      className="min-h-screen transition-colors duration-500"
      style={{ background: bgColor }}
    >
      {/* Header */}
      <div className="px-6 pt-10 pb-6">
        <h1 className="text-white text-2xl font-black">Contrôle Sortie</h1>
        <p className="text-white/60 text-sm mt-1">Agent Sécurité · Fiissa</p>
      </div>

      {/* Résultat */}
      {status !== "idle" && status !== "loading" && (
        <div className="mx-4 rounded-3xl p-8 text-center mb-6" style={{ background: "rgba(0,0,0,0.20)" }}>
          <Icon size={80} className="mx-auto text-white mb-4" />
          <h2 className="text-white text-3xl font-black tracking-wide">{config.title}</h2>

          {receiptData && (
            <div className="mt-6 text-left rounded-2xl p-4 space-y-2" style={{ background: "rgba(255,255,255,0.15)" }}>
              {receiptData.receipt_number && (
                <div className="flex justify-between">
                  <span className="text-white/70 text-sm">N° Reçu</span>
                  <span className="font-bold text-white text-sm">{receiptData.receipt_number}</span>
                </div>
              )}
              {receiptData.order_number && (
                <div className="flex justify-between">
                  <span className="text-white/70 text-sm">Commande</span>
                  <span className="font-bold text-white text-sm">{receiptData.order_number}</span>
                </div>
              )}
              {receiptData.amount_xof && (
                <div className="flex justify-between">
                  <span className="text-white/70 text-sm">Montant</span>
                  <span className="font-bold text-white text-sm">{receiptData.amount_xof?.toLocaleString("fr-FR")} FCFA</span>
                </div>
              )}
              {receiptData.items_count && (
                <div className="flex justify-between">
                  <span className="text-white/70 text-sm">Articles</span>
                  <span className="font-bold text-white text-sm">{receiptData.items_count} article{receiptData.items_count > 1 ? "s" : ""}</span>
                </div>
              )}
              {receiptData.message && (
                <p className="text-white/90 text-sm mt-2 text-center font-medium">{receiptData.message}</p>
              )}
            </div>
          )}

          <button
            onClick={handleReset}
            className="mt-6 w-full py-4 bg-white rounded-2xl font-black text-lg active:scale-95 transition-transform"
            style={{ color: "#1C2540" }}
          >
            Vérifier un autre reçu
          </button>
        </div>
      )}

      {/* Formulaire idle */}
      {status === "idle" && (
        <div className="mx-4">
          <div className="rounded-3xl p-6" style={{ background: "rgba(255,255,255,0.08)" }}>
            <p className="text-white text-center mb-6 text-base">
              Entrez le code du reçu ou scannez le QR code
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="Code de vérification"
                className="w-full py-5 px-4 text-xl text-center font-mono bg-white rounded-2xl outline-none tracking-widest"
                style={{ color: "#1C2540", border: "2px solid transparent" }}
                autoFocus
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="characters"
              />
              <button
                type="submit"
                disabled={!code.trim()}
                className="w-full py-5 bg-white rounded-2xl font-black text-xl disabled:opacity-40 active:scale-95 transition-transform"
                style={{ color: "#1C2540" }}
              >
                VÉRIFIER
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Loading */}
      {status === "loading" && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-16 h-16 border-4 rounded-full animate-spin" style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "white" }} />
          <p className="text-white mt-4 text-lg font-semibold">Vérification en cours...</p>
        </div>
      )}

      {/* Légende */}
      <div className="fixed bottom-8 left-4 right-4">
        <div className="rounded-2xl p-3 grid grid-cols-2 gap-2 text-xs text-white/70" style={{ background: "rgba(0,0,0,0.30)" }}>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full" style={{ background: "var(--s-500)" }} />Valide</div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-red-400" />Invalide</div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-orange-400" />Déjà utilisé</div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-gray-400" />Hors ligne</div>
        </div>
      </div>
    </div>
  );
}
