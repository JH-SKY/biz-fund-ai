# src/app/domains/admin/service.py
"""관리자 비즈니스 로직 및 트랜잭션 경계."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import ADMIN_JWT_EXPIRE_HOURS, ADMIN_POLICY_AGENCY_NAME
from src.app.core.security import create_admin_access_token, verify_password
from src.app.domains.admin.model import Admin
from src.app.domains.admin.repository import AdminRepository, utc_start_of_today
from src.app.domains.admin.schema import (
    AdminLoginRequest,
    AdminUserItem,
    AdminUserListData,
    AuditLogItem,
    BatchDetailData,
    BatchStatusItem,
    ChatMonitorItem,
    ChatMonitorResponseData,
    CorrectionNoteRequest,
    ContentPatchRequest,
    ContentPublishRequest,
    ContentPublishResponseData,
    DashboardStatsData,
    PolicyCreateRequest,
    PolicyCreateResponseData,
    PolicyPatchRequest,
)
from src.app.domains.auth.model import User
from src.app.domains.auth.service import AuthService
from src.app.domains.biz_pick.service import BizPickService
from src.app.domains.chat.model import AgentCtaLog, AgentNodeLog, AgentRunLog, ChatLog
from src.app.domains.chat.service import ChatService
from src.app.domains.diagnosis.service import DiagnosisService
from src.app.domains.policy.model import PolicyStatus
from src.app.domains.policy.service import PolicyService
from src.app.domains.policy.sync_service import BizinfoSyncService
from src.app.domains.system.model import LeadRequest
from src.app.domains.system.service import SystemService


class AdminService:
    """관리자 유스케이스. 타 도메인은 Service를 통해 통신한다."""

    def __init__(
        self,
        session: AsyncSession,
        repo: AdminRepository,
        auth_service: AuthService,
        chat_service: ChatService,
        policy_service: PolicyService,
        biz_pick_service: BizPickService,
        system_service: SystemService,
        diagnosis_service: DiagnosisService,
        sync_service: BizinfoSyncService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._auth_service = auth_service
        self._chat_service = chat_service
        self._policy_service = policy_service
        self._biz_pick_service = biz_pick_service
        self._system_service = system_service
        self._diagnosis_service = diagnosis_service
        self._sync_service = sync_service

    @staticmethod
    def _to_iso(ts: datetime | None) -> str | None:
        if ts is None:
            return None
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.isoformat().replace("+00:00", "Z")

    @staticmethod
    def _feedback_reason_label(reason: str | None) -> str:
        mapping = {
            "INFO_WRONG": "정보 오류",
            "NOT_APPLICABLE": "조건 불일치",
            "DIFFICULT_TERM": "용어 어려움",
            "OTHER": "기타",
        }
        key = (reason or "OTHER").upper()
        return mapping.get(key, "기타")

    @staticmethod
    def _range_to_since(range_value: str) -> datetime:
        now = datetime.now(timezone.utc)
        if range_value == "1h":
            return now - timedelta(hours=1)
        if range_value == "24h":
            return now - timedelta(hours=24)
        if range_value == "7d":
            return now - timedelta(days=7)
        return now - timedelta(days=30)

    @staticmethod
    def _normalize_status(status: str | None) -> str | None:
        if not status:
            return None
        return status.upper()

    def _build_run_filters(
        self,
        *,
        since: datetime,
        intent: str | None = None,
        model: str | None = None,
        fallback_only: bool | None = None,
        status: str | None = None,
    ) -> list[Any]:
        filters: list[Any] = [AgentRunLog.created_at >= since]
        if intent:
            filters.append(AgentRunLog.route_intent == intent)
        if model:
            filters.append(AgentRunLog.model_name == model)
        if fallback_only is True:
            filters.append(AgentRunLog.fallback_mode.isnot(None))
        elif fallback_only is False:
            filters.append(AgentRunLog.fallback_mode.is_(None))
        normalized_status = self._normalize_status(status)
        if normalized_status:
            filters.append(AgentRunLog.status == normalized_status)
        return filters

    async def login(self, body: AdminLoginRequest) -> dict:
        admin = await self._repo.get_admin_by_login_id(body.login_id)
        if admin is None or not admin.is_active:
            raise HTTPException(
                status_code=401, detail="로그인 정보가 올바르지 않습니다."
            )
        if not verify_password(body.password, admin.password):
            raise HTTPException(
                status_code=401, detail="로그인 정보가 올바르지 않습니다."
            )
        token = create_admin_access_token(admin_id=admin.id)
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=ADMIN_JWT_EXPIRE_HOURS)
        ).isoformat().replace("+00:00", "Z")
        return {
            "admin_token": token,
            "admin_id": str(admin.id),
            "name": admin.login_id,
            "role": str(admin.role),
            "expires_at": expires_at,
        }

    async def create_policy(
        self,
        body: PolicyCreateRequest,
        *,
        admin: Admin,
        client_ip: str | None,
    ) -> PolicyCreateResponseData:
        target_logic = {"target_region": body.target_region}
        row = await self._policy_service.create_policy_internal(
            title=body.title,
            agency_name=ADMIN_POLICY_AGENCY_NAME,
            support_type=body.category,
            content_raw=body.content,
            start_date=body.apply_start_date,
            end_date=body.apply_end_date,
            target_logic=target_logic,
            status=PolicyStatus.RECRUITING,
        )
        ts = row.created_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        created_at = ts.isoformat().replace("+00:00", "Z")
        await self._repo.add_audit_log(
            admin_id=admin.id,
            action_type="CREATE_POLICY",
            target_id=row.id,
            changes={"title": body.title},
            ip_address=client_ip,
        )
        await self._session.commit()
        return PolicyCreateResponseData(policy_id=str(row.id), created_at=created_at)

    async def patch_policy(
        self,
        policy_id: uuid.UUID,
        body: PolicyPatchRequest,
        *,
        admin: Admin,
        client_ip: str | None,
    ) -> None:
        row = await self._policy_service.get_policy_by_id_internal(policy_id)
        if row is None:
            raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")
        await self._policy_service.patch_policy_internal(
            row,
            title=body.title,
            apply_end_date=body.apply_end_date,
            content=body.content,
        )
        await self._repo.add_audit_log(
            admin_id=admin.id,
            action_type="UPDATE_POLICY",
            target_id=row.id,
            changes=body.model_dump(exclude_unset=True),
            ip_address=client_ip,
        )
        await self._session.commit()

    async def publish_content(
        self,
        body: ContentPublishRequest,
        *,
        admin: Admin,
        client_ip: str | None,
    ) -> ContentPublishResponseData:
        row = await self._biz_pick_service.create_biz_pick_internal(
            title=body.title,
            category="GENERAL",
            content_html=body.body_html,
            thumbnail_url=body.thumbnail_url,
            is_published=body.is_published,
        )
        await self._repo.add_audit_log(
            admin_id=admin.id,
            action_type="PUBLISH_CONTENT",
            target_id=row.id,
            changes={"title": body.title, "is_published": body.is_published},
            ip_address=client_ip,
        )
        await self._session.commit()
        return ContentPublishResponseData(content_id=str(row.id))

    async def patch_content(
        self,
        content_id: uuid.UUID,
        body: ContentPatchRequest,
        *,
        admin: Admin,
        client_ip: str | None,
    ) -> None:
        row = await self._biz_pick_service.get_biz_pick_by_id_internal(content_id)
        if row is None:
            raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")
        await self._biz_pick_service.patch_biz_pick_internal(
            row,
            title=body.title,
            body_html=body.body_html,
            thumbnail_url=body.thumbnail_url,
            is_published=body.is_published,
        )
        await self._repo.add_audit_log(
            admin_id=admin.id,
            action_type="UPDATE_CONTENT",
            target_id=row.id,
            changes=body.model_dump(exclude_unset=True),
            ip_address=client_ip,
        )
        await self._session.commit()

    async def list_chat_monitor(
        self,
        *,
        user_id: uuid.UUID | None,
        admin_id: uuid.UUID,  # [추가] 로그용
        client_ip: str | None,
        page: int,
        size: int,
    ) -> ChatMonitorResponseData:
        logs = await self._chat_service.list_user_chat_logs_page(
            user_id=user_id,
            page=page,
            size=size,
        )
        await self._repo.add_audit_log(
            admin_id=admin_id,
            action_type="CHAT_MONITOR_VIEW",
            target_id=user_id,
            changes={"page": page, "size": size},
            ip_address=client_ip,
        )
        # 중요: 조회의 경우 session.commit()은 필수는 아니나,
        # 로그 저장(INSERT)을 확정하기 위해 commit을 호출하는 것이 실무적 안전책입니다.
        await self._session.commit()
        items: list[ChatMonitorItem] = []
        for ulog in logs:
            assistant = await self._chat_service.find_first_assistant_after(
                room_id=ulog.room_id,
                after=ulog.created_at,
            )
            ts = ulog.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            items.append(
                ChatMonitorItem(
                    session_id=str(ulog.room_id),
                    user_msg=ulog.content,
                    ai_res=assistant.content if assistant else "",
                    timestamp=ts.isoformat().replace("+00:00", "Z"),
                )
            )
        return ChatMonitorResponseData(
            items=items,
            total_count=len(items),
            total_pages=1,
        )

    async def dashboard_stats(self) -> DashboardStatsData:
        start = utc_start_of_today()
        new_users = await self._auth_service.count_new_users_since(start)
        active_chats = await self._chat_service.count_chat_logs_since(start)
        top = await self._policy_service.list_top_policies_by_views(5)
        popular = [
            {
                "policy_id": str(p.id),
                "title": p.title,
                "view_count": p.view_count,
            }
            for p in top
        ]
        return DashboardStatsData(
            new_users_today=new_users,
            active_chats_today=active_chats,
            popular_policies=popular,
        )

    async def list_audit_logs(
        self,
        *,
        admin_id: uuid.UUID,
        client_ip: str | None,
        page: int = 1,
        size: int = 25,
    ) -> dict:
        rows, total = await self._repo.list_audit_logs_page(page=page, size=size)
        out: list[AuditLogItem] = []
        for r, admin_name in rows:
            ts = r.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            out.append(
                AuditLogItem(
                    audit_id=str(r.id),
                    admin_id=str(r.admin_id),
                    admin_name=admin_name,
                    action=r.action_type,
                    target=str(r.target_id) if r.target_id else None,
                    ip_address=r.ip_address,
                    diff=r.changes if isinstance(r.changes, dict) else None,
                    created_at=ts.isoformat().replace("+00:00", "Z"),
                )
            )
        total_pages = (total + size - 1) // size if size > 0 else 0
        return {
            "items": [i.model_dump() for i in out],
            "total_count": total,
            "total_pages": total_pages,
        }

    async def batch_status(self) -> list[BatchStatusItem]:
        try:
            rows = await self._system_service.list_latest_batch_per_job()
        except Exception:
            # processed_count 등 신규 컬럼이 아직 DB에 없을 때 빈 목록 반환
            return []

        # APScheduler에서 등록된 job의 다음 실행 시간 수집
        scheduler_next_runs: dict[str, str] = {}
        try:
            from src.app.worker.scheduler import _scheduler
            if _scheduler.running:
                for job in _scheduler.get_jobs():
                    nrt = job.next_run_time
                    if nrt:
                        scheduler_next_runs[job.id] = nrt.isoformat()
        except Exception:
            pass

        # APScheduler job_id → BatchLog job_name 매핑
        SCHEDULER_JOB_MAP = {
            "daily_policy_sync": "POLICY_DAILY_SYNC",
        }

        items: list[BatchStatusItem] = []
        seen_job_names: set[str] = set()

        for r in rows:
            lr = r.started_at
            if lr.tzinfo is None:
                lr = lr.replace(tzinfo=timezone.utc)
            last_run = lr.isoformat()

            duration_ms: int | None = None
            if r.finished_at:
                fin = r.finished_at
                if fin.tzinfo is None:
                    fin = fin.replace(tzinfo=timezone.utc)
                duration_ms = int((fin - lr).total_seconds() * 1000)

            # 해당 job_name에 대응하는 APScheduler next_run 찾기
            next_run: str | None = None
            for sched_id, batch_name in SCHEDULER_JOB_MAP.items():
                if r.job_name == batch_name:
                    next_run = scheduler_next_runs.get(sched_id)
                    break

            items.append(
                BatchStatusItem(
                    job_id=str(r.id),
                    job_name=r.job_name,
                    last_run=last_run,
                    status=r.status,
                    total_count=r.total_count if r.total_count else None,
                    processed_count=getattr(r, "processed_count", None),
                    success_count=r.success_count if r.success_count is not None else None,
                    fail_count=r.fail_count if r.fail_count is not None else None,
                    duration_ms=duration_ms,
                    next_run=next_run,
                )
            )
            seen_job_names.add(r.job_name)

        # 아직 한 번도 실행된 적 없는 스케줄러 job은 플레이스홀더로 추가
        for sched_id, batch_name in SCHEDULER_JOB_MAP.items():
            if batch_name not in seen_job_names:
                next_run = scheduler_next_runs.get(sched_id)
                items.append(
                    BatchStatusItem(
                        job_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, batch_name)),
                        job_name=batch_name,
                        last_run=None,
                        status="SCHEDULED",
                        next_run=next_run,
                    )
                )

        return items

    async def batch_detail(self, job_id: uuid.UUID) -> BatchDetailData:
        row = await self._system_service.get_batch_log_by_id(job_id)
        if row is None:
            raise HTTPException(status_code=404, detail="배치 로그를 찾을 수 없습니다.")
        raw = row.error_details
        if raw is None:
            raw_log = ""
        elif isinstance(raw, str):
            raw_log = raw
        else:
            raw_log = json.dumps(raw, ensure_ascii=False)
        return BatchDetailData(job_id=str(row.id), raw_log=raw_log)

    async def list_users(
        self,
        *,
        page: int,
        size: int,
        admin_id: uuid.UUID,
        client_ip: str | None,  # 수정: ip_address → client_ip (router 호출 규약 통일)
        search_keyword: str | None,
        only_active: bool = True,
    ) -> AdminUserListData:
        rows, total = await self._auth_service.list_users_page(
            page=page,
            size=size,
            search_keyword=search_keyword,
            only_active=only_active,
        )

        await self._repo.add_audit_log(
            admin_id=admin_id,
            action_type="USER_LIST_VIEW",
            target_id=None,
            changes={"page": page, "search": search_keyword},
            ip_address=client_ip,
        )
        total_pages = (total + size - 1) // size if size > 0 else 0
        items: list[AdminUserItem] = []
        for u in rows:
            ts = u.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            items.append(
                AdminUserItem(
                    user_id=str(u.id),
                    name=u.name,
                    email=u.email,
                    status=u.status,
                    is_active=u.is_active,
                    created_at=ts.isoformat().replace("+00:00", "Z"),
                )
            )
        return AdminUserListData(
            items=items,
            total_count=total,
            total_pages=total_pages,
        )

    async def set_user_active(
        self,
        *,
        user_id: uuid.UUID,
        is_active: bool,
        admin_id: uuid.UUID,
        client_ip: str | None,
    ) -> None:
        await self._auth_service.set_user_active(user_id=user_id, is_active=is_active)
        await self._repo.add_audit_log(
            admin_id=admin_id,
            action_type="USER_ACTIVATE" if is_active else "USER_DEACTIVATE",
            target_id=user_id,
            changes={"is_active": is_active},
            ip_address=client_ip,
        )
        await self._session.commit()

    async def list_users_page(
        self,
        *,
        page: int,
        size: int,
        search_keyword: str | None,
        only_active: bool = True,
    ) -> tuple[list[User], int]:
        rows, total = await self._repo.list_users_page(
            page=page, size=size, search_keyword=search_keyword, only_active=only_active
        )
        return list(rows), total

    # ---------------------------------------------------------
    # [신규] 진단 및 시뮬레이션 모니터링 (Diagnosis Domain 협력)
    # ---------------------------------------------------------

    async def list_diagnosis_monitor(
        self,
        *,
        admin_id: uuid.UUID,
        client_ip: str | None,
        sim_type: str | None = "DIAGNOSIS",
    ) -> list:
        """
        1. 기능: [관리자] 전수 진단/시뮬레이션 로그 모니터링.
        2. 설계 의도: 시스템 전체에서 발생하는 AI 진단 비용과 결과의 적절성을 관리자가 감시합니다.
        3. 메커니즘: DiagnosisService의 관리 전용 메서드를 호출하여 도메인 경계를 준수합니다.
        """
        # DiagnosisService에 관리자용 조회 로직이 구현되어 있어야 함
        logs = await self._diagnosis_service.get_all_logs_for_admin(sim_type=sim_type)

        await self._repo.add_audit_log(
            admin_id=admin_id,
            action_type="DIAGNOSIS_MONITOR_VIEW",
            target_id=None,
            changes={"sim_type": sim_type},
            ip_address=client_ip,
        )
        await self._session.commit()

        # 실무에서는 여기서 전용 Admin Schema로 변환하여 리턴합니다.
        return logs

    async def get_diagnosis_detail_admin(
        self,
        diagnosis_id: uuid.UUID,
        admin_id: uuid.UUID,
        client_ip: str | None,
    ) -> Any:
        """
        1. 기능: 특정 진단 결과 상세 조회 (관리용).
        2. 설계 의도: 사용자 권한 체크 없이 관리자가 기술적 문제나 CS 대응을 위해 상세 로그를 확인합니다.
        """
        log = await self._diagnosis_service.get_log_detail_for_admin(diagnosis_id)

        await self._repo.add_audit_log(
            admin_id=admin_id,
            action_type="DIAGNOSIS_DETAIL_VIEW",
            target_id=diagnosis_id,
            changes={},
            ip_address=client_ip,
        )
        await self._session.commit()
        return log

    async def sync_bootstrap_policies(self, count: int = 1000):
        """과거 데이터 대량 적재 위임"""
        return await self._sync_service.bootstrap_historical_policies(
            total_count=count
        )

    async def sync_daily_policies(self):
        """일일 최신 정책 업데이트 위임"""
        return await self._sync_service.sync_recent_policies()

    async def run_policy_sync(
        self,
        *,
        page_start: int = 1,
        page_end: int = 1,
        rows_per_page: int = 100,
        with_ai: bool = False,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        """관리자 수동 트리거용 정책 수집 실행.

        run_policy_sync 의 모든 파라미터를 그대로 노출하여,
        관리자가 API 를 통해 원하는 범위·옵션으로 수집을 실행할 수 있도록 한다.
        """
        return await self._sync_service.run_policy_sync(
            job_name="POLICY_ADMIN_MANUAL",
            page_start=page_start,
            page_end=page_end,
            rows_per_page=rows_per_page,
            with_ai=with_ai,
            date_from=date_from,
            date_to=date_to,
        )

    async def sync_full_policies(
        self, *, with_ai: bool = False, rows_per_page: int = 100
    ) -> dict:
        """기업마당 전체 공고 전수 수집 위임 (totalCount 기반 자동 계산)."""
        return await self._sync_service.run_policy_sync_full(
            with_ai=with_ai, rows_per_page=rows_per_page
        )

    async def list_feedback(
        self,
        *,
        reason: str | None,
        is_resolved: bool,
        page: int,
        size: int,
    ) -> dict[str, Any]:
        if is_resolved:
            return {"items": [], "total_count": 0, "total_pages": 0}

        filters = [ChatLog.role == "assistant", ChatLog.is_disliked.is_(True)]
        if reason:
            filters.append(ChatLog.feedback_code == reason)

        total_stmt = select(func.count(ChatLog.id)).where(*filters)
        total = (await self._session.execute(total_stmt)).scalar() or 0
        total_pages = (total + size - 1) // size if size > 0 else 0

        stmt = (
            select(ChatLog, User.name)
            .join(User, User.id == ChatLog.user_id)
            .where(*filters)
            .order_by(desc(ChatLog.created_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        rows = (await self._session.execute(stmt)).all()

        items: list[dict[str, Any]] = []
        for log, user_name in rows:
            reason_code = (log.feedback_code or "OTHER").upper()
            items.append(
                {
                    "feedback_id": str(log.id),
                    "session_id": str(log.room_id),
                    "message_id": str(log.id),
                    "user_id": str(log.user_id),
                    "user_name": user_name,
                    "reason": reason_code,
                    "reason_label": self._feedback_reason_label(reason_code),
                    "user_comment": log.feedback_text,
                    "ai_response_snippet": (log.content or "")[:200],
                    "created_at": self._to_iso(log.created_at),
                    "is_resolved": False,
                }
            )
        return {"items": items, "total_count": total, "total_pages": total_pages}

    async def get_feedback_context(self, feedback_id: uuid.UUID) -> dict[str, Any]:
        stmt = (
            select(ChatLog, User.name)
            .join(User, User.id == ChatLog.user_id)
            .where(ChatLog.id == feedback_id, ChatLog.role == "assistant")
        )
        row = (await self._session.execute(stmt)).one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="피드백을 찾을 수 없습니다.")
        feedback_log, user_name = row

        conv_stmt = (
            select(ChatLog)
            .where(ChatLog.room_id == feedback_log.room_id)
            .order_by(ChatLog.created_at.asc())
            .limit(100)
        )
        conv_rows = (await self._session.execute(conv_stmt)).scalars().all()
        conversation = [
            {
                "message_id": str(log.id),
                "role": log.role,
                "content": log.content,
                "referenced_policies": [],
                "created_at": self._to_iso(log.created_at),
            }
            for log in conv_rows
        ]

        matched_policies: list[dict[str, Any]] = []
        if feedback_log.ref_policy_id:
            policy = await self._policy_service.get_policy_by_id_internal(
                feedback_log.ref_policy_id
            )
            if policy is not None:
                matched_policies.append(
                    {
                        "policy_id": str(policy.id),
                        "title": policy.title,
                        "score": 100.0,
                    }
                )

        reason_code = (feedback_log.feedback_code or "OTHER").upper()
        return {
            "feedback": {
                "feedback_id": str(feedback_log.id),
                "session_id": str(feedback_log.room_id),
                "message_id": str(feedback_log.id),
                "user_id": str(feedback_log.user_id),
                "user_name": user_name,
                "reason": reason_code,
                "reason_label": self._feedback_reason_label(reason_code),
                "user_comment": feedback_log.feedback_text,
                "ai_response_snippet": (feedback_log.content or "")[:200],
                "created_at": self._to_iso(feedback_log.created_at),
                "is_resolved": False,
            },
            "conversation": conversation,
            "matching_logic_snapshot": {
                "applied_at": self._to_iso(feedback_log.created_at),
                "rules": [],
                "matched_policies": matched_policies,
                "raw_payload": {
                    "ref_policy_id": (
                        str(feedback_log.ref_policy_id)
                        if feedback_log.ref_policy_id
                        else None
                    )
                },
            },
        }

    async def create_correction_note(
        self,
        *,
        feedback_id: uuid.UUID,
        body: CorrectionNoteRequest,
        admin_id: uuid.UUID,
        client_ip: str | None,
    ) -> dict[str, Any]:
        from src.app.domains.admin.model import CorrectionNote

        note = CorrectionNote(
            feedback_id=feedback_id,
            created_by_admin_id=admin_id,
            question_pattern=body.question_pattern,
            expected_answer=body.expected_answer,
            applies_to_agent=body.applies_to_agent,
            is_active=body.is_active if body.is_active is not None else True,
        )
        self._session.add(note)

        await self._repo.add_audit_log(
            admin_id=admin_id,
            action_type="FEEDBACK_CORRECTION_CREATE",
            target_id=feedback_id,
            changes=body.model_dump(),
            ip_address=client_ip,
        )
        await self._session.commit()
        await self._session.refresh(note)
        return {
            "note_id": str(note.id),
            "feedback_id": str(note.feedback_id),
            "question_pattern": note.question_pattern,
            "expected_answer": note.expected_answer,
            "applies_to_agent": note.applies_to_agent,
            "is_active": note.is_active,
            "created_by": str(admin_id),
            "created_at": self._to_iso(note.created_at),
        }

    async def list_contents(
        self,
        *,
        page: int,
        size: int,
        category: str | None = None,
    ) -> dict[str, Any]:
        rows, total_count, total_pages = await self._biz_pick_service.list_biz_picks_internal(
            category=category,
            page=page,
            size=size,
        )
        items = []
        for row in rows:
            created_at = self._to_iso(row.created_at)
            items.append(
                {
                    "content_id": str(row.id),
                    "title": row.title,
                    "thumbnail_url": row.thumbnail_url,
                    "category": row.category,
                    "view_count": row.view_count,
                    "like_count": row.like_count,
                    "is_liked": False,
                    "created_at": created_at,
                    "is_published": row.is_published,
                    "scheduled_at": None,
                    "updated_at": created_at,
                }
            )
        return {
            "items": items,
            "total_count": total_count,
            "total_pages": total_pages,
        }

    async def get_content_detail(self, content_id: uuid.UUID) -> dict[str, Any]:
        row = await self._biz_pick_service.get_biz_pick_by_id_internal(content_id)
        if row is None:
            raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")
        return {
            "content_id": str(row.id),
            "title": row.title,
            "body_html": row.content_html,
            "author": "비즈업 에디터",
            "view_count": row.view_count,
            "like_count": row.like_count,
            "is_liked": False,
            "related_policies": [],
            "tags": [row.category] if row.category else [],
            "thumbnail_url": row.thumbnail_url,
            "category": row.category,
            "is_published": row.is_published,
            "scheduled_at": None,
        }

    async def delete_content(
        self,
        *,
        content_id: uuid.UUID,
        admin: Admin,
        client_ip: str | None,
    ) -> None:
        row = await self._biz_pick_service.get_biz_pick_by_id_internal(content_id)
        if row is None:
            raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")
        await self._biz_pick_service.delete_biz_pick_internal(row)
        await self._repo.add_audit_log(
            admin_id=admin.id,
            action_type="DELETE_CONTENT",
            target_id=row.id,
            changes={"title": row.title},
            ip_address=client_ip,
        )
        await self._session.commit()

    async def list_corrections(self, *, page: int, size: int) -> dict[str, Any]:
        from sqlalchemy import func as sa_func, select as sa_select
        from src.app.domains.admin.model import CorrectionNote

        offset = (page - 1) * size
        count_stmt = sa_select(sa_func.count()).select_from(CorrectionNote)
        total = (await self._session.execute(count_stmt)).scalar() or 0
        total_pages = (total + size - 1) // size if size > 0 else 0

        stmt = (
            sa_select(CorrectionNote)
            .order_by(CorrectionNote.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        rows = (await self._session.execute(stmt)).scalars().all()

        items = [
            {
                "note_id": str(n.id),
                "feedback_id": str(n.feedback_id),
                "question_pattern": n.question_pattern,
                "expected_answer": n.expected_answer,
                "applies_to_agent": n.applies_to_agent,
                "is_active": n.is_active,
                "created_by": str(n.created_by_admin_id) if n.created_by_admin_id else None,
                "created_at": self._to_iso(n.created_at),
            }
            for n in rows
        ]
        return {"items": items, "total_count": total, "total_pages": total_pages}

    async def monitoring_health(self) -> dict[str, Any]:
        rows = await self._system_service.list_latest_batch_per_job()
        if not rows:
            return {
                "status": "HEALTHY",
                "latency_p50_ms": 0,
                "latency_p95_ms": 0,
                "error_rate_pct": 0.0,
                "uptime_pct": 100.0,
                "last_incident_at": None,
                "components": [],
            }

        bad_statuses = {"FAILED", "ERROR", "DOWN"}
        failed = [r for r in rows if str(r.status).upper() in bad_statuses]
        error_rate = round((len(failed) / len(rows)) * 100, 2) if rows else 0.0
        status = "HEALTHY" if not failed else "DEGRADED"
        last_incident = max((r.started_at for r in failed), default=None)

        latencies: list[int] = []
        for row in rows:
            if row.finished_at is None or row.started_at is None:
                continue
            delta = row.finished_at - row.started_at
            latencies.append(max(0, int(delta.total_seconds() * 1000)))
        latencies.sort()
        if latencies:
            p50 = latencies[len(latencies) // 2]
            p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
        else:
            p50 = 0
            p95 = 0

        components = [
            {
                "name": row.job_name,
                "status": (
                    "HEALTHY"
                    if str(row.status).upper() not in bad_statuses
                    else "DEGRADED"
                ),
                "message": str(row.status),
            }
            for row in rows
        ]
        return {
            "status": status,
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "error_rate_pct": error_rate,
            "uptime_pct": round(max(0.0, 100.0 - error_rate), 2),
            "last_incident_at": self._to_iso(last_incident),
            "components": components,
        }

    async def monitoring_latency(self, *, range_value: str) -> dict[str, Any]:
        from sqlalchemy import literal_column, text

        now = datetime.now(timezone.utc)

        # range_value에 따라 버킷 단위와 조회 기간을 결정
        if range_value == "1h":
            since = now - timedelta(hours=1)
        elif range_value == "24h":
            since = now - timedelta(hours=24)
        else:  # 7d
            since = now - timedelta(days=7)

        # PostgreSQL date_trunc으로 버킷별 p50/p95 집계
        if range_value == "1h":
            # 5분 버킷: epoch를 300초 단위로 내림
            bucket_expr = text(
                "to_timestamp(floor(extract(epoch from created_at) / 300) * 300)"
            ).label("ts")
        elif range_value == "24h":
            bucket_expr = func.date_trunc("hour", ChatLog.created_at).label("ts")
        else:
            bucket_expr = func.date_trunc("day", ChatLog.created_at).label("ts")

        stmt = (
            select(
                bucket_expr,
                func.percentile_cont(0.5)
                .within_group(ChatLog.response_time_ms)
                .label("p50"),
                func.percentile_cont(0.95)
                .within_group(ChatLog.response_time_ms)
                .label("p95"),
                func.count(ChatLog.id).label("cnt"),
            )
            .where(
                ChatLog.role == "system",
                ChatLog.response_time_ms.isnot(None),
                ChatLog.created_at >= since,
            )
            .group_by(literal_column("ts"))
            .order_by(literal_column("ts"))
        )
        rows = (await self._session.execute(stmt)).all()

        points = [
            {
                "timestamp": row.ts.isoformat() if row.ts else None,
                "p50_ms": int(row.p50) if row.p50 is not None else None,
                "p95_ms": int(row.p95) if row.p95 is not None else None,
                "count": row.cnt,
                "error_rate_pct": 0.0,
            }
            for row in rows
        ]
        return {"range": range_value, "points": points}

    async def monitoring_cost(self, *, target_date: date | None) -> dict[str, Any]:
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()

        # 모델별 토큰 집계
        model_stmt = (
            select(
                ChatLog.model_name,
                func.coalesce(func.sum(ChatLog.tokens_in), 0).label("tokens_in"),
                func.coalesce(func.sum(ChatLog.tokens_out), 0).label("tokens_out"),
                func.coalesce(func.sum(ChatLog.total_cost), 0).label("cost_usd"),
            )
            .where(
                ChatLog.role == "system",
                ChatLog.model_name.isnot(None),
                func.date(ChatLog.created_at) == target_date,
            )
            .group_by(ChatLog.model_name)
        )
        model_rows = (await self._session.execute(model_stmt)).all()

        # GPT 단가표 (USD/1K tokens, 2024 기준 gpt-4o-mini)
        _price_in = {"gpt-4o-mini": 0.00015, "gpt-4o": 0.005}
        _price_out = {"gpt-4o-mini": 0.0006, "gpt-4o": 0.015}

        by_model = []
        total_tokens_in = 0
        total_tokens_out = 0
        total_usd = 0.0

        for row in model_rows:
            model = row.model_name or "unknown"
            t_in = int(row.tokens_in)
            t_out = int(row.tokens_out)
            # DB에 total_cost가 없으면 단가로 추정
            cost = float(row.cost_usd)
            if cost == 0 and (t_in or t_out):
                cost = (
                    t_in / 1000 * _price_in.get(model, 0.00015)
                    + t_out / 1000 * _price_out.get(model, 0.0006)
                )
            total_tokens_in += t_in
            total_tokens_out += t_out
            total_usd += cost
            by_model.append({
                "model": model,
                "tokens_in": t_in,
                "tokens_out": t_out,
                "cost_usd": round(cost, 6),
                "cost_krw": round(cost * 1350, 2),
            })

        # 모델 정보가 없으면 total_cost 합계만 반환
        if not by_model:
            legacy_stmt = select(
                func.coalesce(func.sum(ChatLog.total_cost), 0)
            ).where(
                ChatLog.role == "assistant",
                func.date(ChatLog.created_at) == target_date,
            )
            total_usd = float((await self._session.execute(legacy_stmt)).scalar() or 0)

        return {
            "date": target_date.isoformat(),
            "total_usd": round(total_usd, 6),
            "total_krw": round(total_usd * 1350, 2),
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "by_model": by_model,
        }

    async def monitoring_agent_overview(
        self,
        *,
        range_value: str,
        intent: str | None = None,
        model: str | None = None,
        fallback_only: bool | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        since = self._range_to_since(range_value)
        run_filters = self._build_run_filters(
            since=since,
            intent=intent,
            model=model,
            fallback_only=fallback_only,
            status=status,
        )

        overview_stmt = select(
            func.count(AgentRunLog.id).label("runs"),
            func.count().filter(AgentRunLog.status == "SUCCESS").label("success_runs"),
            func.avg(AgentRunLog.total_latency_ms).label("avg_latency"),
            func.percentile_cont(0.5)
            .within_group(AgentRunLog.total_latency_ms)
            .label("p50_latency"),
            func.percentile_cont(0.95)
            .within_group(AgentRunLog.total_latency_ms)
            .label("p95_latency"),
            func.coalesce(func.sum(AgentRunLog.tokens_in), 0).label("tokens_in"),
            func.coalesce(func.sum(AgentRunLog.tokens_out), 0).label("tokens_out"),
            func.coalesce(func.sum(AgentRunLog.total_cost_usd), 0).label("total_cost_usd"),
            func.count().filter(AgentRunLog.fallback_mode.isnot(None)).label("fallback_runs"),
        ).where(*run_filters)
        overview = (await self._session.execute(overview_stmt)).one()

        intent_stmt = (
            select(
                AgentRunLog.route_intent,
                func.count(AgentRunLog.id).label("runs"),
                func.avg(AgentRunLog.total_latency_ms).label("avg_latency"),
                func.coalesce(func.sum(AgentRunLog.total_cost_usd), 0).label("cost_usd"),
                func.count().filter(AgentRunLog.status != "SUCCESS").label("error_runs"),
            )
            .where(*run_filters)
            .group_by(AgentRunLog.route_intent)
            .order_by(func.count(AgentRunLog.id).desc())
        )
        intent_rows = (await self._session.execute(intent_stmt)).all()

        model_stmt = (
            select(
                AgentRunLog.model_name,
                func.count(AgentRunLog.id).label("runs"),
                func.coalesce(func.sum(AgentRunLog.tokens_in), 0).label("tokens_in"),
                func.coalesce(func.sum(AgentRunLog.tokens_out), 0).label("tokens_out"),
                func.coalesce(func.sum(AgentRunLog.total_cost_usd), 0).label("cost_usd"),
            )
            .where(*run_filters, AgentRunLog.model_name.isnot(None))
            .group_by(AgentRunLog.model_name)
            .order_by(func.count(AgentRunLog.id).desc())
        )
        model_rows = (await self._session.execute(model_stmt)).all()

        cta_stmt = select(
            func.count(AgentCtaLog.id).label("cta_clicks"),
        ).join(
            AgentRunLog,
            AgentRunLog.id == AgentCtaLog.run_id,
            isouter=True,
        ).where(*run_filters)
        cta_clicks = int((await self._session.execute(cta_stmt)).scalar() or 0)

        dislike_stmt = select(func.count(ChatLog.id)).join(
            AgentRunLog,
            AgentRunLog.assistant_message_log_id == ChatLog.id,
        ).where(*run_filters, ChatLog.is_disliked.is_(True))
        dislike_feedback_count = int((await self._session.execute(dislike_stmt)).scalar() or 0)

        version_axes = [
            ("prompt_version", AgentRunLog.prompt_version),
            ("graph_version", AgentRunLog.graph_version),
            ("rag_strategy_version", AgentRunLog.rag_strategy_version),
        ]
        version_breakdowns: dict[str, list[dict[str, Any]]] = {}
        for key, column in version_axes:
            stmt = (
                select(
                    column.label("version"),
                    func.count(AgentRunLog.id).label("runs"),
                    func.avg(AgentRunLog.total_latency_ms).label("avg_latency"),
                    func.coalesce(func.sum(AgentRunLog.total_cost_usd), 0).label("cost_usd"),
                )
                .where(*run_filters)
                .group_by(column)
                .order_by(func.count(AgentRunLog.id).desc())
            )
            rows = (await self._session.execute(stmt)).all()
            version_breakdowns[key] = [
                {
                    "version": version or "unknown",
                    "runs": int(runs or 0),
                    "avg_latency_ms": int(avg_latency or 0),
                    "cost_usd": round(float(cost_usd or 0), 6),
                }
                for version, runs, avg_latency, cost_usd in rows
            ]

        total_runs = int(overview.runs or 0)
        success_runs = int(overview.success_runs or 0)
        fallback_runs = int(overview.fallback_runs or 0)
        return {
            "range": range_value,
            "filters": {
                "intent": intent,
                "model": model,
                "fallback_only": fallback_only,
                "status": self._normalize_status(status),
            },
            "total_runs": total_runs,
            "success_rate_pct": round((success_runs / total_runs) * 100, 2) if total_runs else 0.0,
            "avg_latency_ms": int(overview.avg_latency or 0),
            "p50_latency_ms": int(overview.p50_latency or 0),
            "p95_latency_ms": int(overview.p95_latency or 0),
            "total_tokens_in": int(overview.tokens_in or 0),
            "total_tokens_out": int(overview.tokens_out or 0),
            "total_cost_usd": round(float(overview.total_cost_usd or 0), 6),
            "total_cost_krw": round(float(overview.total_cost_usd or 0) * 1350, 2),
            "fallback_runs": fallback_runs,
            "cta_clicks": cta_clicks,
            "dislike_feedback_count": dislike_feedback_count,
            "quality_metrics": {
                "fallback_rate_pct": round((fallback_runs / total_runs) * 100, 2) if total_runs else 0.0,
                "dislike_feedback_rate_pct": round((dislike_feedback_count / total_runs) * 100, 2)
                if total_runs
                else 0.0,
            },
            "by_intent": [
                {
                    "intent": route_intent or "unknown",
                    "runs": int(runs or 0),
                    "avg_latency_ms": int(avg_latency or 0),
                    "cost_usd": round(float(cost_usd or 0), 6),
                    "error_rate_pct": round((int(error_runs or 0) / int(runs or 1)) * 100, 2),
                }
                for route_intent, runs, avg_latency, cost_usd, error_runs in intent_rows
            ],
            "by_model": [
                {
                    "model": model_name or "unknown",
                    "runs": int(runs or 0),
                    "tokens_in": int(tokens_in or 0),
                    "tokens_out": int(tokens_out or 0),
                    "cost_usd": round(float(cost_usd or 0), 6),
                }
                for model_name, runs, tokens_in, tokens_out, cost_usd in model_rows
            ],
            "by_prompt_version": version_breakdowns["prompt_version"],
            "by_graph_version": version_breakdowns["graph_version"],
            "by_rag_strategy_version": version_breakdowns["rag_strategy_version"],
        }

    async def monitoring_agent_nodes(
        self,
        *,
        range_value: str,
        intent: str | None = None,
        model: str | None = None,
        fallback_only: bool | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        since = self._range_to_since(range_value)
        run_filters = self._build_run_filters(
            since=since,
            intent=intent,
            model=model,
            fallback_only=fallback_only,
            status=status,
        )
        stmt = (
            select(
                AgentNodeLog.node_name,
                func.count(AgentNodeLog.id).label("executions"),
                func.avg(AgentNodeLog.latency_ms).label("avg_latency"),
                func.percentile_cont(0.95)
                .within_group(AgentNodeLog.latency_ms)
                .label("p95_latency"),
                func.coalesce(func.sum(AgentNodeLog.tokens_in), 0).label("tokens_in"),
                func.coalesce(func.sum(AgentNodeLog.tokens_out), 0).label("tokens_out"),
                func.coalesce(func.sum(AgentNodeLog.cost_usd), 0).label("cost_usd"),
                func.count().filter(AgentNodeLog.status != "SUCCESS").label("error_count"),
            )
            .join(AgentRunLog, AgentRunLog.id == AgentNodeLog.run_id)
            .where(*run_filters)
            .group_by(AgentNodeLog.node_name)
            .order_by(func.count(AgentNodeLog.id).desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return {
            "range": range_value,
            "filters": {
                "intent": intent,
                "model": model,
                "fallback_only": fallback_only,
                "status": self._normalize_status(status),
            },
            "items": [
                {
                    "node_name": node_name,
                    "executions": int(executions or 0),
                    "avg_latency_ms": int(avg_latency or 0),
                    "p95_latency_ms": int(p95_latency or 0),
                    "tokens_in": int(tokens_in or 0),
                    "tokens_out": int(tokens_out or 0),
                    "cost_usd": round(float(cost_usd or 0), 6),
                    "error_count": int(error_count or 0),
                    "error_rate_pct": round((int(error_count or 0) / int(executions or 1)) * 100, 2),
                }
                for (
                    node_name,
                    executions,
                    avg_latency,
                    p95_latency,
                    tokens_in,
                    tokens_out,
                    cost_usd,
                    error_count,
                ) in rows
            ],
        }

    async def monitoring_agent_runs(
        self,
        *,
        range_value: str,
        page: int,
        size: int,
        intent: str | None = None,
        model: str | None = None,
        fallback_only: bool | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        since = self._range_to_since(range_value)
        run_filters = self._build_run_filters(
            since=since,
            intent=intent,
            model=model,
            fallback_only=fallback_only,
            status=status,
        )
        total_stmt = select(func.count(AgentRunLog.id)).where(*run_filters)
        total = int((await self._session.execute(total_stmt)).scalar() or 0)
        total_pages = (total + size - 1) // size if size > 0 else 0

        stmt = (
            select(AgentRunLog)
            .where(*run_filters)
            .order_by(AgentRunLog.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return {
            "filters": {
                "intent": intent,
                "model": model,
                "fallback_only": fallback_only,
                "status": self._normalize_status(status),
            },
            "items": [
                {
                    "run_id": str(row.id),
                    "session_id": str(row.room_id),
                    "route_intent": row.route_intent,
                    "final_agent": row.final_agent,
                    "status": row.status,
                    "question_preview": row.question_preview,
                    "total_latency_ms": row.total_latency_ms,
                    "first_token_latency_ms": row.first_token_latency_ms,
                    "tokens_in": row.tokens_in,
                    "tokens_out": row.tokens_out,
                    "total_cost_usd": round(float(row.total_cost_usd or 0), 6),
                    "fallback_mode": row.fallback_mode,
                    "rag_hit_count": row.rag_hit_count,
                    "prompt_version": row.prompt_version,
                    "model_name": row.model_name,
                    "created_at": self._to_iso(row.created_at),
                }
                for row in rows
            ],
            "total_count": total,
            "total_pages": total_pages,
        }

    async def monitoring_agent_run_detail(self, *, run_id: uuid.UUID) -> dict[str, Any]:
        run_stmt = select(AgentRunLog).where(AgentRunLog.id == run_id)
        run = (await self._session.execute(run_stmt)).scalar_one_or_none()
        if run is None:
            raise HTTPException(status_code=404, detail="에이전트 실행 로그를 찾을 수 없습니다.")

        node_stmt = (
            select(AgentNodeLog)
            .where(AgentNodeLog.run_id == run_id)
            .order_by(AgentNodeLog.sequence.asc(), AgentNodeLog.created_at.asc())
        )
        nodes = (await self._session.execute(node_stmt)).scalars().all()
        cta_stmt = (
            select(AgentCtaLog)
            .where(AgentCtaLog.run_id == run_id)
            .order_by(AgentCtaLog.created_at.asc())
        )
        cta_events = (await self._session.execute(cta_stmt)).scalars().all()

        return {
            "run": {
                "run_id": str(run.id),
                "session_id": str(run.room_id),
                "route_intent": run.route_intent,
                "final_agent": run.final_agent,
                "status": run.status,
                "question_preview": run.question_preview,
                "total_latency_ms": run.total_latency_ms,
                "first_token_latency_ms": run.first_token_latency_ms,
                "tokens_in": run.tokens_in,
                "tokens_out": run.tokens_out,
                "total_cost_usd": round(float(run.total_cost_usd or 0), 6),
                "fallback_mode": run.fallback_mode,
                "fallback_reason": run.fallback_reason,
                "rag_hit_count": run.rag_hit_count,
                "prompt_version": run.prompt_version,
                "graph_version": run.graph_version,
                "rag_strategy_version": run.rag_strategy_version,
                "model_name": run.model_name,
                "error_code": run.error_code,
                "error_message": run.error_message,
                "created_at": self._to_iso(run.created_at),
            },
            "nodes": [
                {
                    "node_name": node.node_name,
                    "sequence": node.sequence,
                    "status": node.status,
                    "model_name": node.model_name,
                    "latency_ms": node.latency_ms,
                    "tokens_in": node.tokens_in,
                    "tokens_out": node.tokens_out,
                    "cost_usd": round(float(node.cost_usd or 0), 6),
                    "error_code": node.error_code,
                    "error_message": node.error_message,
                    "metadata": node.metadata or {},
                }
                for node in nodes
            ],
            "cta_events": [
                {
                    "cta_type": cta.cta_type,
                    "target_path": cta.target_path,
                    "ref_policy_id": str(cta.ref_policy_id) if cta.ref_policy_id else None,
                    "metadata": cta.metadata or {},
                    "created_at": self._to_iso(cta.created_at),
                }
                for cta in cta_events
            ],
        }

    async def list_unmet_demand(self, *, page: int, size: int) -> dict[str, Any]:
        keyword_expr = func.substr(func.replace(ChatLog.content, "\n", " "), 1, 60)
        grouped = (
            select(
                keyword_expr.label("keyword"),
                func.count(ChatLog.id).label("query_count"),
                func.max(ChatLog.created_at).label("last_asked_at"),
            )
            .where(ChatLog.role == "user")
            .group_by(keyword_expr)
            .subquery()
        )

        total_stmt = select(func.count()).select_from(grouped)
        total = (await self._session.execute(total_stmt)).scalar() or 0
        total_pages = (total + size - 1) // size if size > 0 else 0

        stmt = (
            select(grouped.c.keyword, grouped.c.query_count, grouped.c.last_asked_at)
            .order_by(desc(grouped.c.query_count), desc(grouped.c.last_asked_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        rows = (await self._session.execute(stmt)).all()

        items = [
            {
                "keyword": (keyword or "").strip(),
                "query_count": int(query_count),
                "last_asked_at": self._to_iso(last_asked_at),
                "related_sector_codes": [],
            }
            for keyword, query_count, last_asked_at in rows
            if (keyword or "").strip()
        ]
        return {"items": items, "total_count": total, "total_pages": total_pages}

    async def conversion_stats(
        self,
        *,
        from_date: date | None,
        to_date: date | None,
    ) -> dict[str, Any]:
        today = datetime.now(timezone.utc).date()
        if from_date is None:
            from_date = today.replace(day=1)
        if to_date is None:
            to_date = today
        if from_date > to_date:
            raise HTTPException(status_code=400, detail="from 날짜가 to 날짜보다 클 수 없습니다.")

        start_dt = datetime.combine(from_date, datetime.min.time())
        end_dt = datetime.combine(to_date + timedelta(days=1), datetime.min.time())

        booking_stmt = select(func.count(LeadRequest.id)).where(
            LeadRequest.created_at >= start_dt,
            LeadRequest.created_at < end_dt,
        )
        consultation_bookings = (await self._session.execute(booking_stmt)).scalar() or 0

        clicks_expr = func.count(AgentCtaLog.id).label("clicks")
        grouped_stmt = (
            select(AgentCtaLog.cta_type, clicks_expr)
            .where(AgentCtaLog.created_at >= start_dt, AgentCtaLog.created_at < end_dt)
            .group_by(AgentCtaLog.cta_type)
            .order_by(desc(clicks_expr))
        )
        grouped = (await self._session.execute(grouped_stmt)).all()
        solution_clicks = [
            {
                "solution_key": cta_type or "UNKNOWN",
                "solution_label": cta_type or "UNKNOWN",
                "clicks": int(clicks),
                "conversions": int(clicks),
                "conversion_rate_pct": 100.0 if int(clicks) > 0 else 0.0,
            }
            for cta_type, clicks in grouped
        ]

        return {
            "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
            "consultation_bookings": int(consultation_bookings),
            "solution_clicks": solution_clicks,
            "revenue_estimate_krw": None,
        }
