---
name: kb-from-raindrop
description: >
  Converts a Raindrop.io bookmark collection into a consolidated knowledge base in the Obsidian vault.
  Fetches all bookmarks from a user-specified collection, reads their full content, clusters them by
  semantic topic, and generates deduplicated .md knowledge files — one per topic cluster — with
  development-relevant sections synthesized from the sources. Validates each file with web search
  suggestions kept strictly separate from Raindrop content.
  Use when user says "convert Raindrop collection", "generate knowledge base from bookmarks",
  "kb from raindrop", "create knowledge base from my Raindrop", "convert my bookmarks to notes",
  or "turn my Raindrop collection into a knowledge base".
  Requires Raindrop MCP connection. Do NOT use for general bookmark search, Raindrop organization,
  one-off link lookup, or generating knowledge bases from local files (use kb-from-folder for that).
metadata:
  author: flaviostudart
  version: 1.0.0
---

# kb-from-raindrop

Converts a Raindrop.io bookmark collection into a synthesized, deduplicated knowledge base. Each topic cluster becomes one `.md` file with structured sections derived from the actual content — not a link list, but a consolidated knowledge document. Web suggestions are added at the end of each file, strictly separated from Raindrop content.

## Prerequisites

CRITICAL: Before doing anything else, verify Raindrop MCP is connected by calling `find_collections` with no parameters. If the call fails, stop immediately and tell the user:

> "Raindrop MCP is not connected. Please ensure the Raindrop MCP server is running and try again."

CRITICAL: Never perform any write, update, or delete operation in Raindrop. This skill is read-only with respect to Raindrop. No exceptions.

## Workflow

### Step 1: Gather Input

Ask the user for the **collection name** to convert. Then:

1. Use `find_collections` with `search` set to the collection name to find it. If multiple matches exist, list them and ask the user to confirm which one.
2. Resolve the full collection path (parent → child) to avoid ambiguity — collections with identical names in different parents are different collections.
3. Suggest an output path based on the collection name (kebab-case). Example: collection "API Design" → suggest `knowledge-base/api-design/`. Present the suggestion and ask:

   > "I'll write the files to `knowledge-base/api-design/`. Want to use a different path or filename?"

   CRITICAL: Do NOT proceed past this step until the user explicitly confirms the output path. Silence, non-objection, or answering a different question (e.g., confirming the clustering) does NOT count as path confirmation. You must receive an explicit "yes", "ok", "looks good", or a corrected path before continuing. If the user provides a specific path or filename in their original request, confirm it back to them and wait for acknowledgment.

### Step 2: Fetch All Bookmarks

Use `find_bookmarks` with the resolved `collection_ids` and `limit: 50`. Exhaust pagination by following the cursor until no more results are returned.

CRITICAL: Do not stop after the first page. Track the total count and verify your final list is complete.

For each bookmark, record: `id`, `title`, `link`, `excerpt`, `tags`, `note`.

Inform the user: "Found N bookmarks in '[collection name]'. Fetching content..."

### Step 3: Fetch Full Content

For each bookmark, call `fetch_bookmark_content` to retrieve the full page text.

- If fetch succeeds: use the full text for synthesis.
- If fetch fails (broken link, paywall, timeout, 403/404): mark the bookmark as `[content unavailable]`, include it in the Sources table of the relevant file, and note the issue. Do not skip it silently — report all inaccessible links to the user at the end.
- If Raindrop has an `excerpt` or `note` for an inaccessible bookmark: use that as the content source, clearly marked as `[from Raindrop excerpt]`.

### Step 4: Deduplicate Bookmarks

Before clustering, identify duplicates: bookmarks with the same URL or near-identical titles pointing to the same resource. Keep one instance (prefer the one with richer metadata or notes) and note the deduplication in the Sources table.

### Step 5: Semantic Clustering

Analyze all bookmarks together and group them into semantic topic clusters.

Rules:
- Every bookmark must belong to exactly one cluster. No bookmark is left out.
- Cluster by topic, not by domain or source. Two links from different sites on the same topic belong together.
- Name each cluster with a lowercase kebab-case label that works as a filename (e.g., `rest-best-practices`, `api-gateway`, `graphql-schema-design`).
- Minimum cluster size: 1. A single bookmark on a unique topic gets its own file.

