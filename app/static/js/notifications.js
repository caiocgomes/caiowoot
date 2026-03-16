import state from './state.js';

// openConversation will be set by main.js to avoid circular imports
let _openConversation = null;
export function setOpenConversation(fn) {
  _openConversation = fn;
}

export function playNotificationSound() {
  const now = Date.now();
  if (now - state.lastSoundTime < 3000) return;
  state.lastSoundTime = now;
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 880;
    osc.type = "sine";
    gain.gain.value = 0.15;
    osc.start();
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
    osc.stop(ctx.currentTime + 0.3);
  } catch (e) { /* silent fail */ }
}

export function updateTitleBadge() {
  document.title = state.unreadCount > 0 ? `(${state.unreadCount}) ${state.originalTitle}` : state.originalTitle;
}

export function notifyInbound(conversationId, messageContent) {
  const isHidden = document.visibilityState === "hidden";
  const isDifferentConversation = conversationId !== state.currentConversationId;

  if (!isHidden && !isDifferentConversation) return;

  state.unreadCount++;
  updateTitleBadge();
  playNotificationSound();

  if (isHidden && Notification.permission === "granted") {
    const name = state.conversationNames.get(conversationId) || "Nova mensagem";
    const body = messageContent ? messageContent.substring(0, 100) : "";
    const n = new Notification(name, { body, tag: String(conversationId), renotify: true });
    n.onclick = () => {
      window.focus();
      if (_openConversation) _openConversation(conversationId);
      n.close();
    };
  }
}

export function initNotificationButton() {
  const btn = document.getElementById("notif-btn");
  if (!btn) return;
  if (!("Notification" in window)) { btn.style.display = "none"; return; }
  if (Notification.permission === "granted") { btn.style.display = "none"; return; }
  if (Notification.permission === "denied") { btn.textContent = "Notificações bloqueadas"; btn.disabled = true; btn.style.opacity = "0.5"; return; }
  btn.style.display = "inline-block";
  btn.onclick = async () => {
    const perm = await Notification.requestPermission();
    if (perm === "granted") { btn.style.display = "none"; }
    else if (perm === "denied") { btn.textContent = "Notificações bloqueadas"; btn.disabled = true; btn.style.opacity = "0.5"; }
  };
}
