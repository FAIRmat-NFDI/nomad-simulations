/* Adds pan/zoom + a small toolbar to Mermaid diagrams rendered by Material v9. */
(function () {
  // Material v9 commonly wraps as <figure class="mdx-mermaid"><svg class="mermaid" ...>
  // but let's be generous with selectors:
  const SELECTOR = [
    '.mdx-mermaid svg',
    'svg.mermaid',
    '.mermaid svg',
    'svg[data-processed="true"]',
    'svg[id^="mermaid-"]'
  ].join(',');

  function ensureSvgPanZoom() {
    return typeof window.svgPanZoom === 'function';
  }

  function initOne(svg) {
    if (!svg || svg.__pz) return;

    // Make responsive
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    svg.removeAttribute('height');
    svg.style.width = '100%';

    // Init pan/zoom (may throw if not inline SVG)
    try {
      svg.__pz = svgPanZoom(svg, {
        controlIconsEnabled: true,   // shows built-in +/-/fit
        fit: true,
        center: true,
        contain: true,
        minZoom: 0.4,
        maxZoom: 12,
        zoomScaleSensitivity: 0.3
      });
    } catch (e) {
      // Try again later if it wasn't ready yet
      return;
    }

    // Toolbar (↗ open, ⬇ download, ⤢ fit, ⟲ reset)
    const parent = svg.parentElement || svg;
    if (!parent.querySelector('.mermaid-zoom-toolbar')) {
      parent.style.position = parent.style.position || 'relative';
      const bar = document.createElement('div');
      bar.className = 'mermaid-zoom-toolbar';
      bar.innerHTML = `
        <button type="button" data-act="open" title="Open in new window">↗</button>
        <button type="button" data-act="dl"   title="Download SVG">⬇</button>
        <button type="button" data-act="fit"  title="Fit">⤢</button>
        <button type="button" data-act="rst"  title="Reset">⟲</button>
      `;
      parent.appendChild(bar);

      bar.addEventListener('click', (e) => {
        const act = e.target && e.target.dataset && e.target.dataset.act;
        if (!act) return;

        if (act === 'open') {
          const w = window.open('', '_blank');
          const markup = svg.outerHTML;
          w.document.write(`<!doctype html>
<html><head><meta charset="utf-8"><title>Diagram</title>
<style>html,body{height:100%;margin:0} svg{width:100%;height:100%}</style>
<script src="https://unpkg.com/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"><\/script>
</head><body>${markup}
<script>
  const s = document.querySelector('svg');
  if (s) {
    s.removeAttribute('height'); s.style.width='100%';
    svgPanZoom(s, { controlIconsEnabled:true, fit:true, center:true, minZoom:0.4, maxZoom:12 });
  }
<\/script></body></html>`);
          w.document.close();
        }

        if (act === 'dl') {
          const blob = new Blob([svg.outerHTML], { type: 'image/svg+xml;charset=utf-8' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url; a.download = 'diagram.svg';
          document.body.appendChild(a); a.click(); a.remove();
          URL.revokeObjectURL(url);
        }

        if (act === 'fit') svg.__pz && svg.__pz.fit();
        if (act === 'rst') { svg.__pz && svg.__pz.reset(); svg.__pz.fit(); svg.__pz.center(); }
      });
    }
  }

  function initAll() {
    if (!ensureSvgPanZoom()) return false;
    document.querySelectorAll(SELECTOR).forEach(initOne);
    return true;
  }

  // Try immediately, then observe DOM changes for late renders
  function onPage() {
    // Attempt a few times to beat race conditions
    let tries = 0;
    function attempt() {
      tries += 1;
      const ok = initAll();
      if (ok && document.querySelector(SELECTOR)) return; // success
      if (tries < 20) requestAnimationFrame(attempt);      // ~300ms window
    }
    attempt();

    // Also watch for diagrams added after navigation
    const root = document.querySelector('main') || document.body;
    if (!root) return;
    const obs = new MutationObserver(() => initAll());
    obs.observe(root, { childList: true, subtree: true });
    setTimeout(() => obs.disconnect(), 5000); // stop after 5s to avoid churn
  }

  if (window.document$) {
    document$.subscribe(() => setTimeout(onPage, 0)); // Material instant nav
  } else {
    window.addEventListener('DOMContentLoaded', onPage);
  }
})();
