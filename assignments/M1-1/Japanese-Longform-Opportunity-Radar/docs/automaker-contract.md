# automaker 연결 — 파일 계약

Radar 와 automaker 를 코드로 붙이지 않는다. **파일로만 주고받는다.**
(지시서 §50~52)

```
Radar      기회를 찾는다
Claude     대본을 쓴다
automaker  영상을 만든다
```

강하게 붙이면 한쪽을 고칠 때마다 다른 쪽이 깨진다. Radar 는 영상을 만들지
않고, automaker 는 유튜브를 뒤지지 않는다. 사이에 파일 두 종류만 둔다.

---

## 주고받는 것

```
data/briefs/{channel_id}/{video_id}.md          Radar 가 쓴다
data/scripts/{channel_id}/{video_id}_script.md  사람이 Claude 에게 받아 넣는다
```

`channel_id` 는 `data/config/channels.json` 의 `id` 다. 지금은 둘이다.

```
loss_defense    🛡️ 제도와 현실의 덫
solo_pride      🍂 정년 후 고독과 자존감
```

같은 영상으로 두 채널 브리프를 각각 만들 수 있다.

```
data/briefs/loss_defense/abc123.md
data/briefs/solo_pride/abc123.md
```

**단, 같은 사실과 구성을 제목만 바꿔 두 채널에 올리지 않는다.** (§68)
각 채널에서 핵심 질문·사례·구성·결론이 실질적으로 달라야 한다.

---

## 흐름

```
오늘의 발견
   ↓  채널 고르기
Opportunity Card (export.one_pager)      ← 이 소재를 «고를지» 판단
   ↓  제작 후보로 확정
댓글 수집 (comments.fetch)                50개까지, 고른 것만
   ↓
댓글 분석 (comments.analyze)              공통 + 채널별 각도
   ↓
Channel Fit (channel_fit.judge)          HIGH/MEDIUM/LOW + 근거
   ↓
Production Brief (production_brief.build)
   → data/briefs/{channel_id}/{video_id}.md
   ↓
Claude 대본용 자료 (production_brief.script_package)
   = script_writer.md + Channel Profile + Brief + Digest + Comment Analysis
   ↓
Claude 웹에 붙여넣기
   ↓
일본어 대본 + FACT CHECK 목록
   ↓  사람이 확인하고 저장
data/scripts/{channel_id}/{video_id}_script.md
   ↓
automaker 가 이 파일을 읽는다
```

---

## automaker 가 할 일

```
완성 대본
   ↓
씬 분할
   ↓
내레이션 (VOICEVOX)
   ↓
이미지·영상 프롬프트
   ↓
최종 영상
```

Radar 는 여기에 관여하지 않는다.

---

## 대본 파일에 반드시 남길 것

Claude 가 낸 대본을 저장할 때 아래를 함께 남긴다. 나중에 «왜 이 대본이
이렇게 나왔나» 를 되짚을 수 있어야 한다. (§66)

```
- 원 소재 video_id 와 URL
- channel_id
- Channel Profile Version   (브리프 머리에 적혀 있다)
- Comment Analysis 일시
- Prompt Version
- FACT CHECK 목록 — 확인 전에는 영상으로 만들지 않는다
```

브리프 머리에 이미 다 적혀 있으므로 그대로 옮기면 된다.

---

## FACT CHECK 는 사람이 한다

대본에 숫자·법률·세금·연금·보험·상속·부동산 제도가 나오면 Claude 가
`[FACT CHECK]` 로 표시한다. **표시된 것을 확인하기 전에는 영상으로 만들지
않는다.**

이 채널들의 시청자는 50~69세이고 다루는 것이 자기 돈과 집이다.
틀린 제도 설명은 조회수 문제가 아니라 사람에게 손해를 끼친다.
