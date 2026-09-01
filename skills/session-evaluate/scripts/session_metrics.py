#!/usr/bin/env python3
"""Extract a compact performance and workflow digest from a Claude Code session transcript.

Session transcripts are multi-megabyte JSONL files. This script does all the parsing so the
agent never loads raw transcript content into its own context; it reads only the digest.

Usage:
    session_metrics.py --list [--project PATH] [--limit N]
    session_metrics.py SESSION_JSONL [--top N] [--json]
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"
CHARS_PER_TOKEN = 4


def encode_project(cwd):
    return str(cwd).replace("/", "-")


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def est_tokens(text):
    return len(text) // CHARS_PER_TOKEN


def human(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def duration(ms):
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds // 60:.0f}m{seconds % 60:02.0f}s"
    return f"{seconds // 3600:.0f}h{(seconds % 3600) // 60:02.0f}m"


def block_text(content):
    """Flatten a tool_result content field (string, or list of blocks) into plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text") or json.dumps(block))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    if content is None:
        return ""
    return json.dumps(content)


LABEL_FIELDS = {
    "Bash": "command",
    "Read": "file_path",
    "Edit": "file_path",
    "Write": "file_path",
    "NotebookEdit": "notebook_path",
    "Grep": "pattern",
    "Glob": "pattern",
    "Agent": "description",
    "Task": "description",
    "Skill": "skill",
    "ToolSearch": "query",
    "WebFetch": "url",
    "WebSearch": "query",
}


def tool_label(name, tool_input):
    if not isinstance(tool_input, dict):
        return ""
    field = LABEL_FIELDS.get(name)
    if field and isinstance(tool_input.get(field), str):
        return tool_input[field][:100]
    for value in tool_input.values():
        if isinstance(value, str) and value:
            return value[:100]
    return ""


def load(path):
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


# --------------------------------------------------------------------------- collectors


def collect_tool_calls(records):
    """Pair every tool_use with its tool_result. Returns a list of call dicts."""
    calls = {}
    order = []
    for record in records:
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                call = {
                    "id": block.get("id"),
                    "name": block.get("name", "?"),
                    "label": tool_label(block.get("name", ""), block.get("input")),
                    "input_tokens": est_tokens(json.dumps(block.get("input") or {})),
                    "result_tokens": 0,
                    "error": False,
                    "ts": parse_ts(record.get("timestamp")),
                    "sidechain": bool(record.get("isSidechain")),
                }
                calls[call["id"]] = call
                order.append(call)
            elif block.get("type") == "tool_result":
                call = calls.get(block.get("tool_use_id"))
                if call is None:
                    continue
                text = block_text(block.get("content"))
                call["result_tokens"] = est_tokens(text)
                call["error"] = bool(block.get("is_error"))
                call["result_head"] = text[:200]
    return order


def token_totals(records):
    totals = Counter()
    peak = {"context": 0, "ts": None}
    effort = Counter()
    turns = 0
    for record in records:
        if record.get("type") != "assistant":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        turns += 1
        effort[record.get("effort") or "?"] += 1
        fresh = usage.get("input_tokens") or 0
        created = usage.get("cache_creation_input_tokens") or 0
        cached = usage.get("cache_read_input_tokens") or 0
        totals["input"] += fresh
        totals["cache_creation"] += created
        totals["cache_read"] += cached
        totals["output"] += usage.get("output_tokens") or 0
        context = fresh + created + cached
        if context > peak["context"]:
            peak = {"context": context, "ts": record.get("timestamp")}
    totals["assistant_turns"] = turns
    return totals, peak, effort


def turn_timeline(records, calls):
    """Bucket tool calls into turns delimited by turn_duration records."""
    turns = [
        {
            "ms": record.get("durationMs") or 0,
            "end": parse_ts(record.get("timestamp")),
            "messages": record.get("messageCount") or 0,
            "tools": Counter(),
        }
        for record in records
        if record.get("type") == "system" and record.get("subtype") == "turn_duration"
    ]
    turns = [turn for turn in turns if turn["end"]]
    turns.sort(key=lambda turn: turn["end"])
    start = None
    for turn in turns:
        turn["start"] = start
        start = turn["end"]
    for call in calls:
        if not call["ts"]:
            continue
        for turn in turns:
            if call["ts"] <= turn["end"] and (turn["start"] is None or call["ts"] > turn["start"]):
                turn["tools"][call["name"]] += 1
                break
    return turns


