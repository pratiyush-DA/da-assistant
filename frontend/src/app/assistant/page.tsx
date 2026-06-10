"use client";

import { useCallback, useEffect, useState } from "react";
import { ManageAccountsModal } from "@/components/accounts/ManageAccountsModal";
import { ChatHistoryPanel } from "@/components/chat/ChatHistoryPanel";
import { ClientSelector } from "@/components/chat/ClientSelector";
import { InputBar } from "@/components/chat/InputBar";
import { Message, MessageThread } from "@/components/chat/MessageThread";
import { DocumentList } from "@/components/documents/DocumentList";
import { UploadZone } from "@/components/documents/UploadZone";
import { useClientContext } from "@/context/ClientContext";
import { useUserContext } from "@/context/UserContext";
import {
  Client,
  Conversation,
  Document,
  createConversation,
  deleteConversation,
  fetchClients,
  fetchConversationMessages,
  fetchConversations,
  fetchDocumentStatus,
  fetchDocuments,
} from "@/lib/api";
import { streamChat } from "@/lib/sse";

export default function AssistantPage() {
  const { clientId, setClientId } = useClientContext();
  const { userId } = useUserContext();
  const [clients, setClients] = useState<Client[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accountsOpen, setAccountsOpen] = useState(false);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);

  const ready = Boolean(clientId && userId);

  const loadClients = useCallback(async () => {
    try {
      const data = await fetchClients();
      setClients(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load clients");
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    if (!clientId) {
      setDocuments([]);
      return;
    }
    try {
      const data = await fetchDocuments(clientId);
      setDocuments(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents");
    }
  }, [clientId]);

  const loadConversations = useCallback(async () => {
    if (!clientId || !userId) {
      setConversations([]);
      return;
    }
    try {
      const data = await fetchConversations(userId, clientId);
      setConversations(data);
    } catch {
      setConversations([]);
    }
  }, [clientId, userId]);

  const loadMessages = useCallback(async (convId: string) => {
    try {
      const history = await fetchConversationMessages(convId);
      setMessages(
        history.map((m) => ({
          role: m.role,
          content: m.content,
          sources: m.sources,
        })),
      );
    } catch {
      setMessages([]);
    }
  }, []);

  useEffect(() => {
    loadClients();
  }, [loadClients]);

  useEffect(() => {
    loadDocuments();
    loadConversations();
  }, [loadDocuments, loadConversations]);

  useEffect(() => {
    setConversationId(null);
    setMessages([]);
    setSelectedDocumentIds([]);
  }, [clientId, userId]);

  useEffect(() => {
    const processing = documents.filter((d) => d.status === "processing");
    if (processing.length === 0) return;

    const interval = setInterval(async () => {
      let changed = false;
      for (const doc of processing) {
        const status = await fetchDocumentStatus(doc.id);
        if (status.status !== "processing") changed = true;
      }
      if (changed) loadDocuments();
    }, 5000);

    return () => clearInterval(interval);
  }, [documents, loadDocuments]);

  const handleNewChat = async () => {
    if (!clientId || !userId) return;
    setError(null);
    try {
      const conv = await createConversation(userId, clientId);
      setConversationId(conv.id);
      setMessages([]);
      setSelectedDocumentIds([]);
      await loadConversations();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start new chat");
    }
  };

  const handleSelectConversation = async (id: string) => {
    setConversationId(id);
    setSelectedDocumentIds([]);
    await loadMessages(id);
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      await deleteConversation(id);
      if (conversationId === id) {
        setConversationId(null);
        setMessages([]);
        setSelectedDocumentIds([]);
      }
      await loadConversations();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete chat");
    }
  };

  const handleSend = async (text: string) => {
    if (!clientId || !userId || selectedDocumentIds.length === 0) return;
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    let assistant = "";
    let activeConvId = conversationId;

    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      await streamChat(clientId, userId, text, {
        onConversationId: (id) => {
          activeConvId = id;
          setConversationId(id);
        },
        onToken: (token) => {
          assistant += token;
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = { role: "assistant", content: assistant };
            return next;
          });
        },
        onDone: (sources, convId) => {
          if (convId) setConversationId(convId);
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = {
              role: "assistant",
              content: assistant,
              sources: sources as Message["sources"],
            };
            return next;
          });
          loadConversations();
        },
        onError: (msg) => setError(msg),
      }, activeConvId, selectedDocumentIds);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-5.5rem)] gap-0 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <ChatHistoryPanel
        conversations={conversations}
        activeId={conversationId}
        disabled={!ready}
        onSelect={handleSelectConversation}
        onNewChat={handleNewChat}
        onDelete={handleDeleteConversation}
      />

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <ClientSelector
          clients={clients}
          value={clientId}
          onChange={(id) => setClientId(id)}
          onManageAccounts={() => setAccountsOpen(true)}
        />
        {error && (
          <p className="bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>
        )}
        <MessageThread messages={messages} loading={loading} />
        <InputBar
          disabled={!ready || loading}
          documents={documents}
          selectedDocumentIds={selectedDocumentIds}
          onSelectionChange={setSelectedDocumentIds}
          onSend={handleSend}
        />
      </div>

      <div
        id="documents"
        className="flex w-[min(100%,300px)] shrink-0 flex-col overflow-hidden border-l border-gray-200 lg:w-[28%] lg:max-w-[320px]"
      >
        <div className="border-b border-gray-200 px-3 py-3">
          <h2 className="text-sm font-semibold text-gray-900">Document Manager</h2>
          <p className="text-xs text-gray-500">Upload and manage client documents</p>
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          <UploadZone clientId={clientId} onUploaded={loadDocuments} />
          <div className="mt-4">
            <DocumentList
              documents={documents}
              clientId={clientId || ""}
              onRefresh={loadDocuments}
            />
          </div>
        </div>
      </div>

      <ManageAccountsModal
        open={accountsOpen}
        onClose={() => {
          setAccountsOpen(false);
          loadClients();
        }}
        initialTab="clients"
      />
    </div>
  );
}
