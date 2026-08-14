/* 과제 증빙 스크린샷 — 데스크톱 / 모바일 / AI 기능 동작 장면.
 *
 *   node scripts/capture.cjs <배포URL>
 *   node scripts/capture.cjs http://localhost:8732     (로컬 검증용)
 *
 * playwright-core + 시스템에 설치된 Edge를 쓴다. 브라우저를 따로 내려받지 않는다.
 * 각 뷰포트마다 페이지를 새로 로드한다 — 노트 모션 그리드가 로드 시점에 한 번만
 * 스케일을 계산하므로, 창 크기만 바꾸면 이전 폭이 남아 잘못된 캡처가 나온다.
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.argv[2];
if (!BASE_URL) {
  console.error('사용법: node scripts/capture.cjs <배포URL>');
  process.exit(1);
}

const OUT_DIR = path.join(__dirname, '..', 'images', 'shots');
const SECTIONS = ['hero', 'story', 'notes', 'curator', 'collection', 'philosophy', 'contact'];
const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'mobile', width: 375, height: 812 }
];

const shot = (name) => path.join(OUT_DIR, name);

async function captureSections(browser, viewport) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
  await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 120000 });
  await page.waitForTimeout(1500);

  for (const id of SECTIONS) {
    const target = page.locator(`#${id}`).first();
    if (!(await target.count())) throw new Error(`섹션을 찾지 못했습니다: #${id}`);
    await target.scrollIntoViewIfNeeded();
    await page.waitForTimeout(900);
    await page.screenshot({ path: shot(`${viewport.name}-${id}.png`) });
    console.log(`  ${viewport.name}-${id}.png`);
  }
  await page.close();
}

async function captureCuratorFlow(browser) {
  const page = await browser.newPage({ viewport: VIEWPORTS[0], deviceScaleFactor: 1 });
  await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 120000 });
  await page.locator('#curator').scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);

  // 1. 빈 입력 실패 안내 — 요청을 보내지 않고 즉시 안내가 뜬다
  await page.click('#curatorSubmit');
  await page.waitForTimeout(400);
  await page.screenshot({ path: shot('ai-01-empty-input.png') });
  console.log('  ai-01-empty-input.png');

  // 2. 입력 완료 상태
  // 라디오는 화면에서 숨겨져 있고 라벨이 그 자리를 덮는다. 실제 사용자와 같은
  // 경로로 라벨을 클릭한다 — check()는 숨은 input을 직접 누르려다 실패한다.
  for (const id of ['season-autumn', 'time-dusk', 'mood-calm']) {
    await page.click(`label[for="${id}"]`);
  }
  await page.fill('#curatorMoment', '퇴근길 지하철에서 창밖을 볼 때');
  await page.waitForTimeout(300);
  await page.screenshot({ path: shot('ai-02-filled.png') });
  console.log('  ai-02-filled.png');

  // 3. 대기 중 — 스켈레톤과 로딩 문구
  await page.click('#curatorSubmit');
  await page.waitForTimeout(1200);
  await page.locator('#curatorResult').scrollIntoViewIfNeeded();
  await page.screenshot({ path: shot('ai-03-loading.png') });
  console.log('  ai-03-loading.png');

  // 4. 결과 — 성공이든 실패든 증빙이 된다
  await page.waitForSelector('.curator-card, .curator-error', { timeout: 45000 });
  // 결과는 폼 아래에 붙는다. 스크롤하지 않으면 화면 밖이라 빈 폼만 찍힌다.
  await page.locator('#curatorResult').scrollIntoViewIfNeeded();
  // 커서를 버튼 밖으로 뺀다. 안 그러면 제출 버튼이 hover 상태(골드 채움)로 찍힌다.
  await page.mouse.move(0, 0);
  await page.waitForTimeout(700);
  await page.screenshot({ path: shot('ai-04-result.png') });
  const outcome = (await page.locator('.curator-card').count()) ? '성공' : '실패 안내';
  console.log(`  ai-04-result.png  (${outcome})`);

  await page.close();
}

(async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  // channel:'msedge' 는 설치된 Edge를 그대로 쓴다. Chromium 다운로드가 필요 없다.
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    for (const viewport of VIEWPORTS) await captureSections(browser, viewport);
    await captureCuratorFlow(browser);
    console.log(`\n저장 완료: ${OUT_DIR}`);
  } finally {
    await browser.close();
  }
})();
