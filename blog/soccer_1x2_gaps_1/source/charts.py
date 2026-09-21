"""Plotly views of notebook 02.1's computed objects, laid out like the notebook: candidate cells as columns."""
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PM, K = '#2f6fd6', '#1a9e6b'             # Polymarket blue, Kalshi green: venues and trade sources
BOTH, NEITHER = '#8b5cf6', '#b9c0c7'
STATE_COLORS = [BOTH, K, PM, NEITHER]     # both fresh, only Kalshi fresh, only PM fresh, neither fresh
PHASE_COLORS = {'pre_24h_to_1h': '#9aa4ae', 'pre_last_hour': '#e8a33d', 'post_0_to_55m': '#8b5cf6',
                'post_55_to_105m': '#c026d3', 'post_105_to_135m': '#d64550'}
WEIGHT_COLORS = {'per print': '#5c6b7a', 'per second': '#c9a227'}
CELL_COLORS = ['#8b5cf6', '#e8a33d', '#d64550', '#5c6b7a']   # one per candidate cell where cells are series, not columns
LEGEND_RANK = {'Both fresh': 1, 'Only Kalshi fresh': 2, 'Only PM fresh': 3, 'Neither fresh': 4}
FONT = '"Source Sans 3", "Segoe UI", Helvetica, Arial, sans-serif'
WORDS = {
    'pre_24h_to_1h': '24 h to 1 h before kickoff', 'pre_last_hour': 'Last hour before kickoff',
    'post_0_to_105m': 'In play (0–105 min)', 'post_0_to_55m': '0–55 min after kickoff',
    'post_55_to_105m': '55–105 min after kickoff', 'post_105_to_135m': '105–135 min after kickoff',
    'KALSHI': 'Kalshi → Polymarket', 'POLYMARKET': 'Polymarket → Kalshi',
    'all': 'All outcomes', 'team_win': 'Home + away', 'draw': 'Draw',
    'balanced | team_win': 'Balanced: home + away', 'balanced | draw': 'Balanced: draw',
    'unequal | strong': 'Unequal: strong side', 'unequal | weak': 'Unequal: weak side', 'unequal | draw': 'Unequal: draw',
    'all/all': 'Pooled (both sides)', 'buy/sell': 'PM buy / K sell', 'sell/buy': 'PM sell / K buy',
    'buy/buy': 'PM buy / K buy', 'sell/sell': 'PM sell / K sell',
}
SHORT_PHASE = {'post_0_to_105m': 'In play', 'pre_last_hour': 'Last pregame hour'}
F_ROBUST = (5, 10, 60)   # the cutoffs gap_cents.csv carries


def competition(combo):
    text = str(combo).replace('World Cup 2026/27', 'World Cup 2026').replace('UEFA Champions League Women', "Women's Champions League")
    return text.replace('UEFA Champions League', 'Champions League')


def short(combo):
    """Tick-label length for the ten-group charts: 'Champions League 25/26', 'World Cup 2026'."""
    return re.sub(r'\b20(\d\d)/', r'\1/', competition(combo).replace("Women's Champions League", "Women's CL"))


def readable(value):
    return WORDS.get(str(value), competition(value))


def cell_title(c):
    return f'{competition(c[0])}<br>{SHORT_PHASE[c[1]]} · F = {c[2]} s'


def cell_label(c):
    return f'{competition(c[0])} · {SHORT_PHASE[c[1]].lower()} · F = {c[2]} s'


def grid(rows, cols, col_titles, height, shared_x=False, shared_y=False, vs=None, hs=0.04, legend=True):
    titles = [str(t) for t in col_titles] + [''] * (rows * cols - len(col_titles))
    top = 118 if legend else 78
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=titles, shared_xaxes=shared_x, shared_yaxes=shared_y,
                        horizontal_spacing=hs, vertical_spacing=vs if vs is not None else min(0.14, 0.5 / max(rows, 1)))
    fig.update_layout(height=height, margin=dict(l=72, r=24, t=top, b=64), font=dict(family=FONT, size=12),
                      hovermode='closest', bargap=0.25,
                      legend=dict(orientation='h', x=0, xanchor='left', y=1 + 52 / (height - top - 64), yanchor='bottom',
                                  title_text='', font_size=12))
    for a in fig.layout.annotations:
        a.font.size = 12
    return fig


