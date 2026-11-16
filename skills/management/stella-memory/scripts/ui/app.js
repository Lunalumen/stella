'use strict';
// Stella Memory local UI. All memory text is untrusted: rendered with textContent only, never as HTML.

const TOKEN = document.querySelector('meta[name="stella-token"]').content;
const KIND_LABEL = { preference: '선호', constraint: '조건', decision: '결정', open_question: '미해결 질문' };
const STATUS_LABEL = { active: '사용 중', conflict: '충돌 후보', superseded: '대체됨', retired: '보관 중지', deleted: '삭제됨' };
const NAME_RE = /^[a-z0-9][a-z0-9._-]{0,63}$/;
const state = { info: null, project: null, selected: null, searchOffset: 0, searchQuery: '', searchHistory: [], importDraft: null };

// ---------- helpers ----------
function el(tag, props, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}
const $ = (id) => document.getElementById(id);
function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); return node; }
function badge(status) { return el('span', { class: 'badge st-' + status, text: STATUS_LABEL[status] || status }); }
function short(id) { return id ? id.slice(0, 8) : ''; }
function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } return null; }

async function api(name, body) {
  const res = await fetch('/api/' + name, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Stella-Token': TOKEN },
    body: JSON.stringify(body || {}),
  });
  let data;
  try { data = await res.json(); } catch (e) { data = { error: '응답을 읽지 못했습니다 (HTTP ' + res.status + ')' }; }
  if (!res.ok || data.error) throw new Error(data.error || ('HTTP ' + res.status));
  return data;
}
function withProject(body) { return Object.assign({ project: state.project }, body || {}); }

function showResult(kind, title, lines) {
  const box = clear($('result'));
  box.className = 'result ' + kind;
  box.append(el('strong', { text: title }));
  for (const l of [].concat(lines || [])) box.append(el('div', { text: l }));
  box.append(el('button', { type: 'button', class: 'ghost close', text: '닫기', onclick: () => box.classList.add('hidden') }));
  clearTimeout(showResult.timer);
  if (kind === 'ok') showResult.timer = setTimeout(() => box.classList.add('hidden'), 6000);  // errors stay until closed
}
const ok = (title, lines) => showResult('ok', title, lines);
const fail = (err, what) => showResult('err', (what || '작업') + ' 실패', [String(err.message || err)]);

function modal(title, bodyNodes, okLabel, { danger = false, requireCheck = null } = {}) {
  return new Promise((resolve) => {
    $('modal-title').textContent = title;
    const body = clear($('modal-body'));
    body.append(...[].concat(bodyNodes));
    const okBtn = $('modal-ok');
    okBtn.textContent = okLabel;
    okBtn.className = danger ? 'danger' : '';
    let check = null;
    if (requireCheck) {
      check = el('input', { type: 'checkbox', id: 'modal-check' });
      body.append(el('label', { class: 'check' }, check, ' ' + requireCheck));
      okBtn.disabled = true;
      check.addEventListener('change', () => { okBtn.disabled = !check.checked; });
    } else okBtn.disabled = false;
    $('modal').classList.remove('hidden');
    const done = (v) => { $('modal').classList.add('hidden'); okBtn.onclick = null; $('modal-cancel').onclick = null; resolve(v); };
    okBtn.onclick = () => done(true);
    $('modal-cancel').onclick = () => done(false);
  });
}

function needProject() {
  if (!state.project) { fail(new Error('먼저 프로젝트를 선택하거나 새 프로젝트 이름을 입력하세요.'), '프로젝트'); return false; }
  return true;
}

// ---------- context: DB + project ----------
async function loadInfo() {
  const info = await api('info');
  state.info = info;
  $('db-path').textContent = info.db;
  const st = $('db-state');
  st.textContent = info.db_exists_now ? (info.db_existed_at_start ? '기존 DB' : '이번 실행에서 생성됨') : '아직 파일 없음';
  st.className = 'badge ' + (info.db_exists_now ? 'on' : 'off');
  $('ai-state').title = info.ai_connection.note;
  const kind = clear($('add-kind'));
  for (const k of info.kinds) kind.append(el('option', { value: k, text: KIND_LABEL[k] + ' (' + k + ')' }));
  fillProjects(info.projects);
}

