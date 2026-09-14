---
name: mermaid-studio-extended
extends: mermaid-studio
description: >
  Extension for the mermaid-studio skill. This file MUST be read together with the parent
  mermaid-studio SKILL.md. The parent governs Mermaid diagram creation, validation, and
  rendering. This extension adds a required PNG-only substitute renderer for multi-row C4
  diagrams, and a mandatory black-text override for nodes/boxes that render with a white or
  near-white background, replacing the parent's white-on-near-white init templates.
metadata:
  version: "1.2.0"
  parent_skill: mermaid-studio
  source: "ai-coding-tooling (extended/)"
---

# mermaid-studio — Renderer & Styling Extension

> This file extends the **mermaid-studio** skill. The parent SKILL.md governs diagram
> creation, validation, and rendering. This extension overrides which script renders C4
> diagrams (in practice every C4 diagram, since the parent mandates `c4ShapeInRow="3"`),
> and hardens the parent's default styling against white-on-white text.

## Use render-c4-fixed.mjs Instead of the Parent's render.mjs

Render a C4 diagram (`C4Context`/`C4Container`/`C4Component`/`C4Dynamic`/`C4Deployment`)
whose `UpdateLayoutConfig` sets `$c4ShapeInRow` or `$c4BoundaryInRow` above 1 with
`scripts/render-c4-fixed.mjs` (sibling to this file), not the parent's `scripts/render.mjs`
— the parent's mmdc-based renderer silently collapses these diagrams to one shape per row
once a row's combined width exceeds 800px, regardless of `--width`.

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

`render-c4-fixed.mjs` outputs PNG only (it screenshots the page). Always give `--output` a
`.png` path. If the user needs SVG or PDF for a multi-row C4 diagram, say so and either
deliver PNG or fall back to the parent's `render.mjs` with `c4ShapeInRow` lowered to 1.

Requires the parent's `.deps` install: run the parent's `scripts/setup.sh` first if
`~/.claude/skills/mermaid-studio/.deps` doesn't exist.

All other diagram types, and C4 diagrams without `c4ShapeInRow`/`c4BoundaryInRow` above 1,
still use the parent's `scripts/render.mjs` as normal.

## Force Black Text on White/Light Node Fills

> This extension overrides every base init template that pairs a light `mainBkg` with a
> white `primaryTextColor`: Rule 1, the 2.3 flowchart example, and the `references/themes.md`
> frontmatter, Tailwind, Monochrome and Indigo-Emerald presets. The parent's Rule 1 template
> pairs `mainBkg` `'#f8fafc'` (the default flowchart node fill) with `primaryTextColor`
> `'#ffffff'`, so default node labels render white-on-white, and the other templates repeat
> that pairing. Do not try `nodeTextColor`: `themeVariables` passed via `%%{init}%%` ignore
> it (verified by repro); `primaryTextColor` is what controls default-node label color.

### Rule: Every White/Light Box Fill Must Declare Black Text Explicitly

**Flowcharts (and any diagram whose default node fill is `mainBkg`)** — since `nodeTextColor`
is inert, `primaryTextColor` is the variable that actually controls default-node label color.
Set it dark for flowchart, sequence, state, class and ERD diagrams when `mainBkg` is
white/near-white — corrected Rule 1 template:

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

For the other overridden templates, keep their palette and set `primaryTextColor` to
`'#000000'` the same way.

This is safe because flowchart nodes never render filled with `primaryColor` itself unless a
`classDef`/`style` explicitly sets `fill:` to it — `primaryColor` in the base theme mainly
seeds derived variables (`secondaryColor`, `tertiaryColor`, `edgeLabelBackground`, etc.), so
darkening `primaryTextColor` to match `mainBkg` does not desync it from any node that's
actually colored `primaryColor`.

Do not use this template for mindmap, timeline or other cScale-colored diagrams: their
section labels also inherit `primaryTextColor` but sit on dark `primaryColor`-derived fills,
so keep `primaryTextColor` light there.

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

**C4 `UpdateElementStyle`** — C4 elements use their own fixed styling mechanism, not
`mainBkg`. Pair every light `$bgColor` you set (white or near-white) with black `$fontColor`;
leave `$fontColor` unset when `$bgColor` is unset, because C4 default fills (`#08427B`,
`#1168BD`, `#438DD5`) are dark and already use white text:

```
UpdateElementStyle(elementAlias, $bgColor="#f8fafc", $fontColor="#000000", $borderColor="#cbd5e1")
```

Apply this check before every render, not only after a bug is spotted (white/near-white =
any fill lighter than `#e5e7eb`): if any node/actor in the diagram ends up white/near-white,
its black text-color declaration must be present via `primaryTextColor`/`actorTextColor` in
the init directive, or via `color:`/`$fontColor` in the same style/classDef/UpdateElementStyle
line — never assumed inherited, and never via `nodeTextColor`.