def parallelism(records):
    """Measure batching: how many tool calls each model response issued.

    Claude Code writes one assistant record per content block, so a parallel batch appears as
    several records sharing a requestId. Grouping by requestId is what recovers the real width.
    """
    by_request = {}
    order = []
    for record in records:
        if record.get("type") != "assistant" or record.get("isSidechain"):
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        width = sum(1 for b in content if isinstance(b, dict) and b.get("type") == "tool_use")
        if not width:
            continue
        key = record.get("requestId") or record.get("uuid")
        if key not in by_request:
            by_request[key] = 0
            order.append(key)
        by_request[key] += width
    widths = [by_request[key] for key in order]
    solo_runs = []
    run = 0
    for width in widths:
        if width == 1:
            run += 1
        else:
            if run:
                solo_runs.append(run)
            run = 0
    if run:
        solo_runs.append(run)
    return {
        "batches": len(widths),
        "solo": sum(1 for w in widths if w == 1),
        "batched": sum(1 for w in widths if w > 1),
        "calls": sum(widths),
        "longest_solo_run": max(solo_runs) if solo_runs else 0,
        "solo_runs_over_3": sum(1 for r in solo_runs if r > 3),
    }


def compactions(records):
    events = []
    for record in records:
        if record.get("subtype") != "compact_boundary":
            continue
        meta = record.get("compactMetadata") or {}
        events.append(
            {
                "trigger": meta.get("trigger", "?"),
                "pre": meta.get("preTokens", 0),
                "post": meta.get("postTokens", 0),
                "dropped": meta.get("cumulativeDroppedTokens", 0),
                "ms": meta.get("durationMs", 0),
                "ts": record.get("timestamp"),
            }
        )
    return events


def subagents(session_path, calls):
    """Subagent spend and whether they ran concurrently."""
    launches = [c for c in calls if c["name"] in ("Agent", "Task")]
    sub_dir = session_path.parent / session_path.stem / "subagents"
    runs = []
    if sub_dir.is_dir():
        for file in sorted(sub_dir.glob("*.jsonl")):
            sub_records = load(file)
            totals, _, _ = token_totals(sub_records)
            stamps = [parse_ts(r.get("timestamp")) for r in sub_records]
            stamps = sorted(s for s in stamps if s)
            if not stamps:
                continue
            runs.append(
                {
                    "id": file.stem[:8],
                    "start": stamps[0],
                    "end": stamps[-1],
                    "billed": totals["input"] + totals["cache_creation"] + totals["cache_read"],
                    "output": totals["output"],
                    "turns": totals["assistant_turns"],
                }
            )
    concurrency = 0
    if runs:
        edges = [(r["start"], 1) for r in runs] + [(r["end"], -1) for r in runs]
        edges.sort(key=lambda e: (e[0], -e[1]))
        live = 0
        for _, delta in edges:
            live += delta
            concurrency = max(concurrency, live)
    return launches, runs, concurrency


def repetition(calls):
    """Identical work done more than once — the clearest token waste signal."""
    seen = defaultdict(int)
    for call in calls:
        if call["name"] in ("Read", "Bash", "Grep", "Glob", "WebFetch"):
            seen[(call["name"], call["label"])] += 1
    repeats = [(name, label, n) for (name, label), n in seen.items() if n > 1]
    repeats.sort(key=lambda item: -item[2])
    return repeats


def toolsearch_batching(calls):
    singles = 0
    total = 0
    for call in calls:
        if call["name"] != "ToolSearch":
            continue
        total += 1
        query = call["label"]
        if query.startswith("select:") and "," not in query:
            singles += 1
    return total, singles


def skills_used(records, calls):
    used = Counter()
    for call in calls:
        if call["name"] == "Skill":
            used[call["label"]] += 1
    for record in records:
        if record.get("type") == "system" and record.get("subtype") == "local_command":
            text = json.dumps(record)
            for match in re.findall(r"<command-name>/?([a-z0-9-]+)</command-name>", text):
                used[match] += 1
    return used


