#!/usr/bin/env node
// fs-harness — skill manager for Claude Code. config/skills.json is the
// authoritative source map (sources: local, tech-leads-club, matt-pocock).
// Vendor calls go through execFileSync with an argument array, never a shell
// string, so skill names cannot inject commands.

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

// ---------------------------------------------------------------------------
// Paths & config
// ---------------------------------------------------------------------------

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(path.dirname(SCRIPT_DIR)); // repo root (scripts/bin/ is two levels down)

// Project-local skill installs (scope: local-only, or `add --local`) land under
// this repo's own .claude/skills/ — tracked directly in the repo, no linking.
const PROJECT_LOCAL_DIR = '.claude';
const TEMPLATES_DIR = path.join(ROOT, 'templates');

// Claude Code's global paths (hardcoded — this tool manages Claude Code only).
const CONFIG_PATH = expandHome('~/.claude/CLAUDE.md');
const SKILLS_DIR = expandHome('~/.claude/skills');
const STATUSLINE_PATH = expandHome('~/.claude/statusline-command.sh');
const SETTINGS_PATH = expandHome('~/.claude/settings.json');
const NPX_AGENT_ID = 'claude-code';

const SKILL_NAME_RE = /^[a-z0-9][a-z0-9-]*$/;

// ---------------------------------------------------------------------------
// Small utilities
// ---------------------------------------------------------------------------

const c = {
  reset: '\x1b[0m', dim: '\x1b[2m', red: '\x1b[31m', green: '\x1b[32m',
  yellow: '\x1b[33m', cyan: '\x1b[36m', bold: '\x1b[1m',
};
const log = (m) => console.log(m);
const info = (m) => console.log(`${c.cyan}•${c.reset} ${m}`);
const ok = (m) => console.log(`${c.green}✓${c.reset} ${m}`);
const skip = (m) => console.log(`${c.dim}– ${m}${c.reset}`);
const warn = (m) => console.warn(`${c.yellow}!${c.reset} ${m}`);
const fail = (m) => console.error(`${c.red}✗ ${m}${c.reset}`);

class UserError extends Error {}

function expandHome(p) {
  if (p === '~') return os.homedir();
  if (p.startsWith('~/')) return path.join(os.homedir(), p.slice(2));
  return p;
}

// Existence check that does NOT follow symlinks (so broken symlinks count).
function lexists(p) {
  try { fs.lstatSync(p); return true; } catch { return false; }
}
function isSymlink(p) {
  try { return fs.lstatSync(p).isSymbolicLink(); }
  catch { return false; }
}
function isDir(p) {
  try { return fs.statSync(p).isDirectory(); } catch { return false; }
}

// Returns the correct install path for a skill: project-local (.claude/skills/) for
// local-only scope, global SKILLS_DIR otherwise.
function skillDest(skill) {
  if (skill.scope === 'local-only') return path.join(ROOT, PROJECT_LOCAL_DIR, 'skills', skill.name);
  return path.join(SKILLS_DIR, skill.name);
}

function loadJson(rel) {
  const p = path.join(ROOT, rel);
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch (e) {
    throw new UserError(`Could not read ${rel}: ${e.message}`);
  }
}

function validateSkillName(name) {
  if (!SKILL_NAME_RE.test(name)) {
    throw new UserError(`Invalid skill name "${name}" (allowed: lowercase letters, digits, hyphens).`);
  }
  return name;
}

// ---------------------------------------------------------------------------
// Filesystem actions (dry-run aware)
// ---------------------------------------------------------------------------

let DRY = false;

function ensureDir(p) {
  if (isDir(p)) return;
  if (DRY) { log(`${c.dim}[dry-run]${c.reset} mkdir -p ${p}`); return; }
  fs.mkdirSync(p, { recursive: true });
}

