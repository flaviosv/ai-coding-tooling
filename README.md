# ai-coding-tooling

Shared agent configuration and skills for AI coding tools (Claude Code, Cursor, Windsurf, Gemini CLI, etc.).

## Installation

### Prerequisites

- Unix-like shell (macOS/Linux)
- `make` installed

### 1. Clone the repository

```bash
git clone <repo-url>
cd ai-coding-tooling
```

### 2. Create the symlinks

```bash
make link
```

This will symlink:

| Source | Target |
|---|---|
| `.agents/` | `.claude/` |
| `.agents/` | `.cursor/` |
| `.agents/` | `.windsurf/` |
| `.agents/` | `.agent/` |
| `.agents/` | `.gemini/` |
| `AGENTS.md` | `CLAUDE.md` |
| `AGENTS.md` | `GEMINI.md` |

Existing files or symlinks are skipped — nothing is overwritten.

### 3. Set up global agent configuration

Open this project in Claude Code and run:

```
/global-agent-setup
```

This will symlink `AGENTS.global.md` to `~/.claude/CLAUDE.md` and install all global skills from the Tech Leads Club registry.

### 4. Remove symlinks

```bash
make unlink
```

Only removes symlinks — real files are never deleted.