class Panels:
    """Adds traces to a subplot grid, showing each legend entry once."""
    def __init__(self, fig):
        self.fig, self.seen = fig, set()

    def add(self, trace, row, col):
        name = trace.name
        trace.showlegend = name not in self.seen
        trace.legendgroup = name
        trace.legendrank = LEGEND_RANK.get(name, 1000)
        self.seen.add(name)
        self.fig.add_trace(trace, row=row, col=col)


def sync_y(fig, values, pad=1.08):
    """One explicit y range for every panel, computed from the data (matched axes do not always autoscale together)."""
    top = float(np.nanmax(values)) * pad if len(values) else 1
    fig.update_yaxes(range=[0, top])
    return top


def label_rows(fig, labels, ylabel):
    """Row labels as first-column y-axis titles, as the notebook does."""
    for i, r in enumerate(labels):
        fig.update_yaxes(title_text=(f'<b>{r}</b><br>{ylabel}' if r else ylabel), title_font_size=12, row=i + 1, col=1)


MEAN_LINE = '#d64550'


def bucket_position(gap_c):
    """Position of a gap in cents on the categorical bucket axis: the centre bucket (−1, 1) at index 4 is 2 c wide,
    every other bucket 1 c wide, so a value maps piecewise-linearly onto category indices."""
    if -1 <= gap_c <= 1:
        return 4 + gap_c / 2
    return 4.5 + (gap_c - 1) if gap_c > 1 else 3.5 + (gap_c + 1)


def gap_distribution(s, selections, cands, cells, ymax=None):
    """Signed-gap bars (rows: outcome or matchup × role selections, columns: cells), one y range for every panel."""
    cents, labels = s['cents'], s['cent_labels']
    n_rows, n_cols = len(selections), len(cands)
    fig = grid(n_rows, n_cols, [cell_title(c) for c in cands], 200 + 210 * n_rows, shared_x=True, shared_y=True, vs=0.26 / n_rows)
    fig.update_layout(barmode='group')
    p = Panels(fig)
    rows = []
    for r, (name, sel) in enumerate(selections.items()):
        for c, cand in enumerate(cands):
            d = s['pick'](s['cell'](cents, cand), sel); d = d[d.pair == 'all/all']
            pct, st = s['cent_stats'](d)
            for weight, col in (('per print', 'n'), ('per second', 'time')):
                p.add(go.Bar(x=labels, y=pct[col].round(3).tolist(), name=weight, marker_color=WEIGHT_COLORS[weight],
                             hovertemplate='%{x} c: %{y:.2f}%<extra>' + weight + '</extra>'), r + 1, c + 1)
                rows += [dict(cell=cells[c], selection=name, gap_bucket=b, weighting=weight, share_pct=v, prints=st['prints'],
                              mean_gap_c=st['mean_gap_c']) for b, v in zip(labels, pct[col].tolist())]
            mean = st['mean_gap_c']
            fig.add_vline(x=bucket_position(mean), line_color=MEAN_LINE, line_width=1.5, line_dash='dash', row=r + 1, col=c + 1,
                          annotation_text=f'mean {mean:+.2f} c'.replace('-', '−'), annotation_position='top right',
                          annotation_font=dict(size=11, color=MEAN_LINE))
    for c in range(1, n_cols + 1):
        fig.update_xaxes(title_text='PM − Kalshi (cents)', tickangle=-40, row=n_rows, col=c)
    label_rows(fig, [readable(k) for k in selections], '% of fresh prints')
    data = pd.DataFrame(rows)
    fig.update_yaxes(range=[0, ymax if ymax else sync_y(fig, data.share_pct.values)])
    return fig, data


