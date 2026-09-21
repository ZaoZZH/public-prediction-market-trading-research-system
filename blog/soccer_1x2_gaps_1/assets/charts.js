// Draws every embedded Plotly figure and restyles its chrome when the page theme changes.
// Figure data is inlined next to each chart; trace colours are fixed, only backgrounds, text and grid follow the theme.
(function () {
  const TEMPLATES = {"light": {"layout": {"paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)", "font": {"family": "\"Source Sans 3\", \"Segoe UI\", Helvetica, Arial, sans-serif", "color": "#23302f", "size": 12}, "xaxis": {"gridcolor": "#e4e8e4", "linecolor": "#c6cfc8", "zerolinecolor": "#c6cfc8", "tickcolor": "#c6cfc8", "ticks": "outside", "showline": false}, "yaxis": {"gridcolor": "#e4e8e4", "linecolor": "#c6cfc8", "zerolinecolor": "#c6cfc8", "tickcolor": "#c6cfc8", "ticks": "outside", "showline": false}, "hoverlabel": {"bgcolor": "#ffffff", "font": {"family": "\"Source Sans 3\", \"Segoe UI\", Helvetica, Arial, sans-serif", "color": "#23302f"}}, "modebar": {"color": "#7d8791", "activecolor": "#167263", "bgcolor": "rgba(0,0,0,0)"}, "legend": {"bgcolor": "rgba(0,0,0,0)"}}}, "dark": {"layout": {"paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)", "font": {"family": "\"Source Sans 3\", \"Segoe UI\", Helvetica, Arial, sans-serif", "color": "#d9dfda", "size": 12}, "xaxis": {"gridcolor": "#2b3237", "linecolor": "#3d464c", "zerolinecolor": "#3d464c", "tickcolor": "#3d464c", "ticks": "outside", "showline": false}, "yaxis": {"gridcolor": "#2b3237", "linecolor": "#3d464c", "zerolinecolor": "#3d464c", "tickcolor": "#3d464c", "ticks": "outside", "showline": false}, "hoverlabel": {"bgcolor": "#1f2529", "font": {"family": "\"Source Sans 3\", \"Segoe UI\", Helvetica, Arial, sans-serif", "color": "#d9dfda"}}, "modebar": {"color": "#8a929b", "activecolor": "#5fc3ad", "bgcolor": "rgba(0,0,0,0)"}, "legend": {"bgcolor": "rgba(0,0,0,0)"}}}};
  const CONFIG = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud', 'lasso2d', 'select2d'],
                   toImageButtonOptions: { format: 'svg' } };
  const mode = () => (document.body.classList.contains('quarto-dark') ? 'dark' : 'light');
  const charts = [];

  function draw() {
    document.querySelectorAll('script[data-chart]').forEach((node) => {
      const fig = JSON.parse(node.textContent);
      const id = node.dataset.chart;
      fig.layout.template = TEMPLATES[mode()];
      Plotly.newPlot(id, fig.data, fig.layout, CONFIG);
      charts.push(id);
    });
  }

  function retheme() {
    const template = TEMPLATES[mode()];
    charts.forEach((id) => Plotly.relayout(id, { template }));
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', draw); else draw();
  new MutationObserver(retheme).observe(document.body, { attributes: true, attributeFilter: ['class'] });
})();
