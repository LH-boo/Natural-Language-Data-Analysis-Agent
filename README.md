# 自然语言数据分析 Agent

面向业务人员的智能数据分析助手：上传 CSV 或连接数据库后，用中文自然语言提问，即可完成数据查询、统计分析与图表生成。

系统将用户问题转换为 SQL，在只读环境中经过安全校验后执行，并返回**分析结论、ECharts 图表、查询语句和数据依据**，支持连续追问、SQL 自动修复、异常提示与执行审计。

## 技术架构

| 层级 | 技术 |
|---|---|
| 前端展示层 | Vue 3 + Vite + Element Plus + ECharts |
| API 接口层 | FastAPI |
| Agent 编排层 | LangGraph（条件分支、SQL 修复、状态流转） |
| LLM 模型层 | DeepSeek / Qwen 等 OpenAI 兼容接口 |
| 数据处理层 | Pandas + DuckDB + SQLAlchemy + SQLGlot |
| 数据存储层 | SQLite（元数据）+ DuckDB（CSV 分析）+ Redis/MySQL（可选扩展） |

核心流程：

```text
用户提问
  -> 理解问题（多轮追问改写）
  -> 获取数据集 Schema
  -> LLM / 规则引擎生成 SQL
  -> SQLGlot 安全校验（单条 SELECT、表白名单、行数限制）
  -> DuckDB / 外部数据库只读执行
  -> 结果分析（基于真实数据）
  -> 生成 ECharts 图表
  -> 返回结论、SQL、数据明细
  -> 失败时最多自动修复 2 次
```

## 功能页面

1. 数据分析首页：数据集、分析任务、报告数量、近 7 天趋势
2. AI 智能分析：中文对话、连续追问、Agent 执行步骤、图表与数据明细
3. 数据集管理：CSV 上传、示例数据、删除、预览
4. 数据预览：字段类型、缺失值、唯一值、分页数据
5. 数据库连接：MySQL / PostgreSQL / SQLite，连接测试与 Schema 查看
6. SQL 查询管理：手工 SQL、安全校验、结果表格、执行日志
7. 数据可视化：选择维度、指标、聚合方式自动生成图表
8. 分析报告：报告列表、详情、CSV / JSON / HTML 导出
9. 历史会话：会话列表、消息回放、继续追问
10. 系统监控：LLM 配置、存储状态、SQL 日志、错误与拦截统计

另外提供全局 AI 小窗口，可在任意页面快速提问。

## 目录结构

```text
.
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置与环境变量
│   ├── api/                    # 数据集、数据库、对话、分析接口
│   ├── agent/                  # LangGraph 状态图、节点、Prompt、LLM 客户端
│   ├── services/               # CSV、数据库、Schema、SQL、分析、图表服务
│   ├── security/               # SQLGlot 安全校验
│   ├── models/                 # SQLAlchemy 元数据模型
│   ├── utils/                  # 日志与数据转换工具
│   ├── sample_data/sales.csv   # 示例销售数据
│   └── requirements.txt
├── frontend/
│   ├── src/views/              # 10 个中文页面
│   ├── src/components/         # 图表、统计卡片、AI 小窗口
│   ├── src/layouts/            # 侧边栏布局
│   └── package.json
└── README.md
```

## 快速启动

### 1. 启动后端

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

后端接口文档：http://127.0.0.1:8000/docs

首次启动会自动创建：

- `backend/data/metadata.db`：SQLite 元数据库
- `backend/data/analytics.duckdb`：CSV 分析库

### 2. 配置大模型（可选）

复制 `backend/.env.example` 为 `backend/.env`，填写：

```ini
LLM_API_KEY=你的密钥
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

不配置密钥也可以运行：系统会自动使用内置规则引擎完成常见的汇总、分组、排序、时间筛选、趋势查询和图表生成，便于本地演示。

### 3. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

打开 http://127.0.0.1:5173 ，在「数据集管理」中点击**加载示例数据**即可体验完整流程。

可尝试的问题：

- 统计最近三个月销售额最高的五个商品
- 按商品类别统计销售额占比
- 每个地区的订单数量是多少
- 只看前三个

## 安全设计

- 只允许单条 `SELECT`，拦截 INSERT / UPDATE / DELETE / DROP / ALTER 等操作
- SQLGlot 解析 AST，检查危险节点、敏感函数、多语句和系统表
- 数据表白名单校验，禁止访问未授权表
- 自动追加 `LIMIT`，限制单次返回行数
- DuckDB 查询超时中断，外部数据库建议使用只读账号
- 上传文件限制大小、编码与路径，查询结果统一序列化
- 全量 SQL 执行日志，记录安全性、耗时、结果行数和错误信息
- 分析结论只基于数据库真实返回结果，不允许模型编造数值

## 主要接口

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/dataset/upload` | POST | 上传 CSV |
| `/api/dataset/list` | GET | 数据集列表 |
| `/api/dataset/preview` | GET | 数据预览 |
| `/api/database/connect` | POST | 保存数据库连接 |
| `/api/database/schema` | GET | 获取表结构 |
| `/api/analysis/chat` | POST | 自然语言分析（核心） |
| `/api/analysis/sql` | POST | 手工执行 SQL |
| `/api/analysis/chart` | POST | 生成可视化图表 |
| `/api/analysis/reports` | GET | 分析报告列表 |
| `/api/analysis/export/{id}` | GET | 导出 CSV / JSON / HTML |
| `/api/analysis/conversations` | GET | 历史会话 |
| `/api/analysis/dashboard` | GET | 首页统计 |
| `/api/analysis/monitoring` | GET | 系统监控 |