def gap_heatmap(s, mats, selections, cands, cells, vmax):
    """3×3 taker-action heatmaps (rows: selections, columns: cells) on one colour scale."""
    ORDER = s['ORDER']
    n_rows, n_cols = len(selections), len(cands)
    fig = grid(n_rows, n_cols, [cell_title(c) for c in cands], 120 + 280 * n_rows, vs=0.24 / n_rows, hs=0.06, legend=False)
    rows = []
    for (r, c), (z, lo, hi, nn) in mats.items():
        text = [[f'{z[a, b]:+.2f}c<br>{lo[a, b]:.0f}% | {hi[a, b]:.0f}%<br>{nn[a, b] / 1000:.0f}k' if np.isfinite(z[a, b]) else ''
                 for b in range(3)] for a in range(3)]
        fig.add_trace(go.Heatmap(z=np.round(z, 3).tolist(), x=ORDER, y=ORDER, text=text, texttemplate='%{text}', textfont_size=11,
                                 zmin=-vmax, zmax=vmax, colorscale='RdBu_r', showscale=(r, c) == (0, n_cols - 1),
                                 colorbar=dict(title='PM − K<br>(cents)', len=0.28, y=0.86, thickness=12),
                                 customdata=np.stack([lo, hi, nn], axis=-1).tolist(),
                                 hovertemplate='PM %{y} / Kalshi %{x}<br>mean %{z:+.2f} c<br>≤ −2 c: %{customdata[0]:.1f}%<br>≥ +2 c: %{customdata[1]:.1f}%<br>%{customdata[2]:,.0f} prints<extra></extra>'),
                      row=r + 1, col=c + 1)
        for a in range(3):
            for b in range(3):
                rows.append(dict(cell=cells[c], selection=list(selections)[r], pm_action=ORDER[a], k_action=ORDER[b],
                                 mean_gap_c=z[a, b], le_m2c_pct=lo[a, b], ge_p2c_pct=hi[a, b], prints=int(nn[a, b])))
    fig.update_yaxes(autorange='reversed')
    for c in range(1, n_cols + 1):
        fig.update_xaxes(title_text='Kalshi taker action', row=n_rows, col=c)
    label_rows(fig, [readable(k) for k in selections], 'PM taker action')
    return fig, pd.DataFrame(rows)