function fillProjects(projects) {
  const sel = clear($('project-select'));
  const saved = store('stella.project');
  const names = Array.from(new Set(projects.concat(state.project && !projects.includes(state.project) ? [state.project] : [])));
  if (!names.length) sel.append(el('option', { value: '', text: '(저장된 프로젝트 없음)' }));
  for (const p of names) sel.append(el('option', { value: p, text: p }));
  const pick = state.project && names.includes(state.project) ? state.project : (saved && names.includes(saved) ? saved : names[0] || null);
  if (pick) sel.value = pick;
  setProject(pick, false);
}

function setProject(name, remember = true) {
  state.project = name || null;
  state.selected = null;
  state.searchQuery = ''; state.searchOffset = 0; state.importDraft = null;
  clear($('search-items')); clear($('search-summary')); clear($('import-result')); clear($('export-result'));
  $('search-next').classList.add('hidden'); $('search-prev').classList.add('hidden');
  if (remember && name) store('stella.project', name);
  const banner = clear($('project-banner'));
  if (state.project) banner.append('현재 프로젝트: ', el('strong', { text: state.project }), ' · 모든 조회와 변경은 이 프로젝트 안에서만 일어납니다.');
  else banner.append('프로젝트가 선택되지 않았습니다. 위에서 새 프로젝트 이름을 입력하고 "사용"을 누르세요.');
  banner.className = 'banner' + (state.project ? '' : ' warn');
  renderDetail(null);
  refreshAll();
}

$('project-select').addEventListener('change', (e) => setProject(e.target.value));
$('project-use').addEventListener('click', () => {
  const name = $('project-new').value.trim();
  if (!NAME_RE.test(name)) { fail(new Error('프로젝트 이름은 영문 소문자·숫자로 시작하고 소문자·숫자·. _ - 만 쓸 수 있습니다 (최대 64자).'), '프로젝트'); return; }
  $('project-new').value = '';
  const sel = $('project-select');
  if (![...sel.options].some((o) => o.value === name)) {
    if (sel.options.length === 1 && !sel.options[0].value) clear(sel);
    sel.append(el('option', { value: name, text: name + ' (새 프로젝트, 첫 저장 전)' }));
  }
  sel.value = name;
  setProject(name);
});

// ---------- tabs ----------
let currentTab = 'list';
for (const btn of document.querySelectorAll('.tabs button')) {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
}
function switchTab(tab) {
  currentTab = tab;
  for (const b of document.querySelectorAll('.tabs button')) b.classList.toggle('active', b.dataset.tab === tab);
  for (const v of document.querySelectorAll('.view')) v.classList.toggle('hidden', v.id !== 'view-' + tab);
  if (tab === 'list') loadList();
  if (tab === 'conflicts') loadConflicts();
  if (tab === 'audit') loadAudit();
}

function refreshAll() {
  if (!state.project) { clear($('list-items')); $('list-summary').textContent = ''; $('conflict-count').textContent = ''; return; }
  loadList();
  loadConflictCount();
  if (currentTab === 'conflicts') loadConflicts();
  if (currentTab === 'audit') loadAudit();
  if (state.searchQuery) runSearch(state.searchQuery, state.searchOffset);  // never leave stale search results on screen
  refreshDbState();
}

async function refreshDbState() {
  try {
    const info = await api('info');
    const st = $('db-state');
    st.textContent = info.db_exists_now ? (info.db_existed_at_start ? '기존 DB' : '이번 실행에서 생성됨') : '아직 파일 없음';
    st.className = 'badge ' + (info.db_exists_now ? 'on' : 'off');
  } catch (e) { /* the failing call reports its own error */ }
}

