"""Parse Nomic game data from game_log.md and transcript JSONL files.

Produces a structured JSON file suitable for the web viewer.
"""

import json
import re
import sys
from pathlib import Path


def parse_game_log(game_dir: Path) -> dict:
    """Parse game_log.md into structured round data."""
    log_path = game_dir / "game_log.md"
    text = log_path.read_text()

    rounds = []
    score_history = [{}]  # round 0 = initial scores
    current_round = None
    key_moments = []

    lines = text.split("\n")
    i = 0

    # Parse initial player info (multiple formats)
    players = []
    for line in lines:
        # "- **Joueurs** : A, B, C" or "**Players:** A, B, C"
        m = re.match(r"[-*]*\s*\*\*(Joueurs|Players):?\*\*\s*:?\s*(.+)", line)
        if m:
            player_names = [n.strip() for n in m.group(2).split(",")]
            for name in player_names:
                players.append({"name": name, "score": 0})
        # "- **Scores initiaux** : A=0, B=0" or "**Starting scores:** ..."
        m = re.match(r"[-*]*\s*\*\*(Scores?\s*initiaux|Starting\s*scores?):?\*\*\s*:?\s*(.+)", line, re.IGNORECASE)
        if m:
            for part in m.group(2).split(","):
                # "A=0" or "A 0" format
                name_val = re.match(r"\s*([\w-]+)\s*[=:]\s*(\d+)", part)
                if name_val:
                    for p in players:
                        if p["name"] == name_val.group(1).strip():
                            p["score"] = int(name_val.group(2))
            score_history[0] = {p["name"]: p["score"] for p in players}

    # If no initial scores found, set all to 0
    if not score_history[0] and players:
        score_history[0] = {p["name"]: 0 for p in players}

    while i < len(lines):
        line = lines[i]

        # Match round header (multiple formats)
        round_match = re.match(
            r"##\s*Round\s+(\d+)\s*[—–-]+\s*(.*)", line
        )
        if round_match:
            if current_round:
                rounds.append(current_round)
            round_num = int(round_match.group(1))
            turn_text = round_match.group(2).strip()
            # Extract player name from various formats:
            # "Tour d'Audace", "Tour de Raison", "escargot-rigolo", "Sable's Turn"
            pm = re.match(r"Tour d[e']'?\s*(\w+)", turn_text)
            if not pm:
                pm = re.match(r"([\w-]+?)(?:'s\s+Turn)?$", turn_text)
            player_name = pm.group(1) if pm else turn_text
            current_round = {
                "number": round_num,
                "player": player_name,
                "proposal": None,
                "counter_proposal": None,
                "amendments": [],
                "votes": {},
                "result": None,
                "vote_count": None,
                "dice": None,
                "scoring_details": "",
                "scores_after": {},
                "special_events": [],
                "flags": [],
            }
            i += 1
            continue

        if current_round is None:
            # Check for game end
            if "FIN DE PARTIE" in line or "VICTOIRE" in line:
                pass  # handled below
            i += 1
            continue

        # Proposal / Proposition (multiple formats)
        prop_match = re.match(
            r"[-*]*\s*\*\*(Proposition|Proposal|Emergency Proposal)\s+(\d+):?\*\*\s*(.*)", line
        )
        if prop_match:
            prop_num = int(prop_match.group(2))
            remainder = prop_match.group(3).strip()
            prop_type = prop_match.group(1)

            flags = []
            if "RÉVOLUTIONNAIRE" in line:
                flags.append("revolutionary")
            if "Emergency" in prop_type:
                flags.append("emergency")

            # Extract title (quoted or after em-dash) and description
            title_match = re.search(r'"(.+?)"', remainder)
            title = title_match.group(1) if title_match else ""
            if not title:
                title_match = re.match(r'.*?[—–]\s*(.+?)[\(—]', remainder)
                title = title_match.group(1).strip() if title_match else ""
            if not title:
                # Use first sentence as title
                title = remainder.split(".")[0][:80] if remainder else f"Proposal {prop_num}"

            # Clean description: remove leading ": " or "— "
            description = re.sub(r"^[:\s—–-]+", "", remainder).strip()

            current_round["proposal"] = {
                "number": prop_num,
                "title": title,
                "description": description,
                "flags": flags,
            }
            current_round["flags"].extend(flags)
            i += 1
            continue

        # Counter-proposal
        if "CONTREPROPOSITION" in line:
            current_round["flags"].append("counter_proposal")
            cp_match = re.match(r".*CONTREPROPOSITION.*?:\s*(.*)", line)
            if cp_match:
                current_round["counter_proposal"] = cp_match.group(1).strip()
            i += 1
            continue

        # Amendment
        if line.startswith("- **Amendement**"):
            amend_match = re.match(r"- \*\*Amendement\*\*\s*:\s*(.*)", line)
            if amend_match:
                current_round["amendments"].append(amend_match.group(1))
            i += 1
            continue

        # Vote block (multiple formats)
        # Game-6: "- **Vote** : Audace=pour, Raison=pour, ..."
        # Game-4/5: "**Vote:**" or "**Votes:**" followed by "- Player: FOR ..."
        is_vote_header = re.match(r"[-*]*\s*\*\*Votes?\*\*\s*:?\s*(.*)", line)
        if is_vote_header:
            vote_text = is_vote_header.group(1) if is_vote_header.lastindex else ""
            # Collect continuation lines (multi-line vote blocks)
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue
                # Stop if we hit a new section header
                if next_line.startswith("**") and not next_line.startswith("**Result"):
                    break
                if next_line.startswith("## ") or next_line.startswith("### "):
                    break
                vote_text += " " + next_line
                j += 1

            # Format 1: "Player=pour/contre" (game-6 inline)
            for vm in re.finditer(r"([\w-]+)=\*?\*?(pour|contre)\*?\*?", vote_text):
                current_round["votes"][vm.group(1)] = vm.group(2)

            # Format 2: "Player: FOR/AGAINST/yes/no" (game-4/5 list)
            for vm in re.finditer(
                r"([\w-]+):\s*\*?\*?(FOR|AGAINST|yes|no|YES|NO)\*?\*?",
                vote_text,
            ):
                raw = vm.group(2).upper()
                current_round["votes"][vm.group(1)] = (
                    "for" if raw in ("FOR", "YES") else "against"
                )

            # Detect result (may be in same block or next "Result" line)
            full_text = vote_text
            # Also check the Result line if present
            if j < len(lines) and "**Result**" in lines[j]:
                full_text += " " + lines[j]
                j += 1
            result_upper = full_text.upper()
            if any(w in result_upper for w in ("ADOPTED", "ADOPTÉE", "ADOPTE")):
                current_round["result"] = "adopted"
            elif any(w in result_upper for w in ("DEFEATED", "REJETÉE", "REJETE")):
                current_round["result"] = "rejected"

            count_match = re.search(r"\((\d+-\d+)", full_text)
            if count_match:
                current_round["vote_count"] = count_match.group(1)

            if "unanim" in full_text.lower():
                current_round["flags"].append("unanimous")

            i = j  # skip past consumed lines
            continue

        # Result line (standalone, game-4/5 style)
        result_match = re.match(r"\*\*Result:?\*\*\s*(.*)", line)
        if result_match and current_round:
            result_text = result_match.group(1).upper()
            if any(w in result_text for w in ("ADOPTED", "ADOPTÉE")):
                current_round["result"] = "adopted"
            elif any(w in result_text for w in ("DEFEATED", "REJETÉE")):
                current_round["result"] = "rejected"
            count_match = re.search(r"\((\d+-\d+)", result_match.group(1))
            if count_match:
                current_round["vote_count"] = count_match.group(1)
            if "unanim" in result_match.group(1).lower():
                current_round["flags"].append("unanimous")
            i += 1
            continue

        # Dice roll (multiple formats)
        dice_match = re.match(r"[-*]*\s*\*\*(Dé|Dice\s*roll):?\*\*\s*:?\s*(.*)", line)
        if dice_match:
            dice_text = dice_match.group(2)
            # Extract the number: "5", "1d6 → **3**", etc.
            dm = re.search(r"\*\*(\d+)\*\*", dice_text)
            if not dm:
                dm = re.search(r"(\d+)\s*$", dice_text.strip())
            if dm:
                current_round["dice"] = int(dm.group(1))
            i += 1
            continue

        # Scoring details
        scoring_match = re.match(r"[-*]*\s*\*\*Scoring.*?\*\*\s*:?\s*(.*)", line)
        if scoring_match:
            current_round["scoring_details"] = scoring_match.group(1)
            i += 1
            continue

        # Scores after round (multiple formats)
        # "**Scores** : A=10, B=0" or "**Cumulative Scores:** A 10 | B 0"
        scores_match = re.match(
            r"[-*]*\s*\*\*(Scores?|Cumulative\s+Scores?|Scores?\s+after).*?\*\*\s*:?\s*(.*)",
            line, re.IGNORECASE
        )
        if scores_match:
            scores_text = scores_match.group(2)
            # Format: "A=10" or "A 10" with | or , separators
            for sm in re.finditer(r"([\w-]+)\s*[=:]\s*\*?\*?(\d+)\*?\*?", scores_text):
                current_round["scores_after"][sm.group(1)] = int(sm.group(2))
            # Also try pipe-separated: "A 10 | B 20"
            if not current_round["scores_after"]:
                for sm in re.finditer(r"([\w-]+)\s+(\d+)", scores_text):
                    current_round["scores_after"][sm.group(1)] = int(sm.group(2))
            i += 1
            continue

        # Special events
        if "Acte de Gloire" in line:
            current_round["flags"].append("acte_de_gloire")
        if "Lettre de Cachet" in line:
            current_round["flags"].append("lettre_de_cachet")
        if "APPEL R217" in line or "CLERK ADOPTE" in line:
            current_round["flags"].append("clerk_override")
        if "IMPÔT APPLIQUÉ" in line or "IMPÔT" in line.upper():
            if "PAS D'IMPÔT" not in line:
                current_round["special_events"].append(
                    {"type": "tax", "description": line.strip("- *")}
                )
        if "Serment" in line or "juré" in line:
            if "serment" not in [f for f in current_round["flags"]]:
                current_round["flags"].append("serment")

        i += 1

    if current_round:
        rounds.append(current_round)

    # Build score history from rounds
    for r in rounds:
        if r["scores_after"]:
            score_history.append(
                {"round": r["number"], **r["scores_after"]}
            )

    # Parse winner
    winner = None
    final_scores = {}
    for line in lines:
        # "VICTOIRE DE TOCSIN" or "ESCARGOT-RIGOLO WINS"
        wm = re.search(r"VICTOIRE DE ([\w-]+)", line)
        if wm:
            winner = wm.group(1)
        wm = re.search(r"([\w-]+)\s+WINS", line, re.IGNORECASE)
        if wm:
            winner = wm.group(1)
        # Medal lines
        fm = re.match(r"- [🥇🥈🥉]\s*([\w-]+)\s*:\s*\*\*(\d+)\*\*", line)
        if fm:
            final_scores[fm.group(1)] = int(fm.group(2))

    return {
        "players": players,
        "rounds": rounds,
        "score_history": score_history,
        "winner": winner,
        "final_scores": final_scores,
    }


