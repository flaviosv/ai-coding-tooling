#!/usr/bin/env node
// Validates the shared-reference rule (see docs/codebase/ARCHITECTURE.md):
// every CLAUDE.global.md -> ~/.claude/references/ link must resolve to a real file in
// references/, no skill may link references/ (it is CLAUDE.md-only — a skill keeps what
// it links inside its own directory), and nothing may link the removed templates/ folder.
//
// Also validates that markdown links inside skill files still resolve once installed.
// A relative link is written against the file's location in this repo, but skills/,
// extended/ overlays, references/, and CLAUDE.global.md are all symlinked into ~/.claude
// at install time — which can shift a file's *effective* directory depth (e.g.
// extended/<skill>/SKILL.md installs as ~/.claude/skills/<skill>/SKILL.extended.md, one
// directory shallower than extended/<skill>/ is in the repo). This pass resolves each
// relative .md link against the file's *installed* directory instead of its repo
// directory, mirroring how an agent actually reads it after `fs-harness setup`.
//
// Exit 0 on a clean report, 1 if any check fails.
//
// STATE.md files are exempt from every pass: they're an append-only decision log
// where a past entry legitimately names a file that has since moved — not a live
// reference. Same class of exemption as scripts/bin/misc/check-no-stale-refs.mjs.
//
// Usage: node scripts/bin/misc/check-references.mjs

import fs from 'node:fs';
import path from 'node:path';
import {
  ROOT, REFERENCES_DIR, CONFIG_PATH,
  lexists, isDir, skillDest, referencesLinkPath, overlayReferencesDestName, loadJson,
} from '../fs-harness.mjs';

const TEMPLATE_LINK_RE = /(?:\.\.\/)+templates\/([A-Za-z0-9._-]+\.md)/g;
const REFERENCE_LINK_RE = /(?:\.\.\/){2,}references\/([A-Za-z0-9._-]+\.md)/g;
const CLAUDE_TEMPLATES_RE = /~\/\.claude\/templates\/([A-Za-z0-9._-]+\.md)/g;
const CLAUDE_REFERENCES_RE = /~\/\.claude\/references\/([A-Za-z0-9._-]+\.md)/g;
// A real markdown link whose target is a .md file, e.g. [text](../../docs/cli.md) or
// [text](path.md#anchor). Anchors are captured separately so they don't leak into the path.
const MD_LINK_RE = /\[[^\]]*\]\(([^)\s#]+\.md)(?:#[^)]*)?\)/g;

const isStateFile = (relPath) => relPath.endsWith('/STATE.md') || relPath === 'STATE.md';
const isRelativeLink = (p) => !/^([a-z]+:)?\/\//i.test(p) && !p.startsWith('~/') && !p.startsWith('/');

// node_modules (and similar dependency-install dirs, e.g. mermaid-studio's .deps/) hold
// bundled third-party runtime dependencies, not skill content — never symlinked from
// this repo, so they can't have the installed-location bug this file checks for, and
// their own READMEs' broken links are an upstream concern, not ours.
const SKIP_DIRS = new Set(['node_modules']);

function walkMarkdown(dir) {
  const out = [];
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory() && SKIP_DIRS.has(entry.name)) continue;
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walkMarkdown(p));
    else if (entry.isFile() && entry.name.endsWith('.md')) out.push(p);
  }
  return out;
}

const fails = [];
const fail = (msg) => fails.push(msg);
const passes = [];
const pass = (msg) => passes.push(msg);

// 1. skills/ + extended/ must never link the repo-root references/ or the removed templates/.
const skillFiles = [
  ...walkMarkdown(path.join(ROOT, 'skills')),
  ...walkMarkdown(path.join(ROOT, 'extended')),
].filter((f) => !isStateFile(path.relative(ROOT, f)));

for (const file of skillFiles) {
  const rel = path.relative(ROOT, file);
  const text = fs.readFileSync(file, 'utf8');
  for (const m of text.matchAll(TEMPLATE_LINK_RE)) {
    fail(`${rel}: links templates/${m[1]} — templates/ was removed; keep the file inside the skill`);
  }
  for (const m of text.matchAll(REFERENCE_LINK_RE)) {
    fail(`${rel}: links references/${m[1]} — skills must not reference the repo-root references/ (CLAUDE.md-only)`);
  }
  for (const m of text.matchAll(CLAUDE_REFERENCES_RE)) {
    fail(`${rel}: links ~/.claude/references/${m[1]} — skills must not reference references/ (CLAUDE.md-only)`);
  }
}
pass(`${skillFiles.length} skill file(s) checked for references/ and templates/ links`);

// 2. CLAUDE.global.md -> references/ links must resolve; must never link templates/.
const claudeGlobalFile = path.join(ROOT, 'CLAUDE.global.md');
const claudeGlobalText = fs.readFileSync(claudeGlobalFile, 'utf8');

let referenceLinksChecked = 0;
for (const m of claudeGlobalText.matchAll(CLAUDE_REFERENCES_RE)) {
  referenceLinksChecked++;
  const target = path.join(ROOT, 'references', m[1]);
  if (!fs.existsSync(target)) fail(`CLAUDE.global.md: links ~/.claude/references/${m[1]}, which does not exist`);
}
for (const m of claudeGlobalText.matchAll(CLAUDE_TEMPLATES_RE)) {
  fail(`CLAUDE.global.md: links ~/.claude/templates/${m[1]} — templates/ was removed`);
}
pass(`${referenceLinksChecked} CLAUDE.global.md→references/ link(s) checked`);

