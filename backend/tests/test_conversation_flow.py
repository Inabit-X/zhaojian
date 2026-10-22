"""2A 端到端：会谈 → 抽取 → 四段草稿 → 编辑 → 确认（需 PostgreSQL）。"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models import User

pytestmark = pytest.mark.integration


async def _login(client: AsyncClient, identifier: str, password: str) -> str:
    """登录并返回 JWT。"""
    response = await client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    """构造 Bearer 头。"""
    return {"Authorization": f"Bearer {token}"}


async def test_conversation_to_confirmed_record(
    db_client: AsyncClient, db_session: AsyncSession
) -> None:
    """覆盖 2A 主链路与越权、重复确认、审计。"""
    admin = User(
        email="admin@campus.edu.cn",
        username="admin",
        password_hash=hash_password("Admin123!"),
        role="admin",
    )
    db_session.add(admin)
    await db_session.commit()

    admin_token = await _login(db_client, "admin@campus.edu.cn", "Admin123!")
    c1 = await db_client.post(
        "/api/v1/admin/counselors",
        json={
            "email": "c1@campus.edu.cn",
            "username": "c1",
            "password": "Counselor123",
        },
        headers=_auth(admin_token),
    )
    assert c1.status_code == 201, c1.text
    c1_id = c1.json()["id"]
    c2 = await db_client.post(
        "/api/v1/admin/counselors",
        json={
            "email": "c2@campus.edu.cn",
            "username": "c2",
            "password": "Counselor123",
        },
        headers=_auth(admin_token),
    )
    assert c2.status_code == 201, c2.text

    student = await db_client.post(
        "/api/v1/auth/register",
        json={
            "student_no": "20260001",
            "username": "stu1",
            "password": "Student123",
            "privacy_accepted": True,
        },
    )
    assert student.status_code == 201, student.text
    student_token = student.json()["access_token"]

    case = await db_client.post(
        "/api/v1/cases",
        json={"student_identifier": "20260001", "counselor_id": c1_id},
        headers=_auth(admin_token),
    )
    assert case.status_code == 201, case.text
    case_id = case.json()["id"]

    c1_token = await _login(db_client, "c1@campus.edu.cn", "Counselor123")
    created = await db_client.post(
        f"/api/v1/cases/{case_id}/conversations",
        json={
            "session_date": "2026-10-21T10:00:00+08:00",
            "consent_confirmed": True,
            "transcript_text": (
                "咨询师：最近睡眠怎么样？\n"
                "来访者：总是睡不着，白天很焦虑。\n"
                "来访者：我觉得自己没用。"
            ),
        },
        headers=_auth(c1_token),
    )
    assert created.status_code == 201, created.text
    conversation = created.json()
    conversation_id = conversation["id"]

    assert conversation["status"] == "extracted"
    assert len(conversation["segments"]) >= 3
    assert conversation["segments"][0]["speaker"] == "counselor"
    assert conversation["segments"][1]["speaker"] == "client"
    assert conversation["extractions"]
    assert conversation["record_id"] is None

    draft = await db_client.post(
        f"/api/v1/conversations/{conversation_id}/records/draft",
        json={"use_llm": False},
        headers=_auth(c1_token),
    )
    assert draft.status_code == 201, draft.text
    record = draft.json()
    record_id = record["id"]
    assert record["status"] == "draft"
    assert record["version_count"] == 1
    assert set(record["sections"]) == {
        "presenting",
        "observations",
        "formulation",
        "plan",
    }

    reextract = await db_client.post(
        f"/api/v1/conversations/{conversation_id}/extract",
        json={"use_llm": False},
        headers=_auth(c1_token),
    )
    assert reextract.status_code == 200, reextract.text
    assert reextract.json()["extractions"]

    sections = dict(record["sections"])
    sections["presenting"] = (
        sections["presenting"] + "\n咨询师补充：已约定睡眠日记。"
    ).strip()
    patched = await db_client.patch(
        f"/api/v1/records/{record_id}",
        json={"sections": sections},
        headers=_auth(c1_token),
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["version_count"] == 2
    assert patched.json()["change_rate"] is not None

    confirmed = await db_client.post(
        f"/api/v1/records/{record_id}/confirm",
        headers=_auth(c1_token),
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["confirmed_at"] is not None

    redraft = await db_client.post(
        f"/api/v1/conversations/{conversation_id}/records/draft",
        json={"use_llm": False},
        headers=_auth(c1_token),
    )
    assert redraft.status_code == 409

    c2_token = await _login(db_client, "c2@campus.edu.cn", "Counselor123")
    other = await db_client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=_auth(c2_token),
    )
    assert other.status_code == 404

    student_access = await db_client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=_auth(student_token),
    )
    assert student_access.status_code == 403

    logs = await db_client.get(
        "/api/v1/admin/audit-logs",
        params={"limit": 100},
        headers=_auth(admin_token),
    )
    assert logs.status_code == 200
    actions = {item["action"] for item in logs.json()["items"]}
    assert {
        "conversation.create",
        "conversation.extract",
        "record.draft",
        "record.update",
        "record.confirm",
    } <= actions
