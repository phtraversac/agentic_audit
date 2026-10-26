# Agentic internal linking audit for Oncrawl

Turn your Oncrawl Internal Linking lens into a full internal linking audit, built by your own AI agent from the
Oncrawl MCP. The report answers three questions:

1. **Is the tool set up right?** Segmentation and zoning scores, with the rules to add.
2. **Where should links go?** Demand vs internal popularity per page group, orphan pages with a verdict, the five
   strategies that weigh most, and the links to add with a simulated PageRank gain.
3. **Which anchors to fix?** Existing links to re-anchor and new links with their anchor, exportable as CSV.

Your data never leaves your machine: the agent reads it through your own Oncrawl MCP access, and the report computes
everything in your browser.

## What you need

- An Oncrawl crawl with the Internal Linking lens. Google Search Console and logs connected give the best results.
- The **Oncrawl Lens Context** Chrome extension (`oncrawl-lens-context.zip` in the
  [latest release](https://github.com/phtraversac/agentic_audit/releases/latest)).
- **Claude Code** with the Oncrawl MCP connected (see the Oncrawl help center for the MCP setup). Claude Desktop and
  claude.ai work for small sites, without the link sections.

## How to run it

1. **Install the extension.** Unzip it, open `chrome://extensions`, turn on Developer mode, click **Load unpacked** and
   pick the unzipped folder.
2. **Copy your lens context.** Open the Internal Linking lens of your crawl, click through its tabs, then click the
   extension icon and **Copy**.
3. **Ask your agent.** In Claude Code, in an empty folder:

   ```
   git clone https://github.com/phtraversac/agentic_audit && cd agentic_audit
   claude
   ```

   and paste:

   > Follow AGENT.md to build my internal linking audit. Here is the context of my lens: *(paste)*

   The agent proposes how to group your pages, waits for your confirmation, collects the data, and opens `audit.html`.

With Claude Desktop or claude.ai, paste the same sentence with the link to
AGENT.md (`https://raw.githubusercontent.com/phtraversac/agentic_audit/v0.1.0/AGENT.md`); the agent gives you a `raw.json`
file to load in the [hosted report](https://phtraversac.github.io/agentic_audit/).

## What is in this repository

| File | Role |
|---|---|
| `index.html` | The report and its engine: every score, verdict and simulation is computed here from `raw.json`. |
| `AGENT.md` | The recipe your agent follows: which MCP calls, how to save them, what to ask you. |
| `tools/pack.py` | Merges the saved MCP answers into `raw.json` and checks the link graph is complete. |
| `tools/check_orphans.py` | Checks the live HTTP status of orphan pages (asks before running, rate-limited). |
| `tools/inject.py` | Puts `raw.json` inside the report so it opens on its own. |
| `tools/test_engine.js` | `node tools/test_engine.js`: self-check of the engine. |

Python 3 standard library only, no install. The report loads Highcharts from the jsDelivr CDN.

## Limits

- The audit groups pages by URL rules your agent proposes and you confirm. Wrong rules give wrong groups: check
  them before the agent goes on.
- The simulated PageRank is computed on the crawl's link graph. It correlates with Oncrawl's Inrank but is not it:
  read the gains as orders of magnitude.
- Suggested anchors come from the Google queries of the 1,000 pages with the most impressions at most; other pages
  get their title.
- Thresholds (50 pages for a repeated block, 1,000 and 200 impressions for the priorities) suit mid-size sites; set
  `settings` in `raw.json` to change them.
