# AI Coding Session Vault — 基于开源底座的完整开发方案

> 文档状态：V2.0
>
> 对应现有代码基线：Agent Session Vault Sync v0.3
>
> 桌面软件基线：`jhlee0409/claude-code-history-viewer` v1.22.0，基准提交 `2e29912c8743c997f203e903e6ae0054865cb8e3`
>
> 目标：不再从零开发会话管理软件，而是在成熟 MIT 开源桌面应用之上，接入现有 Vault Core，形成一个本地优先、可备份、可搜索、可管理、可修复、可交接、可统计、可分析的 AI 编程会话保险箱。
>
> 说明：本文定义下一阶段产品与工程方案。除“当前已实现”明确列出的能力外，其余内容属于待开发范围。

---

## 快速导航

- [1. 决策摘要](#1-决策摘要)
- [2. 产品定位](#2-产品定位)
- [3. 当前已实现](#3-当前已实现)
- [4. 开源底座评估](#4-开源底座评估)
- [5. 复用、修改与新增边界](#5-复用修改与新增边界)
- [6. 最终架构](#6-最终架构)
- [7. 仓库与上游同步策略](#7-仓库与上游同步策略)
- [8. 数据与安全原则](#8-数据与安全原则)
- [9. 桌面软件功能](#9-桌面软件功能)
- [10. Vault Core 接入协议](#10-vault-core-接入协议)
- [11. 会话管理和修改](#11-会话管理和修改)
- [12. 备份、校验和恢复](#12-备份校验和恢复)
- [13. 健康检查和修复](#13-健康检查和修复)
- [14. 跨电脑交接](#14-跨电脑交接)
- [15. 搜索、查看和导出](#15-搜索查看和导出)
- [16. 使用量统计](#16-使用量统计)
- [17. AI 分析](#17-ai-分析)
- [18. UI 信息架构](#18-ui-信息架构)
- [19. 数据模型](#19-数据模型)
- [20. 测试与验收](#20-测试与验收)
- [21. 五阶段开发计划](#21-五阶段开发计划)
- [22. 首个可用版本](#22-首个可用版本)
- [23. 风险与控制](#23-风险与控制)
- [24. Definition of Done](#24-definition-of-done)

---

## 1. 决策摘要

### 1.1 核心决策

不再从零开发：

- 桌面程序外壳；
- 会话列表和详情页；
- 多软件 Provider；
- 全局搜索界面；
- Token 和成本统计界面；
- HTML/JSON 导出框架；
- Windows/macOS/Linux 打包；
- 国际化和中文界面。

以上能力以 `claude-code-history-viewer`（以下简称 CCHV）为桌面软件基础。

现有 `ai-session` 继续承担：

- 增量备份；
- SHA-256 校验；
- 冲突版本保留；
- SQLite 一致快照；
- 多电脑隔离；
- 备份验证；
- Codex 单会话和整库隔离恢复；
- 后续 Doctor、Repair、Handoff 等高可靠能力。

### 1.2 最终产品形态

```text
AI Session Vault Desktop
│
├── CCHV 派生桌面应用
│   ├── Tauri 2
│   ├── React + TypeScript
│   ├── Rust Provider 层
│   ├── 会话浏览、搜索、统计、导出
│   └── Windows/macOS/Linux 软件外壳
│
├── Vault Core Sidecar
│   ├── Python v0.3 现有核心
│   ├── sync / verify / restore
│   ├── doctor / repair / rollback
│   ├── handoff / import
│   └── JSONL 任务事件协议
│
└── 本地数据
    ├── 厂商原生会话
    ├── AgentSessionVault
    ├── 应用元数据数据库
    ├── 修复副本与审计记录
    └── AI 派生分析
```

### 1.3 阶段数量

采用 **5 个阶段**，从阶段 0 到阶段 4：

1. 开源底座导入与基线稳定；
2. 接入现有备份、校验和 Codex 恢复；
3. 健康检查、安全修复和会话管理增强；
4. 导出、跨电脑交接和 Vault 搜索增强；
5. 统一统计、AI 分析和产品化完善。

---

## 2. 产品定位

### 2.1 一句话定位

**AI Session Vault 是一个跨 AI 编程工具的本地会话保险箱，用于查看、搜索、管理、备份、修复、导出、交接和恢复原生会话。**

### 2.2 与普通查看器的差异

CCHV 解决“看得见”，本项目重点补足“保得住、修得好、带得走、能恢复”。

```text
CCHV
= 多工具查看 + 搜索 + 统计 + 导出

AI Session Vault
= CCHV 能力
+ 可验证备份
+ 版本与冲突保护
+ 会话健康检查
+ 安全修复与回滚
+ 原生恢复
+ 跨电脑交接
+ 隐私可控 AI 分析
```

### 2.3 核心用户

- 同时使用 Codex、Claude Code、Gemini CLI、Qwen Code、Kimi、OpenCode、Goose 等工具的开发者；
- 在 Windows、WSL、Linux、远程服务器之间切换工作的用户；
- 担心升级、索引损坏、清理策略或电脑迁移导致会话丢失的用户；
- 需要保存技术决策、错误排查过程和工具调用记录的项目负责人；
- 需要统计不同工具、项目和模型使用量的重度用户。

### 2.4 不做的事情

首期不做：

- 云端账号体系；
- 公网托管会话；
- 团队 RBAC；
- 实时多人协作；
- 自动永久删除；
- 未经验证直接写厂商数据库；
- 为开发测试创建或运行 GitHub Actions。

---

## 3. 当前已实现

当前 `ai-session` v0.3 已实现：

### 3.1 适配器

- Codex；
- Claude Code；
- Gemini CLI；
- Qwen Code；
- Kimi CLI；
- OpenCode；
- Goose；
- Hermes Agent；
- Aider。

### 3.2 备份核心

- 按应用和电脑隔离；
- 增量扫描；
- 未变化文件跳过；
- SHA-256 内容校验；
- 会话增长检测；
- 分叉冲突版本保留；
- SQLite Backup API；
- SQLite `PRAGMA quick_check`；
- manifest 和同步报告；
- 不因源文件删除而删除备份；
- 排除凭据、OAuth、日志和缓存。

### 3.3 恢复

Codex 已支持：

- 单会话隔离恢复；
- 全部会话隔离恢复；
- 已归档单会话激活；
- 不复用旧状态数据库；
- 由 Codex 从 rollout JSONL 重建 SQLite；
- Windows 和 POSIX 启动脚本；
- 恢复报告和哈希验证。

### 3.4 尚未实现

以下属于新方案待开发：

- 桌面软件集成；
- Vault 任务进度界面；
- 通用 Doctor；
- Repair 和回滚；
- `.asvpack` 交接；
- Vault 自有标签和备注；
- Vault 备份内容的统一桌面搜索；
- Markdown/PDF 增强导出；
- AI 分析；
- 更多软件原生恢复。

---

## 4. 开源底座评估

## 4.1 主底座：Claude Code History Viewer

基准：

```text
仓库：jhlee0409/claude-code-history-viewer
版本：1.22.0
提交：2e29912c8743c997f203e903e6ae0054865cb8e3
许可证：MIT
```

### 可直接复用

- Tauri 桌面框架；
- React + TypeScript 前端；
- Rust 后端；
- Windows、macOS、Linux 打包；
- 桌面模式和 Headless Server 模式；
- 多 Provider 检测和解析；
- 会话树、会话列表和详情；
- 工具调用、推理和代码内容渲染；
- 全局搜索；
- 实时文件监听；
- Token 和成本统计；
- HTML、JSON 导出；
- 中文国际化；
- 长会话虚拟滚动；
- Codex 原生重命名和删除的现有实现参考。

### 当前 Provider 覆盖

CCHV 已有 Provider 架构，可覆盖或参考：

- Claude Code；
- Codex；
- Gemini；
- Cursor / Cursor Agent；
- Cline / Roo / Kilo；
- Aider；
- OpenCode；
- Kimi；
- Qwen；
- Goose；
- Continue；
- Trae；
- 其他多种工具。

因此不再在 Python 中重复实现一套完整的“展示解析器”。

## 4.2 使用量参考：ccusage

可借鉴：

- daily / monthly / session 聚合；
- input / output / cache token；
- 按模型拆分；
- 项目过滤；
- 成本估算；
- 离线价格缓存；
- JSON 输出；
- 实际值和估算值区分。

允许借鉴或复用 MIT 代码，但必须保留相应版权和许可证声明。

## 4.3 安全交互参考：Codex Manager

只借鉴设计，不复制 GPL-3.0 代码：

```text
预览 Diff
→ 创建备份
→ 原子写入
→ 重新校验
→ 可恢复旧版本
```

除非未来明确决定整个派生作品采用 GPL-3.0，否则不得将其 GPL 代码复制进项目。

## 4.4 许可证要求

### CCHV 和 ccusage

- MIT；
- 可以修改和再发布；
- 必须保留原版权声明和许可证；
- 新增 `THIRD_PARTY_NOTICES.md`；
- 应在“关于”页面显示上游项目和许可证。

### 厂商格式代码

- 只使用公开源码或官方文档确认路径和格式；
- 不复制不兼容许可证代码；
- 反向工程 Provider 必须标记为 experimental；
- 不把推测路径标记为稳定支持。

---

## 5. 复用、修改与新增边界

| 能力 | 处理方式 | 说明 |
|---|---|---|
| 桌面外壳 | 直接复用 | Tauri、React、设置、更新提示等 |
| Provider 解析 | 以 CCHV 为主 | Rust Provider 是展示和统计的主要解析层 |
| 会话查看 | 直接复用并改中文体验 | 增加 Vault 来源和健康标记 |
| 全局搜索 | 复用并扩展 | 同时搜索原生来源和 Vault 来源 |
| Token 统计 | 复用并统一口径 | 增加数据质量标签 |
| HTML/JSON 导出 | 复用 | 新增 Markdown、PDF 和 Handoff |
| 实时监听 | 复用 | 仅监听，不替代可靠备份 |
| 增量备份 | 使用现有 Vault Core | 不重写为简单文件复制 |
| SQLite 快照 | 使用现有 Vault Core | 保持 Backup API 和校验 |
| Codex 恢复 | 使用现有 Vault Core | 通过 Sidecar 暴露给 UI |
| Doctor/Repair | 新开发 | 优先 Python，逐步迁移 Rust |
| 跨电脑交接 | 新开发 | `.asvpack` |
| AI 分析 | 新开发 | 本地优先、引用可追踪 |
| 原生修改 | 能力门控 | 每个 Provider 独立声明支持范围 |

---

## 6. 最终架构

## 6.1 分层

### A. Desktop Shell

职责：

- 软件窗口；
- 页面路由；
- Provider 视图；
- 任务中心；
- 设置；
- 进度与通知；
- 调用 Tauri Command；
- 启动 Sidecar。

技术：

```text
Tauri 2
React 19
TypeScript
Vite
Rust
```

### B. Provider Layer

职责：

- 发现厂商原生存储；
- 解析会话、消息、工具调用和 Usage；
- 向 UI 提供统一读取结构；
- 提供 Provider 能力声明。

原则：

- CCHV Rust Provider 为主要读取解析器；
- Python Adapter 继续负责备份路径和恢复规则；
- 两者通过能力映射文件保持一致；
- 避免同一格式出现两套互相冲突的业务定义。

### C. Vault Core

职责：

- 建立 Vault；
- 增量同步；
- 内容校验；
- SQLite 快照；
- 冲突版本；
- Doctor；
- Repair；
- Restore；
- Handoff；
- 审计报告。

第一阶段保持 Python，打包为 Sidecar。

### D. App Metadata Store

保存应用自己的信息，而不是修改原始会话：

- Vault 标题；
- 标签；
- 备注；
- 收藏；
- 固定；
- 自定义项目归属；
- 健康状态缓存；
- 修复记录；
- 导出记录；
- AI 分析结果；
- 任务记录。

建议：

```text
<app-data>/ai-session-vault/app.db
```

### E. 原始数据层

来源类型：

```text
live       厂商当前原生会话
vault      AgentSessionVault 备份
recovery   隔离恢复目录
handoff    导入的交接包
```

UI 必须显示来源，不允许让用户误以为 Vault 副本就是正在运行的原生会话。

## 6.2 数据流

```text
原生会话
   │
   ├── CCHV Provider ──→ 浏览 / 搜索 / 统计
   │
   └── Vault Core ─────→ AgentSessionVault
                              │
                              ├── Provider 读取 Vault 副本
                              ├── Doctor / Repair
                              ├── Restore
                              ├── Handoff
                              └── AI 分析
```

---

## 7. 仓库与上游同步策略

## 7.1 推荐双仓库

### 仓库一：当前核心仓库

```text
knownothing20/ai-session
```

职责：

- Vault Core；
- Python CLI；
- Sidecar 协议；
- Doctor/Repair/Restore/Handoff；
- 核心文档；
- 匿名化 Fixtures。

### 仓库二：桌面软件 Fork

建议实施时创建：

```text
knownothing20/ai-session-desktop
```

从 CCHV Fork，职责：

- 桌面 UI；
- Rust Provider；
- Tauri；
- 软件打包；
- 调用 Vault Core Sidecar；
- 应用元数据数据库。

### 为什么不直接把 CCHV 全量塞进当前仓库

- 上游变更量大；
- Rust、React、Python 混在一个仓库会使同步困难；
- 直接 Fork 更容易比较上游提交；
- 桌面发布和核心 CLI 可独立版本；
- 最终安装包仍可把 Sidecar 一起打包，用户看到的是一个软件。

## 7.2 上游同步

添加远端：

```text
origin    knownothing20/ai-session-desktop
upstream  jhlee0409/claude-code-history-viewer
```

维护分支：

```text
main              我们的稳定分支
upstream-sync     纯上游同步分支
feature/*         功能分支
```

同步流程：

1. 读取上游 Release Notes；
2. 拉取到 `upstream-sync`；
3. 本地运行测试和构建；
4. 检查 Provider、数据库和 Tauri 配置差异；
5. 合并到我们分支；
6. 解决冲突；
7. 本地验证；
8. 手动提交。

不得自动周期同步。

## 7.3 GitHub Actions 规则

开发期间：

- 不复制上游 `.github/workflows/`；
- 不创建 Workflow；
- 不触发远端构建；
- 不开启上游 Actions；
- 不设置 push、pull_request、schedule 或 cron；
- 使用本地 Rust、Node、Python 命令验证；
- 发布构建需要 Actions 时，必须单独说明并获得明确授权。

## 7.4 上游代码隔离

Fork 初始化时：

- 保留 `LICENSE`；
- 新增 `THIRD_PARTY_NOTICES.md`；
- “关于”页面显示上游项目；
- 修改品牌和应用 ID；
- 修改存储目录，避免与原 CCHV 冲突；
- 删除未使用的自动更新配置；
- 检查所有外部网络请求；
- 默认完全离线可用。

---

## 8. 数据与安全原则

### 8.1 原始数据不可变

默认不修改：

- 原生 transcript；
- Vault 中的当前备份；
- 厂商 SQLite；
- 厂商索引。

管理操作优先写入应用自己的 `app.db`。

### 8.2 原生修改必须能力门控

Provider 声明：

```text
can_read
can_search
can_export
can_rename_native
can_archive_native
can_delete_native
can_restore_single
can_restore_full
can_repair_index
can_repair_transcript
```

没有明确能力时，UI 禁用按钮，而不是尝试通用修改。

### 8.3 危险操作流程

```text
预检
→ 读取稳定性检查
→ 生成计划
→ 显示 Diff 和影响范围
→ 创建备份或修复副本
→ 原子写入
→ 重读校验
→ 写入审计
→ 支持回滚
```

### 8.4 凭据和隐私

不得备份或导出：

- auth.json；
- API Key；
- OAuth Token；
- Cookie；
- Keychain 导出；
- `.env`；
- 未经用户允许的项目源码。

Handoff 和 AI 分析前必须运行敏感信息扫描。

---

## 9. 桌面软件功能

## 9.1 总览

显示：

- 已检测 Provider；
- 原生会话数量；
- Vault 会话数量；
- 最近备份；
- 备份失败；
- 健康警告；
- 可修复会话；
- 存储占用；
- 最近使用量；
- AI 分析任务。

## 9.2 会话浏览

支持：

- 按 Provider；
- 按项目；
- 按机器；
- 按来源；
- 按日期；
- 按标签；
- 按健康状态；
- 按模型；
- 按是否已备份；
- 按是否可恢复。

## 9.3 会话详情

展示：

- 用户消息；
- 助手消息；
- 推理内容；
- 工具调用；
- 命令；
- 文件路径；
- Diff；
- Token；
- 模型；
- Git 信息；
- 原始文件位置；
- Vault 文件位置；
- 版本记录；
- 健康报告；
- 恢复命令。

## 9.4 任务中心

统一显示：

```text
备份
校验
Doctor
Repair
Restore
Export
Handoff
AI Analyze
```

任务支持：

- 排队；
- 运行；
- 成功；
- 部分成功；
- 失败；
- 取消；
- 查看日志；
- 打开报告目录。

---

## 10. Vault Core 接入协议

## 10.1 初期方案：Tauri Sidecar

将 Python 核心打包为：

```text
vault-core.exe
vault-core
```

Tauri 启动子进程。

## 10.2 命令

```text
list-apps
inspect
layout
sync
verify
restore
doctor
repair-plan
repair-apply
repair-rollback
handoff-export
handoff-inspect
handoff-import
export
```

## 10.3 JSONL 事件

标准输出只输出 JSONL：

```json
{"type":"task_started","task_id":"...","operation":"sync"}
{"type":"progress","current":12,"total":100,"message":"Hashing sessions"}
{"type":"warning","code":"SOURCE_UNSTABLE","message":"..."}
{"type":"artifact","kind":"report","path":"..."}
{"type":"task_completed","ok":true,"summary":{}}
```

标准错误用于诊断，不用于机器协议。

## 10.4 错误代码

统一：

```text
VAULT_NOT_FOUND
VAULT_MARKER_INVALID
SOURCE_NOT_FOUND
SOURCE_UNSTABLE
HASH_MISMATCH
SQLITE_CHECK_FAILED
PARSE_FAILED
CAPABILITY_UNSUPPORTED
HEALTH_BROKEN
REPAIR_PLAN_STALE
RESTORE_TARGET_EXISTS
HANDOFF_SECRET_BLOCKED
AI_PROVIDER_DISABLED
```

## 10.5 Sidecar 安全

- 所有文件路径必须绝对化；
- 阻止 `..` 路径穿越；
- 目标必须在允许根目录；
- 修复只对带标记的副本执行；
- 恢复目录必须不存在；
- 任务中断清理 staging；
- 不允许 UI 传入任意 shell 命令。

## 10.6 后续 Rust 迁移

优先迁移高频、稳定模块：

- 哈希；
- 文件扫描；
- Catalog；
- 任务事件；
- Provider 共用数据结构。

保留 Python：

- 高风险 Repair；
- 快速变化的厂商恢复；
- Handoff 规则；
- 原型功能。

迁移不是首个版本前置条件。

---

## 11. 会话管理和修改

## 11.1 Vault 自有管理

所有 Provider 都支持：

- 自定义标题；
- 标签；
- 备注；
- 收藏；
- 固定；
- 自定义项目；
- 隐藏；
- 软删除；
- 清理保护。

这些只写入 `app.db`，不改厂商文件。

## 11.2 原生修改

### Codex

优先复用和审计 CCHV 已有能力：

- 原生标题修改；
- 归档；
- 删除。

增加：

- 修改前状态数据库快照；
- SQLite 锁检查；
- Diff/影响预览；
- 回读验证；
- 操作审计；
- 从备份恢复。

### 其他 Provider

逐个验证，不统一猜测：

- Claude Code；
- Gemini CLI；
- Qwen Code；
- Kimi；
- OpenCode；
- Goose。

## 11.3 删除策略

默认：

```text
隐藏
→ Vault 回收站
→ 系统回收站
→ 永久删除
```

永久删除必须二次确认，并显示：

- 原生文件；
- Vault 版本；
- 索引；
- 恢复能力；
- 是否还有其他副本。

---

## 12. 备份、校验和恢复

## 12.1 备份入口

UI 支持：

- 全部 Provider；
- 单 Provider；
- 单项目；
- 单会话；
- 当前电脑；
- 指定机器 ID；
- 手动选择 Vault；
- Dry-run。

## 12.2 可靠性增强

新增：

- 备份前磁盘空间检查；
- 移动硬盘断开检测；
- 中断后续传；
- 文件稳定窗口；
- 活跃会话尾部二次读取；
- 长任务 checkpoint；
- 失败重试但不无限重试；
- 上次成功水位线；
- 报告对比；
- Vault 版本升级预检。

## 12.3 校验

三级校验：

### 快速

- 文件存在；
- size；
- mtime；
- manifest。

### 标准

- SHA-256；
- SQLite quick_check；
- manifest 引用。

### 深度

- transcript 可解析；
- Session ID 一致；
- 索引对应；
- Provider Doctor；
- 恢复预检。

## 12.4 恢复中心

展示：

- 可恢复 Provider；
- 恢复范围；
- 原生恢复；
- 隔离恢复；
- 只读恢复；
- 恢复目标；
- 需要重新登录；
- 路径映射；
- 恢复报告。

Codex 保留当前隔离恢复为第一优先。

---

## 13. 健康检查和修复

## 13.1 Doctor 架构

```text
Common Checks
Provider Checks
Index Checks
SQLite Checks
Restore Readiness
```

## 13.2 通用检查

- 文件不可读；
- JSON/JSONL 解析错误；
- 突然截短；
- 空文件；
- Session ID 不一致；
- 重复内容；
- 时间戳异常；
- manifest 缺项；
- hash 不匹配；
- Vault 路径逃逸；
- SQLite 损坏；
- index 指向不存在文件。

## 13.3 Claude 检查

- `parentUuid` 断链；
- 重复 message UUID；
- 不连通消息树；
- tool use 缺少 result；
- `sessions-index.json` 缺失或过期；
- 会话存在但 resume 列表不可见。

## 13.4 Codex 检查

- rollout 命名不合法；
- session meta 缺失；
- rollout 与 threads 表不一致；
- active/archive 状态不一致；
- 旧绝对路径；
- backfill 状态异常；
- SQLite 无法读取；
- JSONL 存在但数据库记录缺失。

## 13.5 修复类型

```text
report_only
copy_repair
index_rebuild
state_rebuild
native_patch
quarantine
```

默认只报告。

## 13.6 Repair Plan

包含：

- 问题；
- 证据；
- 严重程度；
- 建议；
- 将修改的文件；
- 旧哈希；
- 新预期；
- 是否可回滚；
- 需要的 Provider 能力；
- 风险说明。

## 13.7 回滚

每次 apply 生成：

```text
repairs/<repair-id>/
├── plan.json
├── before/
├── after/
├── validation.json
├── audit.json
└── rollback.json
```

---

## 14. 跨电脑交接

## 14.1 格式

```text
<session-id>.asvpack
```

本质可为 ZIP，但扩展名独立。

## 14.2 包结构

```text
manifest.json
sessions/
metadata/
integrity.json
path-map.json
environment.json
redaction-report.json
git-context.json
README.md
```

## 14.3 导出流程

```text
选择会话
→ 检查完整性
→ 扫描敏感信息
→ 选择脱敏规则
→ 生成路径映射
→ 生成包
→ 二次校验
```

## 14.4 导入流程

```text
读取包
→ 校验 hash
→ 检查 Provider
→ 检查版本
→ 目标路径预检
→ 显示导入计划
→ 原生恢复或只读导入
→ 验证
```

## 14.5 降级策略

无法原生恢复时：

- 仍可导入 Vault；
- 仍可查看；
- 仍可搜索；
- 仍可导出；
- 明确标注“不可在厂商工具中继续”。

## 14.6 环境信息

交接包可包含非敏感信息：

- OS；
- 工作目录占位符；
- Git remote；
- branch；
- commit；
- 模型；
- Provider 版本；
- 必要恢复说明。

不默认包含项目源码。

---

## 15. 搜索、查看和导出

## 15.1 搜索

直接复用 CCHV 全局搜索，扩展来源过滤：

```text
live
vault
recovery
handoff
```

过滤项：

- Provider；
- 项目；
- 机器；
- 日期；
- 模型；
- 标签；
- 工具；
- 文件路径；
- 错误；
- 健康状态；
- 是否已备份；
- 是否可恢复。

## 15.2 Vault 搜索接入

两步实现：

### 首期

把 Vault 机器目录作为只读 Provider Root 交给现有 Rust Provider。

### 后期

为超大 Vault 增加持久化 SQLite FTS5，但不替换原始文件。

## 15.3 查看体验

- 长会话虚拟滚动；
- 消息目录；
- 工具调用折叠；
- 代码高亮；
- Diff；
- 搜索命中跳转；
- 原始 JSON 查看；
- 原始文件打开；
- 版本切换；
- 来源标记；
- 健康问题定位。

## 15.4 导出预设

### Clean Chat

只保留：

- 用户；
- 助手；
- 必要代码。

### Technical Audit

保留：

- 工具；
- 命令；
- 错误；
- 文件；
- Token；
- 时间戳。

### Last N Turns

只导出最近 N 回合。

### Full Raw

包含原始结构和元数据。

### Project Handoff

包含：

- 摘要；
- 决策；
- 待办；
- 关键命令；
- 关键文件；
- Git 上下文。

## 15.5 输出格式

- Markdown；
- HTML；
- JSON；
- PDF；
- `.asvpack`。

PDF 初期可由 HTML 打印生成。

---

## 16. 使用量统计

## 16.1 数据字段

```text
input_tokens
output_tokens
reasoning_tokens
cache_creation_tokens
cache_read_tokens
total_tokens
cost_actual
cost_estimated
currency
model
provider
session
project
machine
timestamp
quality
```

## 16.2 数据质量

每个值标记：

```text
actual
provider_reported
derived
estimated
unknown
```

不得把估算成本展示成实际扣费。

## 16.3 统计页面

- 今日；
- 本周；
- 本月；
- 时间范围；
- Provider；
- 模型；
- 项目；
- 会话；
- 机器；
- 缓存命中；
- 最长会话；
- Token 消耗最高会话；
- 估算 API 等价成本。

## 16.4 价格表

- 内置版本化价格表；
- 支持本地更新；
- 记录价格生效日期；
- 支持用户覆盖；
- 离线可用；
- 无价格时显示 unknown。

---

## 17. AI 分析

## 17.1 Provider

支持：

- Ollama；
- OpenAI 兼容 API；
- 用户自定义 endpoint；
- 禁用 AI；
- 将来可增加本地嵌入模型。

## 17.2 隐私模式

```text
Local Only
Redacted Remote
Full Remote
Disabled
```

默认：

```text
Local Only 或 Disabled
```

## 17.3 分析产物

- 会话摘要；
- 技术决策；
- 待办；
- 问题与解决方案；
- 修改文件总结；
- 命令清单；
- 风险；
- 未解决问题；
- 项目交接摘要；
- 可复用提示词；
- 相似会话。

## 17.4 引用要求

每个结论必须尽量带：

- session ID；
- message ID；
- 时间；
- 原文片段位置；
- 点击跳转。

AI 结论不能覆盖原消息。

## 17.5 增量分析

- 以最后分析消息位置为水位线；
- 活跃会话只分析新增内容；
- Prompt 和模型版本进入缓存 key；
- 允许重新分析；
- 旧分析保留版本。

## 17.6 成本控制

- 预估 Token；
- 限制最大输入；
- 分块；
- 汇总树；
- 缓存；
- 用户预算；
- 超预算前确认。

---

## 18. UI 信息架构

```text
总览
会话
搜索
Vault
├── 备份
├── 校验
├── 机器
├── 版本
└── 存储
健康中心
├── Doctor
├── 修复计划
├── 修复记录
└── 回滚
恢复中心
交接
导出
统计
AI 分析
任务中心
设置
关于
```

## 18.1 总览卡片

- Provider 状态；
- 上次备份；
- Vault 容量；
- 健康问题；
- 最近恢复；
- 今日 Token；
- 失败任务。

## 18.2 会话操作栏

安全操作优先顺序：

```text
收藏
标签
备注
导出
备份
Doctor
交接
恢复
原生修改
删除
```

## 18.3 健康状态

```text
Healthy
Warning
Broken
Repairable
Unsupported
Unknown
```

## 18.4 危险操作

危险按钮必须：

- 使用明确动词；
- 显示影响文件；
- 显示是否可回滚；
- 显示来源；
- 需要确认；
- 默认提供 dry-run。

---

## 19. 数据模型

## 19.1 Provider Capability

```json
{
  "provider_id": "codex",
  "can_read": true,
  "can_search": true,
  "can_export": true,
  "can_backup": true,
  "can_verify": true,
  "can_doctor": true,
  "can_repair": true,
  "can_rename_native": true,
  "can_restore_single": true,
  "can_restore_full": true
}
```

## 19.2 SessionRef

```json
{
  "provider_id": "codex",
  "native_session_id": "uuid",
  "machine_id": "leon-windows-main",
  "source_kind": "live",
  "source_root": "C:/Users/.../.codex",
  "native_path": "sessions/...",
  "vault_path": null
}
```

## 19.3 App Metadata

```json
{
  "session_key": "codex:machine:uuid",
  "custom_title": "修复登录问题",
  "tags": ["auth", "important"],
  "note": "继续检查 refresh token",
  "favorite": true,
  "pinned": true,
  "hidden": false,
  "protected_from_cleanup": true
}
```

## 19.4 HealthFinding

```json
{
  "finding_id": "uuid",
  "session_key": "codex:machine:uuid",
  "check_id": "codex.rollout_db_parity",
  "severity": "warning",
  "summary": "rollout exists but DB row is missing",
  "evidence": [],
  "repairable": true,
  "repair_action": "state_rebuild"
}
```

## 19.5 Task

```json
{
  "task_id": "uuid",
  "operation": "sync",
  "status": "running",
  "progress": 0.42,
  "started_at": "...",
  "report_path": null,
  "error_code": null
}
```

---

## 20. 测试与验收

## 20.1 本地测试

### Python Core

```bash
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
```

### Desktop

```bash
pnpm install
pnpm lint
pnpm test
pnpm build
cargo fmt --manifest-path src-tauri/Cargo.toml -- --check
cargo test --manifest-path src-tauri/Cargo.toml
cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets --all-features -- -D warnings
pnpm tauri build
```

根据本地环境选择必要命令，不要求每次开发都打安装包。

## 20.2 无 Actions

- 不创建 `.github/workflows/`；
- 不从上游带入 Workflow；
- 不运行或重跑 Workflow；
- PR 只记录本地测试结果；
- 未执行的测试明确说明；
- 不伪造通过状态。

## 20.3 Fixture

每个 Provider 至少包含匿名样本：

- 正常；
- 活跃增长；
- 归档；
- 尾部损坏；
- 重复 ID；
- 索引缺失；
- 旧版本；
- Windows 路径；
- Linux 路径；
- SQLite WAL。

## 20.4 集成测试

- 原生 Provider 浏览；
- Vault Provider 浏览；
- 搜索；
- 增量备份；
- 重复备份；
- 冲突；
- 验证；
- Doctor；
- Repair dry-run；
- Repair apply；
- 回滚；
- Codex 恢复；
- Handoff 导出/导入；
- 导出；
- AI 隐私阻断。

## 20.5 安全测试

- 路径穿越；
- symlink/junction 逃逸；
- 非空恢复目录；
- Vault marker 错误；
- hash 篡改；
- SQLite 锁；
- 移动盘中断；
- Sidecar 被取消；
- 敏感信息检测；
- 危险命令注入。

---

## 21. 五阶段开发计划

## 阶段 0：开源底座导入与基线稳定

### 目标

建立可持续维护的桌面 Fork，并确认本地 Windows 构建链路。

### 交付

- 创建 CCHV Fork；
- 固定上游版本和提交；
- 保留 MIT 许可证；
- 新增第三方声明；
- 删除 GitHub Actions Workflow；
- 修改产品名、应用 ID、图标占位和数据目录；
- 默认简体中文；
- 检查并关闭非必要网络请求；
- 本地运行前端、Rust 测试和 Tauri 构建；
- 记录上游同步流程；
- 建立 Sidecar 最小调用 Demo。

### 验收

- Windows 可本地启动；
- 能浏览现有会话；
- 中文可用；
- 不与原 CCHV 数据目录冲突；
- 仓库没有 Workflow；
- 能调用 `vault-core list-apps` 并显示 JSON 结果。

### 风险

- 上游已有功能较多，改品牌时避免大范围重构；
- 首期不重写 Provider；
- 不立即迁移 Python 到 Rust。

---

## 阶段 1：接入备份、校验和 Codex 恢复

### 目标

让现有 Vault Core 成为桌面软件中的可靠备份引擎。

### 交付

- Vault 路径选择；
- machine ID 设置；
- Provider 到 Python Adapter 映射；
- inspect；
- dry-run；
- sync；
- verify；
- 任务进度；
- 报告查看；
- 移动硬盘不可用提示；
- Codex 单会话恢复；
- Codex 整库恢复；
- 恢复启动脚本；
- Vault 会话作为只读来源显示。

### 验收

- 用户不使用命令行即可备份；
- 备份不会移动或删除源文件；
- 验证失败有明确报告；
- Codex 恢复不覆盖当前 `.codex`；
- 任务中断不留下已发布半成品；
- UI 能区分 live 和 vault。

---

## 阶段 2：健康检查、安全修复和会话管理增强

### 目标

从“备份查看器”升级为“会话保险箱”。

### 交付

- Vault 标题、标签、备注、收藏、固定；
- Provider 能力声明；
- 健康中心；
- 通用 Doctor；
- Claude Doctor；
- Codex Doctor；
- Repair Plan；
- Dry-run；
- 修复副本；
- Diff/影响预览；
- apply；
- 回读验证；
- rollback；
- 审计日志；
- Codex 原生重命名安全增强；
- 软删除和回收站。

### 验收

- 默认 Doctor 不改文件；
- 所有修复有计划；
- 所有原生修改有备份；
- 修复失败可以回滚；
- 不支持 Provider 的按钮被禁用；
- 用户能看到具体问题、证据和处理结果。

---

## 阶段 3：导出、交接和 Vault 搜索增强

### 目标

让会话可读、可带走、可在新电脑接续。

### 交付

- Markdown；
- HTML；
- JSON；
- PDF；
- 导出预设；
- 敏感信息扫描；
- `.asvpack`；
- Handoff 预检；
- path-map；
- integrity；
- 只读导入；
- Codex 原生交接；
- Vault 大规模搜索；
- 来源、机器、版本筛选；
- 导入导出审计。

### 验收

- 同一会话导出稳定可重复；
- 交接包被篡改时阻止导入；
- 检测到敏感信息时默认阻止；
- 新电脑没有原生支持时仍可只读查看；
- Codex 支持交接后隔离继续；
- 导出不会修改原始会话。

---

## 阶段 4：统一统计、AI 分析和产品化完善

### 目标

补齐统计和知识复用能力，形成日常软件。

### 交付

- 统一 Usage 模型；
- actual / estimated 标签；
- 价格表；
- Provider/模型/项目/会话统计；
- Ollama；
- OpenAI 兼容 API；
- 隐私模式；
- 摘要；
- 决策；
- 待办；
- 问题解决；
- 项目交接摘要；
- 引用跳转；
- 增量分析；
- 分析缓存；
- 成本预算；
- 设置迁移；
- 便携版 Windows 构建；
- 安装包本地构建说明。

### 验收

- 统计口径可追踪；
- 无数据时不伪造；
- AI 默认不发送到外部；
- 远程分析前显示将发送的范围；
- AI 输出能跳回来源；
- 删除派生分析不影响原会话；
- 软件离线仍能浏览、搜索、备份和恢复。

---

## 22. 首个可用版本

首个真正可日常使用版本由 **阶段 0 + 阶段 1 + 阶段 2 的基础部分**组成：

```text
成熟桌面界面
+ 多工具会话查看
+ 全局搜索
+ 基础统计
+ 增量备份
+ 完整性校验
+ Vault 来源查看
+ 标题/标签/备注
+ 基础 Doctor
+ Codex 隔离恢复
+ Markdown/HTML 导出
```

首版暂不强制：

- 所有 Provider 修复；
- 所有 Provider 原生恢复；
- 完整 AI 分析；
- PDF 精排；
- 云端同步；
- 团队功能。

---

## 23. 风险与控制

## 23.1 上游漂移

风险：

- Provider 结构变更；
- Tauri 配置变更；
- React 状态结构变更；
- 上游 UI 大改。

控制：

- 固定基准提交；
- 减少侵入式修改；
- 我们的功能放独立模块；
- 记录 upstream patch；
- 每次同步手动验证。

## 23.2 双解析体系

风险：

- Rust Provider 和 Python Adapter 对路径或 ID 定义不同。

控制：

- 建立 Provider/Adapter 映射契约；
- 共享匿名 Fixture；
- 同一 Fixture 对比结果；
- Rust 负责读取展示；
- Python 负责备份和恢复；
- 不让两套代码都修改原生数据。

## 23.3 Sidecar 打包

风险：

- Python 运行时体积；
- 杀毒软件误报；
- 路径和权限；
- 跨平台差异。

控制：

- 首先支持 Windows x64；
- Sidecar 版本握手；
- 独立日志；
- 便携目录；
- 无 shell 拼接；
- 后续逐步 Rust 化。

## 23.4 厂商格式变化

控制：

- Provider 健康状态；
- schema/version 探测；
- 不支持时只读降级；
- 不猜测写入；
- Fixture 回归；
- 修复能力默认关闭。

## 23.5 许可证

控制：

- CCHV MIT 声明；
- ccusage MIT 声明；
- 不复制 Codex Manager GPL 代码；
- `THIRD_PARTY_NOTICES.md`；
- 发布前许可证扫描。

## 23.6 数据破坏

控制：

- 默认只读；
- Dry-run；
- staging；
- 原子发布；
- before snapshot；
- rollback；
- hash；
- 审计；
- 真实用户目录禁止用于破坏性测试。

---

## 24. Definition of Done

一个功能只有满足以下条件才算完成：

- 明确当前支持范围；
- 明确不支持范围；
- 不破坏原始会话；
- 有中断和失败处理；
- 有本地可重复测试；
- 危险操作支持 dry-run；
- 有结果验证；
- 有用户可读报告；
- 有 UI 错误提示；
- 有文档；
- 有许可证检查；
- 没有擅自新增或触发 GitHub Actions。

Provider 相关能力还必须：

- 有官方源码或文档证据；
- 有匿名化 Fixture；
- 有 Windows/Linux 路径测试；
- 不复制凭据；
- 不把实验性路径称为稳定；
- 原生修改和恢复必须单独能力门控。

---

## 25. 下一步

下一次代码开发从 **阶段 0** 开始：

1. 创建桌面 Fork；
2. 固定 CCHV v1.22.0 基线；
3. 删除上游 Workflows；
4. 保留许可证并增加第三方声明；
5. 本地跑通 Windows Tauri；
6. 修改应用名和数据目录；
7. 添加 Vault Core Sidecar 最小调用；
8. 在设置页显示 Core 版本和适配器列表；
9. 保存本地测试结果；
10. 不进行 GitHub Actions 远端构建。

在阶段 0 验收通过前，不应同时开发 Doctor、Repair、Handoff 和 AI，以免底座和接口尚未稳定时产生大量返工。
