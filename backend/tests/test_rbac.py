"""阶段 1：RBAC、个案归属与审计集成测试。

需要真实 PostgreSQL + pgvector；未配置 TEST_DATABASE_URL 时整组 skip。
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import Role
from app.core.security import hash_password
from app.db.models import AuditLog, User

pytestmark = pytest.mark.integration

STUDENT_PASSWORD = "student-pass-123"
ADMIN_PASSWORD = "admin-pass-123"
COUNSELOR_PASSWORD = "counselor-pass-123"
AUDITOR_PASSWORD = "auditor-pass-123"


def _auth(token: str) -> dict[str, str]:
    """构造 Bearer 认证头。"""
    return {"Authorization": f"Bearer {token}"}


async def _seed_user(
    db: AsyncSession,
    *,
    email: str,
    role: str,
    password: str,
    username: str,
) -> User:
    """直接写入一个账号（用于管理员/审计员等不能自助注册的角色）。"""
    user = User(
        email=email,
        username=username,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _login(client, identifier: str, password: str) -> str:
    """登录并返回 access_token。"""
    response = await client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def test_student_register_with_student_no_and_login(db_client) -> None:
    """学生可用学号注册，注册即登录，登录标识兼容学号。"""
    response = await db_client.post(
        "/api/v1/auth/register",
        json={
            "student_no": "20230001",
            "username": "小明",
            "password": STUDENT_PASSWORD,
            "privacy_accepted": True,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["role"] == "student"
    assert body["user"]["student_no"] == "20230001"
    assert body["user"]["email"] is None

    me = await db_client.get("/api/v1/auth/me", headers=_auth(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["role"] == "student"

    login = await db_client.post(
        "/api/v1/auth/login",
        json={"identifier": "20230001", "password": STUDENT_PASSWORD},
    )
    assert login.status_code == 200, login.text


async def test_student_cannot_create_case_or_list_counselors(db_client) -> None:
    """学生越权访问管理端接口返回 403。"""
    response = await db_client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": STUDENT_PASSWORD,
            "privacy_accepted": True,
            "username": "学生甲",
        },
    )
    token = response.json()["access_token"]

    create_case = await db_client.post(
        "/api/v1/cases",
        json={
            "student_identifier": "student@example.com",
            "counselor_id": str(uuid.uuid4()),
        },
        headers=_auth(token),
    )
    assert create_case.status_code == 403
    assert create_case.json()["code"] == "forbidden"

    counselors = await db_client.get("/api/v1/admin/counselors", headers=_auth(token))
    assert counselors.status_code == 403


async def test_case_visibility_audit_and_admin_boundary(db_client, db_session) -> None:
    """完整链路：管理员开通咨询师→建案→咨询师/学生可见，他人不可见，审计落库。"""
    await _seed_user(
        db_session,
        email="admin@example.com",
        role=Role.ADMIN.value,
        password=ADMIN_PASSWORD,
        username="管理员",
    )
    admin_token = await _login(db_client, "admin@example.com", ADMIN_PASSWORD)

    counselor_one = (
        await db_client.post(
            "/api/v1/admin/counselors",
            json={
                "email": "c1@example.com",
                "username": "咨询师一",
                "password": COUNSELOR_PASSWORD,
            },
            headers=_auth(admin_token),
        )
    ).json()
    await db_client.post(
        "/api/v1/admin/counselors",
        json={
            "email": "c2@example.com",
            "username": "咨询师二",
            "password": COUNSELOR_PASSWORD,
        },
        headers=_auth(admin_token),
    )
    assert counselor_one["role"] == "counselor"

    student = (
        await db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "student@example.com",
                "password": STUDENT_PASSWORD,
                "privacy_accepted": True,
                "username": "学生甲",
            },
        )
    ).json()

    case_response = await db_client.post(
        "/api/v1/cases",
        json={
            "student_identifier": "student@example.com",
            "counselor_id": counselor_one["id"],
        },
        headers=_auth(admin_token),
    )
    assert case_response.status_code == 201, case_response.text
    case = case_response.json()
    assert case["counselor_id"] == counselor_one["id"]

    counselor_one_token = await _login(db_client, "c1@example.com", COUNSELOR_PASSWORD)
    counselor_two_token = await _login(db_client, "c2@example.com", COUNSELOR_PASSWORD)

    own_detail = await db_client.get(
        f"/api/v1/cases/{case['id']}", headers=_auth(counselor_one_token)
    )
    assert own_detail.status_code == 200

    other_detail = await db_client.get(
        f"/api/v1/cases/{case['id']}", headers=_auth(counselor_two_token)
    )
    assert other_detail.status_code == 404
    assert other_detail.json()["code"] == "case_not_found"

    student_detail = await db_client.get(
        f"/api/v1/cases/{case['id']}", headers=_auth(student["access_token"])
    )
    assert student_detail.status_code == 200

    other_student = (
        await db_client.post(
            "/api/v1/auth/register",
            json={
                "student_no": "20239999",
                "password": STUDENT_PASSWORD,
                "privacy_accepted": True,
                "username": "学生乙",
            },
        )
    ).json()
    other_student_detail = await db_client.get(
        f"/api/v1/cases/{case['id']}", headers=_auth(other_student["access_token"])
    )
    assert other_student_detail.status_code == 404

    # 学生列表只包含自己的个案
    own_list = await db_client.get(
        "/api/v1/cases", headers=_auth(student["access_token"])
    )
    assert own_list.json()["total"] == 1
    other_list = await db_client.get(
        "/api/v1/cases", headers=_auth(other_student["access_token"])
    )
    assert other_list.json()["total"] == 0

    # 管理员不能读取个案内容
    admin_list = await db_client.get("/api/v1/cases", headers=_auth(admin_token))
    assert admin_list.status_code == 403
    admin_detail = await db_client.get(
        f"/api/v1/cases/{case['id']}", headers=_auth(admin_token)
    )
    assert admin_detail.status_code == 403

    # 审计：开通、建案、查看都留痕
    audit_response = await db_client.get(
        "/api/v1/admin/audit-logs", headers=_auth(admin_token)
    )
    assert audit_response.status_code == 200, audit_response.text
    actions = {item["action"] for item in audit_response.json()["items"]}
    assert {"counselor.create", "case.create", "case.view"} <= actions

    logs = (await db_session.scalars(select(AuditLog))).all()
    assert len(logs) >= 5


async def test_auditor_is_read_only(db_client, db_session) -> None:
    """审计员可读审计日志，但不能开通账号。"""
    await _seed_user(
        db_session,
        email="auditor@example.com",
        role=Role.AUDITOR.value,
        password=AUDITOR_PASSWORD,
        username="审计员",
    )
    token = await _login(db_client, "auditor@example.com", AUDITOR_PASSWORD)

    read = await db_client.get("/api/v1/admin/audit-logs", headers=_auth(token))
    assert read.status_code == 200

    write = await db_client.post(
        "/api/v1/admin/counselors",
        json={
            "email": "c3@example.com",
            "username": "咨询师三",
            "password": COUNSELOR_PASSWORD,
        },
        headers=_auth(token),
    )
    assert write.status_code == 403
