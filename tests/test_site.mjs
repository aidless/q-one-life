import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { translations } from "../site/app.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const html = await readFile(path.join(root, "site", "index.html"), "utf8");
const css = await readFile(path.join(root, "site", "styles.css"), "utf8");

test("website translations match the rendered page and each other", () => {
  const zhKeys = Object.keys(translations.zh).sort();
  const enKeys = Object.keys(translations.en).sort();
  assert.deepEqual(zhKeys, enKeys);

  const pageKeys = new Set();
  for (const match of html.matchAll(/data-i18n(?:-html)?="([^"]+)"/g)) {
    pageKeys.add(match[1]);
  }
  assert.deepEqual([...pageKeys].sort(), zhKeys);
  for (const value of Object.values(translations.zh)) assert.ok(value.trim());
  for (const value of Object.values(translations.en)) assert.ok(value.trim());
});

test("website has no third-party scripts or remote asset dependencies", () => {
  assert.doesNotMatch(html, /<script[^>]+src="https?:/i);
  assert.doesNotMatch(css, /url\(\s*["']?https?:/i);
  assert.match(html, /<meta name="viewport"/);
  assert.match(html, /class="skip-link"/);
  assert.match(css, /prefers-reduced-motion/);
});
