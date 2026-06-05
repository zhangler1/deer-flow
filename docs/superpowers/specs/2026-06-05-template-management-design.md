# 报告模板管理系统 — 设计文档

> 日期：2026-06-05
> 状态：已确认

---

## 1. 概述

支持用户上传自定义报告模板（docx），系统自动生成对应智能体节点提示词；并建设管理后台，对模板、工具、权限进行统一管理。

### 1.1 核心需求

| # | 需求 | 说明 |
|---|------|------|
| R1 | docx 上传自动生成提示词 | 上传报告模板 docx → LLM 一次性生成 coordinator/planner/researcher/reporter 四个节点提示词 + research_skills |
| R2 | docx 预览和下载 | 内置模板和用户上传模板均支持在线预览（mammoth 实时转 HTML）和下载原始 docx |
| R3 | 管理页面编辑提示词 | 管理员可查看、编辑所有模板的提示词 |
| R4 | 模板选择 + 权限 | 用户选择模板生成报告；公开模板所有人可用，私有模板仅 owner 可用 |
| R5 | 模板工具开关 | 管理页面为每个模板配置启用哪些 researcher 工具 |
| R6 | 全局工具参数 + 默认工具 | 工具管理页统一配置参数；可设置默认工具，新模板自动启用 |

### 1.2 前提条件

- 用户身份认证独立实现，通过 token 获取用户身份信息
- 管理员权限通过用户身份信息中的 admin 标记判断

---

## 2. 存储架构

```
┌──────────────────┐     ┌─────────────────┐
│   PostgreSQL      │     │   MinIO / S3     │
│                  │     │                  │
│  模板元数据       │     │  docx 原始文件    │
│  提示词 (JSONB)   │     │                  │
│  工具配置         │     │  templates/      │
│  权限状态         │     │    {id}.docx     │
│                  │     │                  │
└──────────────────┘     └─────────────────┘
```

- **PostgreSQL**：存储模板元数据、提示词（JSONB）、工具配置、权限状态、审批记录
- **MinIO/S3**：仅存储原始 docx 文件
- **预览**：不预生成 HTML，每次请求时用 mammoth 实时将 docx 转为 HTML 返回前端

---

## 3. 数据模型

### 3.1 表：`templates` — 模板主表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID PK | 唯一标识 |
| `name` | VARCHAR | 模板名称（允许同名，通过 ID 区分） |
| `description` | TEXT | 模板说明 |
| `category` | ENUM('builtin','user') | 内置 / 用户上传 |
| `owner_id` | UUID (可为空) | 上传者 ID，内置模板为 NULL |
| `docx_object_key` | VARCHAR | MinIO 中 docx 文件的 object key |
| `is_public` | BOOLEAN | 是否公开，默认 false |
| `approval_status` | ENUM('none','pending','approved','rejected') | 公开审批状态，默认 none |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 更新时间 |

### 3.2 表：`template_prompts` — 提示词表

一个模板一行，用 JSONB 存储所有提示词内容。

| 字段 | 类型 | 说明 |
|------|------|------|
| `template_id` | UUID PK/FK → templates.id | 所属模板 |
| `content` | JSONB | 所有节点提示词 + research_skills |

`content` 结构：

```json
{
  "coordinator": "你是...",
  "planner": "你需要...",
  "researcher": "你需要...",
  "reporter": "你需要...",
  "research_skills": [
    { "name": "企业基本信息", "prompt": "搜索该企业的基本信息..." },
    { "name": "财务数据分析", "prompt": "分析该企业的财报数据..." }
  ]
}
```

### 3.3 表：`template_tool_configs` — 模板工具开关

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | SERIAL PK | 自增 |
| `template_id` | UUID FK → templates.id | 所属模板 |
| `tool_name` | VARCHAR | 工具名称 |
| `enabled` | BOOLEAN | 是否启用 |

联合唯一约束：`(template_id, tool_name)`

### 3.4 表：`global_tool_params` — 全局工具参数

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | SERIAL PK | 自增 |
| `tool_name` | VARCHAR UNIQUE | 工具名称 |
| `display_name` | VARCHAR | 前端显示名称 |
| `params` | JSONB | 工具参数配置 |
| `is_default` | BOOLEAN | 是否默认工具（新模板自动启用） |
| `description` | TEXT | 工具说明 |

