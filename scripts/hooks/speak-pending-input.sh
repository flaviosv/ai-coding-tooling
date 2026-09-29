#!/usr/bin/env bash
set -uo pipefail

# Claude Code hook that speaks (macOS `say`) when a session is blocked on the
# user: a permission prompt, an MCP elicitation form, AskUserQuestion, or plan
# approval; and, separately, when a session goes idle (its turn ends). A single
# machine-wide marker limits input alerts to one alert plus one reminder
# REMINDER_SECONDS later, then silence until the user is back: a prompt in any
# session, or the blocked session resuming (its next tool result or turn end),
# clears the marker and kills a still-pending reminder.
# Does nothing where `say` is unavailable or in headless (SDK / `claude -p`)
# sessions. Always exits 0.

REMINDER_SECONDS=900
MARKER=/tmp/claude-speak-pending-input
REMINDER_TAG=claude-speak-pending-input-reminder

command -v say >/dev/null 2>&1 || exit 0
case "${CLAUDE_CODE_ENTRYPOINT:-}" in sdk-*) exit 0 ;; esac

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
  nohup say "$msg" >/dev/null 2>&1 </dev/null &
  nohup bash -c 'sleep "$1" && say "$2"' "$REMINDER_TAG" "$REMINDER_SECONDS" "$msg" >/dev/null 2>&1 </dev/null &
}

cancel() {
  pkill -f "$REMINDER_TAG" 2>/dev/null
  rm -f "$MARKER"
}

cancel_own() {
  [ -e "$MARKER" ] && [ "$(head -1 "$MARKER")" = "$session" ] && cancel
}

# Spoken once, with no reminder, and skipped while an input alert is armed.
announce_idle() {
  [ -e "$MARKER" ] && return 0
  nohup say "Claude Code session $(session_name) got idle." >/dev/null 2>&1 </dev/null &
}

case "$event" in
  Notification|PreToolUse) arm ;;
  UserPromptSubmit) [ -e "$MARKER" ] && cancel ;;
  PostToolUse|PostToolUseFailure) cancel_own ;;
  Stop) cancel_own; announce_idle ;;
esac
exit 0
