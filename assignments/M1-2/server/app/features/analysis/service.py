"""사용자가 시작하는 자료 분석(T04.02, docs/decisions.md).

- 시작: 버전·AI 분석 제외·휴지통·내용 유무를 확인하고, 원자적으로 `analyzing`으로 바꾼 뒤 202를 돌려준다.
  실제 Provider 호출은 같은 프로세스의 백그라운드 작업(`run_job`)이 한다.
- 완료된 같은 입력(입력 지문 `analysis_result_fp`)이면 새 요청 키여도 Provider를 부르지 않고 기존 결과를 준다.
- 분석 상태·결과는 `transform`으로 써서 사용자 `version`을 올리지 않는다. 분석 중에도 사용자는 자료를 고칠 수 있고,
  끝났을 때 내용이 바뀌었으면 결과를 버린다(`input_changed`).
- 서버가 재시작되어 작업이 사라지면 `analysis_deadline_at`이 지난 뒤 조회 때 `analysis_stale`로 보인다.
  몰래 다시 호출하지 않고, 사용자가 다시 시작할 때만 호출한다.
- 로그에는 작업 ID·상태·오류 종류만 남긴다(PRD §14).
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from app.core.config import ConfigError
from app.core.context import RequestContext
from app.core.errors import NoChange
from app.core.firestore import NotFound, Store, VersionConflict
from app.features.analysis import usage
from app.features.analysis.prompts import PROMPT_VERSION
from app.features.analysis.provider import AnalysisAdapter, ProviderError
from app.features.analysis.schemas import CONTENT_FIELDS, INPUT_FIELDS, content_hash
from app.features.materials.service import COLLECTION, analysis_stale, public
from app.features.projects import service as projects

log = logging.getLogger("ai_secretary.analysis")


class AnalysisRefused(NoChange):
    """분석할 수 없는 자료다(409). reason: trashed | ai_excluded | no_content."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class AnalysisInProgress(NoChange):
    """이미 분석 중인 자료다(409)."""


class _Superseded(NoChange):
    """늦게 끝난 작업이 더 새 작업이나 다른 상태를 덮어쓰지 않게 한다."""


@dataclass(frozen=True)
class Job:
    material_id: str
    job_id: str
    fingerprint: str
    snapshot: dict  # 시작 시점의 자료. 이 내용만 Provider에 보낸다
    projects: list[dict]
    usage_day: str | None = None  # 사용량을 예약한 서울 날짜(T04.03). 환불·결과 기록은 이 날짜에 한다


def input_fingerprint(doc: dict, offered: list[dict]) -> str:
    """보낼 내용 + 활성 프로젝트 목록 + 프롬프트 버전. 모델명은 넣지 않는다(모델 교체로 전부 재분석되지 않게)."""
    data = {
        "content": content_hash(doc),
        "projects": sorted([p["id"], p["name"]] for p in offered),
        "prompt": PROMPT_VERSION,
    }
    return hashlib.sha256(json.dumps(data, ensure_ascii=False).encode()).hexdigest()


def _check_allowed(doc: dict) -> None:
    if doc.get("lifecycle") != "active":
        raise AnalysisRefused("trashed")
    if doc.get("ai_excluded"):
        raise AnalysisRefused("ai_excluded")
    if not any(doc.get(name) for name in CONTENT_FIELDS):
        raise AnalysisRefused("no_content")


def _active_projects(store: Store, ctx: RequestContext) -> list[dict]:
    return [{"id": p["id"], "name": p["name"]} for p in projects.list_projects(store, ctx)]


def start_analysis(store: Store, ctx: RequestContext, material_id: str, expected_version: int,
                   timeout_seconds: int, daily_limit: int) -> tuple[int, dict, Job | None]:
    """(상태 코드, 응답 본문, 실행할 작업). 재사용·한도 대기면 작업이 없다."""
    doc = store.get(ctx, COLLECTION, material_id)  # 남의 자료·다른 모드는 404
    if doc["version"] != expected_version:
        raise VersionConflict(doc["version"])
    _check_allowed(doc)
    offered = _active_projects(store, ctx)
    fp = input_fingerprint(doc, offered)
    # 지문에 프롬프트 버전이 들어 있지만, 버전 기록도 함께 확인해 이전 기준의 결과를 재사용하지 않는다.
    if (doc.get("analysis_status") == "done" and doc.get("analysis_result_fp") == fp
            and doc.get("analysis_prompt_version") == PROMPT_VERSION):
        return 200, {"status": "reused", "material": public(doc)}, None

    now = datetime.now(timezone.utc)
    if doc.get("analysis_status") == "analyzing" and not analysis_stale(doc, now):
        raise AnalysisInProgress()  # 사용량을 예약하기 전에 거른다

    def check(current: dict) -> None:
        if current["version"] != expected_version:
            raise VersionConflict(current["version"])
        _check_allowed(current)
        if current.get("analysis_status") == "analyzing" and not analysis_stale(current, now):
            raise AnalysisInProgress()

    day = usage.reserve(store, ctx.owner_id, "analysis", daily_limit)
    if day is None:
        # 오늘 한도에 도달했다. 실패가 아니라 '호출 한도 대기'로 남기고 AI를 부르지 않는다(PRD §14).
        # 날짜가 바뀌어도 저절로 시작하지 않으며, 사용자가 다시 시작해야 한다.
        def wait(current: dict) -> dict:
            check(current)
            return {"analysis_status": "quota_waiting", "analysis_error": None}

        waiting = store.transform(ctx, COLLECTION, material_id, wait)
        log.info("analysis quota waiting")
        return 200, {"status": "quota_waiting", "material": public(waiting)}, None

    job_id = uuid.uuid4().hex
    # 서버가 재시작되어 작업이 사라졌다고 볼 시점. Provider 요청 시간의 두 배로 둔다.
    deadline = (now + timedelta(seconds=2 * timeout_seconds)).isoformat()

    def claim(current: dict) -> dict:
        check(current)
        return {
            "analysis_status": "analyzing",
            "analysis_job_id": job_id,
            "analysis_started_at": now.isoformat(),
            "analysis_deadline_at": deadline,
            "analysis_finished_at": None,
            "analysis_error": None,
        }

    try:
        updated = store.transform(ctx, COLLECTION, material_id, claim)
    except Exception:
        usage.refund(store, ctx.owner_id, day, "analysis")  # 시작하지 못했으므로 예약을 돌려준다
        raise
    snapshot = {name: updated.get(name) for name in (*INPUT_FIELDS, "url", "ai_excluded")}
    log.info("analysis accepted job=%s", job_id)
    job = Job(material_id, job_id, fp, snapshot, offered, day)
    return 202, {"status": "accepted", "material": public(updated)}, job


