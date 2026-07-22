# Mneme Frontend Design Quality Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变后端 API、业务能力和预览模式的前提下，把 Mneme 现有 Vue 前端重构为层级清楚、交互一致、移动端可用、具有安静知识工具气质的高品质工作台。

**Architecture:** 保留 `useMnemeWorkspace`、`useDocumentWorkspace`、`useGraphInteraction` 等业务边界，把改造集中在语义化设计令牌、可复用 UI 原语、工作台壳层和各视图的呈现层。先统一跨页面的状态与交互契约，再依次收口 Dashboard、Vault、Graph、AI、Memory、Settings，避免一次性重写业务逻辑。

**Tech Stack:** Vue 3.5、TypeScript 5.8、Tailwind CSS 4、Lucide Vue、D3 7、Vite 6、Playwright（仅运行现有检查；本轮不新增或修改测试文件）。

---

## 1. 设计判断

Mneme 当前前端已经完成了从“通用卡片式 SaaS”向知识工作台的第一轮迁移：深浅主题、活动栏、资源栏、文档阅读器、图谱画布、AI 会话和基础 UI 组件均已存在。本轮不应再次更换视觉方向，而应解决“一致性、密度、状态、交互细节”尚未收口的问题。

目标气质定义为：**安静、可信、专注、略带人文感的个人知识工作台**。视觉上使用纸张/石墨般的中性色、克制的紫色强调、稳定的排版层级；交互上强调即时、可中断和可预测，不追求炫技动效。

### 当前审查结论

| Before | After | Why |
| --- | --- | --- |
| `index.css` 主要定义颜色，间距、字号、圆角、层级和动效仍散落在各视图 | 建立完整的语义令牌，并让页面只消费令牌 | 统一细节比逐页微调更能形成产品质感 |
| `UiIconButton` 使用 `transition: 140ms ease`，隐式影响所有可动画属性 | 仅过渡 `color`、`background-color`、`border-color`、`transform` | 避免布局属性被意外动画，降低不可预测性 |
| 大量原生按钮在每个 `.vue` 内重复定义 | 页面操作统一落到 `UiButton`、`UiIconButton`、`UiSegmentedControl` | 让 hover、focus、active、disabled、loading 行为一致 |
| 可点击控件普遍缺少按压反馈 | 指针点击时使用 `transform: scale(0.97)`，键盘触发不增加运动 | 提供即时触控反馈，同时保持高频键盘操作直接 |
| 通知、过滤器、移动抽屉通过 `v-if` 突然出现或消失 | 浮层从触发源进入，抽屉使用 180–220ms 强 `ease-out`，退出更快 | 保持空间关系，减少界面跳变 |
| `ResourceSidebar` 使用内置 `ease`，遮罩无进入/退出层级 | 使用 `cubic-bezier(0.23, 1, 0.32, 1)`，同步淡入遮罩 | 抽屉应立即响应且在结尾柔和停下 |
| 移动端底栏同时展示 Files + 6 个业务入口 | 保留 4 个高频入口，把 Memory、Settings 收入 More | 7 个入口使标签过窄、误触概率高，缺乏优先级 |
| 顶栏、通知按钮、状态栏是独立叠加区域 | 合并为一致的工作区标题栏与状态槽 | 降低绝对定位造成的冲突和视觉碎片 |
| Dashboard 同时承担概览、创建、上传、问答、Companion | 首屏聚焦“继续工作”，次级动作进入清晰的命令区 | 优先呈现用户下一步，而不是平铺所有能力 |
| Graph 工具条、筛选、状态、提示、预览都悬浮在画布上 | 建立单一画布工具条和可停靠详情面板 | 减少遮挡，提升图谱作为主内容的沉浸感 |
| AI 页单文件约 689 行，消息、运行轨迹、模式和输入区共享一套局部样式 | 拆成会话列表、消息流、运行轨迹、回答模式、Composer | 组件边界与用户感知区域一致，便于统一状态 |
| Memory 的 `CandidateInbox.vue`、`MemoryDetail.vue` 是压缩式单行实现 | 重构为清晰的列表/详情/审核区域并复用基础组件 | 当前实现难以维护，也没有达到其他核心页面的完成度 |
| 设置页把外观、渠道、模型、同步和健康信息全部堆在连续卡片中 | 桌面端使用分组导航与连续设置行；破坏性操作独立分区 | 设置页需要高扫描效率，而不是卡片数量 |
| `prefers-reduced-motion` 将所有动效压到 `0.01ms` | 移除位移动效，保留 120–160ms 的颜色与透明度过渡 | reduced motion 的目标是减少空间运动，不是移除所有状态反馈 |
| 中英文文案仍散落在模板，部分中文显示存在编码异常风险 | 所有用户可见文案进入 `messages.ts`，并进行 UTF-8 与双语布局检查 | 语言切换应是完整体验，不应只覆盖导航 |

