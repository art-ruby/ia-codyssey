// 공개 웹 설정 예시. 같은 폴더에 config.js로 복사해 값을 채운다(config.js는 Git 제외).
// 배포 때는 T08.02의 빌드 단계가 Vercel 환경변수로 config.js를 생성한다.
// 여기에는 브라우저에 공개되어도 되는 값만 둔다. 서버 키·서비스 계정은 절대 넣지 않는다.
window.AI_SECRETARY_CONFIG = {
  apiBaseUrl: "http://127.0.0.1:8000",
  firebase: {
    apiKey: "",
    authDomain: "",
    projectId: "",
  },
};
