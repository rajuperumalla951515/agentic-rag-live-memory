import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api } from "./api";
import type { Conversation, Message, TokenResponse, Workspace } from "./types";

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [demoLoading, setDemoLoading] = useState(import.meta.env.DEV);
  const [demoError, setDemoError] = useState("");

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    let active = true;
    api.demoSession()
      .then((result) => active && setToken(result.access_token))
      .catch((caught: unknown) => active && setDemoError(errorText(caught)))
      .finally(() => active && setDemoLoading(false));
    return () => { active = false; };
  }, []);

  if (demoLoading) {
    return (
      <main className="auth-page">
        <p className="muted" role="status">Opening local demo workspace...</p>
      </main>
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={token ? <Navigate to="/" replace /> : <AuthPage onAuthenticated={setToken} notice={demoError} />}
      />
      <Route
        path="/register"
        element={token ? <Navigate to="/" replace /> : <AuthPage onAuthenticated={setToken} notice={demoError} />}
      />
      <Route
        path="/*"
        element={
          token ? (
            <WorkspacePage token={token} onSignOut={() => setToken(null)} />
          ) : (
            <AuthPage onAuthenticated={setToken} notice={demoError} />
          )
        }
      />
    </Routes>
  );
}

export function AuthPage({
  onAuthenticated,
  notice = "",
}: {
  onAuthenticated: (token: string) => void;
  notice?: string;
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const mode = location.pathname === "/register" ? "register" : "login";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result: TokenResponse = await api.authenticate(mode, email, password);
      onAuthenticated(result.access_token);
      navigate("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to authenticate");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <p className="eyebrow">PERSONAL KNOWLEDGE WORKSPACE</p>
        <h1>agentic-rag-live-memory</h1>
        <p className="muted">Sign in to your workspace to continue.</p>
        {notice && (
          <p className="error" role="status">
            Local demo is unavailable: {notice}. Sign in or enable DEMO_MODE in the backend configuration.
          </p>
        )}
        <form onSubmit={submit}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            autoComplete="email"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            type="password"
            minLength={mode === "register" ? 12 : 1}
            maxLength={128}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error && <p className="error" role="alert">{error}</p>}
          <button className="primary-button" disabled={busy}>
            {busy ? "Please wait..." : mode === "register" ? "Create account" : "Sign in"}
          </button>
        </form>
        <p className="auth-switch">
          {mode === "register" ? "Already have an account?" : "New to the workspace?"}{" "}
          <Link to={mode === "register" ? "/login" : "/register"}>
            {mode === "register" ? "Sign in" : "Create an account"}
          </Link>
        </p>
      </section>
    </main>
  );
}