## 2. 成功标准

- 桌面端 1440×900 下，壳层、标题栏、资源栏和主工作区形成稳定三层层级，不出现悬浮控件互相遮挡。
- 平板端 1024×768 下，资源栏和上下文面板改为覆盖式抽屉，主内容宽度不被长期挤压。
- 移动端 390×844 与 360×800 下，底栏每项标签可读、触控目标不小于 44×44px，主要任务无需横向滚动。
- 深色与浅色主题均具有明确的正文、次级文字、边框、选中态和危险态对比，不使用纯黑/纯白的大面积强反差。
- 页面不再自行定义常规按钮、图标按钮、状态条、分段选择器和确认对话框的交互样式。
- 鼠标点击具有轻微按压反馈；键盘触发的导航、命令和频繁切换不播放进入动画。
- 所有浮层都有明确触发源、Escape 关闭、点击外部关闭和焦点返回；模态框保持居中来源。
- 主要 UI 动画不超过 300ms；抽屉/浮层进入使用强 `ease-out`，同屏位置变化使用 `ease-in-out`，持续运动仅用于真实加载。
- `npm run lint`、`npm run test:contracts`、`npm run build` 和现有关键 Playwright 场景通过。

## 3. 范围与非目标

### 本轮范围

- 设计令牌、基础组件、工作台壳层、登录页和六个现有业务视图。
- 深浅主题、双语、响应式、键盘焦点、浮层行为和状态反馈。
- 仅呈现层组件拆分；允许移动模板与局部状态，不改变请求结构和领域模型。

### 非目标

- 不修改后端 API、数据库结构或 `app/mneme_frontend_v0.2.1/src/lib/api.ts` 的协议。
- 不重写 D3 力导向布局或 `useGraphInteraction` 的模拟算法。
- 不引入新的大型 UI 框架或动画库；预定义动效优先使用 CSS transition。
- 不增加新的业务模块、营销页、插画系统或装饰性 3D 效果。
- 根据项目级 Test Addition Policy，本轮不新增或修改测试文件；功能确认后，如用户明确要求，再单独补充测试。

## 4. 文件结构规划

### 新建设计基础

- `app/mneme_frontend_v0.2.1/src/styles/tokens.css`：颜色、排版、间距、圆角、阴影、层级和动效令牌。
- `app/mneme_frontend_v0.2.1/src/styles/base.css`：元素默认样式、焦点、滚动条、reduced-motion 和触控媒体查询。
- `app/mneme_frontend_v0.2.1/src/styles/workspace.css`：壳层网格和跨视图布局工具。
- `app/mneme_frontend_v0.2.1/src/components/ui/UiSegmentedControl.vue`：主题、过滤器、回答模式等单选分段控件。
- `app/mneme_frontend_v0.2.1/src/components/ui/UiPopover.vue`：有来源感的非模态浮层。
- `app/mneme_frontend_v0.2.1/src/components/ui/UiDialog.vue`：确认与危险操作模态框。
- `app/mneme_frontend_v0.2.1/src/components/ui/UiField.vue`：输入控件标签、说明、错误和禁用状态。
- `app/mneme_frontend_v0.2.1/src/components/shell/WorkspaceToolbar.vue`：统一标题、上下文、通知和页面操作。
- `app/mneme_frontend_v0.2.1/src/components/shell/MoreNavigationSheet.vue`：移动端低频入口。
- `app/mneme_frontend_v0.2.1/src/components/ai/ChatHistory.vue`：会话搜索与历史列表。
- `app/mneme_frontend_v0.2.1/src/components/ai/ChatMessageList.vue`：消息、来源与空状态。
- `app/mneme_frontend_v0.2.1/src/components/ai/AgentRunTrace.vue`：多 Agent 执行轨迹。
- `app/mneme_frontend_v0.2.1/src/components/ai/ChatComposer.vue`：回答模式、输入与运行控制。

### 保留业务边界

