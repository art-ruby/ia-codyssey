import pytest

import curate


def valid_body(**overrides):
    body = {"season": "autumn", "time": "dusk", "mood": "calm", "moment": "퇴근길 지하철에서 창밖을 볼 때"}
    body.update(overrides)
    return body


# ---------- validate_request ----------

def test_valid_request_returns_none():
    assert curate.validate_request(valid_body()) is None


def test_empty_moment_is_empty_input():
    err = curate.validate_request(valid_body(moment="   "))
    assert err["code"] == "EMPTY_INPUT"


def test_missing_moment_is_empty_input():
    body = valid_body()
    del body["moment"]
    assert curate.validate_request(body)["code"] == "EMPTY_INPUT"


def test_moment_over_limit_is_invalid_input():
    err = curate.validate_request(valid_body(moment="가" * (curate.MOMENT_MAX + 1)))
    assert err["code"] == "INVALID_INPUT"


def test_moment_at_limit_is_accepted():
    assert curate.validate_request(valid_body(moment="가" * curate.MOMENT_MAX)) is None


@pytest.mark.parametrize("field,bad", [("season", "monsoon"), ("time", "dawn"), ("mood", "sad")])
def test_value_outside_whitelist_is_invalid_input(field, bad):
    err = curate.validate_request(valid_body(**{field: bad}))
    assert err["code"] == "INVALID_INPUT"


def test_non_dict_body_is_invalid_input():
    assert curate.validate_request(["not", "a", "dict"])["code"] == "INVALID_INPUT"


# ---------- should_retry ----------

@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_transient_statuses_are_retried(status):
    assert curate.should_retry(status) is True


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_permanent_statuses_are_not_retried(status):
    assert curate.should_retry(status) is False


def test_network_error_without_status_is_retried():
    assert curate.should_retry(None) is True


# ---------- next_delay ----------

def test_first_delay_is_half_second_plus_jitter():
    assert 0.5 <= curate.next_delay(1) <= 0.625


def test_second_delay_is_two_seconds_plus_jitter():
    assert 2.0 <= curate.next_delay(2) <= 2.5


def test_delay_beyond_table_reuses_last_step():
    assert 2.0 <= curate.next_delay(9) <= 2.5


# ---------- validate_response ----------

def valid_payload():
    return {
        "name": "Quiet Amber",
        "name_kr": "조용한 앰버",
        "copy": "해가 넘어간 뒤에도 방 안에 남는, 말수 적은 온기.",
        "scene": "해질녘, 불을 켜지 않은 거실",
        "notes": {
            "top": {"materials": ["베르가못", "핑크페퍼"], "description": "첫 10분의 인상"},
            "heart": {"materials": ["아이리스"], "description": "체온에 닿는 중심"},
            "base": {"materials": ["앰버", "샌달우드"], "description": "떠난 뒤의 잔향"},
        },
    }


def test_valid_payload_returns_none():
    assert curate.validate_response(valid_payload()) is None


def test_missing_top_level_field_is_rejected():
    payload = valid_payload()
    del payload["name_kr"]
    assert curate.validate_response(payload) is not None


def test_blank_string_field_is_rejected():
    payload = valid_payload()
    payload["copy"] = "   "
    assert curate.validate_response(payload) is not None


def test_missing_note_layer_is_rejected():
    payload = valid_payload()
    del payload["notes"]["heart"]
    assert curate.validate_response(payload) is not None


def test_empty_materials_list_is_rejected():
    payload = valid_payload()
    payload["notes"]["base"]["materials"] = []
    assert curate.validate_response(payload) is not None


def test_non_string_material_is_rejected():
    payload = valid_payload()
    payload["notes"]["top"]["materials"] = ["베르가못", 42]
    assert curate.validate_response(payload) is not None


def test_non_dict_payload_is_rejected():
    assert curate.validate_response("just a string") is not None


# ---------- curate orchestrator ----------

class FakeClock:
    """단조 증가 시계. sleep 호출이 그대로 시간을 밀어준다."""

    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


def make_caller(outcomes):
    """outcomes의 각 원소는 payload(dict) 또는 raise할 예외다."""
    calls = []

    def call_model(model, timeout):
        calls.append({"model": model, "timeout": timeout})
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    call_model.calls = calls
    return call_model


def test_first_attempt_success_returns_payload_with_attempts_one():
    clock = FakeClock()
    caller = make_caller([valid_payload()])
    status, payload = curate.curate(valid_body(), caller, now=clock.now, sleep=clock.sleep)
    assert status == 200
    assert payload["attempts"] == 1
    assert payload["name"] == "Quiet Amber"
    assert len(caller.calls) == 1