def parse_transcript_messages(transcript_path: Path, agent_name: str) -> list:
    """Extract public messages and thinking from a transcript JSONL.

    Returns a list of message events with timestamps.
    """
    messages = []
    with open(transcript_path) as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("type") != "assistant":
                continue
            msg = entry.get("message", {})
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue

            timestamp = entry.get("timestamp", "")
            thinking_text = ""
            public_text = ""
            send_messages = []

            for block in content:
                if block.get("type") == "thinking":
                    thinking_text = block.get("thinking", "")
                elif block.get("type") == "text":
                    text = block.get("text", "").strip()
                    if text:
                        public_text = text
                elif block.get("type") == "tool_use":
                    if block.get("name") == "SendMessage":
                        inp = block.get("input", {})
                        to = inp.get("to", "")
                        msg_content = inp.get("message", inp.get("content", ""))
                        send_messages.append({
                            "to": to,
                            "message": msg_content,
                        })

            if send_messages:
                for sm in send_messages:
                    messages.append({
                        "timestamp": timestamp,
                        "agent": agent_name,
                        "type": "send_message",
                        "to": sm["to"],
                        "message": sm["message"],
                        "thinking_excerpt": thinking_text[:500] if thinking_text else "",
                    })
            elif public_text:
                messages.append({
                    "timestamp": timestamp,
                    "agent": agent_name,
                    "type": "narration",
                    "message": public_text,
                    "thinking_excerpt": thinking_text[:500] if thinking_text else "",
                })

    return messages


