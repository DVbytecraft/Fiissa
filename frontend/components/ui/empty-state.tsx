"use client";

import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div
        className="w-20 h-20 rounded-3xl flex items-center justify-center mb-5"
        style={{ background: "var(--bg-app)", border: "2px dashed var(--bd)" }}
      >
        <Icon size={36} style={{ color: "var(--bd)" }} />
      </div>
      <p className="font-bold text-base" style={{ color: "var(--tx-head)" }}>{title}</p>
      {description && (
        <p className="text-sm mt-2 max-w-xs leading-relaxed" style={{ color: "var(--tx-muted)" }}>
          {description}
        </p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-5 px-6 py-3 rounded-2xl font-bold text-sm text-white"
          style={{ background: "var(--p-500)", boxShadow: "var(--sh-brand)" }}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