// 3. CLAUDE.md (project-root) is never installed/symlinked anywhere — Claude Code loads
// it directly from whatever repo it's sitting in. Its own relative .md links still need
// to resolve, but plainly against this repo, never through ~/.claude (see #4 below).
const claudeProjectFile = path.join(ROOT, 'CLAUDE.md');
if (lexists(claudeProjectFile)) {
  const text = fs.readFileSync(claudeProjectFile, 'utf8');
  let checked = 0;
  for (const m of text.matchAll(MD_LINK_RE)) {
    const linkPath = m[1];
    if (!isRelativeLink(linkPath)) continue;
    checked++;
    const resolved = path.resolve(path.dirname(claudeProjectFile), linkPath);
    if (!fs.existsSync(resolved)) fail(`CLAUDE.md: links ${linkPath}, which does not exist`);
  }
  pass(`${checked} CLAUDE.md project-relative link(s) checked`);
}

// 4. Installed-location resolution (see file header). Build the same repo-dir ->
// installed-dir map fs-harness.mjs's own install/override logic uses, then resolve
// every relative .md link in the mapped files against their *installed* directory.
//
// Known limitation: this is a plain regex scan, so a fenced code block that merely
// shows example link syntax could produce a false positive — none observed in this
// repo today, but worth knowing if a future skill embeds one.
function buildInstalledMappings() {
  const { skills } = loadJson('config/skills.json');
  const dirMirrors = [{ repoDir: REFERENCES_DIR, installedDir: referencesLinkPath() }];
  const singleFiles = [{ repoFile: claudeGlobalFile, installedFile: CONFIG_PATH }];
  const skipped = [];

  for (const skill of skills) {
    if (skill.installScope === 'none') continue;
    const dest = skillDest(skill);
    if (!lexists(dest)) { skipped.push(skill.name); continue; } // not installed on this machine yet

    // Vendor skills are read-only upstream content, so their own links are not checked.
    if (skill.source === 'local') {
      dirMirrors.push({ repoDir: path.join(ROOT, 'skills', skill.name), installedDir: dest });
    }

    if (skill.extended) {
      const extSkillFile = path.join(ROOT, 'extended', skill.name, 'SKILL.md');
      if (lexists(extSkillFile)) {
        singleFiles.push({ repoFile: extSkillFile, installedFile: path.join(dest, 'SKILL.extended.md') });
      }
      const extRefDir = path.join(ROOT, 'extended', skill.name, 'references');
      if (isDir(extRefDir)) {
        dirMirrors.push({ repoDir: extRefDir, installedDir: path.join(dest, overlayReferencesDestName(dest)) });
      }
    }
  }
  return { dirMirrors, singleFiles, skipped };
}

function toInstalledPath(absFile, { dirMirrors, singleFiles }) {
  for (const sf of singleFiles) if (sf.repoFile === absFile) return sf.installedFile;
  let best = null;
  for (const dm of dirMirrors) {
    const rel = path.relative(dm.repoDir, absFile);
    if (rel === '..' || rel.startsWith(`..${path.sep}`) || path.isAbsolute(rel)) continue;
    if (!best || dm.repoDir.length > best.repoDir.length) best = { ...dm, rel };
  }
  return best ? path.join(best.installedDir, best.rel) : null;
}

const mappings = buildInstalledMappings();
const filesToScan = new Set();
for (const sf of mappings.singleFiles) filesToScan.add(sf.repoFile);
for (const dm of mappings.dirMirrors) for (const f of walkMarkdown(dm.repoDir)) filesToScan.add(f);

let installedLinksChecked = 0;
let installedFilesChecked = 0;
for (const file of filesToScan) {
  const rel = path.relative(ROOT, file);
  if (isStateFile(rel)) continue;

  const installedFile = toInstalledPath(file, mappings);
  if (!installedFile) continue;

  const text = fs.readFileSync(file, 'utf8');
  let fileHadLink = false;
  for (const m of text.matchAll(MD_LINK_RE)) {
    const linkPath = m[1];
    if (!isRelativeLink(linkPath)) continue;
    fileHadLink = true;
    installedLinksChecked++;
    const resolved = path.resolve(path.dirname(installedFile), linkPath);
    if (!fs.existsSync(resolved)) {
      fail(`${rel}: links ${linkPath}, which resolves to ${resolved} once installed under ~/.claude — but that path does not exist there`);
    }
  }
  if (fileHadLink) installedFilesChecked++;
}
const skippedNote = mappings.skipped.length
  ? ` (skipped ${mappings.skipped.length} not-yet-installed skill(s): ${mappings.skipped.join(', ')})`
  : '';
pass(`${installedLinksChecked} installed-location link(s) checked across ${installedFilesChecked} file(s)${skippedNote}`);

for (const p of passes) console.log(`OK    ${p}`);
for (const f of fails) console.error(`FAIL  ${f}`);

if (fails.length) {
  console.error(`\nFAIL — ${fails.length} reference issue(s) found.`);
  process.exit(1);
}
console.log('\nOK — all references/ cross-references and installed-location links are valid.');
