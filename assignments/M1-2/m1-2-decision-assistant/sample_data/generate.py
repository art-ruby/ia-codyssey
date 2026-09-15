"""RADAR 형태를 모사한 표본 후보 생성기.

명세 14절: 실제 RADAR 연결이 바로 안 될 때 개발을 멈추지 않기 위한 것이다.
과제의 '시계열 100개 이상' 요건을 먼저 충족시키되, 이것이 실측이 아니라는
사실이 데이터·API·화면 어디에서도 지워지지 않게 한다.

  - 모든 레코드에 source="sample"
  - 파일 상단 meta 에 is_real_data=false 와 생성 근거
  - radar_id 에 SAMPLE_ 접두어 — 실제 YouTube video_id 와 절대 겹치지 않는다

채널 id 와 주제는 실제 RADAR 저장소에서 확인한 값을 쓴다(loss_defense,
solo_pride). 값이 그럴듯해야 요약·추세·AI 답변을 실제와 비슷한 조건에서
검증할 수 있기 때문이다. 점수는 지어낸 것이며 RADAR 계산이 아니다.

    python sample_data/generate.py
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent / "candidates.json"
SEED = 20260911
DAYS = 75
TARGET_COUNT = 168

# 실제 RADAR 채널 (data/config/channels.json 에서 확인)
CHANNELS = {
    "loss_defense": {
        "label": "손해 방어",
        "topics": ["年金 損", "在職老齢年金 減額", "定年後 住民税", "退職金 税金",
                   "健康保険料 高い", "相続 トラブル", "空き家 処分", "介護費用"],
    },
    "solo_pride": {
        "label": "혼자의 품격",
        "topics": ["定年後 孤独", "熟年離婚", "おひとりさま 老後", "60代 再就職 現実",
                   "友達いない 老後", "終活 一人", "老後資金 いくら"],
    },
}

TITLE_FORMS = [
    "【{topic}】知らないと損する{n}つのこと",
    "{topic}｜60代が今すぐ確認すべき理由",
    "実話｜{topic}で失敗した人の共通点",
    "{topic}の落とし穴と対策を解説",
    "なぜ{topic}が急に増えているのか",
    "{topic}｜専門家が語る本当の話",
    "手取りが変わる｜{topic}の仕組み",
]

MEMO_FORMS = [
    "구독자 대비 조회수가 높음",
    "동일 주제 공급이 최근 증가",
    "댓글에 구체적 질문이 반복됨",
    "채널 적합성은 높으나 경쟁 과열",
    "게시 직후 상승세가 가파름",
    "기존 콘텐츠와 중복도 낮음",
    "표본이 적어 추가 관찰 필요",
]

MAKE_REASONS = [
    "최근 상승세가 강함\n채널 적합성이 높음\n기존 콘텐츠와 중복도가 낮음",
    "댓글에서 같은 질문이 반복 관측됨\n구독자 대비 조회수가 높음",
    "공급이 적은 구간\n채널 약속과 직접 연결됨",
]
WATCH_REASONS = [
    "가능성은 있으나 표본이 부족하다",
    "상승 중이나 경쟁 채널 공급도 함께 증가",
    "주제는 맞으나 검색 수요가 아직 얕다",
]
SKIP_REASONS = [
    "채널 약속과 어긋난다",
    "이미 유사 소재를 다뤘다",
    "수요 신호가 약하다",
    "참여율이 낮아 수요 근거로 보기 어렵다",
]


def _score(rng: random.Random, day_index: int) -> float:
    """최근으로 올수록 완만히 오르는 분포.

    Summary 의 추세 계산이 실제로 무언가를 잡아내는지 확인하려면 신호가
    있어야 한다. 다만 잡음을 충분히 섞어 매끈한 직선이 되지 않게 한다.
    """
    drift = (day_index / DAYS) * 9.0
    base = rng.betavariate(2.2, 3.0) * 100.0
    return round(max(3.0, min(97.0, base * 0.82 + drift + rng.gauss(0, 6))), 1)


def _decision(rng: random.Random, score: float) -> tuple[str | None, str]:
    """점수가 높다고 자동으로 MAKE 가 되지 않는다.

    명세 6절대로 판단은 사람의 것이므로, 표본에서도 상당수를 '미정'으로
    남긴다. 그래야 화면의 결정 버튼과 handoff 흐름을 실제로 시험할 수 있다.
    """
    if rng.random() < 0.42:
        return None, ""
    if score >= 74 and rng.random() < 0.55:
        return "MAKE", rng.choice(MAKE_REASONS)
    if score >= 52:
        return "WATCH", rng.choice(WATCH_REASONS)
    return "SKIP", rng.choice(SKIP_REASONS)


def build() -> dict:
    rng = random.Random(SEED)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    start = now - timedelta(days=DAYS)

    records = []
    for i in range(TARGET_COUNT):
        day_index = rng.randint(0, DAYS)
        when = start + timedelta(days=day_index, hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
        channel_id = rng.choices(list(CHANNELS), weights=[0.58, 0.42])[0]
        topic = rng.choice(CHANNELS[channel_id]["topics"])
        score = _score(rng, day_index)
        decision, reason = _decision(rng, score)
        records.append(
            {
                "date": when.isoformat(),
                "value": score,
                "memo": rng.choice(MEMO_FORMS),
                "radar_id": f"SAMPLE_{i:04d}",
                "channel": channel_id,
                "topic": topic,
                "title": rng.choice(TITLE_FORMS).format(topic=topic, n=rng.choice([3, 5, 7])),
                "radar_score": score,
                "decision": decision,
                "decision_reason": reason,
                "source": "sample",
            }
        )

    records.sort(key=lambda r: r["date"])
    return {
        "meta": {
            "is_real_data": False,
            "generator": "sample_data/generate.py",
            "seed": SEED,
            "generated_at": now.isoformat(),
            "count": len(records),
            "period_days": DAYS,
            "channels": list(CHANNELS),
            "warning": (
                "RADAR 형태를 모사한 표본이다. 점수와 결정은 생성된 값이며 "
                "실제 관측이나 RADAR 계산 결과가 아니다."
            ),
        },
        "candidates": records,
    }


if __name__ == "__main__":
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    counts: dict[str, int] = {}
    for row in data["candidates"]:
        key = row["decision"] or "PENDING"
        counts[key] = counts.get(key, 0) + 1
    print(f"생성: {len(data['candidates'])}건 → {OUT}")
    print(f"기간: {data['candidates'][0]['date'][:10]} ~ {data['candidates'][-1]['date'][:10]}")
    print(f"결정 분포: {counts}")
