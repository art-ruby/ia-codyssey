"""LAPIS 향 큐레이터 — Vercel Python Serverless Function.

이 파일은 두 층으로 나뉜다.
  1) 순수 함수 — 검증, 재시도 판단, 백오프 계산. 네트워크 없이 테스트한다.
  2) I/O — Gemini 호출과 HTTP 핸들러.
경계를 지켜야 Gemini가 503을 뱉는 동안에도 로직을 검증할 수 있다.
"""
import random
import time

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


TOTAL_BUDGET_SECONDS = 25.0
PER_ATTEMPT_CAP_SECONDS = 12.0
MIN_ATTEMPT_SECONDS = 3.0

PRIMARY_MODEL = "gemini-3.5-flash"
FALLBACK_MODEL = PRIMARY_MODEL  # Task 5에서 실제 대체 모델로 교체한다

_BUSY_ERROR = {"code": "MODEL_UNAVAILABLE", "message": "향을 짓는 곳이 잠시 붐비고 있습니다. 잠시 뒤 다시 시도해 주세요."}
_SHAPE_ERROR = {"code": "INVALID_RESPONSE", "message": "결과를 완성하지 못했습니다. 잠시 뒤 다시 시도해 주세요."}
_SERVICE_ERROR = {"code": "SERVICE_UNAVAILABLE", "message": "지금은 큐레이터를 이용할 수 없습니다. 잠시 후 다시 방문해 주세요."}


class ModelError(Exception):
    """모델 호출 실패. status가 None이면 네트워크 오류나 타임아웃이다."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def _model_for(attempt):
    return FALLBACK_MODEL if attempt == MAX_ATTEMPTS else PRIMARY_MODEL


def curate(body, call_model, now=time.monotonic, sleep=time.sleep):
    """(http_status, payload) 를 돌려준다.

    call_model(model, timeout) 은 파싱된 dict를 돌려주거나 ModelError를 던진다.
    now/sleep을 주입받는 이유는 테스트에서 실제로 25초를 기다리지 않기 위해서다.
    """
    invalid = validate_request(body)
    if invalid is not None:
        return 400, {"error": invalid}

    deadline = now() + TOTAL_BUDGET_SECONDS
    last_failure = _BUSY_ERROR

    for attempt in range(1, MAX_ATTEMPTS + 1):
        remaining = deadline - now()
        if remaining < MIN_ATTEMPT_SECONDS:
            break

        timeout = min(PER_ATTEMPT_CAP_SECONDS, remaining)
        try:
            raw = call_model(_model_for(attempt), timeout)
        except ModelError as exc:
            if not should_retry(exc.status):
                return 500, {"error": _SERVICE_ERROR}
            last_failure = _BUSY_ERROR
        else:
            reason = validate_response(raw)
            if reason is None:
                result = dict(raw)
                result["attempts"] = attempt
                return 200, result
            last_failure = _SHAPE_ERROR

        if attempt < MAX_ATTEMPTS:
            sleep(next_delay(attempt))

    status = 502 if last_failure is _SHAPE_ERROR else 503
    return status, {"error": last_failure}
