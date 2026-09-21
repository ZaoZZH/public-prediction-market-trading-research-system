"""Execute notebook 02.1 locally once and render each published part of the series as its own Quarto/Plotly snapshot."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd
from jinja2 import Environment, StrictUndefined
from plotly.offline import get_plotlyjs

from charts import F_ROBUST, FONT, cell_label, competition, readable, views

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ANALYSIS = ROOT / 'research/soccer_1x2_analysis'
OUT = ANALYSIS / 'outputs/gap_analysis'
BUILD = HERE / '.build'
NOTEBOOK = ANALYSIS / 'notebooks/02.1_cross_venue_gaps_by_competition.ipynb'
INPUTS = ['availability.csv', 'trade_waits.parquet', 'gap_cents.csv', 'screen_sweep.csv', 'market_type_share.csv', 'matches.parquet',
          'audit.parquet', 'screen.parquet', 'conditions.parquet', 'manifest.json']
# A changed notebook needs review of the presentation mapping before publication.
EXPECTED = {3: 'cov = m.merge', 5: 'PH5 =', 7: 'STATE_COLS =', 9: 'SCREEN_GRID =', 11: 'PURE =', 13: 'wait4 =',
            16: 'OUTCOME_SEL =', 18: 'ORDER =', 20: 'fee_p =', 21: 'scr = export', 22: '# Last-print positive',
            24: 'MM_DIRS =', 26: 'cd = export', 28: 'plot_price_conditions()', 30: 'ph = screen_rates'}
NOTEBOOK_PLOTS = {3: 1, 5: 1, 7: 3, 9: 1, 11: 1, 13: 1, 16: 2, 18: 2, 21: 1, 22: 1, 24: 1, 28: 1, 30: 1}   # 16/18: outcome split, then matchup x role split
# Published parts: hosted directory name -> narrative template and the notebook cells whose views it shows.
PARTS = {'soccer_1x2_gaps_1': {'template': 'part1.qmd.j2', 'cells': [3, 5, 7, 9, 11, 13, 16, 18]}}
PL, UCL, WC = 'Premier League 2025/26', 'UEFA Champions League 2025/26', 'World Cup 2026/27'
IN_PLAY, LAST_HOUR = 'post_0_to_105m', 'pre_last_hour'

# Chart chrome follows the page theme; trace colours are fixed in charts.py.
TEMPLATES = {
    'light': {'font': '#23302f', 'grid': '#e4e8e4', 'line': '#c6cfc8', 'hover': '#ffffff', 'modebar': '#7d8791', 'active': '#167263'},
    'dark': {'font': '#d9dfda', 'grid': '#2b3237', 'line': '#3d464c', 'hover': '#1f2529', 'modebar': '#8a929b', 'active': '#5fc3ad'},
}


def template(t):
    axis = dict(gridcolor=t['grid'], linecolor=t['line'], zerolinecolor=t['line'], tickcolor=t['line'], ticks='outside', showline=False)
    return {'layout': dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family=FONT, color=t['font'], size=12),
                           xaxis=axis, yaxis=axis, hoverlabel=dict(bgcolor=t['hover'], font=dict(family=FONT, color=t['font'])),
                           modebar=dict(color=t['modebar'], activecolor=t['active'], bgcolor='rgba(0,0,0,0)'),
                           legend=dict(bgcolor='rgba(0,0,0,0)'))}


def plain(obj):
    """JSON-ready copy: numpy scalars and arrays become Python numbers and lists; NaN becomes null."""
    if isinstance(obj, dict):
        return {k: plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [plain(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return plain(obj.tolist())
    if isinstance(obj, np.generic):
        return plain(obj.item())
    if isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


def run_notebook(nb):
    """Execute the code cells in one namespace; count the notebook's own plots to catch mapping drift."""
    state = {'__name__': '__publication__', '__file__': str(NOTEBOOK)}
    shown, current, tables = [], [0], {}

    def capture_display(value):
        if not isinstance(value, (pd.DataFrame, pd.Series)):
            raise TypeError(f'Unhandled notebook display: {type(value)}')
        tables.setdefault(current[0], []).append(value)

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
            if shown.count(i) != NOTEBOOK_PLOTS.get(i, 0):
                raise ValueError(f'Cell {i}: {shown.count(i)} notebook plots, expected {NOTEBOOK_PLOTS.get(i, 0)}')
            plt.close('all')
    finally:
        plt.show = old_show
    return state, tables


def pct(x, d=None):
    """Percent with one decimal; small rates keep two so they do not round to zero."""
    if d is None and abs(x) < 5:
        return f'{x:.2f}'.rstrip('0').rstrip('.') + '%'
    return f'{x:.{1 if d is None else d}f}%'