function WorkspacePage({ token, onSignOut }: { token: string; onSignOut: () => void }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [conversationTitle, setConversationTitle] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    api.workspaces(token)
      .then((items) => {
        if (active) {
          setWorkspaces(items);
          setWorkspaceId(items[0]?.id ?? "");
        }
      })
      .catch((caught: unknown) => active && setError(errorText(caught)));
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    if (!workspaceId) {
      setConversations([]);
      setConversationId("");
      return;
    }
    let active = true;
    api.conversations(token, workspaceId)
      .then((items) => {
        if (active) {
          setConversations(items);
          setConversationId(items[0]?.id ?? "");
        }
      })
      .catch((caught: unknown) => active && setError(errorText(caught)));
    return () => { active = false; };
  }, [token, workspaceId]);

  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    let active = true;
    api.messages(token, conversationId)
      .then((items) => active && setMessages(items))
      .catch((caught: unknown) => active && setError(errorText(caught)));
    return () => { active = false; };
  }, [token, conversationId]);

  async function createWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      const workspace = await api.createWorkspace(token, workspaceName);
      setWorkspaces((items) => [...items, workspace]);
      setWorkspaceId(workspace.id);
      setWorkspaceName("");
    } catch (caught) {
      setError(errorText(caught));
    }
  }

  async function createConversation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspaceId) return;
    setError("");
    try {
      const conversation = await api.createConversation(token, workspaceId, conversationTitle);
      setConversations((items) => [conversation, ...items]);
      setConversationId(conversation.id);
      setConversationTitle("");
    } catch (caught) {
      setError(errorText(caught));
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!conversationId || !draft.trim()) return;
    setError("");
    setBusy(true);
    try {
      const message = await api.createMessage(token, conversationId, draft.trim());
      setMessages((items) => [...items, message]);
      setDraft("");
    } catch (caught) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="workspace-layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">M</span>
          <div><strong>agentic-rag-live-memory</strong><small>PERSONAL WORKSPACE</small></div>
        </div>
        <label className="sidebar-label" htmlFor="workspace">WORKSPACE</label>
        <select id="workspace" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)}>
          {workspaces.map((workspace) => (
            <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
          ))}
        </select>
        <form className="inline-form" onSubmit={createWorkspace}>
          <input
            aria-label="New workspace name"
            placeholder="New workspace"
            maxLength={120}
            required
            value={workspaceName}
            onChange={(event) => setWorkspaceName(event.target.value)}
          />
          <button aria-label="Create workspace" className="icon-button">+</button>
        </form>
        <div className="section-heading">
          <span>CONVERSATIONS</span>
          <button className="text-button" onClick={() => document.getElementById("conversation-title")?.focus()}>
            New
          </button>
        </div>
        <form className="inline-form" onSubmit={createConversation}>
          <input
            id="conversation-title"
            aria-label="New conversation title"
            placeholder="Conversation title"
            maxLength={200}
            required
            disabled={!workspaceId}
            value={conversationTitle}
            onChange={(event) => setConversationTitle(event.target.value)}
          />
          <button aria-label="Create conversation" className="icon-button" disabled={!workspaceId}>+</button>
        </form>
        <nav className="conversation-list" aria-label="Conversations">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={`conversation-link${conversation.id === conversationId ? " selected" : ""}`}
              onClick={() => setConversationId(conversation.id)}
            >
              <span className="conversation-dot" />
              {conversation.title}
            </button>
          ))}
          {conversations.length === 0 && <p className="sidebar-empty">Your conversations will appear here.</p>}
        </nav>
        <button className="sign-out" onClick={onSignOut}>Sign out</button>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <span>Workspace</span>
          <span className="status-pill"><span /> Phase 1 foundation</span>
        </header>
        <section className="chat-panel">
          {error && <p className="error notice" role="alert">{error}</p>}
          {conversationId ? (
            <>
              <div className="chat-heading">
                <p className="eyebrow">CONVERSATION</p>
                <h1>{conversations.find((item) => item.id === conversationId)?.title}</h1>
                <p className="muted">Messages are saved to this workspace.</p>
              </div>
              <div className="message-list" aria-live="polite">
                {messages.map((message) => (
                  <article className="message user-message" key={message.id}>
                    <span className="message-label">YOU</span>
                    <p>{message.content}</p>
                  </article>
                ))}
                {messages.length === 0 && (
                  <div className="empty-state">
                    <div className="empty-icon">✳</div>
                    <h2>A place for connected knowledge</h2>
                    <p>Start a conversation. Your messages are persisted; AI answers and connected sources are not available yet.</p>
                  </div>
                )}
              </div>
              <form className="composer" onSubmit={sendMessage}>
                <textarea
                  aria-label="Write a message"
                  placeholder="Write a message..."
                  maxLength={20000}
                  required
                  rows={2}
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                />
                <div className="composer-footer">
                  <span>Messages are stored securely with your workspace.</span>
                  <button className="primary-button send-button" disabled={busy || !draft.trim()}>
                    {busy ? "Saving..." : "Send"}
                  </button>
                </div>
              </form>
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">✳</div>
              <h2>Start with a conversation</h2>
              <p>Create a conversation from the sidebar. AI responses are not yet implemented.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function errorText(caught: unknown): string {
  return caught instanceof Error ? caught.message : "Something went wrong";
}
