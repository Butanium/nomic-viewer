/**
 * Core game state store.
 *
 * All playback state lives here as Svelte 5 runes ($state / $derived).
 * Mutable state is in the `game` object. Derived values are exported
 * as getter functions (Svelte 5 requires this for .svelte.js modules).
 */

// ── Mutable state ──
export const game = $state({
  data: null,
  currentIdx: -1,
  isPlaying: false,
  speedIdx: 2,
  clerkOpen: true,
  activeTab: 'replay',
});

export const SPEEDS = [0.25, 0.5, 1, 2.5, 5, 25];

// ── Derived values (not exported directly — use getter functions) ──
const _visibleEvents = $derived.by(() => {
  if (!game.data) return [];
  return game.data.events.filter(e => {
    if (e.type === 'tool_call' && e.tool === 'bash') {
      const cmd = e.command || '';
      return cmd.includes('player_cli.py') || cmd.includes('clerk_cli.py');
    }
    if (e.type === 'text' && e.content === 'Prompt is too long') return false;
    return true;
  });
});
export function visibleEvents() { return _visibleEvents; }

const _eventsUpToCurrent = $derived.by(() => {
  return _visibleEvents.slice(0, game.currentIdx + 1);
});
export function eventsUpToCurrent() { return _eventsUpToCurrent; }

const _currentEvent = $derived(game.currentIdx >= 0 ? _visibleEvents[game.currentIdx] : null);
export function currentEvent() { return _currentEvent; }

// ── Derived: per-agent event feeds ──
function buildAgentEvents(allEvents, agentName) {
  const events = [];
  for (const evt of allEvents) {
    // Events this agent produced (including received_message)
    if (evt.source === agentName) {
      events.push(evt);
      continue;
    }
    // Supervisor messages addressed to this agent
    if (evt.source === 'supervisor' && evt.to === agentName) {
      events.push({ ...evt, _incoming: true });
    }
  }
  return events;
}

const _agentFeeds = $derived.by(() => {
  if (!game.data) return {};
  const feeds = {};
  for (const p of game.data.players) {
    feeds[p.name] = buildAgentEvents(_eventsUpToCurrent, p.name);
  }
  feeds['clerk'] = buildAgentEvents(_eventsUpToCurrent, 'clerk');
  return feeds;
});
export function agentFeeds() { return _agentFeeds; }

const _publicChatEvents = $derived(
  _eventsUpToCurrent.filter(e => e.type === 'message' && e.is_broadcast)
);
export function publicChatEvents() { return _publicChatEvents; }

// ── Derived: active agent status ──
const _agentStatuses = $derived.by(() => {
  if (!game.data) return {};
  const statuses = {};
  const allAgents = [...game.data.players.map(p => p.name), 'clerk'];
  for (const name of allAgents) {
    statuses[name] = 'idle';
  }

  const found = new Set();
  for (let i = _eventsUpToCurrent.length - 1; i >= 0 && found.size < allAgents.length; i--) {
    const evt = _eventsUpToCurrent[i];
    if (found.has(evt.source)) continue;
    if (!allAgents.includes(evt.source)) continue;
    found.add(evt.source);

    if (evt.type === 'idle') {
      statuses[evt.source] = 'idle';
    } else {
      let status = 'active';
      if (evt.type === 'thinking') status = 'thinking...';
      else if (evt.type === 'message') status = 'messaging';
      else if (evt.type === 'tool_call') status = evt.tool;
      else if (evt.type === 'file_edit') status = 'editing';
      else if (evt.type === 'compaction') status = 'resuming';
      statuses[evt.source] = status;
    }
  }
  return statuses;
});
export function agentStatuses() { return _agentStatuses; }

// ── Derived: file state reconstruction ──
function reconstructFile(initialContent, events) {
  let content = initialContent;
  let lastEdit = null;
  for (const evt of events) {
    if (evt.type === 'file_read') {
      if (!evt.offset || evt.offset <= 0) {
        content = evt.content;
      } else {
        const offset0 = evt.offset - 1;
        const existingLines = content.split('\n');
        const newLines = evt.content.split('\n');
        const before = existingLines.slice(0, offset0);
        while (before.length < offset0) before.push('');
        const after = evt.limit
          ? existingLines.slice(offset0 + newLines.length)
          : [];
        content = [...before, ...newLines, ...after].join('\n');
      }
    } else if (evt.type === 'file_edit') {
      if (evt.is_error) continue;
      if (evt.tool === 'Edit' && evt.old_string && evt.new_string) {
        let idx = content.indexOf(evt.old_string);
        if (idx === -1) {
          const lines = content.split('\n');
          const oldLines = evt.old_string.split('\n');
          for (let matchLen = Math.min(lines.length, oldLines.length); matchLen > 0; matchLen--) {
            const tail = lines.slice(-matchLen).join('\n');
            const head = oldLines.slice(0, matchLen).join('\n');
            if (tail === head) {
              const missing = oldLines.slice(matchLen).join('\n');
              content = content + '\n' + missing;
              idx = content.indexOf(evt.old_string);
              break;
            }
          }
          if (idx === -1) {
            content = content + '\n' + evt.old_string;
            idx = content.indexOf(evt.old_string);
          }
        }
        if (idx !== -1) {
          content = content.slice(0, idx) + evt.new_string + content.slice(idx + evt.old_string.length);
          lastEdit = evt;
        }
      } else if (evt.tool === 'Write' && evt.content) {
        content = evt.content;
        lastEdit = evt;
      }
    }
  }
  return { content, lastEdit };
}

