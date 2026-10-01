"""소유자·모드로 격리된 문서 저장소.

모든 기능은 이 모듈을 거쳐서만 데이터를 읽고 쓴다. 저장소가 `owner_id`·`mode`를
요청 문맥(RequestContext)에서 직접 채우고, 조회할 때마다 다시 비교하므로
브라우저가 보낸 값으로 다른 소유자·모드의 자료에 닿을 수 없다.

- 최상위 컬렉션 + `owner_id`·`mode` 필드 구조다. 과제가 요구한 `data`·`conversations`
  컬렉션 이름을 그대로 쓴다.
- 문서마다 정수 `version`을 둔다. 수정은 기대 버전이 같을 때만 1 올린다.
- 시간은 UTC ISO-8601 문자열로 저장한다(PRD §9.2).
- `FirestoreStore`는 실제 Firestore, `MemoryStore`는 같은 규칙의 테스트용 구현이다.
"""
from __future__ import annotations

import base64
import copy
import json
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Protocol

from app.core.config import ConfigError, Settings
from app.core.context import RequestContext

FIREBASE_APP_NAME = "ai-secretary"

# MVP에서 쓰는 컬렉션. PC 관련 컬렉션은 확장 단계에서 추가한다.
COLLECTIONS = frozenset(
    {"materials", "intake_records", "settings", "projects", "data", "conversations", "idempotency"}
)
# 저장소가 관리하는 필드. 호출자가 넘긴 값은 무시하고 저장소가 정한다.
SYSTEM_FIELDS = frozenset({"id", "owner_id", "mode", "version", "created_at", "updated_at"})

MAX_PAGE_SIZE = 100
MAX_DOC_ID_BYTES = 1500  # Firestore 문서 ID 한도


class NotFound(Exception):
    """없거나, 다른 소유자·모드의 문서다. 존재 여부를 드러내지 않는다(404)."""


class VersionConflict(Exception):
    """기대한 버전과 현재 버전이 다르다(409)."""

    def __init__(self, current_version: int):
        super().__init__("version conflict")
        self.current_version = current_version


class InvalidCursor(ValueError):
    """페이지 커서를 해석할 수 없다(422)."""


