"""Plotly views of notebook 02.1's computed objects, laid out like the notebook: candidate cells as columns."""
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PM, K = '#2f6fd6', '#1a9e6b'             # Polymarket blue, Kalshi green: venues, trade sources, which venue holds YES
BOTH, NEITHER, POOLED = '#8b5cf6', '#b9c0c7', '#7d8791'
STATE_COLORS = [BOTH, K, PM, NEITHER]     # both fresh, only Kalshi fresh, only PM fresh, neither fresh
ROUTE_COLORS = {'taker/taker': '#d64550', 'taker/maker': '#e8a33d', 'maker/taker': '#8a929b', 'maker/maker': '#8b5cf6'}
DIRECTION_COLORS = {'PM YES + K NO': PM, 'K YES + PM NO': K, 'PM NO + K YES': K, 'pooled': POOLED, 'Pooled': POOLED}
PHASE_COLORS = {'pre_24h_to_1h': '#9aa4ae', 'pre_last_hour': '#e8a33d', 'post_0_to_55m': '#8b5cf6',
                'post_55_to_105m': '#c026d3', 'post_105_to_135m': '#d64550'}
WEIGHT_COLORS = {'per print': '#5c6b7a', 'per second': '#c9a227'}
LEGEND_RANK = {'Both fresh': 1, 'Only Kalshi fresh': 2, 'Only PM fresh': 3, 'Neither fresh': 4,
               'PM YES + K NO': 11, 'K YES + PM NO': 12, 'pooled': 13, 'Pooled': 13, 'per fresh second (dashed)': 14}
FONT = '"Source Sans 3", "Segoe UI", Helvetica, Arial, sans-serif'
WORDS = {
    'pre_24h_to_1h': '24 h to 1 h before kickoff', 'pre_last_hour': 'Last hour before kickoff',
    'post_0_to_105m': 'In play (0–105 min)', 'post_0_to_55m': '0–55 min after kickoff',
    'post_55_to_105m': '55–105 min after kickoff', 'post_105_to_135m': '105–135 min after kickoff',
    'KALSHI': 'Kalshi → Polymarket', 'POLYMARKET': 'Polymarket → Kalshi',
    'all': 'All outcomes', 'team_win': 'Home + away', 'draw': 'Draw',
    'all/all': 'Pooled (both sides)', 'buy/sell': 'PM buy / K sell', 'sell/buy': 'PM sell / K buy',
    'buy/buy': 'PM buy / K buy', 'sell/sell': 'PM sell / K sell',
}
SHORT_PHASE = {'post_0_to_105m': 'In play', 'pre_last_hour': 'Last pregame hour'}


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


def share_y(fig, row, cols, values, pad=1.08):
    """One explicit y range across a row, computed from the data (matched axes do not always autoscale together)."""
    top = float(np.nanmax(values)) * pad if len(values) else 1
    for c in range(1, cols + 1):
        fig.update_yaxes(range=[0, top], row=row, col=c)


