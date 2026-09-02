#!/usr/bin/env node
// Writes/updates a build-feature progress.md checkpoint in one call, replacing
// the hand-edit ritual (bump last_completed_step, append/replace a Step Log
// line, set any Run State fields) that used to take 2-3 separate Edit calls
// per step. See ../references/progress-schema.md for the file's shape.
//
// Usage:
//   node progress.mjs <progress.md path> --step <id> --label <text> --detail <text> [--set field=value]...
//   node progress.mjs <progress.md path> --init --task-id <id> --description <text> \
//     --worktree-path <path> --branch <name> --base-branch <name> --target-branch <name> \
//     --gh-login <login> --human-review <yes|no> [--human-review-exclude <csv>]
//
// Idempotent: re-running the same --step overwrites that step's own Step Log
// line in place rather than appending a duplicate, so a resumed run that
// re-executes a step already logged (a crash mid-step) does not double-log it.

import { readFileSync, writeFileSync, existsSync } from 'node:fs';

function parseArgs(argv) {
  const args = { set: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--init') { args.init = true; continue; }
    if (a === '--set') { args.set.push(argv[++i]); continue; }
    if (a.startsWith('--')) { args[a.slice(2)] = argv[++i]; continue; }
  }
  return args;
}

function fail(msg) {
  console.error(`progress.mjs: ${msg}`);
  process.exit(1);
}

const [, , filePath, ...rest] = process.argv;
if (!filePath) fail('missing <progress.md path>');
const args = parseArgs(rest);

function setRunStateField(content, field, value) {
  const lineRe = new RegExp(`^- ${field}: .*$`, 'm');
  const line = `- ${field}: ${value}`;
  if (lineRe.test(content)) return content.replace(lineRe, line);
  // Field not present yet — insert right before the "## Checkpoints" heading,
  // reusing the blank line already separating the two sections.
  return content.replace(/\n\n## Checkpoints/, `\n${line}\n\n## Checkpoints`);
}

function setStepLogLine(content, stepId, label, detail) {
  const newLine = `- Step ${stepId} (${label}): done — ${detail}`;
  const existingRe = new RegExp(`^- Step ${stepId} \\([^)]*\\):.*$`, 'm');
  if (existingRe.test(content)) return content.replace(existingRe, newLine);
  // No existing line for this step — append at the end of the file.
  const trimmed = content.replace(/\n+$/, '');
  return `${trimmed}\n${newLine}\n`;
}

if (args.init) {
  for (const req of ['task-id', 'description', 'worktree-path', 'branch', 'base-branch', 'target-branch', 'gh-login', 'human-review']) {
    if (!args[req]) fail(`--init requires --${req}`);
  }
  if (existsSync(filePath)) fail(`${filePath} already exists — --init only writes a fresh file`);
  const content = `# Progress: ${args['task-id']} — ${args.description}

## Run State

- status: in-progress
- last_completed_step: 0
- worktree_path: ${args['worktree-path']}
- branch: ${args.branch}
- base_branch: ${args['base-branch']}
- target_branch: ${args['target-branch']}
- gh_login: ${args['gh-login']}
- human_review: ${args['human-review']}
- human_review_exclude: ${args['human-review-exclude'] || ''}

## Checkpoints

- spec: n/a
- design: n/a
- complete_review: n/a

## Step Log

`;
  writeFileSync(filePath, content);
  console.log(`Initialized ${filePath}`);
  process.exit(0);
}

if (!args.step) fail('missing --step (or pass --init to create a fresh file)');
if (!args.label) fail('missing --label');
if (!args.detail) fail('missing --detail');

let content = readFileSync(filePath, 'utf8');

content = setRunStateField(content, 'last_completed_step', args.step);
content = setStepLogLine(content, args.step, args.label, args.detail);

for (const kv of args.set) {
  const eq = kv.indexOf('=');
  if (eq === -1) fail(`--set expects field=value, got: ${kv}`);
  const field = kv.slice(0, eq);
  const value = kv.slice(eq + 1);
  content = setRunStateField(content, field, value);
}

writeFileSync(filePath, content);
console.log(`Step ${args.step} logged.`);
