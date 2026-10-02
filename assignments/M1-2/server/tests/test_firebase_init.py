import threading
import time

import pytest

firebase_admin = pytest.importorskip("firebase_admin")  # 프로젝트 가상환경(.venv)에서 실행한다
from firebase_admin import credentials  # noqa: E402

from app.core.config import load_settings  # noqa: E402
from app.core.firestore import firebase_app  # noqa: E402

SETTINGS = load_settings({"OWNER_UID": "o", "FIREBASE_SERVICE_ACCOUNT_JSON": '{"type": "service_account"}'})


def test_concurrent_first_requests_share_one_app(monkeypatch):
    """서버가 막 켜졌을 때 동시에 온 요청이 모두 같은 앱을 받는다(늦은 쪽이 503이 되지 않는다)."""
    apps: dict[str, object] = {}

    def get_app(name):
        if name not in apps:
            raise ValueError("no app")
        return apps[name]

    def initialize_app(cred, name):
        time.sleep(0.05)  # 초기화 사이에 다른 요청이 끼어드는 상황을 넓힌다
        if name in apps:
            raise ValueError("already exists")
        apps[name] = object()
        return apps[name]

    monkeypatch.setattr(firebase_admin, "get_app", get_app)
    monkeypatch.setattr(firebase_admin, "initialize_app", initialize_app)
    monkeypatch.setattr(credentials, "Certificate", lambda account: account)

    results, errors = [], []
    start = threading.Barrier(8)

    def call():
        start.wait()
        try:
            results.append(firebase_app(SETTINGS))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=call) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [] and len(results) == 8 and len({id(r) for r in results}) == 1