def skill_windows(records, calls, sub_runs, session_end):
    """Wall-clock time and token spend attributed to each skill invocation.

    A window runs from one Skill-tool call or slash-command invocation to the next one
    (or session end). Tokens and tool calls are scoped to the main thread (isSidechain
    records excluded) so they aren't double-counted against the Subagents section — any
    subagent that started inside the window is reported alongside it instead.
    """
    events = []
    for call in calls:
        if call["name"] == "Skill" and call["ts"]:
            events.append({"name": call["label"] or "?", "ts": call["ts"]})
    for record in records:
        if record.get("type") == "system" and record.get("subtype") == "local_command":
            ts = parse_ts(record.get("timestamp"))
            if not ts:
                continue
            for match in re.findall(r"<command-name>/?([a-z0-9-]+)</command-name>", json.dumps(record)):
                events.append({"name": match, "ts": ts})
    events.sort(key=lambda e: e["ts"])
    if not events:
        return []

    tagged = [(record, parse_ts(record.get("timestamp"))) for record in records]
    seen = Counter()
    windows = []
    for i, event in enumerate(events):
        start = event["ts"]
        end = events[i + 1]["ts"] if i + 1 < len(events) else (session_end or start)
        seen[event["name"]] += 1
        window_records = [r for r, ts in tagged if ts and not r.get("isSidechain") and start <= ts < end]
        totals, _, _ = token_totals(window_records)
        window_calls = [c for c in calls if c["ts"] and start <= c["ts"] < end]
        sub_hits = [s for s in sub_runs if start <= s["start"] < end]
        windows.append(
            {
                "name": event["name"],
                "seq": seen[event["name"]],
                "start": start,
                "ms": (end - start).total_seconds() * 1000,
                "input": totals["input"] + totals["cache_creation"] + totals["cache_read"],
                "output": totals["output"],
                "tool_calls": len(window_calls),
                "sub_count": len(sub_hits),
                "sub_billed": sum(s["billed"] for s in sub_hits),
            }
        )
    return windows


FULL_SUITE_PATTERNS = [
    re.compile(r"^\s*(npm|yarn|pnpm)\s+(run\s+)?test(\s+--[\w-]+)*\s*$"),
    re.compile(r"^\s*(python3?\s+-m\s+)?pytest(\s+-[a-zA-Z]+)*\s*$"),
    re.compile(r"^\s*go\s+test\s+\./\.\.\.\s*$"),
    re.compile(r"^\s*cargo\s+test\s*$"),
    re.compile(r"^\s*(mvn|\./?mvnw)\s+(test|verify)\s*$"),
    re.compile(r"^\s*(gradle|\./?gradlew)\s+test\s*$"),
    re.compile(r"^\s*(bundle\s+exec\s+)?rspec\s*$"),
    re.compile(r"^\s*make\s+test\s*$"),
    re.compile(r"^\s*tox\s*$"),
    re.compile(r"^\s*dotnet\s+test\s*$"),
    re.compile(r"^\s*phpunit\s*$"),
]


def test_suite_runs(calls):
    """Bash calls shaped like a full test-suite run — no path/filter narrowing them.

    Heuristic, pattern-matched against common test-runner invocations. `call['label']`
    truncates at 100 chars, so an unusually long command line may be missed or misjudged —
    treat this as a candidate list to verify, not an exhaustive count.

    Each hit also carries the distinct files touched (Edit/Write) since the previous full-suite
    run (or session start, for the first) — the evidence a scope-mismatch finding needs: a full
    run following a one- or two-file touch is the signal, not the raw run count.
    """
    hits = []
    touched = set()
    for call in calls:
        if call["name"] in ("Edit", "Write") and call["label"]:
            touched.add(call["label"])
            continue
        if call["name"] != "Bash":
            continue
        command = call["label"]
        if any(pattern.match(command) for pattern in FULL_SUITE_PATTERNS):
            hits.append(
                {
                    "ts": call["ts"],
                    "command": command,
                    "error": call["error"],
                    "files_touched": len(touched),
                }
            )
            touched = set()
    hits.sort(key=lambda hit: (hit["ts"] is None, hit["ts"]))
    return hits


# --------------------------------------------------------------------------- rendering


