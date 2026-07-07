#!/usr/bin/env node
// Fixes a headless-Chromium bug that breaks multi-shape-per-row C4 layouts.
//
// Mermaid's C4 renderer decides how many shapes fit per row by reading
// `screen.availWidth` (not `window.innerWidth`) — see mermaid's
// c4Diagram source: `screenBounds.data.widthLimit = screen.availWidth`.
// Puppeteer's `page.setViewport({width})` only changes `window.innerWidth`;
// `screen.availWidth` stays pinned at the browser's initial launch size
// (800 in headless Chromium) no matter how wide the viewport is set.
// A real browser (Obsidian/Electron, Chrome) reports the actual monitor
// width there, so `UpdateLayoutConfig($c4ShapeInRow=N)` lays out N shapes
// per row as authored — but under mmdc it silently collapses to one
// shape per row once the row's combined width exceeds 800px (common
// with descriptive C4 labels/descriptions).
//
// Fix: override `screen.availWidth`/`screen.width` via the CDP
// `Emulation.setDeviceMetricsOverride` command, which sets screen size
// independently of the viewport, before mermaid renders.
//
// Reuses the mermaid-studio skill's own puppeteer + mermaid install
// (~/.claude/skills/mermaid-studio/.deps) instead of vendoring them here.
//
// Usage:
//   node render-c4-fixed.mjs --input diagram.mmd --output diagram.png [--screen-width 3000] [--scale 3]
//
// When to reach for this instead of the parent skill's scripts/render.mjs:
// the diagram is C4 (C4Container/C4Context/C4Component/C4Dynamic/C4Deployment),
// it sets `UpdateLayoutConfig($c4ShapeInRow=N)` or `$c4BoundaryInRow=N` with
// N > 1, and mmdc's output shows shapes stacked one-per-row instead of the
// configured grid.

import { readFileSync } from "fs";
import { homedir } from "os";
import { resolve } from "path";
import { createRequire } from "module";

const SKILL_DIR = process.env.MERMAID_STUDIO_DIR
  ? resolve(process.env.MERMAID_STUDIO_DIR, "..")
  : resolve(homedir(), ".claude/skills/mermaid-studio");
const DEPS_DIR = process.env.MERMAID_STUDIO_DIR || resolve(SKILL_DIR, ".deps");
const MERMAID_BUNDLE = resolve(DEPS_DIR, "node_modules/mermaid/dist/mermaid.min.js");

const require = createRequire(resolve(DEPS_DIR, "package.json"));
const puppeteer = require("puppeteer");

function getArg(args, name, def) {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : def;
}

async function main() {
  const args = process.argv.slice(2);
  const input = getArg(args, "--input");
  const output = getArg(args, "--output");
  const screenWidth = parseInt(getArg(args, "--screen-width", "3000"), 10);
  const scale = parseFloat(getArg(args, "--scale", "3"));

  if (!input || !output) {
    console.error(
      "Usage: render-c4-fixed.mjs --input <file.mmd> --output <file.png> [--screen-width 3000] [--scale 3]",
    );
    process.exit(1);
  }

  const definition = readFileSync(input, "utf-8");
  const mermaidBundle = readFileSync(MERMAID_BUNDLE, "utf-8");
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    body { margin: 0; background: white; }
    #container { display: inline-block; }
  </style></head><body><div id="container"></div></body></html>`;

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  try {
    const page = await browser.newPage();
    page.on("pageerror", (e) => console.warn("[pageerror]", e));

    await page.setViewport({ width: screenWidth, height: 1200, deviceScaleFactor: scale });

    const client = await page.createCDPSession();
    await client.send("Emulation.setDeviceMetricsOverride", {
      width: screenWidth,
      height: 1200,
      deviceScaleFactor: scale,
      mobile: false,
      screenWidth,
      screenHeight: 3000,
    });

    await page.setContent(html);
    await page.addScriptTag({ content: mermaidBundle });

    // getBoundingClientRect() would return the browser's 300x150 default
    // for an un-sized <svg>; mermaid encodes the real diagram size in the
    // viewBox instead, so read dimensions from there.
    const { width, height } = await page.evaluate(async (def) => {
      mermaid.initialize({ startOnLoad: false, theme: "default" });
      const { svg } = await mermaid.render("c4diagram", def);
      document.getElementById("container").innerHTML = svg;
      const svgEl = document.querySelector("#container svg");
      const [, , vbWidth, vbHeight] = svgEl.getAttribute("viewBox").split(/\s+/).map(Number);
      svgEl.removeAttribute("style");
      svgEl.setAttribute("width", vbWidth);
      svgEl.setAttribute("height", vbHeight);
      return { width: vbWidth, height: vbHeight };
    }, definition);

    await page.setViewport({
      width: Math.ceil(width) + 10,
      height: Math.ceil(height) + 10,
      deviceScaleFactor: scale,
    });

    const container = await page.$("#container");
    await container.screenshot({ path: output });

    console.log(`Rendered ${input} -> ${output} (${Math.round(width)}x${Math.round(height)} @${scale}x)`);
  } finally {
    await browser.close();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
