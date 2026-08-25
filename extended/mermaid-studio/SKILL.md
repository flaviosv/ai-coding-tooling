---
name: mermaid-studio-extended
extends: mermaid-studio
description: >
  Extension for the mermaid-studio skill. This file MUST be read together with the parent
  mermaid-studio SKILL.md. The parent governs Mermaid diagram creation, validation, and
  rendering. This extension adds a required substitute renderer for multi-row C4 diagrams,
  and a mandatory black-text override for any node/box that renders with a white or
  near-white background.
metadata:
  version: "1.1.0"
  parent_skill: mermaid-studio
  source: "ai-coding-tooling (extended/)"
---

# mermaid-studio — Renderer & Styling Extension

> This file extends the **mermaid-studio** skill. The parent SKILL.md governs diagram
> creation, validation, and rendering. This extension overrides which script renders C4
> diagrams in one specific case, and hardens the parent's default styling against
> white-on-white text.

## Use render-c4-fixed.mjs Instead of the Parent's render.mjs

For any C4 diagram whose `UpdateLayoutConfig` sets `c4ShapeInRow` or `c4BoundaryInRow`
above 1, render it with `scripts/render-c4-fixed.mjs` (sibling to this file), not the
parent's `scripts/render.mjs` — the parent's mmdc-based renderer collapses these diagrams
to one shape per row regardless of `--width`.

This skill is installed as a symlink at `~/.claude/skills/mermaid-studio/SKILL.extended.md`.
Resolve it to find this file's real directory, then run the sibling script from there:

```bash
real_dir="$(dirname "$(readlink -f ~/.claude/skills/mermaid-studio/SKILL.extended.md)")"
node "$real_dir/scripts/render-c4-fixed.mjs" \
  --input diagram.mmd --output diagram.png \
  --screen-width 3000 --scale 3
```

`--screen-width` (default 3000) must exceed the diagram's total row width; `--scale`
(default 3) is the device-scale-factor for PNG sharpness, matching the parent's `-s 3`.

The script reuses the parent skill's own puppeteer + mermaid install
(`~/.claude/skills/mermaid-studio/.deps`) — run the parent's `scripts/setup.sh` first if
`.deps` doesn't exist yet.

All other diagram types, and C4 diagrams without `c4ShapeInRow`/`c4BoundaryInRow` above 1,
still use the parent's `scripts/render.mjs` as normal.

## Force Black Text on White/Light Node Fills

> This extension overrides the parent's Rule 1 init directive: its template sets `mainBkg`
> (the default node background) to a near-white color (`#f8fafc`) but pairs it with
> `primaryTextColor: '#ffffff'`. In flowcharts, EVERY default node gets `mainBkg` as its fill
> (verified in the installed `mermaid` bundle's flowchart CSS: `.node rect, .node circle,
> .node ellipse, .node polygon, .node path { fill: mainBkg }`) and falls back to
> `primaryTextColor` for its label — so the template's own pairing puts white text on a
> white/near-white box. This is exactly what happened in a rendered
> `docs/codebase/ARCHITECTURE.md` diagram: every default-class box came out with the label
> nearly invisible against its own fill.
>
> **`nodeTextColor` does NOT fix this — verified broken, do not use it.** The flowchart CSS
> template does reference `options2.nodeTextColor || options2.textColor`, and the theme's
> `calculate()` step does `this.nodeTextColor = this.nodeTextColor || this.primaryTextColor`,
> which looks like a legitimate override path. It is not: `mmdc` (installed mermaid `11.17.2`,
> checked via `~/.claude/skills/mermaid-studio/.deps/node_modules/mermaid/package.json`)
> silently drops `nodeTextColor` from `themeVariables` passed via an `%%{init}%%` directive —
> confirmed with an isolated repro (`primaryColor`/`primaryTextColor` overrides took effect,
> `nodeTextColor` did not; the rendered label color always matched `primaryTextColor`
> regardless of what `nodeTextColor` was set to). Do not add it expecting it to help.

### Rule: Every White/Light Box Fill Must Declare Black Text Explicitly

**Flowcharts (and any diagram whose default node fill is `mainBkg`)** — since `nodeTextColor`
is inert, `primaryTextColor` is the variable that actually controls default-node label color.
Set it dark whenever `mainBkg` is white/near-white — corrected Rule 1 template:

```
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#4f46e5', 'primaryTextColor': '#000000',
  'primaryBorderColor': '#3730a3', 'lineColor': '#94a3b8',
  'secondaryColor': '#10b981', 'tertiaryColor': '#f59e0b',
  'background': '#ffffff', 'mainBkg': '#f8fafc',
  'nodeBorder': '#cbd5e1', 'clusterBkg': '#f1f5f9',
  'clusterBorder': '#e2e8f0', 'titleColor': '#1e293b',
  'edgeLabelBackground': '#ffffff', 'textColor': '#334155'
}}}%%
```

This is safe because flowchart nodes never render filled with `primaryColor` itself unless a
`classDef`/`style` explicitly sets `fill:` to it — `primaryColor` in the base theme mainly
seeds derived variables (`secondaryColor`, `tertiaryColor`, `edgeLabelBackground`, etc.), so
darkening `primaryTextColor` to match `mainBkg` does not desync it from any node that's
actually colored `primaryColor`.

**Sequence diagrams** — verified working (unlike `nodeTextColor`): the `base` theme derives
`actorBkg = mainBkg` and `actorTextColor = primaryTextColor`, and `actorTextColor` IS honored
when set explicitly. Either rely on the `primaryTextColor: '#000000'` fix above, or set
`actorTextColor` directly for clarity:

```
%%{init: {'theme': 'base', 'themeVariables': {
  ...
  'actorTextColor': '#000000'
}}}%%
```

**Explicit `style`/`classDef` fills** — pair every white/light `fill:` with `color:#000000`
in the same declaration (unaffected by the `nodeTextColor` bug — this path is a direct CSS
override and always wins):

```
style A fill:#ffffff,stroke:#cbd5e1,color:#000000
classDef default fill:#f8fafc,stroke:#e2e8f0,color:#000000
```

**C4 `UpdateElementStyle`** — pair every light/unset `$bgColor` with black `$fontColor`
(also unaffected — C4 elements use their own fixed styling mechanism, not `mainBkg`):

```
UpdateElementStyle(elementAlias, $bgColor="#f8fafc", $fontColor="#000000", $borderColor="#cbd5e1")
```

Apply this check before every render, not only after a bug is spotted: if any node/actor in
the diagram ends up white/near-white, its black text-color declaration must be present via
`primaryTextColor`/`actorTextColor` in the init directive, or via `color:`/`$fontColor` in the
same style/classDef/UpdateElementStyle line — never assumed inherited, and never via
`nodeTextColor`.
