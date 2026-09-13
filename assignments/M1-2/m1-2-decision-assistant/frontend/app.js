/**
 * RADAR Decision Assistant — 프론트엔드 로직 (프레임워크 없음)
 *
 * 오류 처리 원칙: AutoMaker 감사에서 본 실패 방식을 되풀이하지 않는다.
 * 거기서는 연결 거부·401·404·500·JSON 파싱 실패가 전부 "서버 오류" 한 문구로
 * 합쳐져 사용자가 원인을 구분할 수 없었다. 여기서는 계층마다 다른 문구를 낸다.
 */
'use strict';

// ── 상태 ─────────────────────────────────────────
const state = {
  candidates: [],
  summary: null,
  selectedId: null,
  conversationId: '',
  filters: { channel: '', decision: '' },
  lastLedger: null, // 마지막 결정이 RADAR 원장에 남았는지 (id, written, decision_id, revision, reason)
  lastHandoff: null, // 마지막 인계 결과 (id, ok, package_id, revision, link | error)
  persona: null, // AutoMaker 페르소나 상태 (id, draft, draft_hash, persona_status, radar_draft | error)
};

const $ = (id) => document.getElementById(id);

// ── API 주소 ─────────────────────────────────────
const API_KEY_LS = 'rda_api_base';

function apiBase() {
  try {
    const saved = localStorage.getItem(API_KEY_LS);
    if (saved) return saved.replace(/\/+$/, '');
  } catch (e) { /* 사생활 보호 모드 등 — 기본값으로 진행 */ }
  return (window.API_BASE_DEFAULT || '').replace(/\/+$/, '');
}

class ApiError extends Error {
  constructor(kind, message, status) {
    super(message);
    this.kind = kind;
    this.status = status || 0;
  }
}

/** 원인별로 다른 kind 를 붙여 던진다. 화면은 kind 로 문구를 고른다. */
async function api(path, options = {}) {
  const url = apiBase() + path;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), window.API_TIMEOUT_MS || 60000);

  let response;
  try {
    response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
    });
  } catch (err) {
    clearTimeout(timer);
    if (err.name === 'AbortError') {
      throw new ApiError('timeout', '서버가 제한 시간 안에 응답하지 않았습니다. Render 무료 플랜이면 콜드 스타트일 수 있습니다.');
    }
    // fetch 자체가 던진 경우 = 네트워크 계층. 서버 응답을 받지 못한 상태다.
    throw new ApiError('unreachable', `서버에 연결하지 못했습니다 (${url}). 주소와 서버 실행 상태를 확인하세요.`);
  }
  clearTimeout(timer);

  const text = await response.text();
  let data = null;
  let parseFailed = false;
  if (text) {
    try { data = JSON.parse(text); } catch (e) { parseFailed = true; }
  }

  if (response.ok) {
    if (parseFailed) {
      throw new ApiError('bad_payload', '서버가 JSON 이 아닌 응답을 보냈습니다. API 주소가 백엔드가 맞는지 확인하세요.', response.status);
    }
    return data;
  }

  if (response.status === 404) {
    throw new ApiError('not_found', (data && (data.detail || data.error)) || '요청한 항목이 없습니다.', 404);
  }
  if (response.status === 409) {
    throw new ApiError('conflict', (data && (data.detail || data.error)) || '현재 상태에서는 할 수 없는 동작입니다.', 409);
  }
  if (response.status === 422) {
    const first = data && Array.isArray(data.detail) ? data.detail[0] : null;
    const where = first && Array.isArray(first.loc) ? first.loc.slice(-1)[0] : '';
    throw new ApiError('invalid_input', `입력값이 올바르지 않습니다${where ? ` (${where})` : ''}: ${first ? first.msg : ''}`, 422);
  }
  if (response.status >= 500) {
    const detail = (data && (data.error || data.detail)) || text.slice(0, 200);
    throw new ApiError('server_error', `서버 내부 오류: ${detail}`, response.status);
  }
  throw new ApiError('request_failed', (data && (data.detail || data.error)) || `요청 실패 (HTTP ${response.status})`, response.status);
}

function describeError(err) {
  if (!(err instanceof ApiError)) return `알 수 없는 오류: ${err.message}`;
  return err.message;
}

// ── 토스트 ───────────────────────────────────────
let toastTimer = null;
function toast(message) {
  const box = $('toast');
  box.textContent = message;
  box.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { box.hidden = true; }, 3800);
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