- `useMnemeWorkspace.ts` 继续负责认证、知识库、通知、聊天、模型、同步等业务状态。
- `useDocumentWorkspace.ts` 继续负责文档树、标签页、内容和 Blob 生命周期。
- `useGraphInteraction.ts` 继续负责图谱筛选、布局、拖拽、焦点和标签可见性。
- 视图组件只消费上述能力，不复制请求和领域状态。

## 5. 动效决策矩阵

| 场景 | 频率 | 是否动画 | 规范 |
| --- | ---: | --- | --- |
| 活动栏/底栏导航 | 每日数十次 | 否 | 状态颜色即时切换；指针按压仅 100–140ms scale |
| 文档标签切换、Graph filter、回答模式 | 高频 | 否 | 使用背景/文字颜色 120ms，不移动内容 |
| Tooltip 首次出现 | 中频 | 是 | 150ms opacity + `scale(0.97)`；连续浏览工具栏时立即显示 |
| Popover/通知面板 | 偶发 | 是 | 160–200ms opacity + `scale(0.97)`，`transform-origin` 指向触发器 |
| 资源抽屉/详情抽屉 | 偶发 | 是 | 180–220ms translate + opacity，进入 ease-out、退出更快 |
| 模态确认框 | 偶发 | 是 | 居中 180ms opacity + `scale(0.96)`，不从触发器缩放 |
| Toast/状态反馈 | 偶发 | 是 | 180ms opacity + 小幅 Y 位移，使用可中断 transition |
| Skeleton/Spinner | 加载时 | 是 | linear 或柔和 opacity；不阻止 reduced-motion 用户理解状态 |
| 图谱拖拽 | 直接操作 | 跟手 | 位置直接跟随指针，松手后由现有 D3 模拟接管，不添加装饰弹跳 |

## 6. 分阶段实施计划

### Task 1: 统一设计令牌与全局基础

**Files:**
- Create: `app/mneme_frontend_v0.2.1/src/styles/tokens.css`
- Create: `app/mneme_frontend_v0.2.1/src/styles/base.css`
- Create: `app/mneme_frontend_v0.2.1/src/styles/workspace.css`
- Modify: `app/mneme_frontend_v0.2.1/src/index.css`
- Modify: `app/mneme_frontend_v0.2.1/src/main.ts`

- [x] **Step 1: 把主题值迁移为语义令牌**

建立以下稳定契约；组件不得直接写新的十六进制颜色或自定义阴影：

```css
:root {
  --surface-canvas: #111113;
  --surface-sidebar: #18181b;
  --surface-panel: #202024;
  --surface-raised: #29282e;
  --surface-selected: #323038;
  --text-primary: #eeecef;
  --text-secondary: #b4afb8;
  --text-tertiary: #85808a;
  --border-subtle: #343239;
  --border-default: #4a4650;
  --accent-primary: #a78bda;
  --accent-hover: #b79ee2;
  --accent-soft: rgb(167 139 218 / 14%);
  --ease-out-ui: cubic-bezier(0.23, 1, 0.32, 1);
  --ease-in-out-ui: cubic-bezier(0.77, 0, 0.175, 1);
  --duration-press: 120ms;
  --duration-fast: 160ms;
  --duration-panel: 220ms;
  --radius-control: 6px;
  --radius-panel: 10px;
  --shadow-popover: 0 16px 42px rgb(0 0 0 / 30%);
}
```

浅色主题提供一一对应的值；保留旧变量作为临时 alias，完成所有视图迁移后再删除 alias。

- [x] **Step 2: 建立 12/14/16/20/28px 的稳定字号阶梯和 4px 间距网格**

正文默认 14px，阅读正文 16px，辅助元数据 12px；仅长文标题使用 serif，工具栏、按钮和设置标题使用 sans，技术状态使用 mono。

- [x] **Step 3: 拆分 `index.css` 职责**

`index.css` 仅保留 Tailwind 引入和三个样式文件的 import：

```css
@import "tailwindcss";
@import "./styles/tokens.css";
@import "./styles/base.css";
@import "./styles/workspace.css";
```

- [x] **Step 4: 修正全局 reduced-motion 策略**

对 reduced-motion 移除 `transform` 位移和循环装饰动画，保留帮助理解状态的颜色/透明度过渡；spinner 改为静态进度标记或低频 opacity pulse。

- [x] **Step 5: 验证设计基础**

Run: `npm run lint && npm run test:contracts && npm run build`

