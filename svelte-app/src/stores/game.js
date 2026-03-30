/**
 * Core game state store.
 *
 * All playback state lives here. Components subscribe to derived stores
 * and automatically re-render when the playback position changes.
 */

import { writable, derived, get } from 'svelte/store';

// ── Raw game data (loaded once) ──
export const gameData = writable(null);

// ── Playback state ──
export const currentIdx = writable(-1);
export const isPlaying = writable(false);
export const speedIdx = writable(2);
export const clerkOpen = writable(true);
export const activeTab = writable('replay');

export const SPEEDS = [0.25, 0.5, 1, 2.5, 5, 25];

// ── Derived: filtered events (skip noise) ──
export const visibleEvents = derived(gameData, $data => {
  if (!$data) return [];
  return $data.events.filter(e => {
    if (e.type === 'tool_call' && e.tool === 'bash') {
      const cmd = e.command || '';
      return cmd.includes('player_cli.py') || cmd.includes('clerk_cli.py');
    }
    if (e.type === 'text' && e.content === 'Prompt is too long') return false;
    return true;
  });
});

// ── Derived: events visible up to current playback position ──
export const eventsUpToCurrent = derived(
  currentIdx,
  ($idx) => {
    const $events = get(visibleEvents);
    return $events.slice(0, $idx + 1);
  }
);

// ── Derived: current event ──
export const currentEvent = derived(
  currentIdx,
  ($idx) => {
    const $events = get(visibleEvents);
    return $idx >= 0 ? $events[$idx] : null;
  }
);

// ── Derived: per-agent event feeds ──
function buildAgentEvents(allEvents, agentName) {
  const events = [];
  for (const evt of allEvents) {
    // Events this agent produced (including received_message)
    if (evt.source === agentName) {
      events.push(evt);
    }
  }
  return events;
}

export const agentFeeds = derived(
  eventsUpToCurrent,
  ($events) => {
    const $data = get(gameData);
    if (!$data) return {};
    const feeds = {};
    for (const p of $data.players) {
      feeds[p.name] = buildAgentEvents($events, p.name);
    }
    feeds['clerk'] = buildAgentEvents($events, 'clerk');
    return feeds;
  }
);

// ── Derived: public chat (broadcasts only) ──
export const publicChatEvents = derived(
  eventsUpToCurrent,
  $events => $events.filter(e => e.type === 'message' && e.is_broadcast)
);

