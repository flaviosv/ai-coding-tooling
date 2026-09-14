# STATE

## Decisions

### AD-001
- **Decision**: Render multi-row C4 diagrams with the overlay's own `scripts/render-c4-fixed.mjs`, which overrides the screen size via CDP `Emulation.setDeviceMetricsOverride`, instead of the parent's mmdc-based `render.mjs`.
- **Reason**: Mermaid's C4 renderer sizes rows from `screen.availWidth` (`screenBounds.data.widthLimit = screen.availWidth`), which headless Chromium pins at 800 regardless of `page.setViewport`, so under mmdc a `$c4ShapeInRow`/`$c4BoundaryInRow` above 1 silently collapses to one shape per row once a row exceeds 800px. The parent skill is read-only, so the fix ships as a sibling script that reuses the parent's `.deps` puppeteer + mermaid install.
- **Trade-off**: A second renderer to maintain that depends on the parent's `.deps` layout, and it outputs PNG only (it screenshots the page), so multi-row C4 diagrams lose the parent's SVG/PDF output.
- **Date**: 2026-07-07
- **Status**: active

### AD-002
- **Decision**: Require an explicit black text color on every node/box that renders with a white or near-white fill, overriding the parent's init template pairing.
- **Reason**: The parent's Rule 1 template sets `mainBkg` to near-white `#f8fafc` but `primaryTextColor` to `#ffffff`; every default flowchart node fills with `mainBkg` and takes its label color from `primaryTextColor`, so labels rendered white-on-white. This was reproduced in a rendered `docs/codebase/ARCHITECTURE.md` diagram where every default-class box's label was nearly invisible.
- **Trade-off**: The overlay now replaces palette values the parent tells agents to copy verbatim, and adds a pre-render check agents must apply on every diagram.
- **Date**: 2026-08-25
- **Status**: active

### AD-003
- **Decision**: Implement AD-002 through `primaryTextColor` (and `actorTextColor` for sequence diagrams), and reject `nodeTextColor`, which the first version of AD-002 used.
- **Reason**: `nodeTextColor` looks like a legitimate override path: the flowchart CSS template references `options2.nodeTextColor || options2.textColor`, and the base theme's `calculate()` does `this.nodeTextColor = this.nodeTextColor || this.primaryTextColor`, while flowchart CSS fills `.node rect, .node circle, .node ellipse, .node polygon, .node path` with `mainBkg`. But `mmdc` (installed mermaid 11.17.2, checked via `~/.claude/skills/mermaid-studio/.deps/node_modules/mermaid/package.json`) silently drops `nodeTextColor` from `themeVariables` passed via an `%%{init}%%` directive. An isolated repro showed `primaryColor`/`primaryTextColor` overrides taking effect while the rendered label color always matched `primaryTextColor` whatever `nodeTextColor` was set to. Setting `primaryTextColor` dark fixed all 4 affected diagrams on re-render; `actorTextColor` was independently verified to be honored.
- **Trade-off**: Darkening `primaryTextColor` also darkens every other label derived from it, which is safe for flowcharts (nodes never fill with `primaryColor` unless a `classDef`/`style` sets it) but not for every diagram type (see AD-004). The finding is pinned to mermaid 11.17.2 and may change on a `.deps` reinstall.
- **Date**: 2026-08-25
- **Status**: active

### AD-004
- **Decision**: Apply the 2026-09-13 harness-eval overlay findings: use one C4 renderer trigger (a C4 diagram whose `UpdateLayoutConfig` sets `$c4ShapeInRow` or `$c4BoundaryInRow` above 1) in both the overlay and the script header and state that it covers nearly every C4 diagram, document the renderer as PNG-only, limit the black `primaryTextColor` template to flowchart/sequence/state/class/ERD and exclude cScale-colored diagrams, extend the override to every base template with the same white-on-near-white pairing, define near-white as lighter than `#e5e7eb`, pair C4 `$fontColor` black only with a light `$bgColor` that is actually set, cut the redundant `.deps` reuse sentence, and move the AD-003 investigation narrative out of `SKILL.md` into this log.
- **Reason**: Each claim was verified against the base skill and the installed mermaid bundle: the parent mandates `c4ShapeInRow="3"` on every C4 diagram; `render-c4-fixed.mjs` only calls `container.screenshot`; in theme-base `cScale0` derives from `primaryColor` darkened 25% while `cScaleLabel` falls back to `primaryTextColor`, so black text landed on dark mindmap sections; the base 2.3 flowchart example and the `themes.md` frontmatter, Tailwind, Monochrome and Indigo-Emerald presets repeat the Rule 1 pairing; and C4 default fills (`#08427B`, `#1168BD`, `#438DD5`) are dark with white text, so black `$fontColor` on an unset `$bgColor` recreated the unreadable-label bug.
- **Trade-off**: The near-white threshold is a heuristic with no automated check, SVG/PDF for multi-row C4 now requires lowering `c4ShapeInRow` to 1 and using the parent's renderer, and the investigation detail no longer sits next to the rule it justifies.
- **Date**: 2026-09-14
- **Status**: active
