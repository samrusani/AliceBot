import { readFile, stat } from "node:fs/promises";
import { gzipSync } from "node:zlib";

const legacyManifestPath = new URL("../.next/app-build-manifest.json", import.meta.url);
const routeStatsPath = new URL("../.next/diagnostics/route-bundle-stats.json", import.meta.url);
const nextRoot = new URL("../.next/", import.meta.url);
const budgets = [
  { legacyRoute: "/page", route: "/", budget: 164_000 },
  { legacyRoute: "/continuity/page", route: "/continuity", budget: 174_000 },
  { legacyRoute: "/vnext/page", route: "/vnext", budget: 199_000 },
];

let legacyManifest = null;
try {
  legacyManifest = JSON.parse(await readFile(legacyManifestPath, "utf8"));
} catch (error) {
  if (!(error instanceof Error) || !Object.hasOwn(error, "code") || error.code !== "ENOENT") {
    throw error;
  }
}

const routeStats = legacyManifest
  ? null
  : JSON.parse(await readFile(routeStatsPath, "utf8"));
let failed = false;

for (const { legacyRoute, route, budget } of budgets) {
  const assets = legacyManifest
    ? legacyManifest.pages?.[legacyRoute]
    : routeStats
        .find((entry) => entry.route === route)
        ?.firstLoadChunkPaths.map((asset) => asset.replace(/^\.next\//, ""));
  if (!Array.isArray(assets)) {
    throw new Error(`Bundle metadata is missing expected app route ${route}`);
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
