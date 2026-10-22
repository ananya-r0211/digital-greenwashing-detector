import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from detector.matcher import IngredientDB
from detector.matrix import build_matrix, summarise
from detector.parser import parse_ingredients

DB = IngredientDB.from_json(Path(__file__).resolve().parents[1] / "data" / "ingredients.json")


def rows_for(text):
    parsed = parse_ingredients(text)
    return build_matrix([DB.lookup(t) for t in parsed.tokens])


class ParserTests(unittest.TestCase):
    def test_brackets_keep_commas_inside(self):
        result = parse_ingredients("Aqua (Water, Eau), Glycerin")
        self.assertEqual([t.name for t in result.tokens], ["aqua", "glycerin"])
        self.assertIn("water", result.tokens[0].alts)
        self.assertIn("eau", result.tokens[0].alts)

    def test_percentages_removed(self):
        result = parse_ingredients("Aqua 70%, Glycerin (5%)")
        self.assertEqual([t.name for t in result.tokens], ["aqua", "glycerin"])

    def test_prefix_removed(self):
        result = parse_ingredients("Ingredients: Aqua, Glycerin")
        self.assertEqual(len(result.tokens), 2)

    def test_may_contain_not_analysed(self):
        result = parse_ingredients("Aqua, Glycerin, May contain: CI 77891")
        self.assertEqual(len(result.tokens), 2)
        self.assertTrue(result.ignored_tail.lower().startswith("may contain"))

    def test_wrapped_name_is_rejoined(self):
        result = parse_ingredients("Aqua, Sodium Lauryl\nSulfate, Glycerin")
        self.assertEqual(result.tokens[1].name, "sodium lauryl sulfate")

    def test_one_per_line_without_commas(self):
        result = parse_ingredients("Aqua\nGlycerin\nParfum")
        self.assertEqual(len(result.tokens), 3)

    def test_positions_follow_label_order(self):
        result = parse_ingredients("Aqua, Glycerin, Parfum")
        self.assertEqual([t.position for t in result.tokens], [1, 2, 3])


class MatcherTests(unittest.TestCase):
    def test_database_loads_without_alias_clashes(self):
        self.assertGreater(DB.stats()["entries"], 30)

    def test_alias_and_british_spelling(self):
        for text in ("SLS", "Sodium Lauryl Sulphate"):
            row = rows_for(text)[0]
            self.assertEqual(row.matched, "Sodium Lauryl Sulfate")
            self.assertEqual(row.tier, "irritant")

    def test_bracketed_common_name_matches(self):
        row = rows_for("Butyrospermum Parkii (Shea) Butter")[0]
        self.assertEqual(row.matched, "Butyrospermum Parkii Butter")
        self.assertEqual(row.method, "exact")

    def test_unknown_is_yellow_not_red(self):
        row = rows_for("Xanthan Gum")[0]
        self.assertEqual(row.tier, "unknown")
        self.assertEqual(row.colour, "yellow")
        self.assertEqual(row.method, "none")

    def test_typo_is_fuzzy_and_needs_confirmation(self):
        row = rows_for("Sodium Lauryl Sulfat")[0]
        self.assertEqual(row.method, "fuzzy")
        self.assertTrue(row.needs_confirmation)

    def test_short_names_are_never_fuzzy_matched(self):
        self.assertEqual(rows_for("Salz")[0].method, "none")


class MatrixTests(unittest.TestCase):
    def test_summary_counts(self):
        rows = rows_for("Aqua, Sodium Lauryl Sulfate, Aloe Vera, Xanthan Gum")
        summary = summarise(rows)
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["counts"]["irritant"], 1)
        self.assertEqual(summary["counts"]["beneficial"], 1)
        self.assertEqual(summary["counts"]["functional"], 1)
        self.assertEqual(summary["counts"]["unknown"], 1)
        self.assertEqual(summary["unmatched"], 1)

    def test_paraben_is_not_red(self):
        row = rows_for("Methylparaben")[0]
        self.assertEqual(row.tier, "functional")


if __name__ == "__main__":
    unittest.main()
