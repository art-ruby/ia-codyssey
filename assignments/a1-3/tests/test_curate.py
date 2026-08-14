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
