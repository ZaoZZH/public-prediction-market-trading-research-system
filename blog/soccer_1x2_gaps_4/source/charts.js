// Draws every embedded Plotly figure and restyles its chrome when the page theme changes.
// Figure data is inlined next to each chart; trace colours are fixed, only backgrounds, text and grid follow the theme.
(function () {
  /*TEMPLATES*/
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
