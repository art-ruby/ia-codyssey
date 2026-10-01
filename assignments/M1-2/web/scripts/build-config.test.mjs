// 실행: M1-2 폴더에서 `node --test web/scripts/`
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { build, collectPublicValues, readPublicDotenv } from "./build-config.mjs";

const PUBLIC = {
  API_BASE_URL: "https://api.example.test",
  FIREBASE_WEB_API_KEY: "public-web-key",
  FIREBASE_AUTH_DOMAIN: "demo.firebaseapp.com",
  FIREBASE_PROJECT_ID: "demo",
};

function tempDir() {
  return mkdtempSync(join(tmpdir(), "build-config-"));
}

test("필요한 값이 하나라도 없으면 파일을 만들지 않고 실패한다", () => {
  const dir = tempDir();
  const out = join(dir, "config.js");
  const { FIREBASE_PROJECT_ID, ...partial } = PUBLIC;

  assert.throws(() => build({ env: partial, envFile: join(dir, "none.env"), outFile: out }), /FIREBASE_PROJECT_ID/);
  assert.equal(existsSync(out), false);
});

test("API 주소가 http(s)가 아니면 실패한다", () => {
  assert.throws(() => collectPublicValues({ ...PUBLIC, API_BASE_URL: "javascript:alert(1)" }, {}), /API_BASE_URL/);
});

test(".env에서 공개 값만 읽고 서버 비밀값은 결과에 넣지 않는다", () => {
  const dir = tempDir();
  const envFile = join(dir, ".env");
  const out = join(dir, "config.js");
  writeFileSync(envFile, [
    "OPENAI_API_KEY=SECRET-AI-KEY",
    `FIREBASE_SERVICE_ACCOUNT_JSON='{"private_key":"SECRET-SA"}'`,
    ...Object.entries(PUBLIC).map(([k, v]) => `${k}="${v}"`),
  ].join("\n"));

  assert.deepEqual(Object.keys(readPublicDotenv(envFile)).sort(), Object.keys(PUBLIC).sort());
  build({ env: {}, envFile, outFile: out });
  const text = readFileSync(out, "utf8");

  for (const value of Object.values(PUBLIC)) assert.ok(text.includes(JSON.stringify(value)));
  assert.ok(!text.includes("SECRET-AI-KEY") && !text.includes("SECRET-SA"));
  assert.ok(!/__[A-Z_]+__/.test(text));
});

test("환경변수가 .env보다 우선한다", () => {
  const dir = tempDir();
  const envFile = join(dir, ".env");
  writeFileSync(envFile, Object.entries(PUBLIC).map(([k, v]) => `${k}=${v}`).join("\n"));

  const values = collectPublicValues({ API_BASE_URL: "https://deploy.example.test" }, readPublicDotenv(envFile));
  assert.equal(values.API_BASE_URL, "https://deploy.example.test");
});

test("값에 따옴표가 있어도 코드로 해석되지 않게 문자열로 넣는다", () => {
  const dir = tempDir();
  const out = join(dir, "config.js");
  build({ env: { ...PUBLIC, FIREBASE_PROJECT_ID: 'x", evil: "1' }, envFile: join(dir, "none.env"), outFile: out });

  const text = readFileSync(out, "utf8");
  assert.ok(text.includes(JSON.stringify('x", evil: "1')));
});