If a bookmark overlaps significantly between two clusters (e.g., an article covering both REST and GraphQL tradeoffs), stop and ask:

> "The bookmark '[title]' covers both '[topic A]' and '[topic B]'. Which cluster fits best, or should I create a broader cluster like '[broader-name]'?"

Present the proposed clustering before proceeding:

```
Proposed grouping:
- rest-best-practices (5 bookmarks)
- api-gateway (3 bookmarks)
- graphql-schema-design (2 bookmarks)

Proceed, or would you like to adjust any grouping?
```

Wait for explicit confirmation before writing files.

### Step 6: Generate Knowledge Base Files

For each confirmed cluster, generate a `.md` file.

**File structure:**

```markdown
# [Topic Title]

> Knowledge base synthesized from [N] sources via Raindrop collection "[collection name]".
> Generated: [YYYY-MM-DD]

## Overview

[2–4 sentence synthesis of what this topic covers, what problems it addresses, and why it matters
for development. Derived entirely from source content — no invented context.]

## [Section derived from content]

[Synthesized content from relevant bookmarks. Consolidate overlapping information across sources
into a single coherent explanation. If multiple sources agree on a point, state it once.
If sources offer different perspectives or tradeoffs, present both.
Cite sources inline: "([Source Title](URL))".]

### [Subsection if needed]

...

## [Next section]

...

## Sources

| Title | URL | Tags | Notes |
|-------|-----|------|-------|
| [title] | [url] | [tags] | — |
| [title — content unavailable] | [url] | [tags] | Link inaccessible |

---

## Suggested Further Reading

> These resources were found via web search and are NOT part of your Raindrop collection.
> They are suggestions only — review and add to Raindrop manually if relevant.

- [Title](URL) — brief note on why it's relevant to this topic.
```

**Section naming rules:**
- Derive section names from the actual content of the bookmarks. Examples for an API topic: "Design Principles", "Authentication & Authorization", "Error Handling", "Versioning Strategy", "Performance Considerations".
- Use `##` for top-level sections, `###` for subsections.
- If a concept appears across multiple bookmarks, consolidate it into one section — never repeat the same concept in multiple sections.
- Only include sections for content that actually exists in the sources. If no source covers a concept, do not include a section for it.

**Code examples rules:**
- Embed code samples directly inside the corresponding content section — do NOT create a separate `## Code Examples` section. Each code block should appear right after the prose it illustrates, within the same `##` or `###` section.
- Acceptable languages (in preference order): **Python**, **Go**, **PHP**, **TypeScript**, **Ruby**. You do NOT need all of them — use whichever are relevant. One language per concept is fine. When converting or generating code from scratch, prefer languages higher in this list.
- Priority order for sourcing code:
  1. **Extract from bookmarks:** If source bookmarks already contain code snippets, extract and clean them up. Keep the original language. Cite the source inline.
  2. **Convert to another language:** If the source code exists but in a different language, you may convert it to one of the acceptable languages if that better fits the topic. Cite the original source.
  3. **Generate from scratch (last resort):** If no code exists in the sources but the concept benefits from a code example, generate one. Mark these with a comment at the top: `# Generated example — not from source material`.
- Code samples must be practical and runnable — not pseudocode or toy examples. Use realistic variable names, error handling, and idiomatic patterns for each language.
- Keep each code block focused: one concept per block, 10–40 lines. If a concept needs more, split into sub-examples.
- If a topic is purely conceptual (e.g., architectural principles, team processes) with no meaningful code representation, skip code samples for that file and add a note before Sources: `[No code examples — this topic is conceptual/process-oriented.]`

**Hallucination prevention:**
- Only write content grounded in fetched bookmark text or Raindrop metadata (title, excerpt, tags, note).
- If a section would require invented content, omit it and add a note: `[Insufficient source data for this concept — consider adding more bookmarks on this topic.]`
- Cite sources inline so every claim is traceable.

### Step 7: Web Validation

For each generated file, run a web search for the topic (e.g., "REST API best practices 2025", "API gateway patterns").

Add a `## Suggested Further Reading` section at the bottom of each file, after the `---` separator. Include 3–5 high-quality links with a one-line note on relevance.

