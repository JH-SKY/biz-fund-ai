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
from src.app.domains.chat.model import ChatLog
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
        return ChatMonitorResponseData(items=items)

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
        admin_id: uuid.UUID,  # [추가] 로그용
        client_ip: str | None,
    ) -> list[AuditLogItem]:
        rows = await self._repo.list_audit_logs()
        out: list[AuditLogItem] = []
        for r in rows:
            ts = r.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            out.append(
                AuditLogItem(
                    admin_id=str(r.admin_id),
                    action=r.action_type,
                    target=str(r.target_id) if r.target_id else None,
                    created_at=ts.isoformat().replace("+00:00", "Z"),
                )
            )
        return out

    async def batch_status(self) -> list[BatchStatusItem]:
        rows = await self._system_service.list_latest_batch_per_job()
        items: list[BatchStatusItem] = []
        for r in rows:
            lr = r.started_at
            if lr.tzinfo is None:
                lr = lr.replace(tzinfo=timezone.utc)
            last_run = lr.strftime("%Y-%m-%d %H:%M")
            items.append(
                BatchStatusItem(
                    job_name=r.job_name,
                    last_run=last_run,
                    status=r.status,
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
        await self._repo.add_audit_log(
            admin_id=admin_id,
            action_type="FEEDBACK_CORRECTION_CREATE",
            target_id=feedback_id,
            changes=body.model_dump(),
            ip_address=client_ip,
        )
        await self._session.commit()
        now = datetime.now(timezone.utc)
        return {
            "note_id": str(uuid.uuid4()),
            "feedback_id": str(feedback_id),
            "question_pattern": body.question_pattern,
            "expected_answer": body.expected_answer,
            "applies_to_agent": body.applies_to_agent,
            "is_active": body.is_active,
            "created_by": str(admin_id),
            "created_at": self._to_iso(now),
        }

    async def list_corrections(self, *, page: int, size: int) -> dict[str, Any]:
        _ = (page, size)
        return {"items": [], "total_count": 0, "total_pages": 0}

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
        return {"range": range_value, "points": []}

    async def monitoring_cost(self, *, target_date: date | None) -> dict[str, Any]:
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()

        stmt = select(func.coalesce(func.sum(ChatLog.total_cost), 0)).where(
            ChatLog.role == "assistant",
            func.date(ChatLog.created_at) == target_date,
        )
        total_usd_raw = (await self._session.execute(stmt)).scalar() or 0
        total_usd = float(total_usd_raw)

        return {
            "date": target_date.isoformat(),
            "total_usd": round(total_usd, 6),
            "total_krw": round(total_usd * 1350, 2),
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "by_model": [
                {
                    "model": "unknown",
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": round(total_usd, 6),
                    "cost_krw": round(total_usd * 1350, 2),
                }
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

        clicks_expr = func.count(LeadRequest.id).label("clicks")
        grouped_stmt = (
            select(LeadRequest.lead_type, clicks_expr)
            .where(LeadRequest.created_at >= start_dt, LeadRequest.created_at < end_dt)
            .group_by(LeadRequest.lead_type)
            .order_by(desc(clicks_expr))
        )
        grouped = (await self._session.execute(grouped_stmt)).all()
        solution_clicks = [
            {
                "solution_key": lead_type or "UNKNOWN",
                "solution_label": lead_type or "UNKNOWN",
                "clicks": int(clicks),
                "conversions": int(clicks),
                "conversion_rate_pct": 100.0 if int(clicks) > 0 else 0.0,
            }
            for lead_type, clicks in grouped
        ]

        return {
            "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
            "consultation_bookings": int(consultation_bookings),
            "solution_clicks": solution_clicks,
            "revenue_estimate_krw": None,
        }
