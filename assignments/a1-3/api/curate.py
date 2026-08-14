"""LAPIS 향 큐레이터 — Vercel Python Serverless Function.

이 파일은 두 층으로 나뉜다.
  1) 순수 함수 — 검증, 재시도 판단, 백오프 계산. 네트워크 없이 테스트한다.
  2) I/O — Gemini 호출과 HTTP 핸들러.
경계를 지켜야 Gemini가 503을 뱉는 동안에도 로직을 검증할 수 있다.
"""
import random

SEASONS = frozenset({"spring", "summer", "autumn", "winter"})
TIMES = frozenset({"day", "dusk", "night"})
MOODS = frozenset({"calm", "bold", "warm"})
MOMENT_MAX = 120

NOTE_LAYERS = ("top", "heart", "base")

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (0.5, 2.0)
JITTER_RATIO = 0.25

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def validate_request(body):
    """유효하면 None, 아니면 {"code", "message"} 를 돌려준다."""
    if not isinstance(body, dict):
        return {"code": "INVALID_INPUT", "message": "요청 형식이 올바르지 않습니다."}

    moment = body.get("moment")
    moment = moment.strip() if isinstance(moment, str) else ""
    if not moment:
        return {"code": "EMPTY_INPUT", "message": "닿고 싶은 순간을 한 줄 남겨 주세요."}
    if len(moment) > MOMENT_MAX:
        return {"code": "INVALID_INPUT", "message": f"순간은 {MOMENT_MAX}자 이내로 적어 주세요."}

    for field, allowed in (("season", SEASONS), ("time", TIMES), ("mood", MOODS)):
        if body.get(field) not in allowed:
            return {"code": "INVALID_INPUT", "message": "선택 항목을 모두 골라 주세요."}

    return None


def should_retry(status):
    """status가 None이면 네트워크 오류·타임아웃으로 보고 재시도한다.

    401/403은 키가 잘못된 상태다. 세 번 더 시도해도 결과가 같고 지연만 3배가 된다.
    400은 우리 코드의 버그다. 재시도로 가려지면 안 된다.
    """
    if status is None:
        return True
    return status in RETRYABLE_STATUS


def next_delay(attempt):
    """attempt(1-based) 시도 실패 직후 기다릴 초를 돌려준다.

    첫 간격이 짧은 것은 스키마 위반처럼 즉시 다시 물어도 되는 경우를 위해서고,
    두 번째가 벌어진 것은 503이 스파이크성이라 너무 빨리 재시도하면 같은 과부하에
    그대로 부딪히기 때문이다.
    """
    index = min(attempt, len(BACKOFF_SECONDS)) - 1
    base = BACKOFF_SECONDS[index]
    return base + random.uniform(0, base * JITTER_RATIO)


def _is_filled_string(value):
    return isinstance(value, str) and bool(value.strip())


def validate_response(data):
    """유효하면 None, 아니면 실패 이유 문자열을 돌려준다."""
    if not isinstance(data, dict):
        return "payload is not an object"

    for key in ("name", "name_kr", "copy", "scene"):
        if not _is_filled_string(data.get(key)):
            return f"missing or empty field: {key}"

    notes = data.get("notes")
    if not isinstance(notes, dict):
        return "missing field: notes"

    for layer in NOTE_LAYERS:
        node = notes.get(layer)
        if not isinstance(node, dict):
            return f"missing note layer: {layer}"
        materials = node.get("materials")
        if not isinstance(materials, list) or not materials:
            return f"empty materials: {layer}"
        if not all(_is_filled_string(m) for m in materials):
            return f"invalid material entry: {layer}"
        if not _is_filled_string(node.get("description")):
            return f"missing description: {layer}"

    return None