// After a change, reload the open detail so it never shows a stale status.
function refreshAfterChange(memoryId) {
  refreshAll();
  const id = memoryId || state.selected;
  if (id) openDetail(id, true);
}

// ---------- list ----------
function memoryItem(m, onPick) {
  return el('li', { class: 'item' + (state.selected === m.memory_id ? ' sel' : ''), tabindex: '0',
    onclick: () => onPick(m.memory_id), onkeydown: (e) => { if (e.key === 'Enter') onPick(m.memory_id); } },
    el('div', { class: 'item-head' }, badge(m.status), el('span', { class: 'kind', text: KIND_LABEL[m.kind] || m.kind }),
      el('code', { text: m.key }), m.truncated ? el('span', { class: 'badge warn', text: '본문 일부만' }) : null),
    el('div', { class: 'item-text', text: m.text }),
    el('div', { class: 'item-meta muted', text: 'r' + m.rev + ' · ' + (m.updated || '') + ' · ' + short(m.memory_id) }));
}

async function loadList() {
  if (!state.project) return;
  try {
    const data = await api('list', withProject({ include_all: $('list-all').checked }));
    const ul = clear($('list-items'));
    $('list-summary').textContent = '이 프로젝트의 기억 ' + data.count + '건' + ($('list-all').checked ? ' (대체됨·보관 중지 포함)' : ' (사용 중·충돌 후보만)');
    if (!data.count) ul.append(el('li', { class: 'muted', text: '표시할 기억이 없습니다.' }));
    for (const m of data.memories) ul.append(memoryItem(m, openDetail));
  } catch (e) { fail(e, '목록 불러오기'); }
}
$('list-all').addEventListener('change', loadList);
$('list-refresh').addEventListener('click', () => { refreshAll(); });

// ---------- search ----------
$('search-form').addEventListener('submit', (e) => { e.preventDefault(); state.searchHistory = []; runSearch($('search-q').value, 0); });
$('search-next').addEventListener('click', () => { state.searchHistory.push(state.searchOffset); runSearch(state.searchQuery, state.nextOffset); });
$('search-prev').addEventListener('click', () => runSearch(state.searchQuery, state.searchHistory.pop() || 0));

async function runSearch(q, offset) {
  if (!needProject()) return;
  try {
    const r = await api('search', withProject({ query: q, offset, include_global: $('search-global').checked }));
    state.searchQuery = q; state.searchOffset = offset; state.nextOffset = r.next_offset;
    const sum = clear($('search-summary'));
    const from = r.returned ? offset + 1 : 0;
    sum.append(el('div', { class: 'row' }, el('strong', { text: '일치 ' + r.total_matched + '건 중 ' + (r.returned ? from + '–' + (offset + r.returned) : '0') + '번째 표시' }),
      el('span', { class: 'muted small', text: ' 응답 ' + r.response_chars + ' / ' + r.budget.max_response_chars + '자' })));
    if (r.partial) sum.append(el('div', { class: 'banner warn', text: '부분 결과입니다. ' + (r.omitted_count ? '이 페이지 뒤에 ' + r.omitted_count + '건이 더 있습니다. ' : '') + (offset ? '앞쪽 ' + offset + '건은 이전 페이지에 있습니다. ' : '') + (r.results.some((x) => x.truncated) ? '일부 본문이 예산 때문에 잘렸습니다.' : '') }));
    if (r.conflict_count) sum.append(el('div', { class: 'banner danger', text: '미해결 충돌 그룹 ' + r.conflict_count + '개가 검색 결과와 관련되어 있습니다. "충돌" 탭에서 확인하세요.' }));
    if (!r.omitted_ids_complete || !r.conflicts_complete) sum.append(el('div', { class: 'muted small', text: '응답 크기 제한 때문에 일부 목록 정보가 줄어 있습니다. 개수는 정확합니다.' }));
    const ul = clear($('search-items'));
    if (!r.returned) ul.append(el('li', { class: 'muted', text: '일치하는 기억이 없습니다. (키워드 검색이므로 다른 표현으로도 찾아보세요)' }));
    for (const m of r.results) ul.append(memoryItem(m, openDetail));
    $('search-next').classList.toggle('hidden', r.next_offset === null);
    $('search-prev').classList.toggle('hidden', offset === 0);
  } catch (e) { fail(e, '검색'); }
}

