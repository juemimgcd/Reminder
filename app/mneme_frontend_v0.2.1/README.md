# Reminder Frontend

这个前端现在是 Vue 3 + Vite 工作台，直接对接 Reminder 后端接口，不再是静态 AI Studio 原型。

## Run Locally

Prerequisites:

- Node.js 20+
- 可访问的 Reminder 后端

1. 安装依赖

```bash
npm install
```

2. 如有需要，配置接口地址

```bash
cp .env.example .env.local
```

默认开发模式下会请求 `http://127.0.0.1:8000`。

3. 启动前端开发服务器

```bash
npm run dev
```

4. 如果你走的是仓库根目录的嵌入式启动方式，也可以在项目根目录执行：

```bash
bash start.sh
```

这会同时启动后端 `uvicorn` 和前端 `npm run dev:embed`，后者内部执行 `vite build --watch`，最终由后端统一托管页面。

## Build / Check

```bash
npm run lint
npm run build
```

`npm run lint` 使用 `vue-tsc --noEmit` 做类型检查；`npm run build` 会先跑预构建检查，再生成可由后端托管的 `dist`。