Expected: 三条命令退出码均为 0；主题切换、Tailwind 工具类和现有组件样式未丢失。

### Task 2: 补齐 UI 原语并消除重复控件样式

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/components/ui/UiButton.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/ui/UiIconButton.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/ui/UiStatusPanel.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/ui/UiEmptyState.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/ui/UiSkeleton.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/ui/UiSegmentedControl.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/ui/UiPopover.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/ui/UiDialog.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/ui/UiField.vue`

- [ ] **Step 1: 统一按钮状态契约**

`UiButton` 支持 `primary | secondary | ghost | danger`、`sm | md`、loading、disabled；`UiIconButton` 增加 tooltip slot 和 active indicator。两者仅在精确属性上 transition，并在精细指针设备上提供 hover：

```css
.ui-pressable {
  transition:
    color var(--duration-fast) ease,
    background-color var(--duration-fast) ease,
    border-color var(--duration-fast) ease,
    transform var(--duration-press) var(--ease-out-ui);
}
@media (hover: hover) and (pointer: fine) {
  .ui-pressable:hover:not(:disabled) { border-color: var(--border-default); }
}
.ui-pressable:active:not(:disabled) { transform: scale(0.97); }
```

- [ ] **Step 2: 建立分段控件契约**

`UiSegmentedControl` 接收 `modelValue`、`options: { value; label; icon? }[]`、`ariaLabel`，渲染单选语义；切换只改变颜色和背景，不位移滑块，避免高频交互变慢。

- [ ] **Step 3: 建立 Popover 与 Dialog 行为契约**

`UiPopover` 必须支持 trigger slot、content slot、Escape、外部点击、焦点返回和 `transform-origin`；`UiDialog` 必须支持标题、描述、确认/取消、焦点约束和居中进入。所有 `window.confirm` 后续迁移至 `UiDialog`。

- [ ] **Step 4: 建立表单与状态契约**

`UiField` 统一 label、description、error、required；`UiStatusPanel` 的 info/success/warning/danger 同时使用图标、标题和颜色，不仅依赖颜色。

- [ ] **Step 5: 验证键盘、指针和 reduced-motion**

手动使用 Tab、Shift+Tab、Enter、Space、Escape 检查新增原语；在 Chrome DevTools 切换触摸模拟与 reduced-motion，确认 hover 不会在触摸设备粘滞、焦点不会丢失。

### Task 3: 重组工作台壳层、标题栏和移动导航

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/shell/ActivityBar.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/shell/ResourceSidebar.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/shell/MobileNavigation.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/shell/StatusBar.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/shell/WorkspaceToolbar.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/shell/MoreNavigationSheet.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useResponsiveShell.ts`

- [ ] **Step 1: 将顶栏与通知整合进 `WorkspaceToolbar`**

Toolbar 固定包含当前视图标题、知识库上下文、页面级 action slot、通知和用户菜单。Graph、AI 不再通过条件绕过顶栏，而是提供 compact/overlay 变体，避免页面各自发明顶部结构。

- [ ] **Step 2: 让资源栏内容随视图变化**

Dashboard/Settings 展示知识库概览，Vault 展示文档树，Graph 展示节点与文档过滤，AI 展示会话历史；桌面宽度使用 264px，平板和移动改为 overlay drawer。

- [ ] **Step 3: 改造移动端入口优先级**

底栏固定为 `Home / Vault / Graph / AI / More` 五项，Files 成为 Vault/Graph/AI 标题栏的上下文按钮；More sheet 提供 Memory、Settings、主题、帮助和退出。

- [ ] **Step 4: 完成抽屉细节**

资源抽屉进入 220ms、退出 160ms，遮罩同步透明度；支持 Escape、点击遮罩、焦点返回和 safe-area。抽屉关闭时使用 `inert`/不可聚焦状态，不能只靠 `aria-hidden`。

- [ ] **Step 5: 统一低优先级状态**

StatusBar 仅在桌面显示连接、索引、当前知识库等低优先级信息；移动端将异常状态提升为可操作 status panel，避免占用固定高度。

- [ ] **Step 6: 响应式验收**

分别检查 1440×900、1024×768、768×1024、390×844、360×800；Expected: 无主页面横向滚动、通知不覆盖标题、资源抽屉不永久挤压内容、底栏文字完整。

