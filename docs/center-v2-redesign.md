# 心理中心版改造：新旧对照与阶段 1 设计

> 文档状态：阶段 0+1 交付物，供 review。对应新版《「照见」心理中心版项目报告》的「数据模型」与「账号角色」两节。
>
> 红线：本系统是咨询师的文书与随访辅助工具，**不提供诊断、不做治疗决策、不面向学生做 AI 对话**。开发期只使用模拟或脱敏数据。

## 1. 背景与目标

旧版「私人心理伙伴」定位是学生自助记录 + AI 伙伴，与新版报告的定位（高校心理中心的临床文书与随访支持系统）不一致。旧版项目已被否定，但其中通用的工程骨架仍然可用。

阶段 0+1 的目标不是做业务功能，而是把「地基」换对：

1. 说清楚哪些代码复用、哪些改造、哪些删除。
2. 建立中心版的最小领域模型：账号与角色、个案、审计日志。
3. 把「谁能看什么」落到 API 层，而不是只靠前端隐藏。
4. 用一次真实迁移（0003）和集成测试证明这套地基能跑。

阶段 2（记录起草）再建 records / record_versions，不在本期。

## 2. 新旧对照

| 维度 | 旧版（私人心理伙伴） | 新版（心理中心版） |
| --- | --- | --- |
| 使用者 | 学生自己 | 学生 + 咨询师 + 管理员（+ 可选审计员） |
| 核心对象 | 个人事件、智能体草稿 | 个案、咨询记录、随访 |
| AI 的角色 | 生成「伙伴」并对话 | 只生成文书草稿，咨询师确认后归档 |
| 数据主线 | events → event_chunks → agent_drafts | cases → records → summaries / follow_ups |
| 前端 | 个人记录 8 页 | 咨询师工作台 + 学生端两个入口 |
| 权限 | 只有「本人」 | 角色 + 个案归属双重约束 |
| 合规重点 | 非医疗免责 | 不诊断、不对话、数据不出校、操作留痕 |
| 技术栈 | Vue3 + FastAPI + PG/pgvector + Docker | 不变（报告明确沿用） |

## 3. 现有资产处置

### 3.1 直接复用

- `backend/app/main.py`、`core/config.py`、`core/exceptions.py`、`db/session.py`、`db/base.py`、`db/mixins.py`
- Alembic 配置与迁移链
- Docker Compose（db / backend / 可选 redis+worker）
- `core/security.py`（Argon2id + JWT）
- `providers/`（OpenAI 兼容 embedding/LLM）与 `memory/chunking.py`（阶段 3 摘要复用）
- 测试骨架与统一错误体

### 3.2 改造

| 资产 | 改造内容 |
| --- | --- |
| `users` 表 | `email` 改为可空；新增 `role`、`student_no`、`phone`；咨询师账号不再自助注册 |
| `schemas/auth.py` | 注册支持邮箱/学号/手机号任一；登录改为 `identifier`，保留 `email` 兼容 |
| `services/auth.py` | 按标识查询；角色固定学生；冲突检测覆盖三个标识 |
| `api/deps.py` | 新增 `require_roles()` 与角色依赖 |
| `api/routes/auth.py` | 响应带 `role`；注册说明改为「学生注册」 |

### 3.3 删除（0004_drop_legacy）

- `events`、`event_chunks`、`agent_drafts` 三张表及其模型、路由、服务、schema、测试，迁移 `0004_drop_legacy` 统一 DROP。
- 原因：旧业务已作废，保留会形成死代码与误用风险，也会让「个案/记录」的权限与数据边界变得含糊。
- 切片与 embedding 的通用能力已抽到 `memory/chunking.py` 与 `providers/`，阶段 3 直接复用，不依赖旧表。

### 3.4 退役

- 旧版前端 8 页计划取消（前端代码从未生成，无删除成本）。
- `persona`、`memory`、`chat`、`internal` 占位路由随旧代码一并删除；阶段 2 起按新契约重建 `records` 等接口。

## 4. 领域模型

### 4.1 阶段 1 建表

#### users（改造）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | uuid | PK | `gen_random_uuid()` |
| email | varchar(255) | unique, nullable | 学生可无邮箱；咨询师必须有 |
| username | varchar(50) | unique, nullable | 显示名/姓名 |
| student_no | varchar(32) | unique, nullable | 学号 |
| phone | varchar(20) | unique, nullable | 手机号 |
| password_hash | varchar(255) | not null | Argon2id |
| role | varchar(16) | not null, default `student` | student / counselor / admin / auditor |
| created_at | timestamptz | not null | |

约束：`ck_users_role` 限定四个角色。三个登录标识至少一个非空，由应用层校验（PG 的 CHECK 无法优雅表达「至少一个」，且未来可能接统一认证）。

