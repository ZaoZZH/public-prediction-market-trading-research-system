"""Part 3 of the series: Plotly views, quoted numbers and tables from notebook 02.2.1 (maker/maker).

Each view reads the notebook namespace as it stood right after the cell it shows (the notebook reuses
short names such as `g`, `C` and `tot` across sections), so `views(i, snaps)` takes that cell's snapshot.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from charts import BOTH, FONT, K, PM, POOLED, Panels, competition, grid, label_rows

CELLS = ['PL in play, F=60s', 'UCL in play, F=60s', 'WC in play, F=5s', 'WC last pregame hour, F=10s']
CELL_TITLES = ['Premier League 2025/26<br>In play · F = 60 s', 'Champions League 2025/26<br>In play · F = 60 s',
               'World Cup 2026<br>In play · F = 5 s', 'World Cup 2026<br>Last pregame hour · F = 10 s']
D1, D2 = 'PM YES + K NO', 'K YES + PM NO'
DIR_COLORS = {D1: PM, D2: K}
WC = 'World Cup 2026/27'
CLUBS = 'All club competitions (pooled)'
WAIT_GROUPS = ['Premier League 2025/26', 'UEFA Champions League 2025/26', CLUBS, WC]
GUARD_COLORS = {0: '#5c6b7a', 1: '#e8a33d'}          # guard off / on
KP = {0: 'Kalshi order at PM ask', 1: 'Kalshi order at Kalshi ask'}
HATCH = '/'


def pct(x, d=0):
    return f'{x:.{d}f}%'


def c2(x, d=2, sign=False):
    return (f'{x:+.{d}f}' if sign else f'{x:.{d}f}').replace('-', '−')


def rng(values, fmt, sep='–'):
    """'85–90%', '$9.0–14.9', '−0.36 to −0.27', '0.8–1.4'."""
    lo, hi = float(np.nanmin(values)), float(np.nanmax(values))
    a, b = fmt(lo), fmt(hi)
    if a == b:
        return a
    if a.endswith('%') and b.endswith('%'):
        return f'{a[:-1]}–{b}'
    if a.startswith('$') and b.startswith('$'):
        return f'{a}–{b[1:]}'
    if a[0] in '+−' or b[0] in '+−':
        return f'{a} to {b}'
    return f'{a}{sep}{b}'


def usd(x, d=1):
    return ('−' if x < 0 else '') + f'${abs(x):.{d}f}'


def group_title(name):
    return {CLUBS: 'All club competitions', 'PL + UCL 2025/26 (pooled)': 'Premier League + Champions League 25/26'}.get(name, competition(name))


# --- views ------------------------------------------------------------------------------------

def price_view(s):
    """§1: % positive and mean net edge by YES price, both directions, team win and draw rows."""
    g, pb = s['g'], s['PB']
    rows = [('team win', 'pos_pct'), ('team win', 'net_c'), ('draw', 'pos_pct'), ('draw', 'net_c')]
    fig = grid(4, 4, CELL_TITLES, 1180, shared_x=True, vs=0.06)
    fig.update_layout(barmode='group')
    p = Panels(fig)
    for r, (sel, col) in enumerate(rows):
        for c, cl in enumerate(CELLS):
            for d in (D1, D2):
                q = g[(g.cell == cl) & (g.sel == sel) & (g.direction == d)].set_index('price_bucket').reindex(pb)
                ex = q.excluded.fillna(True).astype(bool)
                y = q[col].clip(lower=-1.5) if col == 'net_c' else q[col]
                p.add(go.Bar(x=pb, y=y.round(3).tolist(), name=d,
                             marker=dict(color=DIR_COLORS[d], opacity=[.35 if e else 1 for e in ex],
                                         pattern=dict(shape=[HATCH if e else '' for e in ex])),
                             customdata=np.stack([q.n_k.fillna(0), q.fixtures.fillna(0), q.pos_pct, q.net_c], axis=-1).round(3).tolist(),
                             hovertemplate='%{x}: %{customdata[2]:.1f}% positive, %{customdata[3]:.2f} c net<br>'
                                           '%{customdata[0]:.1f}k observations per outcome, %{customdata[1]:.0f} fixtures<extra>' + d + '</extra>'),
                      r + 1, c + 1)
    for r, (_, col) in enumerate(rows):
        fig.update_yaxes(range=[0, 100] if col == 'pos_pct' else [-1.5, float(g.net_c.clip(upper=4).max()) * 1.1], row=r + 1)
    for c in range(1, 5):
        fig.update_xaxes(title_text='YES price, venue holding YES', tickangle=-50, tickfont_size=9, row=4, col=c)
    label_rows(fig, ['Team win', 'Team win', 'Draw', 'Draw'], '')
    for r, t in enumerate(['% positive after fees', 'mean net edge (c)', '% positive after fees', 'mean net edge (c)']):
        fig.update_yaxes(title_text=f"<b>{['Team win', 'Team win', 'Draw', 'Draw'][r]}</b><br>{t}", row=r + 1, col=1)
    data = g[['cell', 'sel', 'direction', 'price_bucket', 'n', 'n_k', 'fixtures', 'pos_pct', 'net_c', 'excluded']]
    return fig, data


def same_side_view(s):
    """§2.1: signed same-side gap PM − K, team-win ask side and draw bid side."""
    sg, labels, cents = s['sg'], s['CENT_LABELS'], list(s['gaps'].GAP_CENTS)
    rows = [('buy/buy', 'team win', 'Team win · ask side (buy/buy)'), ('sell/sell', 'draw', 'Draw · bid side (sell/sell)')]
    fig = grid(2, 4, CELL_TITLES, 640, shared_x=True, shared_y=True, vs=0.14)
    fig.update_layout(barmode='group')
    p = Panels(fig)
    out = []
    for r, (pair, sel, _) in enumerate(rows):
        for c, cl in enumerate(CELLS):
            d = sg.loc[(cl, pair, sel)].reindex(cents, fill_value=0)
            for weight, col, color in (('per print', 'n', '#5c6b7a'), ('per fresh second', 'time', '#c9a227')):
                share = 100 * d[col] / d[col].sum()
                p.add(go.Bar(x=labels, y=share.round(3).tolist(), name=weight, marker_color=color,
                             hovertemplate='%{x} c: %{y:.1f}%<extra>' + weight + '</extra>'), r + 1, c + 1)
                out += [dict(cell=cl, pair=pair, sel=sel, bucket=b, weighting=weight, share_pct=v) for b, v in zip(labels, share)]
    for c in range(1, 5):
        fig.update_xaxes(title_text='PM − Kalshi (c)', tickangle=-50, tickfont_size=9, row=2, col=c)
    data = pd.DataFrame(out)
    fig.update_yaxes(range=[0, float(data.share_pct.max()) * 1.08])
    for r, (_, _, name) in enumerate(rows):
        fig.update_yaxes(title_text=f'<b>{name}</b><br>% of fresh prints', row=r + 1, col=1)
    return fig, data


def offset_view(s):
    """§2.2: mean same-side gap PM − K by YES price, both sides, team win and draw rows."""
    pg, pb = s['pg'], s['PB']
    fig = grid(2, 4, CELL_TITLES, 640, shared_x=True, shared_y=True, vs=0.14)
    fig.update_layout(barmode='group')
    p = Panels(fig)
    for r, sel in enumerate(['team win', 'draw']):
        for c, cl in enumerate(CELLS):
            for pair, name, color in (('buy/buy', 'ask side (buy/buy)', '#5c6b7a'), ('sell/sell', 'bid side (sell/sell)', '#c9a227')):
                q = pg[(pg.cell == cl) & (pg.sel == sel) & (pg.pair == pair)].set_index('price_bucket').reindex(pb)
                thin = q.thin.fillna(True).astype(bool)
                p.add(go.Bar(x=pb, y=q.mean_gap_c.round(3).tolist(), name=name,
                             marker=dict(color=color, opacity=[.35 if t else 1 for t in thin], pattern=dict(shape=[HATCH if t else '' for t in thin])),
                             customdata=q.n_k.fillna(0).round(1).tolist(),
                             hovertemplate='%{x}: %{y:+.2f} c over %{customdata}k prints per outcome<extra>' + name + '</extra>'), r + 1, c + 1)
    for c in range(1, 5):
        fig.update_xaxes(title_text='YES price (midpoint)', tickangle=-50, tickfont_size=9, row=2, col=c)
    lim = float(pg[~pg.thin].mean_gap_c.abs().max()) * 1.15
    fig.update_yaxes(range=[-lim, lim])
    for r, name in enumerate(['Team win', 'Draw']):
        fig.update_yaxes(title_text=f'<b>{name}</b><br>mean PM − K (cents)', row=r + 1, col=1)
    return fig, pg[['cell', 'sel', 'pair', 'price_bucket', 'n', 'n_k', 'hi_pct', 'lo_pct', 'mean_gap_c', 'thin']]


def spread_view(s):
    """§3: mean net two-sided spread by price: fused, PM only, K only."""
    sp, pb = s['sp'], s['PB']
    series = {'fused': (BOTH, 'Fused: same prices on both venues'), 'pm': (PM, 'Polymarket only'), 'k': (K, 'Kalshi only')}
    fig = grid(2, 4, CELL_TITLES, 640, shared_x=True, shared_y=True, vs=0.14)
    fig.update_layout(barmode='group')
    p = Panels(fig)
    for r, sel in enumerate(['team win', 'draw']):
        for c, cl in enumerate(CELLS):
            for key, (color, name) in series.items():
                q = sp[(sp.cell == cl) & (sp.sel == sel) & (sp.series == key)].set_index('price_bucket').reindex(pb)
                thin = q.thin.fillna(True).astype(bool)
                p.add(go.Bar(x=pb, y=q.net_c.round(3).tolist(), name=name,
                             marker=dict(color=color, opacity=[.35 if t else 1 for t in thin], pattern=dict(shape=[HATCH if t else '' for t in thin])),
                             customdata=np.stack([q.n_k.fillna(0), q.pos_pct], axis=-1).round(2).tolist(),
                             hovertemplate='%{x}: %{y:.2f} c net, %{customdata[1]:.1f}% positive<br>%{customdata[0]}k observations per outcome<extra>' + name + '</extra>'),
                      r + 1, c + 1)
    for c in range(1, 5):
        fig.update_xaxes(title_text='YES price (midpoint)', tickangle=-50, tickfont_size=9, row=2, col=c)
    ok = sp[~sp.thin]
    fig.update_yaxes(range=[min(0, float(ok.net_c.min()) * 1.1), float(ok.net_c.max()) * 1.1])
    for r, name in enumerate(['Team win', 'Draw']):
        fig.update_yaxes(title_text=f'<b>{name}</b><br>mean net spread (cents)', row=r + 1, col=1)
    return fig, sp[['cell', 'sel', 'series', 'price_bucket', 'n', 'n_k', 'pos_pct', 'gross_c', 'net_c', 'thin']]


def pairing_view(s):
    """§4: net edge of the two pairings of a PM YES bid, paired observations."""
    h, bins, labels = s['h'], s['BINS'], s['BIN_LABELS']
    series = {'pm_only': (PM, 'PM YES bid + PM YES ask'), 'pm_yes_k_no': (K, 'PM YES bid + Kalshi NO bid')}
    fig = grid(1, 4, CELL_TITLES, 430, shared_y=True)
    fig.update_layout(barmode='group')
    p = Panels(fig)
    out = []
    for c, cl in enumerate(CELLS):
        for key, (color, name) in series.items():
            d = h.loc[(cl, key)].reindex(bins, fill_value=0)
            share = 100 * d / d.sum()
            p.add(go.Bar(x=labels, y=share.round(3).tolist(), name=name, marker_color=color,
                         hovertemplate='%{x} c: %{y:.1f}% of observations<extra>' + name + '</extra>'), 1, c + 1)
            out += [dict(cell=cl, series=key, net_bin=l, share_pct=v) for l, v in zip(labels, share)]
        fig.add_vline(x=bins.index(0) - .5, line_dash='dot', line_color='#8a929b', row=1, col=c + 1)
    fig.update_xaxes(title_text='net edge after fees (cents)', tickangle=-50)
    data = pd.DataFrame(out)
    fig.update_yaxes(range=[0, float(data.share_pct.max()) * 1.08])
    fig.update_yaxes(title_text='% of paired observations', row=1, col=1)
    return fig, data


def lead_lag_view(s):
    """§5: pooled Hayashi–Yoshida correlation by lag, one panel per group, fixture-bootstrap band."""
    res, lags = s['res'], s['LAGS']
    names = list(res)
    rows = int(np.ceil(len(names) / 4))
    titles = [f"{group_title(n)}<br>peak {res[n]['peak_lag']:+d} s".replace('-', '−') for n in names]
    fig = grid(rows, 4, titles, 330 * rows + 60, shared_x=True, shared_y=True, vs=0.12, legend=False)
    out = []
    for n_, name in enumerate(names):
        r, c = divmod(n_, 4)
        v = res[name]
        color = '#d64550' if name == WC else (POOLED if 'pooled' in name else BOTH)
        fig.add_trace(go.Scatter(x=lags.tolist(), y=np.round(v['hi'], 4).tolist(), mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'), r + 1, c + 1)
        fig.add_trace(go.Scatter(x=lags.tolist(), y=np.round(v['lo'], 4).tolist(), mode='lines', line=dict(width=0), fill='tonexty',
                                 fillcolor='rgba(139,92,246,.18)' if color == BOTH else ('rgba(214,69,80,.18)' if color == '#d64550' else 'rgba(125,135,145,.2)'),
                                 showlegend=False, hoverinfo='skip'), r + 1, c + 1)
        fig.add_trace(go.Scatter(x=lags.tolist(), y=np.round(v['rho'], 4).tolist(), mode='lines', line=dict(color=color, width=2), showlegend=False,
                                 hovertemplate='θ = %{x} s: ρ = %{y:.3f}<extra>' + group_title(name) + '</extra>'), r + 1, c + 1)
        fig.add_vline(x=0, line_color='#8a929b', line_width=1, row=r + 1, col=c + 1)
        out += [dict(group=name, lag=int(l), rho=a, band_lo=b, band_hi=d) for l, a, b, d in zip(lags, v['rho'], v['lo'], v['hi'])]
    fig.update_yaxes(range=[min(0, float(min(np.min(v['lo']) for v in res.values()))) - .02, float(max(np.max(v['hi']) for v in res.values())) * 1.08])
    for c in range(1, 5):
        fig.update_xaxes(title_text='lag θ (s); < 0: Kalshi first', row=rows, col=c)
    for r in range(1, rows + 1):
        fig.update_yaxes(title_text='HY correlation ρ(θ)', row=r, col=1)
    return fig, pd.DataFrame(out)


def waits_view(s):
    """§6: waiting from one resting order's fill to a trade on the other side, selected groups."""
    wg = s['wg']
    rows = [[('pm_bid -> pm_ask', PM, 'PM bid fill → PM ask trade'), ('pm_bid -> k_ask', K, 'PM bid fill → Kalshi ask trade'),
             ('pm_bid -> either_ask', BOTH, 'PM bid fill → either ask trades')],
            [('pm_ask -> pm_bid', PM, 'PM ask fill → PM bid trade'), ('k_ask -> pm_bid', K, 'Kalshi ask fill → PM bid trade')]]
    fig = grid(2, 4, [group_title(gp) for gp in WAIT_GROUPS], 700, shared_x=True, shared_y=True, vs=0.14)
    p = Panels(fig)
    for r, series in enumerate(rows):
        for c, gp in enumerate(WAIT_GROUPS):
            for pair, color, name in series:
                d = wg[(wg.group == gp) & (wg.pair == pair)].sort_values('horizon')
                p.add(go.Scatter(x=d.horizon.tolist(), y=d.follow_pct.round(2).tolist(), name=name, mode='lines', line=dict(color=color, width=2),
                                 hovertemplate='H = %{x} s: %{y:.1f}%<extra>' + name + '</extra>'), r + 1, c + 1)
    fig.update_xaxes(range=[0, 60])
    fig.update_yaxes(range=[0, 100])
    for c in range(1, 5):
        fig.update_xaxes(title_text='Forward horizon H (s)', row=2, col=c)
    fig.update_yaxes(title_text='<b>PM bid fills first</b><br>% followed within H', row=1, col=1)
    fig.update_yaxes(title_text='<b>The other order first</b><br>% followed within H', row=2, col=1)
    data = wg[wg.group.isin(WAIT_GROUPS)][['group', 'pair', 'horizon', 'eligible', 'followed', 'follow_pct']]
    return fig, data


