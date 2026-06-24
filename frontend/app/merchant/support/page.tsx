"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle, ChevronRight, Clock, MessageSquare, Plus, Send, X } from "lucide-react";
import { supportApi } from "@/lib/api";
import { toast } from "sonner";

const STATUS_CONFIG: Record<string, { label: string; bg: string; color: string; icon: JSX.Element }> = {
  open: {
    label: "Ouvert",
    bg: "rgba(34,87,255,0.08)",
    color: "var(--p-500)",
    icon: <AlertCircle size={14} />,
  },
  in_progress: {
    label: "En cours",
    bg: "rgba(245,158,11,0.08)",
    color: "#F59E0B",
    icon: <Clock size={14} />,
  },
  waiting_customer: {
    label: "En attente client",
    bg: "rgba(110,122,138,0.08)",
    color: "var(--tx-muted)",
    icon: <Clock size={14} />,
  },
  resolved: {
    label: "Resolu",
    bg: "rgba(0,214,143,0.1)",
    color: "var(--s-500)",
    icon: <CheckCircle size={14} />,
  },
  closed: {
    label: "Ferme",
    bg: "rgba(110,122,138,0.06)",
    color: "var(--tx-muted)",
    icon: <CheckCircle size={14} />,
  },
};

const PRIORITIES = [
  { value: "low", label: "Basse" },
  { value: "medium", label: "Normale" },
  { value: "high", label: "Haute" },
  { value: "urgent", label: "Urgente" },
];

function NewTicketModal({ onClose }: { onClose: () => void }) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [priority, setPriority] = useState("medium");
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: () =>
      supportApi.createTicket({
        subject,
        body,
        priority,
        company_id: typeof window !== "undefined" ? localStorage.getItem("company_id") : null,
      }),
    onSuccess: () => {
      toast.success("Ticket cree");
      queryClient.invalidateQueries({ queryKey: ["merchant-support-tickets"] });
      onClose();
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || "Erreur creation ticket"),
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end">
      <div style={{ background: "var(--bg-card)" }} className="rounded-t-3xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 style={{ color: "var(--tx-head)" }} className="text-lg font-bold">
            Nouveau ticket
          </h3>
          <button onClick={onClose} style={{ color: "var(--tx-muted)" }}>
            <X size={20} />
          </button>
        </div>

        <div>
          <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
            Sujet
          </label>
          <input value={subject} onChange={(e) => setSubject(e.target.value)} className="input-mobile" />
        </div>

        <div>
          <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
            Priorite
          </label>
          <select value={priority} onChange={(e) => setPriority(e.target.value)} className="input-mobile">
            {PRIORITIES.map((priorityItem) => (
              <option key={priorityItem.value} value={priorityItem.value}>
                {priorityItem.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ color: "var(--tx-muted)" }} className="text-xs font-semibold mb-1.5 block">
            Description
          </label>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={5}
            style={{ borderColor: "var(--bd)", color: "var(--tx-head)" }}
            className="w-full p-3 border rounded-xl text-sm resize-none outline-none"
          />
        </div>

        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 py-3 rounded-xl font-semibold" style={{ background: "var(--bg-app)", color: "var(--tx-muted)" }}>
            Annuler
          </button>
          <button
            onClick={() => createMutation.mutate()}
            disabled={!subject.trim() || !body.trim() || createMutation.isPending}
            style={{ background: "var(--p-500)", boxShadow: "var(--sh-brand)" }}
            className="flex-1 py-3 text-white rounded-xl font-bold disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Send size={16} />
            {createMutation.isPending ? "Envoi..." : "Envoyer"}
          </button>
        </div>
      </div>
    </div>
  );
}

