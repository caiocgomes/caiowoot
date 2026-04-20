import { showToast } from './toast.js';

let rewarmItems = [];
let currentReferenceDate = null;

const WEEKDAY_PT = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado'];
const MONTH_PT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];


function _fmtDateShort(iso) {
  // iso = "YYYY-MM-DD" → "17/04 (sexta-feira)"
  if (!iso) return '';
  const [y, m, d] = iso.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  const dow = WEEKDAY_PT[dt.getUTCDay()];
  const dd = String(d).padStart(2, '0');
  const mm = MONTH_PT[m - 1];
  return `${dd}/${mm} (${dow})`;
}


function _yesterdayIso() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}


export async function startRewarmLeads() {
  // Fetch suggested date to populate modal, then show date chooser.
  const modal = document.getElementById('rewarm-date-modal');
  let suggested = null;
  try {
    const resp = await fetch('/rewarm/suggested-date');
    if (resp.ok) suggested = await resp.json();
  } catch (err) {
    console.warn('suggested-date fetch failed, using client fallback', err);
  }

  const yesterdayIso = _yesterdayIso();
  const yesterdaySub = document.getElementById('rewarm-date-yesterday-sub');
  yesterdaySub.textContent = _fmtDateShort(yesterdayIso);

  const suggestedRow = document.getElementById('rewarm-date-suggested-row');
  const suggestedMain = document.getElementById('rewarm-date-suggested-main');
  const suggestedSub = document.getElementById('rewarm-date-suggested-sub');

  if (suggested && suggested.date && suggested.date !== yesterdayIso) {
    suggestedMain.textContent = (suggested.label || '').charAt(0).toUpperCase() + (suggested.label || '').slice(1);
    suggestedSub.textContent = _fmtDateShort(suggested.date);
    suggestedRow.dataset.iso = suggested.date;
    suggestedRow.hidden = false;
    // Marcar sugestão como default quando diferente de ontem (caso típico: segunda-feira)
    const suggestedRadio = suggestedRow.querySelector('input[type=radio]');
    suggestedRadio.checked = true;
  } else {
    suggestedRow.hidden = true;
    const yesterdayRadio = document.querySelector('input[name=rewarm-date-choice][value=yesterday]');
    yesterdayRadio.checked = true;
  }

  const customInput = document.getElementById('rewarm-date-custom-input');
  customInput.value = yesterdayIso;
  // Permitir clique no input de data selecionar o radio custom automaticamente.
  customInput.onfocus = () => {
    document.querySelector('input[name=rewarm-date-choice][value=custom]').checked = true;
  };
  customInput.onchange = () => {
    document.querySelector('input[name=rewarm-date-choice][value=custom]').checked = true;
  };

  modal.hidden = false;
}


export function closeRewarmDateModal() {
  document.getElementById('rewarm-date-modal').hidden = true;
}


export async function confirmRewarmDate() {
  const choice = document.querySelector('input[name=rewarm-date-choice]:checked');
  if (!choice) return;
  let referenceDate;
  if (choice.value === 'yesterday') {
    referenceDate = _yesterdayIso();
  } else if (choice.value === 'suggested') {
    referenceDate = document.getElementById('rewarm-date-suggested-row').dataset.iso;
  } else {
    referenceDate = document.getElementById('rewarm-date-custom-input').value;
  }
  if (!referenceDate) {
    showToast('Escolha uma data válida', 'warning');
    return;
  }
  closeRewarmDateModal();
  await _openRewarmPreview(referenceDate);
}


async function _openRewarmPreview(referenceDate) {
  currentReferenceDate = referenceDate;
  const modal = document.getElementById('rewarm-modal');
  const loading = document.getElementById('rewarm-modal-loading');
  const body = document.getElementById('rewarm-modal-body');
  const footer = document.getElementById('rewarm-modal-footer');
  const empty = document.getElementById('rewarm-modal-empty');
  const reference = document.getElementById('rewarm-modal-reference');

  modal.hidden = false;
  loading.hidden = false;
  body.hidden = true;
  footer.hidden = true;
  empty.hidden = true;
  reference.hidden = false;
  reference.textContent = `Referência: ${_fmtDateShort(referenceDate)}`;

  try {
    const resp = await fetch('/rewarm/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reference_date: referenceDate }),
    });
    if (!resp.ok) throw new Error(`preview failed ${resp.status}`);
    const payload = await resp.json();
    const items = Array.isArray(payload) ? payload : (payload.items || []);
    rewarmItems = items;
    renderRewarmModal(items);
  } catch (err) {
    console.error('rewarm preview error', err);
    showToast('Erro ao gerar sugestões de reesquentamento', 'error');
    closeRewarmModal();
  } finally {
    loading.hidden = true;
  }
}


// Compat alias: alguns callers antigos ainda referenciam startRewarmD1.
export async function startRewarmD1() {
  return startRewarmLeads();
}


