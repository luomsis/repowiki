# Vendored JavaScript (inlined into the generated `wiki.html`)

Both libraries are MIT-licensed and inlined verbatim (minified UMD/IIFE
builds) so the generated viewer is fully offline and network-free.

| File | Library | Version | Source | License |
|---|---|---|---|---|
| `marked.min.js` | marked | 15.0.12 | <https://cdn.jsdelivr.net/npm/marked@15.0.12/marked.min.js> | MIT |
| `mermaid.min.js` | mermaid | 11.17.2 | <https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.min.js> | MIT |

Update = re-download the pinned version, keep the license header comment,
and bump the table above. `repowiki site` serves these files to the browser
via inline `<script>` tags; it never fetches anything at generation time or
view time.
