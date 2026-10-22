# API 说明（v1）

Base URL：`http://localhost:18080/api/v1`（端口由 `.env` 的 `BACKEND_PORT` 决定，默认 18080）

交互式文档：`/docs`（开发环境启用，`APP_ENV=production` 时关闭）。

## 通用约定

### 认证

除注册、登录、健康检查外，所有接口要求：

```http
Authorization: Bearer <access_token>
```

Token 由注册/登录返回，默认有效期 1440 分钟（`ACCESS_TOKEN_EXPIRE_MINUTES`）。

### 错误响应

所有业务错误统一为**顶层**结构（不是 `{"error": {...}}`）：

```json
{
  "code": "case_not_found",
  "message": "个案不存在",
  "details": null
}
```

常见 `code`：

| HTTP | code | 含义 |
| --- | --- | --- |
| 401 | `missing_token` / `invalid_token` / `user_not_found` | 未带 token、token 无效/过期、用户不存在 |
| 403 | `forbidden` | 角色不允许：学生访问管理端、admin 读取个案内容等 |
| 404 | `case_not_found` / `student_not_found` / `counselor_not_found` | 资源不存在**或无权查看**（不区分，防枚举） |
| 409 | `email_taken` / `username_taken` / `student_no_taken` / `phone_taken` / `identity_taken` | 注册标识冲突（`identity_taken` 为并发兜底） |
| 422 | `validation_error` | 参数校验失败，`details` 为字段错误列表 |
| 501 | `not_implemented` | 本期占位接口 |
| 503 | `provider_unavailable` | Embedding/LLM 服务不可用 |

### 分页

列表接口使用 `offset`（≥0，默认 0）与 `limit`（1–100，默认 20），返回：

```json
{ "items": [], "total": 0, "offset": 0, "limit": 20 }
```

## 端点

### 健康检查

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health/live` | 进程存活，不查数据库 |
| GET | `/health/ready` | 执行 `SELECT 1`，数据库不可用时返回 503 `database_unavailable` |

### 认证

| 方法 | 路径 | 状态码 | 说明 |
| --- | --- | --- | --- |
| POST | `/auth/register` | 201 | 学生注册；email / student_no / phone 至少一个 |
| POST | `/auth/login` | 200 | `identifier`（邮箱/学号/手机号）+ 密码 |
| GET | `/auth/me` | 200 | 当前用户（含 role） |
| POST | `/auth/logout` | 204 | 无状态登出；服务端不维护黑名单 |

注册请求（邮箱或学号二选一，手机号同理）：

```json
{
  "email": "me@example.com",
  "password": "至少8位密码",
  "username": "可选，2-50位中文/字母/数字/_/-",
  "privacy_accepted": true
}
```

```json
{
  "student_no": "20230001",
  "password": "至少8位密码",
  "privacy_accepted": true
}
```

`privacy_accepted` 必须为 `true`，否则 422。响应：

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "0f0e...",
    "email": "me@example.com",
    "username": null,
    "student_no": null,
    "phone": null,
    "role": "student",
    "created_at": "2026-10-19T23:10:00+08:00"
  }
}
```

登录请求：

```json
{ "identifier": "me@example.com", "password": "至少8位密码" }
```

`identifier` 会依次匹配 email、student_no、phone；为兼容旧客户端，也接受 `email` 字段。

`/auth/logout` 无请求体，需带 Bearer token，成功返回 204。JWT 无状态，真正的登出是客户端删除 token；该接口保留用于将来加入黑名单或 refresh token 撤销。

### 管理端（admin）

| 方法 | 路径 | 状态码 | 说明 |
| --- | --- | --- | --- |
| POST | `/admin/counselors` | 201 | 开通咨询师账号（管理员） |
| GET | `/admin/counselors` | 200 | 咨询师列表，分页 |
| GET | `/admin/audit-logs` | 200 | 审计日志，admin / auditor 可读；`action` 可选过滤 |

开通咨询师请求：

```json
{
  "email": "counselor@example.com",
  "username": "张老师",
  "password": "临时密码，至少8位"
}
```

响应 `role` 固定为 `counselor`。首个管理员由 CLI 创建（见 README「创建管理员」）。

### 个案（counselor / student）

| 方法 | 路径 | 状态码 | 说明 |
| --- | --- | --- | --- |
| POST | `/cases` | 201 | admin 创建并分配个案 |
| GET | `/cases` | 200 | 本人个案列表：学生看自己，咨询师看接案 |
| GET | `/cases/{case_id}` | 200 | 个案详情；越权 404；admin 访问 403 |