def render(session_path, records, top):
    out = []
    add = out.append

    meta = next((r for r in records if r.get("type") == "assistant"), {})
    stamps = sorted(s for s in (parse_ts(r.get("timestamp")) for r in records) if s)
    span = (stamps[-1] - stamps[0]).total_seconds() if len(stamps) > 1 else 0

    calls = collect_tool_calls(records)
    totals, peak, effort = token_totals(records)
    turns = turn_timeline(records, calls)
    batching = parallelism(records)
    compact_events = compactions(records)
    launches, sub_runs, concurrency = subagents(session_path, calls)
    repeats = repetition(calls)
    ts_total, ts_singles = toolsearch_batching(calls)
    skills = skills_used(records, calls)
    windows = skill_windows(records, calls, sub_runs, stamps[-1] if stamps else None)
    suite_runs = test_suite_runs(calls)

    billed_input = totals["input"] + totals["cache_creation"] + totals["cache_read"]
    cacheable = billed_input or 1

    add("## Session")
    add(f"- id: {session_path.stem}")
    add(f"- cwd: {meta.get('cwd', '?')}   branch: {meta.get('gitBranch', '?')}   cli: {meta.get('version', '?')}")
    add(f"- records: {len(records)}   wall-clock span: {duration(span * 1000)}")
    add(f"- effort mix: {dict(effort)}")

    add("\n## Tokens")
    add(f"- billed input: {human(billed_input)}  (fresh {human(totals['input'])} | cache-write {human(totals['cache_creation'])} | cache-read {human(totals['cache_read'])})")
    add(f"- output: {human(totals['output'])} over {totals['assistant_turns']} assistant turns")
    add(f"- cache hit ratio: {totals['cache_read'] / cacheable:.1%}   cache-write share: {totals['cache_creation'] / cacheable:.1%}")
    add(f"- peak context: {human(peak['context'])} at {peak['ts']}")

    add("\n## Tool spend (est. tokens returned into context)")
    by_tool = defaultdict(lambda: {"n": 0, "result": 0, "err": 0})
    for call in calls:
        entry = by_tool[call["name"]]
        entry["n"] += 1
        entry["result"] += call["result_tokens"]
        entry["err"] += 1 if call["error"] else 0
    add("| tool | calls | result tokens | mean | errors |")
    add("| --- | --- | --- | --- | --- |")
    for name, entry in sorted(by_tool.items(), key=lambda kv: -kv[1]["result"]):
        add(f"| {name} | {entry['n']} | {human(entry['result'])} | {human(entry['result'] // max(entry['n'], 1))} | {entry['err']} |")

    add(f"\n## Heaviest individual calls (top {top})")
    add("| tokens | tool | target |")
    add("| --- | --- | --- |")
    for call in sorted(calls, key=lambda c: -c["result_tokens"])[:top]:
        label = call["label"].replace("|", "\\|").replace("\n", " ")
        add(f"| {human(call['result_tokens'])} | {call['name']} | `{label}` |")

    add(f"\n## Repeated identical calls (top {top})")
    if repeats:
        add("| times | tool | target |")
        add("| --- | --- | --- |")
        for name, label, count in repeats[:top]:
            label = label.replace("|", "\\|").replace("\n", " ")
            add(f"| {count} | {name} | `{label}` |")
    else:
        add("- none")

    add("\n## Full test-suite runs (heuristic — verify before treating as exhaustive)")
    if suite_runs:
        add(f"- {len(suite_runs)} detected")
        add("| # | time | command | failed | files touched since last run |")
        add("| --- | --- | --- | --- | --- |")
        for i, hit in enumerate(suite_runs, 1):
            when = f"{hit['ts']:%H:%M:%S}" if hit["ts"] else "?"
            add(f"| {i} | {when} | `{hit['command']}` | {'yes' if hit['error'] else 'no'} | {hit['files_touched']} |")
    else:
        add("- none detected")

    add("\n## Runtime")
    if turns:
        durations = sorted(t["ms"] for t in turns)
        p50 = durations[len(durations) // 2]
        p95 = durations[int(len(durations) * 0.95) - 1] if len(durations) > 1 else durations[0]
        add(f"- turns: {len(turns)}   total {duration(sum(durations))}   p50 {duration(p50)}   p95 {duration(p95)}   max {duration(durations[-1])}")
        add(f"\n### Slowest turns (top {min(top, len(turns))})")
        add("| duration | ended | tools in turn |")
        add("| --- | --- | --- |")
        for turn in sorted(turns, key=lambda t: -t["ms"])[:top]:
            tools = ", ".join(f"{k}x{v}" for k, v in turn["tools"].most_common(5)) or "-"
            add(f"| {duration(turn['ms'])} | {turn['end']:%H:%M:%S} | {tools} |")
    else:
        add("- no turn_duration records")

    add("\n## Batching / parallelism")
    add(f"- tool-issuing assistant messages: {batching['batches']} ({batching['solo']} single-call, {batching['batched']} batched)")
    add(f"- total tool calls: {batching['calls']}")
    add(f"- longest consecutive run of single-call turns: {batching['longest_solo_run']}")
    add(f"- runs of >3 consecutive single-call turns: {batching['solo_runs_over_3']}")
    if ts_total:
        add(f"- ToolSearch: {ts_total} calls, {ts_singles} loading a single tool")

    add("\n## Context loss (compaction)")
    if compact_events:
        add("| trigger | pre | post | cumulative dropped | cost |")
        add("| --- | --- | --- | --- | --- |")
        for event in compact_events:
            add(f"| {event['trigger']} | {human(event['pre'])} | {human(event['post'])} | {human(event['dropped'])} | {duration(event['ms'])} |")
    else:
        add("- none")

    add("\n## Subagents")
    add(f"- Agent/Task launches: {len(launches)}   transcripts found: {len(sub_runs)}   max concurrency: {concurrency}")
    if sub_runs:
        add("| id | billed input | output | turns | duration |")
        add("| --- | --- | --- | --- | --- |")
        for run in sorted(sub_runs, key=lambda r: -r["billed"])[:top]:
            secs = (run["end"] - run["start"]).total_seconds()
            add(f"| {run['id']} | {human(run['billed'])} | {human(run['output'])} | {run['turns']} | {duration(secs * 1000)} |")
    for call in launches[:top]:
        add(f"- launch: `{call['label']}`")

    add("\n## Skills invoked")
    add("- " + (", ".join(f"{k} x{v}" for k, v in skills.most_common()) if skills else "none detected"))

    add("\n## Time & tokens by skill invocation")
    if windows:
        add("| skill | # | wall time | input tok | output tok | tool calls | subagent (n, billed) |")
        add("| --- | --- | --- | --- | --- | --- | --- |")
        for window in windows:
            sub = f"{window['sub_count']}, {human(window['sub_billed'])}" if window["sub_count"] else "-"
            add(
                f"| {window['name']} | {window['seq']} | {duration(window['ms'])} | "
                f"{human(window['input'])} | {human(window['output'])} | {window['tool_calls']} | {sub} |"
            )
    else:
        add("- no Skill invocations or slash-commands detected")

    errors = [c for c in calls if c["error"]]
    add(f"\n## Failed tool calls: {len(errors)}")
    for call in errors[:top]:
        head = (call.get("result_head") or "").replace("\n", " ")[:120]
        add(f"- {call['name']} `{call['label'][:60]}` -> {head}")

    return "\n".join(out)


def list_sessions(project, limit):
    directory = PROJECTS_DIR / encode_project(project) if project else None
    if directory and not directory.is_dir():
        return f"No transcripts for {project} (looked in {directory})"
    files = sorted(
        (directory or PROJECTS_DIR).glob("*.jsonl" if directory else "*/*.jsonl"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )[:limit]
    lines = ["| modified | size | session | title |", "| --- | --- | --- | --- |"]
    for file in files:
        stat = file.stat()
        title = ""
        try:
            with open(file, encoding="utf-8") as handle:
                for _ in range(5):
                    line = handle.readline()
                    if not line:
                        break
                    record = json.loads(line)
                    if record.get("type") == "custom-title":
                        title = record.get("customTitle", "")
                        break
        except (OSError, json.JSONDecodeError):
            pass
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"| {modified} | {stat.st_size // 1024}KB | {file} | {title} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", nargs="?", help="path to a session .jsonl transcript")
    parser.add_argument("--list", action="store_true", help="list recent session transcripts")
    parser.add_argument("--project", help="project cwd to scope --list to")
    parser.add_argument("--limit", type=int, default=15, help="rows for --list")
    parser.add_argument("--top", type=int, default=10, help="rows per ranked table")
    args = parser.parse_args()

    if args.list:
        print(list_sessions(args.project, args.limit))
        return 0

    if not args.session:
        parser.error("a session transcript path is required (or use --list)")

    path = Path(args.session).expanduser()
    if not path.is_file():
        print(f"Not a file: {path}", file=sys.stderr)
        return 1

    print(render(path, load(path), args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
