from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


class TestPasswordHashing:
    def test_hash_password(self):
        hashed = hash_password("test123")
        assert hashed != "test123"
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        hashed = hash_password("test123")
        assert verify_password("test123", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("test123")
        assert verify_password("wrong", hashed) is False

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("test123")
        h2 = hash_password("test123")
        assert h1 != h2  # bcrypt uses random salt


class TestJWT:
    def test_create_and_decode_token(self):
        data = {"sub": "user123", "role": "admin"}
        token = create_access_token(data)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"

    def test_decode_invalid_token(self):
        payload = decode_access_token("invalid.token.here")
        assert payload is None

    def test_token_contains_expiry(self):
        data = {"sub": "user123"}
        token = create_access_token(data)
        payload = decode_access_token(token)
        assert payload is not None
        assert "exp" in payload