def label_rows(fig, labels, ylabel, cols):
    """Row labels as first-column y-axis titles, as the notebook does."""
    for i, r in enumerate(labels):
        fig.update_yaxes(title_text=(f'<b>{r}</b><br>{ylabel}' if r else ylabel), title_font_size=12, row=i + 1, col=1)


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
        cents, labels = g('cents'), g('cent_labels')
        fig = grid(3, 4, titles, 820, shared_x=True, shared_y=True, vs=0.08)
        fig.update_layout(barmode='group')
        p = Panels(fig)
        rows = []
        for r, (name, outcomes) in enumerate(g('OUTCOME_SEL').items()):
            for c, cand in enumerate(CANDS):
                d = s['cell'](cents, cand); d = d[(d.pair == 'all/all') & d.outcome.isin(outcomes)]
                pct, st = s['cent_stats'](d)
                for weight, col in (('per print', 'n'), ('per second', 'time')):
                    p.add(go.Bar(x=labels, y=pct[col].round(3).tolist(), name=weight, marker_color=WEIGHT_COLORS[weight],
                                 hovertemplate='%{x} c: %{y:.2f}%<extra>' + weight + '</extra>'), r + 1, c + 1)
                    rows += [dict(cell=CELLS[c], outcome=name, gap_bucket=b, weighting=weight, share_pct=v, prints=st['prints'])
                             for b, v in zip(labels, pct[col].tolist())]
        for c in range(1, 5):
            fig.update_xaxes(title_text='PM − Kalshi (cents)', tickangle=-40, row=3, col=c)
        label_rows(fig, [readable(k) for k in g('OUTCOME_SEL')], '% of fresh prints', 4)
        data = pd.DataFrame(rows)
        for r, name in enumerate(g('OUTCOME_SEL')):
            share_y(fig, r + 1, 4, data[data.outcome == name].share_pct.values)
        return [(fig, data)]
    if i == 18:
        ORDER, vmax = g('ORDER'), float(g('vmax'))
        fig = grid(3, 4, titles, 960, vs=0.08, hs=0.06, legend=False)
        rows = []
        for (r, c), (z, lo, hi, nn) in g('mats').items():
            text = [[f'{z[a, b]:+.2f}c<br>{lo[a, b]:.0f}% | {hi[a, b]:.0f}%<br>{nn[a, b] / 1000:.0f}k' if np.isfinite(z[a, b]) else ''
                     for b in range(3)] for a in range(3)]
            fig.add_trace(go.Heatmap(z=np.round(z, 3).tolist(), x=ORDER, y=ORDER, text=text, texttemplate='%{text}', textfont_size=11,
                                     zmin=-vmax, zmax=vmax, colorscale='RdBu_r', showscale=(r, c) == (0, 3),
                                     colorbar=dict(title='PM − K<br>(cents)', len=0.28, y=0.86, thickness=12),
                                     customdata=np.stack([lo, hi, nn], axis=-1).tolist(),
                                     hovertemplate='PM %{y} / Kalshi %{x}<br>mean %{z:+.2f} c<br>≤ −2 c: %{customdata[0]:.1f}%<br>≥ +2 c: %{customdata[1]:.1f}%<br>%{customdata[2]:,.0f} prints<extra></extra>'),
                          row=r + 1, col=c + 1)
            for a in range(3):
                for b in range(3):
                    rows.append(dict(cell=CELLS[c], outcome=list(g('OUTCOME_SEL'))[r], pm_action=ORDER[a], k_action=ORDER[b],
                                     mean_gap_c=z[a, b], le_m2c_pct=lo[a, b], ge_p2c_pct=hi[a, b], prints=int(nn[a, b])))
        fig.update_yaxes(autorange='reversed')
        for c in range(1, 5):
            fig.update_xaxes(title_text='Kalshi taker action', row=3, col=c)
        label_rows(fig, [readable(k) for k in g('OUTCOME_SEL')], 'PM taker action', 4)
        return [(fig, pd.DataFrame(rows))]
    if i == 21:
        rates, routes, dirs = g('rates'), g('SCREEN_ROUTES'), g('DIRS')
        fig = grid(3, 4, titles, 820, shared_x=True, shared_y=True, vs=0.08)
        fig.update_layout(barmode='group')
        p = Panels(fig)
        for r, name in enumerate(g('OUTCOME_SEL')):
            for c, cl in enumerate(CELLS):
                d = rates[(rates.cell == cl) & (rates.outcome_sel == name)]
                for dr in dirs:
                    q = d[d.direction == dr].set_index('route').reindex(routes)
                    p.add(go.Bar(x=routes, y=q.pos_pct.round(3).tolist(), name=dr, marker_color=DIRECTION_COLORS[dr],
                                 customdata=q.n.tolist(), hovertemplate='%{x}: %{y:.2f}% of %{customdata:,.0f}<extra>' + dr + '</extra>'), r + 1, c + 1)
        for c in range(1, 5):
            fig.update_xaxes(title_text='Route (PM role / Kalshi role)', row=3, col=c)
        fig.update_yaxes(range=[0, 100])
        label_rows(fig, [readable(k) for k in g('OUTCOME_SEL')], '% of observations positive after fees', 4)
        data = rates[['cell', 'outcome_sel', 'route', 'direction', 'n', 'pos_pct', 'mean_net_c', 'open_pct_of_fresh']]
        return [(fig, data)]
    if i == 22:
        sw = g('sw')
        fig = grid(1, 4, titles, 400, shared_y=True)
        p = Panels(fig)
        for c, cand in enumerate(CANDS):
            for route in g('SCREEN_ROUTES'):
                d = sw[(sw.cell == CELLS[c]) & (sw.route == route)].sort_values('freshness')
                p.add(go.Scatter(x=d.freshness.tolist(), y=d.pos_pct.round(3).tolist(), name=route, mode='lines',
                                 line=dict(color=ROUTE_COLORS[route], width=2),
                                 hovertemplate='F = %{x} s: %{y:.1f}%<extra>' + route + '</extra>'), 1, c + 1)
            fig.add_vline(x=cand[2], line_dash='dot', line_color='#8a929b', row=1, col=c + 1)
        fig.update_xaxes(range=[0, 300], title_text='Freshness F (s)')
        fig.update_yaxes(range=[0, 100])
        fig.update_yaxes(title_text='% of observations positive after fees', row=1, col=1)
        return [(fig, sw[['cell', 'route', 'freshness', 'n', 'pos_0c', 'pos_pct']])]
    if i == 24:
        mm, names = g('mm'), g('STATE_NAMES')
        dirs = list(g('MM_DIRS'))
        fig = grid(6, 4, [competition(c[0]) + '<br>' + SHORT_PHASE[c[1]] for c in CANDS], 1500, shared_x=True, vs=0.045)
        fig.update_layout(barmode='stack')
        p = Panels(fig)
        state_cols = ['both_fresh_pct', 'k_only_pct_of_clock', 'pm_only_pct_of_clock']
        for c, cl in enumerate(CELLS):
            for r, d in enumerate(dirs):
                q = mm[(mm.cell == cl) & (mm.direction == d) & mm.freshness.isin(g('F_BARS'))].sort_values('freshness')
                for col, name, color in zip(state_cols, names[:3], STATE_COLORS[:3]):
                    p.add(go.Bar(x=q.freshness.tolist(), y=q[col].round(2).tolist(), name=name, marker_color=color, width=3.6,
                                 hovertemplate='F = %{x} s: %{y:.1f}%<extra>' + name + '</extra>'), r + 1, c + 1)
                p.add(go.Bar(x=q.freshness.tolist(), y=(100 - q[state_cols].sum(axis=1)).round(2).tolist(), name=names[3], width=3.6,
                             marker_color=NEITHER, hovertemplate='F = %{x} s: %{y:.1f}%<extra>' + names[3] + '</extra>'), r + 1, c + 1)
            for d in dirs:
                q = mm[(mm.cell == cl) & (mm.direction == d)].sort_values('freshness')
                color = DIRECTION_COLORS[d]
                p.add(go.Scatter(x=q.freshness.tolist(), y=q.pos_pct.round(3).tolist(), name=d, mode='lines', line=dict(color=color, width=2),
                                 hovertemplate='F = %{x} s: %{y:.1f}%<extra>' + d + '</extra>'), 4, c + 1)
                p.add(go.Scatter(x=q.freshness.tolist(), y=q.open_pct_of_clock.round(3).tolist(), name=d, mode='lines', line=dict(color=color, width=2),
                                 hovertemplate='F = %{x} s: %{y:.1f}% of clock<extra>' + d + '</extra>'), 5, c + 1)
                p.add(go.Scatter(x=q.freshness.tolist(), y=q.mean_net_c.round(4).tolist(), name=d, mode='lines', line=dict(color=color, width=2),
                                 hovertemplate='F = %{x} s: %{y:.2f} c per print<extra>' + d + '</extra>'), 6, c + 1)
                p.add(go.Scatter(x=q.freshness.tolist(), y=q.time_mean_net_c.round(4).tolist(), name='per fresh second (dashed)', mode='lines',
                                 line=dict(color=color, width=1.4, dash='dash'),
                                 hovertemplate='F = %{x} s: %{y:.2f} c per fresh second<extra>' + d + '</extra>'), 6, c + 1)
            fig.add_hline(y=0, line_color='#8a929b', line_width=1, row=6, col=c + 1)
            fig.update_xaxes(title_text='Freshness F (s)', row=6, col=c + 1)
        fig.update_xaxes(range=[0, g('F_MAX_MM') + 3])
        for r in (1, 2, 3, 4, 5):
            fig.update_yaxes(range=[0, 100], row=r)
        share_y(fig, 6, 4, mm[mm.freshness <= g('F_MAX_MM')][['mean_net_c', 'time_mean_net_c']].values.ravel(), pad=1.12)
        fig.update_yaxes(title_text='<b>PM YES + K NO</b><br>clock states (%)', row=1, col=1)
        fig.update_yaxes(title_text='<b>K YES + PM NO</b><br>clock states (%)', row=2, col=1)
        fig.update_yaxes(title_text='<b>Pooled</b><br>clock states (%)', row=3, col=1)
        fig.update_yaxes(title_text='<b>Positive rate</b><br>% of fresh observations', row=4, col=1)
        fig.update_yaxes(title_text='<b>Positive standing</b><br>% of clock', row=5, col=1)
        fig.update_yaxes(title_text='<b>Mean net edge</b><br>cents after fees', row=6, col=1)
        data = mm[['cell', 'direction', 'freshness', 'n', 'pos_pct', 'open_pct_of_clock', 'open_pct_of_fresh', 'mean_net_c',
                   'time_mean_net_c', 'both_fresh_pct', 'k_only_pct_of_clock', 'pm_only_pct_of_clock']]
        return [(fig, data)]
    if i == 28:
        cd = g('cd')
        keys = ['cell', 'direction', 'price_bucket']
        directed = cd.groupby(keys, observed=True)[['n', 'pos_0c']].sum().reset_index()
        pooled = cd.groupby(['cell', 'price_bucket'], observed=True)[['n', 'pos_0c']].sum().reset_index().assign(direction='Pooled')
        gg = pd.concat([directed, pooled], ignore_index=True)
        gg['pos_pct'] = 100 * gg.pos_0c / gg.n.replace(0, np.nan)
        levels = list(s['gaps'].PRICE_BUCKETS)
        series = list(g('CONDITION_DIRECTIONS')) + ['Pooled']
        fig = grid(1, 4, titles, 400, shared_y=True)
        fig.update_layout(barmode='group')
        p = Panels(fig)
        for c, cl in enumerate(CELLS):
            d = gg[gg.cell == cl]
            for name in series:
                q = d[d.direction == name].set_index('price_bucket').reindex(levels)
                p.add(go.Bar(x=levels, y=q.pos_pct.round(3).tolist(), name=name, marker_color=DIRECTION_COLORS[name], customdata=q.n.tolist(),
                             hovertemplate='%{x}: %{y:.1f}% of %{customdata:,.0f}<extra>' + name + '</extra>'), 1, c + 1)
        fig.update_xaxes(title_text='YES reference price')
        fig.update_yaxes(range=[0, 100])
        fig.update_yaxes(title_text='% positive within bucket (maker/maker)', row=1, col=1)
        return [(fig, gg[keys + ['n', 'pos_0c', 'pos_pct']])]
    return []
