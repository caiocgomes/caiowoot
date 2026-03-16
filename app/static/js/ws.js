import state from './state.js';

const handlers = {};

export function on(eventType, handler) {
  if (!handlers[eventType]) handlers[eventType] = [];
  handlers[eventType].push(handler);
}

function dispatch(data) {
  const typeHandlers = handlers[data.type] || [];
  for (const h of typeHandlers) h(data);
  // Also call 'all' handlers
  const allHandlers = handlers['*'] || [];
  for (const h of allHandlers) h(data);
}

function updateWsStatus(connected) {
  let dot = document.getElementById('ws-status-dot');
  if (!dot) {
    dot = document.createElement('span');
    dot.id = 'ws-status-dot';
    const header = document.getElementById('sidebar-header');
    if (header) header.insertBefore(dot, header.firstChild);
  }
  dot.className = connected ? 'ws-dot connected' : 'ws-dot disconnected';
}

export function connectWS() {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) return;
  if (state.ws) { try { state.ws.close(); } catch(e) {} }

  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  state.ws = new WebSocket(`${protocol}//${location.host}/ws`);

  state.ws.onopen = () => {
    updateWsStatus(true);
    clearInterval(state.wsPingInterval);
    state.wsPingInterval = setInterval(() => {
      if (state.ws.readyState === WebSocket.OPEN) {
        state.ws.send("ping");
      }
    }, 30000);
  };

  state.ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    dispatch(data);
  };

  state.ws.onerror = () => {
    updateWsStatus(false);
    state.ws.close();
  };

  state.ws.onclose = () => {
    updateWsStatus(false);
    clearInterval(state.wsPingInterval);
    setTimeout(connectWS, 2000);
  };
}