def cents(x, sign=False):
    """Cents with a real minus sign; `sign` forces an explicit + on positives (signed gaps)."""
    text = f'{x:+.2f}' if sign else f'{x:.2f}'
    return text.replace('-', '−')


def key_numbers(s):
    """Numbers quoted in the articles, read from the executed notebook so the text cannot drift from the charts."""
    k = {}
    st4 = s['state4']

    def states(combo, phase, F, pair='all/all'):
        r = st4[(st4.combo == combo) & (st4.phase == phase) & (st4.freshness == F) & (st4.pair == pair)].iloc[0]
        return dict(both=pct(r.fresh_pct_of_clock), k=pct(r.k_only_pct_of_clock), pm=pct(r.pm_only_pct_of_clock), neither=pct(r.neither_pct_of_clock))
    k['pl60'], k['ucl60'], k['pl5'] = states(PL, IN_PLAY, 60), states(UCL, IN_PLAY, 60), states(PL, IN_PLAY, 5)
    k['wc5'], k['wcpre10'] = states(WC, IN_PLAY, 5), states(WC, LAST_HOUR, 10)
    k['pl_pair'] = {pair: states(PL, IN_PLAY, 60, pair) for pair in s['PURE']}
    k['wcpre_sellbuy'] = states(WC, LAST_HOUR, 10, 'sell/buy')
    pop = s['pop']
    k['wc_vs_pl'] = f"{pop.trades_per_fixture[WC] / pop.trades_per_fixture[PL]:.0f}"
    k['wc_vs_l1'] = f"{pop.trades_per_fixture[WC] / pop.trades_per_fixture['Ligue 1 2025/26']:.0f}"
    k['k_over_pm_pl'] = f"{pop.k_trades_per_fixture[PL] / pop.pm_trades_per_fixture[PL]:.1f}"
    k['k_over_pm_wc'] = f"{pop.k_trades_per_fixture[WC] / pop.pm_trades_per_fixture[WC]:.1f}"
    share = s['share'].set_index(['venue', 'market_type'])
    k['share'] = {'k_bytes': pct(share.loc[('KALSHI', 'game'), 'bytes_pct']), 'k_trades': pct(share.loc[('KALSHI', 'game'), 'trades_pct']),
                  'k_contracts': pct(share.loc[('KALSHI', 'game'), 'contracts_pct']),
                  'pm_bytes': pct(share.loc[('POLYMARKET', 'moneyline'), 'bytes_pct']), 'pm_trades': pct(share.loc[('POLYMARKET', 'moneyline'), 'trades_pct']),
                  'pm_contracts': pct(share.loc[('POLYMARKET', 'moneyline'), 'contracts_pct']),
                  'pm_unknown_trades': pct(share.loc[('POLYMARKET', 'unknown'), 'trades_pct']), 'pm_unknown_contracts': pct(share.loc[('POLYMARKET', 'unknown'), 'contracts_pct']),
                  'k_total_trades': pct(share.loc[('KALSHI', 'total'), 'trades_pct']), 'pm_totals_trades': pct(share.loc[('POLYMARKET', 'totals'), 'trades_pct']),
                  'k_gb': f"{share.loc['KALSHI', 'bytes'].sum() / 1e9:.1f}", 'pm_gb': f"{share.loc['POLYMARKET', 'bytes'].sum() / 1e9:.1f}",
                  'k_rows_m': f"{share.loc['KALSHI', 'trades'].sum() / 1e6:.0f}", 'pm_rows_m': f"{share.loc['POLYMARKET', 'trades'].sum() / 1e6:.0f}"}
    wg, cells = s['wg'], dict(zip(s['CANDS'], s['CELLS']))

    def cell_of(combo, phase):
        return cells[next(c for c in s['CANDS'] if c[0] == combo and c[1] == phase)]
    conc = s['conc']
    k['conc'] = {'top1_max': pct(conc.top1_pct.max()), 'top5_min': pct(conc.top5_pct.min()), 'top5_max': pct(conc.top5_pct.max()),
                 'gini_min': f'{conc.gini.min():.2f}', 'gini_max': f'{conc.gini.max():.2f}',
                 'ucl_gini': f"{conc.gini[cell_of(UCL, IN_PLAY)]:.2f}", 'wc_gini': f"{conc.gini[cell_of(WC, IN_PLAY)]:.2f}",
                 'ucl_top10pct': pct(conc.top10pct_fixtures_pct[cell_of(UCL, IN_PLAY)]), 'ucl_max_over_median': f"{conc.max_over_median[cell_of(UCL, IN_PLAY)]:.0f}",
                 'pl_top10pct': pct(conc.top10pct_fixtures_pct[cell_of(PL, IN_PLAY)])}

    def wait(combo, phase, source, H):
        r = wg[(wg.cell == cell_of(combo, phase)) & (wg.source == source) & (wg.other_state == 'all') & (wg.freshness == 60) & (wg.horizon == H)]
        return pct(r.follow_pct.iloc[0])
    k['wait'] = {name: {H: wait(combo, phase, src, H) for H in (1, 5, 10, 60)}
                 for name, (combo, phase, src) in {'pl_k': (PL, IN_PLAY, 'KALSHI'), 'pl_pm': (PL, IN_PLAY, 'POLYMARKET'),
                                                   'ucl_k': (UCL, IN_PLAY, 'KALSHI'), 'wc_k': (WC, IN_PLAY, 'KALSHI'),
                                                   'wc_pm': (WC, IN_PLAY, 'POLYMARKET')}.items()}
    summary = pd.concat([s['summary'], s['role_summary']]).set_index(['cell', 'outcome'])

    def gap(combo, phase, outcome):
        r = summary.loc[(cell_of(combo, phase), outcome)]
        return dict(abs=cents(r.mean_abs_gap_c), mean=cents(r.mean_gap_c, True), ge2=pct(r.ge_2c_pct), lower=pct(r.pm_lower_1c_pct), higher=pct(r.pm_higher_1c_pct))
    k['gap'] = {'pl': gap(PL, IN_PLAY, 'all'), 'ucl': gap(UCL, IN_PLAY, 'all'), 'wc': gap(WC, IN_PLAY, 'all'), 'wcpre': gap(WC, LAST_HOUR, 'all'),
                'pl_team': gap(PL, IN_PLAY, 'team_win'), 'pl_draw': gap(PL, IN_PLAY, 'draw'),
                'ucl_team': gap(UCL, IN_PLAY, 'team_win'), 'ucl_draw': gap(UCL, IN_PLAY, 'draw'), 'wc_draw': gap(WC, IN_PLAY, 'draw')}
    for name, sel in {'bal_team': 'balanced | team_win', 'bal_draw': 'balanced | draw', 'strong': 'unequal | strong',
                      'weak': 'unequal | weak', 'uneq_draw': 'unequal | draw'}.items():
        for prefix, combo in (('pl', PL), ('ucl', UCL), ('wc', WC)):
            k['gap'][f'{prefix}_{name}'] = gap(combo, IN_PLAY, sel)
    parts = s['parts']; parts = parts[parts.pair == 'all/all'].groupby(['cell', 'matchup']).n.sum().unstack(fill_value=0)
    k['matchup'] = {'unequal_min': pct(100 * (parts.unequal / parts.sum(axis=1)).min()), 'unequal_max': pct(100 * (parts.unequal / parts.sum(axis=1)).max()),
                    'unknown_max': pct(100 * (parts.get('unknown', 0) / parts.sum(axis=1)).max())}
    pairs = pd.concat([s['pair_rows'], s['role_pair_rows']]).set_index(['cell', 'outcome', 'pm_action', 'k_action']).mean_gap_c

    def pair(combo, outcome, p):
        a, b = p.split('/')
        return pairs.loc[(cell_of(combo, IN_PLAY), outcome, a, b)]
    raw_pairs = {'pl_team_sellbuy': pair(PL, 'team_win', 'sell/buy'), 'pl_team_buysell': pair(PL, 'team_win', 'buy/sell'),
                 'pl_team_sellsell': pair(PL, 'team_win', 'sell/sell'), 'pl_draw_sellsell': pair(PL, 'draw', 'sell/sell'),
                 'pl_team_buybuy': pair(PL, 'team_win', 'buy/buy'), 'pl_all_allall': pair(PL, 'all', 'all/all'),
                 'pl_draw_buysell': pair(PL, 'draw', 'buy/sell'), 'pl_draw_sellbuy': pair(PL, 'draw', 'sell/buy'),
                 'ucl_draw_buysell': pair(UCL, 'draw', 'buy/sell'), 'ucl_draw_sellbuy': pair(UCL, 'draw', 'sell/buy'),
                 'ucl_team_buysell': pair(UCL, 'team_win', 'buy/sell'), 'ucl_team_sellbuy': pair(UCL, 'team_win', 'sell/buy'),
                 'wc_all_allall': pair(WC, 'all', 'all/all'), 'wc_team_sellbuy': pair(WC, 'team_win', 'sell/buy'), 'wc_team_buysell': pair(WC, 'team_win', 'buy/sell'),
                 'pl_strong_sellbuy': pair(PL, 'unequal | strong', 'sell/buy'), 'pl_weak_sellbuy': pair(PL, 'unequal | weak', 'sell/buy'),
                 'ucl_strong_sellbuy': pair(UCL, 'unequal | strong', 'sell/buy'), 'ucl_weak_sellbuy': pair(UCL, 'unequal | weak', 'sell/buy'),
                 'pl_strong_buysell': pair(PL, 'unequal | strong', 'buy/sell'), 'pl_weak_buysell': pair(PL, 'unequal | weak', 'buy/sell'),
                 'ucl_uneq_draw_buysell': pair(UCL, 'unequal | draw', 'buy/sell'), 'ucl_bal_draw_buysell': pair(UCL, 'balanced | draw', 'buy/sell')}
    k['pair'] = {name: cents(v, True) for name, v in raw_pairs.items()}          # signed, for the heatmap prose
    k['pair_abs'] = {name: cents(abs(v)) for name, v in raw_pairs.items()}      # unsigned, where the text already says which way
    # Pooled gap at every cutoff gap_cents.csv carries.
    cts = s['cents']
    robust = {}
    for c in s['CANDS']:
        for F in F_ROBUST:
            d = cts[(cts.combo == c[0]) & (cts.phase == c[1]) & (cts.freshness == F) & (cts.pair == 'all/all')]
            _, st = s['cent_stats'](d)
            robust[(c[0], c[1], F)] = st
    k['robust'] = {f'{prefix}_{F}': dict(abs=cents(robust[(combo, phase, F)]['mean_abs_gap_c']), ge2=pct(robust[(combo, phase, F)]['ge_2c_pct']))
                   for prefix, combo, phase in (('pl', PL, IN_PLAY), ('ucl', UCL, IN_PLAY), ('wc', WC, IN_PLAY), ('wcpre', WC, LAST_HOUR)) for F in F_ROBUST}
    return k