// ── health ───────────────────────────────────────
async function loadHealth() {
  const badge = $('healthBadge');
  try {
    const health = await api('/api/health');
    const warnings = health.warnings || [];
    badge.textContent = warnings.length ? `연결됨 · 주의 ${warnings.length}` : '연결됨';
    badge.className = warnings.length ? 'badge badge-warn' : 'badge badge-ok';
    const banner = $('banner');
    if (warnings.length) {
      banner.innerHTML = warnings.map((w) => `⚠️ ${escapeHtml(w)}`).join('<br>');
      banner.hidden = false;
    } else {
      banner.hidden = true;
    }
  } catch (err) {
    badge.textContent = '연결 실패';
    badge.className = 'badge badge-error';
    const banner = $('banner');
    banner.textContent = describeError(err);
    banner.hidden = false;
  }
}

// ── 후보 목록 ────────────────────────────────────
function decisionOf(item) { return item.decision || 'PENDING'; }

async function loadCandidates() {
  const body = $('candidateBody');
  try {
    const params = new URLSearchParams();
    if (state.filters.channel) params.set('channel', state.filters.channel);
    if (state.filters.decision) params.set('decision', state.filters.decision);
    const query = params.toString();
    state.candidates = await api('/api/data' + (query ? `?${query}` : ''));
    renderCandidates();
    syncChannelFilter();
  } catch (err) {
    body.innerHTML = `<tr><td colspan="8" class="empty">${escapeHtml(describeError(err))}</td></tr>`;
    $('rowCount').textContent = '0';
  }
}

function renderCandidates() {
  const body = $('candidateBody');
  if (!state.candidates.length) {
    body.innerHTML = '<tr><td colspan="8" class="empty">후보가 없습니다. [표본 적재] 를 눌러 시작하세요.</td></tr>';
    $('rowCount').textContent = '0';
    return;
  }
  body.innerHTML = state.candidates.map((item) => {
    const decision = decisionOf(item);
    const source = item.source || 'manual';
    return `<tr data-id="${item.id}" class="${item.id === state.selectedId ? 'selected' : ''}">
      <td><span class="tag tag-${source}">${source === 'sample' ? '표본' : source === 'radar' ? '실측' : '수동'}</span></td>
      <td class="title-cell">${escapeHtml(item.title || '(제목 없음)')}</td>
      <td>${escapeHtml(item.topic || '-')}</td>
      <td>${escapeHtml(item.channel || '-')}</td>
      <td class="num">${item.value}</td>
      <td>${String(item.date).slice(0, 10)}</td>
      <td><span class="tag tag-${decision}">${decision === 'PENDING' ? '미정' : decision}</span></td>
      <td><button class="btn btn-small" data-delete="${item.id}" title="삭제">✕</button></td>
    </tr>`;
  }).join('');
  $('rowCount').textContent = String(state.candidates.length);
}

function syncChannelFilter() {
  const select = $('filterChannel');
  const current = select.value;
  const channels = [...new Set(state.candidates.map((c) => c.channel).filter(Boolean))].sort();
  select.innerHTML = '<option value="">전체 채널</option>'
    + channels.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
  select.value = current;
}

// ── 요약 ─────────────────────────────────────────
async function loadSummary() {
  try {
    const summary = await api('/api/data/summary');
    state.summary = summary;
    renderSummary(summary);
  } catch (err) {
    $('sumTrend').textContent = describeError(err);
  }
}

function renderSummary(s) {
  $('sumCount').textContent = s.count;
  $('sumAvg').textContent = s.metrics.average_score;
  $('sumMax').textContent = s.metrics.max_score;
  $('sumMin').textContent = s.metrics.min_score;
  $('sumPeriod').textContent = `기간 ${s.period}`;
  $('sumTrend').textContent = s.trend;

  const order = [['MAKE', 'var(--make)'], ['WATCH', 'var(--watch)'], ['SKIP', 'var(--skip)'], ['PENDING', 'var(--pending)']];
  const total = order.reduce((sum, [k]) => sum + (s.decisions[k] || 0), 0) || 1;
  $('decisionBar').innerHTML = order
    .map(([k, color]) => `<span style="width:${((s.decisions[k] || 0) / total) * 100}%;background:${color}" title="${k} ${s.decisions[k] || 0}"></span>`)
    .join('');
  $('decisionLegend').innerHTML = order
    .map(([k, color]) => `<li><i class="swatch" style="background:${color}"></i>${k === 'PENDING' ? '미정' : k} ${s.decisions[k] || 0}</li>`)
    .join('');

  $('topTopics').innerHTML = s.top_topics.length
    ? s.top_topics.map((t) => `<li>${escapeHtml(t)}</li>`).join('')
    : '<li class="muted">–</li>';

  renderSparkline();
}

