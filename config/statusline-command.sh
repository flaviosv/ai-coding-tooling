#!/bin/sh
# Claude Code statusLine
# Format: [Model (effort) - 📁 dir (branch)] ctx:X% 5h:X%

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

# Model display name
model=$(echo "$input" | jq -r '.model.display_name // empty')

# Effort level — .effort may be an object {level: "..."} or a plain string
effort=$(echo "$input" | jq -r '
  if (.effort | type) == "object" and .effort.level != null and .effort.level != "" then .effort.level
  elif (.effort | type) == "string" and .effort != "" then .effort
  elif .thinking_level != null and .thinking_level != "" then .thinking_level
  elif .reasoning_effort != null and .reasoning_effort != "" then .reasoning_effort
  elif (.output_style.name != null and .output_style.name != "" and .output_style.name != "default") then .output_style.name
  else empty
  end')

# Current directory basename
dir=$(echo "$input" | jq -r '.workspace.current_dir // .cwd')
dir_name=$(basename "$dir")

# Git branch
git_part=""
if git -C "$dir" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  git_branch=$(git -C "$dir" symbolic-ref --short HEAD 2>/dev/null || git -C "$dir" rev-parse --short HEAD 2>/dev/null)
  if [ -n "$git_branch" ]; then
    git_part=" ${DIM}(${RESET}${YELLOW}${git_branch}${RESET}${DIM})${RESET}"
  fi
fi

# Context window used percentage
ctx_used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# 5h rate limit used percentage
five_hour=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')

# Pick color by percentage threshold
pct_color() {
  pct="$1"
  if [ -z "$pct" ]; then printf '%s' "$DIM"; return; fi
  if [ "$pct" -lt 50 ]; then printf '%s' "$GREEN"
  elif [ "$pct" -lt 80 ]; then printf '%s' "$YELLOW"
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
dir_part=" ${DIM}-${RESET} 📁 ${GREEN}${dir_name}${RESET}${git_part}${DIM}]${RESET}"

WHITE=$(printf '\033[97m')

# Stats outside brackets
stats=""
if [ -n "$ctx_used" ]; then
  color=$(pct_color "$ctx_used")
  stats="${stats} ${WHITE}ctx:${RESET}${color}${ctx_used}%${RESET}"
fi
if [ -n "$five_hour" ]; then
  color=$(pct_color "$five_hour")
  stats="${stats} ${WHITE}5h:${RESET}${color}${five_hour}%${RESET}"
fi

printf '%s%s%s' "$header" "$dir_part" "$stats"
