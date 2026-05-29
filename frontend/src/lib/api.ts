const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Client = {
  id: string;
  name: string;
  slug: string;
  created_at: string;
};

export type User = {
  id: string;
  email: string;
  display_name: string;
  external_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type Conversation = {
  id: string;
  user_id: string;
  client_id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type Document = {
  id: string;
  filename: string;
  file_type: string;
  file_size_bytes: number | null;
  status: "processing" | "ready" | "error";
  error_message: string | null;
  uploaded_at: string;
  updated_at: string;
  chunk_count: number;
};

export type DocumentStatus = {
  status: string;
  error_message: string | null;
  chunk_count: number;
};

export type PlatformStats = {
  client_count: number;
  documents_ready: number;
  user_count: number;
};

export type ChatMessage = {
  id: string;
  conversation_id?: string;
  client?: string;
  role: "user" | "assistant";
  content: string;
  sources: Array<{
    id: string;
    section_header: string;
    page_number: number | null;
    document_id: string;
    source?: string;
    chunk_type?: string;
    display_label?: string;
  }>;
  created_at: string;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function fetchPlatformStats(): Promise<PlatformStats> {
  const data = await request<PlatformStats & Record<string, number>>("/api/stats/");
  return {
    client_count: data.client_count,
    documents_ready: data.documents_ready,
    user_count: data.user_count,
  };
}

export async function fetchClients(): Promise<Client[]> {
  return request<Client[]>("/api/clients/");
}

export async function createClient(name: string): Promise<Client> {
  return request<Client>("/api/clients/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export async function fetchUsers(q?: string): Promise<User[]> {
  const params = q ? `?q=${encodeURIComponent(q)}` : "";
  return request<User[]>(`/api/users/${params}`);
}

export async function searchUsers(q: string): Promise<User[]> {
  return request<User[]>(`/api/users/search/?q=${encodeURIComponent(q)}`);
}

export async function createUser(email: string, displayName: string): Promise<User> {
  return request<User>("/api/users/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, display_name: displayName }),
  });
}

export async function updateUser(
  userId: string,
  data: { email?: string; display_name?: string },
): Promise<User> {
  return request<User>(`/api/users/${userId}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function fetchConversations(
  userId: string,
  clientId: string,
): Promise<Conversation[]> {
  return request<Conversation[]>(
    `/api/conversations/?user_id=${userId}&client_id=${clientId}`,
  );
}

export async function createConversation(
  userId: string,
  clientId: string,
  title?: string,
): Promise<Conversation> {
  return request<Conversation>("/api/conversations/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      client_id: clientId,
      title: title || "New chat",
    }),
  });
}

export async function fetchConversationMessages(
  conversationId: string,
): Promise<ChatMessage[]> {
  return request<ChatMessage[]>(`/api/conversations/${conversationId}/messages/`);
}

export async function deleteConversation(conversationId: string): Promise<void> {
  return request<void>(`/api/conversations/${conversationId}/`, { method: "DELETE" });
}

export async function fetchDocuments(clientId: string): Promise<Document[]> {
  return request<Document[]>(`/api/documents/?client_id=${clientId}`);
}

export async function uploadDocument(clientId: string, file: File): Promise<Document> {
  const form = new FormData();
  form.append("client_id", clientId);
  form.append("file", file);
  return request<Document>("/api/documents/", { method: "POST", body: form });
}

export async function fetchDocumentStatus(documentId: string): Promise<DocumentStatus> {
  return request<DocumentStatus>(`/api/documents/${documentId}/status/`);
}

export async function deleteDocument(documentId: string): Promise<void> {
  return request<void>(`/api/documents/${documentId}/`, { method: "DELETE" });
}

export async function reuploadDocument(
  documentId: string,
  clientId: string,
  file: File,
): Promise<Document> {
  const form = new FormData();
  form.append("client_id", clientId);
  form.append("file", file);
  return request<Document>(`/api/documents/${documentId}/`, { method: "PUT", body: form });
}

export { API_URL };
