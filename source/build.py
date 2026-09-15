"""Execute 02.1 locally and render its public Quarto/Plotly snapshot."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nbformat
import pandas as pd
from jinja2 import Environment, StrictUndefined
from plotly.offline import get_plotlyjs

from charts import readable, views

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE.parent
ROOT = ANALYSIS.parent.parent
OUT = ANALYSIS / 'outputs/gap_analysis'
DEST = HERE / '.build/source'
NOTEBOOK = ANALYSIS / 'notebooks/02.1_cross_venue_gaps_by_competition.ipynb'
INPUTS = ['availability.csv', 'trade_waits.csv', 'gap_cents.csv', 'matches.parquet',
          'audit.parquet', 'screen.parquet', 'scenarios.parquet', 'conditions.parquet',
          'episodes.parquet', 'manifest.json']


def build():
    missing = [name for name in INPUTS if not (OUT / name).is_file()]
    if missing:
        raise SystemExit(f'Rebuild the local analysis exports first: {missing}')
    # A changed notebook needs review of the presentation mapping before publication.
    nb = nbformat.read(NOTEBOOK, as_version=4)
    expected = {3: 'cov = m.merge', 5: 'PH5 =', 7: 'STATE_COLS =', 9: 'wait4 =',
                14: 'OUTCOME_SEL =', 16: 'ORDER =', 18: 'OUTS =', 20: 'scr =',
                21: '# Fee scenarios:', 22: '# Last-print positive', 26: "plot_conditions('trigger'",
                28: "plot_conditions('price_bucket'", 30: 'ph = screen_rates', 32: 'ep = export'}
    if len(nb.cells) != 34 or any(not nb.cells[i].source.startswith(start) for i, start in expected.items()):
        raise SystemExit('Notebook structure changed. Review charts.py before rebuilding.')
    for folder in ['assets', 'charts', 'data', 'source']:
        (DEST / folder).mkdir(parents=True, exist_ok=True)
    (DEST / 'assets/plotly.min.js').write_text(get_plotlyjs(), encoding='utf-8')
    figures, tables, charts_meta = {}, {}, []
    state = {'__name__': '__publication__', '__file__': str(NOTEBOOK)}
    current = [0]
    shown = []

    def capture_display(value):
        if not isinstance(value, (pd.DataFrame, pd.Series)):
            raise TypeError(f'Unhandled notebook display: {type(value)}')
        value = value.to_frame() if isinstance(value, pd.Series) else value
        idx = current[0]
        number = len(tables.get(idx, []))
        name = f'table-{idx:02d}-{number}.csv'
        value.to_csv(DEST / 'data' / name)
        tables.setdefault(idx, []).append(
            f'<div class="table-scroll">{value.to_html(border=0, classes="table table-sm")}</div>'
            f'<p><a href="data/{name}" download>Download table (CSV)</a></p>')

    state['publication_display'] = capture_display
    old_show = plt.show
    plt.show = lambda *args, **kwargs: shown.append(current[0])
    try:
        for i, cell in enumerate(nb.cells):
            if cell.cell_type != 'code':
                continue
            current[0] = i
            source = cell.source.replace('from IPython.display import display', 'display = publication_display')
            with redirect_stdout(io.StringIO()):
                exec(compile(source, f'{NOTEBOOK.name}:cell-{i}', 'exec'), state)
            rendered = views(i, state)
            if len(rendered) != shown.count(i):
                raise ValueError(f'Cell {i}: {shown.count(i)} notebook plots vs {len(rendered)} interactive plots')
            for j, (fig, data) in enumerate(rendered):
                name = f'chart-{i:02d}-{j}'
                # CSVs carry only plotted aggregates/quantiles; no trade rows or account data.
                data.to_csv(DEST / 'data' / f'{name}.csv', index=False)
                fig.write_json(DEST / 'data' / f'{name}.json')
                menus = fig.layout.updatemenus
                buttons = [b.to_plotly_json() for b in menus[0].buttons] if menus else []
                fig.layout.updatemenus = ()
                fig.update_layout(margin_t=60 if fig.layout.title.text else 25)
                document = fig.to_html(include_plotlyjs='../assets/plotly.min.js', div_id=name,
                    config={'responsive': True, 'displaylogo': False, 'modeBarButtonsToRemove': ['sendDataToCloud'],
                            'toImageButtonOptions': {'format': 'svg'}}, full_html=True)
                control = ''
                if buttons:
                    options = ''.join(f'<option value="{k}">{html.escape(b["label"])}</option>' for k, b in enumerate(buttons))
                    control = f'<label class="view-label">View <select id="view" aria-label="Chart view">{options}</select></label>'
                    script = ('<script>const views=' + json.dumps(buttons).replace('<', '\\u003c') + ';'
                              'document.getElementById("view").addEventListener("change", e=>{'
                              'const b=views[Number(e.target.value)];Plotly.update(' + json.dumps(name) + ',b.args[0],b.args[1]||{});});</script>')
                    document = document.replace('</body>', script + '</body>')
                style = '<style>body{margin:0;font-family:Arial,sans-serif}.view-label{display:block;padding:12px;color:#245347;font-size:13px}select{width:calc(100% - 42px);padding:8px;border:1px solid #bdcec5;border-radius:5px;background:#f7faf7;color:#23302f}</style>'
                document = document.replace('<body>', '<body>' + style + control)
                (DEST / 'charts' / f'{name}.html').write_text(document, encoding='utf-8')
                height = int(fig.layout.height or 480) + (75 if buttons else 30)
                figures[f'{i}:{j}'] = (
                    f'<iframe class="research-chart" src="charts/{name}.html" title="Interactive chart {i}.{j}" '
                    f'loading="lazy" height="{height}"></iframe>\n'
                    f'<div class="chart-links"><a href="charts/{name}.html" target="_blank">Open full screen</a> · '
                    f'<a href="data/{name}.csv" download>Chart data (CSV)</a></div>')
                charts_meta.append({'id': name, 'rows': len(data), 'notebook_cell': i})
            plt.close('all')
            print(f'Cell {i}: {len(rendered)} interactive charts', flush=True)
    finally:
        plt.show = old_show

    def embed(key): return figures[key]
    def table(i): return '\n'.join(tables[i])
    m = state['m']
    candidate_rows = []
    for combo, phase, f in state['CANDS']:
        coverage = state['cov4'].query('combo == @combo and phase == @phase and freshness == @f').fresh_pct_of_clock.iloc[0]
        candidate_rows.append({'Competition': readable(combo), 'Window': readable(phase), 'Freshness (seconds)': f, 'Both fresh (%)': round(coverage, 2)})
    env = Environment(undefined=StrictUndefined)
    text = env.from_string((HERE / 'article.qmd.j2').read_text(encoding='utf-8')).render(
        chart=embed, table=table, fixtures=f'{len(m):,}', competitions=m.combo.nunique(),
        first=m.kickoff_iso.min().strftime('%B %d, %Y'), last=m.kickoff_iso.max().strftime('%B %d, %Y'),
        date=datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        candidates=pd.DataFrame(candidate_rows).to_html(index=False, border=0, classes='table table-sm'),
        chart_count=len(charts_meta), all_tables=tables,
    )
    (DEST / 'index.qmd').write_text(text, encoding='utf-8')
    for name in ['_quarto.yml', 'styles.css']:
        shutil.copy2(HERE / name, DEST / name)
    # Source download is deliberately limited to this study and its presentation layer.
    for cell in nb.cells:
        if cell.cell_type == 'code':
            cell.outputs, cell.execution_count = [], None
    nbformat.write(nb, DEST / 'source' / NOTEBOOK.name)
    for name in ['charts.py', 'build.py', 'article.qmd.j2', 'README.md']:
        shutil.copy2(HERE / name, DEST / 'source' / name)
    manifest = {
        'built_at_utc': datetime.now(timezone.utc).isoformat(),
        'fixture_count': len(m), 'first_kickoff': str(m.kickoff_iso.min()), 'last_kickoff': str(m.kickoff_iso.max()),
        'notebook_sha256': hashlib.sha256(NOTEBOOK.read_bytes()).hexdigest(),
        'inputs': [{'file': n, 'bytes': (OUT/n).stat().st_size, 'sha256': hashlib.sha256((OUT/n).read_bytes()).hexdigest()} for n in INPUTS],
        'charts': charts_meta,
        'note': 'Trade-reference research. Public data contain chart aggregates and summary tables. Raw inputs remain local.',
    }
    (DEST / 'data/manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    quarto = shutil.which('quarto') or str(Path.home() / '.local/opt/quarto-1.10.18/bin/quarto')
    subprocess.run([quarto, 'render', str(DEST)], check=True, cwd=ROOT)
    (DEST / '_site/.nojekyll').touch()
    print(f'Published bundle ready: {DEST / "_site"}', flush=True)


if __name__ == '__main__':
    build()