/** 점수 추이 그래프. 라이브러리 없이 SVG 를 직접 그린다. */
function renderSparkline() {
  const svg = $('sparkline');
  const note = $('chartNote');
  const points = state.candidates
    .map((c) => ({ t: new Date(c.date).getTime(), v: Number(c.value) }))
    .filter((p) => Number.isFinite(p.t) && Number.isFinite(p.v))
    .sort((a, b) => a.t - b.t);

  if (points.length < 2) {
    svg.innerHTML = '';
    note.textContent = '표시할 점이 부족합니다.';
    return;
  }

  const W = 600, H = 140, PAD = 8;
  const t0 = points[0].t, t1 = points[points.length - 1].t || t0 + 1;
  const x = (t) => PAD + ((t - t0) / (t1 - t0 || 1)) * (W - PAD * 2);
  const y = (v) => H - PAD - (v / 100) * (H - PAD * 2);

  // 개별 점은 잡음이 커서 추세가 안 보인다. 7점 이동평균을 함께 그린다.
  const window = 7;
  const smoothed = points.map((p, i) => {
    const from = Math.max(0, i - window + 1);
    const slice = points.slice(from, i + 1);
    return { t: p.t, v: slice.reduce((sum, q) => sum + q.v, 0) / slice.length };
  });

  const dots = points
    .map((p) => `<circle cx="${x(p.t).toFixed(1)}" cy="${y(p.v).toFixed(1)}" r="1.6" fill="var(--accent)" opacity=".28"/>`)
    .join('');
  const line = smoothed
    .map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`)
    .join(' ');

  svg.innerHTML = `
    <line x1="${PAD}" y1="${y(50)}" x2="${W - PAD}" y2="${y(50)}" stroke="var(--line)" stroke-dasharray="3 3"/>
    ${dots}
    <path d="${line}" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round"/>`;
  note.textContent = `점 ${points.length}개(옅은 점) · 굵은 선은 ${window}점 이동평균 · 파선은 50점`;
}

// ── 선택 · 결정 ──────────────────────────────────
function selectCandidate(id) {
  state.selectedId = id;
  renderCandidates();
  renderSelected();
}

/**
 * ③ 답변의 인용 → ① 표의 실제 행. 여기가 «다시 찾아 검증하는» 수고를 없애는 지점.
 * 현재 필터에 걸려 표에 없으면 필터를 풀고 다시 불러온다. 그래도 없으면
 * (삭제됐거나 다른 데이터를 적재한 경우) 그 사실을 말하고 아무 행도 고르지 않는다.
 */