### Task 4: 重做登录页与 Dashboard 的首要任务层级

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/views/DashboardView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/i18n/messages.ts`

- [ ] **Step 1: 登录页采用双区但克制的构图**

桌面端左侧为品牌价值与三个能力短句，右侧为认证表单；移动端只保留紧凑品牌头和表单。背景使用微弱径向明度变化，不加入插画、粒子或循环动画。

- [ ] **Step 2: Dashboard 首屏改为“继续工作”**

标题区展示当前知识库、最近活动和一个主操作；Documents/Memories/Graph 指标改为一条紧凑概览，不使用三个等权大卡片。

- [ ] **Step 3: 命令模块按用户意图分组**

默认展示“继续阅读”和“最近文件”；Create/Upload 为创建类操作，Ask/Companion 为查询类操作。桌面使用分段侧栏，移动端使用横向分段控件，保持当前提交函数不变。

- [ ] **Step 4: 补齐本地化与状态**

将认证、Dashboard command、空状态和错误文案全部迁移到 `messages.ts`；loading 时骨架与最终布局一致，创建/提问中禁用重复提交。

- [ ] **Step 5: 验证 Preview 模式**

Run: `npm run dev:preview`

Expected: 未登录流程、预览登录、创建知识库、上传入口、Ask Vault 和 Companion 的调用路径仍可达，首屏没有布局跳动。

### Task 5: 优化 Vault 为稳定的阅读工作区

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/views/VaultView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/documents/DocumentTree.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/documents/DocumentTreeNode.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/documents/DocumentReader.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/documents/DocumentContent.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/documents/DocumentProperties.vue`

- [ ] **Step 1: 明确三栏优先级**

文档树 240px、阅读区自适应、属性面板 280px；阅读区是唯一主表面，左右栏降低背景对比。属性面板无选中文档时自动收起，不保留空白列。

- [ ] **Step 2: 统一树节点交互**

选中态同时使用背景、左侧标记和字重；行操作仅在 hover/focus-within 时显示，触摸端进入单独菜单。移动/重命名菜单迁移到 `UiPopover`，来源点与触发按钮一致。

- [ ] **Step 3: 重做阅读标签和文档操作**

标签切换不播放位移动画；关闭按钮仅在 active/hover/focus 时出现。Download/Index 使用 secondary，Delete 使用 danger，并把危险操作迁移到 `UiDialog`。

- [ ] **Step 4: 校准长文阅读**

正文最大行宽 72ch、行高 1.7；标题、段落、列表、引用、代码、表格、图片间距使用稳定节奏。PDF/HTML/Markdown 的加载、失败和下载替代路径保持一致。

- [ ] **Step 5: 平板与移动重组**

文档树和属性改为左右 drawer；移动端顶部仅保留 Files、截断标题、Properties，文档 actions 放入 overflow menu，避免三按钮平均分配挤压。

- [ ] **Step 6: Vault 验收**

检查文件夹创建/重命名/移动、文档拖放、标签切换、PDF 预览、Escape 关闭抽屉和焦点返回；Expected: 无业务行为变化，阅读正文不随面板开合产生不可控跳动。

### Task 6: 减少 Graph 画布遮挡并强化直接操作

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/views/GraphView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useGraphInteraction.ts`（仅在呈现所需状态确实缺失时修改）

- [ ] **Step 1: 合并画布工具条**

将标题、GraphRAG 搜索、过滤器和节点类型整合成一条响应式工具条；Zoom/Center/Restart 保留为右下角紧凑控件。移除画布中央的常驻操作提示，改为首次或空状态提示。

- [ ] **Step 2: 详情面板改为停靠/抽屉模式**

桌面端右侧 320px 停靠，不覆盖工具条；小屏端使用底部 sheet。打开详情时画布可选择保持尺寸或重新 center，但不得让节点落到不可见区域。

- [ ] **Step 3: 强化节点状态而不制造噪声**

默认节点降低标签密度；hover 显示标签和关联路径，selected 使用清晰描边，neighbor 保持高于背景但低于 selected。拖拽期间禁止文字选择并保持 pointer capture。

- [ ] **Step 4: 校准 Graph 动效**

拖拽直接跟手，筛选切换不增加出入场动画，边/节点焦点只过渡 opacity 140ms；详情面板 200ms ease-out。键盘选择和打开文档保持即时。

- [ ] **Step 5: Graph 验收**

检查单击选择、双击打开、Space 选择、Enter 打开、拖拽、缩放、筛选、详情关闭和布局重启；Expected: 工具条与详情不相互遮挡，移动端可触达所有控制。

### Task 7: 拆分并重做 AI 会话体验

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/views/AiLabView.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/ai/ChatHistory.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/ai/ChatMessageList.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/ai/AgentRunTrace.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/ai/ChatComposer.vue`

