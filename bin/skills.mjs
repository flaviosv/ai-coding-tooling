#!/usr/bin/env node
// fsvskills — skill manager for AI coding agents. config/skills.json is the
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
const ROOT = path.dirname(SCRIPT_DIR); // repo root (bin/ is one level down)

// Project-local link sources: setup points <agent.projectDir> at .agents and
// <agent.projectConfig> at AGENTS.md.
const AGENTS_DIR = '.agents';
const MD_SOURCE = 'AGENTS.md';

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

// Returns the correct install path for a skill: project-local (.agents/skills/) for
// local-only scope, global skillsDir otherwise.
function skillDest(skill, agent) {
  if (skill.scope === 'local-only') return path.join(ROOT, AGENTS_DIR, 'skills', skill.name);
  return path.join(agent.skillsDir, skill.name);
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

function resolveAgent(agents, id) {
  if (!id) throw new UserError('Missing agent. Usage example: fsvskills setup claude-code');
  const a = agents[id];
  if (!a) {
    throw new UserError(`Unknown agent "${id}". Known: ${Object.keys(agents).join(', ')}.`);
  }
  return {
    id,
    configPath: expandHome(a.configPath),
    skillsDir: expandHome(a.skillsDir),
    statuslinePath: a.statuslinePath ? expandHome(a.statuslinePath) : null,
    npxId: a.npxId,
    projectDir: a.projectDir || null,
    projectConfig: a.projectConfig || null,
  };
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

// Apply the extended/<skill>/ overlay into <skillsDir>/<skill>/.
// skill may be a full skill object or a plain {name, scope} for the path resolver.
function applyOverlay(skill, agent) {
  const name = skill.name;
  const extDir = path.join(ROOT, 'extended', name);
  if (!isDir(extDir)) return; // nothing to overlay
  const targetDir = skillDest(skill, agent);
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

function installSkill(skill, agent, { force = false } = {}) {
  const name = validateSkillName(skill.name);
  const installScope = skill.installScope || 'global';

  if (installScope === 'none' || (!force && installScope === 'local')) {
    const reason = installScope === 'local' ? 'project-local'
      : `not installed: ${installScope}`;
    skip(`${name} (${reason})`);
    return true;
  }

  const dest = skillDest(skill, agent);
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
      const args = ['@tech-leads-club/agent-skills', 'install', '--skill', name, '--agent', agent.npxId];
      if (installScope !== 'local') args.push('--global');
      return runNpx(args, `installed ${name} (Tech Leads Club)`);
    }
    case 'matt-pocock': {
      if (installScope === 'local') ensureDir(path.dirname(dest));
      const args = ['skills@latest', 'add', 'mattpocock/skills', '--agent', agent.npxId, '--skill', name, '--yes'];
      if (installScope !== 'local') args.push('--global');
      return runNpx(args, `installed ${name} (Matt Pocock)`);
    }
    default:
      fail(`${name}: unknown source "${skill.source}"`);
      return false;
  }
}

function updateSkill(skill, agent) {
  const name = validateSkillName(skill.name);
  const installScope = skill.installScope || 'global';
  switch (skill.source) {
    case 'tech-leads-club': {
      // The vendor `update` subcommand has no scope flag; it auto-detects agent
      // configs from cwd. For global skills, run outside the repo so it never
      // materializes a project-local copy from this repo's .agents/ config.
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

function cmdSetup(agentId) {
  const agents = loadJson('config/agents.json');
  const agent = resolveAgent(agents, agentId);
  const { skills } = loadJson('config/skills.json');

  log(`${c.bold}Setting up ${agent.id}${c.reset}`);
  ensureDir(agent.skillsDir);

  linkSafe(path.join(ROOT, 'AGENTS.global.md'), agent.configPath);

  log(`\n${c.bold}Skills${c.reset}`);
  for (const skill of skills) installSkill(skill, agent);

  log(`\n${c.bold}Overrides${c.reset}`);
  for (const skill of skills) if (skill.extended) applyOverlay(skill, agent);

  const personalDir = path.join(ROOT, 'personal');
  if (isDir(personalDir)) {
    log(`\n${c.bold}Personal${c.reset}`);
    for (const name of fs.readdirSync(personalDir)) {
      const sd = path.join(personalDir, name);
      if (!isDir(sd) || !lexists(path.join(sd, 'SKILL.md'))) continue;
      linkSafe(sd, path.join(agent.skillsDir, name));
    }
  }

  // Project-local links expose .agents skills + AGENTS.md to the agent in this repo.
  if (agent.projectDir || agent.projectConfig) {
    log(`\n${c.bold}Project-local links${c.reset}`);
    if (agent.projectDir) linkSafe(AGENTS_DIR, path.join(ROOT, agent.projectDir));
    if (agent.projectConfig) linkSafe(MD_SOURCE, path.join(ROOT, agent.projectConfig));
  }

  log(`\n${c.green}Setup complete for ${agent.id}.${c.reset}`);
}

// Read the `description:` field from a skill's installed SKILL.md frontmatter so
// the generated registry doc (docs/AGENT-SKILLS.md) shows a real summary instead
// of "undefined". Handles single-line values and folded/literal block scalars.
function readSkillDescription(dest) {
  let text;
  try { text = fs.readFileSync(path.join(dest, 'SKILL.md'), 'utf8'); } catch { return ''; }
  const fm = text.match(/^---\n([\s\S]*?)\n---/);
  if (!fm) return '';
  const lines = fm[1].split('\n');
  const i = lines.findIndex((l) => /^description\s*:/.test(l));
  if (i === -1) return '';
  let val = lines[i].replace(/^description\s*:/, '').trim();
  // Block scalar (`description: >` / `|`): gather the indented continuation lines.
  if (['>', '|', '>-', '|-', ''].includes(val)) {
    const block = [];
    for (let j = i + 1; j < lines.length; j++) {
      if (/^\s+\S/.test(lines[j])) block.push(lines[j].trim());
      else if (lines[j].trim() === '') block.push('');
      else break;
    }
    val = block.join(' ');
  }
  return val.replace(/\s+/g, ' ').replace(/^["']|["']$/g, '').trim();
}

function cmdAdd(agentId, skillName, source, flags = {}) {
  const agents = loadJson('config/agents.json');
  const agent = resolveAgent(agents, agentId);
  const registry = loadJson('config/skills.json');
  const name = validateSkillName(skillName);

  let skill = registry.skills.find((s) => s.name === name);
  if (!skill) {
    if (!source) throw new UserError(`"${name}" is not in skills.json. Provide --source <local|tech-leads-club|matt-pocock>.`);
    const scope = flags.local ? 'local-only' : (source === 'local' ? 'built' : source);
    skill = { name, source, scope };
    if (flags.local) skill.installScope = 'local';
  }

  const dest = skillDest(skill, agent);
  if (lexists(dest)) throw new UserError(`${dest} already exists. Remove it manually or run update.`);

  ensureDir(path.dirname(dest));
  const installed = installSkill(skill, agent, { force: !!flags.local });
  if (!installed) throw new UserError(`Install of ${name} failed.`);

  applyOverlay(skill, agent);

  // Capture the skill's description from its SKILL.md frontmatter so the registry
  // doc shows a real summary. `skill` is the same object stored in the registry
  // (found or newly built), so assigning here persists on write.
  const desc = readSkillDescription(skillDest(skill, agent));
  const known = registry.skills.find((s) => s.name === name);
  const descChanged = desc && skill.description !== desc;
  if (descChanged) skill.description = desc;

  // Register a newly-added skill and/or persist a refreshed description, then refresh the doc.
  if (!known || descChanged) {
    if (!known) registry.skills.push(skill);
    registry.skills.sort((a, b) => a.name.localeCompare(b.name));
    if (!DRY) fs.writeFileSync(path.join(ROOT, 'config/skills.json'), JSON.stringify(registry, null, 2) + '\n');
    ok(known ? `refreshed ${name} description in skills.json` : `registered ${name} (${skill.source}) in skills.json`);
    if (!DRY) generateDocs();
  }
  log(`\n${c.green}Added ${name}.${c.reset}`);
}

function cmdUpdate(agentId, names, all) {
  const agents = loadJson('config/agents.json');
  const agent = resolveAgent(agents, agentId);
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
  log(`${c.bold}Updating ${scope.length} vendor skill(s) for ${agent.id}${c.reset}`);
  let descChanged = false;
  for (const skill of scope) {
    updateSkill(skill, agent);
    if (skill.extended) applyOverlay(skill, agent);
    // Backfill/refresh the description from the reinstalled SKILL.md frontmatter.
    const desc = readSkillDescription(skillDest(skill, agent));
    if (desc && skill.description !== desc) { skill.description = desc; descChanged = true; }
  }
  if (descChanged && !DRY) {
    fs.writeFileSync(path.join(ROOT, 'config/skills.json'), JSON.stringify(registry, null, 2) + '\n');
    generateDocs();
    ok('refreshed skill descriptions in skills.json');
  }
  log(`\n${c.green}Update complete.${c.reset}`);
}

function cmdOverride(agentId, skillName) {
  const agents = loadJson('config/agents.json');
  const agent = resolveAgent(agents, agentId);
  const registry = loadJson('config/skills.json');
  const name = validateSkillName(skillName);

  const skill = registry.skills.find((s) => s.name === name);
  if (skill && skill.source === 'local') {
    warn(`${name} is a local skill you own — edit skills/${name}/ directly instead of overriding.`);
    return;
  }

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

  applyOverlay(skill || { name, scope: 'tech-leads-club' }, agent);
  if (!DRY && skill) generateDocs();
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

function cmdList(agentId) {
  const agents = loadJson('config/agents.json');
  const agent = resolveAgent(agents, agentId);
  const { skills } = loadJson('config/skills.json');

  log(`${c.bold}Skills for ${agent.id}${c.reset} (skillsDir: ${agent.skillsDir})\n`);
  const pad = Math.max(...skills.map((s) => s.name.length));
  for (const s of skills) {
    const dest = skillDest(s, agent);
    let state;
    if (s.installScope === 'none') state = `${c.dim}n/a${c.reset}`;
    else if (!lexists(dest)) state = `${c.yellow}missing${c.reset}`;
    else if (isSymlink(dest)) state = `${c.green}symlink${c.reset}`;
    else state = `${c.green}installed${c.reset}`;
    const ext = s.extended ? ` ${c.cyan}[override]${c.reset}` : '';
    log(`  ${s.name.padEnd(pad)}  ${s.source.padEnd(16)} ${state}${ext}`);
  }
}

// Undo setup: remove the global config symlink, uninstall the skills setup
// installed globally, drop personal + project-local links.
function cmdDestroy(agentId) {
  const agents = loadJson('config/agents.json');
  const agent = resolveAgent(agents, agentId);
  const { skills } = loadJson('config/skills.json');

  log(`${c.bold}Tearing down ${agent.id}${c.reset} (undoes setup)`);

  log(`\n${c.bold}Global config${c.reset}`);
  removeConfigSymlink(agent.configPath);

  log(`\n${c.bold}Skills${c.reset}`);
  for (const skill of skills) uninstallSkill(skill, agent);

  const personalDir = path.join(ROOT, 'personal');
  if (isDir(personalDir)) {
    log(`\n${c.bold}Personal${c.reset}`);
    for (const name of fs.readdirSync(personalDir)) {
      const sd = path.join(personalDir, name);
      if (!isDir(sd) || !lexists(path.join(sd, 'SKILL.md'))) continue;
      unlinkIfSymlink(path.join(agent.skillsDir, name));
    }
  }

  if (agent.projectDir || agent.projectConfig) {
    log(`\n${c.bold}Project-local links${c.reset}`);
    if (agent.projectDir) unlinkIfSymlink(path.join(ROOT, agent.projectDir));
    if (agent.projectConfig) unlinkIfSymlink(path.join(ROOT, agent.projectConfig));
  }

  log(`\n${c.green}Teardown complete. Only setup-managed skills and symlinks were removed.${c.reset}`);
}

// Remove the global config symlink only if it points at this repo's AGENTS.global.md.
function removeConfigSymlink(configPath) {
  if (!lexists(configPath)) { skip(`${configPath} not present`); return; }
  if (!isSymlink(configPath)) { warn(`${configPath} is a real file — leaving it untouched`); return; }
  const expected = path.join(ROOT, 'AGENTS.global.md');
  const actual = path.resolve(path.dirname(configPath), fs.readlinkSync(configPath));
  if (actual !== expected) { warn(`${configPath} points elsewhere (${actual}) — leaving it untouched`); return; }
  if (DRY) { log(`${c.dim}[dry-run]${c.reset} rm ${configPath}`); return; }
  fs.unlinkSync(configPath);
  ok(`removed ${configPath}`);
}

// Uninstall a skill: unlink symlinks, rm -rf vendor dirs.
// Skips installScope=none and project-local skills unless force=true.
function uninstallSkill(skill, agent, { force = false } = {}) {
  const name = validateSkillName(skill.name);
  const installScope = skill.installScope || 'global';
  if (installScope === 'none' || (!force && installScope === 'local')) {
    const reason = installScope === 'local' ? 'project-local'
      : 'installScope=none';
    skip(`${name} (${reason})`);
    return;
  }
  const dest = skillDest(skill, agent);
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
function cmdDelete(agentId, skillName) {
  const agents = loadJson('config/agents.json');
  const agent = resolveAgent(agents, agentId);
  const registry = loadJson('config/skills.json');
  const name = validateSkillName(skillName);

  const skill = registry.skills.find((s) => s.name === name);
  if (!skill) throw new UserError(`"${name}" is not in skills.json — nothing to delete.`);

  log(`${c.bold}Deleting ${name}${c.reset} (${skill.source})`);

  // Filesystem uninstall: symlink unlink (local) / vendor rm -rf; extended/ left intact.
  uninstallSkill(skill, agent, { force: true });
  if (skill.extended && isDir(path.join(ROOT, 'extended', name))) {
    log(`${c.dim}kept extended/${name}/ (override overlay preserved)${c.reset}`);
  }

  // Deregister + regenerate the auto-doc.
  registry.skills = registry.skills.filter((s) => s.name !== name);
  if (DRY) {
    log(`${c.dim}[dry-run]${c.reset} remove ${name} from config/skills.json + regenerate ${DOC_PATH}`);
  } else {
    fs.writeFileSync(path.join(ROOT, 'config/skills.json'), JSON.stringify(registry, null, 2) + '\n');
    ok(`removed ${name} from skills.json`);
    generateDocs();
  }
  log(`\n${c.green}Deleted ${name}.${c.reset}`);
}

function cmdStatusline(force) {
  const agents = loadJson('config/agents.json');
  const dest = expandHome((agents['claude-code'] && agents['claude-code'].statuslinePath) || '~/.claude/statusline-command.sh');
  const src = path.join(ROOT, 'config', 'statusline-command.sh');
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

// ---------------------------------------------------------------------------
// Doc generation (internal; run by add/override)
// ---------------------------------------------------------------------------

const SCOPE_SECTIONS = [
  { key: 'built', title: 'Built in this project' },
  { key: 'local-only', title: 'Local-only (project)' },
  { key: 'tech-leads-club', title: 'Tech Leads Club' },
  { key: 'matt-pocock', title: 'Matt Pocock' },
];

function skillPath(s) {
  if (s.scope === 'built') return ` (\`skills/${s.name}/SKILL.md\`)`;
  if (s.scope === 'local-only') return ` (\`.agents/skills/${s.name}/SKILL.md\`)`;
  return '';
}

const DOC_PATH = 'docs/AGENT-SKILLS.md';
const DOC_MARKER = '<!-- fsvskills:generated — do not edit below this line; regenerated from config/skills.json -->';

function generateDocs() {
  const { skills } = loadJson('config/skills.json');

  // Preserve the hand-written preamble above the marker; regenerate everything below it.
  const docPath = path.join(ROOT, DOC_PATH);
  let preamble = '# Agent Skills';
  if (lexists(docPath)) {
    const existing = fs.readFileSync(docPath, 'utf8');
    const cut = existing.indexOf(DOC_MARKER);
    const at = cut !== -1 ? cut : existing.indexOf('## Global Skills Registry');
    if (at !== -1) preamble = existing.slice(0, at).trimEnd();
  }

  const lines = [preamble, '', DOC_MARKER, '', '## Global Skills Registry', ''];
  for (const section of SCOPE_SECTIONS) {
    const inScope = skills.filter((s) => s.scope === section.key).sort((a, b) => a.name.localeCompare(b.name));
    if (!inScope.length) {
      if (section.key === 'matt-pocock') {
        lines.push(`### ${section.title}`, '', '_No Matt Pocock skills installed yet. Add one with:_ `fsvskills add claude-code <skill> --source matt-pocock`', '');
      }
      continue;
    }
    lines.push(`### ${section.title}`, '');
    for (const s of inScope) {
      lines.push(`- **${s.name}**${skillPath(s)}: ${s.description}`);
    }
    lines.push('');
  }

  const overridden = skills.filter((s) => s.extended).sort((a, b) => a.name.localeCompare(b.name));
  if (overridden.length) {
    lines.push('## Overridden (extended)', '');
    lines.push('These skills carry a project-specific overlay in `extended/<name>/` (applied as `SKILL.extended.md` and optional `references/`):', '');
    for (const s of overridden) {
      lines.push(`- **${s.name}** — overlays the ${SCOPE_SECTIONS.find((x) => x.key === s.scope)?.title || s.source} skill.`);
    }
    lines.push('');
  }

  const out = lines.join('\n').replace(/\n{3,}/g, '\n\n').trimEnd() + '\n';
  if (DRY) { log(`${c.dim}[dry-run]${c.reset} write ${DOC_PATH} (${overridden.length} overrides, ${skills.length} skills)`); return; }
  ensureDir(path.dirname(docPath));
  fs.writeFileSync(docPath, out);
  ok(`generated ${DOC_PATH} (${skills.length} skills)`);
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

const HELP = `${c.bold}fsvskills${c.reset} — skill manager for AI coding agents

${c.bold}Usage:${c.reset} fsvskills <command> [args] [--dry-run]

${c.bold}Commands:${c.reset}
  setup <agent>                 Bootstrap: global config + skills + overrides + project-local links
  destroy <agent>               Undo setup (remove config, uninstall skills, drop links)
  add <agent> <skill> [--source <s>] [--local]   Install one skill (registers it if new; --local installs to .agents/skills/)
  delete <agent> <skill>        Remove one skill (uninstall + deregister; keeps extended/)
  update <agent> <skills|--all> Update vendor skills (Tech Leads Club / Matt Pocock).
                                Pass a comma- or space-separated list, or --all for every vendor skill.
  override <agent> <skill>      Scaffold extended/<skill>/ and apply the overlay
  list <agent>                  Show each skill's source and install state
  statusline [--force]          Install the Claude Code status line script
  help                          Show this message

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
    case 'setup': cmdSetup(rest[0]); break;
    case 'destroy': cmdDestroy(rest[0]); break;
    case 'add': {
      if (!rest[1]) throw new UserError('Usage: fsvskills add <agent> <skill> [--source <s>] [--local]');
      cmdAdd(rest[0], rest[1], flags.source, flags);
      break;
    }
    case 'delete': {
      if (!rest[1]) throw new UserError('Usage: fsvskills delete <agent> <skill>');
      cmdDelete(rest[0], rest[1]);
      break;
    }
    case 'update': cmdUpdate(rest[0], rest.slice(1), flags.all); break;
    case 'override': {
      if (!rest[1]) throw new UserError('Usage: fsvskills override <agent> <skill>');
      cmdOverride(rest[0], rest[1]);
      break;
    }
    case 'list': cmdList(rest[0]); break;
    case 'statusline': cmdStatusline(flags.force); break;
    default:
      throw new UserError(`Unknown command "${command}". Run \`fsvskills help\`.`);
  }
}

try {
  main();
} catch (e) {
  if (e instanceof UserError) { fail(e.message); process.exit(1); }
  throw e;
}
