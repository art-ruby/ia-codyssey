"""저장소 계층. Firestore 가 정본이고, 자격증명이 없을 때만 메모리로 떨어진다.

라우터는 이 인터페이스만 알면 되므로, 나중에 저장소를 바꿔도 API 코드는
그대로다. 두 구현이 같은 dict 모양을 주고받게 맞춰 두었다.
"""
from __future__ import annotations

import json
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from ..config import Settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


class Store(ABC):
    """후보(data)와 대화(conversations) 두 컬렉션만 다룬다.

    명세 3절: 컬렉션을 과도하게 세분화하지 않는다. decisions 는 별도
    컬렉션을 만들지 않고 후보 문서 안의 decision 필드로 둔다 — 판단은
    후보의 상태이지 독립 개체가 아니기 때문이다.
    """

    backend_name: str = "abstract"

    # ── data ──────────────────────────────────────
    @abstractmethod
    def list_candidates(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def create_candidate(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def update_candidate(self, candidate_id: str, patch: dict[str, Any]) -> dict[str, Any] | None: ...

    @abstractmethod
    def delete_candidate(self, candidate_id: str) -> bool: ...

    @abstractmethod
    def bulk_create_candidates(self, payloads: list[dict[str, Any]]) -> int: ...

    @abstractmethod
    def find_by_radar_id(self, radar_id: str) -> dict[str, Any] | None: ...

    # ── conversations ─────────────────────────────
    @abstractmethod
    def list_conversations(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def create_conversation(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def replace_conversation(self, conversation_id: str, payload: dict[str, Any]) -> dict[str, Any] | None: ...

    @abstractmethod
    def delete_conversation(self, conversation_id: str) -> bool: ...


class InMemoryStore(Store):
    """자격증명 없이 돌리는 개발/채점용. 재시작하면 사라진다는 점을 health 가 알린다."""

    backend_name = "memory"

    def __init__(self) -> None:
        self._candidates: dict[str, dict[str, Any]] = {}
        self._conversations: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def list_candidates(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(v) for v in self._candidates.values()]

    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        with self._lock:
            found = self._candidates.get(candidate_id)
            return dict(found) if found else None

    def create_candidate(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = {**payload, "id": _new_id(), "created_at": _now(), "updated_at": _now()}
            self._candidates[record["id"]] = record
            return dict(record)

    def update_candidate(self, candidate_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            current = self._candidates.get(candidate_id)
            if current is None:
                return None
            current.update({**patch, "updated_at": _now()})
            return dict(current)

    def delete_candidate(self, candidate_id: str) -> bool:
        with self._lock:
            return self._candidates.pop(candidate_id, None) is not None

    def bulk_create_candidates(self, payloads: list[dict[str, Any]]) -> int:
        with self._lock:
            for payload in payloads:
                record = {**payload, "id": _new_id(), "created_at": _now(), "updated_at": _now()}
                self._candidates[record["id"]] = record
            return len(payloads)

    def find_by_radar_id(self, radar_id: str) -> dict[str, Any] | None:
        with self._lock:
            for value in self._candidates.values():
                if value.get("radar_id") == radar_id:
                    return dict(value)
            return None

    def list_conversations(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(v) for v in self._conversations.values()]

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with self._lock:
            found = self._conversations.get(conversation_id)
            return dict(found) if found else None

    def create_conversation(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = {**payload, "id": _new_id(), "created_at": _now(), "updated_at": _now()}
            self._conversations[record["id"]] = record
            return dict(record)

    def replace_conversation(self, conversation_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            current = self._conversations.get(conversation_id)
            if current is None:
                return None
            current.update({**payload, "updated_at": _now()})
            return dict(current)

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._lock:
            return self._conversations.pop(conversation_id, None) is not None


class FirestoreStore(Store):
    """firebase-admin 을 서비스 계정 JSON 문자열로 초기화한다.

    Render 같은 환경에서 파일을 올리기 어려우므로 JSON 자체를 환경 변수로
    받는다(과제 7절 예시의 FIREBASE_SERVICE_ACCOUNT_JSON).
    """

    backend_name = "firestore"

    def __init__(self, settings: Settings) -> None:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            info = json.loads(settings.firebase_service_account_json)
            firebase_admin.initialize_app(credentials.Certificate(info))
        self._db = firestore.client()
        self._data = settings.firestore_collection_data
        self._conv = settings.firestore_collection_conversations

    @staticmethod
    def _with_id(doc) -> dict[str, Any]:
        return {**doc.to_dict(), "id": doc.id}

    def list_candidates(self) -> list[dict[str, Any]]:
        return [self._with_id(d) for d in self._db.collection(self._data).stream()]

    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        doc = self._db.collection(self._data).document(candidate_id).get()
        return self._with_id(doc) if doc.exists else None

    def create_candidate(self, payload: dict[str, Any]) -> dict[str, Any]:
        record = {**payload, "created_at": _now(), "updated_at": _now()}
        ref = self._db.collection(self._data).document()
        ref.set(record)
        return {**record, "id": ref.id}

    def update_candidate(self, candidate_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        ref = self._db.collection(self._data).document(candidate_id)
        if not ref.get().exists:
            return None
        ref.update({**patch, "updated_at": _now()})
        return self._with_id(ref.get())

    def delete_candidate(self, candidate_id: str) -> bool:
        ref = self._db.collection(self._data).document(candidate_id)
        if not ref.get().exists:
            return False
        ref.delete()
        return True

    def bulk_create_candidates(self, payloads: list[dict[str, Any]]) -> int:
        written = 0
        # Firestore 배치 상한은 500 이다. 표본 100~200건도 안전하게 나눠 쓴다.
        for start in range(0, len(payloads), 400):
            batch = self._db.batch()
            for payload in payloads[start : start + 400]:
                batch.set(
                    self._db.collection(self._data).document(),
                    {**payload, "created_at": _now(), "updated_at": _now()},
                )
                written += 1
            batch.commit()
        return written

    def find_by_radar_id(self, radar_id: str) -> dict[str, Any] | None:
        hits = self._db.collection(self._data).where("radar_id", "==", radar_id).limit(1).stream()
        return next((self._with_id(d) for d in hits), None)

    def list_conversations(self) -> list[dict[str, Any]]:
        return [self._with_id(d) for d in self._db.collection(self._conv).stream()]

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        doc = self._db.collection(self._conv).document(conversation_id).get()
        return self._with_id(doc) if doc.exists else None

    def create_conversation(self, payload: dict[str, Any]) -> dict[str, Any]:
        record = {**payload, "created_at": _now(), "updated_at": _now()}
        ref = self._db.collection(self._conv).document()
        ref.set(record)
        return {**record, "id": ref.id}

    def replace_conversation(self, conversation_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        ref = self._db.collection(self._conv).document(conversation_id)
        if not ref.get().exists:
            return None
        ref.update({**payload, "updated_at": _now()})
        return self._with_id(ref.get())

    def delete_conversation(self, conversation_id: str) -> bool:
        ref = self._db.collection(self._conv).document(conversation_id)
        if not ref.get().exists:
            return False
        ref.delete()
        return True


_store: Store | None = None
_store_lock = threading.Lock()


def get_store(settings: Settings) -> Store:
    global _store
    with _store_lock:
        if _store is not None:
            return _store
        if settings.firestore_enabled:
            try:
                _store = FirestoreStore(settings)
            except Exception as exc:  # noqa: BLE001 - 기동을 막지 않되 원인을 남긴다
                print(f"[store] Firestore 초기화 실패 → 메모리로 전환: {exc}")
                _store = InMemoryStore()
        else:
            _store = InMemoryStore()
        return _store


def reset_store_for_tests() -> None:
    """테스트가 저장소를 격리할 수 있게 한다. 운영 경로에서는 호출하지 않는다."""
    global _store
    with _store_lock:
        _store = None
