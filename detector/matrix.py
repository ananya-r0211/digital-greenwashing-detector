"""Build the Chemical Breakdown Matrix from matched ingredients."""
from dataclasses import dataclass

# tier -> (colour, label shown to the user)
TIERS = {
    "irritant": ("red", "May irritate or needs review"),
    "beneficial": ("green", "Documented benefit"),
    "unknown": ("yellow", "Not enough evidence"),
    "functional": ("grey", "Functional ingredient"),
}

UNMATCHED_NOTE = ("Not in our database yet, so it has not been judged. "
                  "Check a reliable source or add it to the database.")

_ANSI = {"red": "31", "green": "32", "yellow": "33", "grey": "90"}


@dataclass
class Row:
    position: int
    written: str
    matched: str
    tier: str
    colour: str
    label: str
    function: str
    chemistry: str
    note: str
    source: str
    reviewed: bool
    method: str
    score: float

    @property
    def needs_confirmation(self):
        return self.method == "fuzzy"


def build_matrix(matches):
    rows = []
    for m in matches:
        entry = m.entry
        if entry is None:
            tier = "unknown"
            colour, label = TIERS[tier]
            rows.append(Row(m.token.position, m.token.display, "", tier, colour, label,
                            "", "", UNMATCHED_NOTE, "", False, "none", 0.0))
            continue
        colour, label = TIERS[entry["tier"]]
        rows.append(Row(m.token.position, m.token.display, entry["inci"], entry["tier"],
                        colour, label, entry.get("function", ""), entry.get("chemistry", ""),
                        entry.get("skin_note", ""), entry.get("source", ""),
                        bool(entry.get("reviewed")), m.method, m.score))
    return rows


def summarise(rows):
    counts = {tier: 0 for tier in TIERS}
    for row in rows:
        counts[row.tier] += 1
    unmatched = sum(1 for row in rows if row.method == "none")
    to_confirm = sum(1 for row in rows if row.needs_confirmation)
    return {"total": len(rows), "counts": counts, "unmatched": unmatched, "to_confirm": to_confirm}


def render_text(rows, summary, ignored_tail="", colour=True):
    """Plain-text version of the matrix for the terminal."""
    def paint(text, name):
        return f"\033[{_ANSI[name]}m{text}\033[0m" if colour else text

    width = max([len(r.written) for r in rows] + [10])
    lines = [f"{'#':>2}  {'Ingredient':<{width}}  Result"]
    for r in rows:
        flag = f"  (fuzzy match to {r.matched}, please confirm)" if r.needs_confirmation else ""
        lines.append(f"{r.position:>2}  {r.written:<{width}}  {paint(r.label, r.colour)}{flag}")
    counts = summary["counts"]
    lines.append("")
    lines.append(f"{summary['total']} ingredients: "
                 f"{counts['irritant']} may irritate or need review, "
                 f"{counts['beneficial']} documented benefit, "
                 f"{counts['unknown']} not enough evidence, "
                 f"{counts['functional']} functional.")
    if ignored_tail:
        lines.append(f"Not analysed: {ignored_tail}")
    lines.append("Screening aid only. It reads the label and cannot test the product.")
    return "\n".join(lines)
