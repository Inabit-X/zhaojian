# TODO 与后续路线（心理中心版）

> 旧版「私人心理伙伴」已被否定，其业务表与代码已于阶段 1 末删除；仅 `providers/` 与 `memory/chunking.py` 作为通用能力保留，见 `docs/center-v2-redesign.md`。

## 阶段 0+1 已完成（2026-10-19）

- [x] 《新旧对照与阶段 1 设计》文档：资产复用/改造/删除/退役、权限矩阵、迁移方案
- [x] 迁移 `0003_center_rbac`：`users` 加 `role/student_no/phone`、`email` 可空；新建 `cases`、`audit_logs`
- [x] 角色体系：`student / counselor / admin / auditor`，CHECK 约束 + `core/roles.py`
- [x] 学生注册支持邮箱/学号/手机号任一；登录改 `identifier`；自助注册只产生 student
- [x] 管理员开通咨询师：`POST/GET /admin/counselors`
- [x] 个案：`POST /cases`（admin 建案分配）、`GET /cases`、`GET /cases/{id}`
- [x] 归属校验：咨询师仅本人接案、学生仅本人；越权 404，admin 读个案 403
- [x] 审计：`counselor.create`、`case.create`、`case.view`，与业务同事务；admin/auditor 可查
- [x] `case_id` 统一用 UUID 路径参数，非法 UUID 返回 422
- [x] 管理员 CLI：`python -m app.cli create-admin`
- [x] 集成测试 `tests/test_rbac.py`：真实 PG 上 4 项全绿；无 DB 时自动 skip
- [x] 迁移往返验证：`upgrade → downgrade -1 → upgrade` 全部成功
- [x] 迁移 `0004_drop_legacy`：删除 `events` / `event_chunks` / `agent_drafts`，同步删除旧路由、schema、service、model 与测试
- [x] 文档：`docs/center-v2-redesign.md`、`docs/architecture.md`、`docs/api.md`

## 阶段 2A：文本会谈 → 四段记录草稿（代码完成，待连库验证）

范围：先打通「粘贴会谈文本 → 分段/规则抽取 → 四段草稿 → 编辑 → 确认归档」；语音转写不在本期。

- [x] 迁移 `0005_conversations`：`conversations`、`segments`、`extractions`、`records`、`record_versions`
- [x] `POST /cases/{case_id}/conversations`：全文或手工分段；行首说话人识别；同步规则抽取并写库
- [x] `GET /cases/{case_id}/conversations`、`GET /conversations/{id}`、`POST /conversations/{id}/extract`
- [x] `POST /conversations/{id}/records/draft`：规则模板兜底，可选 LLM 生成四段
- [x] `GET/PATCH /records/{id}`、`POST /records/{id}/confirm`；`record_versions` 留痕、修改率
- [x] 审计：`conversation.create/view/extract`、`record.draft/view/update/confirm`
- [x] 单元测试 40 passed、ruff 全绿
- [ ] 真实 PostgreSQL：`alembic upgrade head`（0005）与 `tests/test_conversation_flow.py` 集成测试（需 `RUN_DB_TESTS=1`，待授权）
- [ ] 语音识别 / 实时转写：`source=audio` 字段已预留，ASR provider 与接口未实现
- [ ] 真实 LLM provider 冒烟（需内网/兼容 API Key），校验 quote 逐字与四段 JSON
- [ ] 前端：会谈录入 → 草稿编辑/确认页面
- [ ] 风险话术的危机流程（当前只抽取 `risk` 事实并提示，不自动升级）

## 后续阶段（报告第 10–12 周）

### P1：档案与简报（阶段 3）

- [ ] `record_summaries` 摘要表 + pgvector（复用 `memory/chunking.py` 与 embedding provider，新建表）
- [ ] `record_themes` 主题层：主题、证据记录 id、置信度
- [ ] `GET /cases/{id}/brief`：一页简报（基本信息、主诉、时间线、主题、风险提示「未评估」）
- [ ] 个案内语义检索：强制 `case_id` 过滤，禁止跨个案
- [ ] 摘要生成后由咨询师确认；未确认摘要不进入简报