// ── Derived: active agent status ──
// Each agent's status is based on their last event up to currentIdx.
// If their last event is 'idle' (turn_duration), they're idle.
// Otherwise they're active with the type of their last event.
export const agentStatuses = derived(
  eventsUpToCurrent,
  ($events) => {
    const $data = get(gameData);
    if (!$data) return {};
    const statuses = {};
    const allAgents = [...$data.players.map(p => p.name), 'clerk'];
    for (const name of allAgents) {
      statuses[name] = 'idle';
    }

    // Scan backward to find each agent's last event
    const found = new Set();
    for (let i = $events.length - 1; i >= 0 && found.size < allAgents.length; i--) {
      const evt = $events[i];
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
  }
);

// ── Derived: file state reconstruction ──
function reconstructFile(initialContent, events) {
  let content = initialContent;
  let lastEdit = null;
  for (const evt of events) {
    if (evt.type === 'file_read') {
      if (!evt.offset || evt.offset <= 0) {
        // Full read (or negative offset = tail read that includes start)
        content = evt.content;
      } else {
        // Partial read — splice at the given absolute line offset
        const offset0 = evt.offset - 1; // 1-indexed to 0-indexed
        const existingLines = content.split('\n');
        const newLines = evt.content.split('\n');
        const before = existingLines.slice(0, offset0);
        // Pad with empty lines if offset is beyond our content
        while (before.length < offset0) before.push('');
        const after = evt.limit
          ? existingLines.slice(offset0 + newLines.length)
          : []; // no limit = replace to end
        content = [...before, ...newLines, ...after].join('\n');
      }
    } else if (evt.type === 'file_edit') {
      if (evt.is_error) continue;
      if (evt.tool === 'Edit' && evt.old_string && evt.new_string) {
        let idx = content.indexOf(evt.old_string);
        if (idx === -1) {
          // old_string not found — likely a side-channel write (e.g. roll_dice)
          // appended content we don't have. The old_string IS the ground truth
          // of what the file contained at this point, so use it to patch.
          // Find the longest matching prefix of old_string at the end of content.
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
            // No prefix overlap — the old_string is entirely new appended content.
            // The edit succeeded on the real file, so old_string follows our content.
            // Append old_string, then the edit will replace it with new_string.
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

function fileState(filename) {
  return derived(
    eventsUpToCurrent,
    ($events) => {
      const $data = get(gameData);
      const initial = $data?.initial_files?.[filename] || '';
      const fileEvents = $events.filter(e =>
        (e.type === 'file_read' || e.type === 'file_edit') && e.filename === filename
      );
      return reconstructFile(initial, fileEvents);
    }
  );
}

export const currentRules = fileState('game_rules.md');
export const currentGameLog = fileState('game_log.md');

// ── Derived: current scores from game_state.yaml rounds ──
export const currentScores = derived(
  currentIdx,
  ($idx) => {
    const $data = get(gameData);
    const $events = get(visibleEvents);
    if (!$data?.rounds?.length) return { scores: {}, round: 0, result: null, winner: null };
    if ($idx < 0) return { scores: {}, round: 0, result: null, winner: null };

    const currentTs = $events[$idx]?.timestamp || '';

    // Find the latest round whose timestamp <= current playback timestamp
    let latestRound = null;
    for (const r of $data.rounds) {
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
  }
);

// ── Playback actions ──
let playTimer = null;

export function advanceTo(targetIdx) {
  const events = get(visibleEvents);
  if (targetIdx < 0 || targetIdx >= events.length) return;
  currentIdx.set(targetIdx);
}

export function stepForward() {
  const idx = get(currentIdx);
  const events = get(visibleEvents);
  if (idx < events.length - 1) {
    currentIdx.set(idx + 1);
  }
}

export function stepBack() {
  const idx = get(currentIdx);
  if (idx > 0) {
    currentIdx.set(idx - 1);
  }
}

export function jumpForward() {
  const idx = get(currentIdx);
  const events = get(visibleEvents);
  advanceTo(Math.min(idx + 30, events.length - 1));
}

export function jumpBack() {
  advanceTo(Math.max(get(currentIdx) - 30, 0));
}

export function togglePlay() {
  const playing = get(isPlaying);
  if (playing) {
    isPlaying.set(false);
    clearTimeout(playTimer);
  } else {
    // If at start (-1), step to first event before playing
    if (get(currentIdx) < 0) {
      currentIdx.set(0);
    }
    isPlaying.set(true);
    scheduleNext();
  }
}

function scheduleNext() {
  if (!get(isPlaying)) return;
  const idx = get(currentIdx);
  const events = get(visibleEvents);

  if (idx >= events.length - 1) {
    isPlaying.set(false);
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

  delay /= SPEEDS[get(speedIdx)];

  playTimer = setTimeout(() => {
    stepForward();
    scheduleNext();
  }, delay);
}

export function seekTo(pct) {
  const events = get(visibleEvents);
  const targetIdx = Math.floor(pct * events.length);
  advanceTo(Math.max(0, Math.min(targetIdx, events.length - 1)));
}

export function speedUp() {
  speedIdx.update(i => Math.min(i + 1, SPEEDS.length - 1));
}

export function speedDown() {
  speedIdx.update(i => Math.max(i - 1, 0));
}

// ── Load game data ──
export async function loadGame(path) {
  const resp = await fetch(path);
  const data = await resp.json();
  gameData.set(data);

  // Optional: jump to a specific event via URL param ?start=N
  const params = new URLSearchParams(window.location.search);
  const startAt = parseInt(params.get('start')) || 0;
  if (startAt > 0) {
    setTimeout(() => {
      const events = get(visibleEvents);
      advanceTo(Math.min(startAt - 1, events.length - 1));
    }, 0);
  }
}
