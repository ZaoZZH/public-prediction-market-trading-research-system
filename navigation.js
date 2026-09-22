// Shared navigation; Quarto keeps ownership of article and chart theme changes.
(() => {
  const root = new URL('.', document.currentScript.src);
  const media = matchMedia('(prefers-color-scheme: dark)');
  const saved = () => { try { return localStorage.getItem('quarto-color-scheme'); } catch { return null; } };
  const preferred = () => saved() ? saved() === 'alternate' : media.matches;
  document.documentElement.dataset.theme = preferred() ? 'dark' : 'light';

  document.addEventListener('DOMContentLoaded', () => {
    const article = !!document.getElementById('quarto-document-content');
    const home = location.pathname === root.pathname || location.pathname === root.pathname + 'index.html';
    const href = path => new URL(path, root).href;
    const header = document.createElement('header');
    header.className = 'site-bar';
    header.innerHTML = `<button class="menu-trigger" aria-label="Open menu" aria-controls="site-menu" aria-expanded="false">☰</button><a class="site-wordmark" href="${href('index.html')}">Gerald's Prediction Market<br>Trading Research &amp; System</a>${home ? '<button class="theme-switch" role="switch" aria-checked="false" aria-label="Dark mode"><span>Dark mode</span><i aria-hidden="true"></i></button>' : ''}`;
    const drawer = document.createElement('dialog');
    drawer.id = 'site-menu';
    drawer.className = 'site-drawer';
    drawer.setAttribute('aria-labelledby', 'menu-title');
    drawer.innerHTML = `<div class="drawer-heading"><span id="menu-title">Explore</span><button class="menu-close" aria-label="Close menu">×</button></div><nav class="drawer-links" aria-label="Main navigation"><a href="${href('index.html')}">Home</a><a href="${href('blog/index.html')}">Research Blog</a><a href="${href('dashboard/index.html')}">Live Dashboard</a><a href="${href('about/index.html')}">About Me</a></nav><div class="drawer-theme"><button class="theme-switch" role="switch" aria-checked="false" aria-label="Dark mode"><span>Dark mode</span><i aria-hidden="true"></i></button></div>`;
    const toc = document.querySelector('#TOC > ul');
    if (toc) {
      const section = document.createElement('nav');
      section.className = 'drawer-toc';
      section.setAttribute('aria-label', 'On this page');
      const title = document.createElement('p');
      title.textContent = 'On this page';
      section.append(title);
      // Copy only semantic links, without Quarto's scrollspy IDs or collapse rules.
      const copy = toc.cloneNode(true);
      copy.querySelectorAll('*').forEach(el => {
        for (const attr of [...el.attributes]) if (attr.name !== 'href') el.removeAttribute(attr.name);
      });
      copy.removeAttribute('class');
      copy.querySelectorAll('a[href]').forEach(a => { if (a.hash) a.href = location.pathname + a.hash; });
      section.append(copy);
      drawer.append(section);
    }
    document.body.prepend(header);
    document.body.append(drawer);
    document.body.classList.add('site-navigation-ready');
    if (article) document.body.classList.add('site-article');
    const trigger = header.querySelector('.menu-trigger');
    trigger.addEventListener('click', () => { drawer.showModal(); trigger.setAttribute('aria-expanded', 'true'); document.body.classList.add('menu-open'); });
    const close = () => drawer.close();
    drawer.querySelector('.menu-close').addEventListener('click', close);
    drawer.addEventListener('click', e => { if (e.target === drawer && e.clientX >= drawer.getBoundingClientRect().right) close(); });
    drawer.addEventListener('close', () => { trigger.setAttribute('aria-expanded', 'false'); document.body.classList.remove('menu-open'); trigger.focus(); });
    drawer.querySelectorAll('a').forEach(a => {
      if (a.href === location.href.split('#')[0]) a.setAttribute('aria-current', 'page');
      a.addEventListener('click', () => {
        close();
        if (a.hash && a.origin === location.origin && a.pathname === location.pathname) {
          const target = document.getElementById(decodeURIComponent(a.hash.slice(1)));
          if (target) { target.setAttribute('tabindex', '-1'); target.focus({ preventScroll: true }); }
        }
      });
    });
    const sync = () => {
      const dark = article ? document.body.classList.contains('quarto-dark') : preferred();
      document.documentElement.dataset.theme = dark ? 'dark' : 'light';
      document.querySelectorAll('.theme-switch').forEach(button => button.setAttribute('aria-checked', String(dark)));
    };
    document.querySelectorAll('.theme-switch').forEach(button => button.addEventListener('click', () => {
      if (article && window.quartoToggleColorScheme) window.quartoToggleColorScheme();
      else {
        const dark = document.documentElement.dataset.theme !== 'dark';
        try { localStorage.setItem('quarto-color-scheme', dark ? 'alternate' : 'default'); } catch {}
        document.documentElement.dataset.theme = dark ? 'dark' : 'light';
        document.querySelectorAll('.theme-switch').forEach(b => b.setAttribute('aria-checked', String(dark)));
        return;
      }
      sync();
    }));
    media.addEventListener('change', sync);
    new MutationObserver(sync).observe(document.body, { attributes: true, attributeFilter: ['class'] });
    sync();
  });
})();