### P2：初筛与随访（阶段 4）

- [ ] `questionnaires` / `answers`：量表定义与作答，评分规则可配置
- [ ] `POST /screenings`：只做「客观结果 + 访谈提纲」，输出禁止诊断结论
- [ ] `follow_ups` + ARQ 定时任务：到期推送待办
- [ ] 学生端：问卷填写页（只读自己的结果）
- [ ] 异常分数进咨询师待办，不做自动危机处置

### P3：合规与部署（阶段 5）

- [ ] 敏感字段加密（应用层 AES-GCM 或 PG `pgcrypto`），密钥不进仓库
- [ ] 审计不可篡改：DB 层 append-only 权限/触发器 + 定期归档
- [ ] 数据导出/删除：按个案导出 JSON、账号删除冷却期；全部留审计
- [ ] Nginx HTTPS、CSP/HSTS、`/docs` 生产关闭
- [ ] 备份恢复演练与保留策略

### P4：评测（阶段 6）

- [ ] 模拟案例集（不含真实个案）
- [ ] 指标：事实错误率、遗漏率、修改率、咨询师 1–5 分评分
- [ ] 评测脚本与报告模板

## 旧版资产处置（已执行）

- 复用：FastAPI 骨架、配置、异常、DB 会话、Alembic、Docker Compose、Argon2/JWT、统一错误体、前端登录/注册页、`providers/`、`memory/chunking.py`。
- 删除：`events`、`event_chunks`、`agent_drafts` 三表（迁移 `0004_drop_legacy`）及对应模型、路由、服务、schema、测试；`scripts/smoke.sh` 同步移除。
- 退役：旧版「个人事件/智能体/画像/对话」前端页面计划取消；前端在阶段 2 按「咨询师工作台 + 学生端」重做。

## 非目标（红线）

- 不做心理诊断、治疗决策、危机识别完整流程；系统只做文书与随访辅助
- 不面向学生提供 AI 对话或「心理伙伴」
- 不做人格类型推理、智能体自动生成
- 不做社区、社交、多用户匹配
- 不做模型训练/微调
- 真实个案数据不出校；开发期只用模拟或脱敏数据

## 迁移与运维注意

1. **迁移链**：`0001_initial` → `0002_persona_todo`（空）→ `0003_center_rbac` → `0004_drop_legacy`。已发布迁移不改写，变更新增 revision。
2. **降级限制**：`0003` 降级会把 `users.email` 恢复 NOT NULL；`0004` 降级只恢复空表结构、不恢复数据；均仅限开发环境。
3. **Embedding 维度**：阶段 3 新建摘要向量列时固定 `vector(1536)`，换模型需新增迁移并重算。
4. **ANN 索引**：数据量上来后对摘要表建 HNSW（`vector_cosine_ops`），并强制 `case_id` 过滤。
5. **测试库**：`TEST_DATABASE_URL` 指向真实 PG（含 pgvector）；集成测试每次重建 schema，别指向开发主库。
6. **Compose**：`--profile async` 才启动 redis/worker；本期未用异步任务。

## 已知风险

- 角色变更靠每请求查库保证即时生效；QPS 上来后需加缓存/短 TTL。
- 审计目前是应用层 append-only，DBA 仍可改库；生产需 DB 权限或触发器兜底。
- 管理员与咨询师账号由 CLI/管理员开通，尚无「停用账号」与密码重置流程。
- 本机端口占用：Windows 8000（Apache）、8080（kdb-web）、5432/6379（其他 Compose）；仓库 `.env` 已用 18080/15432/16379。
- 单机 Compose 无备份与高可用，仅适用于本地开发与早期试用。
