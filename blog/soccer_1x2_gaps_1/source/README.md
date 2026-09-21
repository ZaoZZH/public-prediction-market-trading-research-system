# Kalshi vs Polymarket in soccer 1X2 markets (series)

Quarto + Plotly, part of the [public website](../../README.md). One builder, one notebook
execution, one hosted directory per part:

| Part | Template | Hosted at | Notebook cells |
| --- | --- | --- | --- |
| 1. Two tapes, one fixture | `part1.qmd.j2` | `blog/soccer_1x2_gaps_1/` | 02.1 §1–4 (cells 3–18) |
| 2. Fees, roles, frequency | not written yet | `blog/soccer_1x2_gaps_2/` | 02.1 §5–8 |
| 3. What happens next | not written yet | `blog/soccer_1x2_gaps_3/` | 02.2 |

This series supersedes the single article in [`../soccer_1x2_analysis/`](../soccer_1x2_analysis/README.md),
which stays until part 2 is published and is then deleted together with its copies of the
presentation files (`charts.js`, `styles.css`, `theme-*.scss`).

## Design

The private research notebook ([02.1](../../../research/soccer_1x2_analysis/notebooks/02.1_cross_venue_gaps_by_competition.ipynb))
is unchanged. `build.py` executes its cells locally in one namespace, `charts.py` draws Plotly
versions of the computed objects, and each `partN.qmd.j2` is one trader-facing narrative. The
builder checks the notebook's cell layout and plot count so a changed notebook cannot be
published against a stale presentation mapping. `PARTS` in `build.py` maps each hosted
directory to its template and the notebook cells whose views it shows.

- Charts are laid out like the notebook: candidate groups as columns, outcome or matchup × role
  selections as rows, everything visible at once. Panels of one chart share a single y range.
  Each chart's figure JSON is inlined in the page and drawn by `charts.js`; the plotted
  aggregates are also written to `data/` as CSV and Plotly JSON.
- Colours: Kalshi green, Polymarket blue, for venues and trade sources.
- Light and dark themes (`theme-light.scss`, `theme-dark.scss`) with Quarto's toggle;
  `respect-user-color-scheme` follows the OS by default. `charts.js` re-themes every chart
  when the body class changes; trace colours are fixed, only chrome follows the theme.
- Numbers quoted in the text come from `key_numbers()` in `build.py`, read from the executed
  notebook, so the prose cannot drift from the charts. Tables on the page are explanatory
  (definitions, 1X2 share of the raw tape, candidate rule, fixture concentration).
- Each hosted part carries only the rendered bundle, chart aggregates, the source notebook
  without outputs and these publication scripts. Raw Parquet inputs stay local.

## Build and publish

From the repository root, with the analysis requirements plus `jinja2` installed and Quarto
available (built with 1.10.18; `~/.local/opt/quarto-1.10.18/bin/quarto` is the fallback path):

```bash
python -m pip install -r research/soccer_1x2_analysis/requirements.txt jinja2
python public/build.py
```

The builder requires `availability.csv`, `trade_waits.parquet`, `gap_cents.csv`,
`screen_sweep.csv`, `market_type_share.csv`, `matches.parquet`, `audit.parquet`,
`screen.parquet`, `conditions.parquet` and `manifest.json` under
`research/soccer_1x2_analysis/outputs/gap_analysis/`. It fails if any is missing and never
launches acquisition. Each part renders to `public/blog/soccer_1x2_gaps/.build/<part>/_site/`;
the complete site is `public/_site/`.

For local review, serve `public/_site/` as described in the public website README.
Publish only that complete generated bundle when ready.

For new data:
1. Update curated inputs with the local pipeline and rebuild the gap-analysis exports, then
   `availability.py`, `gap_cents.py`, `screen_sweep.py` and `market_type_share.py` (see the
   [research README](../../../research/soccer_1x2_analysis/README.md)). Do not mix export generations.
2. Rerun notebook 02.1 and review candidate selection.
3. If cells moved, update `EXPECTED`/`NOTEBOOK_PLOTS`/`PARTS` in `build.py` and the cell mapping in
   `charts.py`; the builder refuses to run otherwise.
4. Reread each `partN.qmd.j2`: numbers refresh automatically, the interpretation does not.
5. Run the builder, review each `_site/index.html` locally, then publish.

Official documentation checked 2026-09-20:
- https://quarto.org/docs/output-formats/html-basics.html (`toc-location`, `toc-expand`; no native control to hide a left TOC on desktop)
- https://quarto.org/docs/output-formats/html-themes.html (dark mode, `respect-user-color-scheme`)
- https://plotly.com/python/interactive-html-export/
