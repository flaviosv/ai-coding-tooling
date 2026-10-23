#!/usr/bin/env bash
set -uo pipefail

# Claude Code hook that speaks (macOS `say`) when a session is blocked on the
# user: a permission prompt, an MCP elicitation form, AskUserQuestion, or plan
# approval; and, separately, when a session goes idle (its turn ends). A single
# machine-wide marker limits input alerts to one alert plus one reminder
# REMINDER_SECONDS later, then silence until the user is back: a prompt in any
# session, or the blocked session resuming (its next tool result or turn end),
# clears the marker and kills a still-pending reminder.
# While any app is recording from a microphone (a call), speech plays at
# CALL_VOLUME instead, via a small Swift helper compiled on first use.
# Does nothing where `say` is unavailable or in headless (SDK / `claude -p`)
# sessions. Always exits 0.

REMINDER_SECONDS=900
MARKER=/tmp/claude-speak-pending-input
REMINDER_TAG=claude-speak-pending-input-reminder
CALL_VOLUME=0.2
SELF="$(realpath "${BASH_SOURCE[0]}")"
MIC_SRC="$(dirname "$SELF")/mic-in-use.swift"
MIC_BIN="$HOME/Library/Caches/claude-speak-pending-input/mic-in-use"

command -v say >/dev/null 2>&1 || exit 0
case "${CLAUDE_CODE_ENTRYPOINT:-}" in sdk-*) exit 0 ;; esac

# Until the helper is built (in the background, on first use), or where swiftc
# is missing, this reports "not in a call", so speech keeps its normal volume.
in_call() {
  if [ ! -x "$MIC_BIN" ] || [ "$MIC_SRC" -nt "$MIC_BIN" ]; then
    command -v swiftc >/dev/null 2>&1 && [ -f "$MIC_SRC" ] && mkdir -p "$(dirname "$MIC_BIN")" &&
      nohup bash -c 'swiftc -O "$1" -o "$2.$$" && mv "$2.$$" "$2"' _ "$MIC_SRC" "$MIC_BIN" >/dev/null 2>&1 </dev/null &
    return 1
  fi
  "$MIC_BIN"
}

speak() {
  if in_call; then
    local dir
    dir="$(mktemp -d)"
    say -o "$dir/speech.aiff" "$1" && afplay -v "$CALL_VOLUME" "$dir/speech.aiff"
    rm -rf "$dir"
  else
    say "$1"
  fi
}

if [ "${1:-}" = "--speak" ]; then speak "$2"; exit 0; fi

input="$(cat 2>/dev/null || true)"
field() { printf '%s' "$input" | jq -r "$1 // empty" 2>/dev/null; }

event="$(field .hook_event_name)"
session="$(field .session_id)"

# The session's /rename title, else its auto-generated title, else the folder.
# Both titles are read from the transcript, whose format is undocumented.
session_name() {
  local transcript name=""
  transcript="$(field .transcript_path)"
  if [ -f "$transcript" ]; then
    name="$(grep '"type":"custom-title"' "$transcript" | tail -1 | jq -r '.customTitle // empty' 2>/dev/null)"
    [ -z "$name" ] && name="$(grep '"type":"ai-title"' "$transcript" | tail -1 | jq -r '.aiTitle // empty' 2>/dev/null)"
  fi
  [ -z "$name" ] && name="$(basename "$(field .cwd)")"
  printf '%s' "$name"
}

arm() {
  ( set -C; printf '%s\n' "$session" > "$MARKER" ) 2>/dev/null || return 0
  local msg
  msg="Claude Code needs your input in the session: $(session_name)."
  nohup "$SELF" --speak "$msg" >/dev/null 2>&1 </dev/null &
  nohup bash -c 'sleep "$1" && "$2" --speak "$3"' "$REMINDER_TAG" "$REMINDER_SECONDS" "$SELF" "$msg" >/dev/null 2>&1 </dev/null &
}

cancel() {
  pkill -f "$REMINDER_TAG" 2>/dev/null
  rm -f "$MARKER"
}

cancel_own() {
  [ -e "$MARKER" ] && [ "$(head -1 "$MARKER")" = "$session" ] && cancel
}

# Spoken once, with no reminder, and skipped while an input alert is armed or a
# Monitor is still running (the session is waiting to be woken, not done).
announce_idle() {
  [ -e "$MARKER" ] && return 0
  local monitors
  monitors="$(field '[.background_tasks[]? | select(.type == "monitor")] | length')"
  [ "${monitors:-0}" -gt 0 ] && return 0
  nohup "$SELF" --speak "Claude Code session $(session_name) got idle." >/dev/null 2>&1 </dev/null &
}

case "$event" in
  Notification|PreToolUse) arm ;;
  UserPromptSubmit) [ -e "$MARKER" ] && cancel ;;
  PostToolUse|PostToolUseFailure) cancel_own ;;
  Stop) cancel_own; announce_idle ;;
esac
exit 0