def html_table(df, index=False):
    return df.to_html(index=index, border=0, classes='table table-sm', escape=False)


def candidate_table(s):
    rows = []
    for (combo, phase), r in s['table'].iterrows():
        rows.append({'Competition': competition(combo), 'Window': readable(phase), 'Both fresh at F = 5 s': pct(r[5]),
                     'F = 10 s': pct(r[10]), 'F = 60 s': pct(r[60]), 'F used': f'{int(r.F)} s'})
    return html_table(pd.DataFrame(rows))


def share_table(s):
    share = s['share'].set_index(['venue', 'market_type'])
    rows = []
    for venue, mtype, name in (('KALSHI', 'game', 'Kalshi'), ('POLYMARKET', 'moneyline', 'Polymarket')):
        r = share.loc[(venue, mtype)]
        rows.append({'Venue': name, '1X2 market type': f'<code>{mtype}</code>', 'Files': f'{int(r.files):,}', 'Share of bytes': pct(r.bytes_pct),
                     'Share of trade rows': pct(r.trades_pct), 'Share of contracts': pct(r.contracts_pct)})
    return html_table(pd.DataFrame(rows))


def concentration_table(s):
    conc, cells = s['conc'], dict(zip(s['CELLS'], s['CANDS']))
    rows = []
    for cl, r in conc.iterrows():
        rows.append({'Group': cell_label(cells[cl]), 'Fixtures': f'{int(r.fixtures):,}', 'Fresh observations': f'{int(r.observations):,}',
                     'Busiest fixture': pct(r.top1_pct), 'Busiest 5': pct(r.top5_pct), 'Busiest 10% of fixtures': pct(r.top10pct_fixtures_pct),
                     'Gini': f'{r.gini:.2f}', 'Median per fixture': f'{r.median_obs:,.0f}'})
    return html_table(pd.DataFrame(rows))


