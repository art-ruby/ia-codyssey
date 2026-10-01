import json
import sys
from types import SimpleNamespace

import pytest

from scripts import smoke_ai


@pytest.mark.parametrize(
    ("finish_reason", "expected_success"),
    [("stop", True), ("length", False), ("content_filter", False)],
)
def test_smoke_requires_normal_completion(monkeypatch, capsys, finish_reason, expected_success):
    monkeypatch.setattr(sys, "argv", ["smoke_ai.py"])
    monkeypatch.setattr(
        smoke_ai,
        "_settings",
        lambda path: {
            "OPENAI_API_KEY": "test-key",
            "AI_PROVIDER_BASE_URL": smoke_ai.CODYSSEY_BASE_URL,
            "AI_PROVIDER_MODEL": "gpt-test",
        },
    )

    response = SimpleNamespace(
        model="gpt-test",
        choices=[SimpleNamespace(
            message=SimpleNamespace(content="부분 응답"),
            finish_reason=finish_reason,
        )],
    )

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kwargs: response)
            )

    monkeypatch.setattr(smoke_ai, "OpenAI", FakeClient)

    result = smoke_ai.main()
    output = capsys.readouterr()

    assert (result == 0) is expected_success
    if expected_success:
        assert json.loads(output.out)["finish_reason"] == "stop"
    else:
        assert output.out == ""
        assert "정상 종료" in output.err
