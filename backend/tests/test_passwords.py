from app.core.passwords import (
    hash_password,
    needs_rehash,
    password_policy_errors,
    verify_password,
)


def test_hash_and_verify_round_trip() -> None:
    hashed = hash_password("Correct-Horse-9")
    assert hashed.startswith("$argon2id$")
    assert verify_password("Correct-Horse-9", hashed)
    assert not verify_password("wrong", hashed)
    assert not needs_rehash(hashed)


def test_verify_rejects_garbage_hash() -> None:
    assert not verify_password("anything", "not-a-hash")


def test_password_policy() -> None:
    assert password_policy_errors("Correct-Horse-9") == []
    errors = password_policy_errors("short")
    assert any("between" in e for e in errors)
    assert any("upper-case" in e for e in errors)
    assert any("digit" in e for e in errors)
    assert password_policy_errors("alllowercase123") == ["must contain an upper-case letter"]
    assert password_policy_errors("ALLUPPERCASE123") == ["must contain a lower-case letter"]
