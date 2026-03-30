# Nomic Viewer TODOs

## Done
- [x] Score tracking (from game_state.yaml with timestamps)
- [x] Winner detection (from game_state.yaml)
- [x] Rules tab (live reconstruction from transcript edits)
- [x] Game log tab (live reconstruction from transcript edits)
- [x] Multi-game index page with game cards
- [x] Compaction event markers
- [x] Human (supervisor) messages in agent panels
- [x] Received message timing (delivery timestamp, not send timestamp)
- [x] Svelte 5 runes migration
- [x] Broadcast vs DM detection for received messages
- [x] Multi-agent active status (from turn_duration idle signals)
- [x] Autoscroll only when at bottom
- [x] Post-mortem skill auto-publishes to viewer
- [x] OG image / link previews

## Parser issues (legacy games)

### Games 0-4: No broadcasts
Games 0-4 have 0 broadcast messages (used `to="team-lead"` instead of `to="*"`).
Public chat is empty for these games. Fixed in parser for new format but old
games still have empty public chat.

### Games 0-4: No initial_files for game_rules.md
Clerk used Grep (not Read) to read game_rules.md. Parser only captures Read
results. Rules tab won't work for these games.

## Feature TODOs

### High priority
- [ ] Interactive tutorial — introduction to Nomic rules + UI walkthrough
- [ ] Click on game log entry → jump to that time in playback
- [ ] Strategy notes viewer — player private notes as a dedicated view
- [ ] Phase indicator — current phase (proposal/debate/voting) + whose turn
- [ ] Highlighted moments in progress bar — key events marked on timeline

### Medium priority
- [ ] Post-mortem tab — interview files and group discussion
- [ ] Rules in sidebar — view current rules without switching tabs

### Low priority
- [ ] Theme personalization per game (from game_state.yaml)
- [ ] Clerk tools: spotlight on player, "game comment" tool for highlighted annotations
- [ ] Live update support — poll for new events during active game
- [ ] Deceptiveness scoring hook (haiku subagent at each turn)
- [ ] Scroll-to-bottom button in panels when user has scrolled up
