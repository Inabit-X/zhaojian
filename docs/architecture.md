# 架构说明（心理中心版 · 阶段 1）

## 1. 目标与边界

新版定位是**高校心理中心的临床文书与随访支持系统**，服务对象从「学生自助」转为「咨询师工作台 + 学生端（仅量表/问卷）」。

阶段 1 只换地基：

```text
学生账号 → 管理员开通咨询师 → 管理员建案并分配 → 咨询师/学生按归属查看 → 全程审计
```

明确不做：心理诊断、治疗决策、面向学生的 AI 对话、社区与匹配、模型训练/微调。咨询记录起草、摘要、检索、随访只留表设计与 TODO，不写伪实现。

## 2. 运行拓扑

```text
浏览器（Vue 3 + Vite + Pinia）
        │  /api
        ▼
Nginx / uvicorn（FastAPI，/api/v1）
        │
        ├── PostgreSQL 16 + pgvector（业务数据；阶段 3 起用向量）
        └── Redis + ARQ（compose profile `async`，可选；阶段 4 起用）
        │
        └── Provider（OpenAI 兼容，校内/内网；开发期 fake）
```

数据库端口在开发环境映射为 `15432`，API 为 `18080`（见根 `.env`），避免与本机其他服务冲突。

## 3. 分层

```text
HTTP 层   app/api/routes/*        参数校验、角色依赖、状态码
          app/api/deps.py         get_db / get_current_user / require_roles
业务层    app/services/*          事务边界、归属判定、审计写入
领域层    app/memory/chunking.py  通用切片（阶段 3 复用）
模型层    app/providers/*         Embedding / LLM 抽象（阶段 2-3 使用）
数据层    app/db/models/* + alembic/versions/*   SQLAlchemy 2.0 async + Alembic
          app/db/session.py       async engine / sessionmaker
```

约定：

- 路由不直接拼 SQL，统一走 service；service 接收 `AsyncSession`，负责 `commit`。
- 领域异常（`AppError` 子类）在 `app/main.py` 统一映射为顶层 `{code, message, details}`。
- 配置集中在 `app/core/config.py`（pydantic-settings），启动时校验关键不变量。
- 审计与业务写在同一事务：业务失败则审计不落库，避免「有日志无事实」。

## 4. 认证与角色

| 角色 | 产生方式 | 能力 |
| --- | --- | --- |
| `student` | 自助注册（邮箱/学号/手机号任一） | 查看自己的个案 |
| `counselor` | 管理员开通，不开放注册 | 查看分配给自己的个案 |
| `admin` | CLI `create-admin` | 开通咨询师、建案分配、查看聚合列表；**不读个案内容** |
| `auditor` | 数据库/运维创建（暂未开放接口） | 只读审计日志 |

JWT 载荷**不含角色**：每次请求查库取 `role`，角色变更即时生效，代价是一次主键查询。越权读个案统一 **404**，角色不匹配统一 **403**。

## 5. 关键链路

### 5.1 学生注册

```text
POST /auth/register
  → 校验 email/student_no/phone 至少一个 + privacy_accepted
  → 归一化（email lower、phone 去空格/连字符）
  → 查重（email/student_no/phone/username）
  → Argon2id 哈希
  → INSERT users（role 固定 student）
  → 直接签发 JWT
```

### 5.2 登录 / 鉴权

```text
POST /auth/login
  → identifier 可能是 email / student_no / phone
  → 一次查询 OR 匹配 + LIMIT 1
  → verify_password → create_access_token(sub=user.id)
受保护接口 → HTTPBearer → decode → 查 users → require_roles(...)
```

登录失败统一 401 `invalid_credentials`，不区分「账号不存在 / 密码错误」。

### 5.3 开通咨询师

```text
POST /admin/counselors（admin）
  → 邮箱/用户名查重（409）
  → 创建 role=counselor 的 users
  → 同事务写 audit_logs(action=counselor.create)
```

### 5.4 建案与查看

```text
POST /cases（admin）
  → student_identifier 必须命中 role=student（否则 404 student_not_found）
  → counselor_id 必须命中 role=counselor（否则 404 counselor_not_found）
  → INSERT cases + audit(case.create)

GET /cases、GET /cases/{id}（counselor/student）
  → counselor：counselor_id = 当前用户
  → student：student_id = 当前用户
  → 不匹配一律 404 case_not_found；成功写 audit(case.view)
```

## 6. 数据模型

```text
users 1 ──< cases >── 1 users
  │           （student_id / counselor_id）
  └──< audit_logs（actor_id，SET NULL）
```

