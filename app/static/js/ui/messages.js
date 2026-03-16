import state from '../state.js';
import { normalizeTimestamp, formatTimeShort, formatDateSeparator } from '../utils.js';

export function appendMessage(msg) {
  const messagesEl = document.getElementById("messages");

  // Date separator
  if (msg.created_at) {
    const msgDate = new Date(normalizeTimestamp(msg.created_at)).toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" });
    if (msgDate !== state.lastMessageDate) {
      const sep = document.createElement("div");
      sep.className = "date-separator";
      sep.innerHTML = `<span>${formatDateSeparator(msg.created_at)}</span>`;
      messagesEl.appendChild(sep);
      state.lastMessageDate = msgDate;
    }
  }

  const div = document.createElement("div");
  div.className = `msg ${msg.direction}` + (msg.sent_by === "bot" ? " bot" : "");
  div.textContent = msg.content;
  if (msg.media_type) {
    const badge = document.createElement("div");
    badge.style.cssText = "font-size:11px;color:#888;margin-top:4px;";
    badge.textContent = `[${msg.media_type === "image" ? "Imagem" : "Documento"} anexado]`;
    div.appendChild(badge);
  }
  if (msg.created_at) {
    const timeEl = document.createElement("span");
    timeEl.className = "msg-time";
    timeEl.textContent = formatTimeShort(msg.created_at);
    div.appendChild(timeEl);
  }
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}