def views(i, s):
    """Return (figure, downloadable tidy data) pairs for each chart-producing cell."""
    g = s.get
    CANDS, CELLS = g('CANDS'), g('CELLS')
    titles = [cell_title(c) for c in CANDS]
    pop_order = list(g('pop').index)
    if i == 3:
        pop = g('pop')
        fig = go.Figure()
        fig.add_bar(x=[competition(c) for c in pop.index], y=pop.pm_trades_per_fixture.tolist(), name='Polymarket', marker_color=PM)
        fig.add_bar(x=[competition(c) for c in pop.index], y=pop.k_trades_per_fixture.tolist(), name='Kalshi', marker_color=K)
        fig.update_layout(height=440, barmode='group', margin=dict(l=72, r=24, t=50, b=120), font=dict(family=FONT, size=12),
                          legend=dict(orientation='h', x=0, y=1.08, title_text=''), yaxis_type='log',
                          yaxis_title='Trades per fixture (log scale)', xaxis_tickangle=-28)
        data = pop.reset_index()[['combo', 'fixtures', 'trades', 'pm_trades', 'k_trades', 'trades_per_fixture',
                                  'pm_trades_per_fixture', 'k_trades_per_fixture']]
        return [(fig, data)]
    if i == 5:
        avail = g('avail_all')
        combos = [c for c in pop_order if (avail.combo == c).any()]   # groups with prints on both venues
        fig = grid(3, 3, [short(c) for c in combos[:3]], 900, shared_y=True, vs=0.12, hs=0.05)
        p = Panels(fig)
        rows = []
        for n, combo in enumerate(combos):
            r, c = divmod(n, 3)
            d = avail[avail.combo == combo]
            for ph in g('PH5'):
                q = d[d.phase == ph].sort_values('freshness')
                p.add(go.Scatter(x=q.freshness.tolist(), y=q.fresh_pct_of_clock.round(2).tolist(), name=readable(ph), mode='lines',
                                 line=dict(color=PHASE_COLORS[ph], width=2), hovertemplate='F = %{x} s: %{y:.1f}%<extra>' + readable(ph) + '</extra>'),
                      r + 1, c + 1)
                rows.append(q[['combo', 'phase', 'freshness', 'fresh_pct_of_clock']])
        # titles below the first row by hand (make_subplots only labels the first row)
        for n in range(3, len(combos)):
            r, c = divmod(n, 3)
            fig.add_annotation(text=short(combos[n]), xref='x domain', yref='y domain', x=0.5, y=1.06, showarrow=False, font_size=12,
                               row=r + 1, col=c + 1)
        fig.update_xaxes(type='log', tickvals=[1, 2, 5, 10, 20, 60, 300], range=[0, np.log10(300)])
        fig.update_yaxes(range=[0, 100])
        for c in range(1, 4):
            fig.update_xaxes(title_text='Freshness F (s, log)', row=3, col=c)
        for r in range(1, 4):
            fig.update_yaxes(title_text='Both venues fresh (% of clock)', row=r, col=1)
        return [(fig, pd.concat(rows, ignore_index=True))]
    if i == 7:
        st4 = g('state4'); cols, names = g('STATE_COLS'), g('STATE_NAMES')
        Fs = (5, 10, 60)
        groups = [c for c in pop_order if (st4.combo == c).any()]
        fig = grid(3, 4, [readable(ph) for ph in g('PHASES')], 1080, shared_x=True, shared_y=True, vs=0.07)
        fig.update_layout(barmode='stack', margin_l=200)
        p = Panels(fig)
        rows = []
        for r, F in enumerate(Fs):
            for c, ph in enumerate(g('PHASES')):
                d = st4[(st4.pair == 'all/all') & (st4.phase == ph) & (st4.freshness == F)].set_index('combo').reindex(groups)
                for col, name, color in zip(cols, names, STATE_COLORS):
                    p.add(go.Bar(y=[short(x) for x in d.index], x=d[col].round(2).tolist(), orientation='h', name=name, marker_color=color,
                                 hovertemplate='%{y}: %{x:.1f}%<extra>' + name + '</extra>'), r + 1, c + 1)
                rows.append(d.reset_index().assign(phase=ph, freshness=F)[['combo', 'phase', 'freshness'] + cols])
        fig.update_yaxes(autorange='reversed')
        fig.update_xaxes(range=[0, 100])
        for c in range(1, 5):
            fig.update_xaxes(title_text='% of all outcome-seconds', row=3, col=c)
        for r, F in enumerate(Fs):
            fig.update_yaxes(title_text=f'<b>F = {F} s</b>', title_standoff=18, row=r + 1, col=1)
        return [(fig, pd.concat(rows, ignore_index=True))]
    if i == 9:
        # Lorenz curves: share of a cell's fresh cross-side observations held by its busiest fixtures.
        obs = g('obs')
        fig = go.Figure()
        rows = []
        for cl, cand, color in zip(CELLS, CANDS, CELL_COLORS):
            v = np.sort(obs.loc[cl].to_numpy())[::-1]
            k, share = len(v), 100 * np.cumsum(v) / v.sum()
            x = 100 * np.arange(1, k + 1) / k
            fig.add_scatter(x=x.round(3).tolist(), y=share.round(3).tolist(), name=cell_label(cand), mode='lines', line=dict(color=color, width=2),
                            hovertemplate='busiest %{x:.1f}% of fixtures: %{y:.1f}% of observations<extra>' + cell_label(cand) + '</extra>')
            rows += [dict(cell=cl, fixture_rank=int(j + 1), fixtures_pct=x[j], observations=int(v[j]), cumulative_pct=share[j]) for j in range(k)]
        fig.add_scatter(x=[0, 100], y=[0, 100], mode='lines', line=dict(color='#8a929b', width=1, dash='dot'), name='Equal share', hoverinfo='skip')
        fig.update_layout(height=460, margin=dict(l=72, r=24, t=90, b=64), font=dict(family=FONT, size=12), hovermode='closest',
                          legend=dict(orientation='h', x=0, y=1.02, yanchor='bottom', title_text=''),
                          xaxis=dict(title='% of fixtures, busiest first', range=[0, 100]),
                          yaxis=dict(title='% of fresh observations', range=[0, 100]))
        return [(fig, pd.DataFrame(rows))]
    if i == 11:
        st4 = g('state4'); cols, names = g('STATE_COLS'), g('STATE_NAMES')
        pairs = ['all/all'] + g('PURE')
        fig = grid(1, 4, titles, 380, shared_y=True)
        fig.update_layout(barmode='stack', margin_l=150)
        p = Panels(fig)
        rows = []
        for c, cand in enumerate(CANDS):
            d = st4[(st4.combo == cand[0]) & (st4.phase == cand[1]) & (st4.freshness == cand[2])].set_index('pair').reindex(pairs)
            for col, name, color in zip(cols, names, STATE_COLORS):
                p.add(go.Bar(y=[readable(x) for x in d.index], x=d[col].round(2).tolist(), orientation='h', name=name, marker_color=color,
                             hovertemplate='%{y}: %{x:.1f}%<extra>' + name + '</extra>'), 1, c + 1)
            rows.append(d.reset_index().assign(cell=CELLS[c])[['cell', 'pair'] + cols])
        fig.update_yaxes(autorange='reversed')
        fig.update_xaxes(range=[0, 100], title_text='% of all outcome-seconds')
        return [(fig, pd.concat(rows, ignore_index=True))]
    if i == 13:
        wg, H = g('wg'), g('H_MAX')
        fig = grid(1, 4, titles, 400, shared_y=True)
        p = Panels(fig)
        rows = []
        for c, cl in enumerate(CELLS):
            for src, color in (('KALSHI', K), ('POLYMARKET', PM)):
                d = wg[(wg.cell == cl) & (wg.source == src) & (wg.other_state == 'all') & (wg.freshness == 60) & (wg.horizon <= H)].sort_values('horizon')
                p.add(go.Scatter(x=d.horizon.tolist(), y=d.follow_pct.round(2).tolist(), name=readable(src), mode='lines+markers',
                                 line=dict(color=color, width=2), marker_size=4,
                                 hovertemplate='H = %{x} s: %{y:.1f}%<extra>' + readable(src) + '</extra>'), 1, c + 1)
                rows.append(d[['cell', 'source', 'horizon', 'triggers', 'eligible', 'followed', 'follow_pct']])
        fig.update_xaxes(range=[0, H], title_text='Forward horizon H (s)')
        fig.update_yaxes(range=[0, 100])
        fig.update_yaxes(title_text='% with a strictly later print on the other venue', row=1, col=1)
        return [(fig, pd.concat(rows, ignore_index=True))]
    if i == 16:
        # Outcome split, then the matchup × role split (in-play cells), on one y range; then the same
        # pooled distribution's summary at every cutoff gap_cents.csv carries (not a notebook plot).
        outcome_fig, outcome_data = gap_distribution(s, g('OUTCOME_SEL'), CANDS, CELLS)
        role_fig, role_data = gap_distribution(s, g('ROLE_SEL'), g('POST_CANDS'), g('POST_CELLS'), ymax=outcome_fig.layout.yaxis.range[1])
        cents, robust = g('cents'), []
        for c, cand in enumerate(CANDS):
            for F in F_ROBUST:
                d = cents[(cents.combo == cand[0]) & (cents.phase == cand[1]) & (cents.freshness == F) & (cents.pair == 'all/all')]
                _, st = s['cent_stats'](d)
                robust.append(dict(cell=CELLS[c], freshness=F, prints=st['prints'], mean_abs_gap_c=st['mean_abs_gap_c'],
                                   mean_gap_c=st['mean_gap_c'], ge_2c_pct=st['ge_2c_pct']))
        robust = pd.DataFrame(robust)
        fig = grid(2, 4, titles, 560, shared_x=True, shared_y=True, vs=0.14, legend=False)
        fig.update_layout(bargap=0.35)
        for c, cl in enumerate(CELLS):
            d = robust[robust.cell == cl]
            x = [f'{F} s' for F in d.freshness]
            fig.add_trace(go.Bar(x=x, y=d.mean_abs_gap_c.round(3).tolist(), marker_color=WEIGHT_COLORS['per print'], customdata=d.prints.tolist(),
                                 hovertemplate='F = %{x}: %{y:.2f} c over %{customdata:,.0f} prints<extra></extra>', showlegend=False), 1, c + 1)
            fig.add_trace(go.Bar(x=x, y=d.ge_2c_pct.round(3).tolist(), marker_color=WEIGHT_COLORS['per second'], customdata=d.prints.tolist(),
                                 hovertemplate='F = %{x}: %{y:.1f}% of %{customdata:,.0f} prints<extra></extra>', showlegend=False), 2, c + 1)
            fig.update_xaxes(title_text='Freshness F', row=2, col=c + 1)
        fig.update_yaxes(range=[0, float(robust.mean_abs_gap_c.max()) * 1.15], row=1)
        fig.update_yaxes(range=[0, float(robust.ge_2c_pct.max()) * 1.15], row=2)
        fig.update_yaxes(title_text='<b>Mean |PM − K|</b><br>cents per fresh print', row=1, col=1)
        fig.update_yaxes(title_text='<b>At least 2 c apart</b><br>% of fresh prints', row=2, col=1)
        return [(outcome_fig, outcome_data), (role_fig, role_data), (fig, robust)]
    if i == 18:
        mats, role_mats = g('mats'), g('role_mats')
        vmax = max(np.nanmax(np.abs(z)) for z, *_ in list(mats.values()) + list(role_mats.values()))
        return [gap_heatmap(s, mats, g('OUTCOME_SEL'), CANDS, CELLS, vmax),
                gap_heatmap(s, role_mats, g('ROLE_SEL'), g('POST_CANDS'), g('POST_CELLS'), vmax)]
    return []