- [ ] **Step 1: 以用户感知区域拆分组件**

`AiLabView.vue` 只组合 history、message list、run trace、composer；workspace 业务方法继续由 props 注入，不在子组件创建第二份聊天状态。

- [ ] **Step 2: 提升消息可读性**

消息正文最大宽度 760px；用户消息使用轻量表面，助手消息主要依赖排版而不是大气泡。来源引用折叠在消息尾部，route/mode 作为低对比元数据。

- [ ] **Step 3: 降低运行轨迹噪声**

Agent trace 默认显示当前步骤和总进度，历史步骤可展开；running/success/error 同时使用图标、文本和颜色。步骤更新只做颜色/透明度变化，不 stagger 阻塞阅读。

- [ ] **Step 4: 固定 Composer 的交互层级**

Composer 位于内容底部，回答模式使用 `UiSegmentedControl`，多 Agent 为明确的开关与说明，Send/Stop/Retry 互斥。发送后立即清空输入并展示运行状态，不等待动画。

- [ ] **Step 5: 移动端拆分历史与聊天**

会话历史进入全屏 drawer；正文与 Composer 占满宽度，键盘弹起时 Composer 不被底栏覆盖，并使用 safe-area padding。

- [ ] **Step 6: AI 验收**

检查新建/搜索/切换/删除会话、四种回答模式、多 Agent、发送、停止、重试、来源展开和流式状态；Expected: 所有现有 workspace 方法保持原调用路径。

### Task 8: 完成 Memory Center 的产品化收口

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/views/MemoryCenterView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/memory/CandidateInbox.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/memory/MemoryList.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/memory/MemoryDetail.vue`

- [ ] **Step 1: 将页面分成审核队列、记忆库、详情三个明确区域**

pending 数量作为审核队列 badge，不放在大标题内；没有候选项时收起审核区。桌面采用列表 + 详情，移动端列表和详情改为导航式切换。

- [ ] **Step 2: 重写压缩模板与局部样式**

将 `CandidateInbox.vue` 和 `MemoryDetail.vue` 改为正常格式，使用 `UiButton`、`UiStatusPanel`、`UiDialog`、语义令牌，移除页面级原生按钮规则。

- [ ] **Step 3: 明确审核与危险动作**

Approve/Reject 具有文字和图标；Revise 提供保存中/成功/失败状态；Invalidate、Hard delete、Purge source 使用不同强度的确认说明。知识库清空和账户清空放到独立 Danger Zone。

- [ ] **Step 4: Memory 验收**

检查候选审核、选择、修订、失效、删除、source purge、knowledge base purge、account purge 和自动学习开关；Expected: 每个异步动作都有 pending 防重复提交和完成反馈。

### Task 9: 重组 Settings 与 Channel Gateway

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/views/SettingsView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/channels/ChannelGatewayPanel.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/i18n/messages.ts`

- [ ] **Step 1: 使用连续设置行代替卡片堆叠**

Appearance、Language、Channels、Models、Sync、Health 仍按锚点分组，但组内使用 label/description/control 三列设置行；只有模型实例、回调地址和危险状态使用带边框容器。

- [ ] **Step 2: 让保存反馈靠近触发点**

主题与语言即时生效；context window 保存、模型测试、默认模型切换、图谱/记忆重建的 pending/success/error 出现在对应行，不使用页面顶部通用字符串。

- [ ] **Step 3: 简化 Channel Gateway 的扫描路径**

顶部展示 Ready/Degraded/Offline 总状态；Deployment、Bindings、Routing、Delivery 分段排列。回调地址提供复制反馈；长 command 使用等宽区域和明确的复制按钮。

- [ ] **Step 4: 响应式与本地化**

桌面侧栏 sticky，平板顶部横向 section nav，移动端改为 select/accordion，不能依赖横向滚动访问最后一项。修复 `zh-CN` 标签和所有遗留硬编码英文。

- [ ] **Step 5: Settings 验收**

检查 light/dark/system、English/简体中文、模型测试/default/context、同步重建和 channel routing；Expected: 设置结果靠近操作显示，Danger/Degraded 不只依赖颜色。