def test_retries_on_503_then_succeeds():
    clock = FakeClock()
    caller = make_caller([curate.ModelError("overloaded", status=503), valid_payload()])
    status, payload = curate.curate(valid_body(), caller, now=clock.now, sleep=clock.sleep)
    assert status == 200
    assert payload["attempts"] == 2
    assert len(caller.calls) == 2


def test_retries_on_schema_violation():
    clock = FakeClock()
    broken = valid_payload()
    del broken["notes"]["base"]
    caller = make_caller([broken, valid_payload()])
    status, payload = curate.curate(valid_body(), caller, now=clock.now, sleep=clock.sleep)
    assert status == 200
    assert payload["attempts"] == 2


def test_three_failures_return_model_unavailable():
    clock = FakeClock()
    err = curate.ModelError("overloaded", status=503)
    caller = make_caller([err, err, err])
    status, payload = curate.curate(valid_body(), caller, now=clock.now, sleep=clock.sleep)
    assert status == 503
    assert payload["error"]["code"] == "MODEL_UNAVAILABLE"
    assert len(caller.calls) == curate.MAX_ATTEMPTS


def test_three_schema_violations_return_invalid_response():
    clock = FakeClock()
    broken = valid_payload()
    del broken["notes"]["base"]
    caller = make_caller([broken, dict(broken), dict(broken)])
    status, payload = curate.curate(valid_body(), caller, now=clock.now, sleep=clock.sleep)
    assert status == 502
    assert payload["error"]["code"] == "INVALID_RESPONSE"


def test_auth_failure_stops_immediately():
    clock = FakeClock()
    err = curate.ModelError("bad key", status=401)
    caller = make_caller([err, valid_payload()])
    status, payload = curate.curate(valid_body(), caller, now=clock.now, sleep=clock.sleep)
    assert status == 500
    assert payload["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert len(caller.calls) == 1, "인증 실패에는 재시도하지 않는다"


def test_third_attempt_uses_fallback_model():
    clock = FakeClock()
    err = curate.ModelError("overloaded", status=503)
    caller = make_caller([err, err, valid_payload()])
    curate.curate(valid_body(), caller, now=clock.now, sleep=clock.sleep)
    models = [c["model"] for c in caller.calls]
    assert models[0] == curate.PRIMARY_MODEL
    assert models[1] == curate.PRIMARY_MODEL
    assert models[2] == curate.FALLBACK_MODEL


def test_fallback_model_is_used_when_it_differs(monkeypatch):
    """FALLBACK_MODEL이 PRIMARY_MODEL과 같은 동안에는 위 테스트가 통과해도 의미가 없다.

    (Task 5에서 실제 대체 모델 ID가 정해지기 전까지 두 값이 같다.)
    실제로 다른 값을 넣어 3회차에만 전환되는지 확인한다.
    """
    monkeypatch.setattr(curate, "FALLBACK_MODEL", "some-other-model")
    clock = FakeClock()
    err = curate.ModelError("overloaded", status=503)
    caller = make_caller([err, err, valid_payload()])
    curate.curate(valid_body(), caller, now=clock.now, sleep=clock.sleep)
    assert [c["model"] for c in caller.calls] == [
        curate.PRIMARY_MODEL,
        curate.PRIMARY_MODEL,
        "some-other-model",
    ]


def test_budget_exhaustion_stops_before_max_attempts():
    clock = FakeClock()

    def slow_call(model, timeout):
        clock.t += 11.0
        raise curate.ModelError("overloaded", status=503)

    slow_call.calls = []
    status, payload = curate.curate(valid_body(), slow_call, now=clock.now, sleep=clock.sleep)
    assert status == 503
    assert payload["error"]["code"] == "MODEL_UNAVAILABLE"
    assert clock.t <= curate.TOTAL_BUDGET_SECONDS + curate.PER_ATTEMPT_CAP_SECONDS


def test_attempt_timeout_never_exceeds_cap():
    clock = FakeClock()
    caller = make_caller([valid_payload()])
    curate.curate(valid_body(), caller, now=clock.now, sleep=clock.sleep)
    assert caller.calls[0]["timeout"] <= curate.PER_ATTEMPT_CAP_SECONDS


def test_invalid_request_never_calls_model():
    clock = FakeClock()
    caller = make_caller([valid_payload()])
    status, payload = curate.curate(valid_body(moment=""), caller, now=clock.now, sleep=clock.sleep)
    assert status == 400
    assert payload["error"]["code"] == "EMPTY_INPUT"
    assert caller.calls == []
