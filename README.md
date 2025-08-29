# 🧠 Huawei Cloud ServiceStage MCP Server Adapter

> **LLM × CloudOps 实践案例：构建面向 AI Agent 的 ServiceStage MCP Server，自动封装 API 接口、支持自然语言驱动的云服务调用。**

---

## 📌 项目简介

本项目基于华为云 ServiceStage API，构建了符合 [Model Context Protocol (MCP)](https://www.anthropic.com/news/model-context-protocol) 的三代服务端，支持自动生成工具函数、Agent 场景高层封装，以及跨产品（CAE / FunctionGraph）扩展，助力 AI Agent 实现云上应用的自动化管理。

项目包含 3 个版本：

| 版本 | 关键特性 | 工具数量 | 封装方式 | Agent 调用适配 |
|------|----------|----------|------------|----------------|
| `v1.0` | 手动编写基础工具函数 | 13 个 | 精简原子工具 | ✅ |
| `v2.0` | 基于 OpenAPI 自动生成 | 38 个 | 自定义生成器 (`gen_from_openapi.py`) | ✅ |
| `v3.0` | 控制台旅程场景封装 + 扩展至 CAE / FG | 13 个高层封装 + CAE/FG | LLM 一键调用 | ✅ |

---

## 🚀 快速开始

### 资源准备

#### ✅ Cherry Studio 下载
- 官网：[https://www.cherry-ai.com/](https://www.cherry-ai.com/)

#### ✅ 获取LLM Tokens
- DeepSeek: https://platform.deepseek.com/
- 华为本地部署LLM：https://3ms.huawei.com/km/blogs/details/15325384

#### ✅ 获取ServiceStage Tokens
- 获取华为云ServiceStage Token:参考"Token获取.txt"

#### ✅ ServiceStage OpenAPI spec
- mcp_server_v2.0目录下

### 环境准备

#### ✅ Windows 下各版本mcp server项目启动
- 部署流程：虚拟环境部署 --> 环境激活 -->代理配置 --> 安装依赖
- 推荐以各版本mcp_server_vX.0作为独立目录，进行项目管理及其环境管理
- 参考"创建虚拟环境.txt"

#### ✅ Cherry Studio配置
- 部署流程：配置模型服务（LLM Tokens） --> MCP设置
- 各版本mcp server的MCP设置，参考对应目录下 "CherryStudio配置.txt"
- 参考快速教程：[部署教程（Bilibili）](https://www.bilibili.com/video/BV1RNTtzMENj)

#### ✅ 设置环境变量(可选）
```powershell
$env:HW_AUTH_TOKEN="（ServiceStage 控制台获取）"
$env:SERVICESTAGE_BASE="https://servicestage.cn-north-4.myhuaweicloud.com"
$env:CAE_BASE="https://cae.cn-north-4.myhuaweicloud.com"
$env:FG_BASE="https://functiongraph.cn-north-4.myhuaweicloud.com"
$env:SS_SPEC_PATH="D:/.../ss_environment_api.yaml" # v2 必需
$env:HTTP_VERIFY="false"
$env:HTTP_TIMEOUT="60"
```

---

## 🧩 版本说明

### 🔹 `v1.0/`

- 文件：`main.py`
- 手动编写 MCP 工具函数（环境 CRUD / 调优 API）
- 适配 CherryStudio → 可直接运行：

```bash
uv --directory ./mcp_server_v1.0 run main.py
```

---

### 🔹 `v2.0/`

- 文件：`gen_from_openapi.py`
- 自动化脚本：从 OpenAPI 规范中自动生成 MCP 工具
- 特性：
  - 支持 `$ref` 递归解析、`allOf` 合并、path/query/body 参数提取
  - 覆盖 38 个接口，封装效率提升 80%+
- 启动：

```bash
uv --directory ./mcp_server_v2.0 run gen_from_openapi.py
```

---

### 🔹 `v3.0/`

- 文件：`mcp_agent_ops.py`
- 高层 Agent 场景封装（基于控制台用户旅程）
- 支持：
  - 一键创建环境并开通 RDS
  - 快照回滚 / 自动调优 / CAE 应用与组件 / FG 函数
- 启动：

```bash
uv --directory ./mcp_server_v3.0 run mcp_agent_ops.py
```

---

## 📊 项目结构

```
mcp_server/
│
├─ mcp_server_v1.0/              # 手工编写工具函数
│   └─ main.py
│
├─ mcp_server_v2.0/              # OpenAPI → MCP 自动生成
│   ├─ gen_from_openapi.py
│   └─ ss_environment_api.yaml   # 原始 spec
│
├─ mcp_server_v3.0/              # 控制台旅程封装
│   └─ mcp_agent_ops.py
│
└─ list_mcp_tools_offline.py     # 辅助统计工具数量
```

---

## 📚 相关资料

- [MCP 协议定义（Anthropic）](https://www.anthropic.com/news/model-context-protocol)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [CherryStudio](https://www.cherry-ai.com/)
- [华为云 ServiceStage 控制台](https://support.huaweicloud.com/intl/zh-cn/usermanual-servicestage/)

---

## 📌 致谢 & 贡献

项目由 **XavierD3728** 完成，实习期间在华为云 PaaS 团队主导开发，交付了完整的 MCP Server 三代版本。欢迎 Star 或使用反馈。
