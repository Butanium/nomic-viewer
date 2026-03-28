"""Parse Nomic game transcripts (JSONL) into structured JSON for the replay viewer.

Reads the raw Claude Code transcript files and produces a unified timeline of events.
No game_log.md parsing, no regex heuristics — structured event data only.
"""

import json
import sys
from pathlib import Path


def extract_agent_info(transcript_path: Path) -> dict:
    """Extract agent name and model from transcript filename and content.

    Returns dict with 'name', 'model', 'role' (player or clerk).
    """
    stem = transcript_path.stem
    info = {"name": stem, "model": "", "role": "player", "session_id": ""}

    if stem == "clerk":
        info["role"] = "clerk"
        info["name"] = "clerk"
    elif stem.startswith("player-"):
        # e.g. "player-escargot-rigolo-haiku" → name="escargot-rigolo", model="haiku"
        parts = stem[len("player-"):]
        for model in ("opus", "sonnet", "haiku"):
            if parts.endswith(f"-{model}"):
                info["model"] = model
                info["name"] = parts[: -(len(model) + 1)]
                break
        else:
            info["name"] = parts
    else:
        # e.g. "ember-haiku" (game-0 format)
        for model in ("opus", "sonnet", "haiku"):
            if stem.endswith(f"-{model}"):
                info["model"] = model
                info["name"] = stem[: -(len(model) + 1)]
                break
            elif f"-{model}-" in stem:
                idx = stem.index(f"-{model}-")
                info["model"] = model
                info["name"] = stem[:idx]
                break

    # Read first line for agent-setting and session info
    with open(transcript_path) as f:
        for raw_line in f:
            entry = json.loads(raw_line)
            if entry.get("type") == "agent-setting":
                info["session_id"] = entry.get("sessionId", "")
                break
            if entry.get("sessionId"):
                info["session_id"] = entry["sessionId"]
                break

    # Try to get model from first assistant message
    if not info["model"] and info["role"] != "clerk":
        with open(transcript_path) as f:
            for raw_line in f:
                entry = json.loads(raw_line)
                if entry.get("type") == "assistant":
                    model_id = entry.get("message", {}).get("model", "")
                    if "opus" in model_id:
                        info["model"] = "opus"
                    elif "sonnet" in model_id:
                        info["model"] = "sonnet"
                    elif "haiku" in model_id:
                        info["model"] = "haiku"
                    break

    # Clerk model detection
    if info["role"] == "clerk" and not info["model"]:
        with open(transcript_path) as f:
            for raw_line in f:
                entry = json.loads(raw_line)
                if entry.get("type") == "assistant":
                    model_id = entry.get("message", {}).get("model", "")
                    if "opus" in model_id:
                        info["model"] = "opus"
                    elif "sonnet" in model_id:
                        info["model"] = "sonnet"
                    elif "haiku" in model_id:
                        info["model"] = "haiku"
                    break

    return info


def classify_bash_command(command: str) -> tuple[str, dict]:
    """Classify a Bash command into a semantic action based on the CLI invocation.

    Returns (action_type, extracted_fields).
    Does NOT use regex heuristics — reads the structured CLI arguments.
    """
    parts = command.strip().split()

    # Find the CLI script invocation
    cli_idx = None
    for i, p in enumerate(parts):
        if p.endswith("player_cli.py") or p.endswith("clerk_cli.py"):
            cli_idx = i
            break

    if cli_idx is None:
        return "bash", {}

    # The command is the next argument after the script
    remaining = parts[cli_idx + 1:] if cli_idx + 1 < len(parts) else []
    if not remaining:
        return "bash", {}

    action = remaining[0]

    if action == "propose":
        # propose <key> <proposal_text>
        # The proposal text is everything after the key, but it's in quotes in the original command
        # We just know it's a proposal action
        return "propose", {}

    elif action == "commit":
        # commit <vote> <nonce>
        vote = remaining[1] if len(remaining) > 1 else ""
        return "commit", {"vote": vote}

    elif action == "roll_dice":
        return "roll_dice", {}

    elif action in ("write_note", "append_note"):
        filename = remaining[2] if len(remaining) > 2 else ""
        # Content is the rest, usually in quotes
        content_start = command.find(filename) + len(filename) if filename else -1
        content = command[content_start:].strip().strip("'\"") if content_start > 0 else ""
        return action, {"filename": filename, "content": content}

    elif action == "load_note":
        filename = remaining[2] if len(remaining) > 2 else ""
        return "load_note", {"filename": filename}

    elif action in ("write_file", "edit_file"):
        filename = remaining[2] if len(remaining) > 2 else ""
        return action, {"filename": filename}

    elif action == "contact_supervisor":
        return "contact_supervisor", {}

    elif action == "verify":
        return "verify", {}

    elif action == "verify_proposal":
        return "verify_proposal", {}

    return "bash", {}


