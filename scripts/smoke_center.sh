#!/usr/bin/env bash
# 中心版阶段 1 冒烟：管理员开通咨询师 → 建案 → 归属隔离 → 审计。
# 用法：bash scripts/smoke_center.sh [--no-up]
# 依赖：docker compose、curl、python3；从仓库根 .env 读取端口。
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" != "--no-up" ]]; then
  docker compose up -d --build --wait backend
fi

set -a
# shellcheck disable=SC1091
source .env
set +a
BASE="${BASE:-http://127.0.0.1:${BACKEND_PORT:-8000}/api/v1}"

pass=0
fail=0
check() { # 描述 实际 期望
  if [[ "$2" == "$3" ]]; then
    echo "  ✅ $1 ($2)"
    pass=$((pass + 1))
  else
    echo "  ❌ $1：期望 $3，实际 $2"
    fail=$((fail + 1))
  fi
}

json_field() { python3 -c "import sys,json;print(json.load(sys.stdin).get('$1',''))"; }
status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

echo "== 等待后端就绪 =="
for _ in $(seq 1 120); do
  curl -fsS "$BASE/health/ready" >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS "$BASE/health/ready" >/dev/null || { echo "后端未就绪：$BASE"; exit 1; }
echo "  ready: $BASE"

echo "== 准备账号（幂等） =="
docker compose exec -T backend python -m app.cli create-admin \
  --email admin@example.com --password 'AdminPass123' --name 管理员 >/dev/null 2>&1 || true

ADMIN_TOKEN=$(curl -sS -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d '{"identifier":"admin@example.com","password":"AdminPass123"}' | json_field access_token)
[[ -n "$ADMIN_TOKEN" ]] || { echo "管理员登录失败"; exit 1; }

for i in 1 2; do
  curl -sS -X POST "$BASE/admin/counselors" -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"c$i@example.com\",\"username\":\"咨询师$i\",\"password\":\"Counselor123\"}" \
    >/dev/null 2>&1 || true
done

C1_TOKEN=$(curl -sS -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d '{"identifier":"c1@example.com","password":"Counselor123"}' | json_field access_token)
C2_TOKEN=$(curl -sS -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d '{"identifier":"c2@example.com","password":"Counselor123"}' | json_field access_token)
[[ -n "$C1_TOKEN" && -n "$C2_TOKEN" ]] || { echo "咨询师登录失败"; exit 1; }

curl -sS -X POST "$BASE/auth/register" -H 'Content-Type: application/json' \
  -d '{"email":"student@example.com","password":"Student123","privacy_accepted":true,"username":"学生甲"}' \
  >/dev/null 2>&1 || true
STUDENT_TOKEN=$(curl -sS -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d '{"identifier":"student@example.com","password":"Student123"}' | json_field access_token)
[[ -n "$STUDENT_TOKEN" ]] || { echo "学生登录失败"; exit 1; }

C1_ID=$(curl -sS "$BASE/admin/counselors" -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "
import sys, json
items = json.load(sys.stdin)['items']
print(next(i['id'] for i in items if i['email'] == 'c1@example.com'))")

echo "== 建案与权限 =="
CASE_ID=$(curl -sS -X POST "$BASE/cases" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"student_identifier\":\"student@example.com\",\"counselor_id\":\"$C1_ID\"}" | json_field id)
[[ -n "$CASE_ID" ]] || { echo "建案失败"; exit 1; }

check "管理员不能读个案" "$(status "$BASE/cases/$CASE_ID" -H "Authorization: Bearer $ADMIN_TOKEN")" 403
check "接案咨询师可读" "$(status "$BASE/cases/$CASE_ID" -H "Authorization: Bearer $C1_TOKEN")" 200
check "其他咨询师不可读" "$(status "$BASE/cases/$CASE_ID" -H "Authorization: Bearer $C2_TOKEN")" 404
check "学生本人可读" "$(status "$BASE/cases/$CASE_ID" -H "Authorization: Bearer $STUDENT_TOKEN")" 200

STUDENT_TOTAL=$(curl -sS "$BASE/cases" -H "Authorization: Bearer $STUDENT_TOKEN" | json_field total)
[[ "${STUDENT_TOTAL:-0}" -ge 1 ]] && check "学生列表含本人个案" 1 1 || check "学生列表含本人个案" 0 1

echo "== 审计 =="
AUDIT=$(curl -sS "$BASE/admin/audit-logs" -H "Authorization: Bearer $ADMIN_TOKEN")
python3 - "$AUDIT" <<'PY'
import json
import sys

data = json.loads(sys.argv[1])
actions = {item["action"] for item in data["items"]}
required = {"counselor.create", "case.create", "case.view"}
missing = required - actions
if missing:
    print(f"  ❌ 缺少审计动作：{sorted(missing)}")
    raise SystemExit(1)
print(f"  ✅ 审计动作齐全：{sorted(required)}")
PY

echo
echo "结果：$pass 项通过，$fail 项失败"
[[ "$fail" -eq 0 ]] && echo "✅ SMOKE PASS" || { echo "❌ SMOKE FAIL"; exit 1; }
