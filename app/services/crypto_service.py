from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa


class CryptoService:
    """Service for cryptographic signature verification."""

    @staticmethod
    def verify_signature(public_key_pem: str, payload: bytes, signature: bytes, algorithm: str = "ecdsa") -> bool:
        """Verify a signature against a payload using the provided public key.

        Args:
            public_key_pem: PEM-formatted public key string.
            payload: The bytes that were signed.
            signature: The signature bytes to verify.
            algorithm: "ecdsa" (default) or "rsa".

        Returns:
            True if the signature is valid, False otherwise.
        """
        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode())
        except (ValueError, TypeError):
            return False

        # Convert Web Crypto raw ECDSA signature (64 bytes) to DER format for OpenSSL
        if isinstance(public_key, ec.EllipticCurvePublicKey) and len(signature) == 64:
            from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
            r = int.from_bytes(signature[:32], byteorder="big")
            s = int.from_bytes(signature[32:], byteorder="big")
            signature = encode_dss_signature(r, s)

        try:
            if isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(signature, payload, ec.ECDSA(hashes.SHA256()))
                return True
            elif isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(
                    signature,
                    payload,
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
                return True
            else:
                return False
        except InvalidSignature:
            return False
        except Exception:
            return False