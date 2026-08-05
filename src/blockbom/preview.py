"""Live preview server for `blockbom watch`."""

import json
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .exceptions import BlockBomError
from .export import emit_mermaid
from .project import load_project, validate_project
from .rollup import consolidated_bom, project_rollup

POLL_INTERVAL_S = 0.5

PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>blockbom preview</title>
<style>
  body { font-family: -apple-system, system-ui, sans-serif; margin: 0; padding: 1.5rem;
         background: #fafafa; color: #1a1a1a; }
  h1 { font-size: 1.3rem; margin: 0 0 0.25rem; }
  .stamp { color: #777; font-size: 0.8rem; margin-bottom: 1rem; }
  .totals { display: flex; gap: 2rem; margin-bottom: 1rem; }
  .totals div { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
                padding: 0.6rem 1rem; }
  .totals .label { color: #777; font-size: 0.75rem; text-transform: uppercase; }
  .totals .value { font-size: 1.2rem; font-weight: 600; }
  .error { background: #fdecea; border: 1px solid #f5c6cb; color: #9c2b23;
           border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1rem;
           white-space: pre-wrap; font-family: ui-monospace, monospace; font-size: 0.85rem; }
  #diagram { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
             padding: 1rem; margin-bottom: 1.5rem; overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; background: #fff;
          border: 1px solid #e0e0e0; border-radius: 8px; }
  th, td { text-align: left; padding: 0.45rem 0.8rem; border-bottom: 1px solid #eee;
           font-size: 0.85rem; }
  th { background: #f4f4f4; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
<h1 id="name">blockbom</h1>
<div class="stamp" id="stamp"></div>
<div id="errors"></div>
<div class="totals">
  <div><div class="label">Total cost</div><div class="value" id="cost">–</div></div>
  <div><div class="label">Total weight</div><div class="value" id="weight">–</div></div>
  <div><div class="label">Parts</div><div class="value" id="parts">–</div></div>
</div>
<div id="diagram">Loading diagram…</div>
<table>
  <thead><tr><th>Part Number</th><th>Name</th><th class="num">Qty</th>
  <th>Supplier</th><th class="num">Unit Cost</th><th class="num">Ext Cost</th></tr></thead>
  <tbody id="bom"></tbody>
</table>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
mermaid.initialize({ startOnLoad: false });
let version = null;
async function refresh() {
  try {
    const res = await fetch('/data.json');
    const data = await res.json();
    if (data.version === version) return;
    version = data.version;
    document.getElementById('name').textContent = data.name;
    document.getElementById('stamp').textContent = data.stamp;
    document.getElementById('cost').textContent = data.summary.cost;
    document.getElementById('weight').textContent = data.summary.weight;
    document.getElementById('parts').textContent = data.summary.parts;
    const errors = document.getElementById('errors');
    errors.innerHTML = '';
    for (const problem of data.problems) {
      const div = document.createElement('div');
      div.className = 'error';
      div.textContent = problem;
      errors.appendChild(div);
    }
    const bom = document.getElementById('bom');
    bom.innerHTML = '';
    for (const row of data.bom) {
      const tr = document.createElement('tr');
      for (const [i, cell] of row.entries()) {
        const td = document.createElement('td');
        if ([2, 4, 5].includes(i)) td.className = 'num';
        td.textContent = cell;
        tr.appendChild(td);
      }
      bom.appendChild(tr);
    }
    const { svg } = await mermaid.render('mermaid-svg-' + Date.now(), data.mermaid);
    document.getElementById('diagram').innerHTML = svg;
  } catch (err) {
    console.error(err);
  }
}
refresh();
setInterval(refresh, 1000);
</script>
</body>
</html>
"""


@dataclass
class PreviewState:
    """Shared state between the file watcher and the HTTP handler."""

    data: dict[str, Any]
    lock: threading.Lock = field(default_factory=threading.Lock)

    def get(self) -> dict[str, Any]:
        with self.lock:
            return self.data

    def set(self, data: dict[str, Any]) -> None:
        with self.lock:
            self.data = data


def build_preview_data(path: Path, version: float) -> dict[str, Any]:
    """Build the /data.json payload for the current file contents.

    On load errors, returns the error text with no diagram/BOM so the page
    can keep showing the last good render alongside the error.
    """
    try:
        project = load_project(path)
    except (BlockBomError, OSError) as e:
        return {
            "version": version,
            "name": path.name,
            "stamp": "",
            "problems": [str(e)],
            "summary": {"cost": "–", "weight": "–", "parts": "–"},
            "bom": [],
            "mermaid": 'flowchart TD\n    error["project failed to load"]',
        }

    problems = validate_project(project)
    rollup = project_rollup(project)

    def money(total: float, complete: bool) -> str:
        return f"{total:,.2f}" if complete else f">= {total:,.2f} (incomplete)"

    return {
        "version": version,
        "name": project.name,
        "stamp": f"{path} — saved {time.strftime('%H:%M:%S', time.localtime(version))}",
        "problems": problems,
        "summary": {
            "cost": money(rollup.total_cost, rollup.cost_complete),
            "weight": money(rollup.total_weight_g, rollup.weight_complete) + " g",
            "parts": str(rollup.part_count),
        },
        "bom": [
            [
                row.part_number,
                row.name,
                str(row.total_qty),
                row.supplier,
                f"{row.unit_cost:.2f}" if row.unit_cost is not None else "",
                f"{row.extended_cost:.2f}" if row.extended_cost is not None else "",
            ]
            for row in consolidated_bom(project)
        ],
        "mermaid": emit_mermaid(project),
    }


def _make_handler(state: PreviewState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            if self.path == "/":
                body = PAGE.encode("utf-8")
                content_type = "text/html; charset=utf-8"
            elif self.path == "/data.json":
                body = json.dumps(state.get()).encode("utf-8")
                content_type = "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            pass  # keep the terminal quiet; the watcher prints changes

    return Handler


def serve_preview(
    path: Path | str,
    port: int = 8351,
    open_browser: bool = True,
) -> None:
    """Serve the live preview until interrupted (blocking)."""
    path = Path(path)
    version = path.stat().st_mtime
    state = PreviewState(build_preview_data(path, version))

    server = ThreadingHTTPServer(("127.0.0.1", port), _make_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Watching {path} — preview at {url} (Ctrl-C to stop)")
    if open_browser:
        webbrowser.open(url)

    try:
        while True:
            time.sleep(POLL_INTERVAL_S)
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime != version:
                version = mtime
                state.set(build_preview_data(path, version))
                print(f"Reloaded {path} at {time.strftime('%H:%M:%S')}")
    except KeyboardInterrupt:
        print("\nStopping preview")
    finally:
        server.shutdown()
