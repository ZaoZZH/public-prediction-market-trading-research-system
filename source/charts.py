"""Plotly views of notebook 02.1's computed objects; no separate research pipeline."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLORS = ['#3859b8', '#c6543d', '#15806c', '#865ba6']
WORDS = {
    'pre_24h_to_1h': '24h to 1h before kickoff', 'pre_last_hour': 'Last hour before kickoff',
    'post_0_to_105m': 'In play: 0–105 min', 'post_0_to_55m': '0–55 min after kickoff',
    'post_55_to_105m': '55–105 min after kickoff', 'post_105_to_135m': 'Late window: 105–135 min',
    'pm_trades_per_fixture': 'Polymarket', 'k_trades_per_fixture': 'Kalshi',
    'KALSHI': 'Kalshi → Polymarket', 'POLYMARKET': 'Polymarket → Kalshi',
    'fresh_pct_of_clock': 'Both fresh (% of clock)', 'trades_per_fixture': 'Trades per fixture',
    'freshness': 'Freshness cutoff (seconds)', 'horizon': 'Forward horizon (seconds)',
    'follow_pct': 'Destination traded within horizon (%)', 'clock_pct': 'Share of clock (%)',
    'combo': 'Competition and season', 'share_pct': 'Share (%)', 'gap_bucket': 'PM − Kalshi (cents)',
    'mean_gap_c': 'Mean gap (cents)', 'le_m2c_pct': 'PM at least 2c lower (%)', 'ge_p2c_pct': 'PM at least 2c higher (%)',
    'pos_pct': 'Positive reference observations (%)', 'positive_pct': 'Positive reference observations (%)',
    'pos_per_fixture_hour': 'Positive observations per fixture-hour', 'cumulative_probability': 'Fraction of episodes',
    'seconds': 'Recorded seconds to reprice', 'trigger': 'Latest venue to print', 'price_bucket': 'YES reference price',
    'team_win': 'Home + away', 'outcome': 'Outcome', 'all': 'All outcomes', 'draw': 'Draw', 'home': 'Home', 'away': 'Away',
    'pm': 'Polymarket', 'k': 'Kalshi', 'both': 'Both venues', 'route': 'Route (PM role / Kalshi role)',
}


def readable(value):
    text = str(value).replace('World Cup 2026/27', 'World Cup 2026')
    if text in WORDS:
        return WORDS[text]
    for key in ['pre_24h_to_1h', 'pre_last_hour', 'post_0_to_105m', 'post_105_to_135m',
                'mean_gap_c', 'le_m2c_pct', 'ge_p2c_pct', 'team_win']:
        text = text.replace(key, WORDS[key])
    return text


def chart(data, x, y, color=None, facet=None, kind='bar', **kwargs):
    """One readable panel at a time; dropdowns retain every original facet."""
    plotted = data.copy()
    for key in [x, y, color, facet]:
        if key and not pd.api.types.is_numeric_dtype(plotted[key]):
            plotted[key] = plotted[key].map(readable)
    groups = list(plotted.groupby(facet, sort=False, observed=True)) if facet else [(None, plotted)]
    if facet:
        groups.sort(key=lambda group: (not ('Premier League 2025/26' in str(group[0]) or str(group[0]) == 'In play: 0–105 min'),))
    fig = go.Figure()
    counts = []
    categories = list(plotted[color].dropna().unique()) if color else []
    for label, frame in groups:
        maker = px.line if kind == 'line' else px.bar
        part = maker(frame, x=x, y=y, color=color, color_discrete_sequence=COLORS,
                     category_orders={color: categories} if color else {}, **kwargs)
        counts.append(len(part.data))
        for trace in part.data:
            trace.visible = len(counts) == 1
            if kind == 'line':
                trace.mode = 'lines+markers'
            fig.add_trace(trace)
    buttons, offset = [], 0
    for (label, _), count in zip(groups, counts):
        visible = [False] * len(fig.data)
        visible[offset:offset + count] = [True] * count
        buttons.append(dict(label=str(label), method='update', args=[{'visible': visible}]))
        offset += count
    fig.update_layout(template='plotly_white', height=480, barmode='group',
                      margin=dict(l=65, r=25, t=90 if facet else 30, b=90),
                      font=dict(family='Arial, sans-serif', size=13),
                      xaxis_title=readable(x), yaxis_title=readable(y),
                      legend=dict(orientation='h', y=-.25, title_text=''),
                      hovermode='closest')
    if facet:
        fig.update_layout(updatemenus=[dict(buttons=buttons, x=0, y=1.20, xanchor='left', yanchor='top')])
    if kwargs.get('log_x'):
        fig.update_xaxes(type='log')
    if kwargs.get('log_y'):
        fig.update_yaxes(type='log')
    return fig, data


def views(i, s):
    """Return (figure, downloadable data) pairs for each chart-producing cell."""
    def get(name): return s[name]
    def long(df, ids, values, var='series', val='value'):
        return df[ids + values].melt(id_vars=ids, value_vars=values, var_name=var, value_name=val)
    def label(c): return s['LABEL'][c].replace('\n', ' | ')
    if i == 3:
        d = long(get('pop').reset_index(), ['combo'], ['pm_trades_per_fixture', 'k_trades_per_fixture'], val='trades_per_fixture')
        return [chart(d, 'combo', 'trades_per_fixture', 'series', log_y=True)]
    if i == 5:
        return [chart(get('avail'), 'freshness', 'fresh_pct_of_clock', 'phase', 'combo', kind='line')]
    if i == 7:
        result = []
        for f in (5, 10, 60):
            d = long(get('state4').query('freshness == @f'), ['combo', 'phase', 'freshness'], get('STATE_COLS'), val='clock_pct')
            d['series'] = d.series.replace(dict(zip(get('STATE_COLS'), get('STATE_NAMES'))))
            fig, d = chart(d, 'clock_pct', 'combo', 'series', 'phase', orientation='h')
            fig.update_layout(barmode='stack', title=f'Full-clock activity states · F={f}s', height=570)
            fig.update_xaxes(range=[0, 100])
            result.append((fig, d))
        return result
    if i == 9:
        result = []
        for ph in get('PHASES'):
            fig, d = chart(get('wg').query('phase == @ph and freshness == 60 and other_state == "all"'),
                           'horizon', 'follow_pct', 'source', 'combo', kind='line', log_x=True)
            fig.update_layout(title=readable(ph))
            result.append((fig, d))
        return result
    if i == 14:
        rows = []
        for name, outcomes in get('OUTCOME_SEL').items():
            for c in get('CANDS'):
                d = s['cell'](get('cents'), c)
                pct, _ = s['cent_stats'](d[(d.pair == 'all/all') & d.outcome.isin(outcomes)])
                for bucket, r in pct.iterrows():
                    for weight in ['n', 'time']:
                        rows.append(dict(panel=label(c) + ' | ' + name, gap_bucket=get('cent_labels')[get('C').index(bucket)],
                                         weighting={'n': 'per print', 'time': 'per second'}[weight], share_pct=r[weight]))
        return [chart(pd.DataFrame(rows), 'gap_bucket', 'share_pct', 'weighting', 'panel')]
    if i == 16:
        fig, rows, buttons = go.Figure(), [], []
        for j, (z, lo, hi, nn) in get('mats').items():
            for a in range(3):
                for b in range(3):
                    rows.append(dict(cell=label(get('CANDS')[j]), pm_action=get('ORDER')[a], kalshi_action=get('ORDER')[b],
                                     mean_gap_c=z[a,b], lower_tail_pct=lo[a,b], upper_tail_pct=hi[a,b], prints=nn[a,b]))
            fig.add_trace(go.Heatmap(z=z, x=get('ORDER'), y=get('ORDER'), zmin=-get('vmax'), zmax=get('vmax'),
                colorscale='RdBu_r', visible=j == 0, customdata=np.stack([lo, hi, nn], axis=-1),
                texttemplate='%{z:.2f}c', hovertemplate='PM %{y} / Kalshi %{x}<br>Mean %{z:.3f}c<br>≤−2c %{customdata[0]:.2f}%<br>≥2c %{customdata[1]:.2f}%<br>%{customdata[2]:,.0f} prints<extra></extra>'))
            buttons.append(dict(label=readable(label(get('CANDS')[j])), method='update', args=[{'visible': [k == j for k in range(len(get('CANDS')))]}]))
        fig.update_layout(template='plotly_white', height=460, margin=dict(t=90),
                          xaxis_title='Kalshi taker action', yaxis_title='PM taker action',
                          updatemenus=[dict(buttons=buttons, x=0, y=1.2, xanchor='left')])
        return [(fig, pd.DataFrame(rows))]
    if i == 18:
        # Separate units explicitly instead of overlaying cents and percentages.
        d = long(get('raw'), ['cell', 'outcome'], ['mean_gap_c', 'le_m2c_pct', 'ge_p2c_pct'], var='metric')
        d['panel'] = d.cell + ' | ' + d.metric
        return [chart(d, 'outcome', 'value', facet='panel')]
    if i == 20:
        d = get('rates').copy()
        d['panel'] = d.cell + ' | ' + d.outcome_sel
        return [chart(d, 'route', 'pos_pct', 'direction', 'panel')]
    if i == 21:
        return [chart(get('fs'), 'route', 'positive_pct', 'scenario', 'cell')]
    if i == 22:
        frames = []
        for c in get('CANDS'):
            scr = get('scr')
            d = s['screen_rates'](scr[(scr.combo == c[0]) & (scr.phase == c[1])], ['route', 'freshness'])
            frames.append(d.assign(cell=label(c), candidate_freshness=c[2]))
        return [chart(pd.concat(frames).sort_values('freshness'), 'freshness', 'pos_pct', 'route', 'cell', kind='line', log_x=True)]
    if i in (26, 28):
        key = 'trigger' if i == 26 else 'price_bucket'
        d = get('cd').groupby(['cell', 'route', key], observed=True)[['n', 'pos_0c']].sum().reset_index()
        d['pos_pct'] = 100 * d.pos_0c / d.n.replace(0, np.nan)
        return [chart(d, key, 'pos_pct', 'route', 'cell')]
    if i == 30:
        return [chart(get('ph'), 'route', 'pos_per_fixture_hour', facet='cell', log_y=True)]
    if i == 32:
        rows = []
        for (cl, route), d in get('ep').groupby(['cell', 'route'], observed=True):
            for x, q in zip(np.quantile(d.span_reprice.dropna(), get('qs')), get('qs')):
                rows.append(dict(cell=cl, route=route, seconds=x, cumulative_probability=q, episodes=len(d)))
        return [chart(pd.DataFrame(rows), 'seconds', 'cumulative_probability', 'route', 'cell', kind='line', log_x=True)]
    return []
