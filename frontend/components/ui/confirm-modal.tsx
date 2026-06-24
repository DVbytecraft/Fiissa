"use client";

import { useEffect, useRef } from "react";
import { AlertTriangle, X } from "lucide-react";

interface ConfirmModalProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "warning" | "info";
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "Confirmer",
  cancelLabel = "Annuler",
  variant = "danger",
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) confirmRef.current?.focus();
  }, [open]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!open) return;
      if (e.key === "Escape") onCancel();
      if (e.key === "Enter") onConfirm();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel, onConfirm]);

  if (!open) return null;

  const colors = {
    danger:  { icon: "var(--error)",   bg: "var(--error-bg)",   btn: "var(--error)",   btnText: "#fff" },
    warning: { icon: "var(--warning)", bg: "var(--warning-bg)", btn: "var(--warning)", btnText: "#fff" },
    info:    { icon: "var(--p-500)",   bg: "var(--p-50)",       btn: "var(--p-500)",   btnText: "#fff" },
  }[variant];

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm animate-fade-in"
        onClick={onCancel}
      />
      {/* Modal */}
      <div
        className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
      >
        <div
          className="w-full sm:max-w-sm rounded-3xl p-6 animate-slide-up"
          style={{ background: "var(--bg-card)", boxShadow: "var(--sh-lg)" }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Icône */}
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center mb-4"
            style={{ background: colors.bg }}
          >
            <AlertTriangle size={22} style={{ color: colors.icon }} />
          </div>

          {/* Texte */}
          <h2 id="confirm-title" className="font-black text-lg mb-2" style={{ color: "var(--tx-head)" }}>
            {title}
          </h2>
          <p className="text-sm leading-relaxed" style={{ color: "var(--tx-muted)" }}>
            {message}
          </p>

          {/* Actions */}
          <div className="flex gap-3 mt-6">
            <button
              onClick={onCancel}
              className="flex-1 py-3 rounded-2xl font-semibold text-sm transition-opacity active:opacity-70"
              style={{ background: "var(--bg-app)", color: "var(--tx-muted)", border: "1px solid var(--bd)" }}
            >
              {cancelLabel}
            </button>
            <button
              ref={confirmRef}
              onClick={onConfirm}
              className="flex-1 py-3 rounded-2xl font-bold text-sm transition-opacity active:opacity-70"
              style={{ background: colors.btn, color: colors.btnText }}
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
