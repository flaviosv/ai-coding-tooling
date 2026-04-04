# Token Savings — Rollback Plan

## Baseline
- **Commit SHA:** 408fce03b0fa55ba270220558c91d31fa7d752fc
- **Date:** 2026-04-04
- **Total .md files:** 79 (excluding README.md)
- **Total lines (before):** 21,115

## Per-File Baseline

| File | Original Lines |
|------|---------------|
| AGENTS.global.md | 134 |
| AGENTS.md | 37 |
| CLAUDE.md | 37 (symlink to AGENTS.md) |
| GEMINI.md | 37 (symlink to AGENTS.md) |
| docs/ARCHITECTURE.md | 99 |
| docs/PROJECT_DETAILS.md | 81 |
| extended/coding-guidelines/SKILL.md | 75 |
| extended/coding-guidelines/reference/adobe-commerce-coding-guidelines.md | 383 |
| extended/coding-guidelines/reference/django-coding-guidelines.md | 378 |
| extended/coding-guidelines/reference/gin-coding-guidelines.md | 204 |
| extended/coding-guidelines/reference/go-coding-guidelines.md | 518 |
| extended/coding-guidelines/reference/langchain-langgraph-coding-guidelines.md | 278 |
| extended/coding-guidelines/reference/php-coding-guidelines.md | 220 |
| extended/coding-guidelines/reference/playwright-coding-guidelines.md | 225 |
| extended/coding-guidelines/reference/python-coding-guidelines.md | 612 |
| extended/coding-guidelines/reference/solid-guidelines.md | 94 |
| extended/security-best-practices/SKILL.md | 49 |
| extended/security-best-practices/reference/gin-security-best-practices.md | 404 |
| extended/security-best-practices/reference/langchain-langgraph-security-best-practices.md | 339 |
| extended/security-best-practices/reference/playwright-security-best-practices.md | 239 |
| extended/security-best-practices/reference/python-security-best-practices.md | 396 |
| extended/skill-architect/SKILL.md | 172 |
| personal/generate-knowledge-base/SKILL.md | 230 |
| personal/raindrop-kb-convert/SKILL.md | 263 |
| skills/agent-setup/SKILL.md | 223 |
| skills/agent-setup/references/claude-code.md | 32 |
| skills/agent-setup/references/gemini-cli.md | 51 |
| skills/architecture-evaluate/SKILL.md | 271 |
| skills/code-review/SKILL.md | 267 |
| skills/code-review/references/adobe-commerce-code-review.md | 142 |
| skills/code-review/references/clean-code-checklist.md | 113 |
| skills/code-review/references/django-code-review.md | 302 |
| skills/code-review/references/gin-code-review.md | 238 |
| skills/code-review/references/golang-code-review.md | 406 |
| skills/code-review/references/langchain-langgraph-code-review.md | 154 |
| skills/code-review/references/php-code-review.md | 233 |
| skills/code-review/references/playwright-code-review.md | 153 |
| skills/code-review/references/review-checklist.md | 98 |
| skills/code-review/references/solid-principles.md | 108 |
| skills/code/SKILL.md | 28 |
| skills/documentation-upsert/SKILL.md | 239 |
| skills/performance-review/SKILL.md | 141 |
| skills/performance-review/references/adobe-commerce-performance-review.md | 424 |
| skills/performance-review/references/django-performance-review.md | 436 |
| skills/performance-review/references/gin-performance-review.md | 255 |
| skills/performance-review/references/golang-performance-review.md | 620 |
| skills/performance-review/references/langchain-langgraph-performance-review.md | 272 |
| skills/performance-review/references/performance-checklist.md | 95 |
| skills/performance-review/references/php-performance-review.md | 369 |
| skills/performance-review/references/playwright-performance-review.md | 254 |
| skills/performance-review/references/python-performance-review.md | 413 |
| skills/report-tech-debt/SKILL.md | 151 |
| skills/skill-alias/SKILL.md | 187 |
| skills/skill-installation/SKILL.md | 151 |
| skills/skill-update/SKILL.md | 196 |
| skills/skill-update/references/vendors.md | 49 |
| skills/tech-reference-add/SKILL.md | 372 |
| skills/tests-code-review/SKILL.md | 273 |
| skills/tests-code-review/references/adobe-commerce-tests-code-review.md | 405 |
| skills/tests-code-review/references/django-tests-code-review.md | 439 |
| skills/tests-code-review/references/gin-tests-code-review.md | 254 |
| skills/tests-code-review/references/golang-tests-code-review.md | 603 |
| skills/tests-code-review/references/langchain-langgraph-tests-code-review.md | 262 |
| skills/tests-code-review/references/php-tests-code-review.md | 402 |
| skills/tests-code-review/references/playwright-tests-code-review.md | 299 |
| skills/tests-code-review/references/python-tests-code-review.md | 448 |
| skills/tests-code-review/references/test-review-checklist.md | 100 |
| skills/tests-tdd/SKILL.md | 106 |
| skills/tests/SKILL.md | 142 |
| skills/tests/references/adobe-commerce-tests.md | 511 |
| skills/tests/references/coverage-guide.md | 121 |
| skills/tests/references/django-tests.md | 487 |
| skills/tests/references/gin-tests.md | 403 |
| skills/tests/references/golang-tests.md | 710 |
| skills/tests/references/langchain-langgraph-tests.md | 415 |
| skills/tests/references/php-tests.md | 738 |
| skills/tests/references/playwright-tests.md | 346 |
| skills/tests/references/python-tests.md | 608 |
| skills/tests/references/testing-patterns.md | 96 |