// ---------- detail ----------
async function openDetail(id, quiet) {
  try {
    const m = await api('show', withProject({ memory_id: id }));
    state.selected = id;
    renderDetail(m);
  } catch (e) {
    if (quiet) { state.selected = null; renderDetail(null); } else fail(e, '상세 보기');
  }
}

function field(label, value, cls) { return el('div', { class: 'field' }, el('span', { class: 'label', text: label }), el('span', { class: cls || '', text: value })); }

function renderDetail(m) {
  const box = clear($('detail'));
  $('detail-empty').classList.toggle('hidden', !!m);
  box.classList.toggle('hidden', !m);
  if (!m) return;
  box.append(el('div', { class: 'detail-head' }, badge(m.status), el('span', { class: 'kind', text: KIND_LABEL[m.kind] }), el('code', { text: m.key }),
    m.key_provisional ? el('span', { class: 'badge warn', text: '임시 키·미분류' }) : null));
  box.append(el('div', { class: 'detail-text', text: m.text }));
  box.append(field('ID', m.memory_id, 'mono'), field('프로젝트', m.project), field('현재 개정', 'r' + m.rev),
    field('처음 저장', m.created), field('최근 개정', m.updated), field('저장 실행자', m.actor), field('요청자 표시', m.requested_by + ' (승인 증명 아님)'),
    field('출처 메모', m.source_note || '(없음)'), field('출처 확인', m.source_verified ? '확인됨' : '미확인'));
  if (m.conflict_id) box.append(el('div', { class: 'banner danger' }, '미해결 충돌 그룹에 속해 있습니다. ', el('button', { type: 'button', class: 'link', text: '충돌 보기', onclick: () => switchTab('conflicts') })));

  const actions = el('div', { class: 'row actions' });
  if (m.status === 'active' || m.status === 'conflict') {
    actions.append(el('button', { type: 'button', text: '수정', onclick: () => renderEdit(m) }));
    actions.append(el('button', { type: 'button', class: 'ghost', text: '보관 중지', onclick: () => doRetire(m) }));
  }
  actions.append(el('button', { type: 'button', class: 'danger', text: '삭제', onclick: () => doDelete(m) }));
  box.append(actions);
  box.append(el('details', { class: 'explain' }, el('summary', { text: '보관 중지와 삭제의 차이' }),
    el('p', { text: '보관 중지: 기억과 개정 이력이 그대로 남고, 기본 검색과 새 내보내기에서만 빠집니다. 같은 내용을 다시 저장할 때 재활성화할 수 있습니다.' }),
    el('p', { text: '삭제: 본문과 모든 개정 이력을 저장소에서 지웁니다. 같은 ID의 재가져오기를 막는 기록과 원문 없는 작업 기록만 남습니다. 되돌릴 수 없고, 이미 내보낸 파일·DB 백업·디스크에 남은 사본은 지워지지 않습니다.' })));

  box.append(el('h3', { text: '개정 이력 (' + (m.revisions || []).length + ')' }));
  const hist = el('ol', { class: 'history' });
  for (const r of (m.revisions || []).slice().reverse()) {
    hist.append(el('li', {}, el('div', { class: 'item-meta muted', text: 'r' + r.rev + ' · ' + r.created + ' · ' + r.actor + (r.superseded_by ? ' · 대체: ' + r.superseded_by : '') }),
      el('div', { class: 'item-text', text: r.text }), r.source_note ? el('div', { class: 'muted small', text: '출처: ' + r.source_note }) : null));
  }
  box.append(hist);
}