#### cases（个案）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | uuid | PK | |
| student_id | uuid | FK users, not null, RESTRICT | 个案所属学生 |
| counselor_id | uuid | FK users, nullable, SET NULL | 接案咨询师；未分配为空 |
| status | varchar(16) | not null, default `active` | active / closed / archived |
| opened_at | timestamptz | not null, default now() | 建档时间 |
| closed_at | timestamptz | nullable | 结案时间 |
| created_at / updated_at | timestamptz | not null | |

索引：`(counselor_id, status)`、`(student_id)`。
约束：`ck_cases_status`。`student_id` 必须是 student 角色、`counselor_id` 必须是 counselor 角色，由服务层校验（FK 只能保证存在）。

#### audit_logs（审计）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK, identity | 追加写 |
| actor_id | uuid | FK users, nullable, SET NULL | 系统操作时为空 |
| action | varchar(64) | not null | 如 `case.create` |
| target_type | varchar(32) | nullable | 如 `case` |
| target_id | uuid | nullable | 目标对象 id |
| metadata | jsonb | not null, default `{}` | 只放非敏感上下文 |
| ip | varchar(45) | nullable | 预留，当前可空 |
| created_at | timestamptz | not null | |

索引：`(actor_id, created_at DESC)`、`(target_type, target_id, created_at DESC)`。
只提供插入与查询，**不提供 update/delete**；生产环境建议再加 DB 层 append-only 权限或触发器。

### 4.2 阶段 2/3 规划（本期不建，仅定名）

| 表 | 用途 | 关键字段 |
| --- | --- | --- |
| records | 一次咨询记录 | case_id, counselor_id, session_date, raw_notes, draft_json, confirmed_json, status, confirmed_at |
| record_versions | 草稿/确认稿留痕 | record_id, version, content_json, editor_id, created_at |
| record_summaries | 摘要层（可向量化） | record_id, summary_text, embedding, model, created_at |
| record_themes | 主题层 | case_id, theme, evidence_record_ids, confidence |
| questionnaires | 量表定义 | code, title, items_json, scoring_rule |
| answers | 学生作答 | questionnaire_id, student_id, answers_json, score_json, submitted_at |
| follow_ups | 随访计划 | case_id, due_at, channel, status, note |

关系主线：`User(学生) 1—N Case`、`User(咨询师) 1—N Case`、`Case 1—N Record`、`Record 1—N RecordVersion`、`Record 1—1 RecordSummary`、`Case 1—N FollowUp`。

### 4.3 关键设计决定

- **JWT 不写 role**：每次请求从 DB 读用户，角色变更/停用即时生效。代价是每请求一次主键查询，MVP 可接受。
- **越权返回 404 而不是 403**：咨询师访问他人个案时返回 404，避免泄露「该个案存在」。管理员访问个案内容返回 403，因为这是明确的角色越界，不是资源归属问题。
- **管理员不看个案内容**：`GET /cases`、`GET /cases/{id}` 对 admin 直接 403；管理员只做账号开通、个案创建/分配（仅返回 id 与归属）与审计查看。
- **审计与业务同事务**：业务写失败时审计不落库，避免「有审计无操作」。
- **email 可空**：学生可能只有学号/手机号；唯一索引允许多个 NULL，符合 PG 语义。

## 5. 角色与权限矩阵

| 功能 | student | counselor | admin | auditor |
| --- | --- | --- | --- | --- |
| 注册/登录/查看本人资料 | ✅ | ✅（登录） | ✅（登录） | ✅（登录） |
| 查看本人个案状态 | ✅ | — | — | — |
| 查看/编辑本人个案 | — | ✅ | — | — |
| 查看个案简报/记录 | — | ✅（本人个案） | ❌ | ❌ |
| 创建/分配个案 | — | — | ✅ | — |
| 开通咨询师账号 | — | — | ✅ | — |
| 查看审计日志 | — | — | ✅ | ✅（只读） |
| 系统配置/账号停用 | — | — | ✅（后续） | — |

阶段 1 落地：注册只产生 student；咨询师由 admin 开通；个案由 admin 创建并分配；counselor 只看 `counselor_id=自己`；student 只看 `student_id=自己`；auditor 只读审计。

## 6. 阶段 1 API

前缀 `/api/v1`。错误体仍为 `{code, message, details}`。

| 方法 | 路径 | 角色 | 说明 |
| --- | --- | --- | --- |
| POST | `/auth/register` | 公开 | 学生注册；email/student_no/phone 至少一个；返回 token + user |
| POST | `/auth/login` | 公开 | `identifier`（邮箱/学号/手机号）或兼容 `email` + 密码 |
| GET | `/auth/me` | 登录 | 返回 id/email/username/role/student_no/phone |
| POST | `/admin/counselors` | admin | 开通咨询师账号（201） |
| GET | `/admin/counselors` | admin | 咨询师列表（分页） |
| GET | `/admin/audit-logs` | admin/auditor | 审计列表（分页，可按 action 过滤） |
| POST | `/cases` | admin | 创建个案并分配咨询师（201） |
| GET | `/cases` | counselor/student | 本人个案列表（分页） |
| GET | `/cases/{case_id}` | counselor/student | 个案详情；越权 404 |

