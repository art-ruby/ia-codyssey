"""현재 서버 .env를 이용해 Hermes의 텍스트 응답을 한 번 검증한다."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import ConfigError, load_settings  # noqa: E402
from app.features.analysis.provider import HermesProvider, ProviderError  # noqa: E402


def main() -> int:
    try:
        provider = HermesProvider(load_settings())
        result = provider.complete_text(
            [{"role": "user", "content": "연결 확인. 한 단어로 답하세요."}]
        )
    except (ConfigError, ProviderError) as exc:
        if isinstance(exc, ProviderError):
            print(json.dumps({"success": False, "error": exc.kind, "http_status": exc.status_code}))
        else:
            print(json.dumps({"success": False, "error": "missing_ai_settings"}))
        return 1
    print(json.dumps({
        "success": True,
        "provider": "Hermes",
        "route": provider.route,
        "requested_model": provider.model,
        "response_model": result.model,
        "response_shape": "nonempty text, finish_reason=stop",
        "total_tokens": result.total_tokens,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
