#!/bin/sh
# Claude Code statusLine
# Format: [Model - **Effort**] 📁 dir git:(branch) | context_remaining% | tokens_used tokens

input=$(cat)

# Model display name
model=$(echo "$input" | jq -r '.model.display_name // empty')

# Effort level — prefer a dedicated effort/thinking field; fall back to output_style.name
# but suppress the literal "default" value since it is uninformative
effort=$(echo "$input" | jq -r '
  if .effort != null and .effort != "" then .effort
  elif .thinking_level != null and .thinking_level != "" then .thinking_level
  elif .reasoning_effort != null and .reasoning_effort != "" then .reasoning_effort
  elif (.output_style.name != null and .output_style.name != "" and .output_style.name != "default") then .output_style.name
  else empty
  end')

# Current directory basename
dir=$(echo "$input" | jq -r '.workspace.current_dir // .cwd')
dir_name=$(basename "$dir")

# Context remaining percentage (pre-calculated)
remaining=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty')

# Total tokens used (input + output from current context window call)
tokens_used=$(echo "$input" | jq -r '
  if .context_window.current_usage != null then
    .context_window.current_usage.input_tokens + .context_window.current_usage.output_tokens
  else
    empty
  end')

# Git branch (no lock contention)
git_part=""
if git -C "$dir" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  git_branch=$(git -C "$dir" symbolic-ref --short HEAD 2>/dev/null || git -C "$dir" rev-parse --short HEAD 2>/dev/null)
  if [ -n "$git_branch" ]; then
    git_part=" git:(${git_branch})"
  fi
fi

# Build output
model_part=""
if [ -n "$model" ] && [ -n "$effort" ]; then
  model_part="[${model} - **${effort}**]"
elif [ -n "$model" ]; then
  model_part="[${model}]"
fi

ctx_part=""
if [ -n "$remaining" ]; then
  ctx_part="${remaining}%"
fi

tokens_part=""
if [ -n "$tokens_used" ]; then
  tokens_part="${tokens_used} tokens"
fi

printf "%s 📁 %s%s | %s | %s" "$model_part" "$dir_name" "$git_part" "$ctx_part" "$tokens_part"
