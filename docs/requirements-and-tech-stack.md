# CandyProject — 需求分析 & 技术栈选型

> **原始描述**
> 给项目管理加一层工具糖，适配各种已有的版本库 GIT/SVN 等，它的主体是 SVN 或者 GIT 仓库管理项目任务，外层使用 react/py 技术进行汇总分析，提示完成项目管理，保障了用户针对任务的专注，同时保障了管理方对格式化文库归档需求，满足信息汇合需要。

---

## 一、项目定位

**CandyProject** 是一个版本库原生的项目管理"语法糖"工具。

它不替代现有 VCS（版本控制系统），而是在 Git / SVN 之上叠加一层轻量的任务语义与管理视图：

```
┌────────────────────────────────────────┐
│         管理层  (React + Python)        │  ← 汇总、分析、归档、报告
├────────────────────────────────────────┤
│         适配层  (VCS Adapter)           │  ← Git / SVN / 可扩展
├───────────────────┬────────────────────┤
│    Git Repo(s)    │    SVN Repo(s)     │  ← 任务的真实载体
└───────────────────┴────────────────────┘
```

**核心价值**
- 开发者：不改变 Git/SVN 工作习惯，任务就在 commit/branch/tag 里
- 管理者：获得格式化报告、多仓库聚合视图、归档输出，无需侵入代码库

---

## 二、需求还原

### 2.1 核心概念映射

| VCS 原生概念 | CandyProject 任务语义 |
|---|---|
| Branch | 任务 / Feature |
| Commit message | 任务进展记录 |
| Tag / Release | 里程碑 |
| Merge / PR | 任务完成交付 |
| SVN path (trunk/branches/tags) | 同上映射 |
| Commit author + timestamp | 责任人 + 时间线 |

### 2.2 功能需求

#### F1 · VCS 适配层
- 支持 Git（本地 / 远程：GitHub、GitLab、Gitea、Bitbucket）
- 支持 SVN（本地 / 远程 svnserve / HTTP）
- 统一抽象接口：`list_tasks()` / `get_task_detail()` / `add_progress()`
- 扩展点：预留 Mercurial、Perforce 接口

#### F2 · 任务管理（用户侧）
- 从 VCS 元数据自动提取任务列表（branch 名称解析规则可配置）
- 支持在 commit message 中嵌入任务标记（`[TASK-001]` 等约定）
- 任务状态自动推断（进行中 / 已合并 / 已标记 / 已归档）
- CLI 命令：`candy task list / new / done / log`
- 不强制额外数据库，优先零侵入（元数据存 VCS 本身）

#### F3 · 汇总分析（管理侧）
- 多仓库 / 多项目聚合看板（Web UI）
- 任务燃尽图、提交热力图、成员贡献统计
- 里程碑进度追踪
- 可配置的数据刷新策略（Webhook / 定时拉取）

#### F4 · 格式化归档
- 一键导出：Markdown / PDF / HTML 报告
- 周报 / 月报 / 里程碑报告模板
- 归档包含：任务列表、提交记录摘要、责任人、时间轴
- 支持自定义模板（Jinja2）

#### F5 · 通知与提示
- 检测长期未更新任务并提醒（超期预警）
- Commit message 格式校验（pre-commit hook 辅助）
- 可集成 Webhook 推送（企业微信 / 钉钉 / Slack）

### 2.3 非功能需求

| 维度 | 要求 |
|---|---|
| 零侵入 | 不修改现有 VCS 仓库结构，仓库在没有 Candy 时仍完整可用 |
| 轻量部署 | 单机可用（SQLite + 本地文件），无强制依赖云服务 |
| 可扩展 | VCS 适配器、报告模板、通知渠道均为插件式 |
| 安全 | VCS 凭据本地加密存储，不上传第三方 |
| 多平台 | CLI 跨平台（Linux / macOS / Windows），Web UI 兼容主流浏览器 |

---

## 三、技术栈选型

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────┐
│  Web UI  (React + TypeScript)                        │
│  · 看板 · 统计图表 · 报告预览 · 配置管理             │
└──────────────────┬──────────────────────────────────┘
                   │ REST / WebSocket
┌──────────────────▼──────────────────────────────────┐
│  API Server  (Python · FastAPI)                      │
│  · 任务聚合服务  · 报告生成  · 通知发送              │
├──────────────────────────────────────────────────────┤
│  VCS Adapter Layer  (Python)                         │
│  · GitAdapter (GitPython / pygit2)                   │
│  · SVNAdapter (svn / subprocess + svn CLI)           │
│  · BaseAdapter (抽象接口)                            │
├──────────────────────────────────────────────────────┤
│  Storage                                             │
│  · SQLite（单机）/ PostgreSQL（团队部署）             │
│  · 文件系统（归档包 / 模板）                          │
└──────────────────────────────────────────────────────┘

