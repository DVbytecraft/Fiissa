"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle, Download, Home, Shield,
  ShoppingBag, Share2,
} from "lucide-react";
import { receiptsApi } from "@/lib/api";
import QRCode from "qrcode";

export default function PaymentSuccessPage() {
  const { orderId }    = useParams<{ orderId: string }>();
  const searchParams   = useSearchParams();
  const router         = useRouter();
  const canvasRef      = useRef<HTMLCanvasElement>(null);
  const [qrReady, setQrReady] = useState(false);

  /* ── Reçu lié à la commande ── */
  const { data: receipt, isLoading } = useQuery({
    queryKey: ["receipt-by-order", orderId],
    queryFn: () => receiptsApi.getByOrder(orderId).then((r) => r.data),
    enabled: !!orderId,
    retry: 5,
    retryDelay: 2000,
  });

  /* ── Génération QR code ── */
  useEffect(() => {
    if (!canvasRef.current) return;

    const payload = receipt?.verification_code
      || receipt?.receipt_number
      || `ORDER:${orderId}`;

    QRCode.toCanvas(canvasRef.current, payload, {
      width:           240,
      margin:          2,
      color: { dark: "#111111", light: "#FFFFFF" },
      errorCorrectionLevel: "M",
    })
      .then(() => setQrReady(true))
      .catch(() => {});
  }, [receipt, orderId]);

  /* ── Partager / télécharger le QR ── */
  const handleShare = async () => {
    if (!canvasRef.current) return;
    canvasRef.current.toBlob(async (blob) => {
      if (!blob) return;
      const file = new File([blob], "qr-sortie-fiissa.png", { type: "image/png" });
      if (navigator.share && navigator.canShare({ files: [file] })) {
        await navigator.share({ title: "Mon QR de sortie Fiissa", files: [file] });
      } else {
        const url = URL.createObjectURL(blob);
        const a   = document.createElement("a");
        a.href    = url;
        a.download = "qr-sortie-fiissa.png";
        a.click();
        URL.revokeObjectURL(url);
      }
    });
  };

  const totalXof = receipt?.total_xof;
  const storeName = receipt?.store_name ?? "Fiissa";

  return (
    <div style={{ background: "#FFFFFF", minHeight: "100vh" }}>

      {/* ─── Zone succès ─── */}
      <div
        className="px-6 pt-16 pb-8 flex flex-col items-center text-center"
        style={{ background: "#FFFFFF" }}
      >
        {/* Checkmark animé */}
        <div className="relative mb-6">
          <div
            className="w-24 h-24 rounded-full flex items-center justify-center"
            style={{ background: "var(--s-50)" }}
          >
            <CheckCircle
              size={52}
              style={{ color: "var(--s-500)" }}
              className="animate-fade-in"
            />
          </div>
          {/* Cercle de pulse au succès */}
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background: "var(--s-200)",
              opacity: 0.4,
              animation: "ping 1s ease-in-out 1 forwards",
            }}
          />
        </div>

        <h1 className="text-3xl font-black leading-tight" style={{ color: "#111111" }}>
          Paiement validé !
        </h1>

        {totalXof && (
          <p className="text-2xl font-black mt-2" style={{ color: "var(--s-600)" }}>
            {totalXof.toLocaleString("fr-FR")} FCFA
          </p>
        )}

        <p className="text-sm mt-1" style={{ color: "var(--tx-muted)" }}>
          {storeName} · {receipt?.order_number ?? `Commande ${orderId.slice(0, 8)}`}
        </p>
      </div>

      {/* ─── Séparateur ─── */}
      <div className="mx-6" style={{ height: 1, background: "var(--bd)" }} />

      {/* ─── Zone QR code ─── */}
      <div className="px-6 py-8 flex flex-col items-center">

        <div
          className="flex items-center gap-2 mb-5 px-4 py-2 rounded-full text-sm font-bold"
          style={{ background: "rgba(255,159,0,0.10)", color: "var(--color-action)" }}
        >
          <Shield size={14} />
          Présente ce code à l'agent de sécurité
        </div>

        {/* Canvas QR */}
        <div
          className="rounded-3xl p-5 flex items-center justify-center"
          style={{
            background: "#FFFFFF",
            border: "2px solid var(--bd)",
            boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
          }}
        >
          {isLoading && (
            <div
              className="w-[240px] h-[240px] rounded-xl flex items-center justify-center"
              style={{ background: "var(--n-50)" }}
            >
              <div className="w-8 h-8 rounded-full border-3 border-t-transparent animate-spin"
                style={{ borderColor: "var(--n-300) transparent transparent transparent", borderWidth: 3 }} />
            </div>
          )}
          <canvas
            ref={canvasRef}
            className="rounded-xl"
            style={{ display: qrReady ? "block" : "none" }}
          />
        </div>

        {receipt?.receipt_number && (
          <p className="mt-4 font-mono text-xs tracking-widest" style={{ color: "var(--tx-muted)" }}>
            {receipt.receipt_number}
          </p>
        )}

        {/* Instructions sortie */}
        <div className="w-full mt-6 rounded-2xl overflow-hidden" style={{ background: "var(--n-50)", border: "1px solid var(--bd)" }}>
          {[
            { step: "1", text: "Place ton sac entier sur la balance à la sortie" },
            { step: "2", text: "Montre ce QR code à l'agent de sécurité" },
            { step: "3", text: "L'agent vérifie le poids et valide ta sortie" },
          ].map(({ step, text }) => (
            <div
              key={step}
              className="flex items-center gap-3 px-4 py-3"
              style={{ borderBottom: step !== "3" ? "1px solid var(--bd)" : "none" }}
            >
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-black flex-shrink-0 text-white"
                style={{ background: "#111111" }}
              >
                {step}
              </div>
              <p className="text-sm" style={{ color: "var(--tx-body)" }}>{text}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ─── Actions ─── */}
      <div className="px-6 pb-10 space-y-3">
        {/* Partager / télécharger QR */}
        <button
          onClick={handleShare}
          className="w-full flex items-center justify-center gap-2 py-4 rounded-2xl font-bold transition-all active:scale-95"
          style={{ background: "var(--n-100)", color: "#111111" }}
        >
          <Share2 size={18} />
          Sauvegarder le QR code
        </button>

        {/* Télécharger reçu */}
        {receipt?.id && (
          <button
            onClick={() => window.open(`/api/v1/receipts/${receipt.id}/html`, "_blank")}
            className="w-full flex items-center justify-center gap-2 py-4 rounded-2xl font-bold transition-all active:scale-95"
            style={{ background: "var(--n-100)", color: "#111111" }}
          >
            <Download size={18} />
            Télécharger mon reçu
          </button>
        )}

        {/* Retour accueil */}
        <button
          onClick={() => router.push("/")}
          className="w-full flex items-center justify-center gap-2 py-4 rounded-2xl font-black text-white transition-all active:scale-95"
          style={{ background: "#111111" }}
        >
          <Home size={18} />
          Retour à l'accueil
        </button>
      </div>
    </div>
  );
}
