export interface User {
  id: string;
  email: string;
}

export interface TokenResponse {
  access_token: string;
  expires_in: number;
  user: User;
}

export interface Workspace {
  id: string;
  name: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  workspace_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}
