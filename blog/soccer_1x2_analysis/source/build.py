"""Execute notebook 02.1 locally and render its public Quarto/Plotly snapshot."""
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

from charts import FONT, cell_label, competition, readable, views

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ANALYSIS = ROOT / 'research/soccer_1x2_analysis'
OUT = ANALYSIS / 'outputs/gap_analysis'
DEST = HERE / '.build/source'
NOTEBOOK = ANALYSIS / 'notebooks/02.1_cross_venue_gaps_by_competition.ipynb'
INPUTS = ['availability.csv', 'trade_waits.parquet', 'gap_cents.csv', 'screen_sweep.csv', 'matches.parquet',
          'audit.parquet', 'screen.parquet', 'conditions.parquet', 'manifest.json']
# A changed notebook needs review of the presentation mapping before publication.
EXPECTED = {3: 'cov = m.merge', 5: 'PH5 =', 7: 'STATE_COLS =', 9: 'SCREEN_GRID =', 11: 'PURE =', 13: 'wait4 =',
            16: 'OUTCOME_SEL =', 18: 'ORDER =', 20: 'fee_p =', 21: 'scr = export', 22: '# Last-print positive',
            24: 'MM_DIRS =', 26: 'cd = export', 28: 'plot_price_conditions()', 30: 'ph = screen_rates'}
NOTEBOOK_PLOTS = {3: 1, 5: 1, 7: 3, 9: 1, 11: 1, 13: 1, 16: 2, 18: 2, 21: 1, 22: 1, 24: 1, 28: 1, 30: 1}   # 9: fixture concentration; 16/18: outcome split, then matchup x role split (article uses the first)
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
    return text.replace('-', '\u2212')