CRITICAL: Never move web-sourced content into the main knowledge sections. The `---` separator and the `> These resources were found via web search` disclaimer are mandatory.

### Step 8: Write Files

Before writing, check if any output file already exists at the target path. If a file exists, pause and ask:

> "The file `<filename>.md` already exists. Overwrite, skip, or rename?"

Write each `.md` file to:
```
~/Library/CloudStorage/GoogleDrive-flaviostudart@gmail.com/Meu Drive/Tech/obsidian-vault/knowledge-base/<confirmed-subfolder>/<cluster-name>.md
```

Expand `~` to the full home directory path.

After writing all files, present a summary and report any issues:

```
Knowledge base generated in knowledge-base/<subfolder>/:

  ✓ rest-best-practices.md       (5 sources, 4 sections)
  ✓ api-gateway.md               (3 sources, 3 sections)
  ✓ graphql-schema-design.md     (2 sources, 2 sections)

Inaccessible links (included in Sources tables):
  - "Some Article Title" (https://...) — 404 Not Found
```

## Guardrails

### Scope
- Do NOT perform any write, update, or delete operation in Raindrop. Read only.
- Do NOT write files outside the Obsidian vault path.
- Do NOT merge web search results into the synthesized knowledge sections.
- Do NOT include content that is not grounded in fetched source material or Raindrop metadata.

### Before Starting
- Verify Raindrop MCP is connected (Step 1 prerequisite check).
- Confirm the target collection exists before fetching bookmarks.

### Before Writing Files
Pause after Step 5. Show the proposed cluster grouping **and** the confirmed output path (including filenames). Ask for explicit confirmation of both. Do not write any file until the user approves the grouping AND has explicitly confirmed the output path (from Step 1). If the output path was never explicitly confirmed, ask again before writing.

### Output Path Confirmation
- The output path must be explicitly confirmed by the user before any file is written or any directory is created.
- Do NOT create directories, write files, or perform any filesystem operation until the path is confirmed.
- If the user provides a path in their original request, confirm it back and wait for acknowledgment.
- Answering other questions (e.g., confirming clustering) does NOT constitute path confirmation.

### When to Stop and Ask
- Collection name matches multiple collections → show candidates, ask which one.
- A bookmark overlaps significantly between two clusters → ask before assigning.
- More than 8 files would be generated → confirm the grouping first.
- Content of a section would require invented information → omit the section, note it.

### On Collision
If a `.md` file already exists at the output path: ask whether to overwrite, skip, or rename. Never silently overwrite existing files.

## Examples

### Example 1: API Design collection

User says: "Convert my 'API Design' Raindrop collection to a knowledge base"

Actions:
1. Verify Raindrop MCP connected
2. Find collection "API Design" → confirm with user if ambiguous
3. Fetch all bookmarks (e.g., 10 total across 2 pages)
4. Fetch full content for each; 1 link returns 404 → mark as inaccessible
5. Deduplicate: find 1 duplicate URL → keep one
6. Cluster: `rest-best-practices` (4), `graphql-patterns` (3), `api-gateway` (2)
7. Present grouping → user confirms
8. Generate 3 .md files with synthesized sections (e.g., "Versioning Strategy", "Error Handling", "Authentication")
9. Web search per topic → add Suggested Further Reading to each file
10. Confirm output path `knowledge-base/api-design/` → write files
11. Report summary + 1 inaccessible link

Result: 3 structured `.md` files, no duplicated content, all sources cited inline, inaccessible link reported.

### Example 2: Ambiguous cluster assignment

During Step 5, a bookmark titled "GraphQL vs REST: Performance Tradeoffs" covers both clusters.

Agent asks: "The bookmark 'GraphQL vs REST: Performance Tradeoffs' covers both 'rest-best-practices' and 'graphql-patterns'. Should I place it under one of those, or create a broader 'api-comparison' cluster?"

User replies: "Put it in rest-best-practices" → continues without guessing.

### Example 3: Large collection

User says: "Convert my 'Frontend' collection" — 45 bookmarks found.

Agent informs: "Found 45 bookmarks. Fetching content — this may take a moment."

After clustering proposes 9 clusters → pauses: "This would generate 9 files. Here's the proposed grouping: [list]. Does this look right, or would you like to consolidate any clusters?"