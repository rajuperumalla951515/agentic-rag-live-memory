import type { Conversation, Message, TokenResponse, Workspace } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
let demoSessionRequest: Promise<TokenResponse> | null = null;

async function request<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  demoSession: () => {
    if (!demoSessionRequest) {
      demoSessionRequest = request<TokenResponse>("/api/v1/auth/demo-session", undefined, {
        method: "POST",
      }).finally(() => {
        demoSessionRequest = null;
      });
    }
    return demoSessionRequest;
  },
  authenticate: (mode: "login" | "register", email: string, password: string) =>
    request<TokenResponse>(`/api/v1/auth/${mode}`, undefined, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  workspaces: (token: string) => request<Workspace[]>("/api/v1/workspaces", token),
  createWorkspace: (token: string, name: string) =>
    request<Workspace>("/api/v1/workspaces", token, {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  conversations: (token: string, workspaceId: string) =>
    request<Conversation[]>(`/api/v1/workspaces/${workspaceId}/conversations`, token),
  createConversation: (token: string, workspaceId: string, title: string) =>
    request<Conversation>(`/api/v1/workspaces/${workspaceId}/conversations`, token, {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  messages: (token: string, conversationId: string) =>
    request<Message[]>(`/api/v1/conversations/${conversationId}/messages`, token),
  createMessage: (token: string, conversationId: string, content: string) =>
    request<Message>(`/api/v1/conversations/${conversationId}/messages`, token, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
};