async function jumpToCandidate(id) {
  let row = state.candidates.find((c) => c.id === id);
  if (!row && (state.filters.channel || state.filters.decision)) {
    state.filters = { channel: '', decision: '' };
    $('filterChannel').value = '';
    $('filterDecision').value = '';
    await loadCandidates();
    row = state.candidates.find((c) => c.id === id);
    if (row) toast('필터를 해제하고 후보를 찾았습니다.');
  }
  if (!row) {
    toast('이 후보는 현재 표에 없습니다 — 삭제됐거나 다른 데이터가 적재된 상태입니다.');
    return;
  }
  selectCandidate(id);
  const tr = $('candidateBody').querySelector(`tr[data-id="${CSS.escape(id)}"]`);
  if (tr) {
    tr.scrollIntoView({ block: 'center', behavior: 'smooth' });
    tr.classList.remove('flash');
    void tr.offsetWidth; // 애니메이션 재시작
    tr.classList.add('flash');
  }
  $('selectedBox').scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

function renderSelected() {
  const box = $('selectedBox');
  const item = state.candidates.find((c) => c.id === state.selectedId);
  if (!item) {
    box.innerHTML = '<p class="muted">후보 목록에서 항목을 선택하면 여기서 판단을 바꿀 수 있습니다.</p>';
    return;
  }
  const decision = decisionOf(item);
  box.innerHTML = `
    <p class="selected-title">${escapeHtml(item.title || '(제목 없음)')}</p>
    <p class="selected-meta">
      ${escapeHtml(item.channel || '-')} · ${escapeHtml(item.topic || '-')} ·
      ${item.value}점 · ${String(item.date).slice(0, 10)} ·
      <span class="tag tag-${item.source || 'manual'}">${item.source === 'sample' ? '표본' : item.source === 'radar' ? '실측' : '수동'}</span>
    </p>
    <div class="decision-buttons">
      <button class="btn btn-make ${decision === 'MAKE' ? 'active' : ''}" data-decision="MAKE">MAKE</button>
      <button class="btn btn-watch ${decision === 'WATCH' ? 'active' : ''}" data-decision="WATCH">WATCH</button>
      <button class="btn btn-skip ${decision === 'SKIP' ? 'active' : ''}" data-decision="SKIP">SKIP</button>
    </div>
    <textarea class="reason-input" id="reasonInput" rows="3"
      placeholder="판단 근거 (줄바꿈으로 여러 개)">${escapeHtml(item.decision_reason || '')}</textarea>
    ${renderHandoffButton(item, decision)}
    ${renderLedgerLine(item)}
    ${renderHandoffLine(item)}
    ${renderPersonaBlock(item)}`;
}

/**
 * AutoMaker 채널 페르소나. AutoMaker 는 사람이 승인하기 전엔 채우지 않는다(근거≠정체성).
 * 초안은 AutoMaker 의 프롬프트를 DA 의 모델 키로 돌려 AutoMaker 에 저장한다. 승인은 여기서도 사람이 누른다.
 */
function renderPersonaBlock(item) {
  if (item.source !== 'radar' || decisionOf(item) !== 'MAKE') return '';
  const ps = state.persona && state.persona.id === item.id ? state.persona : null;
  if (!ps) return `<div class="persona-box"><button class="btn btn-small" id="btnPersonaState">AutoMaker 페르소나 상태 보기</button></div>`;
  if (ps.error) return `<div class="persona-box"><p class="ledger-line ledger-no">${escapeHtml(ps.error)}</p></div>`;
  if (ps.persona_status === 'approved' || ps.radar_draft === false) {
    return `<div class="persona-box"><p class="ledger-line ledger-ok">채널 페르소나 승인됨 (AutoMaker)</p>
      <pre class="persona-text">${escapeHtml(ps.channel_persona || '')}</pre></div>`;
  }
  const d = ps.draft;
  if (!d) {
    return `<div class="persona-box"><p class="ledger-line muted">페르소나 없음 — RADAR 초안 채널 (승인 대기). 초안이 아직 없습니다.</p>
      <button class="btn btn-primary btn-small" id="btnPersonaDraft">페르소나 초안 만들기 (AutoMaker 프롬프트 × DA 모델)</button></div>`;
  }
  return `<div class="persona-box">
      <p class="ledger-line ledger-ok">페르소나 초안 저장됨 · review_pending · <code>${escapeHtml(String(ps.draft_hash || '').slice(0, 16))}</code></p>
      <details open><summary>초안 내용 (검토)</summary>
        <pre class="persona-text">${escapeHtml(d.persona || '')}</pre>
        <p class="ledger-line"><b>아트 디렉션 · ${escapeHtml((d.art_direction || {}).name || '')}</b></p>
        <pre class="persona-text">${escapeHtml((d.art_direction || {}).description || '')}</pre>
      </details>
      <div class="decision-buttons">
        <button class="btn btn-make btn-small" id="btnPersonaApprove">이 초안을 채널 페르소나로 승인</button>
        <button class="btn btn-small" id="btnPersonaDraft">초안 다시 만들기</button>
      </div>
      <p class="hint">승인하면 AutoMaker 가 <code>radar_draft=false</code> 로 잠급니다. 이후 변경은 AutoMaker 채널 설정에서.</p>
    </div>`;
}

async function loadPersona(id) {
  try {
    const r = await api(`/api/handoff/${id}/persona`);
    state.persona = { id, ...r };
  } catch (err) {
    state.persona = { id, error: describeError(err) };
  }
  renderSelected();
}

async function makePersonaDraft(id) {
  const btn = $('btnPersonaDraft');
  if (btn) { btn.disabled = true; btn.textContent = '초안 생성 중… (모델 호출)'; }
  try {
    const r = await api(`/api/handoff/${id}/persona-draft`, { method: 'POST' });
    toast(`초안 저장됨 · ${r.model} · ${String(r.draft_hash || '').slice(0, 12)}…`);
  } catch (err) {
    toast(describeError(err));
  }
  await loadPersona(id);
}

async function approvePersona(id) {
  const ps = state.persona;
  if (!ps || !ps.draft_hash) { toast('승인할 초안이 없습니다.'); return; }
  if (!window.confirm('이 초안을 AutoMaker 채널 페르소나로 승인합니다. 승인 후에는 잠깁니다. 계속할까요?')) return;
  try {
    const r = await api(`/api/handoff/${id}/persona-approve`, { method: 'POST', body: JSON.stringify({ draft_hash: ps.draft_hash }) });
    toast(`승인됨 · persona_status=${r.persona_status}`);
  } catch (err) {
    toast(describeError(err));
  }
  await loadPersona(id);
}

function renderHandoffButton(item, decision) {
  if (item.source !== 'radar') {
    return '<button class="btn btn-primary" id="btnHandoff" disabled title="실측(radar) 후보만 RADAR 패키지가 됩니다">실측 후보만 인계 가능</button>';
  }
  if (decision !== 'MAKE') {
    return '<button class="btn btn-primary" id="btnHandoff" disabled>MAKE 확정 후 인계 가능</button>';
  }
  return '<button class="btn btn-primary" id="btnHandoff">AutoMaker 로 인계 (RADAR 패키지)</button>';
}

/** 마지막 인계 결과. 성공이면 RADAR package_id·revision 과 AutoMaker 확인 링크, 실패면 이유. */
function renderHandoffLine(item) {
  const last = state.lastHandoff && state.lastHandoff.id === item.id ? state.lastHandoff : null;
  if (!last) return '';
  if (last.ok) {
    const pack = last.source_pack || {};
    const packLine = pack.included
      ? `Source Pack 동봉 · <code>${escapeHtml(String(pack.hash || '').slice(0, 16))}</code>`
      : `Source Pack 없음 — ${escapeHtml(pack.reason || '소재·브리프만 전송')}`;
    const link = last.link_result || {};
    const linkLine = link.ok
      ? `프로젝트 반영 · 받은 rev ${link.received_revision} (project.json 은 rev ${link.source_revision} 유지 — 사용자 편집 보호)`
      : link.needs_human
        ? `프로젝트 미연결 — AutoMaker 에서 제작 채널을 확인해 연결해야 합니다`
        : `프로젝트 반영 안 됨 — ${escapeHtml(link.error || '')}`;
    return `<p class="ledger-line ledger-ok">AutoMaker 수신 확인 · <code>${escapeHtml(last.package_id)}</code> rev ${last.revision}
      · <a href="${escapeHtml(last.link)}" target="_blank" rel="noopener">AutoMaker 에서 확인 →</a></p>
      <p class="ledger-line ${pack.included ? 'ledger-ok' : 'muted'}">${packLine}</p>
      <p class="ledger-line ${link.ok ? 'ledger-ok' : 'ledger-no'}">${linkLine}</p>`;
  }
  return `<p class="ledger-line ledger-no">인계 안 됨 — ${escapeHtml(last.error || '')}</p>`;
}

/**
 * 이 결정이 «어디에» 남았는지 한 줄. 실측이면 RADAR decisions.jsonl 이 정본이고,
 * 표본/수동이면 DA 저장소에만 있다(재시작 시 소멸). 사용자가 착각하지 않게 적는다.
 */
function renderLedgerLine(item) {
  const last = state.lastLedger && state.lastLedger.id === item.id ? state.lastLedger : null;
  if (last && last.written) {
    return `<p class="ledger-line ledger-ok">RADAR 원장 기록됨 · <code>${escapeHtml(last.decision_id)}</code> · rev ${last.revision}</p>`;
  }
  if (last && !last.written) {
    return `<p class="ledger-line ledger-no">RADAR 원장 미기록 — ${escapeHtml(last.reason || '')}</p>`;
  }
  if (item.source === 'radar') {
    return '<p class="ledger-line muted">실측 후보 — 판단을 누르면 RADAR decisions.jsonl 에 기록됩니다.</p>';
  }
  return '<p class="ledger-line muted">표본/수동 후보 — 판단은 DA 저장소에만 남습니다 (RADAR 원장에 쓰지 않음).</p>';
}

async function setDecision(decision) {
  const item = state.candidates.find((c) => c.id === state.selectedId);
  if (!item) return;

  const typed = ($('reasonInput') || {}).value || '';
  const stored = item.decision_reason || '';
  const changing = decisionOf(item) !== decision;
  // 판단을 바꿨는데 사유칸이 이전 판단의 근거 그대로면, 그것을 새 판단의
  // 근거로 넘기지 않는다. SKIP 사유가 MAKE 의 근거로 인계 파일에 실리면
  // 나중에 왜 만들기로 했는지 되짚을 수 없다.
  const reason = changing && typed.trim() === stored.trim() ? '' : typed;

  try {
    const result = await api(`/api/data/${item.id}/decision`, {
      method: 'PATCH',
      body: JSON.stringify({ decision, reason }),
    });
    // 어디에 남았는지를 숨기지 않는다. RADAR 원장에 썼으면 id 를, 안 썼으면 이유를 보여준다.
    const ledger = result.ledger || {};
    state.lastLedger = { id: item.id, ...ledger };
    toast(ledger.written
      ? `${decision} — RADAR 원장 기록 ${ledger.decision_id.slice(0, 16)}… (rev ${ledger.revision})`
      : `${decision} 로 변경 (DA 에만 저장) — ${ledger.reason || ''}`);
    await Promise.all([loadCandidates(), loadSummary()]);
    renderSelected();
  } catch (err) {
    toast(describeError(err));
  }
}

async function createHandoff() {
  if (!state.selectedId) return;
  const btn = $('btnHandoff');
  if (btn) { btn.disabled = true; btn.textContent = 'RADAR 패키징 → AutoMaker 전송 중…'; }
  try {
    const result = await api(`/api/handoff/${state.selectedId}`, { method: 'POST' });
    // 무엇이 어디로 갔는지 남긴다. package_id·revision 은 RADAR 저널의 것, 수신 확인은 AutoMaker 의 것.
    state.lastHandoff = { id: state.selectedId, ...result };
    toast(`AutoMaker 수신 확인 · ${result.package_id.slice(0, 20)}… rev ${result.revision}`);
    loadHandoffs();
  } catch (err) {
    state.lastHandoff = { id: state.selectedId, ok: false, error: describeError(err) };
    toast(describeError(err));
  } finally {
    renderSelected();
  }
}

// ── 인계 목록 ────────────────────────────────────
async function loadHandoffs() {
  const list = $('handoffList');
  try {
    const result = await api('/api/handoff');
    if (!result.records.length) {
      list.innerHTML = '<li class="muted">아직 없습니다.</li>';
      return;
    }
    list.innerHTML = result.records.map((r) => `
      <li>
        <div class="handoff-title">${escapeHtml(r.topic || r.radar_id || '(제목 없음)')}</div>
        <div class="handoff-meta">
          ${escapeHtml(r.channel || '-')} · ${escapeHtml(r.decision || '-')} ·
          ${String(r.created_at || '').slice(0, 16).replace('T', ' ')} ·
          <code>${escapeHtml(r.package_id || '')}</code> rev ${r.revision}
          · 결정 <code>${escapeHtml((r.decision_id || '').slice(0, 16))}</code>
          · <a href="${escapeHtml(r.link)}" target="_blank" rel="noopener">AutoMaker 에서 확인 →</a>
        </div>
        ${r.note ? `<ul class="handoff-reason">${String(r.note).split(/\n+/).filter(Boolean).map((x) => `<li>${escapeHtml(x)}</li>`).join('')}</ul>` : ''}
      </li>`).join('');
  } catch (err) {
    list.innerHTML = `<li class="muted">${escapeHtml(describeError(err))}</li>`;
  }
}

// ── 채팅 ─────────────────────────────────────────
/**
 * 답변 본문의 «#N» 을 후보 행으로 잇는다.
 *
 * 서버가 준 refs(번호↔id 대응표) 에 있는 번호만 링크가 된다. 목록에 없는 번호는
 * 모델이 지어낸 것이므로 링크를 만들지 않고 «⚠ 목록에 없음» 으로 표시한다 —
 * 조용히 아무 행에나 붙이는 것이 가장 나쁜 방식이다.
 * innerHTML 을 쓰지 않는다. 본문은 모델 출력이라 그대로 노드로만 넣는다.
 */
function renderReplyBody(container, content, refs) {
  const byIndex = new Map((refs || []).map((r) => [r.index, r]));
  const pattern = /#(\d{1,3})(?!\d)/g;
  let last = 0;
  let m;
  while ((m = pattern.exec(content)) !== null) {
    if (m.index > last) container.appendChild(document.createTextNode(content.slice(last, m.index)));
    const ref = byIndex.get(Number(m[1]));
    if (ref) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ref-link';
      btn.dataset.refId = ref.id;
      btn.textContent = m[0];
      btn.title = `${ref.title || '(제목 없음)'} · ${ref.value}점 · ${ref.decision} — 클릭하면 ① 표에서 선택`;
      container.appendChild(btn);
    } else if (byIndex.size) {
      const bad = document.createElement('span');
      bad.className = 'ref-missing';
      bad.textContent = `${m[0]}⚠`;
      bad.title = '이번 답변의 [후보 목록]에 없는 번호입니다. 근거 없는 인용일 수 있습니다.';
      container.appendChild(bad);
    } else {
      container.appendChild(document.createTextNode(m[0]));
    }
    last = m.index + m[0].length;
  }
  if (last < content.length) container.appendChild(document.createTextNode(content.slice(last)));
}