function TicketDetail({ ticket, onClose }: { ticket: any; onClose: () => void }) {
  const [message, setMessage] = useState("");
  const queryClient = useQueryClient();

  const { data: detail, isLoading } = useQuery({
    queryKey: ["merchant-ticket-detail", ticket.id],
    queryFn: () => supportApi.getTicket(ticket.id).then((response) => response.data),
  });

  const replyMutation = useMutation({
    mutationFn: () => supportApi.replyTicket(ticket.id, { body: message }),
    onSuccess: () => {
      setMessage("");
      queryClient.invalidateQueries({ queryKey: ["merchant-ticket-detail", ticket.id] });
      queryClient.invalidateQueries({ queryKey: ["merchant-support-tickets"] });
      toast.success("Reponse envoyee");
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || "Erreur envoi message"),
  });

  const closeMutation = useMutation({
    mutationFn: () => supportApi.updateTicket(ticket.id, { status: "closed" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["merchant-support-tickets"] });
      queryClient.invalidateQueries({ queryKey: ["merchant-ticket-detail", ticket.id] });
      toast.success("Ticket ferme");
      onClose();
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || "Erreur fermeture ticket"),
  });

  const currentStatus = detail?.status || ticket.status;
  const statusInfo = STATUS_CONFIG[currentStatus] || STATUS_CONFIG.open;

  return (
    <div className="fixed inset-0 z-50 flex flex-col" style={{ background: "var(--bg-app)" }}>
      <div style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }} className="px-4 pt-12 pb-4 flex items-start gap-3">
        <button onClick={onClose} style={{ color: "var(--tx-muted)" }} className="mt-0.5 shrink-0">
          <X size={20} />
        </button>
        <div className="flex-1 min-w-0">
          <p style={{ color: "var(--tx-head)" }} className="font-bold text-sm truncate">
            {ticket.subject}
          </p>
          <span style={{ background: statusInfo.bg, color: statusInfo.color }} className="text-xs font-medium px-2 py-0.5 rounded-full flex items-center gap-1 w-fit mt-1">
            {statusInfo.icon}
            {statusInfo.label}
          </span>
        </div>
        {currentStatus !== "closed" && (
          <button onClick={() => closeMutation.mutate()} disabled={closeMutation.isPending} style={{ color: "var(--tx-muted)" }} className="text-xs shrink-0">
            Fermer
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {isLoading ? (
          [...Array(3)].map((_, index) => (
            <div key={index} style={{ background: "var(--bg-card)" }} className="rounded-2xl p-4">
              <div className="skeleton h-12 w-full" />
            </div>
          ))
        ) : (
          detail?.messages?.map((msg: any) => (
            <div key={msg.id} style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }} className="rounded-2xl p-3">
              <p style={{ color: "var(--tx-head)" }} className="text-sm leading-relaxed">
                {msg.body}
              </p>
              <p style={{ color: "var(--tx-muted)" }} className="text-xs mt-2">
                {new Date(msg.created_at).toLocaleString("fr-FR")}
              </p>
            </div>
          ))
        )}
      </div>

      {currentStatus !== "closed" && (
        <div style={{ background: "var(--bg-card)", borderTop: "1px solid var(--bd)" }} className="px-4 py-4 flex gap-3">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Votre reponse..."
            onKeyDown={(e) => e.key === "Enter" && message.trim() && replyMutation.mutate()}
            style={{ background: "var(--bg-app)", color: "var(--tx-head)" }}
            className="flex-1 px-4 py-2.5 rounded-xl text-sm outline-none"
          />
          <button
            onClick={() => replyMutation.mutate()}
            disabled={!message.trim() || replyMutation.isPending}
            style={{ background: "var(--p-500)" }}
            className="p-2.5 rounded-xl text-white disabled:opacity-50"
          >
            <Send size={18} />
          </button>
        </div>
      )}
    </div>
  );
}

export default function MerchantSupportPage() {
  const [showNew, setShowNew] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState<any>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["merchant-support-tickets"],
    queryFn: () => supportApi.getTickets({ mine: false }).then((response) => response.data),
  });

  const tickets = useMemo(() => data?.items || [], [data]);

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-app)" }}>
      <div style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }} className="px-6 pt-12 pb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 style={{ color: "var(--tx-head)" }} className="text-xl font-bold">
              Support marchand
            </h1>
            <p style={{ color: "var(--tx-muted)" }} className="text-sm">
              {tickets.length} ticket{tickets.length > 1 ? "s" : ""}
            </p>
          </div>
          <button onClick={() => setShowNew(true)} style={{ background: "var(--p-500)", boxShadow: "var(--sh-brand)" }} className="flex items-center gap-2 px-4 py-2 text-white rounded-xl text-sm font-semibold">
            <Plus size={16} />
            Nouveau
          </button>
        </div>
      </div>

      <div className="px-4 py-4 space-y-3">
        {isLoading &&
          [...Array(3)].map((_, index) => (
            <div key={index} style={{ background: "var(--bg-card)" }} className="rounded-2xl p-4">
              <div className="skeleton h-16 w-full" />
            </div>
          ))}

        {!isLoading && tickets.length === 0 && (
          <div className="text-center py-16">
            <MessageSquare size={64} style={{ color: "var(--bd)" }} className="mx-auto mb-4" />
            <p style={{ color: "var(--tx-head)" }} className="font-semibold mb-1">
              Aucun ticket
            </p>
            <p style={{ color: "var(--tx-muted)" }} className="text-sm mb-4">
              Creez un ticket si votre equipe a besoin d'assistance.
            </p>
          </div>
        )}

        {tickets.map((ticket: any) => {
          const statusInfo = STATUS_CONFIG[ticket.status] || STATUS_CONFIG.open;
          return (
            <button
              key={ticket.id}
              onClick={() => setSelectedTicket(ticket)}
              style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}
              className="w-full rounded-2xl p-4 text-left"
            >
              <div className="flex items-start gap-3">
                <div style={{ background: statusInfo.bg, color: statusInfo.color }} className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0">
                  {statusInfo.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <p style={{ color: "var(--tx-head)" }} className="font-semibold text-sm truncate">
                    {ticket.subject}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span style={{ background: statusInfo.bg, color: statusInfo.color }} className="text-xs font-medium px-2 py-0.5 rounded-full">
                      {statusInfo.label}
                    </span>
                    <span style={{ color: "var(--tx-muted)" }} className="text-xs">
                      {new Date(ticket.created_at).toLocaleDateString("fr-FR")}
                    </span>
                  </div>
                </div>
                <ChevronRight size={16} style={{ color: "var(--bd)" }} className="shrink-0 mt-1" />
              </div>
            </button>
          );
        })}
      </div>

      {showNew && <NewTicketModal onClose={() => setShowNew(false)} />}
      {selectedTicket && <TicketDetail ticket={selectedTicket} onClose={() => setSelectedTicket(null)} />}
    </div>
  );
}
