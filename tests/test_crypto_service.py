import base64

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from app.services.crypto_service import CryptoService


class TestCryptoServiceECC:
    """Test ECC P-256 signature verification."""

    def test_verify_valid_ecc_signature(self):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        payload = b"resident-id|1700000000"
        signature = private_key.sign(payload, ec.ECDSA(hashes.SHA256()))

        assert CryptoService.verify_signature(public_pem, payload, signature) is True

    def test_verify_ecc_wrong_payload(self):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        payload = b"resident-id|1700000000"
        signature = private_key.sign(payload, ec.ECDSA(hashes.SHA256()))

        assert CryptoService.verify_signature(public_pem, b"wrong-payload", signature) is False

    def test_verify_ecc_wrong_key(self):
        private_key1 = ec.generate_private_key(ec.SECP256R1())
        private_key2 = ec.generate_private_key(ec.SECP256R1())
        public_pem2 = private_key2.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        payload = b"resident-id|1700000000"
        signature = private_key1.sign(payload, ec.ECDSA(hashes.SHA256()))

        # Signature from key1, verified with key2 → should fail
        assert CryptoService.verify_signature(public_pem2, payload, signature) is False

    def test_verify_ecc_corrupted_signature(self):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        payload = b"resident-id|1700000000"
        corrupted_sig = b"\x00" * 64

        assert CryptoService.verify_signature(public_pem, payload, corrupted_sig) is False

    def test_verify_ecc_base64_roundtrip(self):
        """Simulate the full QR flow: sign → base64 encode → decode → verify."""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        payload = b"resident-id|1700000000"
        signature = private_key.sign(payload, ec.ECDSA(hashes.SHA256()))
        sig_b64 = base64.b64encode(signature).decode()
        sig_bytes = base64.b64decode(sig_b64)

        assert CryptoService.verify_signature(public_pem, payload, sig_bytes) is True


class TestCryptoServiceRSA:
    """Test RSA 2048 signature verification."""

    def test_verify_valid_rsa_signature(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        payload = b"resident-id|1700000000"
        signature = private_key.sign(payload, padding.PKCS1v15(), hashes.SHA256())

        assert CryptoService.verify_signature(public_pem, payload, signature, algorithm="rsa") is True

    def test_verify_rsa_wrong_payload(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        payload = b"resident-id|1700000000"
        signature = private_key.sign(payload, padding.PKCS1v15(), hashes.SHA256())

        assert CryptoService.verify_signature(public_pem, b"wrong", signature, algorithm="rsa") is False


class TestCryptoServiceEdgeCases:
    def test_verify_invalid_pem(self):
        assert CryptoService.verify_signature("not-a-pem", b"payload", b"sig") is False

    def test_verify_empty_signature(self):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        assert CryptoService.verify_signature(public_pem, b"payload", b"") is False