`params` 示例：`{"max_results": 10, "timeout_seconds": 30, "region": "cn"}`

---

## 4. 核心流程

### 4.1 docx 上传 → 自动生成提示词

```
用户上传 docx
     ↓
服务端保存到 MinIO（object_key = "templates/{uuid}.docx"）
templates 表写入记录（status=generating）
     ↓
mammoth 提取 docx 文本内容（保留章节标题层级）
     ↓
构造 LLM Prompt：
  - 角色：报告模板分析专家
  - 任务：分析报告模板结构，生成 coordinator/planner/researcher/reporter 提示词和 research_skills
  - 输入：mammoth 提取的文档文本
  - 输出格式：严格 JSON Schema
  - Few-shot：提供现有对公营销报告的提示词作为示例
     ↓
LLM 返回 JSON → 写入 template_prompts 表
     ↓
初始化 template_tool_configs（对所有 is_default=true 的工具 → enabled=true）
     ↓
templates 表状态置为 ready → 前端通知用户完成
```

失败处理：LLM 调用或解析失败时标记 failed，提示用户重新上传。

### 4.2 docx 预览和下载

**预览**（实时转换，不预生成）：

```
前端请求 GET /api/templates/{id}/preview
     ↓
服务端从 MinIO 获取 docx 字节流
     ↓
python-mammoth 实时转为 HTML
     ↓
返回 HTML → 前端渲染（iframe 或 WebView）
```

**下载**：

```
前端请求 GET /api/templates/{id}/download
     ↓
服务端生成 MinIO 预签名 URL
     ↓
302 重定向到预签名 URL → 浏览器触发下载
```

### 4.3 模板选择 + 权限 + 审批

#### 模板市场页面（模板选择器）

模板市场作为研究的入口页面，卡片式展示所有可用模板。

**页面结构：**

```
┌─────────────────────────────────────────────────────────┐
│  📋 模板市场                                [+ 上传模板]  │
│                                                         │
│  [公开模板]  [我的私有模板]    🔍 [搜索模板名称或ID...]    │
│                                                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────┐  │
│  │           👁[预览]│           👁[预览]│       👁[预览]│  │
│  │                 │ │                 │ │              │  │
│  │  学术报告        │ │ 对公营销报告     │ │ 行业研究报告  │  │
│  │  ID: a1b2c3d4   │ │  ID: e5f6g7h8  │ │  ID: i9j0k1l2│  │
│  │                 │ │                 │ │              │  │
│  │  通用学术研究     │ │ 银行对公客户     │ │ 行业趋势与    │  │
│  │  结构化论证      │ │ 深度分析        │ │ 竞争格局分析  │  │
│  │                 │ │                 │ │              │  │
│  └─────────────────┘ └─────────────────┘ └───────────┘  │
│                                                         │
│  ┌─────────────────┐ ┌─────────────────┐               │
│  │           👁[预览]│           👁[预览]│               │
│  │          [🗑删除] │                 │               │
│  │         [📤申请]  │                 │               │
│  │                 │ │                 │               │
│  │  新能源调研🔒     │ │ 汽车行业分析✓    │               │
│  │  ID: m2n3o4p5   │ │  ID: q6r7s8t9  │               │
│  │                 │ │                 │               │
│  │  新能源产业链     │ │ 汽车行业竞争     │               │
│  │  深度调研       │ │ 格局分析       │               │
│  │                 │ │                 │               │
│  └─────────────────┘ └─────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

**模板名称：** 允许同名（不同用户或同一用户可创建同名模板），通过 ID 区分。卡片上显示模板 ID（截取前 8 位）。

**搜索逻辑：**

| 搜索类型 | 匹配方式 | 说明 |
|----------|---------|------|
| 按名称搜索 | `WHERE name ILIKE '%{keyword}%'` | 模糊匹配，输入部分名称即可 |
| 按 ID 搜索 | `WHERE id::text LIKE '{keyword}%'` | 前缀匹配，输入卡片上展示的 8 位 ID 即可搜到 |
| 混合搜索 | `WHERE name ILIKE '%{keyword}%' OR id::text LIKE '{keyword}%'` | 同时按名称和 ID 搜索 |

搜索栏为空时展示全部。搜索在已选 Tab（公开/私有）范围内过滤。

**交互逻辑：**

| 点击位置 | 行为 |
|----------|------|
| 👁 预览按钮 | 打开预览面板（侧边抽屉），mammoth 实时渲染 docx 内容；面板内含 [下载] 按钮 |
| 🗑 删除按钮 | 二次确认弹窗：「确定删除模板『XXX』？此操作不可撤销」→ [取消] [确认删除] → 删除（仅自己的模板显示） |
| 📤 申请公开按钮 | 确认弹窗 → 提交公开申请（仅自己的私有模板显示，审批中时灰色不可点击） |
| 卡片其他任意位置 | **跳转到报告生成对话页，该模板已选中，用户直接输入问题即可开始研究** |

**顶部 Tab 切换：**
- 公开模板 Tab：内置模板 + 用户上传且审批通过的模板
- 我的私有模板 Tab：仅自己上传的私有模板

**跳转后对话页：**
```
┌─────────────────────────────────────────────────┐
│  📋 当前模板：对公营销报告  [切换模板 →]          │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │  请输入你的研究问题...                    │    │
│  └─────────────────────────────────────────┘    │
│                                       [发送]    │
└─────────────────────────────────────────────────┘
```
顶部显示当前模板名，点击 [切换模板 →] 返回模板市场重新选择。

选择模板后，`template_id` 传到后端，加载对应模板的提示词执行研究。

#### 审批流程

```
用户端                              管理端
------                              ------
「我的模板」列表中
每个私有模板旁有「申请公开」按钮
     ↓
