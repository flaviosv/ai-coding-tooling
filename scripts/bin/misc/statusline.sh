#!/bin/sh
# Claude Code statusLine
# Token mode (ANTHROPIC_API_KEY set):    [🤖 Model ⚡● (effort) - dir (branch)] 🪟 Context:X% [🟢/⚠️/🚨/💥] | 💰 Cost:$X.XX | 📅 Monthly:X% (resets in ...) | 💾 Cache:X% | 🕒 Time:H:MM:SS
# Subscription mode (no API key):        [🤖 Model ⚡● (effort) - dir (branch)] 🪟 Context:X% [🟢/⚠️/🚨/💥] | ⏱️ Usage:X% (resets in ...) | 💾 Cache:X% | 📆 Weekly:X% (resets in ...) | 🕒 Time:H:MM:SS

input=$(cat)

# ANSI colors (printf-safe)
RESET=$(printf '\033[0m')
DIM=$(printf '\033[38;5;250m')
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
    (.rate_limits.five_hour.resets_at // ""),
    (if .rate_limits.seven_day.used_percentage == null then "" else (.rate_limits.seven_day.used_percentage | round | tostring) end),
    (.rate_limits.seven_day.resets_at // ""),
    (if .rate_limits.spend_limit.used_percentage == null then "" else (.rate_limits.spend_limit.used_percentage | round | tostring) end),
    (.rate_limits.spend_limit.resets_at // ""),
    (if .cost.total_cost_usd == null then "" else (.cost.total_cost_usd | tostring) end),
    (if .cost.total_duration_ms == null then "" else (.cost.total_duration_ms | round | tostring) end),
    (if .fast_mode == null then "" else (.fast_mode | tostring) end),
    (if .prompt_cache.hit_ratio == null then "" else (.prompt_cache.hit_ratio * 100 | round | tostring) end),
    (if .prompt_cache.warm == null then "" else (.prompt_cache.warm | tostring) end),
    (if .prompt_cache.caching_observed == null then "" else (.prompt_cache.caching_observed | tostring) end)
  ] | join("\t")
' 2>/dev/null)

model=$(printf '%s' "$parsed" | cut -f1)
effort=$(printf '%s' "$parsed" | cut -f2)
dir=$(printf '%s' "$parsed" | cut -f3)
ctx_used=$(printf '%s' "$parsed" | cut -f4)
five_hour=$(printf '%s' "$parsed" | cut -f5)
five_hour_resets=$(printf '%s' "$parsed" | cut -f6)
seven_day=$(printf '%s' "$parsed" | cut -f7)
seven_day_resets=$(printf '%s' "$parsed" | cut -f8)
spend_limit=$(printf '%s' "$parsed" | cut -f9)
spend_limit_resets=$(printf '%s' "$parsed" | cut -f10)
cost_usd=$(printf '%s' "$parsed" | cut -f11)
duration_ms=$(printf '%s' "$parsed" | cut -f12)
fast_mode_flag=$(printf '%s' "$parsed" | cut -f13)
cache_hit_ratio=$(printf '%s' "$parsed" | cut -f14)
cache_warm=$(printf '%s' "$parsed" | cut -f15)
cache_observed=$(printf '%s' "$parsed" | cut -f16)

# Normalize "null" strings that jq emits for tostring of null
[ "$ctx_used" = "null" ] && ctx_used=""
[ "$five_hour" = "null" ] && five_hour=""
[ "$seven_day" = "null" ] && seven_day=""
[ "$spend_limit" = "null" ] && spend_limit=""
[ "$cost_usd" = "null" ] && cost_usd=""
[ "$duration_ms" = "null" ] && duration_ms=""
[ "$fast_mode_flag" = "null" ] && fast_mode_flag=""
[ "$cache_hit_ratio" = "null" ] && cache_hit_ratio=""
[ "$cache_warm" = "null" ] && cache_warm=""
[ "$cache_observed" = "null" ] && cache_observed=""

dir_name=$(basename "$dir")

# Token-based (API key) vs subscription session — statusLine has no auth-source
# field, so ANTHROPIC_API_KEY presence is the only local signal available.
token_mode=false
[ -n "$ANTHROPIC_API_KEY" ] && token_mode=true

# " (resets in ...)" from a Unix timestamp, scaling the unit to how far off it is
format_resets() {
  ts="$1"
  [ -z "$ts" ] && return
  now=$(date +%s)
  diff=$((ts - now))
  [ "$diff" -le 0 ] && return
  days=$((diff / 86400))
  hours=$(((diff % 86400) / 3600))
  mins=$(((diff % 3600) / 60))
  if [ "$days" -gt 0 ]; then
    printf ' %s(resets in %dd %dh)%s' "$DIM" "$days" "$hours" "$RESET"
  elif [ "$hours" -gt 0 ]; then
    printf ' %s(resets in %dh %dm)%s' "$DIM" "$hours" "$mins" "$RESET"
  else
    printf ' %s(resets in %dm)%s' "$DIM" "$mins" "$RESET"
  fi
}

# "H:MM:SS" or "MM:SS" from a millisecond duration
format_duration() {
  ms="$1"
  [ -z "$ms" ] && return
  secs=$((ms / 1000))
  h=$((secs / 3600))
  m=$(((secs % 3600) / 60))
  s=$((secs % 60))
  if [ "$h" -gt 0 ]; then
    printf '%d:%02d:%02d' "$h" "$m" "$s"
  else
    printf '%02d:%02d' "$m" "$s"
  fi
}

five_hour_reset_str=$(format_resets "$five_hour_resets")
seven_day_reset_str=$(format_resets "$seven_day_resets")
spend_limit_reset_str=$(format_resets "$spend_limit_resets")
duration_str=$(format_duration "$duration_ms")

# Git branch — stderr suppressed
git_part=""
if git -C "$dir" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  git_branch=$(git -C "$dir" symbolic-ref --short HEAD 2>/dev/null || git -C "$dir" rev-parse --short HEAD 2>/dev/null)
  if [ -n "$git_branch" ]; then
    git_part=" ${DIM}(${RESET}${YELLOW}${git_branch}${RESET}${DIM})${RESET}"
  fi
fi

# Pick color by percentage threshold. direction "high-good" (e.g. cache hit
# ratio) flips the scale so a high percentage reads green instead of red.
pct_color() {
  # Strip any decimal part defensively so the integer test can never error to stderr
  pct=${1%%.*}
  direction="${2:-high-bad}"
  if [ -z "$pct" ]; then printf '%s' "$DIM"; return; fi
  if [ "$direction" = "high-good" ]; then
    if [ "$pct" -ge 75 ] 2>/dev/null; then printf '%s' "$GREEN"
    elif [ "$pct" -ge 50 ] 2>/dev/null; then printf '%s' "$YELLOW"
    else printf '%s' "$RED"
    fi
  else
    if [ "$pct" -lt 50 ] 2>/dev/null; then printf '%s' "$GREEN"
    elif [ "$pct" -lt 80 ] 2>/dev/null; then printf '%s' "$YELLOW"
    else printf '%s' "$RED"
    fi
  fi
}

# Fast mode badge, right after the model name. ⚡ is purely decorative — it's
# an emoji-presentation glyph so terminals always paint it its built-in
# yellow, ignoring ANSI color (see the ● fix above). The actual on/off signal
# stays on ●, a plain text-presentation character that does take the color.
fast_badge=""
if [ "$fast_mode_flag" = "true" ]; then
  fast_badge=" ⚡${GREEN}●${RESET}"
elif [ "$fast_mode_flag" = "false" ]; then
  fast_badge=" ⚡${RED}●${RESET}"
fi

# Model + effort
if [ -n "$model" ] && [ -n "$effort" ]; then
  header="${DIM}[${RESET}🤖 ${BOLD}${CYAN}${model}${RESET}${fast_badge} ${DIM}(${RESET}${BOLD}${MAGENTA}${effort}${RESET}${DIM})${RESET}"
elif [ -n "$model" ]; then
  header="${DIM}[${RESET}🤖 ${BOLD}${CYAN}${model}${RESET}${fast_badge}"
else
  header="${DIM}["
fi

# Dir + branch (inside brackets)
dir_part=" ${DIM}-${RESET} ${GREEN}${dir_name}${RESET}${git_part}${DIM}]${RESET}"

stats=""
append_stat() {
  sep=""
  [ -n "$stats" ] && sep=" ${DIM}|${RESET}"
  stats="${stats}${sep} $1"
}

# Context stat, shared by both modes. Four tiers by used_percentage: calm
# under 20%, yellow warning 20-40%, red warning 40-60%, explosion past 60%
# — real emoji glyphs so the signal is actually visible, unlike a bare ⚠
# character at terminal font size.
ctx_stat=""
if [ -n "$ctx_used" ]; then
  color=$(pct_color "$ctx_used")
  ctx_pct=${ctx_used%%.*}
  if [ "$ctx_pct" -lt 20 ] 2>/dev/null; then tier=" 🟢"
  elif [ "$ctx_pct" -lt 40 ] 2>/dev/null; then tier=" ⚠️"
  elif [ "$ctx_pct" -lt 60 ] 2>/dev/null; then tier=" 🚨"
  else tier=" 💥"
  fi
  ctx_stat="🪟 ${WHITE}Context:${RESET}${color}${ctx_used}%${RESET}${tier}"
fi

# Cache stat, shared by both modes: how much of this session's input tokens
# were served from the prompt cache instead of reprocessed fresh. A low hit
# ratio explains a rising Cost in token mode, and burns the 5h/7d rate-limit
# budget faster in subscription mode — the mechanism (more tokens per
# request) is the same either way. "cold" flags that the next request pays
# the full re-cache price regardless of the session-wide ratio shown.
cache_stat=""
if [ -n "$cache_hit_ratio" ]; then
  color=$(pct_color "$cache_hit_ratio" high-good)
  cold=""
  [ "$cache_warm" = "false" ] && [ "$cache_observed" = "true" ] && cold=" ${DIM}(cold)${RESET}"
  cache_stat="💾 ${WHITE}Cache:${RESET}${color}${cache_hit_ratio}%${RESET}${cold}"
fi

if [ "$token_mode" = true ]; then
  # Context | Cost | Monthly | Cache
  [ -n "$ctx_stat" ] && append_stat "$ctx_stat"
  if [ -n "$cost_usd" ]; then
    # LC_ALL=C keeps the decimal point regardless of the shell's locale —
    # the shell-builtin printf ignores per-call locale overrides and would
    # otherwise mis-parse "12.34" (or render it "12,34") in comma-locales.
    cost_fmt=$(LC_ALL=C awk -v v="$cost_usd" 'BEGIN { printf "%.2f", v }' 2>/dev/null)
    append_stat "💰 ${WHITE}Cost:${RESET}${GREEN}\$${cost_fmt}${RESET}"
  fi
  if [ -n "$spend_limit" ]; then
    color=$(pct_color "$spend_limit")
    append_stat "📅 ${WHITE}Monthly:${RESET}${color}${spend_limit}%${RESET}${spend_limit_reset_str}"
  fi
  [ -n "$cache_stat" ] && append_stat "$cache_stat"
else
  # Context | Usage (5h) | Cache | Weekly (7d)
  [ -n "$ctx_stat" ] && append_stat "$ctx_stat"
  if [ -n "$five_hour" ]; then
    color=$(pct_color "$five_hour")
    append_stat "⏱️ ${WHITE}Usage:${RESET}${color}${five_hour}%${RESET}${five_hour_reset_str}"
  fi
  [ -n "$cache_stat" ] && append_stat "$cache_stat"
  if [ -n "$seven_day" ]; then
    color=$(pct_color "$seven_day")
    append_stat "📆 ${WHITE}Weekly:${RESET}${color}${seven_day}%${RESET}${seven_day_reset_str}"
  fi
fi

[ -n "$duration_str" ] && append_stat "🕒 ${WHITE}Time:${RESET}${CYAN}${duration_str}${RESET}"

printf '%s%s%s' "$header" "$dir_part" "$stats"