def extract_sendmessage(tool_input: dict) -> dict:
    """Extract fields from a SendMessage tool call input."""
    return {
        "to": tool_input.get("to", ""),
        "message": tool_input.get("message", tool_input.get("content", "")),
        "summary": tool_input.get("summary", ""),
    }


def extract_file_edit(tool_name: str, tool_input: dict) -> dict:
    """Extract fields from an Edit or Write tool call."""
    file_path = tool_input.get("file_path", "")
    # Simplify path to just the filename
    filename = Path(file_path).name if file_path else ""

    result = {"filename": filename, "file_path": file_path}

    if tool_name == "Edit":
        result["old_string"] = tool_input.get("old_string", "")
        result["new_string"] = tool_input.get("new_string", "")
    elif tool_name == "Write":
        result["content"] = tool_input.get("content", "")

    return result


def parse_transcript(transcript_path: Path, agent_info: dict) -> list[dict]:
    """Parse a single transcript JSONL file into a list of events.

    Each event has: id, timestamp, source, type, and type-specific fields.
    Only extracts OUTGOING events (what this agent did/said/thought).
    """
    events = []
    agent_name = agent_info["name"]

    # Build a map of tool_use_id → tool call event, so we can attach results
    pending_tool_calls: dict[str, dict] = {}

    with open(transcript_path) as f:
        for raw_line in f:
            entry = json.loads(raw_line)
            entry_type = entry.get("type")
            timestamp = entry.get("timestamp", "")

            if entry_type == "assistant":
                content_blocks = entry.get("message", {}).get("content", [])
                if not isinstance(content_blocks, list):
                    continue

                for block in content_blocks:
                    if not isinstance(block, dict):
                        continue

                    block_type = block.get("type")

                    # ── Thinking ──
                    if block_type == "thinking":
                        thinking_text = block.get("thinking", "")
                        if thinking_text.strip():
                            events.append({
                                "timestamp": timestamp,
                                "source": agent_name,
                                "type": "thinking",
                                "content": thinking_text,
                            })

                    # ── Text output ──
                    elif block_type == "text":
                        text = block.get("text", "").strip()
                        if text:
                            events.append({
                                "timestamp": timestamp,
                                "source": agent_name,
                                "type": "text",
                                "content": text,
                            })

                    # ── Tool use ──
                    elif block_type == "tool_use":
                        tool_name = block.get("name", "")
                        tool_id = block.get("id", "")
                        tool_input = block.get("input", {})

                        if tool_name == "SendMessage":
                            sm = extract_sendmessage(tool_input)
                            evt = {
                                "timestamp": timestamp,
                                "source": agent_name,
                                "type": "message",
                                "to": sm["to"],
                                "content": sm["message"],
                                "summary": sm["summary"],
                                "is_broadcast": sm["to"] == "*",
                                "tool_use_id": tool_id,
                            }
                            events.append(evt)
                            pending_tool_calls[tool_id] = evt

                        elif tool_name in ("Edit", "Write"):
                            fe = extract_file_edit(tool_name, tool_input)
                            evt = {
                                "timestamp": timestamp,
                                "source": agent_name,
                                "type": "file_edit",
                                "tool": tool_name,
                                "tool_use_id": tool_id,
                                **fe,
                            }
                            events.append(evt)
                            pending_tool_calls[tool_id] = evt

                        elif tool_name == "Bash":
                            command = tool_input.get("command", "")
                            description = tool_input.get("description", "")
                            action, fields = classify_bash_command(command)

                            evt = {
                                "timestamp": timestamp,
                                "source": agent_name,
                                "type": "tool_call",
                                "tool": action,
                                "tool_name": "Bash",
                                "description": description,
                                "command": command,
                                "tool_use_id": tool_id,
                                **fields,
                            }
                            events.append(evt)
                            pending_tool_calls[tool_id] = evt

                        elif tool_name.startswith("mcp__"):
                            # MCP tool call — extract the tool name
                            # e.g. "mcp__nomic-crypto__verify" → "verify"
                            mcp_parts = tool_name.split("__")
                            short_name = mcp_parts[-1] if len(mcp_parts) > 1 else tool_name

                            evt = {
                                "timestamp": timestamp,
                                "source": agent_name,
                                "type": "tool_call",
                                "tool": short_name,
                                "tool_name": tool_name,
                                "input": tool_input,
                                "tool_use_id": tool_id,
                            }
                            events.append(evt)
                            pending_tool_calls[tool_id] = evt

                        elif tool_name in ("Agent", "TeamCreate"):
                            evt = {
                                "timestamp": timestamp,
                                "source": agent_name,
                                "type": "tool_call",
                                "tool": tool_name.lower(),
                                "tool_name": tool_name,
                                "input": {
                                    k: v for k, v in tool_input.items()
                                    if k in ("prompt", "description", "team_name",
                                             "agent_type", "name", "model")
                                },
                                "tool_use_id": tool_id,
                            }
                            events.append(evt)
                            pending_tool_calls[tool_id] = evt

                        else:
                            # Other tools (Read, Grep, Glob, ToolSearch, etc.)
                            evt = {
                                "timestamp": timestamp,
                                "source": agent_name,
                                "type": "tool_call",
                                "tool": tool_name.lower(),
                                "tool_name": tool_name,
                                "description": tool_input.get("description", ""),
                                "tool_use_id": tool_id,
                            }
                            events.append(evt)
                            pending_tool_calls[tool_id] = evt

            elif entry_type == "user":
                # User events contain tool results and incoming messages.
                # We only extract tool results to attach to pending tool calls.
                msg_content = entry.get("message", {}).get("content", "")

                if isinstance(msg_content, list):
                    for block in msg_content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "tool_result":
                            tool_use_id = block.get("tool_use_id", "")
                            is_error = block.get("is_error", False)
                            result_content = block.get("content", "")

                            # Simplify result content
                            if isinstance(result_content, list):
                                texts = []
                                for item in result_content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        texts.append(item.get("text", ""))
                                result_content = "\n".join(texts)

                            # Attach result to the pending tool call
                            if tool_use_id in pending_tool_calls:
                                evt = pending_tool_calls[tool_use_id]
                                evt["result"] = result_content[:2000] if isinstance(result_content, str) else str(result_content)[:2000]
                                evt["is_error"] = is_error
                                del pending_tool_calls[tool_use_id]

    return events