export function closeRewarmModal() {
  const modal = document.getElementById('rewarm-modal');
  modal.hidden = true;
  rewarmItems = [];
  currentReferenceDate = null;
  document.getElementById('rewarm-send-list').innerHTML = '';
  document.getElementById('rewarm-skip-list').innerHTML = '';
  const reference = document.getElementById('rewarm-modal-reference');
  if (reference) {
    reference.hidden = true;
    reference.textContent = '';
  }
}

function renderRewarmModal(items) {
  const body = document.getElementById('rewarm-modal-body');
  const footer = document.getElementById('rewarm-modal-footer');
  const empty = document.getElementById('rewarm-modal-empty');
  const sendList = document.getElementById('rewarm-send-list');
  const skipList = document.getElementById('rewarm-skip-list');

  if (!items || items.length === 0) {
    empty.hidden = false;
    body.hidden = true;
    footer.hidden = true;
    return;
  }

  const sends = items.filter(i => i.action === 'send');
  const skips = items.filter(i => i.action === 'skip');

  sendList.innerHTML = '';
  for (const item of sends) {
    const card = document.createElement('div');
    card.className = 'rewarm-card';
    card.dataset.itemId = item.item_id;

    const header = document.createElement('div');
    header.className = 'rewarm-card-header';
    const name = document.createElement('div');
    name.className = 'rewarm-card-name';
    name.textContent = `${item.contact_name || '(sem nome)'} · ${item.phone_number}`;
    const stage = document.createElement('span');
    stage.className = 'rewarm-card-stage';
    stage.textContent = item.funnel_stage;
    header.appendChild(name);
    header.appendChild(stage);

    const reason = document.createElement('div');
    reason.className = 'rewarm-card-reason';
    reason.textContent = item.reason || '';

    const textarea = document.createElement('textarea');
    textarea.className = 'rewarm-card-textarea';
    textarea.value = item.message || '';
    textarea.rows = 4;

    const actions = document.createElement('div');
    actions.className = 'rewarm-card-actions';
    const remove = document.createElement('button');
    remove.className = 'rewarm-card-remove';
    remove.textContent = 'Remover';
    remove.onclick = () => removeRewarmItem(item.item_id);
    actions.appendChild(remove);

    card.appendChild(header);
    card.appendChild(reason);
    card.appendChild(textarea);
    card.appendChild(actions);
    sendList.appendChild(card);
  }

  skipList.innerHTML = '';
  if (skips.length > 0) {
    const title = document.createElement('div');
    title.className = 'rewarm-skip-title';
    title.textContent = `Pulados (${skips.length})`;
    skipList.appendChild(title);
    for (const item of skips) {
      const row = document.createElement('div');
      row.className = 'rewarm-skip-row';
      row.innerHTML = `<span class="rewarm-skip-name">${escapeHtml(item.contact_name || '(sem nome)')}</span><span class="rewarm-skip-reason">${escapeHtml(item.reason || '')}</span>`;
      skipList.appendChild(row);
    }
  }

  updateCount(sends.length);
  body.hidden = false;
  footer.hidden = false;
  empty.hidden = true;
}

function removeRewarmItem(itemId) {
  rewarmItems = rewarmItems.filter(i => i.item_id !== itemId);
  const card = document.querySelector(`.rewarm-card[data-item-id="${itemId}"]`);
  if (card) card.remove();
  const remainingSends = rewarmItems.filter(i => i.action === 'send').length;
  updateCount(remainingSends);
  if (remainingSends === 0) {
    document.getElementById('rewarm-modal-footer').hidden = true;
  }
}

function updateCount(n) {
  document.getElementById('rewarm-modal-count').textContent = `${n} conversa${n === 1 ? '' : 's'} a enviar`;
}

export async function sendRewarmBatch() {
  // Collect current textarea values for each send item
  const cards = document.querySelectorAll('#rewarm-send-list .rewarm-card');
  const items = [];
  for (const card of cards) {
    const itemId = card.dataset.itemId;
    const original = rewarmItems.find(i => i.item_id === itemId);
    if (!original) continue;
    const text = card.querySelector('.rewarm-card-textarea').value.trim();
    if (!text) continue;
    items.push({ conversation_id: original.conversation_id, message: text });
  }

  if (items.length === 0) {
    showToast('Nenhuma mensagem válida para enviar', 'warning');
    return;
  }

  const sendBtn = document.getElementById('rewarm-send-all-btn');
  sendBtn.disabled = true;
  sendBtn.textContent = 'Enviando…';

  try {
    const resp = await fetch('/rewarm/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items }),
    });
    if (resp.status !== 202) throw new Error(`execute failed ${resp.status}`);
    showToast(`${items.length} mensagem(ns) enfileirada(s). Envios vão sair com intervalo de ~1 min.`, 'success');
    closeRewarmModal();
  } catch (err) {
    console.error('rewarm execute error', err);
    showToast('Erro ao disparar envios', 'error');
    sendBtn.disabled = false;
    sendBtn.textContent = 'Enviar todos';
  }
}

function escapeHtml(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}
