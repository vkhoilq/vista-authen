import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import ActivationToken, AuditLog

class CleanupService:
    """Service to handle background database maintenance and data pruning."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def purge_expired_tokens(self) -> int:
        """Purge activation tokens that are either expired or already used."""
        now = datetime.now(timezone.utc)
        
        stmt = delete(ActivationToken).where(
            (ActivationToken.expires_at < now) | (ActivationToken.used_at.is_not(None))
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def purge_old_audit_logs(self) -> int:
        """Purge audit logs older than the configured retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
        
        stmt = delete(AuditLog).where(AuditLog.timestamp < cutoff)
        result = await self.db.execute(stmt)
        return result.rowcount

    async def cleanup_all(self) -> dict:
        """Run all cleanup tasks and commit the changes."""
        purged_tokens = await self.purge_expired_tokens()
        purged_logs = await self.purge_old_audit_logs()
        await self.db.commit()
        
        return {
            "purged_tokens": purged_tokens,
            "purged_audit_logs": purged_logs
        }
