"""Part 4 of the series: Plotly views, quoted numbers and tables from notebook 02.2.1 §7.1–7.6 (sizing a first test).

Like part3.py, each view reads the notebook namespace as it stood right after the cell it shows.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from charts import BOTH, K, PM, Panels, grid
from part3 import c2, html, pct, rng, usd

BEST = 'K at K ask, guard on'                 # notebook label: Kalshi order at Kalshi's ask, guard on
VARIANTS = ['K at K ask, guard on', 'K at K ask, guard off', 'K at PM ask, guard on', 'K at PM ask, guard off']
SIZES = [100, 50, 20, 15, 10]
CAP = 'cap $200 / $300'
SETUP_COLORS = {'three orders': BOTH, 'PM bid + Kalshi ask': K, 'PM bid + PM ask': PM}
RHO_COLORS = {1.0: '#5c6b7a', 0.25: '#e8a33d'}
ROLE_COLORS = {'strong': '#d64550', 'weak': '#5c6b7a'}
COMBOS = [(1.0, 0), (1.0, 1), (0.25, 0), (0.25, 1)]


def combo_label(r, gd):
    return f"ρ = {r:g} · guard {'on' if gd else 'off'}"


def n_for_ci(mean, sd):
    """Fixtures until a 95% interval on the mean excludes zero, if the replay is right."""
    return int(np.ceil((1.96 * sd / mean) ** 2)) if mean > 0 else None


def bars_ci(d, x, name, color, pattern=''):
    return go.Bar(x=x, y=d.pnl_usd.round(2).tolist(), name=name, marker=dict(color=color, pattern=dict(shape=pattern)),
                  error_y=dict(type='data', symmetric=False, array=(d.ci_hi - d.pnl_usd).round(2).tolist(),
                               arrayminus=(d.pnl_usd - d.ci_lo).round(2).tolist(), thickness=1, width=3),
                  customdata=np.stack([d.ci_lo, d.ci_hi, d.realized_usd, d.losing_fx_pct], axis=-1).round(2).tolist(),
                  hovertemplate='%{x}: $%{y:.2f} per fixture [%{customdata[0]:.2f}, %{customdata[1]:.2f}]<br>'
                                'realized $%{customdata[2]:.2f}; %{customdata[3]:.0f}% of fixtures lose<extra>' + name + '</extra>')


def fill_quintiles(oc6):
    d = oc6['no cap'][oc6['no cap'].role != 'unlabelled'].copy()
    d['fill quintile'] = pd.qcut(d.fills.rank(method='first'), 5, labels=['F1 low', 'F2', 'F3', 'F4', 'F5 high'])
    return d.groupby(['fill quintile', 'role'], observed=True).agg(
        n=('value', 'size'), mean_fills=('fills', 'mean'), mean_usd=('value', 'mean'),
        losing_pct=('value', lambda v: 100 * (v < 0).mean())).reset_index()


# --- views ------------------------------------------------------------------------------------

def orders_view(s):
    """§7.1: three orders against either pair, by queue share and guard."""
    resl = s['resl']
    fig = grid(1, 2, [f'Club competitions ({int(resl[resl.group == "Clubs"].fixtures.iloc[0]):,} fixtures)',
                      f'World Cup 2026 ({int(resl[resl.group == "World Cup"].fixtures.iloc[0])} fixtures)'], 470)
    fig.update_layout(barmode='group')
    p = Panels(fig)
    x = [combo_label(*c) for c in COMBOS]
    for c, gp in enumerate(['Clubs', 'World Cup']):
        d = resl[resl.group == gp].set_index(['setup', 'rho', 'guard'])
        for setup, color in SETUP_COLORS.items():
            p.add(bars_ci(d.loc[[(setup, r, gd) for r, gd in COMBOS]], x, setup, color), 1, c + 1)
    fig.update_yaxes(title_text='P&L per fixture ($, L = 100, 95% CI)', row=1, col=1)
    cols = ['group', 'setup', 'rho', 'guard', 'fixtures', 'pnl_usd', 'ci_lo', 'ci_hi', 'realized_usd', 'inventory_usd', 'pm_yes_k', 'exit_k',
            'pm_yes_mo0_c', 'pair_median_s', 'double_fill_pct', 'losing_fx_pct', 'p5_usd', 'sd_usd', 'fixtures_for_ci']
    return fig, resl[cols]


def buffer_view(s):
    """§7.2: P&L per fixture by guard buffer."""
    resb, order = s['resb'], s['ORDER_B']
    fig = grid(1, 2, ['Club competitions', 'World Cup 2026'], 450)
    fig.update_layout(barmode='group')
    p = Panels(fig)
    for c, gp in enumerate(['Clubs', 'World Cup']):
        for r, color in RHO_COLORS.items():
            d = resb[(resb.group == gp) & (resb.rho == r)].set_index('guard_label').reindex(order)
            p.add(bars_ci(d, order, f'ρ = {r:g}', color), 1, c + 1)
    fig.update_xaxes(title_text='guard: off, or on with a buffer of 0–3 ticks of 1 c')
    fig.update_yaxes(title_text='P&L per fixture ($, L = 100, 95% CI)', row=1, col=1)
    cols = ['group', 'rho', 'guard_label', 'fixtures', 'pnl_usd', 'ci_lo', 'ci_hi', 'guard_pulls', 'pm_yes_k', 'pm_yes_mo0_c',
            'double_fill_pct', 'losing_fx_pct', 'p5_usd', 'sd_usd']
    return fig, resb[cols]


def size_view(s):
    """§7.3: P&L, P&L per contract of L and cash needed (95th percentile) by order size, best club variant."""
    sz, cap7 = s['sz'].sort_index().loc[('Clubs', BEST)].reindex(SIZES), s['cap7'].sort_index().loc[('Clubs', BEST)].reindex(SIZES)
    x = [f'L = {L}' for L in SIZES]
    fig = grid(1, 3, ['P&L per fixture ($, 95% CI)', 'P&L per contract of L ($)', 'Cash needed per fixture, 95th percentile ($)'], 430,
               hs=0.07)
    fig.update_layout(barmode='group')
    p = Panels(fig)
    ci = sz['95% CI'].str.strip('[]').str.split(', ', expand=True).astype(float)
    pnl = sz['P&L ($)']
    p.add(go.Bar(x=x, y=pnl.round(2).tolist(), name='P&L per fixture', marker_color=BOTH,
                 error_y=dict(type='data', symmetric=False, array=(ci[1] - pnl).round(2).tolist(), arrayminus=(pnl - ci[0]).round(2).tolist(),
                              thickness=1, width=3),
                 hovertemplate='%{x}: $%{y:.2f} per fixture<extra></extra>', showlegend=False), 1, 1)
    p.add(go.Bar(x=x, y=sz['per contract of L'].round(3).tolist(), name='per contract of L', marker_color='#5c6b7a',
                 hovertemplate='%{x}: $%{y:.3f} per contract of L<extra></extra>'), 1, 2)
    for venue, color in (('Polymarket', PM), ('Kalshi', K)):
        p.add(go.Bar(x=x, y=cap7[f'{venue} p95'].round(0).tolist(), name=f'{venue} cash', marker_color=color,
                     hovertemplate='%{x}: $%{y:,.0f}<extra>' + venue + ', 95th percentile</extra>'), 1, 3)
    fig.data[0].showlegend = fig.data[1].showlegend = False
    data = sz.join(cap7).reset_index()
    return fig, data.drop(columns=['worst fixture'])


def cap_view(s):
    """§7.4: P&L per fixture, club competitions, L = 10, without and with the cash cap."""
    dist = s['dist4']
    a, b = dist[('no cap', 'Clubs')], dist[(CAP, 'Clubs')]
    edges = np.arange(np.floor(min(a.min(), b.min()) * 2) / 2, 25.51, 0.5)
    fig = grid(1, 1, [''], 430)
    p = Panels(fig)
    out = []
    for v, name, color, width in ((a, 'no cap', '#8b97a3', 3), (b, 'cap $200 Polymarket / $300 Kalshi', '#e8a33d', 1.6)):
        # right-closed bins, so fixtures at exactly $0 sit in (−0.5, 0] like the near-zero band quoted in §5
        counts = pd.cut(v.clip(upper=25.25), edges, right=True, include_lowest=True).value_counts(sort=False).to_numpy()
        mids = (edges[:-1] + .25).round(2)
        p.add(go.Scatter(x=mids.tolist(), y=counts.tolist(), name=f'{name}: mean {usd(v.mean(), 2)}, median {usd(v.median(), 2)}',
                         mode='lines', line=dict(color=color, width=width, shape='hvh'),
                         hovertemplate='$%{x:.2f} ± 0.25: %{y} fixtures<extra>' + name + '</extra>'), 1, 1)
        out += [dict(run=name, bin_mid_usd=m, fixtures=int(n)) for m, n in zip(mids, counts)]
    fig.add_vline(x=0, line_color='#8a929b', line_width=1)
    fig.update_xaxes(title_text='P&L per fixture ($), both team-win outcomes; $0.50 bins, fixtures above $25 in the last bin', range=[edges[0], 25.5])
    fig.update_yaxes(title_text='fixtures')
    return fig, pd.DataFrame(out)


def drivers_view(s):
    """§7.5: edge and inventory by taker-volume quintile; P&L of jump seconds by position and move."""
    drv, jmp = s['drv'], s['jmp']
    fig = grid(1, 2, ['By taker-volume quintile (mean per fixture)', 'Jump seconds with a position (all club fixtures)'], 450, hs=0.1)
    fig.update_layout(barmode='relative')
    p = Panels(fig)
    q = drv.groupby('volume quintile', observed=True)[['pnl', 'edge', 'inv']].mean()
    x = [str(i) for i in q.index]
    p.add(go.Bar(x=x, y=q.edge.round(2).tolist(), name='edge (spread captured)', marker_color=BOTH,
                 hovertemplate='%{x}: edge $%{y:.2f}<extra></extra>'), 1, 1)
    p.add(go.Bar(x=x, y=q.inv.round(2).tolist(), name='inventory', marker_color='#d64550',
                 hovertemplate='%{x}: inventory $%{y:.2f}<extra></extra>'), 1, 1)
    p.add(go.Scatter(x=x, y=q.pnl.round(2).tolist(), name='P&L', mode='markers', marker=dict(color='#e8a33d', symbol='diamond', size=11),
                     hovertemplate='%{x}: P&L $%{y:.2f}<extra></extra>'), 1, 1)
    order = ['short YES, price up', 'long YES, price down', 'long YES, price up', 'short YES, price down']
    j = jmp.groupby('position and move').pnl.sum().reindex(order)
    p.add(go.Bar(x=[o.replace(', ', '<br>') for o in order], y=j.round(0).tolist(), name='jump-second P&L',
                 marker_color='#8b97a3', hovertemplate='%{x}: $%{y:,.0f}<extra></extra>'), 1, 2)
    fig.data[-1].showlegend = False
    fig.update_xaxes(title_text='taker volume on both venues, quintiles', row=1, col=1)
    fig.update_yaxes(title_text='$ per fixture (L = 10)', row=1, col=1)
    fig.update_yaxes(title_text='$ over 996 club fixtures', row=1, col=2)
    data = pd.concat([q.reset_index().assign(panel='volume quintile'),
                      j.rename('pnl').reset_index().rename(columns={'position and move': 'volume quintile'}).assign(panel='jump seconds')])
    return fig, data.rename(columns={'volume quintile': 'category'})


def strength_view(s):
    """§7.6: P&L per outcome by fill quintile, strong against weak team."""
    fq = fill_quintiles(s['oc6'])
    fig = grid(1, 2, ['Mean P&L per outcome ($)', '% of outcomes losing'], 420, hs=0.08)
    fig.update_layout(barmode='group')
    p = Panels(fig)
    for role, color in ROLE_COLORS.items():
        d = fq[fq.role == role]
        x = [f'{q}<br>~{m:,.0f} fills' for q, m in zip(d['fill quintile'].astype(str), fq.groupby('fill quintile', observed=True).mean_fills.mean())]
        name = f'{role} team'
        p.add(go.Bar(x=x, y=d.mean_usd.round(2).tolist(), name=name, marker_color=color,
                     hovertemplate='%{x}: $%{y:.2f}<extra>' + name + '</extra>'), 1, 1)
        p.add(go.Bar(x=x, y=d.losing_pct.round(1).tolist(), name=name, marker_color=color,
                     hovertemplate='%{x}: %{y:.0f}% losing<extra>' + name + '</extra>'), 1, 2)
    fig.update_xaxes(title_text='contracts filled per outcome, quintiles')
    return fig, fq


VIEWS = {27: [orders_view], 30: [buffer_view], 33: [size_view], 36: [cap_view], 39: [drivers_view], 42: [strength_view]}


def views(i, snaps):
    return [f(snaps[i]) for f in VIEWS.get(i, [])]


# --- quoted numbers ------------------------------------------------------------------------------

def key_numbers(snaps):
    k = {}
    # §7.1 which orders
    r = snaps[27]['resl'].set_index(['group', 'setup', 'rho', 'guard'])
    v = lambda setup, rho, gd, col='pnl_usd', gp='Clubs': r.loc[(gp, setup, rho, gd), col]
    drop = [v('three orders', rho, gd) - v(pair, rho, gd) for rho, gd in COMBOS for pair in ('PM bid + Kalshi ask', 'PM bid + PM ask')]
    lift = [v('three orders', rho, 1) / v('PM bid + PM ask', rho, 0) - 1 for rho in (1.0, 0.25)]
    k['o'] = {'three_1': usd(v('three orders', 1.0, 1)), 'three_25': usd(v('three orders', 0.25, 1)),
              'pmk_1': usd(v('PM bid + Kalshi ask', 1.0, 1)), 'pmpm_1': usd(v('PM bid + PM ask', 1.0, 1)),
              'drop': rng(drop, lambda x: usd(x, 0)),
              'plain_1': usd(v('PM bid + PM ask', 1.0, 0)), 'plain_25': usd(v('PM bid + PM ask', 0.25, 0)),
              'plain_guard_1': usd(v('PM bid + PM ask', 1.0, 1)), 'plain_guard_25': usd(v('PM bid + PM ask', 0.25, 1)),
              'lift': rng([100 * x for x in lift], pct),
              'double': pct(v('three orders', 1.0, 1, 'double_fill_pct')),
              'losing': rng([v(st, 1.0, 1, 'losing_fx_pct') for st in SETUP_COLORS], pct),
              'p5_three': usd(v('three orders', 1.0, 1, 'p5_usd'), 0), 'p5_pmk': usd(v('PM bid + Kalshi ask', 1.0, 1, 'p5_usd'), 0),
              'p5_pmpm': usd(v('PM bid + PM ask', 1.0, 1, 'p5_usd'), 0),
              'pmk_inv_off': rng([v('PM bid + Kalshi ask', rho, 0, 'inventory_usd') for rho in (1.0, 0.25)], usd),
              'pmk_n': f"{int(v('PM bid + Kalshi ask', 1.0, 1, 'fixtures_for_ci'))}", 'three_n': f"{int(v('three orders', 1.0, 1, 'fixtures_for_ci'))}",
              'pmpm_sd': rng([v('PM bid + PM ask', rho, gd, 'sd_usd') for rho, gd in COMBOS], lambda x: usd(x, 0)),
              'pmpm_n25': f"{int(v('PM bid + PM ask', 0.25, 1, 'fixtures_for_ci'))}",
              'pmpm_pair': f"{v('PM bid + PM ask', 1.0, 1, 'pair_median_s'):.0f}", 'three_pair': f"{v('three orders', 1.0, 1, 'pair_median_s'):.0f}",
              'wc_pmpm_1': usd(v('PM bid + PM ask', 1.0, 0, gp='World Cup')), 'wc_three_1': usd(v('three orders', 1.0, 0, gp='World Cup')),
              'wc_pmpm_25': usd(v('PM bid + PM ask', 0.25, 0, gp='World Cup')), 'wc_three_25': usd(v('three orders', 0.25, 0, gp='World Cup'))}
    # §7.2 guard buffer
    b = snaps[30]['resb'].set_index(['group', 'rho', 'guard_label'])
    w = lambda lab, col, rho=1.0, gp='Clubs': b.loc[(gp, rho, lab), col]
    bufs = ['buffer 0', 'buffer 1', 'buffer 2', 'buffer 3']
    k['g'] = {'pulls': ', '.join(f"{w(x, 'guard_pulls'):.0f}" for x in bufs),
              'pulls_cut': pct(100 * (1 - w('buffer 1', 'guard_pulls') / w('buffer 0', 'guard_pulls'))),
              'bid_k_0': f"{w('buffer 0', 'pm_yes_k'):.2f}k", 'bid_k_3': f"{w('buffer 3', 'pm_yes_k'):.2f}k",
              'mo': ', '.join(c2(w(x, 'pm_yes_mo0_c')) for x in bufs),
              'double_0': pct(w('buffer 0', 'double_fill_pct')), 'double_123': rng([w(x, 'double_fill_pct') for x in bufs[1:]], pct),
              'club_spread': rng([w(x, 'pnl_usd', rho) for x in bufs for rho in (1.0, 0.25)], usd),
              'b1_1': usd(w('buffer 1', 'pnl_usd')), 'b0_1': usd(w('buffer 0', 'pnl_usd')),
              'wc_off_1': usd(w('guard off', 'pnl_usd', gp='World Cup')), 'wc_b0_1': usd(w('buffer 0', 'pnl_usd', gp='World Cup')),
              'wc_b1_1': usd(w('buffer 1', 'pnl_usd', gp='World Cup')),
              'wc_b23': rng([w(x, 'pnl_usd', rho, 'World Cup') for x in bufs[2:] for rho in (1.0,)], usd),
              'wc_cost': rng([w('guard off', 'pnl_usd', rho, 'World Cup') - w('buffer 0', 'pnl_usd', rho, 'World Cup') for rho in (1.0, 0.25)],
                             lambda x: usd(x, 0))}
    # §7.3 order size
    sz, cap7 = snaps[33]['sz'].sort_index().loc['Clubs'], snaps[33]['cap7'].sort_index().loc['Clubs']
    z = lambda L, col, var=BEST: sz.loc[(var, L), col]
    zc = lambda L, col, var=BEST: cap7.loc[(var, L), col]
    k['l'] = {'keep50': pct(100 * z(50, 'P&L ($)') / z(100, 'P&L ($)')), 'p50': usd(z(50, 'P&L ($)')), 'p100': usd(z(100, 'P&L ($)')),
              'fills_ratio': pct(100 * sum(z(50, c) for c in ('bid fills', 'PM ask fills', 'K ask fills')) /
                                 sum(z(100, c) for c in ('bid fills', 'PM ask fills', 'K ask fills'))),
              'pc100': f"{z(100, 'per contract of L'):.2f}", 'pc50': f"{z(50, 'per contract of L'):.2f}", 'pc10': f"{z(10, 'per contract of L'):.2f}",
              'sd100': usd(z(100, 'SD ($)'), 0), 'sd50': usd(z(50, 'SD ($)'), 0), 'sd10': usd(z(10, 'SD ($)')),
              'ms100': f"{z(100, 'mean / SD'):.2f}", 'ms10': f"{z(10, 'mean / SD'):.2f}",
              'worst100': usd(z(100, 'max loss ($)'), 0), 'worst10': usd(z(10, 'max loss ($)'), 0),
              'p10': usd(z(10, 'P&L ($)'), 2), 'lose10': pct(z(10, 'losing %')),
              'cash_med100': rng([zc(100, 'Polymarket median'), zc(100, 'Kalshi median')], lambda x: usd(x, 0)),
              'cash_max100': f"${zc(100, 'both max'):,.0f}",
              'cash_ratio50': rng([100 * zc(50, f'{v_} p95') / zc(100, f'{v_} p95') for v_ in ('Polymarket', 'Kalshi')], pct),
              'n100': f"{n_for_ci(z(100, 'P&L ($)'), z(100, 'SD ($)'))}", 'n10': f"{n_for_ci(z(10, 'P&L ($)'), z(10, 'SD ($)'))}",
              'pm_p95_10': usd(zc(10, 'Polymarket p95'), 0), 'k_p95_10': usd(zc(10, 'Kalshi p95'), 0)}
    # §7.4 cash cap
    c4 = snaps[36]['cap4'].sort_index().loc['Clubs']
    cut = {var: 100 * (1 - c4.loc[(var, CAP), 'P&L ($)'] / c4.loc[(var, 'no cap'), 'P&L ($)']) for var in VARIANTS}
    wc4 = snaps[36]['cap4'].sort_index().loc['World Cup']
    bind = {x['variant']: x for x in snaps[36]['bind']}[BEST]
    qt = snaps[36]['qt']
    a = snaps[36]['dist4'][('no cap', 'Clubs')]
    k['c'] = {'cut_best': pct(cut[BEST]), 'cut_others': rng([cut[x] for x in VARIANTS[1:]], pct),
              'nocap': usd(c4.loc[(BEST, 'no cap'), 'P&L ($)'], 2), 'capped': usd(c4.loc[(BEST, CAP), 'P&L ($)'], 2),
              'over': f"{bind['fixtures over the cap']}", 'of': f"{bind['of fixtures']:,}", 'share': pct(bind['their share of total P&L, no cap (%)']),
              'over_pct': pct(100 * bind['fixtures over the cap'] / bind['of fixtures']),
              'n_cap': f"{n_for_ci(c4.loc[(BEST, CAP), 'P&L ($)'], c4.loc[(BEST, CAP), 'SD ($)'])}",
              'over_nocap': usd(bind['their mean P&L, no cap ($)']), 'over_cap': usd(bind['their mean P&L, capped ($)']),
              'maxq': f"{int(c4.loc[(BEST, CAP), 'max |q|'])}",
              'wc_cut': rng([100 * (1 - wc4.loc[(x, CAP), 'P&L ($)'] / wc4.loc[(x, 'no cap'), 'P&L ($)']) for x in VARIANTS], pct),
              'median': usd(qt.loc['median', 'Clubs · no cap'], 2), 'mean': usd(a.mean(), 2),
              'p95': usd(qt.loc['p95', 'Clubs · no cap']), 'p99': usd(qt.loc['p99', 'Clubs · no cap']),
              'p95_cap': usd(qt.loc['p95', f'Clubs · {CAP}']), 'p99_cap': usd(qt.loc['p99', f'Clubs · {CAP}']),
              'p5': usd(qt.loc['p5', 'Clubs · no cap']), 'min': usd(qt.loc['min', 'Clubs · no cap']),
              'top10': pct(100 * a.nlargest(len(a) // 10).sum() / a.sum())}
    # §7.5 drivers
    drv, jmp, s39 = snaps[39]['drv'], snaps[39]['jmp'], snaps[39]
    near = {x['P&L band ($)']: x for x in s39['near']}
    dec = {x['fixtures']: x for x in s39['dec']}
    corr = drv[['fills', 'quoted_s', 'k_vol', 'pm_vol', 'pm_depth', 'k_depth', 'pnl']].corr(method='spearman').pnl
    vq = drv.groupby('volume quintile', observed=True)[['pnl', 'edge', 'inv']].mean()
    dp = drv.pivot_table(index='volume quintile', columns='depth tercile', values='pnl', aggfunc='mean', observed=True)
    jp = jmp.groupby('position and move').pnl.sum()
    jl = jmp[jmp.pnl < 0].groupby(['position and move', 'filled in the 10 s before']).pnl.sum()
    k['d'] = {'flat_n': f"{near['(-0.5, 0]']['fixtures']}", 'flat_zero': f"{near['(-0.5, 0]']['with zero fills']}",
              'flat_quoted': f"{near['(-0.5, 0]']['median quoted seconds (3 orders)']:,.0f}",
              'top_quoted': f"{near['(1, inf]']['median quoted seconds (3 orders)']:,.0f}",
              'c_fills': c2(corr.fills), 'c_quoted': c2(corr.quoted_s), 'c_k': c2(corr.k_vol), 'c_pm': c2(corr.pm_vol),
              'c_depth': rng([corr.pm_depth, corr.k_depth], c2),
              'q1': usd(vq.pnl.iloc[0]), 'q5': usd(vq.pnl.iloc[-1]), 'e1': usd(vq.edge.iloc[0]), 'e5': usd(vq.edge.iloc[-1]),
              'inv_q': rng(vq.inv, usd),
              'thin5': usd(dp.iloc[-1]['thin']), 'mid5': usd(dp.iloc[-1]['mid']), 'deep5': usd(dp.iloc[-1]['deep']),
              'edge_all': usd(dec['all']['edge'], 2), 'inv_all': usd(dec['all']['inventory'], 2), 'jump_all': usd(dec['all']['inventory, jump seconds'], 2),
              'edge_lose': usd(dec['losing']['edge'], 2), 'inv_lose': usd(dec['losing']['inventory'], 2),
              'jump_lose': usd(dec['losing']['inventory, jump seconds'], 2),
              'short_up': usd(jp['short YES, price up'], 0), 'short_up_held': usd(jl[('short YES, price up', 'nothing (position held earlier)')], 0),
              'short_up_k': usd(jl[('short YES, price up', 'Kalshi ask')], 0),
              'long_down': usd(jp['long YES, price down'], 0), 'long_down_bid': usd(jl[('long YES, price down', 'PM bid')], 0),
              'payback': usd(jp['short YES, price down'] + jp['long YES, price up'], 0),
              'net_jump': usd(-jmp.pnl.sum(), 0), 'edge_total': usd(drv.edge.sum(), 0)}
    # §7.6 per outcome, strong and weak
    s42 = snaps[42]
    rows6 = {(x['run'], x['unit']): x for x in s42['rows6']}
    pair6 = {x['run']: x for x in s42['pair6']}
    fq = fill_quintiles(s42['oc6']).set_index(['fill quintile', 'role'])
    k['w'] = {'corr': c2(s42['w6'].home.corr(s42['w6'].away), 2, True),
              'fx_mean': usd(rows6[(CAP, 'per fixture')]['mean ($)'], 2), 'oc_mean': usd(rows6[(CAP, 'per outcome')]['mean ($)'], 2),
              'fx_p5': usd(rows6[(CAP, 'per fixture')]['p5 ($)']), 'fx_min': usd(rows6[(CAP, 'per fixture')]['min ($)']),
              'oc_min': usd(rows6[(CAP, 'per outcome')]['min ($)']),
              'diff': usd(pair6['no cap']['strong - weak ($ per outcome)'], 2), 'diff_ci': pair6['no cap']['95% CI'],
              'diff_cap': usd(pair6[CAP]['strong - weak ($ per outcome)'], 2), 'diff_cap_ci': pair6[CAP]['95% CI'].replace('-', '−'),
              'f5_strong': usd(fq.loc[('F5 high', 'strong'), 'mean_usd'], 2), 'f5_weak': usd(fq.loc[('F5 high', 'weak'), 'mean_usd'], 2),
              'dd95': usd({(x['run'], x['traded']): x for x in s42['dd6']}[('no cap', 'both outcomes')]['max drawdown, p95 ($)'], 0)}
    return k


# --- tables ------------------------------------------------------------------------------------

def orders_table(snaps):
    r = snaps[27]['resl']
    d = r[r.group == 'Clubs'].set_index(['rho', 'guard', 'setup'])
    rows = []
    for rho, gd in COMBOS:
        row = {'Clubs, L = 100': combo_label(rho, gd)}
        for setup in SETUP_COLORS:
            q = d.loc[(rho, gd, setup)]
            row[setup] = usd(q.pnl_usd)
        rows.append(row)
    rows.append({'Clubs, L = 100': 'losing / 5th percentile / fixtures needed (ρ = 1, guard on)',
                 **{st: f"{pct(d.loc[(1.0, 1, st)].losing_fx_pct)} / {usd(d.loc[(1.0, 1, st)].p5_usd, 0)} / {int(d.loc[(1.0, 1, st)].fixtures_for_ci)}"
                    for st in SETUP_COLORS}})
    return html(pd.DataFrame(rows))


def buffer_table(snaps):
    b = snaps[30]['resb']
    d = b[(b.group == 'Clubs') & (b.rho == 1.0)].set_index('guard_label').reindex(snaps[30]['ORDER_B'])
    rows = [{'Clubs, ρ = 1': lab, 'P&L per fixture': usd(q.pnl_usd), 'Guard cancels per fixture': f'{q.guard_pulls:.0f}',
             'Bid contracts filled': f'{q.pm_yes_k * 1000:,.0f}', 'Bid markout at the fill': f'{q.pm_yes_mo0_c:.2f} c',
             'Double fills (fixtures)': pct(q.double_fill_pct)} for lab, q in d.iterrows()]
    return html(pd.DataFrame(rows))


def size_table(snaps):
    sz, cap7 = snaps[33]['sz'].sort_index().loc[('Clubs', BEST)], snaps[33]['cap7'].sort_index().loc[('Clubs', BEST)]
    rows = []
    for L in SIZES:
        q, c = sz.loc[L], cap7.loc[L]
        rows.append({'L': L, 'P&L per fixture': f"{usd(q['P&L ($)'], 2)} {q['95% CI']}", 'Per contract of L': f"{q['per contract of L']:.2f}",
                     'Mean ÷ SD': f"{q['mean / SD']:.2f}", 'Losing': pct(q['losing %']),
                     '5th pct / worst fixture': f"{usd(q['p5 ($)'], 0)} / {usd(q['max loss ($)'], 0)}",
                     'Cash, 95th pct (PM / Kalshi)': f"${c['Polymarket p95']:,.0f} / ${c['Kalshi p95']:,.0f}",
                     'Cash, max (PM / Kalshi)': f"${c['Polymarket max']:,.0f} / ${c['Kalshi max']:,.0f}",
                     'Fixtures needed': f"{n_for_ci(q['P&L ($)'], q['SD ($)'])}"})
    return html(pd.DataFrame(rows))


def cap_table(snaps):
    c4 = snaps[36]['cap4'].sort_index().loc[('Clubs', BEST)]
    rows = []
    for run, q in c4.iterrows():
        pm, kc = q['PM cash median / p90 / p95 / max'], q['Kalshi cash median / p90 / p95 / max']
        rows.append({'Clubs, L = 10': run, 'P&L per fixture': f"{usd(q['P&L ($)'], 2)} {q['95% CI']}", 'Losing': pct(q['losing %']),
                     '5th pct / worst': f"{usd(q['p5 ($)'], 1)} / {usd(q['max loss ($)'], 1)}", 'SD': usd(q['SD ($)']),
                     'PM cash, median / p90 / p95 / max': '$' + pm.replace(' / ', ' / $'), 'Kalshi cash, median / p90 / p95 / max': '$' + kc.replace(' / ', ' / $')})
    return html(pd.DataFrame(rows).iloc[::-1])


def decomposition_table(snaps):
    rows = [{'Club fixtures': x['fixtures'], 'Number': x['n'], 'P&L': usd(x['P&L'], 2), 'Edge': usd(x['edge'], 2),
             'Inventory': usd(x['inventory'], 2), 'of which jump seconds': usd(x['inventory, jump seconds'], 2),
             'of which other seconds': usd(x['inventory, other'], 2)} for x in snaps[39]['dec']]
    return html(pd.DataFrame(rows))


def strength_table(snaps):
    s = snaps[42]
    rows6 = {(x['run'], x['unit']): x for x in s['rows6']}
    rows = []
    for role in ('strong', 'weak'):
        x = rows6[('no cap', role)]
        rows.append({'No cap, per outcome': f'{role} team', 'Mean': usd(x['mean ($)'], 2), 'Median': usd(x['median ($)'], 2),
                     'Losing': pct(x['losing %']), 'Losing, if filled': pct(x['losing % if filled']), 'No fill': pct(x['zero-fill %']),
                     'Mean fills': f"{x['mean fills']:.0f}", 'SD': usd(x['SD ($)']), 'Worst': usd(x['min ($)'])})
    return html(pd.DataFrame(rows))


def bankroll_table(snaps):
    rows = [{'Traded (no cap)': x['traded'], 'Mean per fixture': usd(x['mean ($ per fixture)'], 2), 'Mean ÷ SD': f"{x['mean / SD']:.2f}",
             'P&L after 100, median': usd(x['P&L after 100, median ($)'], 0),
             'Max drawdown, median / 95th pct': f"{usd(x['max drawdown, median ($)'], 0)} / {usd(x['max drawdown, p95 ($)'], 0)}",
             'Behind after 100': pct(x['P(P&L after 100 < 0) %'], 2)} for x in snaps[42]['dd6'] if x['run'] == 'no cap']
    return html(pd.DataFrame(rows))


def tables(snaps):
    return {'orders_table': orders_table(snaps), 'buffer_table': buffer_table(snaps), 'size_table': size_table(snaps),
            'cap_table': cap_table(snaps), 'decomposition_table': decomposition_table(snaps), 'strength_table': strength_table(snaps),
            'bankroll_table': bankroll_table(snaps)}
