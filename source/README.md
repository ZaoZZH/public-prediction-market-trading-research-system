# Public soccer research article

Quarto + Plotly, hosted on GitHub Pages at
https://zaozzh.github.io/soccer-cross-venue-research/ (branch `codex/publication`, root).

## Design

The private research notebook ([02.1](../notebooks/02.1_cross_venue_gaps_by_competition.ipynb))
is unchanged. `build.py` executes its cells locally in one namespace, `charts.py` draws Plotly
versions of the computed objects, and `article.qmd.j2` is the trader-facing narrative. The
builder checks the notebook's cell layout and plot count so a changed notebook cannot be
published against a stale presentation mapping.

- Charts are laid out like the notebook: candidate groups as columns, outcome selections as
  rows, everything visible at once (no dropdowns, no collapsed sections). Each chart's
  figure JSON is inlined in the page and drawn by `charts.js`; the plotted aggregates are
  also written to `data/` as CSV and Plotly JSON.
- Colours: Kalshi green, Polymarket blue, for venues, trade sources and which venue holds YES.
- Light and dark themes (`theme-light.scss`, `theme-dark.scss`) with Quarto's toggle;
  `respect-user-color-scheme` follows the OS by default. `charts.js` re-themes every chart
  when the body class changes; trace colours are fixed, only chrome follows the theme.
- Numbers quoted in the text come from `key_numbers()` in `build.py`, read from the executed
  notebook, so the prose cannot drift from the charts. The only tables on the page are
  explanatory (definitions, candidate rule, fee model) plus the §8 frequency table.
- The hosting repository contains only the rendered bundle, chart aggregates, the source
  notebook without outputs and these publication scripts. Raw Parquet inputs stay local.

## Build and publish

From the repository root, with the analysis requirements plus `jinja2` installed and Quarto
available (built with 1.10.18; `~/.local/opt/quarto-1.10.18/bin/quarto` is the fallback path):

```bash
python -m pip install -r research/soccer_1x2_analysis/requirements.txt jinja2
python research/soccer_1x2_analysis/publication/build.py
```

The builder requires `availability.csv`, `trade_waits.parquet`, `gap_cents.csv`,
`screen_sweep.csv`, `matches.parquet`, `audit.parquet`, `screen.parquet`,
`conditions.parquet` and `manifest.json` under `outputs/gap_analysis`. It fails if any is
missing and never launches acquisition. Output: `publication/.build/source/_site/`.

To publish, replace the contents of the `.build/deploy` clone (branch `codex/publication` of
`ZaoZZH/soccer-cross-venue-research`) with `_site/`, commit and push. Pages serves the new
snapshot within a minute or two.

For new data:
1. Update curated inputs with the local pipeline and rebuild the gap-analysis exports, then
   `availability.py`, `gap_cents.py` and `screen_sweep.py` (see the parent README). Do not
   mix export generations.
2. Rerun notebook 02.1 and review candidate selection.
3. If cells moved, update `EXPECTED`/`NOTEBOOK_PLOTS` in `build.py` and the cell mapping in
   `charts.py`; the builder refuses to run otherwise.
4. Reread `article.qmd.j2`: numbers refresh automatically, the interpretation does not.
5. Run the builder, review `_site/index.html` locally, then publish.

Official documentation checked 2026-09-16:
- https://quarto.org/docs/output-formats/html-themes.html (dark mode, `respect-user-color-scheme`)
- https://quarto.org/docs/publishing/github-pages.html
- https://plotly.com/python/interactive-html-export/
