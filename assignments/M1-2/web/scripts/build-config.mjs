// 공개 웹 설정 생성: config.template.js + 공개 변수 → web/js/config.js
//
// 실행: M1-2 폴더에서 `node web/scripts/build-config.mjs`
// 값은 환경변수(배포: Vercel)에서 먼저 찾고, 없으면 M1-2/.env에서 찾는다.
// M1-2/.env에는 서버 비밀값도 있으므로 아래 PUBLIC_KEYS 네 개만 골라 읽는다.
// 하나라도 없거나 형식이 틀리면 파일을 만들지 않고 실패(종료 코드 1)한다.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const WEB_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const M1_2_DIR = resolve(WEB_DIR, "..");

export const PUBLIC_KEYS = ["API_BASE_URL", "FIREBASE_WEB_API_KEY", "FIREBASE_AUTH_DOMAIN", "FIREBASE_PROJECT_ID"];

// .env에서 허용 목록의 이름만 읽는다. 다른 줄(비밀값)은 해석하지도 않는다.
export function readPublicDotenv(path) {
  if (!existsSync(path)) return {};
  const found = {};
  for (const line of readFileSync(path, "utf8").split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$/);
    if (!match || !PUBLIC_KEYS.includes(match[1])) continue;
    found[match[1]] = match[2].trim().replace(/^(['"])(.*)\1$/, "$2");
  }
  return found;
}

export function collectPublicValues(env, dotenv) {
  const values = {};
  const missing = [];
  for (const key of PUBLIC_KEYS) {
    const value = (env[key] ?? dotenv[key] ?? "").trim();
    if (value) values[key] = value;
    else missing.push(key);
  }
  if (missing.length) throw new Error(`공개 설정 누락: ${missing.join(", ")}`);
  if (!/^https?:\/\/[^\s"'<>]+$/.test(values.API_BASE_URL)) {
    throw new Error("API_BASE_URL은 http(s) 주소여야 합니다");
  }
  return values;
}

export function render(template, values) {
  let out = template;
  for (const key of PUBLIC_KEYS) {
    // JSON 문자열로 넣어 따옴표·특수문자가 코드로 해석되지 않게 한다.
    out = out.replace(`"__${key}__"`, JSON.stringify(values[key]));
  }
  if (/"__[A-Z_]+__"/.test(out)) throw new Error("템플릿에 채우지 못한 자리가 남았습니다");
  return "// 생성 파일(Git 제외). web/scripts/build-config.mjs가 만든다. 직접 고치지 않는다.\n" + out;
}

export function build({ env = process.env, envFile = join(M1_2_DIR, ".env"), outFile = join(WEB_DIR, "js", "config.js") } = {}) {
  const values = collectPublicValues(env, readPublicDotenv(envFile));
  const template = readFileSync(join(WEB_DIR, "js", "config.template.js"), "utf8");
  writeFileSync(outFile, render(template, values), "utf8");
  return outFile;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    console.log(`생성: ${build()}`);
  } catch (error) {
    console.error(`config.js 생성 실패: ${error.message}`);
    process.exit(1);
  }
}
