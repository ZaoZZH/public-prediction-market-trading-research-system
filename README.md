# Public soccer research article

Quarto + native Plotly, hosted on GitHub Pages at
https://zaozzh.github.io/soccer-cross-venue-research/.

## Design and cost

The private research notebook is unchanged. `build.py` executes its existing
calculations locally and `charts.py` draws interactive views of those computed
objects. `article.qmd.j2` is the trader-facing narrative. All original figures
are represented, with secondary figures and tables inside expandable sections.
The builder checks the notebook structure and plot count to catch mapping drift.

The hosting repository contains only the rendered publication, plotted aggregates,
summary tables, source notebook without outputs, and the publication scripts.
The raw Parquet trade data and ingestion credentials stay in the research environment.
No cloud Python server, database, scheduled job, or API key is needed to read the page.

| Option | Cost / fit |
| --- | --- |
| GitHub Pages (selected) | Free for a public publication repository; existing GitHub authentication; static HTML/JS/CSV. 1 GB published site, 100 GB/month soft bandwidth limit. |
| Cloudflare Pages | Free tier supports 500 builds/month, 20,000 files, 25 MiB per asset. Good alternative with separate Cloudflare setup. |
| Quarto Pub | Free, public Quarto hosting; requires a Quarto Pub account. |
| Dash / hosted Python app | Useful for server-side queries later; unnecessary for these aggregate views. |

Official documentation checked 2026-09-15:
- https://quarto.org/docs/publishing/github-pages.html
- https://quarto.org/docs/publishing/quarto-pub.html
- https://quarto.org/docs/computations/python.html
- https://plotly.com/python/interactive-html-export/
- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- https://developers.cloudflare.com/pages/platform/limits/

## Build and manually update

From the research repository root, install its existing analysis requirements
and the publication dependency `jinja2>=3.1`, plus Quarto (built with 1.10.18):

```bash
python -m pip install -r research/soccer_1x2_analysis/requirements.txt
python -m pip install jinja2
python research/soccer_1x2_analysis/publication/build.py
```

The output is `publication/.build/source/_site/`. The builder requires the current
availability, waiting, gap-bucket, match, audit, screen, scenario, condition,
episode and manifest exports under `outputs/gap_analysis`. It fails if inputs
are missing; it does not launch acquisition or silently fetch newer data.

For new data:
1. Update curated inputs using the existing local pipeline.
2. Rebuild the gap-analysis exports, then availability and gap-cent exports,
   following the parent analysis README. Do not mix export generations.
3. Rerun notebook 02.1 and review candidate selection and results.
4. Update dated numerical commentary in `article.qmd.j2`; the headline percentages
   are editorial text, not automatically refreshed. Review them against the tables.
5. Run this builder. It refreshes chart data, source hashes, fixture range and build date.
6. Review the rendered article, then replace the publication repository's bundle
   with `_site/`, commit, and push. Pages serves the new snapshot.

Only the small public snapshot needs uploading. Hosting the acquisition pipeline
or raw data becomes useful only when adding cloud execution or larger live queries.
That migration can be independent of Quarto and the public URL. No automatic
data updates or ingestion have been built.

The included notebook is research source, not a standalone reproducibility bundle:
it imports project modules and reads private local exports. Public CSVs and Plotly
JSON provide the exact displayed aggregates. The manifest records SHA-256 hashes
of the notebook and required inputs, not proof of upstream freshness or consistency.
