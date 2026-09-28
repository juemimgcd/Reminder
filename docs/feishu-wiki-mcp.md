# 飞书知识库只读 MCP

入口：`python -m app.mneme.memoria.feishu_mcp`。

Agent 可以浏览指定知识库的目录、调用飞书搜索、读取新版文档纯文本，并按原文链接引用。
每个进程绑定一个飞书用户令牌和一个知识空间。访问范围是该用户当前权限与配置空间的交集。
首版不接入 Reminder 的画像、索引或记忆提取，不写飞书文档、不发送消息。

## 准备飞书访问权限

1. 在飞书开放平台配置应用，申请以下 API 页面列出的只读权限，并按租户流程发布/批准。
2. 通过应用的用户 OAuth 授权流程获取 `user_access_token`。用户必须能访问目标知识空间和文档。
   **Wiki 搜索使用用户令牌**，现有飞书消息适配器的 `tenant_access_token` 不能替代它。
3. 由可信宿主将有效用户令牌保存到本机文件，限制为运行用户可读（例如 `chmod 600`）。
   不要把令牌写进仓库、对话或 MCP 工具参数。
4. 从目标知识空间管理信息/API 获取 `space_id`，从实际 Wiki 链接获取租户域名。
   `space_id` 是数字空间 ID，不是 `/wiki/` 后面的节点 token。

OAuth 登录、刷新令牌由宿主负责；本适配器不保存 App Secret，也不自动刷新令牌。
宿主应在到期前原子替换令牌文件。适配器每次工具调用重新读取，单次调用内使用同一份令牌。
不要把同一个授权进程分享给不同身份的用户。

## 启动配置

复用独立 MCP 依赖，不需要数据库、Redis、Embedding 或大模型配置：

```sh
python -m pip install -r requirements/mcp.txt

export FEISHU_WIKI_MCP_SPACE_ID='你的数字知识空间ID'
export FEISHU_WIKI_MCP_USER_TOKEN_FILE='/absolute/path/to/feishu-user-token'
export FEISHU_WIKI_MCP_ORIGIN='https://你的租户.feishu.cn'
python -m app.mneme.memoria.feishu_mcp
```

| 环境变量 | 含义 |
| --- | --- |
| `FEISHU_WIKI_MCP_SPACE_ID` | 必填，固定知识空间 ID |
| `FEISHU_WIKI_MCP_USER_TOKEN_FILE` | 必填，用户访问令牌文件的绝对路径 |
| `FEISHU_WIKI_MCP_ORIGIN` | 必填，真实租户 HTTPS 域名，用来生成原文链接 |
| `FEISHU_WIKI_MCP_TIMEOUT_SECONDS` | 可选，单次 HTTP 请求超时，默认 30 秒，最大 120 秒 |

通用 stdio MCP 客户端配置示例（将路径和占位值替换为实际值）：

```json
{
  "mcpServers": {
    "reminder-feishu-wiki": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["-m", "app.mneme.memoria.feishu_mcp"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/Reminder",
        "FEISHU_WIKI_MCP_SPACE_ID": "1234567890123456789",
        "FEISHU_WIKI_MCP_USER_TOKEN_FILE": "/absolute/path/to/feishu-user-token",
        "FEISHU_WIKI_MCP_ORIGIN": "https://example.feishu.cn"
      }
    }
  }
}
```

服务不监听 HTTP 端口；stdout 保留给 MCP 协议，运行日志由 SDK 写 stderr。

## 工具

### `list_wiki_nodes(parent_node_token?, page_token?, page_size=20)`

列出根节点或指定节点的直接子节点，每页最多 50 条。返回标题、类型、原文链接和分页信息。
可以沿目录逐层浏览，不会自动遍历全部文档。指定父节点时先确认其知识空间归属。

### `search_wiki(query, page_token?, page_size=20)`

调用飞书原生 Wiki 搜索，始终向上游传入配置的 `space_id`，并检查返回条目的空间归属。
关键词不能为空，每页最多 50 条。结果是文档元数据；需要阅读原文后才能据此回答内容问题。
搜索匹配语义和索引时效由飞书决定，不代表 Reminder 的向量召回或对所有正文的完整匹配。

### `read_wiki_document(node_token, offset=0, max_chars=12000)`

先解析 Wiki 节点并验证范围，再读取它对应的 `docx` 文档纯文本。
模型不能直接提供任意文档 ID 或 URL 绕过节点检查。跨空间快捷方式暂不支持。

返回 `source`、文本、字符偏移、总字符数、`next_offset` 和全文 `content_sha256`。
每次最多返回 20000 字符；沿 `next_offset` 继续读取，直至它为 `null`。
字符偏移针对纯文本，不是页码或飞书块 ID。每次读取都会重新请求完整纯文本；分段限制的是
Agent 上下文大小，不是飞书下载量。若两次读取的哈希不同，表示内容发生变化，应从头重读。
元数据中的更新时间来自读取前的节点信息，不代表原子版本快照。

只支持新版文档纯文本。旧版 doc、表格、多维表格、文件附件、图片识别暂未实现；不支持的类型
会返回明确错误，可通过目录/搜索结果的 `source_url` 在飞书打开。

## 分页、错误与回答边界

- 空页不一定表示结束：飞书权限过滤可能产生 `items=[]` 且 `has_more=true`，仍应继续分页。
- 工具错误与“搜索成功但无结果”分开；网络故障、令牌过期、权限不足、限流不会伪装为空结果。
- API 错误只返回状态/错误码，不转发上游任意响应体或凭据；不自动重试，避免隐藏请求次数。
- 目录和原文内容都是外部数据。Agent 应引用 `source_url`，不能执行文档中的指令。
- 本地没有内容缓存；实时权限由飞书检查。未来同步到 Reminder 时，需要另行实现权限撤销与删除同步。

可用于接入后验收的真实问题：

- “列出这个知识库的一级目录。”
- “搜索发布流程，读取相关文档并附上来源。”
- “继续读取上次文档剩余部分。”

## 官方接口依据

- [搜索 Wiki：官方 SDK 请求定义](https://github.com/larksuite/oapi-sdk-python/blob/v2_main/lark_oapi/api/wiki/v1/model/search_node_request.py)：`POST /open-apis/wiki/v1/nodes/search`，用户令牌。
- [搜索参数：官方 MCP 定义](https://github.com/larksuite/lark-openapi-mcp/blob/main/src/mcp-tool/tools/zh/gen-tools/zod/wiki_v1.ts)：`query` 与 `space_id`。
- [获取知识空间子节点列表](https://open.feishu.cn/document/server-docs/docs/wiki-v2/space-node/list)。
- [获取知识空间节点信息](https://open.feishu.cn/document/server-docs/docs/wiki-v2/space-node/get_node)。
- [获取文档纯文本内容](https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document/raw_content)。

本地协议检查只能验证 MCP 工具发现和参数契约。真实飞书搜索、权限、原文访问需要配置有效用户
令牌与知识空间后联调；没有完成该联调前，不应称为已接通飞书。