@dataclass(frozen=True)
class Page:
    items: list[dict]
    next_cursor: str | None


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode_cursor(doc: Mapping[str, Any]) -> str:
    raw = json.dumps({"t": doc["created_at"], "id": doc["id"]}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _is_utc_iso(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.utcoffset() == timedelta(0)


def decode_cursor(cursor: str) -> tuple[str, str]:
    """encode_cursor가 만든 값만 받는다. 형식이 하나라도 틀리면 InvalidCursor(422)."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        # validate=True: 허용 밖 문자를 조용히 버리지 않고 오류로 본다.
        data = json.loads(base64.b64decode(padded.encode(), altchars=b"-_", validate=True))
    except (ValueError, TypeError, AttributeError):
        raise InvalidCursor("cursor") from None
    if not isinstance(data, dict):
        raise InvalidCursor("cursor")
    created_at, doc_id = data.get("t"), data.get("id")
    if not _is_utc_iso(created_at) or not _valid_doc_id(doc_id):
        raise InvalidCursor("cursor")
    return created_at, doc_id


def _check_collection(name: str) -> None:
    if name not in COLLECTIONS:
        raise ValueError(f"unknown collection: {name}")


def _valid_doc_id(doc_id: str) -> bool:
    """Firestore가 단일 문서 ID로 받는 값인가. `/`가 있으면 하위 컬렉션 경로가 되므로 거부한다."""
    return (
        isinstance(doc_id, str)
        and 0 < len(doc_id.encode()) <= MAX_DOC_ID_BYTES
        and "/" not in doc_id
        and doc_id not in (".", "..")
        and not (doc_id.startswith("__") and doc_id.endswith("__"))
    )


def _check_doc_id(collection: str, doc_id: str) -> None:
    # 형식이 틀린 ID도 없는 문서와 같이 404로 처리한다(SDK 오류가 500이 되지 않게).
    if not _valid_doc_id(doc_id):
        raise NotFound(collection)


def _new_id(doc_id: str | None) -> str:
    if doc_id is None:
        return uuid.uuid4().hex
    if not _valid_doc_id(doc_id):
        raise ValueError("invalid document id")
    return doc_id


def _expired(record: Mapping[str, Any], now_iso: str) -> bool:
    return record.get("expire_at", "") <= now_iso


def _user_fields(data: Mapping[str, Any]) -> dict:
    return {k: v for k, v in data.items() if k not in SYSTEM_FIELDS}


def _owned(doc: Mapping[str, Any] | None, ctx: RequestContext) -> bool:
    return bool(doc) and doc.get("owner_id") == ctx.owner_id and doc.get("mode") == ctx.mode


def _page_size(limit: int) -> int:
    return max(1, min(int(limit), MAX_PAGE_SIZE))


class Store(Protocol):
    def create(self, ctx: RequestContext, collection: str, data: Mapping[str, Any],
               doc_id: str | None = None) -> dict: ...

    def get(self, ctx: RequestContext, collection: str, doc_id: str) -> dict: ...

    def update(self, ctx: RequestContext, collection: str, doc_id: str,
               expected_version: int, changes: Mapping[str, Any]) -> dict: ...

    def list(self, ctx: RequestContext, collection: str, limit: int = 20,
             cursor: str | None = None) -> Page: ...

    def delete(self, ctx: RequestContext, collection: str, doc_id: str) -> None: ...

    # 중복 요청 기록(requests.py 전용). 소유자 단위로 키를 둔다.
    # 기록이 없거나 now_iso 기준으로 만료됐으면 record로 원자적으로 차지하고 None,
    # 아니면 기존 기록을 돌려준다.
    def claim_key(self, record_id: str, record: Mapping[str, Any], now_iso: str) -> dict | None: ...

    def finish_key(self, record_id: str, changes: Mapping[str, Any]) -> None: ...

    def release_key(self, record_id: str) -> None: ...


def _new_doc(ctx: RequestContext, data: Mapping[str, Any], doc_id: str) -> dict:
    stamp = now_utc()
    return {
        **_user_fields(data),
        "id": doc_id,
        "owner_id": ctx.owner_id,
        "mode": ctx.mode,
        "version": 1,
        "created_at": stamp,
        "updated_at": stamp,
    }


class MemoryStore:
    """테스트용 구현. 같은 인스턴스를 다시 감싸면 '서버 재시작 후' 상태를 흉내 낸다."""

    def __init__(self) -> None:
        self._docs: dict[str, dict[str, dict]] = {name: {} for name in COLLECTIONS}
        self._lock = threading.Lock()

    def create(self, ctx, collection, data, doc_id=None):
        _check_collection(collection)
        doc_id = _new_id(doc_id)
        with self._lock:
            if doc_id in self._docs[collection]:
                raise VersionConflict(self._docs[collection][doc_id]["version"])
            doc = _new_doc(ctx, data, doc_id)
            self._docs[collection][doc_id] = doc
            return copy.deepcopy(doc)

    def get(self, ctx, collection, doc_id):
        _check_collection(collection)
        _check_doc_id(collection, doc_id)
        doc = self._docs[collection].get(doc_id)
        if not _owned(doc, ctx):
            raise NotFound(collection)
        return copy.deepcopy(doc)

    def update(self, ctx, collection, doc_id, expected_version, changes):
        _check_collection(collection)
        _check_doc_id(collection, doc_id)
        with self._lock:
            doc = self._docs[collection].get(doc_id)
            if not _owned(doc, ctx):
                raise NotFound(collection)
            if doc["version"] != expected_version:
                raise VersionConflict(doc["version"])
            doc.update(_user_fields(changes))
            doc["version"] += 1
            doc["updated_at"] = now_utc()
            return copy.deepcopy(doc)

    def list(self, ctx, collection, limit=20, cursor=None):
        _check_collection(collection)
        size = _page_size(limit)
        docs = sorted(
            (d for d in self._docs[collection].values() if _owned(d, ctx)),
            key=lambda d: (d["created_at"], d["id"]),
        )
        if cursor:
            after = decode_cursor(cursor)
            docs = [d for d in docs if (d["created_at"], d["id"]) > after]
        page = [copy.deepcopy(d) for d in docs[: size + 1]]
        has_more = len(page) > size
        page = page[:size]
        return Page(page, encode_cursor(page[-1]) if has_more and page else None)

    def delete(self, ctx, collection, doc_id):
        _check_collection(collection)
        _check_doc_id(collection, doc_id)
        with self._lock:
            if not _owned(self._docs[collection].get(doc_id), ctx):
                raise NotFound(collection)
            del self._docs[collection][doc_id]

    def claim_key(self, record_id, record, now_iso):
        with self._lock:
            existing = self._docs["idempotency"].get(record_id)
            if existing is not None and not _expired(existing, now_iso):
                return copy.deepcopy(existing)
            self._docs["idempotency"][record_id] = dict(record)
            return None

    def finish_key(self, record_id, changes):
        with self._lock:
            self._docs["idempotency"][record_id].update(changes)

    def release_key(self, record_id):
        with self._lock:
            self._docs["idempotency"].pop(record_id, None)


def firebase_app(settings: Settings):
    """서비스 계정으로 초기화한 Firebase 앱(인증과 같은 이름을 공유). 설정 오류는 ConfigError."""
    settings.require("firebase")
    try:
        account = json.loads(settings.get("FIREBASE_SERVICE_ACCOUNT_JSON"))
        if not isinstance(account, dict):
            raise ValueError
    except ValueError:
        # 서비스 계정 내용이 오류 메시지·로그에 남지 않게 변수 이름만 알린다.
        raise ConfigError("FIREBASE_SERVICE_ACCOUNT_JSON은 JSON 객체여야 합니다") from None

    import firebase_admin
    from firebase_admin import credentials

    try:
        return firebase_admin.get_app(FIREBASE_APP_NAME)
    except ValueError:
        try:
            return firebase_admin.initialize_app(credentials.Certificate(account), name=FIREBASE_APP_NAME)
        except ValueError:
            raise ConfigError("FIREBASE_SERVICE_ACCOUNT_JSON이 서비스 계정 형식이 아닙니다") from None


class FirestoreStore:
    """실제 Firestore 구현. 목록 조회에는 firestore.indexes.json의 복합 색인이 필요하다."""

    def __init__(self, client) -> None:
        self._db = client

    @classmethod
    def from_settings(cls, settings: Settings) -> "FirestoreStore":
        from firebase_admin import firestore

        return cls(firestore.client(firebase_app(settings)))

    def _ref(self, collection: str, doc_id: str):
        _check_collection(collection)
        _check_doc_id(collection, doc_id)
        return self._db.collection(collection).document(doc_id)

    def create(self, ctx, collection, data, doc_id=None):
        from google.api_core.exceptions import AlreadyExists

        ref = self._ref(collection, _new_id(doc_id))
        doc = _new_doc(ctx, data, ref.id)
        try:
            ref.create(doc)  # 같은 ID가 있으면 덮어쓰지 않고 실패한다.
        except AlreadyExists:
            snap = ref.get()
            raise VersionConflict(int((snap.to_dict() or {}).get("version", 0))) from None
        return doc

    def get(self, ctx, collection, doc_id):
        snap = self._ref(collection, doc_id).get()
        doc = snap.to_dict() if snap.exists else None
        if not _owned(doc, ctx):
            raise NotFound(collection)
        return doc

    def update(self, ctx, collection, doc_id, expected_version, changes):
        from google.cloud import firestore as gcf

        ref = self._ref(collection, doc_id)

        @gcf.transactional
        def run(tx):
            snap = ref.get(transaction=tx)
            doc = snap.to_dict() if snap.exists else None
            if not _owned(doc, ctx):
                raise NotFound(collection)
            if doc["version"] != expected_version:
                raise VersionConflict(doc["version"])
            doc.update(_user_fields(changes))
            doc["version"] += 1
            doc["updated_at"] = now_utc()
            tx.set(ref, doc)
            return doc

        return run(self._db.transaction())

    def list(self, ctx, collection, limit=20, cursor=None):
        from google.cloud.firestore_v1 import FieldFilter
        from google.cloud.firestore_v1.field_path import FieldPath

        _check_collection(collection)
        size = _page_size(limit)
        query = (
            self._db.collection(collection)
            .where(filter=FieldFilter("owner_id", "==", ctx.owner_id))
            .where(filter=FieldFilter("mode", "==", ctx.mode))
            .order_by("created_at")
            .order_by(FieldPath.document_id())
        )
        if cursor:
            created_at, doc_id = decode_cursor(cursor)
            query = query.start_after([created_at, self._ref(collection, doc_id)])
        docs = [s.to_dict() for s in query.limit(size + 1).stream()]
        has_more = len(docs) > size
        docs = docs[:size]
        return Page(docs, encode_cursor(docs[-1]) if has_more and docs else None)

    def delete(self, ctx, collection, doc_id):
        self.get(ctx, collection, doc_id)  # 소유권 확인. 남의 문서면 NotFound.
        self._ref(collection, doc_id).delete()

    def claim_key(self, record_id, record, now_iso):
        from google.cloud import firestore as gcf

        ref = self._ref("idempotency", record_id)

        # 읽기·만료 판단·덮어쓰기를 한 트랜잭션에서 한다. 동시에 들어온 요청 중 하나만 차지하고,
        # 나머지는 충돌로 재시도된 뒤 먼저 차지한 기록을 보게 된다.
        @gcf.transactional
        def run(tx):
            snap = ref.get(transaction=tx)
            existing = snap.to_dict() if snap.exists else None
            if existing is not None and not _expired(existing, now_iso):
                return existing
            tx.set(ref, dict(record))
            return None

        return run(self._db.transaction())

    def finish_key(self, record_id, changes):
        self._ref("idempotency", record_id).update(dict(changes))

    def release_key(self, record_id):
        self._ref("idempotency", record_id).delete()
