import { Loader2, Lock, LogIn, UserPlus } from "lucide-react";
import { useState } from "react";

type AuthMode = "login" | "register";

interface AuthScreenProps {
  loading: boolean;
  error: string | null;
  onSubmit: (payload: {
    mode: AuthMode;
    username: string;
    password: string;
    displayName?: string;
  }) => Promise<void> | void;
}

export default function AuthScreen({ loading, error, onSubmit }: AuthScreenProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#eef2ff_100%)] text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-6xl items-stretch px-6 py-10 lg:px-10">
        <section className="hidden flex-1 flex-col justify-between rounded-l-2xl border border-slate-200 bg-slate-950 px-10 py-12 text-slate-100 lg:flex">
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-slate-300">
              <Lock className="h-3.5 w-3.5" />
              Mneme Workspace
            </div>
            <div className="space-y-4">
              <h1 className="font-serif text-5xl leading-tight">让知识库、记忆库和图谱在一个工作台里协同起来。</h1>
              <p className="max-w-xl text-sm leading-7 text-slate-300">
                这个前端现在直接接入后端接口。登录后可以管理知识库、上传文档、提交索引、发起问答，并查看图谱、
                记忆治理、画像分析、成长建议和陪伴式回复。
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            {[
              ["Documents", "上传、索引、删除和任务追踪"],
              ["Graph", "用户、知识库、文档三种图视角"],
              ["Memory", "时间线、主题聚类与治理关系"],
              ["Insights", "画像、成长、分析、建议、陪伴"],
            ].map(([title, text]) => (
              <div key={title} className="border border-white/10 bg-white/5 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.2em] text-slate-400">{title}</div>
                <div className="mt-2 leading-6 text-slate-200">{text}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="flex w-full max-w-2xl flex-1 items-center rounded-2xl border border-slate-200 bg-white px-6 py-10 shadow-[0_40px_120px_rgba(15,23,42,0.10)] lg:rounded-l-none lg:px-12">
          <div className="mx-auto w-full max-w-md space-y-8">
            <div className="space-y-4">
              <div className="inline-flex rounded-full border border-slate-200 bg-slate-50 p-1">
                <button
                  type="button"
                  onClick={() => setMode("login")}
                  className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm transition ${
                    mode === "login" ? "bg-slate-950 text-white" : "text-slate-500"
                  }`}
                >
                  <LogIn className="h-4 w-4" />
                  登录
                </button>
                <button
                  type="button"
                  onClick={() => setMode("register")}
                  className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm transition ${
                    mode === "register" ? "bg-slate-950 text-white" : "text-slate-500"
                  }`}
                >
                  <UserPlus className="h-4 w-4" />
                  注册
                </button>
              </div>

              <div>
                <h2 className="font-serif text-4xl leading-tight text-slate-950">
                  {mode === "login" ? "进入你的工作台" : "创建新的账户"}
                </h2>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  {mode === "login"
                    ? "使用用户名和密码登录，继续管理知识库与分析结果。"
                    : "注册后会自动创建默认知识库，后续可以继续扩展更多知识库。"}
                </p>
              </div>
            </div>

            <form
              className="space-y-5"
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
                    className="h-12 w-full border border-slate-300 px-4 text-sm outline-none transition focus:border-slate-950"
                    placeholder="例如：Juemin"
                  />
                </label>
              )}

              <label className="block space-y-2">
                <span className="text-[11px] uppercase tracking-[0.24em] text-slate-500">用户名</span>
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  className="h-12 w-full border border-slate-300 px-4 text-sm outline-none transition focus:border-slate-950"
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
                  className="h-12 w-full border border-slate-300 px-4 text-sm outline-none transition focus:border-slate-950"
                  placeholder="至少 8 个字符"
                  minLength={8}
                  required
                />
              </label>

              {error && <div className="border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

              <button
                type="submit"
                disabled={loading}
                className="inline-flex h-12 w-full items-center justify-center gap-2 bg-slate-950 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : mode === "login" ? <LogIn className="h-4 w-4" /> : <UserPlus className="h-4 w-4" />}
                {mode === "login" ? "登录并加载工作台" : "注册并继续"}
              </button>
            </form>

            <p className="text-xs leading-6 text-slate-400">
              当前前端直接对接后端 API，建议先确保后端数据库、Milvus、Neo4j 与任务队列已经可用。
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
