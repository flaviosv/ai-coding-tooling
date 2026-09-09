#!/usr/bin/env bash
set -euo pipefail

# Claude Code hook (SessionStart + UserPromptSubmit) that verifies direnv,
# not this script, has correctly resolved credentials for the current
# directory. Policy (which directory needs which credential) lives entirely
# in .envrc files managed by direnv — this script only asks direnv what it
# already knows and reacts to that, so it never re-implements a directory
# walk of its own.

input="$(cat 2>/dev/null || true)"
target_dir="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null || true)"
[ -z "$target_dir" ] && target_dir="$PWD"

if ! command -v direnv >/dev/null 2>&1; then
  {
    echo "BLOCKED: direnv is not installed or not hooked into your shell."
    echo "This session cannot verify which Anthropic credential is active."
    echo "Run: brew install direnv"
    echo "Then add as the LAST line of ~/.zshrc: eval \"\$(direnv hook zsh)\""
    echo "Then open a new terminal and try again."
  } >&2
  exit 2
fi

status_json="$(cd "$target_dir" 2>/dev/null && direnv status --json 2>/dev/null || true)"

if [ -n "$status_json" ] && echo "$status_json" | jq -e . >/dev/null 2>&1; then
  found_allowed="$(echo "$status_json" | jq -r '.state.foundRC.allowed // "none"')"
  rc_path="$(echo "$status_json" | jq -r '.state.foundRC.path // ""')"
else
  # Fallback: plain-text parsing (direnv --json unavailable/unreliable).
  status_text="$(cd "$target_dir" 2>/dev/null && direnv status 2>/dev/null || true)"
  rc_path="$(echo "$status_text" | grep "^Found RC path" | awk '{print $NF}')"
  if [ -z "$rc_path" ]; then
    found_allowed="none"
  else
    # direnv's AllowStatus has no String()/JSON marshaler: it prints the raw
    # int (0=Allowed, 1=NotAllowed, 2=Denied) even in text mode.
    found_allowed="$(echo "$status_text" | grep "^Found RC allowed" | awk '{print $NF}')"
  fi
fi

key_present=0
[ -n "${ANTHROPIC_API_KEY:-}" ] && key_present=1
[ -n "${ANTHROPIC_AUTH_TOKEN:-}" ] && key_present=1

if [ "$found_allowed" = "none" ]; then
  # No .envrc found anywhere upward: unmanaged directory, safe default.
  if [ "$key_present" -eq 1 ]; then
    {
      echo "BLOCKED: a company credential (ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN) is"
      echo "active in an unmanaged directory (no .envrc found upward from $target_dir)."
      echo "Unset it, or cd into a directory governed by an approved .envrc."
    } >&2
    exit 2
  fi
  exit 0
fi

if [ "$found_allowed" != "0" ]; then
  # .envrc exists but is not trusted (NotAllowed=1 or Denied=2).
  {
    echo "BLOCKED: .envrc found at $rc_path but not yet trusted by direnv."
    echo "Run: direnv allow \"$(dirname "$rc_path")\""
  } >&2
  exit 2
fi

# .envrc found and allowed (0) — trust direnv's resolution for this location.
exit 0
