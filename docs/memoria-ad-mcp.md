# 广告候选重排 MCP

`app.mneme.memoria.mcp_server` 是独立的 stdio MCP 服务，使用官方 Python SDK
`mcp==1.30.0` 的 FastMCP。支持标准初始化、`tools/list`、`tools/call` 和结构化工具结果。
依赖与 Web/模型运行环境分开，安装文件为 `requirements/mcp.txt`。

调用链：MCP Host → `recommend_ads` → Memoria `POST /v1/ad-recommendations`
→ 原有授权、低敏 Memory 筛选、Embedding 重排与业务分降级 → MCP 结构化结果。

## 启动

在仓库根目录安装适配器依赖后启动：

```sh
python -m pip install -r requirements/mcp.txt
python -m app.mneme.memoria.mcp_server
```

启动环境由可信宿主配置：

| 环境变量 | 含义 |
| --- | --- |
| `MEMORIA_MCP_BASE_URL` | Memoria 服务地址，默认 `http://127.0.0.1:8010`；远程地址必须使用 HTTPS |
| `MEMORIA_MCP_OWNER_ID` | 必填，固定的正整数用户 ID |
| `MEMORIA_MCP_KNOWLEDGE_BASE_ID` | 可选；缺省表示用户范围，必须与令牌声明一致 |
| `MEMORIA_MCP_TOKEN_FILE` | 必填，包含服务 JWT 的文件路径，建议使用绝对路径 |
| `MEMORIA_MCP_TIMEOUT_SECONDS` | 请求超时，默认 30 秒，最大 120 秒 |

MCP 客户端的启动 command 为对应环境的 Python，args 为
`["-m", "app.mneme.memoria.mcp_server"]`，工作目录为仓库根目录。
所有日志写 stderr，stdout 仅用于 MCP 协议消息。服务不监听 HTTP 端口。

宿主为每个用户/知识库范围启动独立进程，不能把同一个已授权进程共享给不同用户。
服务 JWT 由已有后端或可信凭据签发组件提供，包含 `ads:recommend`、`owner_id`、
`knowledge_base_id` 以及正确的 `iss`、`aud`、`iat`、`exp`。适配器不持有签名密钥。
令牌文件应仅允许运行用户读取；宿主在过期前原子替换文件，适配器每次调用重新读取。
签发和轮换仍由宿主负责，适配器不会自行提升权限或刷新令牌。

## 工具契约

`recommend_ads(placement, candidates, limit=1)`：

- `placement`：1–64 字符的广告位标识。
- `candidates`：1–100 条上游已经完成业务筛选的候选广告；沿用 `AdCandidate`
  字段与长度限制，广告 ID 必须唯一，`business_score` 在 0–1 之间。
- `limit`：1–10。
- 用户 ID、知识库 ID、服务地址、令牌均不属于模型可填参数。

结果沿用 `AdRecommendationResponse`，包含生成的 `request_id`、`personalized`、
以及广告 ID、分数和匹配候选标签。适配器校验结果的请求 ID、候选归属、去重与数量。
结果不包含 Memory 原文、证据或身份凭据。

无授权偏好、无合格偏好或 Embedding 失败时，业务服务返回 `personalized=false`
和业务分排序。服务令牌过期或范围不匹配则返回 MCP 工具错误，不能被伪装成排序成功。
网络超时、HTTP 失败和响应契约错误均转换为不含响应体或凭据的工具错误。

该适配器不修改用户广告授权，不产生广告曝光或点击事件，不承担候选生成与投放。

## 验证边界

协议发现和工具参数验证可以在没有数据库的情况下检查。成功的个性化结果还需要
运行中的 Memoria、匹配范围的有效服务 JWT、用户明确开启广告个性化、有效低敏偏好
以及可用 Embedding 服务。协议握手通过不代表这条业务链路已经联调成功。

SDK 参考：[官方 Python SDK v1 文档](https://py.sdk.modelcontextprotocol.io/v1/)。