创建请求：

```json
{
  "student_identifier": "student@example.com",
  "counselor_id": "0f0e..."
}
```

- `student_identifier` 支持邮箱/学号/手机号；`counselor_id` 必须是 counselor 角色。
- 咨询师访问他人个案返回 404 `case_not_found`，避免泄露个案是否存在。
- 管理员访问个案列表/详情返回 403 `forbidden`：管理员只做开通与分配，不读个案内容。
- 审计动作：`counselor.create`、`case.create`、`case.view`。


### 会谈与记录（仅接案咨询师）

| 方法 | 路径 | 状态码 | 说明 |
| --- | --- | --- | --- |
| POST | `/cases/{case_id}/conversations` | 201 | 新建会谈；同步分段与事实抽取 |
| GET | `/cases/{case_id}/conversations` | 200 | 个案下的会谈列表 |
| GET | `/conversations/{conversation_id}` | 200 | 会谈详情：分段 + 抽取事实 + 关联记录 |
| POST | `/conversations/{conversation_id}/extract` | 200 | 重新抽取（覆盖旧结果） |
| POST | `/conversations/{conversation_id}/records/draft` | 201 | 生成四段草稿 |
| GET | `/records/{record_id}` | 200 | 记录详情（版本数、修改率） |
| PATCH | `/records/{record_id}` | 200 | 整体替换四段文本 |
| POST | `/records/{record_id}/confirm` | 200 | 确认归档 |

创建请求二选一：

```json
{
  "session_date": "2026-10-21T10:00:00+08:00",
  "consent_confirmed": true,
  "transcript_text": "咨询师：最近睡眠怎么样？\n来访者：总是睡不着。"
}
```

- `consent_confirmed` 必须为 `true`；`session_date` 必须带时区，且不能晚于当前时间（+5 分钟容差）。
- 也可传 `segments: [{"speaker": "client", "text": "..."}]`；文本行首的「咨询师：/来访者：」会被自动识别，无标签记为 `unknown`。
- 抽取默认规则版；`use_llm: true` 且服务端配置了 `LLM_API_KEY` 时走 LLM，失败或输出不合规则自动回退规则版。
- 记录状态 `draft → confirmed`；确认后不可再生成或编辑，重复确认 409 `record_already_confirmed`。
- 未确认草稿仅创建它的咨询师可见，本期不参与检索（检索在阶段 3）。
- 审计动作：`conversation.create`、`conversation.view`、`conversation.extract`、`record.draft`、`record.view`、`record.update`、`record.confirm`。

### 数据与隐私（占位，返回 501）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/privacy/export` | 导出我的全部数据（后续阶段） |
| DELETE | `/privacy/data` | 删除账号与全部数据（后续阶段） |

## curl 示例

```bash
BASE=http://localhost:18080/api/v1

# 注册
curl -s -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"me@example.com","password":"passw0rd!","privacy_accepted":true}'

# 登录并取出 token
TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"identifier":"me@example.com","password":"passw0rd!"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

```

完整链路（管理员由 CLI 创建）：

```bash
# 管理员登录
ADMIN_TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"identifier":"admin@example.com","password":"ChangeMe123"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 开通咨询师
curl -s -X POST "$BASE/admin/counselors" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"counselor@example.com","username":"张老师","password":"TempPass123"}'

# 建个案并分配（counselor_id 取上一步响应）
curl -s -X POST "$BASE/cases" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"student_identifier":"student@example.com","counselor_id":"<id>"}'

# 咨询师查看自己的个案
curl -s "$BASE/cases" -H "Authorization: Bearer $COUNSELOR_TOKEN"

# 新建会谈（CASE_ID 取建案响应，COUNSELOR_TOKEN 必须是接案咨询师）
curl -s -X POST "$BASE/cases/$CASE_ID/conversations" \
  -H "Authorization: Bearer $COUNSELOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_date":"2026-10-21T10:00:00+08:00","consent_confirmed":true,"transcript_text":"咨询师：最近睡眠怎么样？\n来访者：总是睡不着。"}'

# 生成四段草稿（CONV_ID 取上一步响应；先用规则版，不依赖 LLM）
curl -s -X POST "$BASE/conversations/$CONV_ID/records/draft" \
  -H "Authorization: Bearer $COUNSELOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"use_llm":false}'
```