function counter(input, out, max) {
  const upd = () => { const n = input.value.length; out.textContent = n + ' / ' + max + '자'; out.classList.toggle('over', n > max); };
  input.addEventListener('input', upd); upd();
  return () => input.value.length <= max;
}

function renderEdit(m) {
  const box = clear($('detail'));
  const kind = el('select', {}); for (const k of state.info.kinds) kind.append(el('option', { value: k, text: KIND_LABEL[k] }));
  kind.value = m.kind;
  const text = el('textarea', { rows: '5' }); text.value = m.text;
  const note = el('input', { autocomplete: 'off' }); note.value = '';
  const tc = el('span', { class: 'counter' }), nc = el('span', { class: 'counter' });
  const textOk = counter(text, tc, state.info.limits.text), noteOk = counter(note, nc, state.info.limits.source_note);
  const preview = el('div', { class: 'preview hidden' });
  box.append(el('h3', { text: '기억 수정 · r' + m.rev + ' 기준' }), el('p', { class: 'muted small', text: '저장할 때 다른 곳에서 먼저 바뀌었으면 덮어쓰지 않고 알려 드립니다.' }),
    el('label', {}, '종류 ', kind), el('label', {}, '내용 ', tc, text), el('label', {}, '이번 개정의 출처 메모 (선택) ', nc, note), preview,
    el('div', { class: 'row' }, el('button', { type: 'button', class: 'ghost', text: '취소', onclick: () => openDetail(m.memory_id) }),
      el('button', { type: 'button', text: '저장 전 미리보기', onclick: async () => {
        if (!textOk() || !noteOk()) { fail(new Error('글자 수 제한을 넘었습니다. 잘라내지 않으니 직접 줄여 주세요.'), '수정'); return; }
        const body = withProject({ memory_id: m.memory_id, expect_rev: m.rev, text: text.value, kind: kind.value !== m.kind ? kind.value : null, source_note: note.value });
        try {
          const r = await api('update', Object.assign({ dry_run: true }, body));
          clear(preview).classList.remove('hidden');
          if (r.status === 'stale_revision') { preview.append(el('div', { class: 'banner danger', text: '다른 변경이 먼저 저장되었습니다 (현재 r' + r.current_rev + '). 다시 열어 확인하세요.' })); return; }
          if (r.status === 'unchanged') { preview.append(el('div', { class: 'banner', text: '바뀐 내용이 없습니다. 저장하지 않습니다.' })); return; }
          preview.append(el('div', { class: 'label', text: '이전 (r' + m.rev + ')' }), el('div', { class: 'item-text old', text: r.previous_text }),
            el('div', { class: 'label', text: '저장될 내용 (r' + r.rev + ')' }), el('div', { class: 'item-text new', text: r.text }),
            kind.value !== m.kind ? el('div', { text: '종류: ' + KIND_LABEL[m.kind] + ' → ' + KIND_LABEL[kind.value] }) : null,
            el('button', { type: 'button', text: '이대로 저장', onclick: async () => {
              try {
                const s = await api('update', body);
                if (s.status === 'stale_revision') { fail(new Error('다른 변경이 먼저 저장되어 덮어쓰지 않았습니다 (현재 r' + s.current_rev + ').'), '수정'); return; }
                ok('수정 저장됨', ['r' + s.rev + ' · ' + short(s.memory_id)]);
                refreshAfterChange(m.memory_id);
              } catch (e) { fail(e, '수정'); }
            } }));
        } catch (e) { fail(e, '수정 미리보기'); }
      } })));
}

async function doRetire(m) {
  const go = await modal('보관 중지', [el('p', { text: '이 기억을 보관 중지합니다. 기록은 남고 기본 검색·새 내보내기에서만 빠집니다.' }), el('div', { class: 'item-text', text: m.text })], '보관 중지');
  if (!go) return;
  try { await api('retire', withProject({ memory_id: m.memory_id })); ok('보관 중지됨', [m.key + ' · ' + short(m.memory_id)]); refreshAfterChange(m.memory_id); }
  catch (e) { fail(e, '보관 중지'); }
}