点击 → 确认弹窗
     ↓
approval_status → pending
按钮变为「审批中...」
                                    管理页面 Tab3「审批管理」
                                    列表：pending 状态的模板
                                    [通过] → is_public=true, status=approved
                                    [拒绝] → status=rejected
                                      └ 可选填写拒绝原因

被拒绝后可重新申请
```

---

## 5. 前端页面

### 5.1 模板市场页面（模板选择入口）

作为 Deep Research 的入口页面，也是默认首页。

| 区域 | 内容 |
|------|------|
| 顶部 Tab | [公开模板] [我的私有模板] |
| 卡片列表 | 每个模板一张卡片：名称 + 简介 |
| 卡片右上角 | 👁 预览按钮（所有卡片均有） |
| 自己的模板卡片 | 额外显示 🗑 删除按钮 |
| 点击卡片主体 | 跳转对话页，模板已选中 |
| 上传按钮 | 右上角 [+ 上传模板] |

预览抽屉：mammoth 实时渲染 docx 内容 + [下载] 按钮。

### 5.2 对话页（带模板上下文）

从模板市场点击模板进入。顶部显示当前模板名 + [切换模板 →] 返回市场。

### 5.3 「我的模板」页面

已合并到模板市场的「我的私有模板」Tab 中。

| 功能 | 权限 |
|------|------|
| 上传 docx 创建新模板 | 所有用户 |
| 查看自己的模板列表（含审批状态） | 所有用户 |
| 删除自己的模板 | 所有用户 |
| 申请公开 | 所有用户 |
| 预览 / 下载 docx | 所有用户 |

### 5.3 管理后台（仅管理员）

#### Tab 1：模板管理

| 功能 | 说明 |
|------|------|
| 模板列表 | 模板名、类型（内置/用户）、拥有人、公开状态、审批状态 |
| 新增 | 管理员上传 docx 创建模板，触发自动生成提示词 |
| 编辑提示词 | 进入编辑器，分 tab 编辑 coordinator/planner/researcher/reporter 和 research_skills |
| 删除 | 二次确认弹窗 → 可删除任意模板（含内置） |
| 工具开关 | 在模板编辑页内，为该模板勾选启用哪些工具 |

#### Tab 2：工具管理

| 功能 | 说明 |
|------|------|
| 工具列表 | 工具名、显示名、参数(JSON)、是否默认工具 |
| 编辑参数 | 修改工具的全局参数配置（JSONB） |
| 设为默认 | 勾选后，用户上传新模板时自动启用该工具 |
| 🧪 测试工具 | 点击打开测试面板，输入工具方法入参，调用工具并展示返回值 |

> 工具由代码定义，不通过前端增删。Tab 2 仅管理参数和默认设置。

#### 工具测试功能

**流程：**

```
点击 🧪 测试按钮
     ↓
