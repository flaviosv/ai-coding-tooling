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

Existing files or symlinks are skipped — nothing is overwritten.

### 3. Set up global agent configuration

Open this project in Claude Code and run:

```
/global-agent-setup
```

This will symlink `AGENTS.global.md` to the agent's global config file and install all global skills.

### 4. Install extended skill files

After the global skills are installed (step 3), link the extended skill files into the installed skill directories:

```bash
make link-extended
```

### 5. Remove symlinks

```bash
make unlink
```

Only removes symlinks — real files are never deleted.