def pnl_view(s):
    """§6 of the post (notebook §7): simulated P&L per fixture by queue share ρ and variant."""
    res7 = s['res7']
    rhos, variants = [1.0, 0.5, 0.25, 0.0], [(1, 1), (1, 0), (0, 1), (0, 0)]
    fig = grid(1, 2, ['Club competitions', 'World Cup 2026'], 480)
    fig.update_layout(barmode='group')
    p = Panels(fig)
    for c, gp in enumerate(['Clubs', 'World Cup']):
        d = res7[res7.group == gp].set_index(['rho', 'k_price', 'guard'])
        x = [f'ρ = {r:g}' for r in rhos]
        for kp, gd in variants:
            q = d.loc[[(r, kp, gd) for r in rhos]]
            name = f"{KP[kp]}, guard {'on' if gd else 'off'}"
            p.add(go.Bar(x=x, y=q.pnl_usd.round(2).tolist(), name=name,
                         marker=dict(color=GUARD_COLORS[gd], pattern=dict(shape='' if kp else HATCH)),
                         error_y=dict(type='data', symmetric=False, array=(q.ci_hi - q.pnl_usd).round(2).tolist(),
                                      arrayminus=(q.pnl_usd - q.ci_lo).round(2).tolist(), thickness=1, width=3),
                         customdata=np.stack([q.ci_lo, q.ci_hi, q.realized_usd, q.losing_fx_pct], axis=-1).round(2).tolist(),
                         hovertemplate='%{x}: $%{y:.2f} per fixture [%{customdata[0]:.2f}, %{customdata[1]:.2f}]<br>'
                                       'realized $%{customdata[2]:.2f}; %{customdata[3]:.0f}% of fixtures lose<extra>' + name + '</extra>'), 1, c + 1)
    fig.update_yaxes(title_text='P&L per fixture ($, 100 contracts, 95% CI)', row=1, col=1)
    fig.update_xaxes(title_text='queue share ρ (1 = back of the displayed queue)')
    cols = ['group', 'rho', 'k_price', 'guard', 'fixtures', 'pnl_usd', 'ci_lo', 'ci_hi', 'realized_usd', 'inventory_usd', 'sd_usd',
            'losing_fx_pct', 'p5_usd', 'double_fill_pct', 'pm_yes_k', 'pm_no_k', 'k_no_k', 'pair_median_s']
    return fig, res7[cols]