### Task 10: 全局视觉、无障碍和性能验收

**Files:**
- Modify only if defects are found: `app/mneme_frontend_v0.2.1/src/styles/*.css`
- Modify only if defects are found: affected files under `app/mneme_frontend_v0.2.1/src/components/`
- Modify only if defects are found: affected files under `app/mneme_frontend_v0.2.1/src/views/`

- [ ] **Step 1: 运行静态与构建检查**

Run: `npm run lint`

Expected: exit code 0，无 Vue/TypeScript 错误。

Run: `npm run test:contracts`

Expected: exit code 0，现有架构、视图边界和设计系统契约通过。

Run: `npm run build`

Expected: exit code 0，Vite 生成生产构建且 prebuild check 通过。

- [ ] **Step 2: 运行现有关键 E2E 场景**

Run: `npm run test:e2e -- tests/auth-flow.spec.ts tests/responsive-shell.spec.ts tests/layout-regression.spec.ts tests/document-reader.spec.ts tests/force-directed-graph.spec.ts tests/channel-streaming.spec.ts tests/memory-center.spec.ts`

Expected: 所有现有测试通过；如测试断言绑定旧视觉结构，先判断是否为真实行为回归，不在本轮直接修改测试规避失败。

- [ ] **Step 3: 视觉矩阵检查**

在 1440×900、1024×768、768×1024、390×844、360×800 下分别检查 light/dark；覆盖 Login、Dashboard、Vault 空/有内容、Graph 空/有节点、AI 空/流式、Memory 空/有候选、Settings。

- [ ] **Step 4: 动效慢放检查**

在 Chrome Animations 面板以 25% 速度检查抽屉、Popover、Dialog、通知和按钮状态。确认无 `scale(0)`、无 `ease-in`、无大于 300ms 的常规 UI 动画、无错误 transform-origin、无 `transition: all`。

- [ ] **Step 5: 键盘与屏幕阅读语义检查**

仅用键盘完成登录、导航、打开/关闭资源栏、切换文档、Graph 选择、发送聊天和确认危险操作；检查焦点顺序、可见焦点、Escape、aria-expanded/pressed/busy/live 和焦点返回。

- [ ] **Step 6: 性能检查**

在 Graph 模拟与 AI 流式输出同时发生时记录 Performance；Expected: 动画只涉及 transform/opacity/color，持续交互不通过父级 CSS variable 触发整树重算，主线程没有由装饰动画造成的长任务。

## 7. 实施顺序与里程碑

1. **Foundation（Task 1–2）**：设计令牌和 UI 原语成为唯一基础，页面仍保持可用。
2. **Shell（Task 3）**：统一全局导航、标题栏、资源栏和移动结构。
3. **Primary workflows（Task 4–7）**：依次完成 Dashboard、Vault、Graph、AI；每个视图独立验收后再进入下一个。
4. **Governance（Task 8–9）**：完成 Memory 与 Settings/Channels 的信息层级和危险操作。
5. **Quality gate（Task 10）**：统一做双主题、多尺寸、键盘、reduced-motion 和性能检查。

每个里程碑都必须保持 `npm run lint` 和 `npm run build` 可通过；不要在跨里程碑时保留新旧两套基础组件长期并存。

## 8. 完成定义

- 所有成功标准均有对应页面或检查记录。
- `src/views` 和业务组件中不再出现新的通用按钮/输入/浮层重复实现。
- 搜索结果中不存在 `transition: all`、UI `ease-in`、`scale(0)` 进入动效，以及未受 pointer media query 限制的装饰 hover transform。
- 登录、导航、文档、图谱、AI、记忆和设置的业务路径与改造前一致。
- 计划范围内没有新增大型依赖，没有修改后端契约，没有顺带增加业务功能。
- 静态检查、现有契约测试、生产构建、关键 E2E 和人工视觉矩阵均完成并记录结果。

## 9. 自检结果

- **需求覆盖：** 已覆盖前端整体重设计、视觉系统、壳层、六个核心视图、响应式、双主题、双语、动效、无障碍与验证。
- **文件边界：** 新文件只用于跨页面基础和 AI 感知区域拆分；业务 composable 保持原职责。
- **测试策略：** 遵守项目级 Test Addition Policy，不在本轮计划中新增或修改测试，只运行现有检查；用户确认功能后可另立测试补强任务。
- **范围控制：** 不修改后端、不增加业务模块、不引入新 UI/动画框架。
