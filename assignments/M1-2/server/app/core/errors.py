"""공통 예외 표시."""
from __future__ import annotations


class NoChange(Exception):
    """아무것도 쓰기 전에 요청을 거부했다(404·409·422 등).

    run_idempotent는 이 예외에서만 중복 요청 기록을 지워, 같은 키로 다시 판단할 수 있게 한다.
    변경 적용 여부가 불확실한 다른 예외는 기록을 processing으로 남긴다(docs/api-contract.md).
    쓰기를 시작한 뒤에는 이 예외를 내면 안 된다(트랜잭션·일괄 쓰기 안에서 커밋 전에 낸 경우는 괜찮다).
    """
