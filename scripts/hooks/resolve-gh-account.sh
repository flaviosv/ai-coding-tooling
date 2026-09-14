#!/usr/bin/env bash
set -uo pipefail

# Claude Code hook (SessionStart + CwdChanged) that scopes this session's gh
# calls to the GitHub account the current repo belongs to, when more than one
# account is logged in to gh. The account is resolved purely from the repo's
# own git/GitHub data (SSH key identity, remote owner, push access) and
# exported as GH_TOKEN through CLAUDE_ENV_FILE, so gh never depends on the
# machine-global "active account" another process can switch at any time.
# Folders that are not GitHub repos are never touched. Always exits 0.

BUDGET_SECONDS=8
HOOK_MARKER=GH_ACCOUNT_HOOK
CLEAR_LINE="if [ -n \"\${$HOOK_MARKER:-}\" ]; then unset GH_TOKEN $HOOK_MARKER; fi"

input="$(cat 2>/dev/null || true)"
event="$(printf '%s' "$input" | jq -r '.hook_event_name // empty' 2>/dev/null || true)"
target_dir="$(printf '%s' "$input" | jq -r '.new_cwd // .cwd // empty' 2>/dev/null || true)"
old_dir="$(printf '%s' "$input" | jq -r '.old_cwd // empty' 2>/dev/null || true)"
[ -z "$target_dir" ] && target_dir="$PWD"

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

# Runs a command, killing it once the given seconds (capped by what is left of
# the overall budget) elapse. macOS has no `timeout` binary, and a SIGALRM
# approach does not work because gh (Go) ignores that signal.
bounded() {
  local secs="$1"; shift
  local left=$((BUDGET_SECONDS - SECONDS))
  [ "$left" -lt "$secs" ] && secs="$left"
  [ "$secs" -le 0 ] && return 124
  "$@" &
  local pid=$!
  ( sleep "$secs"; kill -TERM "$pid" 2>/dev/null ) >/dev/null 2>&1 &
  local watchdog=$!
  wait "$pid"
  local rc=$?
  kill "$watchdog" 2>/dev/null
  wait "$watchdog" 2>/dev/null
  return "$rc"
}

write_env() { [ -n "${CLAUDE_ENV_FILE:-}" ] && printf '%s\n' "$1" >> "$CLAUDE_ENV_FILE"; }

# SessionStart stdout becomes Claude's context; CwdChanged stdout does not, so
# there the message can only surface as a user-facing systemMessage.
say() {
  if [ "$event" = "CwdChanged" ]; then
    jq -cn --arg m "$1" '{systemMessage: $m}'
  else
    printf '%s\n' "$1"
  fi
}

leave_untouched() {
  [ "$event" = "CwdChanged" ] && write_env "$CLEAR_LINE"
  exit 0
}

command -v git >/dev/null 2>&1 || exit 0
command -v jq >/dev/null 2>&1 || exit 0
git -C "$target_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || leave_untouched

if [ "$event" = "CwdChanged" ] && [ -n "$old_dir" ]; then
  old_top="$(git -C "$old_dir" rev-parse --show-toplevel 2>/dev/null || true)"
  new_top="$(git -C "$target_dir" rev-parse --show-toplevel 2>/dev/null || true)"
  [ -n "$old_top" ] && [ "$old_top" = "$new_top" ] && exit 0
fi

# Sets url_scheme, url_user, url_host, url_port, url_path from a remote URL.
parse_url() {
  url_scheme="" url_user="" url_host="" url_port="" url_path=""
  local re_scheme='^(ssh|https?)://(([^@/]+)@)?([^:/]+)(:([0-9]+))?/(.+)$'
  local re_scp='^(([^@/]+)@)?([^:/]+):(.+)$'
  if [[ "$1" =~ $re_scheme ]]; then
    url_scheme="${BASH_REMATCH[1]}" url_user="${BASH_REMATCH[3]}" url_host="${BASH_REMATCH[4]}"
    url_port="${BASH_REMATCH[6]}" url_path="${BASH_REMATCH[7]}"
  elif [[ "$1" != *://* && "$1" =~ $re_scp ]]; then
    url_scheme="ssh" url_user="${BASH_REMATCH[2]}" url_host="${BASH_REMATCH[3]}" url_path="${BASH_REMATCH[4]}"
  fi
}

resolved_host() {
  parse_url "$1"
  [ -z "$url_host" ] && return
  if [ "$url_scheme" = "ssh" ]; then
    lower "$(ssh -G "$url_host" 2>/dev/null | awk '$1 == "hostname" { print $2; exit }')"
  else
    lower "$url_host"
  fi
}

is_github_url() {
  case "$(resolved_host "$1")" in
    github.com|ssh.github.com) return 0 ;;
    *) return 1 ;;
  esac
}

