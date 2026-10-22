import uuid

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    password_hash = hash_password("correct horse battery staple")
    assert password_hash != "correct horse battery staple"
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    assert decode_access_token(token) == user_id


def test_tampered_token_rejected() -> None:
    token = create_access_token(uuid.uuid4())
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    try:
        decode_access_token(tampered)
    except Exception:
        return
    raise AssertionError("篡改后的 token 不应通过校验")
