import assert from "node:assert/strict";
import { test } from "node:test";
import { failureText, kindLabel, relativeTime, safeLink } from "../js/news.js";

test("링크는 http·https만 연다", () => {
  assert.equal(safeLink("https://openai.com/n/1"), "https://openai.com/n/1");
  assert.equal(safeLink("http://a.example/x?y=1"), "http://a.example/x?y=1");
  for (const bad of ["javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "", "relative/path", null]) {
    assert.equal(safeLink(bad), null, String(bad));
  }
});

test("상대 시각은 분·시간·일, 30일 넘으면 날짜로 보인다", () => {
  const now = new Date("2026-10-04T12:00:00Z");
  assert.equal(relativeTime("2026-10-04T11:59:30Z", now), "방금 전");
  assert.equal(relativeTime("2026-10-04T11:15:00Z", now), "45분 전");
  assert.equal(relativeTime("2026-10-04T09:00:00Z", now), "3시간 전");
  assert.equal(relativeTime("2026-10-01T12:00:00Z", now), "3일 전");
  assert.match(relativeTime("2026-08-01T00:00:00Z", now), /2026/);
  assert.equal(relativeTime("not a date", now), "");
  assert.equal(relativeTime("2026-10-05T00:00:00Z", now), "방금 전");
});

test("종류 표시와 실패 요약", () => {
  assert.equal(kindLabel("official"), "공식");
  assert.equal(kindLabel("custom"), "직접 추가");
  assert.equal(kindLabel("unknown"), "");
  assert.equal(failureText([]), "");
  assert.equal(failureText([{ source_name: "Hacker News", error: "응답 지연" }]),
    "1곳을 읽지 못했습니다 (Hacker News: 응답 지연)");
});
