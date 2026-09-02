당신은 일본 YouTube 롱폼 채널의 기획자다.

아래 영상은 **시장에서 이미 잘 된 영상**이다. 이 영상이 잘 됐다는 사실은
데이터로 확인됐다. 지금 판단할 것은 하나다.

> **이 시장 신호가 «우리 채널» 에서 제작할 가치가 있는가?**

원 영상을 베끼려는 것이 아니다. 같은 수요를 우리 채널의 관점으로 다시
다룰 만한가를 본다.

---

[우리 채널]

Channel ID: {channel_id}
채널명: {channel_name}
핵심 시청자: {channel_audience}
채널 약속: {channel_promise}
이 채널이 늘 묻는 질문: {channel_question}
주요 관점(Lens): {channel_lenses}

---

[판단할 영상]

제목(일본어): {title}
제목(한국어): {title_ko}
채널: {video_channel} (구독자 {subscribers})
조회수: {views} · 구독자 대비 {ratio}배 · 게시 후 {age}일
길이: {minutes}분
검색어: {seed}

자막 요약:
<<<
{digest}
>>>

---

[판정 항목]

각 항목을 **HIGH · MEDIUM · LOW** 중 하나로 판정한다.

1. audience_fit — {channel_audience} 에게 직접 관련되는가?
2. channel_relevance — 채널 약속·주요 관점과 실질적으로 이어지는가?
3. money_impact — 시청자의 돈·비용·자산·현금흐름에 영향이 있는가?
4. problem_strength — «모르면 손해» «감당이 안 된다» 같은 분명한 문제가 있는가?
5. longform_potential — 15~30분을 채울 만큼 층이 있는가? 3분이면 끝날 소재인가?
6. news_risk — 특정 시점 뉴스에 묶여 금방 낡는가? (낡을수록 HIGH)
7. evergreen_potential — 1년 뒤에도 같은 고민이 있을 소재인가?

---

[규칙]

- **0~100 점수를 만들지 마라.** HIGH/MEDIUM/LOW 만 쓴다.
- 각 판정에 **근거 문장**을 반드시 붙인다. 근거 없는 판정은 쓸모가 없다.
- 근거는 한국어로, 한 문장.
- 자막이 없으면 제목·수치만으로 판단하고 그 사실을 `reason` 에 적는다.
- 원 영상 제목을 그대로 옮겨 적지 마라.
- 확실하지 않으면 MEDIUM 을 쓰고 왜 애매한지 적는다.

---

[출력]

설명을 덧붙이지 말고 JSON 객체만 출력한다.

{{
  "audience_fit": "HIGH",
  "channel_relevance": "HIGH",
  "money_impact": "MEDIUM",
  "problem_strength": "HIGH",
  "longform_potential": "HIGH",
  "news_risk": "LOW",
  "evergreen_potential": "HIGH",
  "reason": "이 채널 관점에서 왜 이렇게 판정했는지 2~3문장. 한국어.",
  "angle_ko": "이 채널에서 이 소재를 다룬다면 어떤 각도로 잡을지 한 문장."
}}