// Skills reference shared templates as ../../templates/<name>.md. Installed skills are
// symlinks, so the kernel resolves that to the repo — but tools that normalize paths
// lexically (collapsing ../../ before following the symlink) resolve it to
// <skillsDir>/../templates instead. Link that path at the same target so both resolve.
// Any command that installs a skill must call this: a skill whose template links are
// dead fails silently at run time, with the agent guessing instead of erroring.
function templatesLinkPath() {
  return path.join(path.dirname(SKILLS_DIR), 'templates');
}

function ensureTemplatesLink() {
  const dest = templatesLinkPath();
  if (lexists(dest)) return 'present';
  return linkSafe(TEMPLATES_DIR, dest);
}

// Create a symlink, never clobbering anything that already exists.
// Returns 'linked' | 'present' | 'dry'.
function linkSafe(target, dest) {
  if (lexists(dest)) { skip(`${dest} already exists`); return 'present'; }
  if (DRY) { log(`${c.dim}[dry-run]${c.reset} ln -s ${target} ${dest}`); return 'dry'; }
  fs.symlinkSync(target, dest);
  ok(`linked ${dest} -> ${target}`);
  return 'linked';
}

// Force-create an overlay symlink: removes an existing symlink first, but never
// deletes a real file/dir.
function relinkOverlay(target, dest) {
  if (lexists(dest)) {
    if (!isSymlink(dest)) { warn(`${dest} is a real file/dir — leaving it untouched`); return 'blocked'; }
    if (!DRY) fs.unlinkSync(dest);
  }
  if (DRY) { log(`${c.dim}[dry-run]${c.reset} ln -sf ${target} ${dest}`); return 'dry'; }
  fs.symlinkSync(target, dest);
  return 'linked';
}

function unlinkIfSymlink(dest) {
  if (!lexists(dest)) { skip(`${dest} not present`); return; }
  if (!isSymlink(dest)) { skip(`${dest} is not a symlink`); return; }
  if (DRY) { log(`${c.dim}[dry-run]${c.reset} rm ${dest}`); return; }
  fs.unlinkSync(dest);
  ok(`removed ${dest}`);
}

function runNpx(args, label, { cwd } = {}) {
  const printable = `npx ${args.join(' ')}`;
  if (DRY) { log(`${c.dim}[dry-run]${c.reset} ${printable}`); return true; }
  info(printable);
  try {
    execFileSync('npx', args, { stdio: 'inherit', cwd });
    ok(label);
    return true;
  } catch (e) {
    fail(`${label} failed (${e.message})`);
    return false;
  }
}

// ---------------------------------------------------------------------------
// Overrides (extended/) overlay
// ---------------------------------------------------------------------------

// Apply the extended/<skill>/ overlay into SKILLS_DIR/<skill>/ (or the project-local
// dest for local-only skills). skill may be a full skill object or a plain
// {name, scope} for the path resolver.
function applyOverlay(skill) {
  const name = skill.name;
  const extDir = path.join(ROOT, 'extended', name);
  if (!isDir(extDir)) return; // nothing to overlay
  const targetDir = skillDest(skill);
  if (!isDir(targetDir)) { warn(`override for ${name}: parent skill not installed yet — skipping overlay`); return; }

  const extSkill = path.join(extDir, 'SKILL.md');
  if (lexists(extSkill)) {
    const r = relinkOverlay(extSkill, path.join(targetDir, 'SKILL.extended.md'));
    if (r === 'linked' || r === 'dry') ok(`override ${name}: SKILL.extended.md`);
  }

  const refSrc = path.join(extDir, 'references');
  if (isDir(refSrc)) {
    // Collision-aware: if the vendor shipped a references/ dir, use references.extended.
    const destName = isDir(path.join(targetDir, 'references')) ? 'references.extended' : 'references';
    const r = relinkOverlay(refSrc, path.join(targetDir, destName));
    if (r === 'linked' || r === 'dry') ok(`override ${name}: ${destName}/`);
  }
}

// ---------------------------------------------------------------------------
// Vendor install / update (hardcoded, arg arrays)
// ---------------------------------------------------------------------------