| 表 | 关键字段 | 约束/索引 |
| --- | --- | --- |
| `users` | id(uuid)、email、student_no、phone、username、password_hash、role、created_at | email/student_no/phone/username 唯一且可空；`ck_users_role` 限定四角色 |
| `cases` | id、student_id、counselor_id、status、opened_at、closed_at、created_at、updated_at | FK→users（student RESTRICT / counselor SET NULL）；`ck_cases_status`；`(counselor_id, status)`、`(student_id)` |
| `audit_logs` | id(bigint)、actor_id、action、target_type、target_id、metadata(jsonb)、ip、created_at | FK→users SET NULL；`(actor_id, created_at DESC)`、`(action, created_at DESC)` |

`metadata` 列名在 ORM 中映射为 `meta` 属性，避免与 SQLAlchemy 的 `DeclarativeBase.metadata` 冲突。

### 迁移链

```text
0001 initial（users/events/event_chunks/agent_drafts）
0002 persona_todo（空迁移，历史占位）
0003 center_rbac（users 扩展 + cases + audit_logs）
0004 drop_legacy（DROP events/event_chunks/agent_drafts）
```

`0001`/`0002` 保留为历史，保证已有环境可顺序升级；`0004` 的 `downgrade` 只恢复空表结构，不恢复数据。

## 7. 权限矩阵

| 资源 / 动作 | student | counselor | admin | auditor |
| --- | --- | --- | --- | --- |
| 查看自己的个案 | ✅ | ✅（被分配） | ❌ 403 | ❌ 403 |
| 建案 / 分配 | ❌ | ❌ | ✅ | ❌ |
| 开通咨询师 | ❌ | ❌ | ✅ | ❌ |
| 咨询师列表（不含个案） | ❌ | ❌ | ✅ | ✅ |
| 审计日志 | ❌ | ❌ | ✅ | ✅（只读） |
| 个案内容 | 仅本人 | 仅本人负责 | ❌ | ❌ |

## 8. 审计

- 动作常量在 `app/core/constants.py`：`counselor.create`、`case.create`、`case.view`。
- `services/audit.py` 的 `record_audit()` 只 `add` 不 `commit`，由调用方与业务同事务提交。
- `metadata` 只写结构化、非自由文本字段（如 `student_id`、`counselor_id`），不写个案内容。
- 审计查询支持 `action` 过滤 + 分页，按 `created_at` 倒序。

## 9. 通用能力（保留，阶段 2-3 使用）

```python
class EmbeddingProvider(ABC):
    dim: int
    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]

class LLMProvider(ABC):
    async def complete(self, messages, *, temperature=0.7, max_tokens=None) -> str
```

- `FakeEmbeddingProvider`：确定性、离线、1536 维，供测试。
- `OpenAICompatEmbeddingProvider` / `OpenAICompatLLMProvider`：OpenAI 兼容协议，可指向校内网关。
- `app/memory/chunking.py`：按段落/标点切片，阶段 3 用于档案摘要的输入切分。

## 10. 关键决策

| 决策 | 理由 |
| --- | --- |
| 角色存库、JWT 不载角色 | 角色变更即时生效，避免旧 token 越权 |
| 咨询师不自助注册 | 临床角色需要机构背书，防止冒充 |
| 管理员不读个案内容 | 最小权限；聚合统计在阶段 4 以脱敏方式提供 |
| 越权 404、角色不符 403 | 前者防枚举资源，后者明确「角色不允许」 |
| 审计与业务同事务 | 审计不可脱离事实单独存在 |
| 旧业务表用迁移 DROP 而非保留 | 避免死代码与误用；`providers`/`chunking` 作为通用能力留下 |
| 邮件/学号/手机号均可登录 | 高校场景学生可能没有常用邮箱 |
| 占位接口返回 501 | 契约先行，前端可并行 |

## 11. 安全边界

- 密码：Argon2id（`pwdlib`），不可逆；登录失败不区分原因。
- JWT：HS256 + `SECRET_KEY`；生产环境使用默认密钥会启动报错。
- 授权：service 层强制归属过滤；管理端不返回个案内容。
- 输入：Pydantic 校验 + DB CHECK；注册标识规范化后再查重。
- 输出：统一错误体，不返回堆栈；日志不打印密码、token、个案内容。
- 运行：后端容器非 root；CORS 白名单；`.env` 被 git 忽略。
- 隐私：导出/删除账号仅保留 501 契约；阶段 5 再实现。

## 12. 扩展点（阶段 2-4）

1. **咨询记录**：`records` / `record_versions`，实现「要点 → 四段草稿 → 编辑 → 确认」。
2. **档案与简报**：`record_summaries` / `record_themes`，pgvector 个案内检索。
3. **初筛与随访**：`questionnaires` / `answers` / `follow_ups`，ARQ 定时任务。
4. **前端**：咨询师工作台 + 学生端双入口，按 `docs/api.md` 契约对接。
5. **合规**：字段加密、审计防篡改、导出/删除、Nginx HTTPS。

详见 `docs/center-v2-redesign.md`。
