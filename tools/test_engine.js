// Self-check of the engine inside index.html: node tools/test_engine.js [raw.json]
// Without an argument, runs a small synthetic site with known answers. With a raw.json, builds it and prints the headline figures.
const fs = require("fs"), path = require("path"), assert = require("assert");
const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const engine = html.slice(html.indexOf('const ROLES = ['), html.indexOf("// REPORT"));
const buildModel = new Function(engine.replace(/\/\/ =+\s*$/, "") + "; return buildModel;")();

if (process.argv[2]) {
  const t0 = Date.now(), M = buildModel(JSON.parse(fs.readFileSync(process.argv[2], "utf8")));
  console.log(JSON.stringify({ms: Date.now() - t0, pages: M.groups.reduce((s, g) => s + g.pages, 0), seg: M.segmentation.score, zoning: M.zoning && M.zoning.score,
    kinds: M.kinds, orphans: M.orphan_summary, proposals: M.proposals.length, sim: M.sim && {rho: M.sim.rho, edges: M.sim.edges, by: M.sim.by_strategy}, fixes: M.anchor_fixes.length,
    groups: M.groups.map(g => `${g.name}:${g.pages}/${g.live}`).join(" ")}, null, 1));
  process.exit(0);
}

const S = "https://ex.com";
const agg = (cols, rows) => ({cols, rows});
const R = {
  version: 1, meta: {site: S + "/", crawl: "c1", seg: "seg", brand: ["ex"]},
  rules: [{name: "Pagination", role: "pagination", match: "/page/\\d+"}, {name: "Home", role: "home", match: "^/$"},
    {name: "Hub", role: "hub", match: "^/[a-z]+/$", topic: 0}, {name: "Post", role: "content", match: "^/[a-z]+/[^/]+/$", topic: 0}],
  tables: {
    pages: agg(["url", "fetched", ["status_code:min", "depth:min", "inrank_decimal:sum", "gsc_impressions:sum", "gsc_impressions_pos_4_10:sum"]], [
      [S + "/", "true", [200, 0, 10, 100, 0]], [S + "/a/", "true", [200, 1, 5, 0, 0]], [S + "/a/one/", "true", [200, 2, 2, 3000, 2000]],
      [S + "/a/two/", "true", [200, 2, 3, 50, 10]], [S + "/a/gone/", "false", [null, null, 0, 500, 0]], [S + "/x.php", "true", [200, 1, 0, 0, 0]],
      ["https://other.com/a/one/", "true", [200, 1, 1, 9, 9]]]),
    indexable: agg(["url", "indexable", "page_count"], [[S + "/", "true", 1], [S + "/a/", "true", 1], [S + "/a/one/", "true", 1], [S + "/a/two/", "true", 1], [S + "/a/two/", "false", 0]]),
    seg: agg(["url", "page_group_seg", "page_count"], [[S + "/", "Home", 1], [S + "/a/one/", "Post", 1], [S + "/a/one/", "Hub", 0]]),
    kw: {urls: [{url: S + "/a/one/", gsc_kw: ["ex brand query", "first real query", "second query"]}]},
    positions: agg(["origin_position", "link_count"], [["main", 4], ["footer", 1]]),
    links_main: agg(["origin", "target", "anchor", "link_count"], [[S + "/a/two/", S + "/a/one/", "read more", 1], [S + "/a/", S + "/a/one/", "One", 1], [S + "/", S + "/a/", "A", 1]]),
    links_main_empty: agg(["origin", "target", "link_count"], [[S + "/a/two/", S + "/a/", 1]]),
    graph: agg(["origin", "target", "link_count"], [[S + "/", S + "/a/", 1], [S + "/a/", S + "/a/one/", 1], [S + "/a/", S + "/a/two/", 1], [S + "/a/two/", S + "/a/one/", 1], [S + "/a/one/", S + "/", 1]]),
  },
  orphan_status: {[S + "/a/gone/"]: {status: 404}},
};
const M = buildModel(R);
const G = Object.fromEntries(M.groups.map(g => [g.name, g]));
assert.strictEqual(G.Post.pages, 3, "posts: one, two and the orphan gone (other host and x.php left out)");
assert.strictEqual(G.Post.live, 2);
assert.strictEqual(M.orphans.length, 1); assert.strictEqual(M.orphans[0].verdict, "lost", "404 with 500 impressions = lost");
assert.strictEqual(M.kinds.listing, 2, "links from the hub and the home are listing links");
assert.strictEqual(M.kinds.editorial, 2, "post two -> one (read more) and the anchorless post two -> hub");
const one = M.targets.find(t => t.path === "/a/one/");
assert.strictEqual(one.ed_src, 1); assert.strictEqual(one.prio, "High");
assert.deepStrictEqual(one.top_kw, ["first real query", "second query"], "brand queries left out");
const fix = M.anchor_fixes.find(f => f.anchor === "read more");
assert.ok(fix && fix.kind === "generic" && fix.suggested === "first real query", "generic anchor gets the first non-brand query");
assert.strictEqual(M.segmentation.live, 4); assert.strictEqual(M.segmentation.live_grouped, 2, "count-0 seg rows ignored");
assert.ok(M.sim && Math.abs(M.sim.rho) <= 1 && M.sim.edges === 5);
assert.ok(M.proposals.every(p => p.sender !== p.receiver));
const noLinks = buildModel({...R, tables: {pages: R.tables.pages, indexable: R.tables.indexable}});
assert.strictEqual(noLinks.zoning, null); assert.strictEqual(noLinks.sim, null); assert.strictEqual(noLinks.targets.find(t => t.path === "/a/one/").ed_src, null);
assert.throws(() => buildModel({...R, rules: [{name: "x", role: "nope", match: "."}]}), /unknown role/);
// non-Latin anchors are words, not "generic"; data keys like "constructor" are plain keys; settings are numbers only
const cyr = JSON.parse(JSON.stringify(R)); cyr.tables.links_main.rows[0][2] = "Подробнее о сканере";
assert.strictEqual(buildModel(cyr).anchor_fixes.find(f => f.origin === S + "/a/two/")?.kind, "descriptive", "Cyrillic anchor is a descriptive anchor, not generic");
const proto = JSON.parse(JSON.stringify(R).replaceAll("/a/", "/constructor/"));
assert.strictEqual(buildModel(proto).proposals.length, M.proposals.length, "a topic named constructor behaves like any topic");
const bad = buildModel({...R, settings: {template_min: "<img src=x onerror=alert(1)>", high_sd: 500}});
assert.strictEqual(bad.settings.template_min, 50); assert.strictEqual(bad.settings.high_sd, 500);
console.log("engine: all checks passed");
