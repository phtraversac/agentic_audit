"""Check the live HTTP status of the orphan pages in raw.json, in place. Stdlib only.

Usage: python3 tools/check_orphans.py raw.json [--max 2000]
Orphans = pages not fetched by the crawl that Google still sees (impressions, Googlebot hits or SEO visits).
One HEAD per URL (GET when HEAD is refused), no redirect followed, 2 at a time, 0.2 s apart, named user agent.
Only run it on a site you are allowed to audit. A rerun skips URLs already checked.
"""
import json, os, re, sys, time, datetime, urllib.request, urllib.error
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (compatible; agentic-audit internal-linking status check; +https://github.com/phtraversac/agentic_audit)"

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a): return None
opener = urllib.request.build_opener(NoRedirect)

def head(url, method="HEAD"):
    time.sleep(0.2)
    try:
        with opener.open(urllib.request.Request(url, method=method, headers={"User-Agent": UA}), timeout=10) as r:
            return {"status": r.status, "location": r.headers.get("Location")}
    except urllib.error.HTTPError as e:
        if e.code == 405 and method == "HEAD": return head(url, "GET")
        return {"status": e.code, "location": e.headers.get("Location")}
    except Exception as e:
        return {"status": None, "location": None, "error": type(e).__name__}

def rows(t):
    if "cols" in t:
        names = [n for c in t["cols"] for n in (c if isinstance(c, list) else [c])]
        for r in t["rows"]:
            v = [x for c, y in zip(t["cols"], r) for x in (y if isinstance(c, list) else [y])]
            yield dict(zip(names, v))
    else: yield from t.get("urls", [])

def main():
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    path = args[0]; cap = int(args[args.index("--max") + 1]) if "--max" in args else 2000
    with open(path, encoding="utf-8") as f: raw = json.load(f)
    done = raw.get("orphan_status") or {}
    signal = lambda o: (o.get("gsc_impressions:sum") or 0) + (o.get("googlebot_hits:sum") or 0) + (o.get("seo_visits:sum") or 0)
    # the report's hosts and rules (first match wins, "ignore" drops); a few pagination URLs the report sets aside as a log artefact may still be checked
    meta = raw.get("meta", {})
    host = lambda u: (urlparse(u).hostname or "") + (f":{urlparse(u).port}" if urlparse(u).port else "")   # like JS URL.host
    hosts = {h.lower() for h in (meta.get("hosts") or ([host(meta["site"])] if meta.get("site") else []))}
    if not hosts: sys.exit('raw.json meta has neither "hosts" nor "site": refusing to request URLs of unknown hosts')
    rules = []
    for r in raw.get("rules", []):
        try: rules.append((re.compile(r["match"]), r["role"]))
        except re.error: rules = None; break   # a JS-only pattern: check every URL of the hosts
    def kept(url):
        u = urlparse(url)
        if host(url) not in hosts: return False
        if rules is None: return True
        role = next((role for rx, role in rules if rx.search(u.path or "/")), None)
        return role is not None and role != "ignore"
    cand = [o for o in rows(raw["tables"]["pages"]) if str(o.get("fetched")).lower() == "false" and "?" not in o["url"] and signal(o) > 0
            and o["url"].startswith(("http://", "https://")) and kept(o["url"]) and done.get(o["url"], {}).get("status") is None]
    todo = [o["url"] for o in sorted(cand, key=lambda o: -signal(o))]   # most-seen first when --max cuts the list
    if len(todo) > cap: print(f"{len(todo)} orphans, checking the first {cap} (--max to change)"); todo = todo[:cap]
    def save():
        raw["orphan_status"] = done
        if done: raw.setdefault("meta", {})["orphans_checked_on"] = datetime.date.today().isoformat()
        with open(path + ".tmp", "w", encoding="utf-8") as f: json.dump(raw, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(path + ".tmp", path)   # atomic: a stop never leaves a half-written raw.json
    if not todo: print("no orphan URL to check"); return
    try:
        with ThreadPoolExecutor(2) as ex:
            for i, (url, res) in enumerate(zip(todo, ex.map(head, todo)), 1):
                done[url] = res
                if i % 100 == 0: save(); print(i, "checked")   # a stop keeps what is done; a rerun skips it
    finally:
        save()
    from collections import Counter
    print(len(todo), "checked,", len(done), "total", dict(Counter(v["status"] for v in done.values())))

if __name__ == "__main__":
    main()
