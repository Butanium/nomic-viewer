# Nomic Viewer TODOs

## Parser issues by game

### Games 0-4: No broadcasts
Games 0-4 have 0 broadcast messages (SendMessage with `to="*"`). The team messaging pattern changed between game-4 and game-5. The public chat panel will be empty for these games. All messages go to `team-lead` (clerk) instead.

**Workaround needed:** Treat `to="team-lead"` messages as public for games 0-4, or show them in the public chat with a different label.

### Games 0-4: No initial_files for game_rules.md
The clerk used Grep (not Read) to read `game_rules.md` in games 0-5 because Read was denied by hooks. The parser only captures Read results. `game_rules.md` initial content is missing for these games.

**Workaround:** Manually extract initial rules content from Grep results, or update parser to handle Grep reads.

### Game-5: initial_files content issue
Game-5's `initial_files` may have incorrect content for `game_rules.md` (captured from Grep not Read). Needs verification.

## Feature TODOs

- [ ] Score tracking: extract scores from Edit events on game_log.md (parse cumulative score lines)
- [ ] Winner detection: identify who won from transcript events
- [ ] Key moments: manually annotatable highlights
- [ ] Live update support: poll for new events during an active game