remotes="$(git -C "$target_dir" remote 2>/dev/null || true)"
remote_url=""
if printf '%s\n' "$remotes" | grep -qx origin; then
  remote_url="$(git -C "$target_dir" remote get-url origin 2>/dev/null || true)"
elif [ -n "$remotes" ] && [ "$(printf '%s\n' "$remotes" | wc -l | tr -d ' ')" -eq 1 ]; then
  remote_url="$(git -C "$target_dir" remote get-url "$remotes" 2>/dev/null || true)"
else
  github_urls=""
  for r in $remotes; do
    u="$(git -C "$target_dir" remote get-url "$r" 2>/dev/null || true)"
    [ -n "$u" ] && is_github_url "$u" && github_urls="${github_urls}${u}"$'\n'
  done
  [ "$(printf '%s' "$github_urls" | grep -c .)" -eq 1 ] && remote_url="${github_urls%$'\n'}"
fi

[ -n "$remote_url" ] && is_github_url "$remote_url" || leave_untouched

parse_url "$remote_url"
repo_path="${url_path#/}"
repo_path="${repo_path%/}"
repo_path="${repo_path%.git}"
owner="" repo=""
if [[ "$repo_path" =~ ^([^/]+)/([^/]+)$ ]]; then
  owner="${BASH_REMATCH[1]}" repo="${BASH_REMATCH[2]}"
fi

command -v gh >/dev/null 2>&1 || exit 0
logins="$(bounded 3 env -u GH_TOKEN -u GITHUB_TOKEN gh auth status --json hosts 2>/dev/null \
  | jq -r '.hosts["github.com"][]?.login // empty' 2>/dev/null | sort -u || true)"
[ "$(printf '%s' "$logins" | grep -c .)" -le 1 ] && exit 0

# Echoes the logged-in login matching $1 case-insensitively, if any.
match_login() {
  local want l
  want="$(lower "$1")"
  for l in $logins; do
    [ "$(lower "$l")" = "$want" ] && { printf '%s' "$l"; return 0; }
  done
  return 1
}

resolve() {
  local login="$1" signal="$2"
  if [[ ! "$login" =~ ^[A-Za-z0-9-]+$ ]]; then return; fi
  write_env "if __gh_t=\"\$(gh auth token --user '$login' 2>/dev/null)\"; then export GH_TOKEN=\"\$__gh_t\" $HOOK_MARKER=1; else $CLEAR_LINE; fi; unset __gh_t"
  say "gh calls in this session run as $login (resolved from $signal)."
  exit 0
}

if [ "$url_scheme" = "ssh" ]; then
  ssh_args=(-T -o BatchMode=yes -o ConnectTimeout=3)
  [ -n "$url_port" ] && ssh_args+=(-p "$url_port")
  greeting="$(bounded 4 ssh "${ssh_args[@]}" "${url_user:-git}@$url_host" 2>&1 </dev/null || true)"
  ssh_name="$(printf '%s\n' "$greeting" | sed -n 's/^Hi \([^!]*\)!.*/\1/p' | head -n 1)"
  if [ -n "$ssh_name" ] && login="$(match_login "$ssh_name")"; then
    resolve "$login" "the SSH key identity for $url_host"
  fi
fi

if [ -n "$owner" ] && login="$(match_login "$owner")"; then
  resolve "$login" "the remote owner $owner"
fi

if [ -n "$owner" ]; then
  pushers=""
  for l in $logins; do
    can_push="$(
      GH_TOKEN="$(gh auth token --user "$l" 2>/dev/null)" || exit 0
      export GH_TOKEN
      bounded 3 gh api "repos/$owner/$repo" --jq .permissions.push 2>/dev/null
    )" || true
    [ "$can_push" = "true" ] && pushers="${pushers} $l"
  done
  pushers="${pushers# }"
  if [ -n "$pushers" ] && [ "${pushers// /}" = "$pushers" ]; then
    resolve "$pushers" "push access to $owner/$repo"
  fi
fi

[ "$event" = "CwdChanged" ] && write_env "$CLEAR_LINE"
say "The gh account for this repo is unresolved (candidates: $(printf '%s' "$logins" | paste -sd ',' - | sed 's/,/, /g')). Ask the user which account to use before any gh call or HTTPS git push, then scope those calls with GH_TOKEN=\"\$(gh auth token --user <login>)\". Never run gh auth switch."
exit 0