async function doDelete(m) {
  const revs = (m.revisions || []).length;
  const body = [
    el('p', { text: '다음 기억을 삭제합니다. 되돌릴 수 없습니다.' }),
    field('프로젝트', m.project), field('키', m.key), field('ID', m.memory_id, 'mono'), field('지워지는 개정', revs + '개'),
    el('div', { class: 'item-text', text: m.text }),
    el('ul', { class: 'small' }, el('li', { text: '지워짐: 본문과 모든 개정 이력, 검색 대상' }),
      el('li', { text: '남음: 재가져오기 차단 기록(ID·시각), 원문 없는 작업 기록, 과거 충돌 이력의 "삭제됨" 표시' }),
      el('li', { text: '지워지지 않음: 이미 내보낸 파일, DB 백업, 디스크에 남은 이전 페이지' })),
  ];
  const go = await modal('기억 삭제', body, '영구 삭제', { danger: true, requireCheck: '삭제 대상과 범위를 확인했습니다' });
  if (!go) return;
  try {
    const r = await api('delete', withProject({ memory_id: m.memory_id, confirm: true }));
    ok('삭제됨', ['개정 ' + r.revisions_removed + '개 삭제 · ' + short(m.memory_id), '이전 내보내기·백업 사본은 지워지지 않았습니다.']);
    renderDetail(null); refreshAll();
  } catch (e) { fail(e, '삭제'); }
}

// ---------- add ----------
const addTextOk = counter($('add-text'), $('add-text-count'), 2000);
const addNoteOk = counter($('add-note'), $('add-note-count'), 500);
$('add-form').addEventListener('submit', async (e) => { e.preventDefault(); previewAdd(false); });

const ADD_STATUS = {
  created: '새 기억으로 저장됩니다.',
  conflict_candidate: '같은 키에 다른 내용이 있어 충돌 후보로 저장됩니다. 저장 뒤 "충돌" 탭에서 직접 고르세요.',
  unchanged: '같은 내용이 이미 있어 저장하지 않습니다.',
  retired_exists: '같은 내용이 보관 중지 상태로 있습니다. 재활성화할 수 있습니다.',
  reactivated: '보관 중지된 기억이 다시 사용 중으로 바뀝니다.',
  reactivated_conflict_candidate: '보관 중지된 기억이 다시 살아나며, 같은 키의 다른 내용과 충돌 후보가 됩니다.',
};

async function previewAdd(reactivate) {
  if (!needProject()) return;
  if (!addTextOk() || !addNoteOk()) { fail(new Error('글자 수 제한을 넘었습니다. 잘라내지 않으니 직접 줄여 주세요.'), '추가'); return; }
  const body = withProject({ text: $('add-text').value, kind: $('add-kind').value, key: $('add-key').value.trim() || null, source_note: $('add-note').value, reactivate });
  const box = clear($('add-preview'));
  try {
    const r = await api('add', Object.assign({ dry_run: true }, body));
    box.classList.remove('hidden');
    box.append(el('h3', { text: '저장 전 확인' }), field('프로젝트', state.project), field('종류', KIND_LABEL[body.kind]),
      field('키', body.key || r.key + ' (임시 키·미분류)'), el('div', { class: 'label', text: '저장될 내용 (앞뒤 공백만 정리, 대소문자·내부 공백 유지)' }),
      el('div', { class: 'item-text new', text: $('add-text').value.normalize('NFC').trim() }), field('출처 메모', body.source_note || '(없음)'),
      el('div', { class: 'banner' + (r.status === 'conflict_candidate' || r.status === 'reactivated_conflict_candidate' ? ' danger' : ''), text: ADD_STATUS[r.status] || r.status }));
    const row = el('div', { class: 'row' });
    if (r.status === 'retired_exists') row.append(el('button', { type: 'button', text: '재활성화 미리보기', onclick: () => previewAdd(true) }));
    else if (r.status !== 'unchanged') row.append(el('button', { type: 'button', text: '이대로 저장', onclick: () => saveAdd(body) }));
    row.append(el('button', { type: 'button', class: 'ghost', text: '고치기', onclick: () => box.classList.add('hidden') }));
    box.append(row);
  } catch (e) { fail(e, '저장 미리보기'); }
}

