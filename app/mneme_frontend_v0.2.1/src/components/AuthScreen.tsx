import { ArrowRight, Bot, Database, GitBranch, Loader2, Lock, LogIn, ShieldCheck, UserPlus } from "lucide-react";
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
    title: "Docs",
    text: "上传、索引、追踪",
    icon: Database,
  },
  {
    title: "Graph",
    text: "用户、知识库、文档三层视角",
    icon: GitBranch,
  },
  {
    title: "Memory",
    text: "记忆沉淀与洞察",
    icon: Bot,
  },
];

const fieldClassName =
  "h-12 w-full rounded-md border border-slate-300 bg-white px-4 text-sm text-slate-950 shadow-sm outline-none transition placeholder:text-slate-400 hover:border-slate-400 focus-visible:border-sky-700 focus-visible:ring-4 focus-visible:ring-sky-100 disabled:cursor-not-allowed disabled:bg-slate-100";

export default function AuthScreen({ apiBaseUrl, loading, error, onSubmit }: AuthScreenProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");

  return (
    <div className="min-h-screen text-slate-900">
      <div className="mx-auto grid min-h-screen max-w-[1400px] gap-5 px-4 py-4 sm:px-6 sm:py-6 lg:grid-cols-[minmax(0,1.15fr)_520px] lg:px-8 lg:py-8">
        <section className="order-2 relative overflow-hidden rounded-lg border border-slate-200/80 bg-slate-950 text-slate-100 shadow-[0_40px_120px_rgba(15,23,42,0.16)] lg:order-1">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(96,165,250,0.2),transparent_32%),radial-gradient(circle_at_80%_18%,rgba(45,212,191,0.14),transparent_24%)]" />
          <div className="absolute inset-0 bg-[linear-gradient(120deg,transparent_0%,rgba(255,255,255,0.02)_42%,transparent_100%)]" />

          <div className="relative flex h-full flex-col justify-between gap-10 px-6 py-7 sm:px-8 sm:py-9 lg:px-10 lg:py-10">
            <div className="space-y-8">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-slate-200">
                <Lock className="h-3.5 w-3.5" />
                Mneme Workspace
              </div>

              <div className="space-y-4">
                <div className="flex flex-wrap gap-2 text-[11px] uppercase tracking-[0.18em] text-slate-300">
                  <span className="rounded-full border border-white/12 bg-white/6 px-3 py-1">Knowledge Base</span>
                  <span className="rounded-full border border-white/12 bg-white/6 px-3 py-1">GraphRAG</span>
                  <span className="rounded-full border border-white/12 bg-white/6 px-3 py-1">Insights</span>
                </div>
                <h1 className="max-w-3xl font-serif text-4xl leading-tight text-white sm:text-5xl lg:text-6xl">
                  一处登录，进入完整记忆工作台。
                </h1>
                <p className="max-w-xl text-sm leading-7 text-slate-300 sm:text-[15px]">
                  更少说明，更快进入知识库、文档、图谱和分析流。
                </p>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                {capabilityItems.map((item) => (
                  <div key={item.title} className="rounded-lg border border-white/10 bg-white/[0.06] px-4 py-4 backdrop-blur-sm">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-md border border-white/10 bg-white/10 text-sky-200">
                        <item.icon className="h-5 w-5" />
                      </div>
                      <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Module</div>
                    </div>
                    <div className="mt-5 text-lg font-medium text-white">{item.title}</div>
                    <p className="mt-2 text-sm leading-6 text-slate-300">{item.text}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-[1.2fr_0.8fr]">
              <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
                <div className="flex items-center justify-between gap-3 border-b border-white/10 pb-3">
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Live Surface</div>
                    <div className="mt-1 text-sm font-medium text-white">进入后立刻可见的核心层</div>
                  </div>
                  <ShieldCheck className="h-4 w-4 text-sky-200" />
                </div>
                <div className="mt-4 grid gap-2 text-sm text-slate-300 sm:grid-cols-2">
                  <div className="rounded-md border border-white/10 bg-black/10 px-3 py-3">知识库切换</div>
                  <div className="rounded-md border border-white/10 bg-black/10 px-3 py-3">文档任务状态</div>
                  <div className="rounded-md border border-white/10 bg-black/10 px-3 py-3">图谱视角</div>
                  <div className="rounded-md border border-white/10 bg-black/10 px-3 py-3">成长分析</div>
                </div>
              </div>

              <div className="grid gap-3">
                {[
                  ["Auth", "用户名密码直达工作台"],
                  ["Runtime", "健康状态同屏可见"],
                ].map(([title, text]) => (
                  <div key={title} className="rounded-lg border border-white/10 bg-slate-950/50 px-4 py-4">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-slate-400">{title}</div>
                    <p className="mt-2 text-sm leading-6 text-slate-300">{text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="order-1 flex items-center rounded-lg border border-slate-200/80 bg-white/[0.92] px-5 py-6 shadow-[0_32px_90px_rgba(15,23,42,0.08)] backdrop-blur lg:order-2 lg:px-8 lg:py-8">
          <div className="mx-auto flex w-full max-w-md flex-col">
            <div className="space-y-5">
              <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-slate-500 shadow-sm">
                <ShieldCheck className="h-3.5 w-3.5 text-sky-700" />
                Local access
              </div>

              <div className="inline-flex w-fit rounded-full border border-slate-200 bg-slate-100 p-1">
                <button
                  type="button"
                  onClick={() => setMode("login")}
                  aria-pressed={mode === "login"}
                  className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-sky-100 ${
                    mode === "login" ? "bg-slate-950 text-white shadow-sm" : "text-slate-500 hover:text-slate-900"
                  }`}
                >
                  <LogIn className="h-4 w-4" />
                  登录
                </button>
                <button
                  type="button"
                  onClick={() => setMode("register")}
                  aria-pressed={mode === "register"}
                  className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-sky-100 ${
                    mode === "register" ? "bg-slate-950 text-white shadow-sm" : "text-slate-500 hover:text-slate-900"
                  }`}
                >
                  <UserPlus className="h-4 w-4" />
                  注册
                </button>
              </div>

              <div className="space-y-3">
                <h2 className="font-serif text-4xl leading-tight text-slate-950 sm:text-[2.5rem]">
                  {mode === "login" ? "进入你的工作台" : "创建新的账户"}
                </h2>
                <p className="text-sm leading-7 text-slate-500">{mode === "login" ? "继续处理知识库与任务。" : "注册后会自动创建默认知识库。"}</p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="text-[11px] uppercase tracking-[0.2em] text-slate-500">Access</div>
                  <div className="mt-2 text-sm font-medium text-slate-900">Username + password</div>
                  <p className="mt-1 text-xs leading-6 text-slate-500">认证后直接进入控制台。</p>
                </div>
                <div className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="text-[11px] uppercase tracking-[0.2em] text-slate-500">Workspace</div>
                  <div className="mt-2 text-sm font-medium text-slate-900">默认知识库自动就绪</div>
                  <p className="mt-1 text-xs leading-6 text-slate-500">首次注册即可开始上传文档。</p>
                </div>
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
                  <span className="text-[11px] uppercase tracking-[0.24em] text-slate-500">显示名</span>
                  <input
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    autoComplete="nickname"
                    className={fieldClassName}
                    placeholder="例如：Juemin"
                  />
                </label>
              )}

              <label className="block space-y-2">
                <span className="text-[11px] uppercase tracking-[0.24em] text-slate-500">用户名</span>
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  autoComplete="username"
                  className={fieldClassName}
                  placeholder="至少 3 个字符"
                  minLength={3}
                  required
                />
              </label>

              <label className="block space-y-2">
                <span className="text-[11px] uppercase tracking-[0.24em] text-slate-500">密码</span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  className={fieldClassName}
                  placeholder="至少 8 个字符"
                  minLength={8}
                  required
                />
              </label>

              {error ? (
                <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={loading}
                className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-md bg-slate-950 text-sm font-medium text-white transition hover:bg-sky-700 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-sky-100 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : mode === "login" ? (
                  <ArrowRight className="h-4 w-4" />
                ) : (
                  <UserPlus className="h-4 w-4" />
                )}
                {mode === "login" ? "登录" : "注册并继续"}
              </button>
            </form>

            <div className="mt-6 flex items-start gap-3 rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-xs leading-6 text-slate-500">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
              <div>
                当前前端连接
                <span className="mx-1 font-mono text-[11px] text-slate-900">{apiBaseUrl}</span>
                ，请先确认后端与任务队列已可用。
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
