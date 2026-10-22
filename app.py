"""Digital Greenwashing Detector, Phase 1 (30%).

Paste an ingredient list and get the Chemical Breakdown Matrix.

    python app.py                      start the web page at http://127.0.0.1:8000
    python app.py --cli "Aqua, ..."    print the matrix in the terminal
    python app.py --file label.txt     read the label from a text file
"""
import argparse
import html
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from detector.matcher import IngredientDB
from detector.matrix import TIERS, build_matrix, render_text, summarise
from detector.parser import parse_ingredients

ROOT = Path(__file__).parent
DB = IngredientDB.from_json(ROOT / "data" / "ingredients.json")

SAMPLES = {
    "Shampoo label": ("Aqua, Sodium Laureth Sulfate, Cocamidopropyl Betaine, Parfum, Methylparaben, "
                      "Propylparaben, Glycerin, Citric Acid, Sodium Chloride, "
                      "Camellia Sinensis Leaf Extract (Green Tea), Disodium EDTA, Limonene, Linalool"),
    "Cream that says natural": ("Aqua (Water), Aloe Barbadensis Leaf Juice, Butyrospermum Parkii (Shea) Butter, "
                                "Glycerin, Cetearyl Alcohol, Tocopherol, Melaleuca Alternifolia (Tea Tree) Leaf Oil, "
                                "Phenoxyethanol, Parfum, Xanthan Gum, Sodium Hyaluronate"),
}


def analyse(text):
    parsed = parse_ingredients(text)
    matches = [DB.lookup(token) for token in parsed.tokens]
    rows = build_matrix(matches)
    return rows, summarise(rows), parsed.ignored_tail


# ---------------------------------------------------------------- web page

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ingredient label check</title>
<style>
:root {
  --bg: #f4f6f5; --panel: #ffffff; --ink: #14262b; --muted: #55656b; --rule: #c9d3d0;
  --red: #b3372b; --green: #2f7a4d; --yellow: #a8700f; --grey: #66737a; --focus: #1b5e8a;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f1a1d; --panel: #16252a; --ink: #e6eeec; --muted: #9fb0b4; --rule: #2b3f45;
    --red: #e0766b; --green: #6cc08b; --yellow: #e0b25a; --grey: #9aa7ad; --focus: #7cc0ea;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 16px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 960px; margin: 0 auto; padding: 32px 20px 64px; }
h1 { font: 700 2rem/1.15 Georgia, "Times New Roman", serif; margin: 0 0 8px; }
h2 { font: 700 1.25rem/1.3 Georgia, "Times New Roman", serif; margin: 32px 0 12px; }
p.lead { margin: 0 0 24px; color: var(--muted); max-width: 62ch; }
label { display: block; font-weight: 600; margin-bottom: 6px; }
textarea { width: 100%; min-height: 130px; padding: 12px; font: inherit; color: var(--ink);
  background: var(--panel); border: 1px solid var(--rule); border-radius: 6px; resize: vertical; }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; align-items: center; }
button { font: inherit; cursor: pointer; padding: 9px 16px; border-radius: 6px;
  border: 1px solid var(--rule); background: var(--panel); color: var(--ink); }
button.primary { background: var(--ink); color: var(--bg); border-color: var(--ink); font-weight: 600; }
.strip { display: flex; height: 22px; border-radius: 4px; overflow: hidden; margin: 12px 0 8px;
  border: 1px solid var(--rule); }
.strip span { min-width: 6px; background: var(--c); }
.legend { display: flex; flex-wrap: wrap; gap: 6px 20px; margin: 0; padding: 0; list-style: none; }
.legend li::before { content: ""; display: inline-block; width: 10px; height: 10px; margin-right: 6px;
  background: var(--c); border-radius: 2px; }
.t-irritant { --c: var(--red); } .t-beneficial { --c: var(--green); }
.t-unknown { --c: var(--yellow); } .t-functional { --c: var(--grey); }
.scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--rule); }
th, td { text-align: left; padding: 10px 12px; vertical-align: top; border-bottom: 1px solid var(--rule); }
th { font-weight: 600; color: var(--muted); }
td.pos { width: 3rem; color: var(--muted); border-left: 5px solid var(--c); }
td.result { font-weight: 600; color: var(--c); white-space: nowrap; }
.sub { display: block; color: var(--muted); font-size: 0.875rem; }
details summary { cursor: pointer; color: var(--focus); }
details dl { margin: 8px 0 0; font-size: 0.9rem; }
details dt { font-weight: 600; margin-top: 6px; }
details dd { margin: 0; color: var(--muted); max-width: 60ch; }
.note { margin-top: 20px; padding: 12px 14px; border: 1px solid var(--rule); border-radius: 6px;
  background: var(--panel); color: var(--muted); font-size: 0.9rem; }
