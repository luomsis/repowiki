# Wiki viewer: single-file offline HTML with embedded rendering libraries

[中文](../../zh/adr/0002-single-file-offline-site.md) | **English**

v0.2.0's Non-Goals explicitly excluded an "HTML preview service". After users asked for
"a web page to view the generated docs conveniently", we chose to generate **one
self-contained HTML file** via a separate command `repowiki site` after `finalize`
(`<locale>/wiki.html`): all pages, the referenced source line ranges, the markdown
rendering library (marked), and the mermaid rendering library are all embedded in the
file — double-click to view in a browser, zero servers, zero network, one file to
share. This decision withdrew the original Non-Goal: the point of the exclusion was "no
resident service", and a static single-file artifact doesn't violate that intent, so
the Non-Goals wording became "no resident preview server".

## Considered Options

- **A local server `repowiki serve`**: feels more like "a website", but the terminal
  must stay resident, background processes are awkward on Windows, and the artifact is
  less shareable than a single file;
- **Render markdown in Python (e.g. mistune)**: smaller artifact, but a new runtime
  dependency, and mermaid still needs a browser or a CDN — the offline story is
  incomplete;
- **Reference the rendering libraries from a CDN**: zero bytes, but
  markdown/mermaid won't render when opened offline — conflicts with the tool's
  offline-install positioning.

## Consequences

- Each generated wiki.html is about 4-5 MB (embedded mermaid ~3.5 MB) — acceptable for
  one repository's documentation; the vendored minified JS is committed to the repo and
  shipped with the wheel (see `src/repowiki/vendor/README.md`).
- Site generation is a pure derived artifact: idempotent and re-runnable anytime; it
  can still rebuild from the on-disk pages after `repowiki clean` deletes state/
  (section order degrades to directory order).
- The established design of deliberately zero cross-page links is unchanged — the
  site's navigation derives from the catalog tree, not from page-to-page links.
