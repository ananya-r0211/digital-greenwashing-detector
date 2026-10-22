"""Turn a raw ingredient-list string into clean ingredient tokens.

Phase 1 uses plain regular expressions and character scanning only.
No third-party libraries are needed.
"""
import re
import unicodedata
from dataclasses import dataclass, field

_PREFIX = re.compile(r"^\s*(?:ingredients?|inci|contains)\s*[:\-]\s*", re.IGNORECASE)
_TAIL_MARKER = re.compile(r"\bmay contain\b|\+/-", re.IGNORECASE)
_PERCENT = re.compile(r"\(?\s*\d+(?:[.,]\d+)?\s*%\s*\)?")
_MARKS = re.compile(r"[*\u2020\u2021\u00b9\u00b2]+")
_BRACKETED = re.compile(r"[\(\[]([^()\[\]]*)[\)\]]")
_BULLETS = str.maketrans({"\u2022": ",", "\u00b7": ",", "|": ","})


@dataclass
class Token:
    """One ingredient as written on the label."""
    position: int          # 1 = listed first (usually the largest amount)
    display: str           # cleaned text as written, for showing to the user
    name: str              # normalised main name used for matching
    alts: list = field(default_factory=list)   # normalised names found in brackets


@dataclass
class ParseResult:
    tokens: list
    ignored_tail: str = ""   # text after "may contain" or "+/-", not analysed in Phase 1


def normalize(text):
    """Lower-case, strip accents and punctuation, collapse spaces and hyphens."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"[\s\-]+", " ", text)
    return text.strip()


def _split_top_level(text, separators):
    """Split on separators that sit outside brackets, so 'Aqua (Water, Eau)' stays whole."""
    parts, buf, depth = [], [], 0
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch in separators and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def _make_token(chunk, position):
    chunk = _MARKS.sub(" ", _PERCENT.sub(" ", chunk))
    chunk = re.sub(r"\s+", " ", chunk).strip(" .:")
    if not chunk:
        return None
    alts = []
    for inner in _BRACKETED.findall(chunk):
        for piece in re.split(r"[,/]", inner):
            piece = normalize(piece)
            if piece:
                alts.append(piece)
    name = normalize(_BRACKETED.sub(" ", chunk))
    if not name and alts:
        name = alts.pop(0)
    if not name or name == "and":
        return None
    return Token(position=position, display=chunk, name=name, alts=alts)


def parse_ingredients(text):
    """Return a ParseResult with one Token per ingredient, in label order."""
    text = (text or "").translate(_BULLETS)
    text = _PREFIX.sub("", text, count=1)

    tail = ""
    marker = _TAIL_MARKER.search(text)
    if marker:
        tail = text[marker.start():].strip()
        text = text[:marker.start()]

    # Labels pasted from photos often wrap mid-name. Treat a newline as a
    # separator only when the list has no commas or semicolons at all.
    if "," in text or ";" in text:
        text = text.replace("\n", " ")
        separators = ",;"
    else:
        separators = "\n"

    tokens = []
    for chunk in _split_top_level(text, separators):
        token = _make_token(chunk, len(tokens) + 1)
        if token:
            tokens.append(token)
    return ParseResult(tokens=tokens, ignored_tail=tail)