弹出测试面板（侧边抽屉或弹窗）
  ├── 展示该工具的全局参数（只读）
  ├── 输入框：填写方法入参（JSON 格式，如 {"query": "今天天气"}）
  └── [执行测试] 按钮
     ↓
POST /api/admin/tools/{tool_name}/test
  body: { "args": { "query": "今天天气" } }
     ↓
后端加载该工具的全局参数 + 用户传入的 args
     ↓
调用实际工具执行
     ↓
返回结果 → 前端展示（JSON 格式化或纯文本）
```

**API 新增：**

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/admin/tools/{name}/test` | POST | 调用工具并返回结果，body: `{"args": {...}}`

**调用示例（以 `online_search` 为例）：**

```
全局参数（global_tool_params.params）：
  { "max_results": 10, "timeout_seconds": 30 }

用户测试面板输入（方法入参）：
  { "query": "2024年AI行业发展趋势" }

后端合并调用：
  online_search(query="2024年AI行业发展趋势", max_results=10, timeout_seconds=30)

返回搜索结果 → 前端 JSON 格式化展示
```

#### Tab 3：审批管理

| 功能 | 说明 |
|------|------|
| 待审列表 | 模板名、申请人、申请时间 |
| 通过 | 模板变为公开（is_public=true, approval_status=approved） |
| 拒绝 | 可选填写拒绝原因（approval_status=rejected） |

---

## 6. API 设计要点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/templates` | GET | 当前用户可见的模板列表 |
| `/api/templates` | POST | 上传 docx 创建模板 |
| `/api/templates/{id}` | GET | 模板详情 |
| `/api/templates/{id}` | DELETE | 删除模板（owner 或 admin） |
| `/api/templates/{id}/preview` | GET | 实时 docx → HTML 预览 |
| `/api/templates/{id}/download` | GET | 下载原始 docx |
| `/api/templates/{id}/prompts` | PUT | 更新模板提示词（admin） |
| `/api/templates/{id}/apply-public` | POST | 申请公开 |
| `/api/admin/templates` | GET | 管理员查看所有模板 |
| `/api/admin/templates/{id}` | PUT | 管理员更新模板 |
| `/api/admin/templates/{id}` | DELETE | 管理员删除模板 |
| `/api/admin/approvals` | GET | 待审批列表 |
| `/api/admin/approvals/{id}` | POST | 审批（通过/拒绝） |
| `/api/admin/tools` | GET | 工具列表及参数 |
| `/api/admin/tools/{name}` | PUT | 更新工具参数/默认设置 |
| `/api/admin/templates/{id}/tool-configs` | PUT | 更新模板工具开关 |

---

## 7. 现有系统改造

### 7.1 后端改动

- `src/prompts/template.py`：不再从文件系统加载，改为从 DB + template_prompts 表加载
- `src/prompts/__init__.py`：`ReportStyle` 枚举改为动态（从 templates 表查询公开模板）
- `src/graph/types.py`：`State.report_style` 改为 `State.template_id`
- 现有内置模板 .md 文件 → 迁移脚本写入 DB（seed）

### 7.2 前端改动

- `report-style-dialog.tsx`：删除，不再需要
- 新增「模板市场」页面作为默认首页，包含公开/私有模板 Tab 切换
- 对话页顶部新增模板名显示 + 切换入口
- 新增「管理后台」页面（仅 admin 可见）
- 新增路由 + 权限守卫

---

## 8. 边界情况与错误处理

- docx 解析失败：提示「文件格式错误，请上传有效的 docx 文件」
- LLM 生成失败：标记模板状态为 failed，提示用户重新上传
- 文件过大：docx 限制 10MB（大于当前附件的 2MB，因为报告模板文件可能更大）
- 删除已被选择的模板：不影响正在进行的研究（已加载到 State 中的提示词不变）
- 内置模板前端不显示删除按钮（仅管理后台可删除内置模板）
- **所有删除操作均需二次确认弹窗**
