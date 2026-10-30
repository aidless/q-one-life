import assert from "node:assert/strict";
import test from "node:test";
import { recoveryKeyQrSvg } from "../recovery-qr";

test("recovery key QR is a self-contained SVG without the key text", () => {
  const key = `Q1-${"A".repeat(58)}`;
  const svg = recoveryKeyQrSvg(key);
  assert.match(svg, /^<svg /);
  assert.match(svg, /viewBox=/);
  assert.doesNotMatch(svg, new RegExp(key));
  assert.doesNotMatch(svg, /<script|foreignObject|image|use|href=|on\w+=/i);
});

test("recovery key QR rejects malformed text", () => {
  assert.throws(() => recoveryKeyQrSvg("not-a-recovery-key"), /format is invalid/);
});
