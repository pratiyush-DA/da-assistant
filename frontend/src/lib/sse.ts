import { API_URL } from "./api";

export type StreamHandlers = {
  onConversationId?: (id: string) => void;
  onToken: (token: string) => void;
  onDone: (sources: unknown[], conversationId?: string) => void;
  onError: (message: string) => void;
};

export async function streamChat(
  clientId: string,
  userId: string,
  message: string,
  handlers: StreamHandlers,
  conversationId?: string | null,
  documentIds?: string[],
): Promise<void> {
  const body: Record<string, unknown> = {
    client_id: clientId,
    user_id: userId,
    message,
  };
  if (conversationId) body.conversation_id = conversationId;
  if (documentIds && documentIds.length > 0) {
    body.document_ids = documentIds;
    if (documentIds.length === 1) {
      body.focus_document_id = documentIds[0];
    }
  }

  const res = await fetch(`${API_URL}/api/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok || !res.body) {
    handlers.onError(await res.text());
    return;
  }

  const headerConv = res.headers.get("X-Conversation-Id");
  if (headerConv) handlers.onConversationId?.(headerConv);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data: ")) continue;
      try {
        const payload = JSON.parse(line.slice(6));
        if (payload.conversation_id && !payload.token && !payload.done) {
          handlers.onConversationId?.(payload.conversation_id);
        }
        if (payload.token) handlers.onToken(payload.token);
        if (payload.error) handlers.onError(payload.error);
        if (payload.done) {
          handlers.onDone(
            payload.sources || [],
            payload.conversation_id || headerConv || undefined,
          );
        }
      } catch {
        /* ignore malformed chunks */
      }
    }
  }
}