错误码沿用：400/401/403/404/409/422/503。新增 `forbidden`（403）。

审计动作：`counselor.create`、`case.create`、`case.view`。登录/注册不写审计（避免高频噪音），后续接入统一认证时再评估。

## 7. 迁移 0003 与 0004

`0003_center_rbac`：

1. `users.email` 改为可空。
2. 新增 `users.role`（默认 `student`）、`student_no`、`phone` 及唯一约束与角色 CHECK。
3. 新建 `cases`、`audit_logs` 及索引、外键。
4. 旧版三表此时保持不变，由 `0004` 删除。

`0004_drop_legacy`：

1. `DROP TABLE event_chunks / events / agent_drafts`（含索引与约束）。
2. `downgrade` 只重建空表结构，不恢复数据；仅用于开发环境回滚。

兼容性：旧账号的 `role` 全部回填为 `student`；`email` 放开可空不影响已有非空数据。

兼容性：旧账号的 `role` 全部回填为 `student`，与旧版定位一致；`email` 放开可空不影响已有非空数据。

降级：删 `audit_logs`、`cases`、新增列；`email` 恢复 NOT NULL。若已存在无邮箱账号，降级会失败——仅开发环境使用，文档中注明。

## 8. 安全与合规

- 密码 Argon2id；JWT HS256，24h，密钥仅环境变量。
- 审计 append-only：无修改/删除接口；日志与业务同事务。
- 管理员接口不返回任何个案内容；审计 metadata 不写自由文本。
- 应用日志不记录密码、token、个案原文。
- 开发期只用模拟数据；真实个案数据需伦理审查与数据不出校约束。
- 全局免责声明保留。

## 9. 阶段 1 验收清单

- [x] `alembic upgrade head` 在 PostgreSQL 上成功，`downgrade -1` 可回滚。
- [x] 学生可用邮箱或学号注册、登录，`role=student`。
- [x] 学生访问 `/cases` 只看到自己；访问他个案 404。
- [x] 咨询师由 admin 开通；咨询师 A 看不到咨询师 B 的个案（404）。
- [x] admin 访问个案详情 403；可创建/分配个案；可查看审计。
- [x] 审计日志记录 `counselor.create` / `case.create` / `case.view`。
- [x] `pytest` 全绿（无 DB 时集成测试自动 skip）。

验证记录（2026-10-19，PostgreSQL 16 + pgvector，WSL Docker）：

| 项 | 命令 | 结果 |
| --- | --- | --- |
| 迁移往返 | `alembic upgrade head` → `downgrade -1` → `upgrade head` | 退出码 0，`current = 0004_drop_legacy (head)` |
| 集成测试 | `pytest tests/test_rbac.py -q` | 4 passed（真实 PG，非 skip） |
| 全量测试 | `pytest -q` | 17 项：13 passed、4 skipped（无 DB 时的默认路径） |
| 静态检查 | `ruff check app tests alembic` | All checks passed |
| 管理员 CLI | `python -m app.cli create-admin --email … --password … --name …` | 创建成功；重复执行提示「邮箱已存在」并退出 1 |
| 容器冒烟 | `bash scripts/smoke_center.sh --no-up` | 5 项通过，`✅ SMOKE PASS`（admin 403 / 接案 200 / 他咨询师 404 / 学生 200 / 审计齐全） |
| 删除旧链路后复验 | `pytest` + `ruff` + `smoke_center.sh` | 13 passed / 4 skipped；ruff 全绿；冒烟 5 项通过 |

## 10. 开放问题

1. 个案分配是否允许咨询师自领，还是必须管理员分配？（本期按管理员分配）
2. 学号/手机号是否对接学校统一认证？若对接，密码登录可降级为备用。
3. 管理员是否需要「停用账号」？本期只做开通。
4. 审计保留期限与导出格式？（报告要求可导出，本期仅接口占位）
5. records 的四段字段最终结构需在阶段 2 与咨询师确认后定稿。

## 11. 阶段 2 入口（下一期）

阶段 2 只做「咨询记录起草」最小闭环，仍不碰诊断与智能体：

1. 建 `records`、`record_versions` 两张表（字段见 4.2），先不建摘要与主题表。
2. `POST /cases/{case_id}/records/draft`：接收咨询师输入的要点，调用 LLM provider 生成四段草稿（主诉/观察/评估/计划），**只允许使用输入信息，缺失写「未提及」**。
3. `PATCH /records/{id}` 保存编辑稿；`POST /records/{id}/confirm` 固化确认稿并递增版本。
4. 修改率：`record_versions` 保存草稿原文与确认稿，事后可计算编辑距离。
5. 权限沿用本期的 `CaseViewer`：只有接案咨询师可起草/确认；未确认记录不进档案、不参与后续检索。

