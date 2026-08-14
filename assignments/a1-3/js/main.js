(function(){
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- nav ---------- */
  var nav = document.getElementById('nav');
  window.addEventListener('scroll', function(){
    nav.classList.toggle('scrolled', window.scrollY > 40);
  }, { passive: true });

  var navToggle = document.getElementById('navToggle');
  var mobileOverlay = document.getElementById('mobileOverlay');
  var mobileClose = document.getElementById('mobileClose');
  navToggle.addEventListener('click', function(){ mobileOverlay.classList.add('open'); });
  mobileClose.addEventListener('click', function(){ mobileOverlay.classList.remove('open'); });
  mobileOverlay.querySelectorAll('a').forEach(function(a){
    a.addEventListener('click', function(){ mobileOverlay.classList.remove('open'); });
  });

  document.getElementById('ctaCollection').addEventListener('click', function(){
    var el = document.getElementById('collection');
    el.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth' });
  });

  /* ---------- scroll reveal ---------- */
  var observer = new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      if (e.isIntersecting) { e.target.classList.add('in'); observer.unobserve(e.target); }
    });
  }, { threshold: 0.15 });
  document.querySelectorAll('.fade-up').forEach(function(el){ observer.observe(el); });

  /* ---------- brand story accordion ---------- */
  var storyMore = document.getElementById('storyMore');
  var storyToggle = document.getElementById('storyToggle');
  storyToggle.addEventListener('click', function(){
    var isOpen = storyMore.classList.toggle('open');
    storyToggle.classList.toggle('open', isOpen);
    storyToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    storyToggle.querySelector('.label').textContent = isOpen ? '접기' : '더 보기';
  });

  /* ---------- reflective prompt (ephemeral, no persistence) ---------- */
  var promptForm = document.getElementById('promptForm');
  var promptInput = document.getElementById('promptInput');
  var promptReply = document.getElementById('promptReply');
  promptInput.addEventListener('input', function(){ promptReply.classList.remove('show'); });
  promptForm.addEventListener('submit', function(e){
    e.preventDefault();
    if (!promptInput.value.trim()) return;
    promptReply.classList.add('show');
  });

  /* ---------- newsletter ---------- */
  var subscribeForm = document.getElementById('subscribeForm');
  var subscribeEmail = document.getElementById('subscribeEmail');
  var subscribeMsg = document.getElementById('subscribeMsg');
  subscribeForm.addEventListener('submit', function(e){
    e.preventDefault();
    var val = subscribeEmail.value.trim();
    if (!val || val.indexOf('@') === -1) {
      subscribeMsg.textContent = '올바른 이메일 주소를 입력해주세요.';
      subscribeMsg.style.color = 'var(--state-error)';
    } else {
      subscribeMsg.textContent = '구독해주셔서 감사합니다.';
      subscribeMsg.style.color = 'var(--gold-light)';
      subscribeForm.reset();
    }
  });

  /* ---------- notes highlight-promotion motion ---------- */
  /* 실측 상수 — 1920px 기준, 바꾸지 말 것 */
  var TRANSITION_MS = reducedMotion ? 1 : 380;
  var HOLD_EQUAL_MS = 450;
  var HOLD_HIGHLIGHT_MS = 1200;
  var CONTENT_FADE_MS = 240;
  var CONTENT_DELAY_MS = 120;
  var WIDTH_HIGHLIGHT = 1119, WIDTH_SIDE = 281, WIDTH_EQUAL = 512;
  var GAP_EQUAL = 105, GAP_HIGHLIGHT = 33;
  var HEIGHT_HIGHLIGHT = 773, HEIGHT_SIDE = 427;
  var STAGE_BASE = 1920;
  var EASE = 'cubic-bezier(0.2, 0, 0.4, 1)';

  var notesData = [
    { num:'01', en:'Top Note', kr:'탑 노트', list:'베르가못 · 라임 · 만다린', img:'images/note-top.webp', alt:'짙은 남색 배경 위로 물방울이 튀는 라임과 시트러스 열매 클로즈업' },
    { num:'02', en:'Heart Note', kr:'미들 노트', list:'화이트 아이리스 · 자스민 · 인센스 스모크', img:'images/note-heart.webp', alt:'짙은 남색 실크 위에서 연기가 피어오르는 화이트 아이리스와 자스민 꽃송이' },
    { num:'03', en:'Base Note', kr:'베이스 노트', list:'앰버 · 다크 우드 · 청금석', img:'images/note-base.webp', alt:'짙은 남색 배경 속 앰버 원석과 다크 우드, 청금석이 어우러진 정물' }
  ];

  var motionGrid = document.getElementById('notesMotion');
  var cards = [];
  notesData.forEach(function(n, i){
    var card = document.createElement('div');
    card.className = 'note-card';
    card.innerHTML =
      '<img src="' + n.img + '" alt="' + n.alt + '">' +
      '<div class="scrim"></div>' +
      '<div class="note-num">' + n.num + '</div>' +
      '<div class="note-en">' + n.en + '</div>' +
      '<div class="note-kr">' + n.kr + '</div>' +
      '<div class="note-body"><div class="rule"></div><div class="list">' + n.list + '</div></div>';
    card.addEventListener('click', function(){ manualGoTo(i); });
    motionGrid.appendChild(card);
    cards.push(card);
  });

  var highlightIndex = 0;
  var phase = 'highlighted'; // 'highlighted' | 'equal'
  var timers = [];

  function clearTimers(){ timers.forEach(function(t){ clearTimeout(t); }); timers = []; }

  function applyLayout(){
    var containerWidth = motionGrid.getBoundingClientRect().width || STAGE_BASE;
    var scale = containerWidth / STAGE_BASE;
    var wHi = WIDTH_HIGHLIGHT * scale, wSide = WIDTH_SIDE * scale, wEq = WIDTH_EQUAL * scale;
    var gEq = GAP_EQUAL * scale, gHi = GAP_HIGHLIGHT * scale;
    var hHi = HEIGHT_HIGHLIGHT * scale, hSide = HEIGHT_SIDE * scale;
    var isEqual = phase === 'equal';

    var cols;
    if (isEqual) {
      cols = wEq + 'px ' + wEq + 'px ' + wEq + 'px';
    } else {
      var widths = [wSide, wSide, wSide];
      widths[highlightIndex] = wHi;
      cols = widths.map(function(w){ return w + 'px'; }).join(' ');
    }
    motionGrid.style.gridTemplateColumns = cols;
    motionGrid.style.gap = (isEqual ? gEq : gHi) + 'px';
    motionGrid.style.transitionDuration = TRANSITION_MS + 'ms';
    motionGrid.style.transitionTimingFunction = EASE;

    cards.forEach(function(card, i){
      var isHi = !isEqual && highlightIndex === i;
      card.style.height = (isHi ? hHi : hSide) + 'px';
      card.style.transition = 'height ' + TRANSITION_MS + 'ms ' + EASE
        + ', border-color ' + TRANSITION_MS + 'ms ' + EASE
        + ', background-color ' + TRANSITION_MS + 'ms ' + EASE;
      card.classList.toggle('is-highlighted', isHi);
      var body = card.querySelector('.note-body');
      body.style.maxHeight = isHi ? '260px' : '0px';
      body.style.opacity = isHi ? '1' : '0';
      body.style.transition = isHi
        ? 'max-height ' + TRANSITION_MS + 'ms ' + EASE + ', opacity ' + CONTENT_FADE_MS + 'ms ' + EASE + ' ' + CONTENT_DELAY_MS + 'ms'
        : 'max-height ' + TRANSITION_MS + 'ms ' + EASE + ', opacity ' + CONTENT_FADE_MS + 'ms ' + EASE;
    });
  }

  // 강조 ──380ms──▶ 균등 ──450ms 유지──▶ 다음 강조 ──380ms──▶ … ──1200ms 유지── 반복
  function scheduleAutoAdvance(){
    clearTimers();
    timers.push(setTimeout(function(){
      phase = 'equal'; applyLayout();
      timers.push(setTimeout(function(){
        highlightIndex = (highlightIndex + 1) % 3;
        phase = 'highlighted'; applyLayout();
        timers.push(setTimeout(scheduleAutoAdvance, TRANSITION_MS));
      }, TRANSITION_MS + HOLD_EQUAL_MS));
    }, HOLD_HIGHLIGHT_MS));
  }

  function manualGoTo(targetIndex){
    if (targetIndex === highlightIndex && phase === 'highlighted') return;
    clearTimers();
    phase = 'equal'; applyLayout();
    timers.push(setTimeout(function(){
      highlightIndex = targetIndex;
      phase = 'highlighted'; applyLayout();
      timers.push(setTimeout(scheduleAutoAdvance, TRANSITION_MS));
    }, TRANSITION_MS + HOLD_EQUAL_MS));
  }

  applyLayout();
  if (!reducedMotion) scheduleAutoAdvance();

  var ro = new ResizeObserver(function(){ applyLayout(); });
  ro.observe(motionGrid);
})();
