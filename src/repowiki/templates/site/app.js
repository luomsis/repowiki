/* repowiki site runtime. All data comes from window.SITE_DATA, embedded by
   `repowiki site`. No network: markdown via vendored marked, diagrams via
   vendored mermaid, source snippets pre-extracted at generation time. */
(function () {
  'use strict';
  var D = window.SITE_DATA;
  var zh = D.locale === 'zh';
  var $ = function (sel, el) { return (el || document).querySelector(sel); };
  document.documentElement.lang = D.locale;
  $('#site-title').textContent = D.repo;
  $('#search').placeholder = D.ui.search_placeholder;
  $('#menu-btn').title = D.ui.menu_label;
  $('#menu-btn').setAttribute('aria-label', D.ui.menu_label);
  $('#theme-btn').title = D.ui.theme_label;
  $('#theme-btn').setAttribute('aria-label', D.ui.theme_label);
  $('#modal-close').title = D.ui.close_label;
  $('#toc-label').textContent = zh ? '本页内容' : 'On this page';

  var ICON_COPY = '<svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" aria-hidden="true"><rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 3.5v-1a1 1 0 0 0-1-1h-6a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h1"/></svg>';
  var ICON_CHECK = '<svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 8.5l3.5 3.5L13 5"/></svg>';
  var ICON_CHEV = '<svg class="chev" viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 6l4 4 4-4"/></svg>';

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

  // --- navigation (collapsible chapters, state persisted) -------------------
  var navState = {};
  try { navState = JSON.parse(localStorage.getItem('rw-nav') || '{}'); } catch (e) { navState = {}; }
  function saveNavState() {
    try { localStorage.setItem('rw-nav', JSON.stringify(navState)); } catch (e) { /* ignore */ }
  }
  function navLink(pageIdx, title, cls) {
    return '<a class="' + cls + '" data-page="' + pageIdx + '" href="#/p/' + pageIdx + '">' + esc(title) + '</a>';
  }
  function buildNav() {
    var html = '';
    D.nav.forEach(function (entry, i) {
      if (entry.children) {
        var open = navState['c' + i] !== '0';
        html += '<button type="button" class="nav-chapter" data-ch="' + i + '" aria-expanded="' + open + '">' +
          '<span>' + esc(entry.title) + '</span>' + ICON_CHEV + '</button>';
        html += '<div class="nav-children" data-chp="' + i + '"' + (open ? '' : ' hidden') + '>';
        entry.children.forEach(function (c) {
          html += navLink(c.page, c.title, 'nav-page');
        });
        html += '</div>';
      } else {
        html += navLink(entry.page, entry.title, i === 0 ? 'nav-page nav-overview' : 'nav-page');
      }
    });
    $('#nav-tree').innerHTML = html;
  }
  function expandChapter(pageIdx) {
    var a = document.querySelector('#nav-tree a[data-page="' + pageIdx + '"]');
    if (!a) return;
    var group = a.closest('.nav-children');
    if (!group) return;
    group.hidden = false;
    var btn = document.querySelector('#nav-tree .nav-chapter[data-ch="' + group.getAttribute('data-chp') + '"]');
    if (btn) btn.setAttribute('aria-expanded', 'true');
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
      var outer = code.parentElement.closest('.codeblock');
      (outer || code.parentElement).replaceWith(holder);
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

  function enhanceCode() {
    [].forEach.call(document.querySelectorAll('#content pre > code'), function (code) {
      if (/language-mermaid/.test(code.className)) return;
      var pre = code.parentElement;
      if (pre.parentElement && pre.parentElement.classList.contains('codeblock')) return;
      var lang = (code.className.match(/language-([\w+-]+)/) || [])[1] || '';
      var wrap = document.createElement('div');
      wrap.className = 'codeblock';
      var head = document.createElement('div');
      head.className = 'codeblock-head';
      var label = document.createElement('span');
      label.className = 'codeblock-lang';
      label.textContent = lang || 'text';
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'copy-btn';
      btn.innerHTML = ICON_COPY + '<span>' + (zh ? '复制' : 'Copy') + '</span>';
      btn.addEventListener('click', function () { copyText(code.textContent, btn); });
      head.appendChild(label);
      head.appendChild(btn);
      pre.replaceWith(wrap);
      wrap.appendChild(head);
      wrap.appendChild(pre);
    });
  }

  function copyText(text, btn) {
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { /* ignore */ }
      document.body.removeChild(ta);
      return ok;
    }
    function done(ok) {
      btn.innerHTML = ICON_CHECK + '<span>' +
        (ok ? (zh ? '已复制' : 'Copied') : (zh ? '复制失败' : 'Failed')) + '</span>';
      setTimeout(function () {
        btn.innerHTML = ICON_COPY + '<span>' + (zh ? '复制' : 'Copy') + '</span>';
      }, 1400);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(fallback()); });
    } else {
      done(fallback());
    }
  }

  // --- on-this-page toc + scroll spy + reading progress ---------------------
  var tocHeads = [];
  function buildToc() {
    var box = $('#page-toc');
    tocHeads = [].filter.call(
      document.querySelectorAll('#content h2, #content h3'),
      function (h) { return h.textContent.trim() && h.id; }
    );
    if (tocHeads.length < 2) { $('#toc-wrap').hidden = true; box.innerHTML = ''; return; }
    $('#toc-wrap').hidden = false;
    box.innerHTML = tocHeads.map(function (h) {
      return '<a class="toc-' + h.tagName.toLowerCase() + '" href="#' + h.id + '">' + esc(h.textContent) + '</a>';
    }).join('');
  }
  var ticking = false;
  function onScroll() {
    ticking = false;
    var doc = document.documentElement;
    var max = doc.scrollHeight - window.innerHeight;
    $('#progress').style.transform = 'scaleX(' + (max > 0 ? Math.min(window.scrollY / max, 1) : 0) + ')';
    var activeId = tocHeads.length ? tocHeads[0].id : null;
    for (var k = 0; k < tocHeads.length; k++) {
      if (tocHeads[k].getBoundingClientRect().top <= 76) activeId = tocHeads[k].id;
    }
    [].forEach.call(document.querySelectorAll('#page-toc a'), function (a) {
      a.classList.toggle('active', a.getAttribute('href') === '#' + activeId);
    });
  }
  window.addEventListener('scroll', function () {
    if (!ticking) { ticking = true; requestAnimationFrame(onScroll); }
  }, { passive: true });

  // --- pager ----------------------------------------------------------------
  function buildPager(i) {
    var pager = $('#pager');
    var prev = D.pages[i - 1], next = D.pages[i + 1];
    if (!prev && !next) { pager.hidden = true; return; }
    pager.hidden = false;
    pager.innerHTML =
      (prev
        ? '<a class="prev" href="#/p/' + (i - 1) + '"><span class="dir">← ' + (zh ? '上一页' : 'Previous') + '</span>' + esc(prev.title) + '</a>'
        : '<span></span>') +
      (next
        ? '<a class="next" href="#/p/' + (i + 1) + '"><span class="dir">' + (zh ? '下一页' : 'Next') + ' →</span>' + esc(next.title) + '</a>'
        : '');
  }

  // --- footer ----------------------------------------------------------------
  (function buildFooter() {
    var f = $('#site-footer');
    var date = (D.generatedAt || '').slice(0, 10);
    f.textContent = D.repo + ' · repowiki' + (date ? ' · ' + date : '');
    f.hidden = false;
  })();

  function openPage(i, push) {
    var page = D.pages[i];
    if (!page) return;
    current = i;
    var el = $('#content');
    el.innerHTML = marked.parse(page.md);
    enhanceCites(el);
    assignHeadingIds(el);
    enhanceCode();
    renderMermaid();
    buildToc();
    buildPager(i);
    document.title = page.title + ' · ' + D.repo;
    $('#crumb-page').textContent = page.title;
    [].forEach.call(document.querySelectorAll('#nav-tree a'), function (a) { a.classList.toggle('active', +a.getAttribute('data-page') === i); });
    expandChapter(i);
    closeSidebar();
    window.scrollTo(0, 0);
    onScroll();
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

  // --- search (with hit highlighting) ---------------------------------------
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
      var ctx = D.pages[i].md.slice(from, at + 60).replace(/\s+/g, ' ');
      var p = ctx.toLowerCase().indexOf(q);
      var shown = p === -1 ? esc(ctx)
        : esc(ctx.slice(0, p)) + '<mark>' + esc(ctx.slice(p, p + q.length)) + '</mark>' + esc(ctx.slice(p + q.length));
      hits.push({ i: i, ctx: shown });
    });
    box.innerHTML = hits.length
      ? hits.slice(0, 20).map(function (h) {
          return '<a class="search-hit" data-page="' + h.i + '" href="#/p/' + h.i + '"><b>' +
            esc(D.pages[h.i].title) + '</b><span>…' + h.ctx + '…</span></a>';
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
    var btn = ev.target.closest ? ev.target.closest('.nav-chapter') : null;
    if (btn) {
      var group = document.querySelector('#nav-tree .nav-children[data-chp="' + btn.getAttribute('data-ch') + '"]');
      if (group) {
        var open = group.hidden;
        group.hidden = !open;
        btn.setAttribute('aria-expanded', String(open));
        navState['c' + btn.getAttribute('data-ch')] = open ? '1' : '0';
        saveNavState();
      }
      return;
    }
    var a = ev.target.closest('a[data-page]');
    if (!a) return;
    ev.preventDefault();
    openPage(+a.getAttribute('data-page'));
  });
  function closeSidebar() { document.body.classList.remove('sidebar-open'); }

  buildNav();
  fromHash(true);
})();