function installSkill(skill, { force = false } = {}) {
  const name = validateSkillName(skill.name);
  const installScope = skill.installScope || 'global';

  if (installScope === 'none' || (!force && installScope === 'local')) {
    const reason = installScope === 'local' ? 'project-local'
      : `not installed: ${installScope}`;
    skip(`${name} (${reason})`);
    return true;
  }

  const dest = skillDest(skill);
  if (lexists(dest)) { skip(`${name} already installed`); return true; }

  switch (skill.source) {
    case 'local': {
      const src = path.join(ROOT, 'skills', name);
      if (!isDir(src)) { fail(`${name}: source skills/${name} not found`); return false; }
      linkSafe(src, dest);
      return true;
    }
    case 'tech-leads-club': {
      if (installScope === 'local') ensureDir(path.dirname(dest));
      const args = ['@tech-leads-club/agent-skills', 'install', '--skill', name, '--agent', NPX_AGENT_ID];
      if (installScope !== 'local') args.push('--global');
      return runNpx(args, `installed ${name} (Tech Leads Club)`);
    }
    case 'matt-pocock': {
      if (installScope === 'local') ensureDir(path.dirname(dest));
      const args = ['skills@latest', 'add', 'mattpocock/skills', '--agent', NPX_AGENT_ID, '--skill', name, '--yes'];
      if (installScope !== 'local') args.push('--global');
      return runNpx(args, `installed ${name} (Matt Pocock)`);
    }
    default:
      fail(`${name}: unknown source "${skill.source}"`);
      return false;
  }
}