.empty { color: var(--muted); }
</style>
</head>
<body>
<main>
  <h1>Ingredient label check</h1>
  <p class="lead">Paste the ingredient list from a soap, shampoo or cream. We match each ingredient
  against our database and show what it does and whether it needs a closer look.</p>

  <form method="post" action="/">
    <label for="ingredients">Ingredient list</label>
    <textarea id="ingredients" name="ingredients" placeholder="Aqua, Sodium Laureth Sulfate, Glycerin, Parfum">{{TEXT}}</textarea>
    <div class="actions">
      <button class="primary" type="submit">Check ingredients</button>
      {{SAMPLE_BUTTONS}}
    </div>
  </form>

  {{RESULTS}}

  <p class="note">This is a screening aid built from the printed label. It cannot test a product or
  find contaminants, and it is not medical advice. {{DB_STATUS}}</p>
</main>
<script>
document.querySelectorAll("[data-sample]").forEach(function (btn) {
  btn.addEventListener("click", function () {
    document.getElementById("ingredients").value = btn.dataset.sample;
  });
});
</script>
</body>
</html>
"""


def _e(value):
    return html.escape(str(value), quote=True)


def render_results(rows, summary, tail):
    if not rows:
        return '<p class="empty">No ingredients found. Paste a list separated by commas.</p>'

    counts = summary["counts"]
    strip = "".join(f'<span class="t-{t}" style="flex:{n}"></span>' for t, n in counts.items() if n)
    legend = "".join(f'<li class="t-{t}">{_e(TIERS[t][1])}: {counts[t]}</li>' for t in TIERS)

    body = []
    for r in rows:
        name = _e(r.matched or r.written)
        sub = ""
        if r.matched and r.written.lower() != r.matched.lower():
            sub = f'<span class="sub">written as {_e(r.written)}</span>'
        if r.needs_confirmation:
            sub += f'<span class="sub">Close match ({int(r.score * 100)}%), please confirm</span>'
        details = []
        if r.chemistry:
            details.append(f"<dt>Chemistry</dt><dd>{_e(r.chemistry)}</dd>")
        details.append(f"<dt>Skin and evidence</dt><dd>{_e(r.note)}</dd>")
        source = r.source or "Source pending"
        if r.source and not r.reviewed:
            source += " (entry not yet reviewed by the team)"
        details.append(f"<dt>Source</dt><dd>{_e(source)}</dd>")
        body.append(
            f'<tr class="t-{r.tier}">'
            f'<td class="pos">{r.position}</td>'
            f'<td>{name}{sub}</td>'
            f'<td class="result">{_e(r.label)}</td>'
            f'<td>{_e(r.function)}</td>'
            f'<td><details><summary>Details</summary><dl>{"".join(details)}</dl></details></td>'
            f"</tr>")

    extra = ""
    if tail:
        extra = f'<p class="note">Not analysed in this version: {_e(tail)}</p>'
    if summary["unmatched"]:
        extra += (f'<p class="note">{summary["unmatched"]} ingredient(s) are not in the database yet. '
                  "They are shown as not enough evidence and have not been judged.</p>")

    return (
        "<h2>Chemical Breakdown Matrix</h2>"
        f'<div class="strip" role="img" aria-label="Share of ingredients by result">{strip}</div>'
        f'<ul class="legend">{legend}</ul>'
        '<div class="scroll"><table><thead><tr><th>#</th><th>Ingredient</th><th>Result</th>'
        "<th>What it does</th><th></th></tr></thead>"
        f'<tbody>{"".join(body)}</tbody></table></div>{extra}')


def render_page(text="", rows=None, summary=None, tail=""):
    stats = DB.stats()
    db_status = (f"Database: {stats['entries']} entries, {stats['reviewed']} reviewed against sources "
                 "so far.")
    buttons = "".join(f'<button type="button" data-sample="{_e(v)}">{_e(k)}</button>'
                      for k, v in SAMPLES.items())
    results = render_results(rows, summary, tail) if rows is not None else ""
    return (PAGE.replace("{{TEXT}}", _e(text)).replace("{{SAMPLE_BUTTONS}}", buttons)
            .replace("{{RESULTS}}", results).replace("{{DB_STATUS}}", _e(db_status)))


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, status=200):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(render_page())

    def do_POST(self):
        length = min(int(self.headers.get("Content-Length", 0)), 20000)
        form = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
        text = form.get("ingredients", [""])[0]
        rows, summary, tail = analyse(text)
        self._send(render_page(text, rows, summary, tail))

    def log_message(self, fmt, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="Digital Greenwashing Detector, Phase 1")
    parser.add_argument("--cli", metavar="TEXT", help="analyse this ingredient list in the terminal")
    parser.add_argument("--file", metavar="PATH", help="analyse the ingredient list in this text file")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    text = args.cli
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    if text is not None:
        rows, summary, tail = analyse(text)
        print(render_text(rows, summary, tail, colour=sys.stdout.isatty()))
        return

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Running at http://127.0.0.1:{args.port}  (press Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
