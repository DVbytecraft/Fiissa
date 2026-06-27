"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle, ChevronLeft, Download, QrCode, Share2, Sparkles } from "lucide-react";
import QRCode from "qrcode";
import { toast } from "sonner";
import { receiptsApi } from "@/lib/api";

function sanitizeReceiptHtml(html: string): string {
  return html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
    .replace(/\s+on\w+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]*)/gi, "")
    .replace(/href\s*=\s*"javascript:[^"]*"/gi, 'href="#"')
    .replace(/href\s*=\s*'javascript:[^']*'/gi, "href='#'");
}

export default function ReceiptDetailPage() {
  const { receiptId } = useParams<{ receiptId: string }>();
  const router = useRouter();
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);

  const { data: receipt, isLoading } = useQuery({
    queryKey: ["receipt", receiptId],
    queryFn: () => receiptsApi.getOne(receiptId).then((response) => response.data),
  });

  useEffect(() => {
    async function generateQr() {
      if (!receipt?.verification_code || typeof window === "undefined") {
        setQrDataUrl(null);
        return;
      }
      const verificationUrl = `${window.location.origin}/receipts/verify/${receipt.verification_code}`;
      try {
        const dataUrl = await QRCode.toDataURL(verificationUrl, {
          width: 240,
          margin: 1,
          color: { dark: "#111827", light: "#FFFFFF" },
        });
        setQrDataUrl(dataUrl);
      } catch {
        setQrDataUrl(null);
      }
    }

    generateQr();
  }, [receipt]);

  const handleDownloadPDF = async () => {
    if (!receipt?.pdf_url) {
      toast.error("PDF non disponible");
      return;
    }
    try {
      const response = await fetch(receipt.pdf_url);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `recu-${receipt.receipt_number}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Erreur lors du telechargement du PDF");
    }
  };

  const handleShare = async () => {
    if (!receipt || typeof window === "undefined") return;

    const shareData = {
      title: `Recu ${receipt.receipt_number}`,
      text: `Recu de ${receipt.store_name} - ${receipt.total_xof?.toLocaleString("fr-FR")} FCFA`,
      url: `${window.location.origin}/receipts/verify/${receipt.verification_code}`,
    };

    if (navigator.share) {
      await navigator.share(shareData);
    } else {
      await navigator.clipboard.writeText(shareData.url);
      toast.success("Lien copie");
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-app)" }}>
        <div className="spinner border-blue-600 border-t-transparent w-8 h-8" />
      </div>
    );
  }

  if (!receipt) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-6" style={{ background: "var(--bg-app)" }}>
        <p style={{ color: "var(--tx-muted)" }} className="text-center">
          Recu introuvable
        </p>
        <button onClick={() => router.back()} className="mt-4 font-medium" style={{ color: "var(--p-500)" }}>
          Retour
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-app)" }}>
      <div className="px-4 pt-5 pb-6 space-y-4">
        <div className="surface-card px-4 py-4">
          <div className="flex items-center justify-between">
            <button onClick={() => router.back()} style={{ color: "var(--tx-muted)" }}>
              <ChevronLeft size={24} />
            </button>
            <h1 className="font-bold" style={{ color: "var(--tx-head)" }}>
              Recu
            </h1>
            <button onClick={handleShare} style={{ color: "var(--tx-muted)" }}>
              <Share2 size={20} />
            </button>
          </div>
        </div>

        <section className="hero-panel p-6">
          <div className="relative text-center">
            <div className="eyebrow mx-auto w-fit">
              <Sparkles size={14} />
              Recu securise
            </div>
            <CheckCircle size={44} className="mx-auto mt-4 text-white" />
            <p className="mt-4 text-lg font-black">{receipt.receipt_number}</p>
            <p className="mt-1 text-sm text-white/75">{receipt.store_name}</p>
            <p className="mt-4 text-4xl font-black">{receipt.total_xof?.toLocaleString("fr-FR")} FCFA</p>
            <p className="mt-2 text-xs text-white/65">
              {new Date(receipt.created_at).toLocaleDateString("fr-FR", {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </p>
          </div>
        </section>

        {receipt.html_content && (
          <div className="surface-card overflow-hidden">
            <div className="border-b px-4 py-3" style={{ borderColor: "var(--bd)" }}>
              <p className="text-sm font-black" style={{ color: "var(--tx-head)" }}>
                Detail du recu
              </p>
            </div>
            <div
              className="receipt-html p-4"
              dangerouslySetInnerHTML={{ __html: sanitizeReceiptHtml(receipt.html_content) }}
            />
          </div>
        )}

        {receipt.verification_code && (
          <div className="surface-card p-5 text-center">
            <div className="flex items-center justify-center gap-2 mb-3">
              <QrCode size={18} style={{ color: "var(--tx-muted)" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--tx-head)" }}>
                QR de verification
              </p>
            </div>
            <div className="inline-block rounded-2xl p-4" style={{ background: "var(--n-50)" }}>
              {qrDataUrl ? (
                <Image src={qrDataUrl} alt="QR Code verification" width={160} height={160} unoptimized className="w-40 h-40 mx-auto" />
              ) : (
                <div className="w-40 h-40 grid place-items-center text-sm" style={{ color: "var(--tx-muted)" }}>
                  QR indisponible
                </div>
              )}
            </div>
            <p className="mt-3 text-xs" style={{ color: "var(--tx-muted)" }}>
              Code : <span className="font-mono font-bold" style={{ color: "var(--tx-head)" }}>{receipt.verification_code}</span>
            </p>
            <p className="mt-1 text-xs leading-5" style={{ color: "var(--tx-muted)" }}>
              Presentez ce QR code a l&apos;agent de securite a la sortie pour verification rapide.
            </p>
          </div>
        )}

        <div className="space-y-3">
          {receipt.pdf_url && (
            <button onClick={handleDownloadPDF} className="btn-secondary">
              <Download size={20} />
              Telecharger le PDF
            </button>
          )}

          <button onClick={handleShare} className="btn-primary">
            <Share2 size={20} />
            Partager le recu
          </button>
        </div>

        <div className="pb-safe pb-6" />
      </div>
    </div>
  );
}