/**
 * 답변이 실제로 인용한 후보만 칩으로 나열한다 (프롬프트에 넣은 25건 전부가 아니라).
 * 칩의 수치는 **답변 시점의 저장소 값**이다. AI 가 «근거 데이터» 줄에 옮겨 적은 값과
 * 다르면 여기서 드러난다 — 그것이 검증 지점이다.
 */
function renderCitedChips(container, content, refs) {
  if (!refs || !refs.length) return;
  const cited = new Set();
  for (const m of content.matchAll(/#(\d{1,3})(?!\d)/g)) cited.add(Number(m[1]));
  const rows = refs.filter((r) => cited.has(r.index));
  if (!rows.length) return;
  const wrap = document.createElement('div');
  wrap.className = 'ref-chips';
  const label = document.createElement('span');
  label.className = 'ref-chips-label';
  label.textContent = '인용 후보 (저장된 값) →';
  wrap.appendChild(label);
  rows.forEach((r) => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = `ref-chip ref-chip-${r.decision === '미정' ? 'PENDING' : r.decision}`;
    chip.dataset.refId = r.id;
    const src = r.source === 'sample' ? '표본' : r.source === 'radar' ? '실측' : '수동';
    chip.textContent = `#${r.index} ${(r.title || '(제목 없음)').slice(0, 28)}${(r.title || '').length > 28 ? '…' : ''} · ${r.value} · ${r.decision} · ${src}`;
    chip.title = `${r.title || ''}
채널 ${r.channel || '-'} · 주제 ${r.topic || '-'} · ${r.date}
id ${r.id}`;
    wrap.appendChild(chip);
  });
  container.appendChild(wrap);
}

function appendMessage(role, content, meta, source, refs) {
  const log = $('chatLog');
  const div = document.createElement('div');
  div.className = `msg msg-${role}`;
  if (source) {
    // 규칙 기반 결과를 GPT 응답처럼 보이게 하지 않는다.
    const badge = document.createElement('span');
    badge.className = `src-badge ${source.cls}`;
    badge.textContent = source.text;
    div.appendChild(badge);
  }
  if (role === 'assistant' && refs && refs.length) {
    renderReplyBody(div, content, refs);
    renderCitedChips(div, content, refs);
  } else {
    div.appendChild(document.createTextNode(content));
  }
  if (meta) {
    const small = document.createElement('div');
    small.className = 'msg-meta';
    small.textContent = meta;
    div.appendChild(small);
  }
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

async function sendChat(question) {
  appendMessage('user', question);
  $('chatInput').value = '';
  $('chatLoading').hidden = false;
  $('chatSend').disabled = true;
  try {
    const result = await api('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message: question, conversation_id: state.conversationId || null }),
    });
    state.conversationId = result.conversation_id;
    // 출처를 모델명 문자열로 추측하지 않는다. 서버가 answer_source 로 못박아 준다.
    const SOURCE_LABEL = {
      openai:          { text: 'AI 응답',            cls: 'src-ai' },
      rule_based:      { text: '규칙 기반 대체 응답', cls: 'src-fallback' },
      error_fallback:  { text: 'AI 호출 실패 → 대체', cls: 'src-error' },
      missing_package: { text: 'openai 미설치 → 대체', cls: 'src-error' },
    };
    const src = SOURCE_LABEL[result.answer_source] || SOURCE_LABEL.rule_based;
    const BASIS_LABEL = {
      decision: '판단 상태로 선별',
      keyword: '질문 낱말과 일치',
      top_score: '일치 없음 → 점수 상위',
    };
    appendMessage('assistant', result.reply,
      `근거 후보 ${result.candidates_used}건 · 요약 ${result.summary_used.count}건 · ` +
      `${BASIS_LABEL[result.selection_basis] || result.selection_basis} · ${result.model}`,
      src, result.candidate_refs);
    await loadConversations();
    $('conversationSelect').value = state.conversationId;
  } catch (err) {
    appendMessage('system', describeError(err));
  } finally {
    $('chatLoading').hidden = true;
    $('chatSend').disabled = false;
  }
}

async function loadConversations() {
  try {
    const rows = await api('/api/conversations');
    const select = $('conversationSelect');
    const current = select.value;
    select.innerHTML = '<option value="">새 대화</option>'
      + rows.map((c) => `<option value="${c.id}">${escapeHtml(c.title)} (${c.message_count})</option>`).join('');
    select.value = current;
  } catch (e) { /* 목록 실패가 채팅을 막지는 않는다 */ }
}

async function openConversation(id) {
  const log = $('chatLog');
  if (!id) {
    state.conversationId = '';
    log.innerHTML = '<div class="msg msg-system">새 대화입니다.</div>';
    return;
  }
  try {
    const conversation = await api(`/api/conversations/${id}`);
    state.conversationId = conversation.id;
    log.innerHTML = '';
    appendMessage('system', `불러온 대화: ${conversation.title}`);
    conversation.messages.forEach((m) => appendMessage(m.role, m.content, null, null, m.refs));
  } catch (err) {
    toast(describeError(err));
  }
}

async function deleteConversation() {
  const id = $('conversationSelect').value;
  if (!id) { toast('삭제할 대화를 먼저 선택하세요.'); return; }
  try {
    await api(`/api/conversations/${id}`, { method: 'DELETE' });
    toast('대화를 삭제했습니다.');
    state.conversationId = '';
    $('chatLog').innerHTML = '<div class="msg msg-system">새 대화입니다.</div>';
    await loadConversations();
  } catch (err) {
    toast(describeError(err));
  }
}

const SUGGESTIONS = [
  '오늘 제작할 후보 3개를 추천해줘',
  '최근 일주일 사이 가장 빠르게 올라오는 주제가 뭐야?',
  'loss_defense 채널에 맞는 MAKE 후보를 보여줘',
  '최근 연금 주제가 너무 많아지고 있지는 않아?',
];

// ── 초기화 ───────────────────────────────────────
function bindEvents() {
  $('candidateBody').addEventListener('click', (event) => {
    const deleteId = event.target.dataset.delete;
    if (deleteId) {
      event.stopPropagation();
      api(`/api/data/${deleteId}`, { method: 'DELETE' })
        .then(() => {
          toast('삭제했습니다.');
          if (state.selectedId === deleteId) state.selectedId = null;
          return Promise.all([loadCandidates(), loadSummary()]);
        })
        .then(renderSelected)
        .catch((err) => toast(describeError(err)));
      return;
    }
    const row = event.target.closest('tr[data-id]');
    if (row) selectCandidate(row.dataset.id);
  });

  $('selectedBox').addEventListener('click', (event) => {
    if (event.target.dataset.decision) setDecision(event.target.dataset.decision);
    if (event.target.id === 'btnHandoff') createHandoff();
    if (event.target.id === 'btnPersonaState') loadPersona(state.selectedId);
    if (event.target.id === 'btnPersonaDraft') makePersonaDraft(state.selectedId);
    if (event.target.id === 'btnPersonaApprove') approvePersona(state.selectedId);
  });

  $('filterChannel').addEventListener('change', (e) => {
    state.filters.channel = e.target.value;
    loadCandidates();
  });
  $('filterDecision').addEventListener('change', (e) => {
    state.filters.decision = e.target.value;
    loadCandidates();
  });

  $('btnImport').addEventListener('click', async (event) => {
    event.target.disabled = true;
    try {
      const result = await api('/api/data/import?source=sample&replace=true', { method: 'POST' });
      toast(result.ok ? `표본 ${result.imported}건을 적재했습니다.` : result.error);
      await Promise.all([loadCandidates(), loadSummary()]);
    } catch (err) {
      toast(describeError(err));
    } finally {
      event.target.disabled = false;
    }
  });

  $('btnAdd').addEventListener('click', () => { $('addForm').hidden = false; });
  $('btnAddCancel').addEventListener('click', () => { $('addForm').hidden = true; });

  $('addForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const payload = {
      date: new Date(form.get('date')).toISOString(),
      value: Number(form.get('value')),
      memo: form.get('memo') || '',
      title: form.get('title') || null,
      topic: form.get('topic') || null,
      channel: form.get('channel') || null,
      source: 'manual',
    };
    try {
      await api('/api/data', { method: 'POST', body: JSON.stringify(payload) });
      toast('후보를 추가했습니다.');
      event.target.reset();
      $('addForm').hidden = true;
      await Promise.all([loadCandidates(), loadSummary()]);
    } catch (err) {
      toast(describeError(err));
    }
  });

  $('btnExport').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(state.candidates, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `radar-candidates-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
  });

  $('chatLog').addEventListener('click', (event) => {
    const target = event.target.closest('[data-ref-id]');
    if (target) jumpToCandidate(target.dataset.refId);
  });

  $('chatForm').addEventListener('submit', (event) => {
    event.preventDefault();
    const question = $('chatInput').value.trim();
    if (question) sendChat(question);
  });

  $('conversationSelect').addEventListener('change', (e) => openConversation(e.target.value));
  $('btnDeleteConv').addEventListener('click', deleteConversation);
  $('btnRefreshHandoff').addEventListener('click', loadHandoffs);

  $('suggestions').innerHTML = SUGGESTIONS
    .map((s) => `<button type="button">${escapeHtml(s)}</button>`).join('');
  $('suggestions').addEventListener('click', (event) => {
    if (event.target.tagName === 'BUTTON') sendChat(event.target.textContent);
  });

  $('settingsToggle').addEventListener('click', () => {
    const panel = $('settingsPanel');
    panel.hidden = !panel.hidden;
    $('apiBaseInput').value = apiBase();
  });
  $('apiBaseSave').addEventListener('click', () => {
    const value = $('apiBaseInput').value.trim();
    try { localStorage.setItem(API_KEY_LS, value); } catch (e) { /* 저장 불가여도 진행 */ }
    toast('API 주소를 저장했습니다. 다시 불러옵니다.');
    $('settingsPanel').hidden = true;
    init();
  });

  $('themeToggle').addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('rda_theme', next); } catch (e) { /* 무시 */ }
  });
}

async function init() {
  await loadHealth();
  await Promise.all([loadCandidates(), loadSummary(), loadConversations(), loadHandoffs()]);
  renderSelected();
}

document.addEventListener('DOMContentLoaded', () => {
  try {
    const theme = localStorage.getItem('rda_theme');
    if (theme) document.documentElement.dataset.theme = theme;
  } catch (e) { /* 무시 */ }
  bindEvents();
  init();
});
