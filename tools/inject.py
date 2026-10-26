"""Embed raw.json into the report: python3 tools/inject.py raw.json [-o audit.html]. Stdlib only.

The report computes everything from raw.json in the browser; this only puts the data inside the page so it opens
on its own (double-click, or any static server). Serve over http if your browser blocks the Highcharts CDN on file://.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SLOT = '<script id="raw" type="application/json">null</script>'

def main():
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    out = args[args.index("-o") + 1] if "-o" in args else "audit.html"
    with open(args[0], encoding="utf-8") as f: raw = json.load(f)
    with open(os.path.join(HERE, "..", "index.html"), encoding="utf-8") as f: html = f.read()
    if html.count(SLOT) != 1: sys.exit("index.html: data slot not found exactly once")
    data = json.dumps(raw, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")   # no </script> can close the tag
    with open(out, "w", encoding="utf-8") as f: f.write(html.replace(SLOT, SLOT.replace(">null<", ">" + data + "<")))
    print("wrote", out, os.path.getsize(out) // 1024, "KB")

if __name__ == "__main__":
    main()
