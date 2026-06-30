# Uninstalling SonarQube — Claude Code Integration

Complete removal guide for every artifact installed by `sonar integrate claude --global`.
Each section is independently executable — follow only the sections you need.

Installed with: `sonar` CLI v1.2.0 on 2026-06-30 against `http://shared.sonarqube.test/`

---

## Artifact Inventory

| Artifact | Location |
|----------|----------|
| MCP server entry | `~/.claude.json` → `mcpServers.sonarqube` |
| MCP Docker wrapper | `~/.local/bin/sonar-mcp-wrapper.sh` |
| Claude Code hook — Read scanner | `~/.claude/settings.json` → `hooks.PreToolUse[Read]` |
| Claude Code hook — Prompt scanner | `~/.claude/settings.json` → `hooks.UserPromptSubmit[*]` |
| Hook scripts | `~/.claude/hooks/sonar-secrets/` |
| Secrets binary | `~/.sonar/sonarqube-cli/bin/sonar-secrets-*` |
| Sonar CLI state | `~/.sonar/sonarqube-cli/state.json` |
| Auth token | macOS Keychain — service: `sonarqube-cli`, account: `shared.sonarqube.test` |
| Context augmentation | **N/A** — not available on SonarQube Server Community edition |

---

## 1. MCP Server

### What was installed

`~/.claude.json` has an entry under `mcpServers.sonarqube` pointing to the Docker wrapper:

```json
"sonarqube": {
  "command": "/Users/<you>/.local/bin/sonar-mcp-wrapper.sh",
  "args": []
}
```

### Remove

Edit `~/.claude.json` and delete the `"sonarqube"` key from `mcpServers`.

Then delete the wrapper script:

```bash
rm ~/.local/bin/sonar-mcp-wrapper.sh
```

### Verify

```bash
grep -i sonar ~/.claude.json
```

Expected: no output (or only unrelated references).

```bash
ls ~/.local/bin/sonar-mcp-wrapper.sh 2>&1
```

Expected: `No such file or directory`.

---

## 2. Claude Code Hooks (Secrets Scanning)

> These are Claude Code lifecycle hooks — NOT git hooks. They fire when Claude reads a file
> or submits a prompt, scanning for secrets. They are registered in `~/.claude/settings.json`.

### What was installed

Two entries in `~/.claude/settings.json`:

- `hooks.PreToolUse` — matcher `Read` → runs `pretool-secrets.sh`
- `hooks.UserPromptSubmit` — matcher `*` → runs `prompt-secrets.sh`

### Remove

Edit `~/.claude/settings.json`. In the `hooks` object:

1. Remove the entry in `PreToolUse` whose `command` contains `sonar-secrets`
2. Remove the entire `UserPromptSubmit` array (or the entry whose `command` contains `sonar-secrets` if you have other `UserPromptSubmit` hooks)

Then delete the hook scripts directory:

```bash
rm -rf ~/.claude/hooks/sonar-secrets/
```

### Verify

```bash
grep -r sonar-secrets ~/.claude/settings.json
```

Expected: no output.

```bash
ls ~/.claude/hooks/sonar-secrets/ 2>&1
```

Expected: `No such file or directory`.

---

## 3. Secrets Binary

### What was installed

```
~/.sonar/sonarqube-cli/bin/sonar-secrets-<version>-macos-arm64
```

### Remove

```bash
rm ~/.sonar/sonarqube-cli/bin/sonar-secrets-*
```

### Verify

```bash
ls ~/.sonar/sonarqube-cli/bin/
```

Expected: directory empty or non-existent.

---

## 4. Auth Token (Keychain)

### What was installed

macOS Keychain entry:
- Service: `sonarqube-cli`
- Account: `shared.sonarqube.test`

### Remove

```bash
security delete-generic-password -s "sonarqube-cli" -a "shared.sonarqube.test"
```

### Verify

```bash
security find-generic-password -s "sonarqube-cli" -a "shared.sonarqube.test" 2>&1
```

Expected: `The specified item could not be found in the keychain.`

---

## 5. Sonar CLI State

### What was installed

`~/.sonar/sonarqube-cli/state.json` — tracks auth connection, agent registration, installed hooks and tools.

### Remove

```bash
rm -rf ~/.sonar/sonarqube-cli/
```

### Verify

```bash
ls ~/.sonar/sonarqube-cli/ 2>&1
```

Expected: `No such file or directory`.

---

## 6. Context Augmentation

**Not applicable** — context augmentation is only available on **SonarQube Cloud**, not SonarQube Server Community edition. `sonar integrate claude --global` skipped it automatically. No removal steps are needed.

Confirmation:

```bash
sonar context 2>&1
```

Expected: reports "not installed" — this is the correct state on Community edition.

---

## 7. Nuclear Option

Removes everything in one command — including auth tokens and all registered artifacts tracked by the Sonar CLI state file:

```bash
sonar system reset --force
```

⚠️ **Warning**: This also removes your authentication token. You will need to run `sonar auth login` again to restore access to `http://shared.sonarqube.test/`.

After reset, manually remove the MCP entry from `~/.claude.json` (the nuclear option does not edit Claude Code config files) and the wrapper script:

```bash
# Edit ~/.claude.json and remove the "sonarqube" key from mcpServers, then:
rm ~/.local/bin/sonar-mcp-wrapper.sh
```

### Verify full removal

```bash
sonar system status 2>&1    # should error or show unauthenticated
grep -i sonar ~/.claude.json   # no mcpServers.sonarqube entry
grep -r sonar-secrets ~/.claude/settings.json   # no hook entries
ls ~/.claude/hooks/sonar-secrets/ 2>&1          # no such file
ls ~/.sonar/sonarqube-cli/bin/ 2>&1             # empty or no such file
```

---

## Re-installing After Removal

To restore the full integration:

```bash
sonar auth login --server http://shared.sonarqube.test/
sonar integrate claude --global --non-interactive
```

Then re-apply the Docker wrapper fix (needed because `sonar run mcp` cannot resolve `shared.sonarqube.test` from inside Docker):

```bash
cp config/sonar-mcp-wrapper.sh ~/.local/bin/sonar-mcp-wrapper.sh
chmod +x ~/.local/bin/sonar-mcp-wrapper.sh
```

And update `~/.claude.json` to point to the wrapper instead of `sonar run mcp`:

```json
"sonarqube": {
  "command": "/Users/<you>/.local/bin/sonar-mcp-wrapper.sh",
  "args": []
}
```