def _settle_usage(store: Store, ctx: RequestContext, job: Job, *, sent: bool, failed: bool,
                  tokens: int | None) -> None:
    """예약한 사용량을 정산한다. 보내기 전 실패만 환불하고, 보낸 요청은 실패·429도 사용으로 남긴다."""
    if job.usage_day is None:
        return
    try:
        if sent:
            usage.record_sent(store, ctx.owner_id, job.usage_day, failed=failed, tokens=tokens)
        else:
            usage.refund(store, ctx.owner_id, job.usage_day, "analysis")
    except Exception:  # noqa: BLE001 — 정산 실패는 사용으로 남는 쪽(한도를 넘지 않는 쪽)이다
        log.exception("analysis job=%s usage settle failed", job.job_id)


def run_job(store: Store, ctx: RequestContext, job: Job, adapter_factory: Callable[[], AnalysisAdapter]) -> None:
    """백그라운드에서 Provider를 한 번 부르고 결과를 저장한다. 자동 재시도는 하지 않는다."""
    result, error, sent, tokens = None, None, True, None
    try:
        result = adapter_factory().analyze_material(job.snapshot, job.projects)
        tokens = result.total_tokens
    except ProviderError as exc:
        # 응답을 받은 뒤 검증에 실패한 경우에도 그 응답의 토큰을 정산에 넘긴다.
        error, sent, tokens = exc.kind, exc.request_sent, exc.total_tokens
    except ConfigError:
        error, sent = "missing_ai_settings", False
    except Exception:  # noqa: BLE001 — 원인 본문은 남기지 않는다. 호출 여부를 모르므로 보낸 것으로 센다
        log.exception("analysis job=%s internal error", job.job_id)
        error = "internal_error"
    finished = datetime.now(timezone.utc).isoformat()
    _settle_usage(store, ctx, job, sent=sent, failed=error is not None, tokens=tokens)

    def finish(current: dict) -> dict:
        if current.get("analysis_job_id") != job.job_id or current.get("analysis_status") != "analyzing":
            raise _Superseded()
        base = {
            "analysis_job_id": None,
            "analysis_finished_at": finished,
            "analysis_request_sent": sent,
            "analysis_total_tokens": tokens,
        }
        # 분석 중에 AI 분석 제외를 켰거나 내용이 바뀌었으면 결과를 저장하지 않는다. 이미 보낸 요청은 되돌릴 수
        # 없으므로 사용량 기록(`analysis_request_sent`)만 남긴다. 제외는 내용 지문에 없으므로 따로 확인한다.
        discard = ("ai_excluded" if current.get("ai_excluded")
                   else "input_changed" if content_hash(current) != content_hash(job.snapshot) else None)
        if discard:
            has_content = any(current.get(name) for name in CONTENT_FIELDS)
            return {**base, "analysis_status": "awaiting_start" if has_content else "link_only",
                    "analysis_error": discard}
        if error == "rate_limited":
            # Provider 요청 한도(429)는 실패가 아니라 호출 한도 대기로 둔다(PRD §14). 재개는 사용자가 한다.
            return {**base, "analysis_status": "quota_waiting", "analysis_error": error}
        if error:
            return {**base, "analysis_status": "failed", "analysis_error": error}
        return {
            **base, **result.to_fields(),
            "analysis_status": "done", "analysis_error": None, "analysis_model": result.model,
            "analysis_result_fp": job.fingerprint, "ai_content_hash": content_hash(job.snapshot),
            "analysis_prompt_version": PROMPT_VERSION,
        }

    try:
        saved = store.transform(ctx, COLLECTION, job.material_id, finish)
    except (_Superseded, NotFound):
        log.info("analysis job=%s superseded", job.job_id)
        return
    except Exception:  # noqa: BLE001 — 저장 실패 시 상태는 analyzing으로 남고 기한 뒤 확인 필요로 보인다
        log.exception("analysis job=%s save failed", job.job_id)
        return
    log.info("analysis job=%s %s %s", job.job_id, saved["analysis_status"], saved.get("analysis_error") or "")