def assign_messages_to_rounds(messages: list, rounds: list) -> None:
    """Assign transcript messages to their corresponding rounds based on timing."""
    if not messages or not rounds:
        return

    # Sort messages by timestamp
    messages.sort(key=lambda m: m["timestamp"])

    # For each round, find messages that fall within its time window
    # We use a simple heuristic: messages between round N start and round N+1 start
    # belong to round N
    for r in rounds:
        r["debate_messages"] = []

    # Simple assignment: distribute messages across rounds proportionally
    # Better approach would use actual timestamps from transcripts
    # For now, just attach all SendMessage entries
    for msg in messages:
        if msg["type"] == "send_message" and msg["to"] in ("*", "team-lead", "Clerk"):
            # This is a public debate message
            # Try to determine which round it belongs to based on content
            for r in rounds:
                if r["proposal"] and (
                    str(r["proposal"]["number"]) in msg["message"]
                    or r["player"] in msg["message"]
                ):
                    r["debate_messages"].append(msg)
                    break


def build_game_data(game_dir: Path) -> dict:
    """Build complete game data from game directory."""
    # Parse game log
    log_data = parse_game_log(game_dir)

    # Parse transcripts if available
    transcript_dir = game_dir / "transcripts"
    all_messages = []
    if transcript_dir.exists():
        for jsonl_file in transcript_dir.glob("*.jsonl"):
            # Derive agent name from filename
            name = jsonl_file.stem
            if name.startswith("player-"):
                # e.g. "player-tocsin-opus" -> "Tocsin"
                parts = name.split("-")
                agent_name = parts[1].capitalize() if len(parts) > 1 else name
            else:
                agent_name = name.capitalize()

            messages = parse_transcript_messages(jsonl_file, agent_name)
            all_messages.extend(messages)

    # Assign messages to rounds
    assign_messages_to_rounds(all_messages, log_data["rounds"])

    # Read charter if available
    charter = ""
    charter_path = game_dir / "game_charter.md"
    if charter_path.exists():
        charter = charter_path.read_text().strip()

    # Read briefing if available
    briefing = ""
    briefing_path = game_dir / "game_briefing.md"
    if briefing_path.exists():
        briefing = briefing_path.read_text().strip()

    # Determine player models from transcript filenames
    player_models = {}
    if transcript_dir.exists():
        for jsonl_file in transcript_dir.glob("player-*.jsonl"):
            parts = jsonl_file.stem.split("-")
            if len(parts) >= 3:
                name = parts[1].capitalize()
                model = parts[2]
                player_models[name] = model

    # Enrich player data
    model_display = {"opus": "Opus", "sonnet": "Sonnet", "haiku": "Haiku"}
    player_colors = {}
    color_palette = ["#D4920B", "#2952A3", "#A61C1C", "#2D8659", "#7B3FA0"]
    for idx, p in enumerate(log_data["players"]):
        p["model"] = model_display.get(player_models.get(p["name"], ""), "")
        p["color"] = color_palette[idx % len(color_palette)]
        p["final_score"] = log_data["final_scores"].get(p["name"], p["score"])
        player_colors[p["name"]] = p["color"]

    # Build key moments (editorial — curated from game events)
    key_moments = []
    for r in log_data["rounds"]:
        if "revolutionary" in r["flags"]:
            key_moments.append({
                "round": r["number"],
                "type": "revolutionary",
                "title": f"Proposition Révolutionnaire",
                "description": f"{r['player']} invoque la Proposition Révolutionnaire pour la proposition {r['proposal']['number']}",
            })
        if "counter_proposal" in r["flags"]:
            key_moments.append({
                "round": r["number"],
                "type": "counter_proposal",
                "title": "Contreproposition",
                "description": f"Une contreproposition remplace la proposition originale au Round {r['number']}",
            })
        if r["result"] == "rejected":
            key_moments.append({
                "round": r["number"],
                "type": "turning_point",
                "title": "Proposition Rejetée",
                "description": f"La proposition de {r['player']} est rejetée ({r['vote_count']})",
            })
        if "lettre_de_cachet" in r["flags"]:
            key_moments.append({
                "round": r["number"],
                "type": "power_play",
                "title": "Lettre de Cachet",
                "description": f"Un joueur est banni du vote au Round {r['number']}",
            })
        if "clerk_override" in r["flags"]:
            key_moments.append({
                "round": r["number"],
                "type": "power_play",
                "title": "Appel au Clerk",
                "description": f"Le Clerk intervient pour adopter la proposition au Round {r['number']}",
            })

    # Find game date from transcripts
    game_date = ""
    if transcript_dir.exists():
        for jsonl_file in transcript_dir.glob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    entry = json.loads(line)
                    ts = entry.get("timestamp", "")
                    if ts:
                        game_date = ts[:10]
                        break
            if game_date:
                break

    return {
        "meta": {
            "id": game_dir.name,
            "theme": "Révolution Française",
            "date": game_date,
            "winner": log_data["winner"],
            "total_rounds": len(log_data["rounds"]),
            "charter": charter,
            "briefing": briefing,
        },
        "players": log_data["players"],
        "rounds": log_data["rounds"],
        "score_history": log_data["score_history"],
        "key_moments": key_moments,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_game.py <game_directory> [output_path]")
        sys.exit(1)

    game_dir = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("game_data.json")

    data = build_game_data(game_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Parsed {len(data['rounds'])} rounds, {len(data['key_moments'])} key moments")
    print(f"Players: {', '.join(p['name'] + ' (' + p['model'] + ')' for p in data['players'])}")
    print(f"Winner: {data['meta']['winner']}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