def chart_block(name, fig, payload):
    return ('::: {.column-screen-inset-right .chart-block}\n```{=html}\n'
            f'<div class="chart-frame"><div id="{name}" class="research-chart" style="height:{int(fig.layout.height)}px"></div></div>\n'
            f'<script type="application/json" data-chart="{name}">{payload}</script>\n```\n'
            f'<p class="chart-links"><a href="data/{name}.csv" download>Chart data (CSV)</a> · '
            f'<a href="data/{name}.json" download>Figure (Plotly JSON)</a></p>\n:::\n')


def build_part(slug, spec, nb, state, k, quarto):
    dest = BUILD / slug
    shutil.rmtree(dest, ignore_errors=True)   # no files from earlier builds survive into the bundle
    for folder in ['assets', 'data', 'source']:
        (dest / folder).mkdir(parents=True, exist_ok=True)
    figures, charts_meta = {}, []
    for i in spec['cells']:
        for j, (fig, data) in enumerate(views(i, state)):
            name = f'chart-{i:02d}-{j}'
            # Public files carry plotted aggregates only: no trade rows, no account data.
            data.to_csv(dest / 'data' / f'{name}.csv', index=False)
            fig_dict = plain(fig.to_plotly_json())
            fig_dict['layout'].pop('template', None)
            (dest / 'data' / f'{name}.json').write_text(json.dumps(fig_dict, separators=(',', ':')), encoding='utf-8')
            figures[f'{i}:{j}'] = chart_block(name, fig, json.dumps(fig_dict, separators=(',', ':')).replace('<', '\\u003c'))
            charts_meta.append({'id': name, 'rows': len(data), 'notebook_cell': i})
            print(f'{slug} cell {i}: chart {name} ({len(data)} rows)', flush=True)
    m = state['m']
    env = Environment(undefined=StrictUndefined)
    text = env.from_string((HERE / spec['template']).read_text(encoding='utf-8')).render(
        chart=lambda key: figures[key], fixtures=f'{len(m):,}', competitions=m.combo.nunique(),
        first=m.kickoff_iso.min().strftime('%B %d, %Y'), last=m.kickoff_iso.max().strftime('%B %d, %Y'),
        date=datetime.now(timezone.utc).strftime('%Y-%m-%d'), candidates=candidate_table(state), share=share_table(state),
        concentration=concentration_table(state), k=k, chart_count=len(charts_meta),
    )
    (dest / 'index.qmd').write_text(text, encoding='utf-8')
    for name in ['_quarto.yml', 'styles.css', 'theme-light.scss', 'theme-dark.scss']:
        shutil.copy2(HERE / name, dest / name)
    (dest / 'assets/plotly.min.js').write_text(get_plotlyjs(), encoding='utf-8')
    charts_js = (HERE / 'charts.js').read_text(encoding='utf-8').replace(
        '/*TEMPLATES*/', 'const TEMPLATES = ' + json.dumps({key: template(v) for key, v in TEMPLATES.items()}) + ';')
    (dest / 'assets/charts.js').write_text(charts_js, encoding='utf-8')
    # Source download is deliberately limited to this study and its presentation layer.
    nbformat.write(nb, dest / 'source' / NOTEBOOK.name)
    for name in ['charts.py', 'charts.js', 'build.py', spec['template'], 'README.md']:
        shutil.copy2(HERE / name, dest / 'source' / name)
    manifest = {
        'built_at_utc': datetime.now(timezone.utc).isoformat(), 'part': slug,
        'fixture_count': len(m), 'first_kickoff': str(m.kickoff_iso.min()), 'last_kickoff': str(m.kickoff_iso.max()),
        'notebook_sha256': hashlib.sha256(NOTEBOOK.read_bytes()).hexdigest(),
        'inputs': [{'file': n, 'bytes': (OUT / n).stat().st_size, 'sha256': hashlib.sha256((OUT / n).read_bytes()).hexdigest()} for n in INPUTS],
        'charts': charts_meta,
        'note': 'Trade-reference research. Public data contain chart aggregates only. Raw inputs remain local.',
    }
    (dest / 'data/manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    subprocess.run([quarto, 'render', str(dest)], check=True, cwd=ROOT)
    (dest / '_site/.nojekyll').touch()
    print(f'Published bundle ready: {dest / "_site"}', flush=True)


def build():
    missing = [name for name in INPUTS if not (OUT / name).is_file()]
    if missing:
        raise SystemExit(f'Rebuild the local analysis exports first: {missing}')
    nb = nbformat.read(NOTEBOOK, as_version=4)
    if len(nb.cells) != 32 or any(not nb.cells[i].source.startswith(start) for i, start in EXPECTED.items()):
        raise SystemExit('Notebook structure changed. Review charts.py and build.py before rebuilding.')
    os.chdir(ROOT)   # the notebook locates the repository from the working directory
    state, _ = run_notebook(nb)
    k = key_numbers(state)
    for cell in nb.cells:
        if cell.cell_type == 'code':
            cell.outputs, cell.execution_count = [], None
    quarto = shutil.which('quarto') or str(Path.home() / '.local/opt/quarto-1.10.18/bin/quarto')
    for slug, spec in PARTS.items():
        build_part(slug, spec, nb, state, k, quarto)


if __name__ == '__main__':
    build()