function updateSkill(skill) {
  const name = validateSkillName(skill.name);
  const installScope = skill.installScope || 'global';
  switch (skill.source) {
    case 'tech-leads-club': {
      // The vendor `update` subcommand has no scope flag; it auto-detects agent
      // configs from cwd. For global skills, run outside the repo so it never
      // materializes a project-local copy from this repo's .claude/ config.
      const args = ['@tech-leads-club/agent-skills', 'update', '--skill', name];
      const cwd = installScope === 'local' ? undefined : os.homedir();
      return runNpx(args, `updated ${name} (Tech Leads Club)`, { cwd });
    }
    case 'matt-pocock': {
      const args = ['skills', 'update', name, '--yes'];
      if (installScope !== 'local') args.push('-g');
      return runNpx(args, `updated ${name} (Matt Pocock)`);
    }
    default:
      skip(`${name} (${skill.source}: nothing to update)`);
      return true;
  }
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

function cmdSetup() {
  const { skills } = loadJson('config/skills.json');

  log(`${c.bold}Setting up Claude Code${c.reset}`);
  ensureDir(SKILLS_DIR);

  linkSafe(path.join(ROOT, 'CLAUDE.global.md'), CONFIG_PATH);

  ensureTemplatesLink();

  log(`\n${c.bold}Skills${c.reset}`);
  for (const skill of skills) installSkill(skill);

  log(`\n${c.bold}Overrides${c.reset}`);
  for (const skill of skills) if (skill.extended) applyOverlay(skill);

  const personalDir = path.join(ROOT, 'personal');
  if (isDir(personalDir)) {
    log(`\n${c.bold}Personal${c.reset}`);
    for (const name of fs.readdirSync(personalDir)) {
      const sd = path.join(personalDir, name);
      if (!isDir(sd) || !lexists(path.join(sd, 'SKILL.md'))) continue;
      linkSafe(sd, path.join(SKILLS_DIR, name));
    }
  }

  log(`\n${c.bold}Hooks${c.reset}`);
  cmdHooks();

  log(`\n${c.green}Setup complete.${c.reset}`);
}

function cmdAdd(skillName, source, flags = {}) {
  const registry = loadJson('config/skills.json');
  const name = validateSkillName(skillName);

  let skill = registry.skills.find((s) => s.name === name);
  if (!skill) {
    if (!source) throw new UserError(`"${name}" is not in skills.json. Provide --source <local|tech-leads-club|matt-pocock>.`);
    const scope = flags.local ? 'local-only' : (source === 'local' ? 'built' : source);
    skill = { name, source, scope };
    if (flags.local) skill.installScope = 'local';
  }

  const dest = skillDest(skill);
  if (lexists(dest)) throw new UserError(`${dest} already exists. Remove it manually or run update.`);

  ensureDir(path.dirname(dest));
  ensureTemplatesLink();
  const installed = installSkill(skill, { force: !!flags.local });
  if (!installed) throw new UserError(`Install of ${name} failed.`);

  applyOverlay(skill);

  // Register a newly-added skill in the registry.
  const known = registry.skills.find((s) => s.name === name);
  if (!known) {
    registry.skills.push(skill);
    registry.skills.sort((a, b) => a.name.localeCompare(b.name));
    if (!DRY) fs.writeFileSync(path.join(ROOT, 'config/skills.json'), JSON.stringify(registry, null, 2) + '\n');
    ok(`registered ${name} (${skill.source}) in skills.json`);
  }
  log(`\n${c.green}Added ${name}.${c.reset}`);
}

function cmdUpdate(names, all) {
  const registry = loadJson('config/skills.json');
  const { skills } = registry;

  const vendorSkills = skills.filter((s) => s.source === 'tech-leads-club' || s.source === 'matt-pocock');

  // Accept comma- and/or space-separated names; --all updates every vendor skill.
  const requested = names.flatMap((n) => n.split(',')).map((n) => n.trim()).filter(Boolean);
  if (!all && !requested.length) {
    throw new UserError('Specify skills to update (comma- or space-separated) or pass --all for every vendor skill.');
  }

  let scope;
  if (all) {
    scope = vendorSkills;
  } else {
    scope = [];
    for (const n of requested) {
      const s = vendorSkills.find((x) => x.name === n);
      if (!s) { warn(`${n} is not a vendor skill in skills.json — skipping`); continue; }
      scope.push(s);
    }
  }

  if (!scope.length) { warn('No vendor skills to update.'); return; }
  log(`${c.bold}Updating ${scope.length} vendor skill(s)${c.reset}`);
  for (const skill of scope) {
    updateSkill(skill);
    if (skill.extended) applyOverlay(skill);
  }
  log(`\n${c.green}Update complete.${c.reset}`);
}

function cmdOverride(skillName) {
  const registry = loadJson('config/skills.json');
  const name = validateSkillName(skillName);

  const skill = registry.skills.find((s) => s.name === name);
  if (skill && skill.source === 'local') {
    warn(`${name} is a local skill you own — edit skills/${name}/ directly instead of overriding.`);
    return;
  }

  ensureTemplatesLink();

  // Scaffold extended/<name>/SKILL.md from the frontmatter template.
  const extDir = path.join(ROOT, 'extended', name);
  const extSkill = path.join(extDir, 'SKILL.md');
  if (lexists(extSkill)) {
    skip(`extended/${name}/SKILL.md already exists — leaving it untouched`);
  } else {
    ensureDir(extDir);
    const body = overrideTemplate(name);
    if (DRY) log(`${c.dim}[dry-run]${c.reset} write extended/${name}/SKILL.md`);
    else fs.writeFileSync(extSkill, body);
    ok(`scaffolded extended/${name}/SKILL.md`);
  }

  if (skill) {
    if (!skill.extended) {
      skill.extended = true;
      if (!DRY) fs.writeFileSync(path.join(ROOT, 'config/skills.json'), JSON.stringify(registry, null, 2) + '\n');
      ok(`marked ${name} extended in skills.json`);
    }
  } else {
    warn(`${name} is not in skills.json — add it (or run \`add\`) so the override is tracked.`);
  }

  applyOverlay(skill || { name, scope: 'tech-leads-club' });
  log(`\n${c.green}Override scaffolded for ${name}. Fill in extended/${name}/SKILL.md.${c.reset}`);
}

function overrideTemplate(name) {
  return `---
name: ${name}-extended
extends: ${name}
description: >
  Extension for the ${name} skill. This file MUST be read together with the parent
  ${name} SKILL.md. The parent skill defines [what the parent governs]. This extension
  adds [what this adds].
metadata:
  version: "1.0.0"
  parent_skill: ${name}
  source: "ai-coding-tooling (extended/)"
---

# ${name} — Extension

<!-- Add project-specific guidance that layers on top of the parent ${name} skill. -->
`;
}

function cmdList() {
  const { skills } = loadJson('config/skills.json');

  log(`${c.bold}Skills${c.reset} (skillsDir: ${SKILLS_DIR})\n`);
  const pad = Math.max(...skills.map((s) => s.name.length));
  for (const s of skills) {
    const dest = skillDest(s);
    let state;
    if (s.installScope === 'none') state = `${c.dim}n/a${c.reset}`;
    else if (!lexists(dest)) state = `${c.yellow}missing${c.reset}`;
    else if (isSymlink(dest)) state = `${c.green}symlink${c.reset}`;
    else state = `${c.green}installed${c.reset}`;
    const ext = s.extended ? ` ${c.cyan}[override]${c.reset}` : '';
    log(`  ${s.name.padEnd(pad)}  ${s.source.padEnd(16)} ${state}${ext}`);
  }

  // Surface the shared-templates link: without it every ../../templates/<name>.md
  // reference in an installed skill reads as a missing file, silently.
  const tl = templatesLinkPath();
  const tlState = !lexists(tl)
    ? `${c.yellow}missing — run \`fs-harness setup\`${c.reset}`
    : isSymlink(tl) ? `${c.green}symlink${c.reset}` : `${c.yellow}real dir (expected a symlink)${c.reset}`;
  log(`\n${c.bold}Shared templates${c.reset}  ${tl}  ${tlState}`);
}

// Undo setup: remove the global config symlink, uninstall the skills setup
// installed globally, drop personal links.
function cmdDestroy() {
  const { skills } = loadJson('config/skills.json');

  log(`${c.bold}Tearing down Claude Code setup${c.reset} (undoes setup)`);

  log(`\n${c.bold}Global config${c.reset}`);
  removeConfigSymlink(CONFIG_PATH);
  unlinkIfSymlink(templatesLinkPath());

  log(`\n${c.bold}Skills${c.reset}`);
  for (const skill of skills) uninstallSkill(skill);

  const personalDir = path.join(ROOT, 'personal');
  if (isDir(personalDir)) {
    log(`\n${c.bold}Personal${c.reset}`);
    for (const name of fs.readdirSync(personalDir)) {
      const sd = path.join(personalDir, name);
      if (!isDir(sd) || !lexists(path.join(sd, 'SKILL.md'))) continue;
      unlinkIfSymlink(path.join(SKILLS_DIR, name));
    }
  }

  log(`\n${c.green}Teardown complete. Only setup-managed skills and symlinks were removed.${c.reset}`);
}

// Remove the global config symlink only if it points at this repo's CLAUDE.global.md.
function removeConfigSymlink(configPath) {
  if (!lexists(configPath)) { skip(`${configPath} not present`); return; }
  if (!isSymlink(configPath)) { warn(`${configPath} is a real file — leaving it untouched`); return; }
  const expected = path.join(ROOT, 'CLAUDE.global.md');
  const actual = path.resolve(path.dirname(configPath), fs.readlinkSync(configPath));
  if (actual !== expected) { warn(`${configPath} points elsewhere (${actual}) — leaving it untouched`); return; }
  if (DRY) { log(`${c.dim}[dry-run]${c.reset} rm ${configPath}`); return; }
  fs.unlinkSync(configPath);
  ok(`removed ${configPath}`);
}

// Uninstall a skill: unlink symlinks, rm -rf vendor dirs.
// Skips installScope=none and project-local skills unless force=true.
function uninstallSkill(skill, { force = false } = {}) {
  const name = validateSkillName(skill.name);
  const installScope = skill.installScope || 'global';
  if (installScope === 'none' || (!force && installScope === 'local')) {
    const reason = installScope === 'local' ? 'project-local'
      : 'installScope=none';
    skip(`${name} (${reason})`);
    return;
  }
  const dest = skillDest(skill);
  if (!lexists(dest)) { skip(`${name} not installed`); return; }
  if (isSymlink(dest)) {
    if (DRY) { log(`${c.dim}[dry-run]${c.reset} rm ${dest}`); return; }
    fs.unlinkSync(dest);
    ok(`removed ${name} (symlink)`);
  } else if (isDir(dest)) {
    if (DRY) { log(`${c.dim}[dry-run]${c.reset} rm -rf ${dest}`); return; }
    fs.rmSync(dest, { recursive: true, force: true });
    ok(`uninstalled ${name} (${skill.source})`);
  }
}

// Remove a single skill: uninstall (symlink for local, rm -rf for vendor dirs),
// deregister from skills.json, and regenerate the doc. Keeps extended/<name>/ and,
// for local skills, the skills/<name>/ source.
function cmdDelete(skillName) {
  const registry = loadJson('config/skills.json');
  const name = validateSkillName(skillName);

  const skill = registry.skills.find((s) => s.name === name);
  if (!skill) throw new UserError(`"${name}" is not in skills.json — nothing to delete.`);

  log(`${c.bold}Deleting ${name}${c.reset} (${skill.source})`);

  // Filesystem uninstall: symlink unlink (local) / vendor rm -rf; extended/ left intact.
  uninstallSkill(skill, { force: true });
  if (skill.extended && isDir(path.join(ROOT, 'extended', name))) {
    log(`${c.dim}kept extended/${name}/ (override overlay preserved)${c.reset}`);
  }

  // Deregister.
  registry.skills = registry.skills.filter((s) => s.name !== name);
  if (DRY) {
    log(`${c.dim}[dry-run]${c.reset} remove ${name} from config/skills.json`);
  } else {
    fs.writeFileSync(path.join(ROOT, 'config/skills.json'), JSON.stringify(registry, null, 2) + '\n');
    ok(`removed ${name} from skills.json`);
  }
  log(`\n${c.green}Deleted ${name}.${c.reset}`);
}

function cmdStatusline(force) {
  const dest = STATUSLINE_PATH;
  const src = path.join(ROOT, 'scripts', 'bin', 'misc', 'statusline.sh');
  if (!lexists(src)) throw new UserError(`Status line source not found: ${src}`);

  if (lexists(dest) && !force) {
    skip(`${dest} already exists (use --force to overwrite)`);
    return;
  }
  if (DRY) { log(`${c.dim}[dry-run]${c.reset} cp ${src} ${dest} && chmod +x ${dest}`); return; }
  ensureDir(path.dirname(dest));
  fs.copyFileSync(src, dest);
  fs.chmodSync(dest, 0o755);
  ok(`installed status line -> ${dest}`);
}

// Merges config/hooks.json's entries into settings.json's `hooks` object.
// Additive only: existing event arrays (ai-memory, sonar-secrets, etc.) are
// never touched, and re-running is a no-op once a script's absolute path is
// already present for an event.
function cmdHooks() {
  const entries = loadJson('config/hooks.json');
  if (entries.length === 0) { skip('no hooks registered'); return; }

  let settings = {};
  if (lexists(SETTINGS_PATH)) {
    try { settings = JSON.parse(fs.readFileSync(SETTINGS_PATH, 'utf8')); }
    catch (e) { throw new UserError(`Could not read ${SETTINGS_PATH}: ${e.message}`); }
  }
  settings.hooks = settings.hooks || {};

  let changed = false;
  for (const entry of entries) {
    const scriptAbsPath = path.join(ROOT, entry.script);
    for (const [event, cfg] of Object.entries(entry.events)) {
      settings.hooks[event] = settings.hooks[event] || [];
      const installed = settings.hooks[event].some((g) =>
        g.hooks && g.hooks.some((h) => h.command === scriptAbsPath));
      if (installed) { skip(`${entry.id} already installed for ${event}`); continue; }
      settings.hooks[event].push({
        matcher: cfg.matcher ?? '',
        hooks: [{ type: 'command', command: scriptAbsPath, timeout: cfg.timeout ?? 10 }],
      });
      ok(`registered ${entry.id} on ${event}`);
      changed = true;
    }
  }

  if (!changed) { skip('hooks already up to date'); return; }
  if (DRY) { log(`${c.dim}[dry-run]${c.reset} update ${SETTINGS_PATH}`); return; }
  fs.writeFileSync(SETTINGS_PATH, JSON.stringify(settings, null, 2) + '\n');
  ok(`installed hooks -> ${SETTINGS_PATH}`);
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

const HELP = `${c.bold}fs-harness${c.reset} — skill manager for Claude Code

${c.bold}Usage:${c.reset} fs-harness <command> [args] [--dry-run]

${c.bold}Commands:${c.reset}
  setup                          Bootstrap: global config + skills + overrides
  destroy                        Undo setup (remove config, uninstall skills)
  add <skill> [--source <s>] [--local]   Install one skill (registers it if new; --local installs to .claude/skills/)
  delete <skill>                 Remove one skill (uninstall + deregister; keeps extended/)
  update <skills|--all>          Update vendor skills (Tech Leads Club / Matt Pocock).
                                  Pass a comma- or space-separated list, or --all for every vendor skill.
  override <skill>               Scaffold extended/<skill>/ and apply the overlay
  list                           Show each skill's source and install state
  statusline [--force]           Install the Claude Code status line script
  hooks                          Sync config/hooks.json into settings.json (run by setup)
  help                           Show this message

${c.bold}Sources:${c.reset} local · tech-leads-club · matt-pocock
${c.bold}Flags:${c.reset}   --dry-run (print actions, change nothing) · --all (update only) · --force (statusline only) · --local (add only)`;

function parseArgs(argv) {
  const positionals = [];
  const flags = { dryRun: false, force: false, all: false, local: false, source: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--dry-run') flags.dryRun = true;
    else if (a === '--force') flags.force = true;
    else if (a === '--all') flags.all = true;
    else if (a === '--local') flags.local = true;
    else if (a === '--source') flags.source = argv[++i];
    else if (a.startsWith('--source=')) flags.source = a.slice('--source='.length);
    else positionals.push(a);
  }
  return { positionals, flags };
}

function main() {
  const { positionals, flags } = parseArgs(process.argv.slice(2));
  DRY = flags.dryRun;
  const [command, ...rest] = positionals;

  if (!command || command === 'help' || command === '--help' || command === '-h') {
    log(HELP);
    return;
  }
  if (DRY) log(`${c.dim}(dry-run: no changes will be made)${c.reset}\n`);

  switch (command) {
    case 'setup': cmdSetup(); break;
    case 'destroy': cmdDestroy(); break;
    case 'add': {
      if (!rest[0]) throw new UserError('Usage: fs-harness add <skill> [--source <s>] [--local]');
      cmdAdd(rest[0], flags.source, flags);
      break;
    }
    case 'delete': {
      if (!rest[0]) throw new UserError('Usage: fs-harness delete <skill>');
      cmdDelete(rest[0]);
      break;
    }
    case 'update': cmdUpdate(rest, flags.all); break;
    case 'override': {
      if (!rest[0]) throw new UserError('Usage: fs-harness override <skill>');
      cmdOverride(rest[0]);
      break;
    }
    case 'list': cmdList(); break;
    case 'statusline': cmdStatusline(flags.force); break;
    case 'hooks': cmdHooks(); break;
    default:
      throw new UserError(`Unknown command "${command}". Run \`fs-harness help\`.`);
  }
}

try {
  main();
} catch (e) {
  if (e instanceof UserError) { fail(e.message); process.exit(1); }
  throw e;
}
