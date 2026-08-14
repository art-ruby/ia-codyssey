/* LAPIS 향 큐레이터 — 입력 수집, 검증, 호출, 상태 전환.
   모델이 만든 문자열은 전부 textContent로 넣는다. innerHTML을 쓰지 않는다. */
(function () {
  var form = document.getElementById('curatorForm');
  if (!form) return;

  var momentInput = document.getElementById('curatorMoment');
  var fieldMsg = document.getElementById('curatorFieldMsg');
  var submit = document.getElementById('curatorSubmit');
  var result = document.getElementById('curatorResult');

  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var CLIENT_TIMEOUT_MS = 30000;
  var WAIT_STAGES = [
    { after: 0, text: '당신의 노트를 고르는 중' },
    { after: 6000, text: '조금 더 걸리고 있습니다' },
    { after: 15000, text: '거의 다 왔습니다' }
  ];
  var NOTE_LAYERS = [
    { key: 'top', label: 'TOP' },
    { key: 'heart', label: 'HEART' },
    { key: 'base', label: 'BASE' }
  ];

  var waitTimers = [];

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function clearResult() {
    waitTimers.forEach(clearTimeout);
    waitTimers = [];
    while (result.firstChild) result.removeChild(result.firstChild);
  }

  function selectedValue(name) {
    var checked = form.querySelector('input[name="' + name + '"]:checked');
    return checked ? checked.value : '';
  }

  function showFieldError(message) {
    fieldMsg.textContent = message;
    momentInput.classList.add('invalid');
    momentInput.focus();
  }

  function clearFieldError() {
    fieldMsg.textContent = '';
    momentInput.classList.remove('invalid');
  }

  function renderLoading() {
    clearResult();
    result.setAttribute('aria-busy', 'true');

    var box = el('div', 'curator-skeleton');
    ['w1', 'w2', 'w3'].forEach(function (w) {
      box.appendChild(el('div', 'curator-bar ' + w));
    });
    var label = el('div', 'curator-loading', WAIT_STAGES[0].text);
    box.appendChild(label);
    result.appendChild(box);

    WAIT_STAGES.slice(1).forEach(function (stage) {
      waitTimers.push(setTimeout(function () {
        label.textContent = stage.text;
      }, stage.after));
    });
  }

  function renderError(message, code, retryable) {
    clearResult();
    result.setAttribute('aria-busy', 'false');

    var box = el('div', 'curator-error');
    box.appendChild(el('p', 'curator-error-title',
      retryable ? '지금은 향을 고르지 못했습니다' : '지금은 큐레이터를 이용할 수 없습니다'));
    box.appendChild(el('p', 'curator-error-body', message));

    if (retryable) {
      var again = el('button', 'curator-submit', '다시 시도');
      again.type = 'button';
      again.addEventListener('click', run);
      box.appendChild(again);
    }

    if (code) box.appendChild(el('div', 'curator-error-code', code));
    result.appendChild(box);
  }

  function renderResult(data) {
    clearResult();
    result.setAttribute('aria-busy', 'false');

    var card = el('div', 'curator-card');
    card.appendChild(el('div', 'curator-name', data.name));
    card.appendChild(el('div', 'curator-name-kr', data.name_kr));
    card.appendChild(el('p', 'curator-copy', data.copy));

    var grid = el('div', 'curator-notes');
    NOTE_LAYERS.forEach(function (layer, index) {
      var note = data.notes[layer.key];
      var cell = el('div', 'curator-note');
      if (!reducedMotion) cell.style.animationDelay = (index * 120) + 'ms';
      cell.appendChild(el('div', 'curator-note-label', layer.label));
      cell.appendChild(el('div', 'curator-note-materials', note.materials.join(' · ')));
      cell.appendChild(el('div', 'curator-note-desc', note.description));
      grid.appendChild(cell);
    });
    card.appendChild(grid);

    card.appendChild(el('div', 'curator-scene', data.scene));
    result.appendChild(card);
  }

  function run() {
    var moment = momentInput.value.trim();
    if (!moment) {
      showFieldError('닿고 싶은 순간을 한 줄 남겨 주세요.');
      clearResult();
      return;
    }
    if (!selectedValue('season') || !selectedValue('time') || !selectedValue('mood')) {
      showFieldError('계절 · 시간 · 무드를 모두 골라 주세요.');
      clearResult();
      return;
    }
    clearFieldError();

    submit.disabled = true;
    submit.textContent = '향 찾는 중';
    renderLoading();

    var controller = new AbortController();
    var abortTimer = setTimeout(function () { controller.abort(); }, CLIENT_TIMEOUT_MS);

    fetch('/api/curate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        season: selectedValue('season'),
        time: selectedValue('time'),
        mood: selectedValue('mood'),
        moment: moment
      }),
      signal: controller.signal
    })
      .then(function (response) {
        return response.json().then(function (payload) {
          return { ok: response.ok, payload: payload };
        });
      })
      .then(function (outcome) {
        if (outcome.ok) {
          renderResult(outcome.payload);
          return;
        }
        var error = (outcome.payload && outcome.payload.error) || {};
        var code = error.code || 'UNKNOWN';
        renderError(
          error.message || '잠시 뒤 다시 시도해 주세요.',
          code,
          code !== 'SERVICE_UNAVAILABLE'
        );
      })
      .catch(function (err) {
        if (err.name === 'AbortError') {
          renderError('응답이 오지 않았습니다. 잠시 뒤 다시 시도해 주세요.', 'CLIENT_TIMEOUT', true);
        } else {
          renderError('연결에 실패했습니다. 네트워크를 확인해 주세요.', 'NETWORK_ERROR', true);
        }
      })
      .then(function () {
        clearTimeout(abortTimer);
        submit.disabled = false;
        submit.textContent = '향 찾기';
      });
  }

  momentInput.addEventListener('input', clearFieldError);
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    run();
  });
})();
