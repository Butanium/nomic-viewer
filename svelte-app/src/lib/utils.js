/** Shared utility functions for rendering and formatting. */

const MODEL_COLORS = {
  opus: 'var(--opus)',
  sonnet: 'var(--sonnet)',
  haiku: 'var(--haiku)',
};

export function agentColor(gameData, name) {
  if (!gameData) return 'var(--text-dim)';
  if (name === 'clerk') return 'var(--clerk)';
  const player = gameData.players.find(p => p.name === name);
  return player ? (MODEL_COLORS[player.model] || 'var(--text-dim)') : 'var(--text-dim)';
}

export function agentModel(gameData, name) {
  if (!gameData) return '';
  if (name === 'clerk') return gameData.clerk?.model || '';
  const player = gameData.players.find(p => p.name === name);
  return player?.model || '';
}

export function shortTime(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toUTCString().slice(17, 22); // HH:MM
}

export function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

export function renderMarkdown(text) {
  let html = escapeHtml(text);
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/`(.+?)`/g, '<code style="background:var(--bg);padding:1px 3px;border-radius:2px;font-size:0.9em">$1</code>');
  html = html.replace(/\n/g, '<br>');
  return html;
}
