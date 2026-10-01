// 공개 웹 설정의 구조. 직접 고치지 말고 `node web/scripts/build-config.mjs`로 config.js를 생성한다.
// 여기에는 브라우저에 공개되어도 되는 값만 들어간다. 서버 키·서비스 계정은 절대 넣지 않는다.
window.AI_SECRETARY_CONFIG = {
  apiBaseUrl: "__API_BASE_URL__",
  firebase: {
    apiKey: "__FIREBASE_WEB_API_KEY__",
    authDomain: "__FIREBASE_AUTH_DOMAIN__",
    projectId: "__FIREBASE_PROJECT_ID__",
  },
};
