#!/usr/bin/env node
// Validates the shared-reference rule (see CLAUDE.global.md's "Shared Reference Files"):
// every CLAUDE.global.md -> ~/.claude/references/ link must resolve to a real file in
// references/, no skill may link references/ (it is CLAUDE.md-only — a skill keeps what
// it links inside its own directory), and nothing may link the removed templates/ folder.
// Exit 0 on a clean report, 1 if any check fails.
//
// STATE.md files are exempt: they're an append-only decision log
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
const REFERENCE_LINK_RE = /(?:\.\.\/){2,}references\/([A-Za-z0-9._-]+\.md)/g;
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
const claudeFile = path.join(ROOT, 'CLAUDE.global.md');
const claudeText = fs.readFileSync(claudeFile, 'utf8');

let referenceLinksChecked = 0;
for (const m of claudeText.matchAll(CLAUDE_REFERENCES_RE)) {
  referenceLinksChecked++;
  const target = path.join(ROOT, 'references', m[1]);
  if (!fs.existsSync(target)) fail(`CLAUDE.global.md: links ~/.claude/references/${m[1]}, which does not exist`);
}
for (const m of claudeText.matchAll(CLAUDE_TEMPLATES_RE)) {
  fail(`CLAUDE.global.md: links ~/.claude/templates/${m[1]} — templates/ was removed`);
}
pass(`${referenceLinksChecked} CLAUDE.global.md→references/ link(s) checked`);

for (const p of passes) console.log(`OK    ${p}`);
for (const f of fails) console.error(`FAIL  ${f}`);

if (fails.length) {
  console.error(`\nFAIL — ${fails.length} reference issue(s) found.`);
  process.exit(1);
}
console.log('\nOK — all references/ cross-references are valid.');