def key_numbers(s):
    """Numbers quoted in the article, read from the executed notebook so the text cannot drift from the charts."""
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
    wg, cells = s['wg'], dict(zip(s['CANDS'], s['CELLS']))

    def wait(combo, phase, source, H, state='all'):
        cl = cells[next(c for c in s['CANDS'] if c[0] == combo and c[1] == phase)]
        F = 60 if state == 'all' else next(c[2] for c in s['CANDS'] if c[0] == combo and c[1] == phase)
        r = wg[(wg.cell == cl) & (wg.source == source) & (wg.other_state == state) & (wg.freshness == F) & (wg.horizon == H)]
        return pct(r.follow_pct.iloc[0])
    k['wait'] = {name: {H: wait(combo, phase, src, H) for H in (1, 5, 10, 60)}
                 for name, (combo, phase, src) in {'pl_k': (PL, IN_PLAY, 'KALSHI'), 'pl_pm': (PL, IN_PLAY, 'POLYMARKET'),
                                                   'ucl_k': (UCL, IN_PLAY, 'KALSHI'), 'wc_k': (WC, IN_PLAY, 'KALSHI'),
                                                   'wc_pm': (WC, IN_PLAY, 'POLYMARKET')}.items()}
    k['stale'] = {name: wait(combo, phase, src, 60, 'stale')
                  for name, (combo, phase, src) in {'pl_k': (PL, IN_PLAY, 'KALSHI'), 'pl_pm': (PL, IN_PLAY, 'POLYMARKET'),
                                                    'ucl_k': (UCL, IN_PLAY, 'KALSHI'), 'ucl_pm': (UCL, IN_PLAY, 'POLYMARKET'),
                                                    'wc_k': (WC, IN_PLAY, 'KALSHI')}.items()}
    summary = s['summary'].set_index(['cell', 'outcome'])

    def gap(combo, phase, outcome):
        r = summary.loc[(cells[next(c for c in s['CANDS'] if c[0] == combo and c[1] == phase)], outcome)]
        return dict(abs=cents(r.mean_abs_gap_c), mean=cents(r.mean_gap_c, True), ge2=pct(r.ge_2c_pct), lower=pct(r.pm_lower_1c_pct), higher=pct(r.pm_higher_1c_pct))
    k['gap'] = {'pl': gap(PL, IN_PLAY, 'all'), 'ucl': gap(UCL, IN_PLAY, 'all'), 'wc': gap(WC, IN_PLAY, 'all'), 'wcpre': gap(WC, LAST_HOUR, 'all'),
                'pl_team': gap(PL, IN_PLAY, 'team_win'), 'pl_draw': gap(PL, IN_PLAY, 'draw'),
                'ucl_team': gap(UCL, IN_PLAY, 'team_win'), 'ucl_draw': gap(UCL, IN_PLAY, 'draw')}
    pairs = pd.DataFrame([dict(cell=cl, outcome=o, pair=f'{a}/{b}', mean=z[x, y]) for (r, c), (z, *_) in s['mats'].items()
                          for x, a in enumerate(s['ORDER']) for y, b in enumerate(s['ORDER'])
                          for cl, o in [(s['CELLS'][c], list(s['OUTCOME_SEL'])[r])]]).set_index(['cell', 'outcome', 'pair'])['mean']

    def pair(combo, outcome, p):
        return cents(pairs.loc[(cells[next(c for c in s['CANDS'] if c[0] == combo and c[1] == IN_PLAY)], outcome, p)], True)
    k['pair'] = {'pl_team_sellbuy': pair(PL, 'team_win', 'sell/buy'), 'pl_team_buysell': pair(PL, 'team_win', 'buy/sell'),
                 'pl_team_sellsell': pair(PL, 'team_win', 'sell/sell'), 'pl_draw_sellsell': pair(PL, 'draw', 'sell/sell'),
                 'ucl_draw_sellsell': pair(UCL, 'draw', 'sell/sell'), 'pl_team_buybuy': pair(PL, 'team_win', 'buy/buy'),
                 'pl_draw_buybuy': pair(PL, 'draw', 'buy/buy'), 'pl_all_allall': pair(PL, 'all', 'all/all'),
                 'pl_draw_buysell': pair(PL, 'draw', 'buy/sell'), 'pl_draw_sellbuy': pair(PL, 'draw', 'sell/buy'),
                 'ucl_draw_buysell': pair(UCL, 'draw', 'buy/sell'), 'ucl_draw_sellbuy': pair(UCL, 'draw', 'sell/buy'),
                 'ucl_team_buysell': pair(UCL, 'team_win', 'buy/sell'), 'ucl_team_sellbuy': pair(UCL, 'team_win', 'sell/buy'),
                 'wc_all_allall': pair(WC, 'all', 'all/all')}
    rates = s['rates'].set_index(['cell', 'outcome_sel', 'route', 'direction'])

    def rate(combo, phase, outcome, route, direction, col='pos_pct'):
        v = rates.loc[(cells[next(c for c in s['CANDS'] if c[0] == combo and c[1] == phase)], outcome, route, direction), col]
        return pct(v) if col == 'pos_pct' else cents(v)
    D1, D2 = 'PM YES + K NO', 'K YES + PM NO'
    k['screen'] = {
        'tt_pl_1': rate(PL, IN_PLAY, 'all', 'taker/taker', D1), 'tt_pl_2': rate(PL, IN_PLAY, 'all', 'taker/taker', D2),
        'tt_wc_1': rate(WC, IN_PLAY, 'all', 'taker/taker', D1), 'tt_wcpre_1': rate(WC, LAST_HOUR, 'all', 'taker/taker', D1),
        'tt_pl_net': rate(PL, IN_PLAY, 'all', 'taker/taker', D1, 'mean_net_c'), 'tt_wc_net': rate(WC, IN_PLAY, 'all', 'taker/taker', D1, 'mean_net_c'),
        'mm_pl_1': rate(PL, IN_PLAY, 'all', 'maker/maker', D1), 'mm_pl_2': rate(PL, IN_PLAY, 'all', 'maker/maker', D2),
        'mm_ucl_1': rate(UCL, IN_PLAY, 'all', 'maker/maker', D1), 'mm_ucl_2': rate(UCL, IN_PLAY, 'all', 'maker/maker', D2),
        'mm_wc_1': rate(WC, IN_PLAY, 'all', 'maker/maker', D1), 'mm_wc_2': rate(WC, IN_PLAY, 'all', 'maker/maker', D2),
        'mm_wcpre_1': rate(WC, LAST_HOUR, 'all', 'maker/maker', D1), 'mm_wcpre_2': rate(WC, LAST_HOUR, 'all', 'maker/maker', D2),
        'mm_pl_net_1': rate(PL, IN_PLAY, 'all', 'maker/maker', D1, 'mean_net_c'), 'mm_pl_net_2': rate(PL, IN_PLAY, 'all', 'maker/maker', D2, 'mean_net_c'),
        'mm_wc_net_1': rate(WC, IN_PLAY, 'all', 'maker/maker', D1, 'mean_net_c'), 'mm_wcpre_net_2': rate(WC, LAST_HOUR, 'all', 'maker/maker', D2, 'mean_net_c'),
        'mm_pl_draw_1': rate(PL, IN_PLAY, 'draw', 'maker/maker', D1), 'mm_pl_draw_2': rate(PL, IN_PLAY, 'draw', 'maker/maker', D2),
        'mm_ucl_draw_1': rate(UCL, IN_PLAY, 'draw', 'maker/maker', D1), 'mm_ucl_draw_2': rate(UCL, IN_PLAY, 'draw', 'maker/maker', D2),
        'mm_wc_draw_1': rate(WC, IN_PLAY, 'draw', 'maker/maker', D1), 'mm_wc_draw_2': rate(WC, IN_PLAY, 'draw', 'maker/maker', D2),
        'mm_pl_team_1': rate(PL, IN_PLAY, 'team_win', 'maker/maker', D1), 'mm_pl_team_2': rate(PL, IN_PLAY, 'team_win', 'maker/maker', D2),
        'tm_pl_draw_2': rate(PL, IN_PLAY, 'draw', 'taker/maker', D2), 'tm_ucl_draw_2': rate(UCL, IN_PLAY, 'draw', 'taker/maker', D2),
        'tm_pl_team_2': rate(PL, IN_PLAY, 'team_win', 'taker/maker', D2), 'tm_pl_team_1': rate(PL, IN_PLAY, 'team_win', 'taker/maker', D1),
        'mt_pl_team_1': rate(PL, IN_PLAY, 'team_win', 'maker/taker', D1), 'mt_pl_team_2': rate(PL, IN_PLAY, 'team_win', 'maker/taker', D2),
    }
    one = s['rates'][s['rates'].route.isin(['taker/maker', 'maker/taker'])].pos_pct
    k['one_taker_min'], k['one_taker_max'] = pct(one.min()), pct(one.max())
    sw = s['sw'].set_index(['cell', 'route', 'freshness'])

    def sweep(combo, phase, route, F):
        return pct(sw.loc[(cells[next(c for c in s['CANDS'] if c[0] == combo and c[1] == phase)], route, F), 'pos_pct'])
    k['sweep'] = {'mm_pl_1': sweep(PL, IN_PLAY, 'maker/maker', 1), 'mm_pl_10': sweep(PL, IN_PLAY, 'maker/maker', 10),
                  'mm_pl_300': sweep(PL, IN_PLAY, 'maker/maker', 300), 'tt_pl_1': sweep(PL, IN_PLAY, 'taker/taker', 1),
                  'tt_pl_300': sweep(PL, IN_PLAY, 'taker/taker', 300), 'tm_pl_1': sweep(PL, IN_PLAY, 'taker/maker', 1),
                  'tm_pl_300': sweep(PL, IN_PLAY, 'taker/maker', 300), 'mt_pl_1': sweep(PL, IN_PLAY, 'maker/taker', 1),
                  'mt_pl_300': sweep(PL, IN_PLAY, 'maker/taker', 300)}
    mm = s['mm'].set_index(['cell', 'direction', 'freshness'])

    def clock(combo, phase, direction, F, col='open_pct_of_clock'):
        return pct(mm.loc[(cells[next(c for c in s['CANDS'] if c[0] == combo and c[1] == phase)], direction, F), col])
    k['mm'] = {'pl_open_1_60': clock(PL, IN_PLAY, D1, 60), 'pl_open_2_60': clock(PL, IN_PLAY, D2, 60), 'pl_open_1_10': clock(PL, IN_PLAY, D1, 10),
               'wc_open_1_5': clock(WC, IN_PLAY, D1, 5), 'wc_open_2_5': clock(WC, IN_PLAY, D2, 5), 'wc_open_1_60': clock(WC, IN_PLAY, D1, 60),
               'wcpre_open_1_10': clock(WC, LAST_HOUR, D1, 10), 'wcpre_open_2_10': clock(WC, LAST_HOUR, D2, 10),
               'pl_both_1_60': clock(PL, IN_PLAY, D1, 60, 'both_fresh_pct'), 'pl_both_2_60': clock(PL, IN_PLAY, D2, 60, 'both_fresh_pct'),
               'pl_both_1_10': clock(PL, IN_PLAY, D1, 10, 'both_fresh_pct'), 'ucl_both_1_60': clock(UCL, IN_PLAY, D1, 60, 'both_fresh_pct'),
               'ucl_both_2_60': clock(UCL, IN_PLAY, D2, 60, 'both_fresh_pct'),
               'wcpre_pos_1_10': clock(WC, LAST_HOUR, D1, 10, 'pos_pct'), 'wcpre_pos_2_10': clock(WC, LAST_HOUR, D2, 10, 'pos_pct')}
    # The text quotes the original coarse price levels; the export carries deciles, which nest in them exactly.
    coarse = {'<10c': ['0-10c'], '10-30c': ['10-20c', '20-30c'], '30-70c': ['30-40c', '40-50c', '50-60c', '60-70c'],
              '70-90c': ['70-80c', '80-90c'], '>=90c': ['90-100c']}
    cd = s['cd'].assign(price_bucket=lambda d: d.price_bucket.map({b: k for k, v in coarse.items() for b in v}))
    assert cd.price_bucket.notna().all(), 'unexpected price bucket'
    directed = cd.groupby(['cell', 'direction', 'price_bucket'], observed=True)[['n', 'pos_0c']].sum().reset_index()
    directed['pos_pct'] = 100 * directed.pos_0c / directed.n.replace(0, np.nan)
    price = directed.set_index(['cell', 'direction', 'price_bucket']).pos_pct

    def level(combo, phase, direction, bucket):
        return pct(price.loc[(cells[next(c for c in s['CANDS'] if c[0] == combo and c[1] == phase)], direction, bucket)])
    k['price'] = {'pl_1_mid': level(PL, IN_PLAY, D1, '30-70c'), 'pl_2_mid': level(PL, IN_PLAY, D2, '30-70c'),
                  'pl_1_high': level(PL, IN_PLAY, D1, '70-90c'), 'pl_2_high': level(PL, IN_PLAY, D2, '70-90c'),
                  'pl_1_low': level(PL, IN_PLAY, D1, '<10c'), 'pl_2_low': level(PL, IN_PLAY, D2, '<10c'),
                  'wc_2_mid': level(WC, IN_PLAY, D2, '30-70c'), 'wc_2_high': level(WC, IN_PLAY, D2, '70-90c'),
                  'wcpre_1_top': level(WC, LAST_HOUR, D1, '>=90c'), 'wcpre_2_mid': level(WC, LAST_HOUR, D2, '30-70c')}
    ph = s['ph'].set_index('cell')
    dist = pd.DataFrame(s['dist']).set_index('cell')
    k['freq'] = {'pl_hour': f"{ph.pos_per_fixture_hour[cells[(PL, IN_PLAY, 60)]]:,.0f}", 'wc_hour': f"{ph.pos_per_fixture_hour[cells[(WC, IN_PLAY, 5)]]:,.0f}",
                 'pl_clock': pct(ph.open_pct_of_clock[cells[(PL, IN_PLAY, 60)]]), 'ucl_clock': pct(ph.open_pct_of_clock[cells[(UCL, IN_PLAY, 60)]]),
                 'wc_clock': pct(ph.open_pct_of_clock[cells[(WC, IN_PLAY, 5)]]), 'wcpre_clock': pct(ph.open_pct_of_clock[cells[(WC, LAST_HOUR, 10)]]),
                 'top10_min': pct(dist.top10_share_pct.min()), 'top10_max': pct(dist.top10_share_pct.max()),
                 'all_have': 'every' if (dist.with_any == dist.fixtures).all() else 'nearly every'}
    fees = s['fee_table']
    k['fee50'] = {'pm_taker': f"{fees.loc[0.5, 'PM taker']:.2f}", 'k_taker': f"{fees.loc[0.5, 'Kalshi taker']:.2f}", 'k_maker': f"{fees.loc[0.5, 'Kalshi maker']:.2f}"}
    k['fee_round_trip'] = f"{fees.loc[0.5, 'PM taker'] + fees.loc[0.5, 'Kalshi taker']:.2f}"
    k['fee_mm'] = f"{fees.loc[0.5, 'PM maker'] + fees.loc[0.5, 'Kalshi maker']:.2f}"
    return k


