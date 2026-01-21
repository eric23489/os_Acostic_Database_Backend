import pytest
from datetime import timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from jose import JWTError


def test_password_hashing():
    password = "secret_password"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_jwt_token_creation_and_decoding():
    data = {"sub": "test@example.com"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "test@example.com"
    assert "exp" in decoded


def test_jwt_token_expired():
    # Create a token that expired 1 minute ago
    data = {"sub": "test@example.com"}
    expired_token = create_access_token(data, expires_delta=timedelta(minutes=-1))
    with pytest.raises(JWTError):
        decode_access_token(expired_token)
