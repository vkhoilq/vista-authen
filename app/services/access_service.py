import base64
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import AuditLog, Checker, CheckerRole, Resident, ResidentStatus
from app.services.crypto_service import CryptoService


class AccessService:
    """Service for verifying QR access codes."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.crypto = CryptoService()

    async def verify(self, qr_payload: str, checker_id: uuid.UUID) -> dict:
        """Verify a QR code payload and return role-appropriate response.

        QR payload format: V1|{resident_id}|{timestamp}|{signature_b64}

        Returns a dict with at least 'status' and 'action' keys.
        """
        # Check payload size
        if len(qr_payload) > 10240:
            return await self._reject(
                action="scan_failed_bad_signature",
                checker_id=checker_id,
                details={"reason": "payload_too_large"},
            )

        # Parse QR payload
        parts = qr_payload.split("|")
        if len(parts) != 4 or parts[0] != "V1":
            return await self._reject(
                action="scan_failed_bad_signature",
                checker_id=checker_id,
                details={"reason": "invalid_format", "payload_prefix": qr_payload[:50]},
            )

        version, resident_id_str, timestamp_str, signature_b64 = parts

        # Parse resident_id
        try:
            resident_id = uuid.UUID(resident_id_str)
        except ValueError:
            return await self._reject(
                action="scan_failed_bad_signature",
                checker_id=checker_id,
                details={"reason": "invalid_resident_id"},
            )

        # Parse timestamp
        try:
            timestamp = int(timestamp_str)
        except ValueError:
            return await self._reject(
                action="scan_failed_bad_signature",
                checker_id=checker_id,
                details={"reason": "invalid_timestamp"},
            )

        # Replay protection: check timestamp tolerance
        now = int(datetime.now(timezone.utc).timestamp())
        if abs(now - timestamp) > settings.QR_TIMESTAMP_TOLERANCE_SEC:
            return await self._reject(
                action="scan_failed_expired",
                checker_id=checker_id,
                resident_id=resident_id,
                details={"timestamp": timestamp, "server_time": now, "diff": abs(now - timestamp)},
            )

        # Fetch resident
        resident = await self.db.get(Resident, resident_id)
        if resident is None or resident.status != ResidentStatus.ACTIVE or resident.public_key is None:
            return await self._reject(
                action="scan_failed_bad_signature",
                checker_id=checker_id,
                resident_id=resident_id,
                details={"reason": "resident_not_active"},
            )

        # Verify signature
        payload_str = f"{resident_id_str}|{timestamp_str}"
        try:
            signature_bytes = base64.b64decode(signature_b64)
        except Exception:
            return await self._reject(
                action="scan_failed_bad_signature",
                checker_id=checker_id,
                resident_id=resident_id,
                details={"reason": "invalid_signature_encoding"},
            )

        try:
            signature_valid = self.crypto.verify_signature(resident.public_key, payload_str.encode(), signature_bytes)
        except Exception as e:
            return await self._reject(
                action="scan_failed_bad_signature",
                checker_id=checker_id,
                resident_id=resident_id,
                details={"reason": "signature_verification_error", "error": str(e)},
            )

        if not signature_valid:
            return await self._reject(
                action="scan_failed_bad_signature",
                checker_id=checker_id,
                resident_id=resident_id,
                details={"reason": "signature_verification_failed"},
            )

        # Success — log and return
        checker = await self.db.get(Checker, checker_id)
        await self._log_action(
            action="scan_success",
            checker_id=checker_id,
            resident_id=resident_id,
            unit_id=resident.unit_id,
            details={"checker_role": checker.role if checker else None},
        )

        # Role-based response
        if checker and checker.role == CheckerRole.MANAGER:
            # Fetch unit info for manager
            from app.models.models import Unit

            unit = await self.db.get(Unit, resident.unit_id)
            return {
                "status": "valid",
                "resident_name": resident.name,
                "unit": unit.unit_number if unit else "Unknown",
                "phone": resident.phone,
            }
        else:
            return {"status": "valid"}

    async def _reject(
        self,
        action: str,
        checker_id: uuid.UUID | None = None,
        resident_id: uuid.UUID | None = None,
        unit_id: uuid.UUID | None = None,
        details: dict | None = None,
    ) -> dict:
        """Log a rejection and return the appropriate status."""
        # Try to find unit_id from resident if not provided
        if unit_id is None and resident_id is not None:
            resident = await self.db.get(Resident, resident_id)
            if resident:
                unit_id = resident.unit_id

        await self._log_action(
            action=action,
            checker_id=checker_id,
            resident_id=resident_id,
            unit_id=unit_id,
            details=details,
        )

        if action == "scan_failed_expired":
            return {"status": "expired"}
        return {"status": "invalid"}

    async def _log_action(
        self,
        action: str,
        checker_id: uuid.UUID | None = None,
        resident_id: uuid.UUID | None = None,
        unit_id: uuid.UUID | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        if details is None:
            details = {}
        if resident_id:
            details["resident_id"] = str(resident_id)

        log = AuditLog(
            action=action,
            actor_id=checker_id,
            actor_role="checker",
            unit_id=unit_id,
            details=details,
        )
        self.db.add(log)
        await self.db.flush()
        return log