def candidate_table(s):
    rows = []
    for (combo, phase), r in s['table'].iterrows():
        rows.append({'Competition': competition(combo), 'Window': readable(phase), 'Both fresh at F = 5 s': pct(r[5]),
                     'F = 10 s': pct(r[10]), 'F = 60 s': pct(r[60]), 'F used': f'{int(r.F)} s'})
    return pd.DataFrame(rows).to_html(index=False, border=0, classes='table table-sm', escape=False)


def frequency_table(s):
    ph = s['ph'].set_index('cell')
    dist = pd.DataFrame(s['dist']).set_index('cell')
    cells = dict(zip(s['CELLS'], s['CANDS']))
    rows = []
    for cl in s['CELLS']:
        p, d = ph.loc[cl], dist.loc[cl]
        rows.append({'Group': cell_label(cells[cl]), 'Fixtures': f'{int(d.fixtures):,}', 'Fresh observations': f'{int(p.n):,}',
                     'Positive per fixture-hour': f'{p.pos_per_fixture_hour:,.0f}', 'Positives per fixture (median)': f'{d["median"]:,.0f}',
                     'Positives per fixture (90th pct)': f'{d.p90:,.0f}', 'Top-10 fixtures share': pct(d.top10_share_pct),
                     'Standing: % of fresh clock': pct(p.open_pct_of_fresh), 'Standing: % of whole clock': pct(p.open_pct_of_clock)})
    return pd.DataFrame(rows).to_html(index=False, border=0, classes='table table-sm', escape=False)


