import { showToast } from './toast.js';

let coldItems = [];

export async function startColdRewarm() {
  const modal = document.getElementById('cold-rewarm-modal');
  const loading = document.getElementById('cold-rewarm-modal-loading');
  const body = document.getElementById('cold-rewarm-modal-body');
  const footer = document.getElementById('cold-rewarm-modal-footer');
  const empty = document.getElementById('cold-rewarm-modal-empty');

  modal.hidden = false;
  loading.hidden = false;
  body.hidden = true;
  footer.hidden = true;
  empty.hidden = true;

  try {
    const resp = await fetch('/cold-rewarm/preview', { method: 'POST' });
    if (!resp.ok) throw new Error(`preview failed ${resp.status}`);
    const items = await resp.json();
    coldItems = items;
    renderColdModal(items);
  } catch (err) {
    console.error('cold preview error', err);
    showToast('Erro ao gerar triagem cold', 'error');
    closeColdRewarmModal();
  } finally {
    loading.hidden = true;
  }
}

export function closeColdRewarmModal() {
  const modal = document.getElementById('cold-rewarm-modal');
  modal.hidden = true;
  coldItems = [];
  document.getElementById('cold-rewarm-send-list').innerHTML = '';
  document.getElementById('cold-rewarm-skip-list').innerHTML = '';
}

function renderColdModal(items) {
  const body = document.getElementById('cold-rewarm-modal-body');
  const footer = document.getElementById('cold-rewarm-modal-footer');
  const empty = document.getElementById('cold-rewarm-modal-empty');
  const sendList = document.getElementById('cold-rewarm-send-list');
  const skipList = document.getElementById('cold-rewarm-skip-list');

  if (!items || items.length === 0) {
    empty.hidden = false;
    body.hidden = true;
    footer.hidden = true;
    return;
  }

  const sends = items.filter(i => i.action !== 'skip');
  const skips = items.filter(i => i.action === 'skip');

  sendList.innerHTML = '';
  for (const item of sends) {
    const card = document.createElement('div');
    card.className = 'rewarm-card cold-card';
    card.dataset.itemId = item.item_id;
    card.dataset.dispatchId = item.dispatch_id;

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

    const chips = document.createElement('div');
    chips.className = 'cold-chips';
    const classChip = document.createElement('span');
    classChip.className = `cold-chip cold-chip-${item.classification}`;
    classChip.textContent = item.classification;
    const confChip = document.createElement('span');
    confChip.className = `cold-chip cold-chip-conf-${item.confidence}`;
    confChip.textContent = `conf: ${item.confidence}`;
    const actionChip = document.createElement('span');
    actionChip.className = `cold-chip cold-chip-action-${item.action}`;
    actionChip.textContent = `ação: ${item.action}`;
    const daysChip = document.createElement('span');
    daysChip.className = 'cold-chip cold-chip-days';
    daysChip.textContent = `${Math.round(item.days_cold)}d frio`;
    chips.append(classChip, confChip, actionChip, daysChip);

    if (item.quote_from_lead) {
      const quote = document.createElement('div');
      quote.className = 'cold-quote';
      quote.textContent = `"${item.quote_from_lead}"`;
      card.appendChild(header);
      card.appendChild(chips);
      card.appendChild(quote);
    } else {
      card.appendChild(header);
      card.appendChild(chips);
    }

    const textarea = document.createElement('textarea');
    textarea.className = 'rewarm-card-textarea';
    textarea.value = item.message || '';
    textarea.rows = 5;

    const actions = document.createElement('div');
    actions.className = 'rewarm-card-actions';
    const remove = document.createElement('button');
    remove.className = 'rewarm-card-remove';
    remove.textContent = 'Remover';
    remove.onclick = () => removeColdItem(item.item_id);
    actions.appendChild(remove);

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
      const reason = item.classification === 'negativo_explicito'
        ? 'negativo explicito'
        : `${item.classification} (${item.confidence})`;
      row.innerHTML = `<span class="rewarm-skip-name">${escapeHtml(item.contact_name || '(sem nome)')}</span><span class="rewarm-skip-reason">${escapeHtml(reason)}</span>`;
      skipList.appendChild(row);
    }
  }

  updateColdCount(sends.length);
  body.hidden = false;
  footer.hidden = false;
  empty.hidden = true;
}

function removeColdItem(itemId) {
  coldItems = coldItems.filter(i => i.item_id !== itemId);
  const card = document.querySelector(`#cold-rewarm-send-list .rewarm-card[data-item-id="${itemId}"]`);
  if (card) card.remove();
  const remainingSends = coldItems.filter(i => i.action !== 'skip').length;
  updateColdCount(remainingSends);
  if (remainingSends === 0) {
    document.getElementById('cold-rewarm-modal-footer').hidden = true;
  }
}

function updateColdCount(n) {
  document.getElementById('cold-rewarm-modal-count').textContent = `${n} conversa${n === 1 ? '' : 's'} a enviar`;
}

export async function sendColdBatch() {
  const cards = document.querySelectorAll('#cold-rewarm-send-list .rewarm-card');
  const items = [];
  for (const card of cards) {
    const itemId = card.dataset.itemId;
    const dispatchId = parseInt(card.dataset.dispatchId, 10);
    const original = coldItems.find(i => i.item_id === itemId);
    if (!original) continue;
    const text = card.querySelector('.rewarm-card-textarea').value.trim();
    if (!text) continue;
    items.push({
      dispatch_id: dispatchId,
      conversation_id: original.conversation_id,
      message: text,
    });
  }

  if (items.length === 0) {
    showToast('Nenhuma mensagem válida para enviar', 'warning');
    return;
  }

  const sendBtn = document.getElementById('cold-rewarm-send-all-btn');
  sendBtn.disabled = true;
  sendBtn.textContent = 'Enviando…';

  try {
    const resp = await fetch('/cold-rewarm/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items }),
    });
    if (resp.status !== 202) throw new Error(`execute failed ${resp.status}`);
    showToast(`${items.length} cold rewarm enfileirado(s). Envios vão sair com intervalo de ~1 min.`, 'success');
    closeColdRewarmModal();
  } catch (err) {
    console.error('cold execute error', err);
    showToast('Erro ao disparar cold rewarm', 'error');
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
