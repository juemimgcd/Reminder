# mneme_frontend

Mneme 的 Vue 3 前端工作台，围绕当前后端已确认的稳定能力构建：

- 认证登录 / 注册
- 知识库切换与创建
- 文档上传、索引状态与手动触发索引
- 基于知识库的 RAG 问答
- 记忆库结构化视图
- 画像与成长分析面板

## 技术栈

- Vue 3
- Vite
- TypeScript
- Vue Router
- Pinia
- 原生 `fetch` API

## 目录结构

```text
src/
├─ assets/styles/       # 全局样式与设计 token
├─ components/          # 工作台组件
├─ composables/         # 主题与 reduced-motion
├─ lib/                 # API 层与类型
├─ mocks/               # Mock 数据与演示 API
├─ router/              # 路由
├─ stores/              # 会话与工作台状态
└─ views/               # 页面级视图
```

## 运行方式

```bash
npm install
npm run dev
```

默认会读取 `.env` 或 `.env.example` 中的以下配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_API_PREFIX=
VITE_USE_MOCKS=true
```

## 后端接入说明

当前项目默认开启 Mock 回退，原因是后端工作树里存在部分缺位文件，无法仅凭源码 100% 还原所有响应 schema。前端因此做了两层保护：

1. `VITE_USE_MOCKS=true` 时直接使用本地演示数据
2. `VITE_USE_MOCKS=false` 时优先调用真实接口，失败后自动回退 Mock

另外还增加了两层协议兼容：

1. 自动尝试无前缀路径和 `/api/v1` 路径
2. 自动兼容 `data/items/records/knowledge_bases/documents/profile/growth` 等常见包裹结构

切到真实后端时建议：

1. 先确认后端允许前端域名的 CORS
2. 按实际接口 schema 调整 `src/lib/api.ts`
3. 如果上传接口字段名不同，优先调整 `uploadDocuments`

## 设计取向

这个前端没有做成通用 SaaS 模板，而是围绕 Mneme 的“个人记忆型 RAG”定位设计：

- 视觉上强调 archive / workspace / memory atlas
- 信息架构上强调“上下文切换”和“证据可追溯”
- 动效上保留微交互，但遵守 `prefers-reduced-motion`
- 响应式覆盖桌面与移动端，不依赖 hover 才能完成核心操作