## Rollback Instructions

### Option 1: Selective revert (only .md files, preserves other commits)

```bash
# 1. Identify the token-savings commit(s)
git log --oneline --all --grep="token"

# 2. Create a reverse patch of only .md files from that commit range
git diff 408fce03..HEAD -- '*.md' > /tmp/token-savings.patch

# 3. Reverse-apply the patch
git apply -R /tmp/token-savings.patch

# 4. Commit the revert
git add -A '*.md'
git commit -m "Revert token savings — reverting .md files to pre-optimization state"
```

### Option 2: Full revert (if no other commits landed after)
```bash
git revert <token-savings-sha>
```

### Option 3: Per-file revert (surgical)
```bash
# Restore a single file to its pre-optimization state
git checkout 408fce03 -- path/to/file.md
```

## Results

Original 79 files: **21,115 → 18,557 lines (−2,558 lines, −12.1%)**
New files added (templates + docs-writer extension): **+314 lines (7 files)**
Overall project total: **18,871 lines**

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| AGENTS.global.md | 134 | 138 | +4 (Phase 8 additions) |
| AGENTS.md | 37 | 34 | −3 |
| CLAUDE.md (symlink) | 37 | 34 | −3 |
| GEMINI.md (symlink) | 37 | 34 | −3 |
| docs/ARCHITECTURE.md | 99 | 94 | −5 |
| docs/PROJECT_DETAILS.md | 81 | 80 | −1 |
| extended/coding-guidelines/SKILL.md | 75 | 48 | −27 |
| extended/coding-guidelines/reference/adobe-commerce-coding-guidelines.md | 383 | 285 | −98 |
| extended/coding-guidelines/reference/django-coding-guidelines.md | 378 | 317 | −61 |
| extended/coding-guidelines/reference/gin-coding-guidelines.md | 204 | 205 | +1 |
| extended/coding-guidelines/reference/go-coding-guidelines.md | 518 | 477 | −41 |
| extended/coding-guidelines/reference/langchain-langgraph-coding-guidelines.md | 278 | 239 | −39 |
| extended/coding-guidelines/reference/php-coding-guidelines.md | 220 | 212 | −8 |
| extended/coding-guidelines/reference/playwright-coding-guidelines.md | 225 | 198 | −27 |
| extended/coding-guidelines/reference/python-coding-guidelines.md | 612 | 549 | −63 |
| extended/coding-guidelines/reference/solid-guidelines.md | 94 | 84 | −10 |
| extended/security-best-practices/SKILL.md | 49 | 44 | −5 |
| extended/security-best-practices/reference/gin-security-best-practices.md | 404 | 326 | −78 |
| extended/security-best-practices/reference/langchain-langgraph-security-best-practices.md | 339 | 310 | −29 |
| extended/security-best-practices/reference/playwright-security-best-practices.md | 239 | 210 | −29 |
| extended/security-best-practices/reference/python-security-best-practices.md | 396 | 380 | −16 |
| extended/skill-architect/SKILL.md | 172 | 166 | −6 |
| personal/generate-knowledge-base/SKILL.md | 230 | 228 | −2 |
| personal/raindrop-kb-convert/SKILL.md | 263 | 263 | 0 |
| skills/agent-setup/SKILL.md | 223 | 219 | −4 |
| skills/agent-setup/references/claude-code.md | 32 | 31 | −1 |
| skills/agent-setup/references/gemini-cli.md | 51 | 50 | −1 |
| skills/architecture-evaluate/SKILL.md | 271 | 269 | −2 |
| skills/code-review/SKILL.md | 267 | 257 | −10 |
| skills/code-review/references/adobe-commerce-code-review.md | 142 | 116 | −26 |
| skills/code-review/references/clean-code-checklist.md | 113 | 94 | −19 |
| skills/code-review/references/django-code-review.md | 302 | 226 | −76 |
| skills/code-review/references/gin-code-review.md | 238 | 216 | −22 |
| skills/code-review/references/golang-code-review.md | 406 | 377 | −29 |
| skills/code-review/references/langchain-langgraph-code-review.md | 154 | 142 | −12 |
| skills/code-review/references/php-code-review.md | 233 | 182 | −51 |
| skills/code-review/references/playwright-code-review.md | 153 | 140 | −13 |
| skills/code-review/references/review-checklist.md | 98 | 85 | −13 |
| skills/code-review/references/solid-principles.md | 108 | 72 | −36 |
| skills/code/SKILL.md | 28 | 27 | −1 |
| skills/documentation-upsert/SKILL.md | 239 | 239 | 0 |
| skills/performance-review/SKILL.md | 141 | 123 | −18 |
| skills/performance-review/references/adobe-commerce-performance-review.md | 424 | 376 | −48 |
| skills/performance-review/references/django-performance-review.md | 436 | 343 | −93 |
| skills/performance-review/references/gin-performance-review.md | 255 | 221 | −34 |
| skills/performance-review/references/golang-performance-review.md | 620 | 521 | −99 |
| skills/performance-review/references/langchain-langgraph-performance-review.md | 272 | 243 | −29 |
| skills/performance-review/references/performance-checklist.md | 95 | 78 | −17 |
| skills/performance-review/references/php-performance-review.md | 369 | 307 | −62 |
| skills/performance-review/references/playwright-performance-review.md | 254 | 202 | −52 |
| skills/performance-review/references/python-performance-review.md | 413 | 358 | −55 |
| skills/report-tech-debt/SKILL.md | 151 | 148 | −3 |
| skills/skill-alias/SKILL.md | 187 | 187 | 0 |
| skills/skill-installation/SKILL.md | 151 | 150 | −1 |
| skills/skill-update/SKILL.md | 196 | 196 | 0 |
| skills/skill-update/references/vendors.md | 49 | 44 | −5 |
| skills/tech-reference-add/SKILL.md | 372 | 327 | −45 |
| skills/tests-code-review/SKILL.md | 273 | 260 | −13 |
| skills/tests-code-review/references/adobe-commerce-tests-code-review.md | 405 | 375 | −30 |
| skills/tests-code-review/references/django-tests-code-review.md | 439 | 361 | −78 |
| skills/tests-code-review/references/gin-tests-code-review.md | 254 | 197 | −57 |
| skills/tests-code-review/references/golang-tests-code-review.md | 603 | 472 | −131 |
| skills/tests-code-review/references/langchain-langgraph-tests-code-review.md | 262 | 227 | −35 |
| skills/tests-code-review/references/php-tests-code-review.md | 402 | 330 | −72 |
| skills/tests-code-review/references/playwright-tests-code-review.md | 299 | 267 | −32 |
| skills/tests-code-review/references/python-tests-code-review.md | 448 | 401 | −47 |
| skills/tests-code-review/references/test-review-checklist.md | 100 | 86 | −14 |
| skills/tests-tdd/SKILL.md | 106 | 100 | −6 |
| skills/tests/SKILL.md | 142 | 115 | −27 |
| skills/tests/references/adobe-commerce-tests.md | 511 | 464 | −47 |
| skills/tests/references/coverage-guide.md | 121 | 80 | −41 |
| skills/tests/references/django-tests.md | 487 | 431 | −56 |
| skills/tests/references/gin-tests.md | 403 | 339 | −64 |
| skills/tests/references/golang-tests.md | 710 | 614 | −96 |
| skills/tests/references/langchain-langgraph-tests.md | 415 | 369 | −46 |
| skills/tests/references/php-tests.md | 738 | 625 | −113 |
| skills/tests/references/playwright-tests.md | 346 | 302 | −44 |
| skills/tests/references/python-tests.md | 608 | 535 | −73 |
| skills/tests/references/testing-patterns.md | 96 | 86 | −10 |
| **TOTAL (79 original files)** | **21,115** | **18,557** | **−2,558 (−12.1%)** |
