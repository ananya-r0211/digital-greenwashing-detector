"""Match parsed ingredient tokens against the curated ingredient database."""
import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from .parser import Token, normalize

FUZZY_CUTOFF = 0.90     # high on purpose: wrong guesses are worse than "unknown"
FUZZY_MIN_LENGTH = 6    # very short names are never fuzzy matched

VALID_TIERS = {"irritant", "beneficial", "unknown", "functional"}


@dataclass
class Match:
    token: Token
    entry: dict        # None when the ingredient is not in the database
    method: str        # "exact", "alias", "fuzzy" or "none"
    score: float       # 1.0 for exact and alias matches


class IngredientDB:
    def __init__(self, entries):
        self.entries = entries
        self._index = {}
        for entry in entries:
            if entry["tier"] not in VALID_TIERS:
                raise ValueError(f"{entry['inci']}: unknown tier {entry['tier']!r}")
            self._add(normalize(entry["inci"]), entry, "exact")
            for alias in entry.get("aliases", []):
                self._add(normalize(alias), entry, "alias")

    @classmethod
    def from_json(cls, path):
        with open(Path(path), encoding="utf-8") as handle:
            return cls(json.load(handle))

    def _add(self, key, entry, kind):
        existing = self._index.get(key)
        if existing and existing[0] is not entry:
            raise ValueError(f"'{key}' belongs to both {existing[0]['inci']} and {entry['inci']}")
        self._index.setdefault(key, (entry, kind))

    def lookup(self, token):
        candidates = [token.name, *token.alts]

        for name in candidates:
            hit = self._index.get(name)
            if hit:
                return Match(token, hit[0], hit[1], 1.0)

        best_entry, best_score = None, 0.0
        for name in candidates:
            if len(name) < FUZZY_MIN_LENGTH:
                continue
            for key, (entry, _kind) in self._index.items():
                score = SequenceMatcher(None, name, key).ratio()
                if score > best_score:
                    best_entry, best_score = entry, score
        if best_entry and best_score >= FUZZY_CUTOFF:
            return Match(token, best_entry, "fuzzy", round(best_score, 2))

        return Match(token, None, "none", 0.0)

    def stats(self):
        reviewed = sum(1 for e in self.entries if e.get("reviewed"))
        return {"entries": len(self.entries), "reviewed": reviewed}
