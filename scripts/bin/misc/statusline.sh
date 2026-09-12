#!/bin/sh
# Claude Code statusLine
# Format: [Model (effort) - dir (branch)] Context:X% | Usage:X% (resets in Xh Xm)

input=$(cat)

# ANSI colors (printf-safe)
RESET=$(printf '\033[0m')
DIM=$(printf '\033[2m')
BOLD=$(printf '\033[1m')
CYAN=$(printf '\033[96m')
MAGENTA=$(printf '\033[95m')
GREEN=$(printf '\033[92m')
YELLOW=$(printf '\033[93m')
RED=$(printf '\033[91m')
WHITE=$(printf '\033[97m')
ESC=$(printf '\033')

# Extract all fields in a single jq call
parsed=$(echo "$input" | jq -r '
  [
    (.model.display_name // ""),
    (
      if (.effort | type) == "object" and .effort.level != null and .effort.level != "" then .effort.level
      elif (.effort | type) == "string" and .effort != "" then .effort
      elif .thinking_level != null and .thinking_level != "" then .thinking_level
      elif .reasoning_effort != null and .reasoning_effort != "" then .reasoning_effort
      elif (.output_style.name != null and .output_style.name != "" and .output_style.name != "default") then .output_style.name
      else ""
      end
    ),
    (.workspace.current_dir // .cwd // ""),
    (if .context_window.used_percentage == null then "" else (.context_window.used_percentage | round | tostring) end),
    (if .rate_limits.five_hour.used_percentage == null then "" else (.rate_limits.five_hour.used_percentage | round | tostring) end),
    (.rate_limits.five_hour.resets_at // "")
  ] | join("\t")
' 2>/dev/null)

model=$(printf '%s' "$parsed" | cut -f1)
effort=$(printf '%s' "$parsed" | cut -f2)
dir=$(printf '%s' "$parsed" | cut -f3)
ctx_used=$(printf '%s' "$parsed" | cut -f4)
five_hour=$(printf '%s' "$parsed" | cut -f5)
five_hour_resets=$(printf '%s' "$parsed" | cut -f6)

# Normalize "null" strings that jq emits for tostring of null
[ "$ctx_used" = "null" ] && ctx_used=""
[ "$five_hour" = "null" ] && five_hour=""

dir_name=$(basename "$dir")

# Compute "resets in Xh Xm" — resets_at is a Unix timestamp
resets_in=""
if [ -n "$five_hour_resets" ]; then
  now=$(date +%s)
  diff=$((five_hour_resets - now))
  if [ "$diff" -gt 0 ]; then
    hours=$((diff / 3600))
    mins=$(((diff % 3600) / 60))
    if [ "$hours" -gt 0 ]; then
      resets_in=" ${DIM}(resets in ${hours}h ${mins}m)${RESET}"
    else
      resets_in=" ${DIM}(resets in ${mins}m)${RESET}"
    fi
  fi
fi

# Git branch — stderr suppressed
git_part=""
if git -C "$dir" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  git_branch=$(git -C "$dir" symbolic-ref --short HEAD 2>/dev/null || git -C "$dir" rev-parse --short HEAD 2>/dev/null)
  if [ -n "$git_branch" ]; then
    git_part=" ${DIM}(${RESET}${YELLOW}${git_branch}${RESET}${DIM})${RESET}"
  fi
fi

# Pick color by percentage threshold
pct_color() {
  # Strip any decimal part defensively so the integer test can never error to stderr
  pct=${1%%.*}
  if [ -z "$pct" ]; then printf '%s' "$DIM"; return; fi
  if [ "$pct" -lt 50 ] 2>/dev/null; then printf '%s' "$GREEN"
  elif [ "$pct" -lt 80 ] 2>/dev/null; then printf '%s' "$YELLOW"
  else printf '%s' "$RED"
  fi
}

# Model + effort
if [ -n "$model" ] && [ -n "$effort" ]; then
  header="${DIM}[${RESET}${BOLD}${CYAN}${model}${RESET} ${DIM}(${RESET}${BOLD}${MAGENTA}${effort}${RESET}${DIM})${RESET}"
elif [ -n "$model" ]; then
  header="${DIM}[${RESET}${BOLD}${CYAN}${model}${RESET}"
else
  header="${DIM}["
fi

# Dir + branch (inside brackets)
dir_part=" ${DIM}-${RESET} ${GREEN}${dir_name}${RESET}${git_part}${DIM}]${RESET}"

# Stats: Context | Usage (resets in ...)
stats=""
if [ -n "$ctx_used" ]; then
  color=$(pct_color "$ctx_used")
  stats="${stats} ${WHITE}Context:${RESET}${color}${ctx_used}%${RESET}"
fi
if [ -n "$five_hour" ]; then
  color=$(pct_color "$five_hour")
  sep=""
  [ -n "$stats" ] && sep=" ${DIM}|${RESET}"
  stats="${stats}${sep} ${WHITE}Usage:${RESET}${color}${five_hour}%${RESET}${resets_in}"
fi

printf '%s%s%s' "$header" "$dir_part" "$stats"
