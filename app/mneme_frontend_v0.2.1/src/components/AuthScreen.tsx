import { ArrowRight, Database, GitBranch, Key, Loader2, Lock, Mail, ShieldCheck, UserPlus } from "lucide-react";
import { useState } from "react";

type AuthMode = "login" | "register";

interface AuthScreenProps {
  apiBaseUrl: string;
  loading: boolean;
  error: string | null;
  onSubmit: (payload: {
    mode: AuthMode;
    username: string;
    password: string;
    displayName?: string;
  }) => Promise<void> | void;
}

const capabilityItems = [
  {
    title: "Documents",
    text: "Upload, index, and trace source files inside one vault.",
    icon: Database,
  },
  {
    title: "Graph",
    text: "Move between user, vault, document, and memory graph scopes.",
    icon: GitBranch,
  },
  {
    title: "Memory",
    text: "Surface durable entries, evidence, and retrieval context.",
    icon: ShieldCheck,
  },
];

const fieldClassName =
  "h-10 w-full rounded-md border border-outline-variant bg-surface-container-low pl-9 pr-3 text-sm text-on-surface outline-none transition placeholder:text-text-muted focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60";

export default function AuthScreen({ apiBaseUrl, loading, error, onSubmit }: AuthScreenProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");

  return (
    <div className="min-h-screen bg-surface-dim text-on-surface">
      <div className="mx-auto grid min-h-screen max-w-[1180px] gap-5 px-4 py-4 sm:px-6 sm:py-6 lg:grid-cols-[minmax(0,0.95fr)_440px] lg:px-8 lg:py-8">
        <section className="order-2 relative overflow-hidden rounded-md border border-outline bg-surface-container-lowest shadow-[0_30px_140px_rgba(0,0,0,0.38)] lg:order-1">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(#2a2721_1px,transparent_1px)] [background-size:22px_22px] opacity-80" />
          <div className="relative flex h-full flex-col justify-between gap-10 px-6 py-7 sm:px-8 sm:py-9 lg:px-10">
            <div>
              <div className="mb-10 inline-flex items-center gap-2 rounded-md border border-outline-variant bg-surface-container px-3 py-1.5">
                <Lock className="h-3.5 w-3.5 text-primary" />
                <span className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Private memory vault</span>
              </div>

              <div className="mb-5 flex size-12 items-center justify-center rounded-md bg-primary text-xl font-bold text-on-primary">
                M
              </div>
              <h1 className="text-5xl font-semibold tracking-normal text-on-surface">Mneme</h1>
              <p className="mt-5 max-w-xl text-sm leading-7 text-on-surface-variant">
                A focused knowledge workspace for indexed documents, graph-backed retrieval, and durable memory context.
              </p>

              <div className="mt-10 grid gap-3 md:grid-cols-3">
                {capabilityItems.map((item) => (
                  <div key={item.title} className="rounded-md border border-outline-variant bg-surface/80 px-4 py-4">
                    <div className="flex size-9 items-center justify-center rounded-md border border-outline-variant bg-surface-container text-primary">
                      <item.icon className="h-4 w-4" />
                    </div>
                    <div className="mt-5 text-sm font-semibold text-on-surface">{item.title}</div>
                    <p className="mt-2 text-xs leading-6 text-text-muted">{item.text}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-outline-variant bg-surface/80 p-4">
              <div className="flex items-center justify-between gap-3 border-b border-outline-variant pb-3">
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Connection</div>
                  <div className="mt-1 text-sm font-medium text-on-surface">Backend endpoint</div>
                </div>
                <ShieldCheck className="h-4 w-4 text-secondary" />
              </div>
              <div className="mt-3 truncate font-mono text-[11px] text-on-surface-variant">{apiBaseUrl}</div>
            </div>
          </div>
        </section>

        <section className="order-1 flex items-center rounded-md border border-outline bg-surface px-5 py-6 shadow-[0_28px_100px_rgba(0,0,0,0.28)] lg:order-2 lg:px-8 lg:py-8">
          <div className="mx-auto flex w-full max-w-md flex-col">
            <div className="space-y-5">
              <div className="inline-flex w-fit rounded-md border border-outline-variant bg-surface-container-low p-1">
                <button
                  type="button"
                  onClick={() => setMode("login")}
                  aria-pressed={mode === "login"}
                  className={`inline-flex items-center gap-2 rounded px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
                    mode === "login" ? "bg-primary text-on-primary" : "text-text-muted hover:text-on-surface"
                  }`}
                >
                  <ArrowRight className="h-4 w-4" />
                  Sign in
                </button>
                <button
                  type="button"
                  onClick={() => setMode("register")}
                  aria-pressed={mode === "register"}
                  className={`inline-flex items-center gap-2 rounded px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
                    mode === "register" ? "bg-primary text-on-primary" : "text-text-muted hover:text-on-surface"
                  }`}
                >
                  <UserPlus className="h-4 w-4" />
                  Register
                </button>
              </div>

              <div>
                <h2 className="text-3xl font-semibold leading-tight text-on-surface">
                  {mode === "login" ? "Open your vault" : "Create a vault"}
                </h2>
                <p className="mt-2 text-sm leading-7 text-text-muted">
                  {mode === "login" ? "Continue into your Mneme workspace." : "Create an account and start with a default knowledge base."}
                </p>
              </div>
            </div>

            <form
              className="mt-8 space-y-5"
              onSubmit={async (event) => {
                event.preventDefault();
                await onSubmit({
                  mode,
                  username,
                  password,
                  displayName: displayName || undefined,
                });
              }}
            >
              {mode === "register" && (
                <label className="block space-y-2">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Display name</span>
                  <div className="relative">
                    <ShieldCheck className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                    <input
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                      autoComplete="nickname"
                      className={fieldClassName}
                      placeholder="Your name"
                    />
                  </div>
                </label>
              )}

              <label className="block space-y-2">
                <span className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Username</span>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                  <input
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    autoComplete="username"
                    className={fieldClassName}
                    placeholder="username"
                    minLength={3}
                    required
                  />
                </div>
              </label>

              <label className="block space-y-2">
                <span className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Password</span>
                <div className="relative">
                  <Key className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                    className={fieldClassName}
                    placeholder="password"
                    minLength={8}
                    required
                  />
                </div>
              </label>

              {error ? (
                <div className="rounded-md border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-300" role="alert">
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={loading}
                className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-primary text-sm font-semibold text-on-primary transition hover:bg-on-primary-container focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : mode === "login" ? <ArrowRight className="h-4 w-4" /> : <UserPlus className="h-4 w-4" />}
                {mode === "login" ? "Open vault" : "Create vault"}
              </button>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}
