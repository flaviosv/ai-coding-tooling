#!/usr/bin/env node
// Validates the templates/ vs references/ split (see CLAUDE.md's "Reference vs.
// Template Files"): every skill -> templates/ link must resolve to a real file, every
// CLAUDE.global.md -> references/ link must resolve to a real file, and neither side
// may cross into the other's folder — skills never link references/, CLAUDE.global.md
// never links templates/. Exit 0 on a clean report, 1 if any check fails.
//
// STATE.md files are exempt: they're an append-only decision log (docs/SKILL-ADR.md)
// where a past entry legitimately names a file that has since moved — not a live
// reference. Same class of exemption as scripts/bin/misc/check-no-stale-refs.mjs.
//
// Usage: node scripts/bin/misc/check-references.mjs

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(path.dirname(path.dirname(SCRIPT_DIR))); // scripts/bin/misc/ is three levels down

const TEMPLATE_LINK_RE = /(?:\.\.\/)+templates\/([A-Za-z0-9._-]+\.md)/g;
const REFERENCE_LINK_RE = /(?:\.\.\/)+references\/([A-Za-z0-9._-]+\.md)/g;
const CLAUDE_TEMPLATES_RE = /~\/\.claude\/templates\/([A-Za-z0-9._-]+\.md)/g;
const CLAUDE_REFERENCES_RE = /~\/\.claude\/references\/([A-Za-z0-9._-]+\.md)/g;

const isStateFile = (relPath) => relPath.endsWith('/STATE.md') || relPath === 'STATE.md';

function walkMarkdown(dir) {
  const out = [];
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walkMarkdown(p));
    else if (entry.isFile() && entry.name.endsWith('.md')) out.push(p);
  }
  return out;
}

let failures = 0;
const fails = [];
const fail = (msg) => { fails.push(msg); failures++; };
const passes = [];
const pass = (msg) => passes.push(msg);

// 1. skills/ + extended/ -> templates/ links must resolve; must never link references/.
const skillFiles = [
  ...walkMarkdown(path.join(ROOT, 'skills')),
  ...walkMarkdown(path.join(ROOT, 'extended')),
].filter((f) => !isStateFile(path.relative(ROOT, f)));

let templateLinksChecked = 0;
for (const file of skillFiles) {
  const rel = path.relative(ROOT, file);
  const text = fs.readFileSync(file, 'utf8');

  for (const m of text.matchAll(TEMPLATE_LINK_RE)) {
    templateLinksChecked++;
    const target = path.join(ROOT, 'templates', m[1]);
    if (!fs.existsSync(target)) fail(`${rel}: links templates/${m[1]}, which does not exist`);
  }
  for (const m of text.matchAll(REFERENCE_LINK_RE)) {
    fail(`${rel}: links references/${m[1]} — skills must not reference references/ (CLAUDE.md-only, see CLAUDE.md's "Reference vs. Template Files")`);
  }
}
pass(`${templateLinksChecked} skill→templates/ link(s) checked across ${skillFiles.length} file(s)`);

// 2. CLAUDE.global.md -> references/ links must resolve; must never link templates/.
const claudeFile = path.join(ROOT, 'CLAUDE.global.md');
const claudeText = fs.readFileSync(claudeFile, 'utf8');

let referenceLinksChecked = 0;
for (const m of claudeText.matchAll(CLAUDE_REFERENCES_RE)) {
  referenceLinksChecked++;
  const target = path.join(ROOT, 'references', m[1]);
  if (!fs.existsSync(target)) fail(`CLAUDE.global.md: links ~/.claude/references/${m[1]}, which does not exist`);
}
for (const m of claudeText.matchAll(CLAUDE_TEMPLATES_RE)) {
  fail(`CLAUDE.global.md: links ~/.claude/templates/${m[1]} — CLAUDE.md must not reference templates/ (skills-only, see CLAUDE.md's "Reference vs. Template Files")`);
}
pass(`${referenceLinksChecked} CLAUDE.global.md→references/ link(s) checked`);

for (const p of passes) console.log(`OK    ${p}`);
for (const f of fails) console.error(`FAIL  ${f}`);

if (failures) {
  console.error(`\nFAIL — ${failures} reference issue(s) found.`);
  process.exit(1);
}
console.log('\nOK — all templates/ and references/ cross-references are valid.');
