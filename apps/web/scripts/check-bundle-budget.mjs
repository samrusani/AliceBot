import { readFile, stat } from "node:fs/promises";
import { gzipSync } from "node:zlib";

const manifestPath = new URL("../.next/app-build-manifest.json", import.meta.url);
const nextRoot = new URL("../.next/", import.meta.url);
const budgets = {
  "/page": 120_000,
  "/continuity/page": 130_000,
  "/vnext/page": 155_000,
};

const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
let failed = false;

for (const [route, budget] of Object.entries(budgets)) {
  const assets = manifest.pages?.[route];
  if (!Array.isArray(assets)) {
    throw new Error(`Bundle manifest is missing expected app route ${route}`);
  }

  const javascriptAssets = [...new Set(assets.filter((asset) => asset.endsWith(".js")))];
  let gzipBytes = 0;
  for (const asset of javascriptAssets) {
    const assetUrl = new URL(asset, nextRoot);
    await stat(assetUrl);
    gzipBytes += gzipSync(await readFile(assetUrl)).byteLength;
  }

  const headroom = budget - gzipBytes;
  console.log(`${route}: ${gzipBytes} gzip bytes (budget ${budget}, headroom ${headroom})`);
  if (headroom < 0) {
    failed = true;
  }
}

if (failed) {
  throw new Error("One or more route JavaScript bundles exceeded the checked-in gzip budget");
}
