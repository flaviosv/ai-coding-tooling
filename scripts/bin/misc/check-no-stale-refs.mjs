#!/usr/bin/env node
// Fails if a given string reappears anywhere in tracked files, so a removed
// file/skill/template can't silently regain a stale reference later.
// Usage: node scripts/bin/misc/check-no-stale-refs.mjs [pattern]

import { execSync } from "node:child_process";

const PATTERN = process.argv[2] || "token-efficiency-rules";

// Files allowed to keep the string as a historical record, not a live reference.
const ALLOWED = new Set(["docs/harness-evaluation.md", "scripts/bin/misc/check-no-stale-refs.mjs"]);
// Every skill's STATE.md is the same class of historical record (docs/skill-adr.md) —
// append-only, so a past decision entry legitimately names a since-removed file.
const isAllowed = (file) => ALLOWED.has(file) || file.endsWith("/STATE.md") || file === "STATE.md";

let output = "";
try {
  output = execSync(`git grep -n -- "${PATTERN}"`, { encoding: "utf8" });
} catch (err) {
  if (err.status === 1) {
    console.log(`OK — no references to "${PATTERN}" found.`);
    process.exit(0);
  }
  throw err;
}

const hits = output
  .trim()
  .split("\n")
  .filter((line) => !isAllowed(line.split(":")[0]));

if (hits.length === 0) {
  console.log(`OK — no references to "${PATTERN}" found (outside the allowed historical record).`);
  process.exit(0);
}

console.error(`FAIL — found ${hits.length} reference(s) to "${PATTERN}":\n`);
for (const line of hits) console.error(`  ${line}`);
process.exit(1);
