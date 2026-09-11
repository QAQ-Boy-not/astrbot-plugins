# inspect_response

全链路 4 点调试打印插件。**不修改任何数据流**，纯旁路监听。

## 它做什么

按消息生命周期，在 4 个时刻打印 JSON：

| # | 触发钩子 | 看到什么 |
|---|---------|---------|
| 1 | `event_message_type(ALL)` | AstrBot 收到的**原始消息**（message_chain 结构化） |
| 2 | `on_llm_request` | LLM 实际看到的请求 |
| 3 | `on_llm_response` | LLM 返回的响应 |
| 4 | `on_decorating_result` | 最终装饰后（bot 实际发送的内容） |

完整覆盖"原始 → LLM → 最终"全链路。

## 适合什么场景

- 调试消息处理逻辑
- 验证 @ / 引用 / 附件的解析
- 看 LLM 看到的 vs 原始消息差距多大
- 看 bot 实际发送什么

## 安装

AstrBot Web UI → 插件管理 → 上传 zip → 重载（**不重启容器**）。

## 验证

```
docker logs -f astrbot 2>&1 | grep inspect_response
```

每次消息会触发 1-4 段 JSON 输出。

## 版本

v2.0.0 — 全链路 4 点打印（从 v1.0.0 的 2 点升级）
