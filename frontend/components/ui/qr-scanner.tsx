"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";

interface QrScannerProps {
  onScan: (value: string) => void;
  onClose: () => void;
}

export function QrScanner({ onScan, onClose }: QrScannerProps) {
  const scannerRef = useRef<any>(null);
  const elementId = "fiissa-qr-scanner";

  useEffect(() => {
    let scanner: any = null;
    let stopped = false;

    import("html5-qrcode").then(({ Html5Qrcode }) => {
      if (stopped) return;
      scanner = new Html5Qrcode(elementId);
      scannerRef.current = scanner;
      scanner
        .start(
          { facingMode: "environment" },
          { fps: 10, qrbox: { width: 240, height: 240 } },
          (decodedText: string) => {
            onScan(decodedText);
            scanner.stop().catch(() => {});
          },
          () => {}
        )
        .catch(() => {});
    });

    return () => {
      stopped = true;
      if (scannerRef.current) {
        scannerRef.current
          .stop()
          .catch(() => {})
          .finally(() => {
            try {
              scannerRef.current?.clear();
            } catch (_) {}
          });
      }
    };
  }, [onScan]);

  return (
    <div className="fixed inset-0 z-[100] bg-black flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-safe pt-4 pb-4">
        <p className="text-white font-bold text-base">Scanner une carte</p>
        <button
          onClick={onClose}
          className="w-10 h-10 rounded-full flex items-center justify-center"
          style={{ background: "rgba(255,255,255,0.15)" }}
          aria-label="Fermer le scanner"
        >
          <X size={20} className="text-white" />
        </button>
      </div>

      {/* Zone de scan */}
      <div className="flex-1 flex flex-col items-center justify-center px-4">
        <div
          id={elementId}
          className="w-full max-w-xs rounded-2xl overflow-hidden"
          style={{ background: "#111" }}
        />
        <p className="text-white/60 text-sm mt-4 text-center">
          Pointez la caméra vers le QR code ou le code-barres de la carte
        </p>
      </div>

      {/* Footer */}
      <div className="px-5 pb-safe pb-8 pt-4">
        <button
          onClick={onClose}
          className="w-full py-3.5 rounded-2xl font-bold text-sm"
          style={{ background: "rgba(255,255,255,0.12)", color: "#fff" }}
        >
          Saisie manuelle à la place
        </button>
      </div>
    </div>
  );
}