def markout_view(s):
    """Markouts per contract by order, club competitions, worst-case queue."""
    fl7, pid = s['fl7'], s['pid']
    fig = grid(1, 3, ['PM YES bid (pm_yes)', 'PM YES ask (pm_no)', 'Kalshi YES ask (k_no)'], 430, shared_y=True)
    p = Panels(fig)
    out = []
    for c, leg in enumerate(['pm_yes', 'pm_no', 'k_no']):
        for kp in (1, 0):
            for gd in (1, 0):
                f = fl7[(fl7.param == pid[(1.0, kp, gd)]) & (fl7.group == 'Clubs') & (fl7.leg == leg)]
                y = [f[f'mo_{hz}_x'].sum() / f.qty.sum() for hz in (0, 5, 30, 60)]
                name = f"{KP[kp]}, guard {'on' if gd else 'off'}"
                p.add(go.Scatter(x=[0, 5, 30, 60], y=np.round(y, 3).tolist(), name=name, mode='lines+markers',
                                 line=dict(color=GUARD_COLORS[gd], width=2, dash='solid' if kp else 'dot'), marker_size=6,
                                 hovertemplate='+%{x} s: %{y:.2f} c per contract<extra>' + name + '</extra>'), 1, c + 1)
                out += [dict(leg=leg, k_price=kp, guard=gd, horizon_s=hz, markout_c=v) for hz, v in zip((0, 5, 30, 60), y)]
        fig.add_hline(y=0, line_color='#8a929b', line_width=1, row=1, col=c + 1)
    fig.update_xaxes(title_text='seconds after the fill', tickvals=[0, 5, 30, 60])
    fig.update_yaxes(title_text='markout vs Kalshi mid (c / contract)', row=1, col=1)
    return fig, pd.DataFrame(out)


