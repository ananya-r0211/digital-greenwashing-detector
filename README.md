# Digital Greenwashing Detector, Phase 1 (30%)

Paste an ingredient list and get a Chemical Breakdown Matrix. Python 3.9 or newer. No packages to install.

## Run it

```
python app.py                         # web page at http://127.0.0.1:8000
python app.py --cli "Aqua, Parfum"    # terminal output
python app.py --file label.txt        # read the label from a file
python -m unittest discover -s tests  # run the tests
```

## Files

| File | Team role | Job |
|---|---|---|
| `detector/parser.py` | AI/ML | Regular-expression cleaning and splitting of the label text |
| `detector/matcher.py` | AI/ML and CSE | Exact, alias and fuzzy lookup against the database |
| `detector/matrix.py` | CSE Core | Builds the matrix rows, summary counts and terminal output |
| `app.py` | CSE Core | Local web page and command line |
| `data/ingredients.json` | Chemical Engineering and Biotechnology | Ingredient records (tier, function, chemistry, skin note, source) |
| `tests/test_phase1.py` | All | Checks for the parser, matcher and matrix |

## Before you demo

Every entry in `data/ingredients.json` is a draft with `"reviewed": false`. Chemical Engineering and Biotechnology should check each entry against a source, fill in the `source` field and set `reviewed` to `true`. The web page shows how many entries are reviewed.

## Phases

**Phase 1 (30%), this folder.** Manual text input, regex parser, 45-entry draft database, exact, alias and fuzzy matching, four-tier matrix (red, green, yellow, grey), unknown-ingredient handling, local web page, tests.

**Phase 2 (50%).** Grow the database to about 150 reviewed entries with an evidence-level field (lab, human trial, regulatory). Add the rule-based claim checker ("paraben-free", "sulfate-free", "natural", "fragrance-free") with three outcomes: supported, contradicted, cannot verify. Use list position as a rough concentration proxy. Move storage to SQLite and add report export.

**Phase 3 (100%).** OCR label scanning with manual correction. Product-level assessment engine (percentages, safety limits, likely harmful, likely not harmful or uncertain) with PostgreSQL and a REST API. Human review console, product comparison, testing against expert-reviewed products, deployment and final report.
