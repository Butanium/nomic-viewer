# Nomic Game Replay Viewer

Web-based replay viewer for AI Nomic games where Claude models negotiate, strategize, and self-modify rules.

## Architecture

**Svelte + Vite** single-page app. No router — one page with tabs (Replay, Scores, Rules).

### Data flow
```
transcript.jsonl files (per game)
  → parse_transcripts.py (Python, in parent dir)
  → public/data/game-N.json (static JSON)
  → loaded by stores/game.js at runtime
  → reactive Svelte stores drive all components
```

### Key design decision: transcript-only parsing
The parser reads ONLY the Claude Code `.jsonl` transcript files. No parsing of `game_log.md`, `game_rules.md`, or any other game files. No regex heuristics. All game events (messages, tool calls, file edits, thinking) are extracted from structured JSONL event data.

### Stores (`src/stores/game.js`)
All state lives here. Components never manage playback state locally.

- `gameData` — raw loaded JSON (set once)
- `currentIdx` — playback position (the one number that drives everything)
- `visibleEvents` — derived: filtered events (removes bash noise, synthetic errors)
- `eventsUpToCurrent` — derived: `events.slice(0, currentIdx + 1)`
- `agentFeeds` — derived: per-agent event lists including incoming messages
- `publicChatEvents` — derived: broadcast messages only
- `agentStatuses` — derived: who's active/idle based on current event

Changing `currentIdx` automatically recomputes all derived stores → all components re-render. No manual DOM manipulation. Rewind/seek just sets the index.

### Components
- `App.svelte` — layout shell: topbar, scoreboard, tabs, clerk panel
- `PublicChat.svelte` — left panel, broadcast messages
- `AgentPanel.svelte` — one player's column (events + incoming messages)
- `ChatMessage.svelte` — renders a message (sent/received/public variants)
- `AgentEvent.svelte` — renders non-message events (thinking, text, tool calls, notes, file edits)
- `PlaybackBar.svelte` — play/pause, seek, speed controls, keyboard shortcuts

### Layout
```
┌─ topbar (game title, tabs, clerk toggle) ──────────────────┐
├─ scoreboard ───────────────────────────────────────────────┤
│ Public Chat │ Agent 1    │ Agent 2    │ Agent 3   │ Clerk  │
│ (broadcasts)│ (all events│ (all events│ (all evts)│ (panel)│
│             │ + incoming)│ + incoming)│           │        │
├─ playback bar (controls, seek, speed) ─────────────────────┤
└────────────────────────────────────────────────────────────┘
```
Clerk panel is a fixed-position right sidebar, open by default. Toggling it pushes all other elements left via `margin-right`.

## Development

```bash
cd svelte-app
npm install
npx vite --port 8111       # dev server with HMR
npx vite build              # production build → dist/
```

### Adding a new game
```bash
cd ..  # parent nomic-viewer dir
python parse_transcripts.py /path/to/game-N svelte-app/public/data/game-N.json
```
Then load with `?game=data/game-N.json` URL param.

### Debug: start position
URL param `?start=500` jumps to event 500 on load. `?start=0` starts from beginning.

## Conventions

- **Transcript data is the sole source of truth.** Do not parse game_log.md or game_rules.md.
- **Agent colors:** Opus = `--opus` (gold), Sonnet = `--sonnet` (blue), Haiku = `--haiku` (green), Clerk = `--clerk` (purple).
- **Message display:** Sent messages right-aligned with right border. Received messages left-aligned with left border. Public chat messages never truncated. Agent panel messages truncated at 200 chars with click-to-expand.
- **Playback speed** is content-based: delay scales with word count per event type, not timestamp gaps.
- Keyboard shortcuts: Space/K = play/pause, Arrow keys/J/L = step, +/= = cycle speed.

## Deploy

GitHub Pages via `.github/workflows/deploy.yml`. Builds svelte-app and deploys `dist/` with game data from `public/data/`.