VIEWS = {3: [price_view], 6: [same_side_view], 9: [offset_view], 12: [spread_view], 15: [pairing_view],
         18: [lead_lag_view], 21: [waits_view], 24: [pnl_view, markout_view]}


def views(i, snaps):
    return [f(snaps[i]) for f in VIEWS.get(i, [])]


# --- quoted numbers ------------------------------------------------------------------------------

def key_numbers(snaps):
    k = {}
    # §1: maker/maker by price, outcome and direction
    s = snaps[3]; g = s['g'].set_index(['cell', 'sel', 'direction', 'price_bucket'])
    PL, UCL, WCI, WCP = CELLS

    def b(cell, sel, d, buckets, col):
        rows = g.loc[[(cell, sel, d, x) for x in buckets if (cell, sel, d, x) in g.index]]
        return rows[col]
    k['s1'] = {
        'pl_team_5060_1': c2(b(PL, 'team win', D1, ['50-60c'], 'net_c').iloc[0], 1), 'pl_team_5060_2': c2(b(PL, 'team win', D2, ['50-60c'], 'net_c').iloc[0], 1),
        'pl_draw_6070_1': c2(b(PL, 'draw', D1, ['60-70c'], 'net_c').iloc[0], 1), 'pl_draw_6070_2': c2(b(PL, 'draw', D2, ['60-70c'], 'net_c').iloc[0], 1),
        'fee_max': c2(100 * s['gaps'].kalshi_fee(0.5, s['CFG'].lot, s['CFG'].kalshi_maker_rate) / s['CFG'].lot),
    }
    mid = ['40-50c', '50-60c', '60-70c', '70-80c']
    both = lambda d, col: pd.concat([b(PL, 'team win', d, mid, col), b(WCI, 'team win', d, mid, col)])
    k['s1'].update({'team_mid_2_pos': rng(both(D2, 'pos_pct'), pct), 'team_mid_2_net': rng(both(D2, 'net_c'), lambda v: c2(v, 1)),
                    'team_mid_1_pos': rng(both(D1, 'pos_pct'), pct), 'team_mid_1_net': rng(both(D1, 'net_c'), lambda v: c2(v, 1))})
    low = ['0-10c', '10-20c', '20-30c']
    diff = [abs(b(cl, 'team win', D1, [x], 'net_c').iloc[0] - b(cl, 'team win', D2, [x], 'net_c').iloc[0]) for cl in CELLS for x in low]
    k['s1']['team_low_maxdiff'] = c2(max(diff), 1)
    k['s1']['pl_draw_low_2_net'] = rng(b(PL, 'draw', D2, ['0-10c', '10-20c'], 'net_c'), lambda v: c2(v, 1))
    k['s1']['pl_draw_low_2_pos'] = rng(b(PL, 'draw', D2, ['0-10c', '10-20c'], 'pos_pct'), pct)
    k['s1']['pl_draw_high_2_net'] = rng(b(PL, 'draw', D2, ['50-60c', '60-70c'], 'net_c'), lambda v: c2(v, 1))
    k['s1']['pl_draw_high_1_net'] = rng(b(PL, 'draw', D1, ['50-60c', '60-70c'], 'net_c'), lambda v: c2(v, 1))
    club_low = pd.concat([b(PL, 'draw', D2, ['0-10c', '10-20c'], col) for col in ('net_c',)] + [b(UCL, 'draw', D2, ['0-10c', '10-20c'], 'net_c')])
    club_low_pos = pd.concat([b(PL, 'draw', D2, ['0-10c', '10-20c'], 'pos_pct'), b(UCL, 'draw', D2, ['0-10c', '10-20c'], 'pos_pct')])
    k['s1'].update({'club_draw_low_net': rng(club_low, lambda v: c2(v, 1)), 'club_draw_low_pos': rng(club_low_pos, pct),
                    'pl_draw_low_2_n': f"{b(PL, 'draw', D2, ['0-10c', '10-20c'], 'n').sum() / 1000:.0f}k",
                    'pl_team_low_1_n': f"{b(PL, 'team win', D1, ['0-10c', '10-20c'], 'n_k').sum():.0f}k",
                    'wc_draw_2_net': rng(b(WCI, 'draw', D2, ['0-10c', '10-20c', '20-30c', '30-40c', '40-50c', '50-60c', '60-70c'], 'net_c'), lambda v: c2(v, 1)),
                    'wc_draw_1_net': rng(b(WCI, 'draw', D1, ['0-10c', '10-20c', '20-30c', '30-40c', '40-50c', '50-60c', '60-70c'], 'net_c'), lambda v: c2(v, 1))})
    tot = s['g'].groupby(['cell', 'sel', 'direction'])[['n']].sum().n
    k['s1']['pl_team_n_1'] = f"{tot[(PL, 'team win', D1)] / 2000:.0f}k"; k['s1']['pl_team_n_2'] = f"{tot[(PL, 'team win', D2)] / 2000:.0f}k"
    k['s1']['pl_draw_n_1'] = f"{tot[(PL, 'draw', D1)] / 1000:.0f}k"; k['s1']['pl_draw_n_2'] = f"{tot[(PL, 'draw', D2)] / 1000:.0f}k"
    # §2: same-side offsets
    st = snaps[6]['stats']
    tb, ds = st.loc[('buy/buy', 'team win')], st.loc[('sell/sell', 'draw')]
    k['s2'] = {'team_ask_below': rng(tb.one_tick_below_pct, pct), 'team_ask_above': rng(tb.one_tick_above_pct, pct),
               'team_ask_mean': rng(tb.mean_gap_c, lambda v: c2(v, 2, True)),
               'draw_bid_above': rng(ds.one_tick_above_pct, pct), 'draw_bid_below': rng(ds.one_tick_below_pct, pct),
               'draw_bid_mean': rng(ds.mean_gap_c, lambda v: c2(v, 2, True))}
    pg = snaps[9]['pg'].set_index(['cell', 'sel', 'pair', 'price_bucket'])
    pgv = lambda sel, pair, buckets: pg.loc[[(PL, sel, pair, x) for x in buckets]].mean_gap_c
    k['s2'].update({'pl_team_ask_low': rng(pgv('team win', 'buy/buy', low), lambda v: c2(v, 2, True)),
                    'pl_team_ask_high': rng(pgv('team win', 'buy/buy', ['40-50c', '50-60c', '60-70c', '70-80c', '80-90c']), lambda v: c2(v, 1, True)),
                    'pl_draw_bid_low': rng(pgv('draw', 'sell/sell', ['0-10c', '10-20c', '20-30c', '30-40c']), lambda v: c2(v, 1, True))})
    # §3: two-sided spread
    sp = snaps[12]['sp']
    t3 = sp.groupby(['cell', 'series'])[['n', 'net_sum', 'gross_sum']].sum()
    net3 = (100 * t3.net_sum / t3.n).unstack('series'); gross3 = (100 * t3.gross_sum / t3.n).unstack('series')
    k['s3'] = {'pm_club': rng(net3.loc[[PL, UCL], 'pm'], lambda v: c2(v, 1)), 'pm_wc': rng(net3.loc[[WCI, WCP], 'pm'], c2),
               'k_gross_club': rng(gross3.loc[[PL, UCL], 'k'], lambda v: c2(v, 1)), 'k_net_wc': c2(net3.loc[WCI, 'k']),
               'fused_pl': c2(net3.loc[PL, 'fused']), 'fused_wc': c2(net3.loc[WCI, 'fused'])}
    # §4: pairing a PM YES bid
    s4 = snaps[15]; pc, h = s4['pc'], s4['h']
    t4 = pc.groupby(['cell', 'series'])[['n', 'pos', 'net_sum']].sum()
    net4, pos4 = (100 * t4.net_sum / t4.n).unstack('series'), (100 * t4.pos / t4.n).unstack('series')
    share = lambda cl, key, bins: 100 * h.loc[(cl, key)].reindex(bins, fill_value=0).sum() / h.loc[(cl, key)].sum()
    k['s4'] = {'pl_pm': c2(net4.loc[PL, 'pm_only']), 'pl_k': c2(net4.loc[PL, 'pm_yes_k_no']), 'wc_pm': c2(net4.loc[WCI, 'pm_only']),
               'wc_k': c2(net4.loc[WCI, 'pm_yes_k_no']), 'pos_pm': rng(pos4.pm_only, pct), 'pos_k': rng(pos4.pm_yes_k_no, pct),
               'one_tick_pm': rng([share(cl, 'pm_only', [1]) for cl in CELLS], pct),
               'two_tick_k': rng([share(cl, 'pm_yes_k_no', [3]) for cl in CELLS], pct),
               'zero_tick_k': rng([share(cl, 'pm_yes_k_no', [-1]) for cl in CELLS], pct)}
    # §5: lead-lag
    res = snaps[18]['res']
    clubs = [n for n in res if n != WC and 'pooled' not in n]
    k['s5'] = {'wc_peak': f"{res[WC]['peak_lag']:+d}".replace('-', '−'), 'club_peak': rng([res[n]['peak_lag'] for n in clubs], lambda v: f'{v:+.0f}'.replace('-', '−'), ' to '),
               'pooled_peak': f"{res[CLUBS]['peak_lag']:+d}".replace('-', '−'),
               'pooled_lo': f"{res[CLUBS]['peak_lag_lo']:+.0f}".replace('-', '−'), 'pooled_hi': f"{res[CLUBS]['peak_lag_hi']:+.0f}".replace('-', '−'),
               'wc_rho_peak': c2(res[WC]['peak_rho']), 'wc_rho_0': c2(res[WC]['rho_0']), 'wc_llr': c2(res[WC]['llr']),
               'club_rho_peak': rng([res[n]['peak_rho'] for n in clubs], c2),
               'club_pm_every': rng([2 * 6300 / res[n]['pm_prints_per_fx'] for n in clubs], lambda v: f'{v:.0f}'),
               'wc_pm_every': f"{2 * 6300 / res[WC]['pm_prints_per_fx']:.1f}"}
    # §6 of the post (notebook §6): waiting
    wg, base = snaps[21]['wg'].set_index(['group', 'pair', 'horizon']).follow_pct, snaps[21]['base']
    w = lambda gp, pair, H: pct(wg[(gp, pair, H)])
    k['s6'] = {f'{tag}_{d}_{H}': w(gp, f'{src} -> {d}', H) for tag, gp in (('pl', 'Premier League 2025/26'), ('clubs', CLUBS), ('wc', WC))
               for src, d in (('pm_bid', 'pm_ask'), ('pm_bid', 'k_ask'), ('pm_bid', 'either_ask')) for H in (5, 10, 60)}
    k['s6'].update({f'{tag}_{src}_first_10': w(gp, f'{src} -> pm_bid', 10) for tag, gp in (('pl', 'Premier League 2025/26'), ('clubs', CLUBS), ('wc', WC))
                    for src in ('pm_ask', 'k_ask')})
    k['s6'].update({'clubs_same_either': pct(base.loc[(CLUBS, 'pm_bid -> either_ask'), 'same_second_pct']),
                    'clubs_same_k': pct(base.loc[(CLUBS, 'pm_bid -> k_ask'), 'same_second_pct']),
                    'clubs_k_fills_m': f"{base.loc[(CLUBS, 'k_ask -> pm_bid'), 'triggers'] / 1e6:.2f}",
                    'clubs_pmbid_fills_m': f"{base.loc[(CLUBS, 'pm_bid -> k_ask'), 'triggers'] / 1e6:.2f}"})
    # notebook §7: replay simulation
    s7 = snaps[24]; r7 = s7['res7'].set_index(['group', 'rho', 'k_price', 'guard'])
    best = r7.loc[('Clubs', 1.0, 1, 1)]
    k['s7'] = {'best': usd(best.pnl_usd), 'best_lo': usd(best.ci_lo), 'best_hi': usd(best.ci_hi), 'best_real': usd(best.realized_usd),
               'best_inv': usd(best.inventory_usd), 'best_sd': usd(best.sd_usd, 0), 'best_lose': pct(best.losing_fx_pct),
               'best_p5': usd(best.p5_usd, 0), 'best_n': f'{int(best.fixtures_for_ci)}', 'best_pair_s': f'{best.pair_median_s:.0f}',
               'best_qnz': pct(best.q_nonzero_pct), 'best_double': pct(best.double_fill_pct),
               'worst': usd(r7.loc[('Clubs', 1.0, 0, 0)].pnl_usd), 'rho25_best': usd(r7.loc[('Clubs', 0.25, 1, 1)].pnl_usd),
               'rho25_n': f"{int(r7.loc[('Clubs', 0.25, 1, 1)].fixtures_for_ci)}", 'rho0_best': usd(r7.loc[('Clubs', 0.0, 1, 1)].pnl_usd, 0),
               'club_rho1': rng([r7.loc[('Clubs', 1.0, kp, gd)].pnl_usd for kp in (0, 1) for gd in (0, 1)], usd),
               'wc': rng(r7.loc['World Cup'].pnl_usd, lambda v: usd(v, 0)),
               'fixtures_clubs': f"{int(best.fixtures):,}", 'fixtures_wc': f"{int(r7.loc[('World Cup', 1.0, 1, 1)].fixtures):,}"}
    adv = {r: [r7.loc[('Clubs', r, 1, gd)].pnl_usd - r7.loc[('Clubs', r, 0, gd)].pnl_usd for gd in (0, 1)] for r in (1.0, 0.5, 0.25, 0.0)}
    k['s7'].update({'kask_adv_1': rng(adv[1.0], lambda v: usd(v, 0)), 'kask_adv_mid': rng(adv[0.5] + adv[0.25], lambda v: usd(v, 0)),
                    'kask_adv_0': rng(adv[0.0], lambda v: usd(v, 0))})
    guard = [r7.loc[('Clubs', r, kp, 1)].pnl_usd - r7.loc[('Clubs', r, kp, 0)].pnl_usd for r in (1.0, 0.5, 0.25) for kp in (0, 1)]
    k['s7']['guard_gain'] = rng(guard, usd)
    k['s7']['guard_wc_all_negative'] = all(r7.loc[('World Cup', r, kp, 1)].pnl_usd < r7.loc[('World Cup', r, kp, 0)].pnl_usd
                                           for r in (1.0, 0.5, 0.25, 0.0) for kp in (0, 1))
    k['s7'].update({'mo_bid_off': rng([r7.loc[('Clubs', 1.0, kp, 0)].pm_yes_mo0_c for kp in (0, 1)], lambda v: c2(v, 1)),
                    'mo_bid_on': rng([r7.loc[('Clubs', 1.0, kp, 1)].pm_yes_mo0_c for kp in (0, 1)], lambda v: c2(v, 1)),
                    'mo_k_pmask': rng([r7.loc[('Clubs', 1.0, 0, gd)].k_no_mo60_c for gd in (0, 1)], lambda v: c2(v, 2, True)),
                    'mo_k_kask': rng([r7.loc[('Clubs', 1.0, 1, gd)].k_no_mo60_c for gd in (0, 1)], lambda v: c2(v, 2, True)),
                    'double_off': pct(r7.loc[('Clubs', 1.0, 1, 0)].double_fill_pct), 'double_on': pct(r7.loc[('Clubs', 1.0, 1, 1)].double_fill_pct),
                    'thru_pm': rng([r7.loc[('Clubs', 1.0, kp, gd)][f'{leg}_through_pct'] for kp in (0, 1) for gd in (0, 1) for leg in ('pm_yes', 'pm_no')], pct),
                    'thru_k': rng([r7.loc[('Clubs', 1.0, 1, gd)].k_no_through_pct for gd in (0, 1)], pct)})
    ft = s7['fl7']
    imp = ft[(ft.group == 'Clubs') & ft.param.isin([s7['pid'][(1.0, 0, gd)] for gd in (0, 1)]) & (ft.leg == 'k_no')]
    k['s7']['improved_share'] = pct(100 * imp.qty[imp.fill_type == 'improved'].sum() / imp.qty.sum())
    cp = s7['cp']['mean'].unstack('param')[s7['pid'][(1.0, 1, 1)]]
    k['s7']['by_league'] = ', '.join(f'{competition(lg)} {usd(v)}' for lg, v in cp.drop('World Cup').sort_values(ascending=False).items())
    k['s7']['weakest'] = competition(cp.drop('World Cup').idxmin())
    return k


