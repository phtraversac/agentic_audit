"""Merge saved Oncrawl MCP answers into raw.json. Stdlib only.

Usage: python3 tools/pack.py <dir> [-o raw.json]

<dir> holds:
  meta.json            {"site", "crawl", "project", "env", "seg", "topic_seg", "brand": [...], "built"}
  rules.json           [{"name", "role", "match", "topic"}, ...]  (confirmed by the user)
  topic_money.json     optional {"<topic>": "/money/page/path/"}
  orphan_status.json   optional, written by tools/check_orphans.py
  settings.json        optional {"template_min": 50, "high_sd": 1000, "med_sd": 200, "sender_cap": 5}
  <table>.json, <table>.<n>.json   one MCP answer per file, slices of one table share its name
                                   (graph.1.json, graph.2.json ... are concatenated)
Tables: pages, indexable, titles, seg, topic, kw_anchor, kw, positions, footer, links_main, links_main_empty, graph, links_total.
A file may hold the MCP answer as returned ({"result": {"aggs": [...]}} or {"query_result": {...}}),
a bare {"cols", "rows"}, or the text-block list Claude Code saves for large tool results.
"""
import json, os, re, sys, datetime

def load(path):
    with open(path, encoding="utf-8") as f: data = json.load(f)
    if isinstance(data, list) and data and isinstance(data[0], dict) and data[0].get("type") == "text":   # saved tool result
        data = json.loads("".join(b.get("text", "") for b in data))
    if isinstance(data, dict) and isinstance(data.get("result"), dict) and "aggs" in data["result"]:
        aggs = data["result"]["aggs"]
        if len(aggs) != 1: sys.exit(f"{path}: expected one aggregation, got {len(aggs)}")
        data = aggs[0]
    if isinstance(data, dict) and "query_result" in data: data = data["query_result"]
    if isinstance(data, dict) and "error" in data: sys.exit(f"{path}: the MCP answered an error: {data['error']}")
    return data

def merge(parts, name):
    if all("cols" in p for p in parts):
        cols = parts[0]["cols"]
        for p in parts[1:]:
            if p["cols"] != cols: sys.exit(f"{name}: slices have different columns {cols} vs {p['cols']}")
        # enum dimensions come back as every combination: rows with a count of 0 hold nothing
        ci = next((i for i, c in enumerate(cols) if c in ("page_count", "link_count")), None)
        return {"cols": cols, "rows": [r for p in parts for r in p["rows"] if ci is None or r[ci]]}
    key = "urls" if "urls" in parts[0] else "links"
    return {key: [r for p in parts for r in p.get(key, [])]}

def count_of(t):
    if "cols" not in t: return None
    flat = [c for c in t["cols"] if not isinstance(c, list)]
    if "link_count" not in flat: return None
    i = t["cols"].index("link_count")
    return sum(r[i] or 0 for r in t["rows"])

def main():
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    d = args[0]; out = args[args.index("-o") + 1] if "-o" in args else "raw.json"
    side = {"meta": "meta.json", "rules": "rules.json", "topic_money": "topic_money.json", "orphan_status": "orphan_status.json", "settings": "settings.json"}
    raw = {"version": 1}
    for k, f in side.items():
        p = os.path.join(d, f)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh: raw[k] = json.load(fh)
    if "rules" not in raw or "meta" not in raw: sys.exit("meta.json and rules.json are required")
    raw["meta"].setdefault("built", datetime.date.today().isoformat())
    groups = {}
    for f in sorted(os.listdir(d)):
        m = re.fullmatch(r"([a-z_]+)(?:\.(\d+))?\.json", f)
        if not m or f in side.values(): continue
        groups.setdefault(m.group(1), []).append(load(os.path.join(d, f)))
    raw["tables"] = {name: merge(parts, name) for name, parts in groups.items()}
    if "pages" not in raw["tables"]: sys.exit('no "pages" table')
    # the graph slices must add up to the single link-count aggregate (aggregates cut rows without warning)
    g, tot = raw["tables"].get("graph"), raw["tables"].get("links_total")
    if g and tot:
        want, got = count_of(tot), count_of(g)
        if want is not None and got != want: sys.exit(f"graph slices hold {got} links, links_total says {want}: a slice was cut, split it further")
        print(f"graph check OK: {got} links in {len(g['rows'])} pairs")
    with open(out, "w", encoding="utf-8") as f: json.dump(raw, f, ensure_ascii=False, separators=(",", ":"))
    for name, t in raw["tables"].items(): print(f"{name:12} {len(t.get('rows', t.get('urls', t.get('links', []))))} rows")
    print("wrote", out, os.path.getsize(out) // 1024, "KB")

if __name__ == "__main__":
    main()
