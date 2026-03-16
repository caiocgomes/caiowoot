export function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

export function normalizeTimestamp(dateStr) {
  if (/[+-]\d{2}:\d{2}$/.test(dateStr) || dateStr.endsWith("Z")) return dateStr;
  return dateStr.replace(" ", "T") + "Z";
}

export function formatTime(dateStr) {
  const date = new Date(normalizeTimestamp(dateStr));
  const tz = "America/Sao_Paulo";

  const todayStr = new Date().toLocaleDateString("pt-BR", { timeZone: tz });
  const dateStr2 = date.toLocaleDateString("pt-BR", { timeZone: tz });
  const isToday = todayStr === dateStr2;

  if (isToday) {
    return date.toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: tz,
    });
  }
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    timeZone: tz,
  });
}

export function formatTimeShort(dateStr) {
  const date = new Date(normalizeTimestamp(dateStr));
  return date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Sao_Paulo",
  });
}

export function formatDateSeparator(dateStr) {
  const date = new Date(normalizeTimestamp(dateStr));
  const tz = "America/Sao_Paulo";
  const todayStr = new Date().toLocaleDateString("pt-BR", { timeZone: tz });
  const dateStr2 = date.toLocaleDateString("pt-BR", { timeZone: tz });
  if (todayStr === dateStr2) return "Hoje";
  return date.toLocaleDateString("pt-BR", {
    day: "numeric",
    month: "long",
    timeZone: tz,
  });
}

export function isMobile() {
  return window.innerWidth < 768;
}

export function autoResize(el) {
  var maxH = isMobile() ? window.innerHeight * 0.4 : 500;
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, maxH) + "px";
}