# --- tables ------------------------------------------------------------------------------------

def html(df):
    return df.to_html(index=False, border=0, classes='table table-sm', escape=False)


def lead_lag_table(snaps):
    res = snaps[18]['res']
    rows = []
    for name, v in res.items():
        rows.append({'Group': group_title(name), 'Fixtures': f"{v['fixtures']:,}",
                     'PM bid prints per outcome': f"{v['pm_prints_per_fx'] / 2:,.0f}",
                     'Peak lag θ': f"{v['peak_lag']:+d} s".replace('-', '−'),
                     '95% interval': f"[{v['peak_lag_lo']:+.0f}, {v['peak_lag_hi']:+.0f}] s".replace('-', '−'),
                     'Peak ρ': f"{v['peak_rho']:.2f}", 'ρ at θ = 0': f"{v['rho_0']:.2f}"})
    return html(pd.DataFrame(rows))


def pnl_table(snaps):
    r7 = snaps[24]['res7']
    d = r7[r7.group == 'Clubs'].set_index(['rho', 'k_price', 'guard'])
    rows = []
    for r in (1.0, 0.5, 0.25, 0.0):
        row = {'Queue share ρ': f'{r:g}'}
        for kp, gd in ((1, 1), (1, 0), (0, 1), (0, 0)):
            q = d.loc[(r, kp, gd)]
            row[f"{KP[kp]}, guard {'on' if gd else 'off'}"] = f'{usd(q.pnl_usd)} [{usd(q.ci_lo)}, {usd(q.ci_hi)}]'
        rows.append(row)
    return html(pd.DataFrame(rows))