def detect_players_from_clerk(clerk_events: list[dict]) -> list[dict]:
    """Detect player info from clerk's Agent/TeamCreate tool calls."""
    players = []
    for evt in clerk_events:
        if evt["type"] == "tool_call" and evt.get("tool") == "agent":
            prompt = evt.get("input", {}).get("prompt", "")
            # The prompt starts with "You are **player-name**"
            if "You are **" in prompt:
                start = prompt.index("You are **") + len("You are **")
                end = prompt.index("**", start)
                name = prompt[start:end]
                model = evt.get("input", {}).get("model", "")
                if name and name not in [p["name"] for p in players]:
                    players.append({"name": name, "model": model})
    return players


def build_game_data(game_dir: Path) -> dict:
    """Build complete game data from a game directory's transcripts.

    Returns a structured dict ready for JSON serialization.
    """
    transcript_dir = game_dir / "transcripts"
    if not transcript_dir.exists():
        raise FileNotFoundError(f"No transcripts directory found in {game_dir}")

    # Parse all transcripts
    agents = {}
    all_events = []

    for jsonl_file in sorted(transcript_dir.glob("*.jsonl")):
        agent_info = extract_agent_info(jsonl_file)
        agents[agent_info["name"]] = agent_info

        events = parse_transcript(jsonl_file, agent_info)
        all_events.extend(events)

    # Sort by timestamp
    all_events.sort(key=lambda e: e.get("timestamp", ""))

    # Extract time range
    timestamps = [e["timestamp"] for e in all_events if e.get("timestamp")]
    start_time = timestamps[0] if timestamps else ""
    end_time = timestamps[-1] if timestamps else ""

    # Detect players from clerk events
    clerk_events = [e for e in all_events if e.get("source") == "clerk"]
    detected_players = detect_players_from_clerk(clerk_events)

    # Build player list: merge detected info with agent file info
    players = []
    for agent_name, info in sorted(agents.items()):
        if info["role"] == "clerk":
            continue
        model = info["model"]
        # Check if we got model from clerk's Agent calls
        if not model:
            for dp in detected_players:
                if dp["name"] == agent_name:
                    model = dp["model"]
                    break
        players.append({
            "name": agent_name,
            "model": model,
            "role": "player",
        })

    # Sort players alphabetically (game turn order)
    players.sort(key=lambda p: p["name"])

    # Clerk info
    clerk_info = None
    for agent_name, info in agents.items():
        if info["role"] == "clerk":
            clerk_info = {
                "name": agent_name,
                "model": info["model"],
                "role": "clerk",
            }
            break

    # Filter events to remove low-signal noise
    filtered_events = []
    for evt in all_events:
        # Skip Read/Grep/Glob/ToolSearch tool calls — too noisy for the viewer
        if evt["type"] == "tool_call" and evt.get("tool") in (
            "read", "grep", "glob", "toolsearch",
        ):
            continue

        # Skip progress/system events (already filtered by parse_transcript)
        filtered_events.append(evt)

    # Compute stats
    stats = {
        "total_events": len(filtered_events),
        "total_messages": sum(1 for e in filtered_events if e["type"] == "message"),
        "total_broadcasts": sum(
            1 for e in filtered_events
            if e["type"] == "message" and e.get("is_broadcast")
        ),
        "total_thinking": sum(1 for e in filtered_events if e["type"] == "thinking"),
        "total_tool_calls": sum(1 for e in filtered_events if e["type"] == "tool_call"),
        "total_file_edits": sum(1 for e in filtered_events if e["type"] == "file_edit"),
    }

    return {
        "meta": {
            "game_id": game_dir.name,
            "start_time": start_time,
            "end_time": end_time,
            "stats": stats,
        },
        "players": players,
        "clerk": clerk_info,
        "events": filtered_events,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_transcripts.py <game_directory> [output_path]")
        sys.exit(1)

    game_dir = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("game_data.json")

    data = build_game_data(game_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    meta = data["meta"]
    print(f"Game: {meta['game_id']}")
    print(f"Time: {meta['start_time']} → {meta['end_time']}")
    print(f"Players: {', '.join(p['name'] + ' (' + p['model'] + ')' for p in data['players'])}")
    if data["clerk"]:
        print(f"Clerk: {data['clerk']['name']} ({data['clerk']['model']})")
    print(f"Events: {meta['stats']['total_events']} total")
    print(f"  Messages: {meta['stats']['total_messages']} ({meta['stats']['total_broadcasts']} broadcasts)")
    print(f"  Thinking: {meta['stats']['total_thinking']}")
    print(f"  Tool calls: {meta['stats']['total_tool_calls']}")
    print(f"  File edits: {meta['stats']['total_file_edits']}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