async function saveAdd(body) {
  try {
    const r = await api('add', body);
    ok('저장됨: ' + (ADD_STATUS[r.status] || r.status), [r.key + ' · ' + short(r.memory_id)]);
    $('add-text').value = ''; $('add-note').value = ''; $('add-key').value = '';
    $('add-text').dispatchEvent(new Event('input')); $('add-note').dispatchEvent(new Event('input'));
    clear($('add-preview')).classList.add('hidden');
    const info = await api('projects'); fillProjects(info.projects);
    refreshAfterChange(r.memory_id);
  } catch (e) { fail(e, '저장'); }
}

// ---------- conflicts ----------
async function loadConflictCount() {
  if (!state.project) return;
  try { const d = await api('conflicts', withProject()); $('conflict-count').textContent = d.count ? String(d.count) : ''; } catch (e) { /* shown elsewhere */ }
}

let conflictSeq = 0;
async function loadConflicts() {
  if (!state.project) return;
  const mine = ++conflictSeq;
  try {
    const d = await api('conflicts', withProject());
    if (mine !== conflictSeq) return;  // a newer load is in flight; avoid drawing twice
    const box = clear($('conflict-list'));
    $('conflict-count').textContent = d.count ? String(d.count) : '';
    if (!d.count) { box.append(el('p', { class: 'muted', text: '미해결 충돌이 없습니다.' })); return; }
    for (const c of d.conflicts) box.append(conflictCard(c));
  } catch (e) { fail(e, '충돌 불러오기'); }
}

function conflictCard(c) {
  const name = 'keep-' + c.conflict.conflict_id;
  const go = el('button', { type: 'button', text: '선택한 후보 유지', disabled: true });
  const card = el('div', { class: 'card' }, el('div', { class: 'item-head' }, el('strong', { text: '키 ' }), el('code', { text: c.conflict.key }),
    el('span', { class: 'muted small', text: ' 후보 ' + c.members.length + '개 · 그룹 ' + short(c.conflict.conflict_id) })));
  for (const m of c.members) {
    const radio = el('input', { type: 'radio', name, value: m.memory_id + ':' + m.rev, onchange: () => { go.disabled = false; } });
    card.append(el('label', { class: 'candidate' }, radio, el('div', {},
      el('div', { class: 'item-text', text: m.text === null ? '(삭제된 기억)' : m.text }),
      el('div', { class: 'item-meta muted', text: (STATUS_LABEL[m.status] || m.status) + ' · r' + m.rev + ' · 저장 ' + (m.updated || m.deleted_at || '') + ' · ' + short(m.memory_id) }))));
  }
  go.addEventListener('click', async () => {
    const chosen = card.querySelector('input[name="' + name + '"]:checked');
    if (!chosen) return;
    const keep = c.members.find((m) => chosen.value.startsWith(m.memory_id));
    const yes = await modal('충돌 해소', [el('p', { text: '다음 후보를 유지합니다. 나머지 후보는 "대체됨"으로 바뀌며 이력은 남습니다.' }), el('div', { class: 'item-text new', text: keep.text })], '이 후보 유지');
    if (!yes) return;
    try {
      const r = await api('resolve', withProject({ conflict_id: c.conflict.conflict_id, keep: chosen.value }));
      ok('충돌 해소됨', ['유지: ' + short(r.kept), '대체됨: ' + r.superseded.map(short).join(', ')]);
      refreshAfterChange();
    } catch (e) { fail(e, '충돌 해소'); }
  });
  card.append(el('div', { class: 'row' }, go));
  return card;
}