CLI Tool  (Python · Typer)  — 可独立运行，不依赖 Web 服务
```

### 3.2 前端

| 选型 | 库/框架 | 理由 |
|---|---|---|
| 框架 | **React 18 + TypeScript** | 原始描述指定；生态成熟，组件复用性强 |
| 构建 | **Vite** | 快速 HMR，开发体验好 |
| UI 组件 | **Ant Design 5** | 管理后台场景成熟，表格/图表/表单开箱即用 |
| 图表 | **ECharts（echarts-for-react）** | 燃尽图、热力图、贡献统计 |
| 状态管理 | **Zustand** | 轻量，适合中小规模状态 |
| 路由 | **React Router v6** | 标准选择 |
| 请求 | **TanStack Query (React Query)** | 服务端状态缓存与同步 |

### 3.3 后端

| 选型 | 库/框架 | 理由 |
|---|---|---|
| 框架 | **FastAPI** | 原始描述指定 Python；异步支持好，自动 OpenAPI 文档 |
| VCS-Git | **GitPython** | 纯 Python，API 友好；复杂操作降级 `pygit2` |
| VCS-SVN | **svn（PyPI）+ subprocess** | SVN Python 绑定有限，subprocess 调用 svn CLI 最可靠 |
| 报告生成 | **Jinja2 + WeasyPrint / Pandoc** | 模板渲染 → HTML → PDF |
| 数据分析 | **Pandas** | 提交数据聚合、时间序列统计 |
| 任务调度 | **APScheduler** | 定时拉取 VCS 数据 |
| CLI | **Typer** | 基于 FastAPI 同作者，风格一致 |
| 配置 | **Pydantic v2 + python-dotenv** | 类型安全配置 |

### 3.4 存储

| 场景 | 选型 | 说明 |
|---|---|---|
| 单机 / 个人 | **SQLite** | 零配置，文件即数据库 |
| 团队部署 | **PostgreSQL** | 配置切换，同一 ORM |
| ORM | **SQLModel**（基于 SQLAlchemy + Pydantic）| 与 FastAPI 同生态，模型即 Schema |
| 缓存 | **Redis（可选）** | 多用户并发场景下缓存 VCS 扫描结果 |

### 3.5 部署

| 方式 | 方案 |
|---|---|
| 容器化 | Docker + Docker Compose（前后端 + DB 一键起） |
| 单机裸跑 | `uvicorn` + 静态文件托管，SQLite |
| CI 集成 | GitHub Actions / GitLab CI 中直接调用 `candy` CLI |

### 3.6 开发工具链

| 类型 | 工具 |
|---|---|
| Python 包管理 | **uv**（现代、快速）|
| 代码规范 | **Ruff**（lint + format）+ **mypy** |
| 前端规范 | **ESLint + Prettier** |
| 测试 | **pytest** + **pytest-asyncio** / **Vitest** |
| API 文档 | FastAPI 自动生成 `/docs` |

---

## 四、目录结构建议

```
CandyProject/
├── candy/                    # Python 包（核心）
│   ├── adapters/
│   │   ├── base.py           # 抽象适配器接口
│   │   ├── git_adapter.py    # Git 实现
│   │   └── svn_adapter.py    # SVN 实现
│   ├── api/                  # FastAPI 路由
│   ├── models/               # SQLModel 数据模型
│   ├── reports/              # 报告生成（模板 + 渲染）
│   ├── scheduler.py          # 定时任务
│   ├── cli.py                # Typer CLI 入口
│   └── main.py               # FastAPI app 入口
├── web/                      # React 前端
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── api/              # TanStack Query hooks
│   └── vite.config.ts
├── templates/                # Jinja2 报告模板
├── docs/                     # 文档
├── tests/
├── docker-compose.yml
├── pyproject.toml
└── LICENSE
```

---

## 五、关键设计决策

### 5.1 零侵入原则
Candy 读取 VCS 数据时只做只读操作（`git log`、`svn log`）。
任务标记约定通过 commit message 规范实现，仓库本身无任何额外文件。

### 5.2 本地优先
默认 SQLite，无需服务器。个人开发者 `pip install candy-pm` + `candy init` 即可使用。

### 5.3 适配器扩展点
```python
class BaseVCSAdapter(ABC):
    @abstractmethod
    def list_branches(self) -> list[Branch]: ...
    @abstractmethod
    def list_commits(self, since: datetime) -> list[Commit]: ...
    @abstractmethod
    def get_tags(self) -> list[Tag]: ...
```
新增 VCS 只需实现此接口，注册到适配器注册表即可。

### 5.4 Commit Message 约定（可配置）
```
[TASK-001] feat: 实现用户登录模块
[TASK-001][review] 修复登录态失效问题
[MILESTONE-1.0] release: 正式发布
```
正则规则可在 `candy.toml` 中自定义，适配已有团队规范。

---

## 六、阶段规划

| 阶段 | 目标 | 产出 |
|---|---|---|
| MVP | Git 适配 + CLI 任务列表 + Markdown 报告 | `candy init / task / report` |
| v0.2 | SVN 适配 + Web UI 看板 | 多仓库聚合视图 |
| v0.3 | 统计分析 + PDF 归档 + 超期预警 | 完整管理侧功能 |
| v1.0 | 多人协作 + Webhook + 插件 API | 团队部署就绪 |
