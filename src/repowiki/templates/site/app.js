/* repowiki site runtime. All data comes from window.SITE_DATA, embedded by
   `repowiki site`. No network: markdown via vendored marked, diagrams via
   vendored mermaid, source snippets pre-extracted at generation time. */
(function () {
  'use strict';
  var D = window.SITE_DATA;
  var $ = function (sel, el) { return (el || document).querySelector(sel); };
  document.documentElement.lang = D.locale;
  $('#site-title').textContent = D.repo;
  $('#search').placeholder = D.ui.search_placeholder;
  $('#menu-btn').title = D.ui.menu_label;
  $('#menu-btn').setAttribute('aria-label', D.ui.menu_label);
  $('#theme-btn').title = D.ui.theme_label;
  $('#theme-btn').setAttribute('aria-label', D.ui.theme_label);
  $('#modal-close').title = D.ui.close_label;

  // --- theme ---------------------------------------------------------------
  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem('rw-theme', t); } catch (e) { /* file:// may block storage */ }
  }
  var saved = null;
  try { saved = localStorage.getItem('rw-theme'); } catch (e) { /* ignore */ }
  applyTheme(saved || (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
  $('#theme-btn').addEventListener('click', function () {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    applyTheme(dark ? 'light' : 'dark');
    renderMermaid();
  });

  // --- slug (mirrors paths.github_anchor: lowercase, drop punctuation, spaces->-) ---
  function slug(t) {
    return t.trim().toLowerCase()
      .replace(/[^\p{L}\p{N}\s]/gu, '')
      .replace(/\s+/g, '-').replace(/-{2,}/g, '-').replace(/^-|-$/g, '');
  }
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // --- navigation ----------------------------------------------------------
  function navLink(pageIdx, title, cls) {
    return '<a class="' + cls + '" data-page="' + pageIdx + '" href="#/p/' + pageIdx + '">' + esc(title) + '</a>';
  }
  function buildNav() {
    var html = '';
    D.nav.forEach(function (entry, i) {
      if (entry.children) {
        html += '<div class="nav-chapter">' + esc(entry.title) + '</div>';
        entry.children.forEach(function (c) {
          html += navLink(c.page, c.title, 'nav-page');
        });
      } else {
        html += navLink(entry.page, entry.title, i === 0 ? 'nav-page nav-overview' : 'nav-page');
      }
    });
    $('#nav-tree').innerHTML = html;
  }

  // --- page rendering ------------------------------------------------------
  var mermaidCounter = 0;
  function renderMermaid() {
    var blocks = document.querySelectorAll('#content pre code.language-mermaid');
    if (!blocks.length) return;
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    window.mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: dark ? 'dark' : 'default' });
    [].forEach.call(blocks, function (code) {
      var holder = document.createElement('div');
      holder.className = 'rw-mermaid';
      code.parentElement.replaceWith(holder);
      var src = code.textContent;
      window.mermaid.render('rw-m' + (mermaidCounter++), src)
        .then(function (res) { holder.innerHTML = res.svg; })
        .catch(function () {
          holder.className = 'rw-mermaid-error';
          holder.innerHTML = '<pre>' + esc(src) + '</pre>';
        });
    });
  }

  function enhanceCites(root) {
    // <cite> blocks hold markdown that CommonMark leaves unparsed inside raw
    // HTML; re-parse their text content so the reference lists render.
    [].forEach.call(root.querySelectorAll('cite'), function (el) {
      var inner = marked.parse(el.textContent.trim());
      if (inner.trim()) el.innerHTML = inner;
    });
  }

  function assignHeadingIds(root) {
    [].forEach.call(root.querySelectorAll('h1,h2,h3,h4,h5,h6'), function (h) {
      if (!h.id) h.id = slug(h.textContent);
    });
  }

  function openPage(i, push) {
    var page = D.pages[i];
    if (!page) return;
    current = i;
    var el = $('#content');
    el.innerHTML = marked.parse(page.md);
    enhanceCites(el);
    assignHeadingIds(el);
    document.title = page.title + ' · ' + D.repo;
    renderMermaid();
    [].forEach.call(document.querySelectorAll('#nav-tree a'), function (a) { a.classList.toggle('active', +a.getAttribute('data-page') === i); });
    closeSidebar();
    window.scrollTo(0, 0);
    if (push !== false && location.hash !== '#/p/' + i) location.hash = '#/p/' + i;
  }

  // --- snippet modal (file:// references) ----------------------------------
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest ? ev.target.closest('a[href^="file://"]') : null;
    if (!a) return;
    ev.preventDefault();
    showSnippet(a.getAttribute('href').slice('file://'.length));
  });

  function showSnippet(key) {
    var sn = D.snippets[key];
    var path = key.split('#')[0];
    $('#modal-title').textContent = path + (sn ? ' · ' + sn.start + '–' + sn.end + ' ' + D.ui.lines_label : '');
    if (!sn || sn.missing) {
      $('#modal-body').innerHTML = '<p class="rw-missing">' + esc(D.ui.snippet_missing) + '</p>';
    } else {
      var html = '<table class="rw-code"><tbody>';
      for (var i = 0; i < sn.lines.length; i++) {
        html += '<tr><td class="rw-ln">' + (sn.start + i) + '</td><td><pre>' + esc(sn.lines[i]) + '</pre></td></tr>';
      }
      $('#modal-body').innerHTML = html + '</tbody></table>';
    }
    $('#modal').hidden = false;
    $('#modal-close').focus();
  }
  function closeModal() { $('#modal').hidden = true; }
  $('#modal-close').addEventListener('click', closeModal);
  $('#modal').addEventListener('click', function (ev) { if (ev.target === this) closeModal(); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') closeModal(); });

  // --- search --------------------------------------------------------------
  var idx = D.pages.map(function (p) { return p.md.toLowerCase(); });
  $('#search').addEventListener('input', function () {
    var q = this.value.trim().toLowerCase();
    var box = $('#search-results');
    if (!q) { box.hidden = true; box.innerHTML = ''; return; }
    var hits = [];
    idx.forEach(function (text, i) {
      var at = text.indexOf(q);
      if (at === -1) return;
      var from = Math.max(0, at - 30);
      hits.push({ i: i, ctx: D.pages[i].md.slice(from, at + 60).replace(/\s+/g, ' ') });
    });
    box.innerHTML = hits.length
      ? hits.slice(0, 20).map(function (h) {
          return '<a class="search-hit" data-page="' + h.i + '" href="#/p/' + h.i + '"><b>' +
            esc(D.pages[h.i].title) + '</b><span>…' + esc(h.ctx) + '…</span></a>';
        }).join('')
      : '<span class="search-none">' + esc(D.ui.no_results) + '</span>';
    box.hidden = false;
  });
  $('#search-results').addEventListener('click', function (ev) {
    var a = ev.target.closest('a[data-page]');
    if (!a) return;
    $('#search').value = '';
    this.hidden = true;
    openPage(+a.getAttribute('data-page'));
  });

  // --- routing & responsive sidebar ---------------------------------------
  var current = -1;
  function fromHash(initial) {
    // `#/p/N` selects a page. Any other hash (in-page TOC anchors like `#简介`)
    // keeps the current page; only an initial load without a page route opens 0.
    var m = location.hash.match(/^#\/p\/(\d+)/);
    if (!m) {
      if (initial) openPage(0, false);
      return;
    }
    if (+m[1] !== current) openPage(+m[1], false);
  }
  window.addEventListener('hashchange', function () { fromHash(false); });

  $('#menu-btn').addEventListener('click', function () { document.body.classList.toggle('sidebar-open'); });
  $('#backdrop').addEventListener('click', closeSidebar);
  $('#nav-tree').addEventListener('click', function (ev) {
    var a = ev.target.closest('a[data-page]');
    if (!a) return;
    ev.preventDefault();
    openPage(+a.getAttribute('data-page'));
  });
  function closeSidebar() { document.body.classList.remove('sidebar-open'); }

  buildNav();
  fromHash(true);
})();