def fee_table(s):
    t = s['fee_table'].copy()
    t.index = [f'{int(round(p * 100))} c' for p in t.index]
    t.index.name = 'Contract price'
    return t.round(2).to_html(border=0, classes='table table-sm')


def build():
    missing = [name for name in INPUTS if not (OUT / name).is_file()]
    if missing:
        raise SystemExit(f'Rebuild the local analysis exports first: {missing}')
    nb = nbformat.read(NOTEBOOK, as_version=4)
    if len(nb.cells) != 32 or any(not nb.cells[i].source.startswith(start) for i, start in EXPECTED.items()):
        raise SystemExit('Notebook structure changed. Review charts.py and build.py before rebuilding.')
    os.chdir(ROOT)   # the notebook locates the repository from the working directory
    shutil.rmtree(DEST, ignore_errors=True)   # no files from earlier builds survive into the bundle
    for folder in ['assets', 'data', 'source']:
        (DEST / folder).mkdir(parents=True, exist_ok=True)
    state, _ = run_notebook(nb)
    figures, charts_meta = {}, []
    for i in sorted(NOTEBOOK_PLOTS):
        for j, (fig, data) in enumerate(views(i, state)):
            name = f'chart-{i:02d}-{j}'
            # Public files carry plotted aggregates only: no trade rows, no account data.
            data.to_csv(DEST / 'data' / f'{name}.csv', index=False)
            fig_dict = plain(fig.to_plotly_json())
            fig_dict['layout'].pop('template', None)
            (DEST / 'data' / f'{name}.json').write_text(json.dumps(fig_dict, separators=(',', ':')), encoding='utf-8')
            payload = json.dumps(fig_dict, separators=(',', ':')).replace('<', '\\u003c')
            figures[f'{i}:{j}'] = (
                '::: {.column-screen-inset-right .chart-block}\n```{=html}\n'
                f'<div class="chart-frame"><div id="{name}" class="research-chart" style="height:{int(fig.layout.height)}px"></div></div>\n'
                f'<script type="application/json" data-chart="{name}">{payload}</script>\n```\n'
                f'<p class="chart-links"><a href="data/{name}.csv" download>Chart data (CSV)</a> · '
                f'<a href="data/{name}.json" download>Figure (Plotly JSON)</a></p>\n:::\n')
            charts_meta.append({'id': name, 'rows': len(data), 'notebook_cell': i})
            print(f'Cell {i}: chart {name} ({len(data)} rows)', flush=True)
    m = state['m']
    env = Environment(undefined=StrictUndefined)
    text = env.from_string((HERE / 'article.qmd.j2').read_text(encoding='utf-8')).render(
        chart=lambda key: figures[key], fixtures=f'{len(m):,}', competitions=m.combo.nunique(),
        first=m.kickoff_iso.min().strftime('%B %d, %Y'), last=m.kickoff_iso.max().strftime('%B %d, %Y'),
        date=datetime.now(timezone.utc).strftime('%Y-%m-%d'), candidates=candidate_table(state), frequency=frequency_table(state),
        fees=fee_table(state), k=key_numbers(state), chart_count=len(charts_meta),
    )
    (DEST / 'index.qmd').write_text(text, encoding='utf-8')
    for name in ['_quarto.yml', 'styles.css', 'theme-light.scss', 'theme-dark.scss']:
        shutil.copy2(HERE / name, DEST / name)
    (DEST / 'assets/plotly.min.js').write_text(get_plotlyjs(), encoding='utf-8')
    charts_js = (HERE / 'charts.js').read_text(encoding='utf-8').replace(
        '/*TEMPLATES*/', 'const TEMPLATES = ' + json.dumps({k: template(v) for k, v in TEMPLATES.items()}) + ';')
    (DEST / 'assets/charts.js').write_text(charts_js, encoding='utf-8')
    # Source download is deliberately limited to this study and its presentation layer.
    for cell in nb.cells:
        if cell.cell_type == 'code':
            cell.outputs, cell.execution_count = [], None
    nbformat.write(nb, DEST / 'source' / NOTEBOOK.name)
    for name in ['charts.py', 'charts.js', 'build.py', 'article.qmd.j2', 'README.md']:
        shutil.copy2(HERE / name, DEST / 'source' / name)
    manifest = {
        'built_at_utc': datetime.now(timezone.utc).isoformat(),
        'fixture_count': len(m), 'first_kickoff': str(m.kickoff_iso.min()), 'last_kickoff': str(m.kickoff_iso.max()),
        'notebook_sha256': hashlib.sha256(NOTEBOOK.read_bytes()).hexdigest(),
        'inputs': [{'file': n, 'bytes': (OUT / n).stat().st_size, 'sha256': hashlib.sha256((OUT / n).read_bytes()).hexdigest()} for n in INPUTS],
        'charts': charts_meta,
        'note': 'Trade-reference research. Public data contain chart aggregates only. Raw inputs remain local.',
    }
    (DEST / 'data/manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    quarto = shutil.which('quarto') or str(Path.home() / '.local/opt/quarto-1.10.18/bin/quarto')
    subprocess.run([quarto, 'render', str(DEST)], check=True, cwd=ROOT)
    (DEST / '_site/.nojekyll').touch()
    print(f'Published bundle ready: {DEST / "_site"}', flush=True)


if __name__ == '__main__':
    build()
