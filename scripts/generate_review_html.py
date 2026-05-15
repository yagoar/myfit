#!/usr/bin/env python3
"""Generate a static review.html from src/body_scanner/measure/definitions/merged.yaml.

The output is a single self-contained HTML file at the repository root. Open it
in a browser with file:// and the inline frame thumbnails render directly from
the LFS-checked-out images under references/dpm_videos/.

Each measurement is rendered as a card with:
  - canonical name, aliases, type, source_classification
  - the full parameters block as pretty YAML
  - the notes field
  - every source citation; frame citations get an inline thumbnail
  - a per-entry "Your notes" textarea backed by browser localStorage so the
    user can leave corrections / observations / new frame suggestions per
    measurement and export the lot as JSON when done.

Re-run after editing merged.yaml to refresh review.html. Existing browser
notes survive because they key off the measurement name, not the rendered
output.
"""
from __future__ import annotations

import re
from html import escape
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / "src" / "body_scanner" / "measure" / "definitions" / "merged.yaml"
OUT_PATH = ROOT / "review.html"

FRAME_RE = re.compile(r"(references/[^\s\"']+/frame_\d{2}h\d{2}m\d{2}s\.jpg)")


def render_source(text: str) -> str:
    """One citation line. If the text contains a frame path, also embed the image."""
    m = FRAME_RE.search(text)
    if not m:
        return f'<div class="source">{escape(text)}</div>'
    frame_path = m.group(1)
    return (
        '<div class="source frame">'
        f'<div class="cite">{escape(text)}</div>'
        f'<a href="{escape(frame_path)}" target="_blank" rel="noopener">'
        f'<img src="{escape(frame_path)}" loading="lazy" alt="{escape(frame_path)}">'
        "</a>"
        "</div>"
    )


def render_entry(m: dict) -> str:
    name = m["name"]
    rows: list[str] = [
        f'<section class="measurement" id="{escape(name)}" data-name="{escape(name)}">',
        f'<h2><a href="#{escape(name)}"><code>{escape(name)}</code></a></h2>',
        '<dl>',
    ]

    def add(label: str, value: str, *, html: bool = False) -> None:
        rows.append(f'<dt>{escape(label)}</dt>')
        rows.append('<dd>' + (value if html else escape(value)) + '</dd>')

    aliases = m.get("aliases") or []
    if aliases:
        add("aliases", ", ".join(str(a) for a in aliases))
    if "type" in m:
        add("type", str(m["type"]))
    if "source_classification" in m:
        add("source_classification", str(m["source_classification"]))
    if m.get("superseded_by"):
        add("superseded_by", str(m["superseded_by"]))
    if "parameters" in m:
        params_yaml = yaml.safe_dump(
            m["parameters"], sort_keys=False, default_flow_style=False, width=88
        )
        add("parameters", f"<pre>{escape(params_yaml.rstrip())}</pre>", html=True)
    notes = m.get("notes")
    if notes:
        add("notes (from yaml)", f'<pre class="from-yaml">{escape(notes.rstrip())}</pre>', html=True)
    if m.get("sources"):
        sources_html = "".join(render_source(s) for s in m["sources"])
        add("sources", f'<div class="sources">{sources_html}</div>', html=True)

    rows.append("</dl>")
    rows.append(
        '<label class="review-notes">'
        '<span class="lbl">Your review notes (saved in this browser)</span>'
        f'<textarea data-entry="{escape(name)}" rows="4" '
        'placeholder="corrections, frame suggestions, anything off…"></textarea>'
        "</label>"
    )
    rows.append("</section>")
    return "\n".join(rows)


def main() -> int:
    with YAML_PATH.open() as f:
        doc = yaml.safe_load(f)
    measurements = doc["measurements"]

    cards = "\n".join(render_entry(m) for m in measurements)

    page = PAGE_TEMPLATE.replace("__COUNT__", str(len(measurements))).replace(
        "__CARDS__", cards
    )
    OUT_PATH.write_text(page)
    print(f"wrote {OUT_PATH.relative_to(ROOT)}  ({len(measurements)} measurements)")
    print(f"open: file://{OUT_PATH}")
    return 0


