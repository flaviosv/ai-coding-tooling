#!/usr/bin/env python3
"""
review-token-usage.py — measure real token cost of code-review / tests-code-review
dispatches from Claude Code's local session transcripts.

Not part of any project repo — cross-project investigative tooling, lives under
~/.claude/tools/. Reports RAW TOKEN COUNTS (input/output/cache_creation/cache_read),
not dollar cost, since the constraint that matters is the subscription's token-based
rate-limit window, not billing.

Usage:
    python3 ~/.claude/tools/review-token-usage.py [project_dir ...] [--json out.jsonl]

    project_dir: a directory under ~/.claude/projects/ (or any dir with the same
                 <session>.jsonl + <session>/subagents/ layout). If omitted, defaults
                 to the three recargapay project dirs used for the initial baseline.

Detection heuristic (validated against real sessions 2026-08-08):
  - "Skill" tool_use with input.skill in {code-review, tests-code-review} marks a
    direct-invocation dispatch.
  - A depth-1 "Agent" spawn whose description matches "^Run (code-review|
    tests-code-review) on" is a ship-spec dispatcher-wrapper (adds a real cost layer
    with no reviewing of its own — see the ship-spec dispatcher-wrapper finding).
  - A dimension-reviewer agent is any spawn (any depth) whose description matches a
    known dimension name, excluding "Execute*/Verify*/Re-verify*/Fix*" agents (those
    belong to unrelated tlc-spec-driven work in the same session).
  - Any agent that is a descendant (via parentAgentId) of a detected root but doesn't
    itself match a dimension name (e.g. a research-helper spawned by a dimension
    agent) is attributed to its nearest classified ancestor's bucket.
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

DEFAULT_DIRS = [
    "~/.claude/projects/-Users-flaviostudart-Projects-Personal-tests-recargapay",
    "~/.claude/projects/-Users-flaviostudart-Projects-Personal-tests-recargapay-worktrees-feature-6-reimbursement-consumer",
    "~/.claude/projects/-Users-flaviostudart-Projects-Personal-tests-recargapay-worktrees-feature-7-reimbursement-get-put",
]

DISPATCHER_RE = re.compile(r"^Run (code-review|tests-code-review)\b", re.I)
DIMENSION_RE = re.compile(
    r"(architecture|security|performance|code quality|regression|"
    r"requirements? trace\w*|coverage|clarity|isolation|maintainability|"
    r"gap[- ]?detect\w*)\b.*(review|detect)|"
    r"(review\b.*(architecture|security|performance|code quality|regression|"
    r"requirements? trace\w*|coverage|clarity|isolation|maintainability))",
    re.I,
)
EXCLUDE_RE = re.compile(r"^(Execute (batch|GET|PUT)|Verify |Re-verify|Fix )", re.I)

USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def zero_usage():
    return {k: 0 for k in USAGE_FIELDS}


def add_usage(a, b):
    for k in USAGE_FIELDS:
        a[k] += b.get(k, 0)


def sum_total(u):
    return sum(u.values())


def classify(description):
    if not description:
        return "unrelated"
    if EXCLUDE_RE.match(description):
        return "unrelated"
    if DISPATCHER_RE.match(description):
        return "dispatcher"
    if DIMENSION_RE.search(description):
        return "dimension"
    return "unrelated"


def load_jsonl_usage_by_id(path):
    """Return {message_id: usage_dict} deduped, and (min_ts, max_ts) seen."""
    by_id = {}
    min_ts, max_ts = None, None
    if not path.exists():
        return by_id, (None, None)
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = obj.get("timestamp")
            if ts:
                if min_ts is None or ts < min_ts:
                    min_ts = ts
                if max_ts is None or ts > max_ts:
                    max_ts = ts
            msg = obj.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            mid = msg.get("id")
            usage = msg.get("usage")
            if not mid or not usage:
                continue
            if mid not in by_id:
                u = zero_usage()
                for k in USAGE_FIELDS:
                    u[k] = usage.get(k, 0)
                by_id[mid] = (u, ts)
    return by_id, (min_ts, max_ts)


REPORT_HEADER_RE = re.compile(
    # A real report header has no "<...>" placeholder syntax — SKILL.md's own
    # template/example text ("# <branch or TASK-ID> — Code Review") does, and
    # gets echoed into context whenever the orchestrator reads the skill file,
    # so excluding placeholder brackets is required to avoid false-positive
    # matches on documentation text rather than an actual completed report.
    r"^#\s+(?!.*[<>]).+—\s*(Code Review|Test Code Review)\s*$", re.MULTILINE
)


def find_skill_and_agent_tool_uses(session_path):
    """Scan orchestrator transcript for Skill/Agent tool_use blocks, and for
    Step 8 report-header text blocks (the definitive end-of-review marker)."""
    skill_calls = []  # (timestamp, skill_name)
    agent_spawns = {}  # toolUseId -> (timestamp, description)
    report_headers = []  # (timestamp, report_type)
    with open(session_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = obj.get("timestamp")
            msg = obj.get("message") or {}
            for block in msg.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    name = block.get("name")
                    if name == "Skill":
                        skill = (block.get("input") or {}).get("skill")
                        if skill in ("code-review", "tests-code-review"):
                            skill_calls.append((ts, skill))
                    elif name == "Agent":
                        desc = (block.get("input") or {}).get("description")
                        agent_spawns[block.get("id")] = (ts, desc)
                elif block.get("type") == "text":
                    m = REPORT_HEADER_RE.search(block.get("text") or "")
                    if m:
                        report_headers.append((ts, m.group(1)))
    return skill_calls, agent_spawns, report_headers


def pair_skill_windows(skill_calls, report_headers):
    """Pair each Skill invocation with the nearest matching report header
    that follows it — the definitive end of that review's orchestrator work
    (Step 8 consolidation happens in that same turn)."""
    windows = []  # (start_ts, end_ts, skill_name, anchored)
    used_headers = set()
    skill_to_report_type = {
        "code-review": "Code Review",
        "tests-code-review": "Test Code Review",
    }
    for ts, skill in sorted(skill_calls):
        wanted = skill_to_report_type.get(skill)
        candidates = [
            (hts, htype)
            for i, (hts, htype) in enumerate(report_headers)
            if i not in used_headers and htype == wanted and hts and hts > ts
        ]
        if candidates:
            end_ts, _ = min(candidates)
            used_headers.add(report_headers.index((end_ts, wanted)))
            windows.append((ts, end_ts, skill, True))
        else:
            windows.append((ts, None, skill, False))
    return windows


def analyze_session(session_path):
    session_dir = session_path.parent / session_path.stem
    subagents_dir = session_dir / "subagents"
    if not subagents_dir.exists():
        return None

    skill_calls, agent_spawns, report_headers = find_skill_and_agent_tool_uses(session_path)

    # Load all subagent meta + agent id
    agents = {}  # agent_id -> {meta, path}
    for meta_path in subagents_dir.glob("agent-*.meta.json"):
        agent_id = meta_path.stem.replace("agent-", "").replace(".meta", "")
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            continue
        jsonl_path = subagents_dir / f"agent-{agent_id}.jsonl"
        agents[agent_id] = {"meta": meta, "path": jsonl_path}

    if not agents:
        return None

    # Determine own classification and resolved bucket (with ancestor fallback)
    memo = {}

    def resolve_bucket(agent_id, seen=None):
        if agent_id in memo:
            return memo[agent_id]
        seen = seen or set()
        if agent_id in seen:  # cycle guard
            return "unrelated"
        seen.add(agent_id)
        meta = agents[agent_id]["meta"]
        own = classify(meta.get("description"))
        if own != "unrelated":
            memo[agent_id] = own
            return own
        parent = meta.get("parentAgentId")
        if parent and parent in agents:
            bucket = resolve_bucket(parent, seen)
            memo[agent_id] = bucket
            return bucket
        memo[agent_id] = "unrelated"
        return "unrelated"

    buckets = defaultdict(lambda: zero_usage())
    dimension_agent_count = 0
    dispatcher_agent_count = 0
    nested_helper_count = 0
    included_ids = []
    session_max_ts = None

    for agent_id, info in agents.items():
        bucket = resolve_bucket(agent_id)
        if bucket == "unrelated":
            continue
        included_ids.append(agent_id)
        own = classify(info["meta"].get("description"))
        if own == "dimension":
            dimension_agent_count += 1
        elif own == "dispatcher":
            dispatcher_agent_count += 1
        else:
            nested_helper_count += 1

        by_id, (mn, mx) = load_jsonl_usage_by_id(info["path"])
        for u, _ in by_id.values():
            add_usage(buckets[bucket], u)
        if mx and (session_max_ts is None or mx > session_max_ts):
            session_max_ts = mx

    if not included_ids:
        return None

    # Orchestrator scoped window(s). Preferred: anchor each Skill invocation to
    # its own Step-8 report-header turn — the definitive end of that review's
    # orchestrator work (cache_read at that turn reflects the full context built
    # up through consolidation, which legitimately belongs to the review). This
    # avoids guessing from agent-spawn timestamps, which undercounts whenever
    # Step 7 (await) + Step 8 (consolidation) take meaningfully longer than the
    # slowest subagent's own transcript.
    skill_windows = pair_skill_windows(skill_calls, report_headers)
    anchored_windows = [(s, e) for s, e, _, ok in skill_windows if ok]
    window_anchor = "report-header"

    if anchored_windows:
        windows = anchored_windows
    else:
        # Fallback (e.g. ship-spec-nested: Skill is invoked inside a nested
        # dispatcher subagent, not visible at this transcript level) — use
        # agent-spawn timestamps, capped before the next unrelated Agent spawn.
        window_anchor = "agent-spawn-fallback"
        candidate_starts = [ts for ts, _ in skill_calls if ts]
        for agent_id in included_ids:
            tool_use_id = agents[agent_id]["meta"].get("toolUseId")
            spawn = agent_spawns.get(tool_use_id)
            if spawn and spawn[0]:
                candidate_starts.append(spawn[0])
        if not candidate_starts:
            return None
        start_ts = min(candidate_starts)
        end_ts = session_max_ts or start_ts
        unrelated_spawn_ts_after_end = [
            ts
            for tool_use_id, (ts, desc) in agent_spawns.items()
            if ts and ts > end_ts and classify(desc) == "unrelated"
        ]
        cap_ts = min(unrelated_spawn_ts_after_end) if unrelated_spawn_ts_after_end else None
        windows = [(start_ts, cap_ts if cap_ts else end_ts)]

    def in_any_window(ts):
        return any(s <= ts <= e for s, e in windows if e is not None)

    orch_by_id, _ = load_jsonl_usage_by_id(session_path)
    orch_usage = zero_usage()
    for mid, (u, ts) in orch_by_id.items():
        if ts and in_any_window(ts):
            add_usage(orch_usage, u)

    start_ts = min(s for s, _ in windows)
    end_ts = max(e for _, e in windows if e is not None)

    skills_seen = sorted({s for _, s in skill_calls}) or (
        ["code-review", "tests-code-review"]
        if dispatcher_agent_count >= 2
        else ["unknown"]
    )
    pattern = "ship-spec-nested" if dispatcher_agent_count > 0 else "direct-invocation"

    grand_total = sum_total(orch_usage) + sum(sum_total(v) for v in buckets.values())

    return {
        "session": session_path.stem,
        "path": str(session_path),
        "skills": skills_seen,
        "pattern": pattern,
        "window": [start_ts, end_ts],
        "window_anchor": window_anchor,
        "window_count": len(windows),
        "dispatcher_agents": dispatcher_agent_count,
        "dimension_agents": dimension_agent_count,
        "nested_helper_agents": nested_helper_count,
        "orchestrator_usage": orch_usage,
        "orchestrator_total": sum_total(orch_usage),
        "buckets": {k: dict(v) for k, v in buckets.items()},
        "bucket_totals": {k: sum_total(v) for k, v in buckets.items()},
        "grand_total": grand_total,
    }


def main():
    args = sys.argv[1:]
    json_out = None
    if "--json" in args:
        i = args.index("--json")
        json_out = args[i + 1]
        del args[i : i + 2]

    dirs = args or DEFAULT_DIRS
    results = []
    for d in dirs:
        p = Path(d).expanduser()
        if not p.exists():
            print(f"skip (not found): {p}", file=sys.stderr)
            continue
        for session_path in sorted(p.glob("*.jsonl")):
            r = analyze_session(session_path)
            if r:
                results.append(r)

    if not results:
        print("No code-review/tests-code-review dispatch sessions found.")
        return

    grand_total_all = 0
    for r in results:
        print(f"\n=== {r['session']} ({r['pattern']}) ===")
        print(f"  skills: {', '.join(r['skills'])}")
        print(
            f"  window: {r['window'][0]} .. {r['window'][1]}"
            f"  ({r['window_anchor']}, {r['window_count']} window(s))"
        )
        print(
            f"  agents: {r['dispatcher_agents']} dispatcher, "
            f"{r['dimension_agents']} dimension, {r['nested_helper_agents']} nested-helper"
        )
        print(f"  orchestrator: {r['orchestrator_total']:>12,} tokens  {r['orchestrator_usage']}")
        for bucket, total in r["bucket_totals"].items():
            print(f"  {bucket:>12}: {total:>12,} tokens  {r['buckets'][bucket]}")
        print(f"  GRAND TOTAL:  {r['grand_total']:>12,} tokens")
        grand_total_all += r["grand_total"]

    print(f"\n{'=' * 60}")
    print(f"Sessions analyzed: {len(results)}")
    print(f"Combined grand total: {grand_total_all:,} tokens")

    if json_out:
        with open(json_out, "w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        print(f"Raw results written to {json_out}")


if __name__ == "__main__":
    main()
