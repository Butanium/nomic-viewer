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
export const speedIdx = writable(1);
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
  [visibleEvents, currentIdx],
  ([$events, $idx]) => $events.slice(0, $idx + 1)
);

// ── Derived: current event ──
export const currentEvent = derived(
  [visibleEvents, currentIdx],
  ([$events, $idx]) => $idx >= 0 ? $events[$idx] : null
);

// ── Derived: per-agent event feeds ──
function buildAgentEvents(allEvents, agentName) {
  const events = [];
  for (const evt of allEvents) {
    // Events this agent produced
    if (evt.source === agentName) {
      events.push(evt);
      continue;
    }
    // Incoming messages to this agent
    if (evt.type === 'message') {
      if (evt.is_broadcast && evt.source !== agentName) {
        events.push({ ...evt, _incoming: true });
      } else if (evt.to === agentName) {
        events.push({ ...evt, _incoming: true });
      }
    }
  }
  return events;
}

export const agentFeeds = derived(
  [gameData, eventsUpToCurrent],
  ([$data, $events]) => {
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
export const agentStatuses = derived(
  [gameData, currentEvent],
  ([$data, $evt]) => {
    if (!$data) return {};
    const statuses = {};
    for (const p of $data.players) {
      statuses[p.name] = 'idle';
    }
    statuses['clerk'] = 'idle';

    if ($evt) {
      let status = 'active';
      if ($evt.type === 'thinking') status = 'thinking...';
      else if ($evt.type === 'message') status = 'messaging';
      else if ($evt.type === 'tool_call') status = $evt.tool;
      else if ($evt.type === 'file_edit') status = 'editing';
      statuses[$evt.source] = status;
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
      if (!evt.offset && !evt.limit) {
        // Full read — replace entire content
        content = evt.content;
      } else {
        // Partial read — splice into existing content at the given line offset
        const offset = (evt.offset || 1) - 1; // convert 1-indexed to 0-indexed
        const existingLines = content.split('\n');
        const newLines = evt.content.split('\n');
        // Replace lines from offset, extending if needed
        const before = existingLines.slice(0, offset);
        const after = evt.limit ? existingLines.slice(offset + newLines.length) : [];
        content = [...before, ...newLines, ...after].join('\n');
      }
    } else if (evt.type === 'file_edit') {
      if (evt.is_error) continue;
      if (evt.tool === 'Edit' && evt.old_string && evt.new_string) {
        const idx = content.indexOf(evt.old_string);
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
    [gameData, eventsUpToCurrent],
    ([$data, $events]) => {
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

  // Start at event 500 for debugging (or from URL param)
  const params = new URLSearchParams(window.location.search);
  const startAt = parseInt(params.get('start')) || 500;
  // Wait a tick for derived stores to update
  setTimeout(() => {
    if (startAt > 0) {
      const events = get(visibleEvents);
      advanceTo(Math.min(startAt - 1, events.length - 1));
    }
  }, 0);
}