PAGE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>merged.yaml review — __COUNT__ measurements</title>
<style>
  :root { color-scheme: light; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
         max-width: 1100px; margin: 0 auto; padding: 0 1rem 3rem; line-height: 1.45;
         color: #222; background: #fafafa; }
  header { position: sticky; top: 0; background: #fafafa; padding: 0.8rem 0 1rem;
           border-bottom: 2px solid #ccc; margin-bottom: 1rem; z-index: 10; }
  header h1 { margin: 0 0 0.4rem; font-size: 1.2rem; font-weight: 600; }
  header .controls { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
  input[type=search] { flex: 1; min-width: 220px; padding: 0.45rem 0.7rem;
                       font-size: 1rem; border: 1px solid #bbb; border-radius: 4px; }
  button { padding: 0.45rem 0.9rem; font-size: 0.95rem; border: 1px solid #888;
           background: #fff; border-radius: 4px; cursor: pointer; }
  button:hover { background: #eee; }
  section.measurement { background: #fff; padding: 1rem 1.2rem; margin-bottom: 1rem;
                        border: 1px solid #ddd; border-radius: 6px; scroll-margin-top: 6rem; }
  section.measurement h2 { margin: 0 0 0.7rem; font-size: 1.05rem; font-weight: 600; }
  section.measurement h2 a { color: inherit; text-decoration: none; }
  section.measurement h2 a:hover { text-decoration: underline; }
  section.measurement h2 code { background: #f0f0f0; padding: 0.1rem 0.3rem;
                                border-radius: 3px; font-size: 0.95rem; }
  dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.3rem 1rem; margin: 0; }
  dt { font-weight: 600; color: #555; font-size: 0.9rem; padding-top: 0.15rem; }
  dd { margin: 0; min-width: 0; }
  pre { background: #f6f6f6; padding: 0.5rem 0.7rem; border-radius: 4px;
        overflow-x: auto; font-size: 0.82rem; margin: 0; white-space: pre-wrap;
        word-break: break-word; }
  pre.from-yaml { background: #fcfaf2; }
  .sources { display: flex; flex-direction: column; gap: 0.6rem; }
  .source { font-size: 0.86rem; }
  .source.frame { display: flex; flex-direction: column; gap: 0.35rem;
                  padding: 0.4rem; background: #f3f7fb; border-radius: 4px; }
  .source.frame img { max-height: 240px; max-width: 100%;
                      border: 1px solid #bbb; border-radius: 4px; display: block; }
  .source .cite { font-family: ui-monospace, "SF Mono", Menlo, monospace;
                  font-size: 0.78rem; color: #444; }
  label.review-notes { display: block; margin-top: 0.9rem; padding-top: 0.7rem;
                        border-top: 1px dashed #ddd; }
  label.review-notes .lbl { font-weight: 600; color: #555; font-size: 0.9rem;
                            display: block; margin-bottom: 0.25rem; }
  textarea { width: 100%; min-height: 4rem; font-family: ui-monospace, monospace;
             font-size: 0.9rem; padding: 0.5rem; border: 1px solid #ccc;
             border-radius: 4px; box-sizing: border-box; resize: vertical;
             background: #fffef9; }
  textarea.has-content { background: #fff8e5; border-color: #d4a017; }
  section.hidden { display: none; }
  .count-pill { background: #ddd; padding: 0.1rem 0.5rem; border-radius: 999px;
                font-size: 0.85rem; }
</style>
</head>
<body>
<header>
  <h1>merged.yaml review · <span class="count-pill" id="visible-count">__COUNT__</span> measurements</h1>
  <div class="controls">
    <input type="search" id="filter" placeholder="filter by measurement name (e.g. waist, sleeve, crotch)…">
    <button id="export">export notes (JSON)</button>
    <button id="export-md">export as markdown</button>
    <button id="clear">clear all notes</button>
  </div>
</header>
<main>
__CARDS__
</main>
<script>
const STORAGE_KEY = 'merged_yaml_review_notes_v1';

function readAll() { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
function writeAll(obj) { localStorage.setItem(STORAGE_KEY, JSON.stringify(obj)); }

const all = readAll();
document.querySelectorAll('textarea[data-entry]').forEach(ta => {
  const key = ta.dataset.entry;
  if (all[key]) {
    ta.value = all[key];
    ta.classList.add('has-content');
  }
  ta.addEventListener('input', () => {
    const cur = readAll();
    if (ta.value.trim()) { cur[key] = ta.value; ta.classList.add('has-content'); }
    else { delete cur[key]; ta.classList.remove('has-content'); }
    writeAll(cur);
  });
});

const filterEl = document.getElementById('filter');
const visibleCountEl = document.getElementById('visible-count');
filterEl.addEventListener('input', () => {
  const q = filterEl.value.toLowerCase().trim();
  let visible = 0;
  document.querySelectorAll('section.measurement').forEach(s => {
    const match = !q || s.dataset.name.toLowerCase().includes(q);
    s.classList.toggle('hidden', !match);
    if (match) visible++;
  });
  visibleCountEl.textContent = visible;
});

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 0);
}

document.getElementById('export').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify(readAll(), null, 2)], { type: 'application/json' });
  downloadBlob(blob, 'merged_yaml_review_notes.json');
});

document.getElementById('export-md').addEventListener('click', () => {
  const all = readAll();
  const lines = ['# merged.yaml review notes', ''];
  for (const [name, note] of Object.entries(all)) {
    lines.push('## ' + name);
    lines.push('');
    lines.push(note.trim());
    lines.push('');
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
  downloadBlob(blob, 'merged_yaml_review_notes.md');
});

document.getElementById('clear').addEventListener('click', () => {
  if (!confirm('Clear all your review notes from this browser?')) return;
  localStorage.removeItem(STORAGE_KEY);
  document.querySelectorAll('textarea[data-entry]').forEach(ta => {
    ta.value = ''; ta.classList.remove('has-content');
  });
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