const _currentRules = $derived.by(() => {
  const initial = game.data?.initial_files?.['game_rules.md'] || '';
  const fileEvents = _eventsUpToCurrent.filter(e =>
    (e.type === 'file_read' || e.type === 'file_edit') && e.filename === 'game_rules.md'
  );
  return reconstructFile(initial, fileEvents);
});
export function currentRules() { return _currentRules; }

const _currentGameLog = $derived.by(() => {
  const initial = game.data?.initial_files?.['game_log.md'] || '';
  const fileEvents = _eventsUpToCurrent.filter(e =>
    (e.type === 'file_read' || e.type === 'file_edit') && e.filename === 'game_log.md'
  );
  return reconstructFile(initial, fileEvents);
});
export function currentGameLog() { return _currentGameLog; }

// ── Derived: current scores from game_state.yaml rounds ──
const _currentScores = $derived.by(() => {
  if (!game.data?.rounds?.length) return { scores: {}, round: 0, result: null, winner: null };
  if (game.currentIdx < 0) return { scores: {}, round: 0, result: null, winner: null };

  const currentTs = _visibleEvents[game.currentIdx]?.timestamp || '';

  let latestRound = null;
  for (const r of game.data.rounds) {
    if (r.timestamp && r.timestamp <= currentTs) {
      latestRound = r;
    }
  }

  if (!latestRound) return { scores: {}, round: 0, result: null, winner: null };

  return {
    scores: latestRound.scores || {},
    round: latestRound.round,
    result: latestRound.result,
    winner: latestRound.winner || null,
  };
});
export function currentScores() { return _currentScores; }

// ── Playback actions ──
let playTimer = null;

export function advanceTo(targetIdx) {
  if (targetIdx < 0 || targetIdx >= _visibleEvents.length) return;
  game.currentIdx = targetIdx;
}

export function stepForward() {
  if (game.currentIdx < _visibleEvents.length - 1) {
    game.currentIdx = game.currentIdx + 1;
  }
}

export function stepBack() {
  if (game.currentIdx > 0) {
    game.currentIdx = game.currentIdx - 1;
  }
}

export function jumpForward() {
  advanceTo(Math.min(game.currentIdx + 30, _visibleEvents.length - 1));
}

export function jumpBack() {
  advanceTo(Math.max(game.currentIdx - 30, 0));
}

export function togglePlay() {
  if (game.isPlaying) {
    game.isPlaying = false;
    clearTimeout(playTimer);
  } else {
    if (game.currentIdx < 0) {
      game.currentIdx = 0;
    }
    game.isPlaying = true;
    scheduleNext();
  }
}

function scheduleNext() {
  if (!game.isPlaying) return;
  const idx = game.currentIdx;
  const events = _visibleEvents;

  if (idx >= events.length - 1) {
    game.isPlaying = false;
    return;
  }

  const current = events[idx];
  const content = current.content || '';
  const wordCount = content.split(/\s+/).filter(Boolean).length;

  let delay;
  if (current.type === 'message') {
    delay = Math.max(1000, Math.min(5000, wordCount * 60));
  } else if (current.type === 'thinking') {
    delay = Math.max(500, Math.min(4000, wordCount * 40));
  } else if (current.type === 'text') {
    delay = Math.max(500, Math.min(3000, wordCount * 50));
  } else {
    delay = 400;
  }

  delay /= SPEEDS[game.speedIdx];

  playTimer = setTimeout(() => {
    stepForward();
    scheduleNext();
  }, delay);
}

export function seekTo(pct) {
  const targetIdx = Math.floor(pct * _visibleEvents.length);
  advanceTo(Math.max(0, Math.min(targetIdx, _visibleEvents.length - 1)));
}

export function speedUp() {
  game.speedIdx = Math.min(game.speedIdx + 1, SPEEDS.length - 1);
}

export function speedDown() {
  game.speedIdx = Math.max(game.speedIdx - 1, 0);
}

export function resetGame() {
  game.data = null;
  game.currentIdx = -1;
}

// ── Load game data ──
export async function loadGame(path) {
  const resp = await fetch(path);
  const data = await resp.json();
  game.data = data;

  const params = new URLSearchParams(window.location.search);
  const startAt = parseInt(params.get('start')) || 0;
  if (startAt > 0) {
    setTimeout(() => {
      advanceTo(Math.min(startAt - 1, _visibleEvents.length - 1));
    }, 0);
  }
}
