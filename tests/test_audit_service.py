import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import AuditService


class TestAuditServiceLog:
    async def test_log_basic_action(self, db_session: AsyncSession):
        svc = AuditService(db_session)
        log = await svc.log(action="test_action")
        assert log.id is not None
        assert log.action == "test_action"
        assert log.timestamp is not None

    async def test_log_with_all_fields(self, db_session: AsyncSession):
        svc = AuditService(db_session)
        actor_id = uuid.uuid4()
        unit_id = uuid.uuid4()
        log = await svc.log(
            action="scan_success",
            actor_id=actor_id,
            actor_role="checker",
            unit_id=unit_id,
            details={"resident_id": str(uuid.uuid4())},
        )
        assert log.actor_id == actor_id
        assert log.actor_role == "checker"
        assert log.unit_id == unit_id
        assert log.details is not None


class TestAuditServiceListLogs:
    async def test_list_logs_empty(self, db_session: AsyncSession):
        svc = AuditService(db_session)
        logs, total = await svc.list_logs()
        assert total == 0
        assert len(logs) == 0

    async def test_list_logs_with_data(self, db_session: AsyncSession):
        svc = AuditService(db_session)
        await svc.log(action="scan_success", actor_role="checker")
        await svc.log(action="scan_failed_expired", actor_role="checker")
        await svc.log(action="registration_blocked", actor_role="resident_admin")

        logs, total = await svc.list_logs()
        assert total == 3
        assert len(logs) == 3

    async def test_list_logs_filter_by_action(self, db_session: AsyncSession):
        svc = AuditService(db_session)
        await svc.log(action="scan_success", actor_role="checker")
        await svc.log(action="scan_failed_expired", actor_role="checker")

        logs, total = await svc.list_logs(action="scan_success")
        assert total == 1
        assert logs[0].action == "scan_success"

    async def test_list_logs_filter_by_actor_role(self, db_session: AsyncSession):
        svc = AuditService(db_session)
        await svc.log(action="scan_success", actor_role="checker")
        await svc.log(action="registration_blocked", actor_role="resident_admin")

        logs, total = await svc.list_logs(actor_role="checker")
        assert total == 1
        assert logs[0].actor_role == "checker"

    async def test_list_logs_pagination(self, db_session: AsyncSession):
        svc = AuditService(db_session)
        for i in range(5):
            await svc.log(action=f"action_{i}")

        # Page 1, size 2
        logs, total = await svc.list_logs(page=1, page_size=2)
        assert total == 5
        assert len(logs) == 2

        # Page 2, size 2
        logs, total = await svc.list_logs(page=2, page_size=2)
        assert total == 5
        assert len(logs) == 2

        # Page 3, size 2
        logs, total = await svc.list_logs(page=3, page_size=2)
        assert total == 5
        assert len(logs) == 1

    async def test_list_logs_ordered_by_timestamp_desc(self, db_session: AsyncSession):
        svc = AuditService(db_session)
        await svc.log(action="first")
        await svc.log(action="second")
        await svc.log(action="third")

        logs, total = await svc.list_logs()
        assert total == 3
        # Most recent first
        assert logs[0].action == "third"
        assert logs[2].action == "first"