def worst_case_table(snaps):
    r7 = snaps[24]['res7']
    d = r7[(r7.group == 'Clubs') & (r7.rho == 1.0)].set_index(['k_price', 'guard'])
    rows = []
    for kp, gd in ((1, 1), (1, 0), (0, 1), (0, 0)):
        q = d.loc[(kp, gd)]
        rows.append({'Variant': f"{KP[kp]}, guard {'on' if gd else 'off'}", 'P&L per fixture': usd(q.pnl_usd),
                     'Realized / inventory': f'{usd(q.realized_usd)} / {usd(q.inventory_usd)}',
                     'Contracts filled per fixture (bid / PM ask / Kalshi ask)': f'{q.pm_yes_k * 1000:,.0f} / {q.pm_no_k * 1000:,.0f} / {q.k_no_k * 1000:,.0f}',
                     'Fixtures losing': pct(q.losing_fx_pct), 'SD per fixture': usd(q.sd_usd, 0),
                     'Double fills (fixtures)': pct(q.double_fill_pct), 'Median pair time': f'{q.pair_median_s:.0f} s'})
    return html(pd.DataFrame(rows))


def league_table(snaps):
    s7 = snaps[24]
    cp, pid = s7['cp'], s7['pid']
    mean, size = cp['mean'].unstack('param'), cp['size'].unstack('param')
    rows = []
    for lg in sorted(mean.index, key=lambda x: (x == 'World Cup', x)):   # clubs alphabetically, then the World Cup
        row = {'Competition': competition(lg), 'Fixtures': f'{int(size.loc[lg].iloc[0]):,}'}
        for kp, gd in ((1, 1), (1, 0), (0, 1), (0, 0)):
            row[f"{KP[kp]}, guard {'on' if gd else 'off'}"] = usd(mean.loc[lg, pid[(1.0, kp, gd)]])
        rows.append(row)
    return html(pd.DataFrame(rows))


def tables(snaps):
    return {'lead_lag_table': lead_lag_table(snaps), 'pnl_table': pnl_table(snaps), 'worst_case_table': worst_case_table(snaps),
            'league_table': league_table(snaps)}
