"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, MessageSquare, Plus, Send } from "lucide-react";
import { supportApi } from "@/lib/api";
import { toast } from "sonner";
import Link from "next/link";

export default function SupportPage() {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["customer-support-tickets"],
    queryFn: () => supportApi.getTickets({ mine: true }).then((response) => response.data),
  });

  const { data: detail } = useQuery({
    queryKey: ["customer-support-ticket", selectedId],
    queryFn: () => supportApi.getTicket(selectedId as string).then((response) => response.data),
    enabled: Boolean(selectedId),
  });

  const createMutation = useMutation({
    mutationFn: () => supportApi.createTicket({ subject, body }),
    onSuccess: () => {
      setSubject("");
      setBody("");
      queryClient.invalidateQueries({ queryKey: ["customer-support-tickets"] });
      toast.success("Ticket envoye");
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || "Erreur creation ticket"),
  });

  const replyMutation = useMutation({
    mutationFn: () => supportApi.replyTicket(selectedId as string, { body: reply }),
    onSuccess: () => {
      setReply("");
      queryClient.invalidateQueries({ queryKey: ["customer-support-ticket", selectedId] });
      queryClient.invalidateQueries({ queryKey: ["customer-support-tickets"] });
      toast.success("Reponse envoyee");
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || "Erreur envoi message"),
  });

  const tickets = data?.items || [];

  return (
    <div style={{ background: "var(--bg-app)", minHeight: "100vh" }}>
      <div className="px-5 pt-4 pb-4 flex items-center gap-3" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--bd)" }}>
        <Link href="/account" style={{ color: "var(--tx-muted)" }}>
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-xl font-semibold" style={{ color: "var(--tx-head)" }}>
            Aide & Support
          </h1>
          <p className="text-sm" style={{ color: "var(--tx-muted)" }}>
            Suivi de vos demandes
          </p>
        </div>
      </div>

      <div className="px-4 py-4 space-y-4">
        <div className="rounded-2xl p-4 space-y-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <div className="flex items-center gap-2">
            <Plus size={18} style={{ color: "var(--p-500)" }} />
            <h2 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
              Nouveau ticket
            </h2>
          </div>
          <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Sujet" className="input-mobile" />
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Decrivez votre demande"
            rows={4}
            className="input-mobile min-h-28"
          />
          <button onClick={() => createMutation.mutate()} disabled={!subject.trim() || !body.trim() || createMutation.isPending} className="btn-primary">
            {createMutation.isPending ? "Envoi..." : "Envoyer"}
          </button>
        </div>

        <div className="rounded-2xl p-4 space-y-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
          <h2 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
            Mes tickets
          </h2>

          {isLoading && <div className="skeleton h-24 w-full rounded-2xl" />}

          {!isLoading && tickets.length === 0 && (
            <div className="text-center py-8">
              <MessageSquare size={48} className="mx-auto mb-3" style={{ color: "var(--bd)" }} />
              <p style={{ color: "var(--tx-muted)" }}>Aucun ticket pour le moment</p>
            </div>
          )}

          {tickets.map((ticket: any) => (
            <button
              key={ticket.id}
              onClick={() => setSelectedId(ticket.id)}
              className={`w-full rounded-2xl p-4 text-left ${selectedId === ticket.id ? "ring-2 ring-blue-500" : ""}`}
              style={{ background: "var(--bg-app)", border: "1px solid var(--bd)" }}
            >
              <p className="font-semibold text-sm" style={{ color: "var(--tx-head)" }}>
                {ticket.subject}
              </p>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs" style={{ color: "var(--tx-muted)" }}>
                  {ticket.status}
                </span>
                <span className="text-xs" style={{ color: "var(--tx-muted)" }}>
                  {new Date(ticket.created_at).toLocaleDateString("fr-FR")}
                </span>
              </div>
            </button>
          ))}
        </div>

        {detail && (
          <div className="rounded-2xl p-4 space-y-3" style={{ background: "var(--bg-card)", border: "1px solid var(--bd)" }}>
            <h2 className="font-bold text-sm" style={{ color: "var(--tx-head)" }}>
              Conversation
            </h2>
            <div className="space-y-2">
              {detail.messages?.map((message: any) => (
                <div key={message.id} className="rounded-2xl p-3" style={{ background: "var(--bg-app)" }}>
                  <p className="text-sm" style={{ color: "var(--tx-head)" }}>
                    {message.body}
                  </p>
                  <p className="text-xs mt-2" style={{ color: "var(--tx-muted)" }}>
                    {new Date(message.created_at).toLocaleString("fr-FR")}
                  </p>
                </div>
              ))}
            </div>

            {detail.status !== "closed" && (
              <>
                <textarea
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  placeholder="Votre reponse"
                  rows={3}
                  className="input-mobile min-h-24"
                />
                <button onClick={() => replyMutation.mutate()} disabled={!reply.trim() || replyMutation.isPending} className="btn-primary flex items-center justify-center gap-2">
                  <Send size={16} />
                  {replyMutation.isPending ? "Envoi..." : "Repondre"}
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