// ---------- import ----------
$('import-preview').addEventListener('click', async () => {
  if (!needProject()) return;
  const f = $('import-file').files[0];
  if (!f) { fail(new Error('JSONL 파일을 고르세요.'), '가져오기'); return; }
  if (f.size > 5000000) { fail(new Error('파일이 5 MB를 넘습니다.'), '가져오기'); return; }
  const content = await f.text();
  const box = clear($('import-result'));
  try {
    const r = await api('import', withProject({ content }));
    state.importDraft = { content, sha256: r.sha256, name: f.name };
    box.append(el('h3', { text: '미리보기: ' + f.name }), field('대상 프로젝트', state.project), field('적용 가능한 행', r.valid_rows + '개'), field('오류', r.errors.length + '개'));
    if (r.errors.length) {
      const ul = el('ul', { class: 'errors' });
      for (const er of r.errors) ul.append(el('li', { text: (er.line ? er.line + '행: ' : '') + er.error }));
      box.append(el('div', { class: 'banner danger', text: '오류가 있어 적용할 수 없습니다. 파일을 고친 뒤 다시 미리보기 하세요. (아무것도 저장되지 않았습니다)' }), ul);
      return;
    }
    if (!r.valid_rows) { box.append(el('div', { class: 'banner', text: '가져올 행이 없습니다.' })); return; }
    box.append(el('button', { type: 'button', text: r.valid_rows + '개 행 적용', onclick: applyImport }));
  } catch (e) { fail(e, '가져오기 미리보기'); }
});

async function applyImport() {
  const d = state.importDraft;
  if (!d) return;
  const yes = await modal('가져오기 적용', [el('p', { text: d.name + '의 내용을 프로젝트 ' + state.project + '에 적용합니다. 하나라도 실패하면 전체가 취소됩니다.' })], '적용');
  if (!yes) return;
  try {
    const r = await api('import', withProject({ content: d.content, apply: true, expect_sha256: d.sha256 }));
    if (r.status !== 'applied') { fail(new Error((r.errors[0] || {}).error || r.status), '가져오기 (변경 없음)'); return; }
    ok('가져오기 적용됨', [r.applied + '개 행 처리 · 출처는 모두 미확인으로 저장']);
    clear($('import-result')); state.importDraft = null;
    const info = await api('projects'); fillProjects(info.projects);
  } catch (e) { fail(e, '가져오기 적용'); }
}

// ---------- export ----------
$('export-run').addEventListener('click', async () => {
  if (!needProject()) return;
  try {
    const r = await api('export', withProject({ format: $('export-format').value, include_retired: $('export-retired').checked }));
    const blob = new Blob([r.content], { type: 'text/plain;charset=utf-8' });
    const a = el('a', { href: URL.createObjectURL(blob), download: r.filename, text: r.filename + ' 다시 받기' });
    clear($('export-result')).append(el('p', { text: r.count + '건을 내보냈습니다 (' + r.format + ').' }), a);
    a.click();
    ok('내보내기 완료', [r.count + '건 · ' + r.filename]);
  } catch (e) { fail(e, '내보내기'); }
});

// ---------- audit ----------
async function loadAudit() {
  if (!state.project) return;
  try {
    const d = await api('audit', withProject({ limit: 100 }));
    const ul = clear($('audit-items'));
    if (!d.entries.length) ul.append(el('li', { class: 'muted', text: '기록이 없습니다.' }));
    for (const a of d.entries) ul.append(el('li', { class: 'item-meta', text: a.at + ' · ' + a.op + ' · ' + (a.key || '-') + ' · ' + short(a.memory_id) + ' · ' + a.actor }));
  } catch (e) { fail(e, '작업 기록'); }
}

loadInfo().catch((e) => fail(e, '서버 연결'));
