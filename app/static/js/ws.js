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

export function connectWS() {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) return;
  if (state.ws) { try { state.ws.close(); } catch(e) {} }

  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  state.ws = new WebSocket(`${protocol}//${location.host}/ws`);

  state.ws.onopen = () => {
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
    state.ws.close();
  };

  state.ws.onclose = () => {
    clearInterval(state.wsPingInterval);
    setTimeout(connectWS, 2000);
  };
}
