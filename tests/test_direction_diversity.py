import tempfile
import unittest
from pathlib import Path

from qone_life.research_factory.direction_diversity import (
    DiversityError,
    rank_with_diversity,
    write_direction_allocation,
)


class DiversityTests(unittest.TestCase):
    def test_capacity_validation(self):
        with self.assertRaises(DiversityError):
            rank_with_diversity([{"family_id": "a", "roi": 1.0}], 0)

    def test_missing_roi_rejected(self):
        with self.assertRaises(DiversityError):
            rank_with_diversity([{"family_id": "a"}], 1)

    def test_bonus_favors_under_tried_direction(self):
        items = [
            {"family_id": "a1", "roi": 0.9, "direction": "A"},
            {"family_id": "a2", "roi": 0.88, "direction": "A"},
            {"family_id": "b1", "roi": 0.80, "direction": "B"},
        ]
        report = rank_with_diversity(
            items, 2, exploration_bonus=0.2, open_cost=0.0
        )
        self.assertEqual([x["family_id"] for x in report["selected"]], ["a1", "b1"])
        self.assertEqual(report["directions"], {"A": 1, "B": 1})

    def test_without_bonus_roi_wins(self):
        items = [
            {"family_id": "a1", "roi": 0.9, "direction": "A"},
            {"family_id": "a2", "roi": 0.88, "direction": "A"},
            {"family_id": "b1", "roi": 0.80, "direction": "B"},
        ]
        report = rank_with_diversity(
            items, 2, exploration_bonus=0.0, open_cost=0.0
        )
        self.assertEqual([x["family_id"] for x in report["selected"]], ["a1", "a2"])

    def test_skipped_recorded(self):
        items = [
            {"family_id": f"f{i}", "roi": 1.0 - i / 10, "direction": "A"}
            for i in range(4)
        ]
        report = rank_with_diversity(items, 2)
        self.assertEqual(len(report["skipped"]), 2)

    def test_write_report(self):
        report = rank_with_diversity([{"family_id": "a", "roi": 0.5}], 1)
        with tempfile.TemporaryDirectory() as tmp:
            written = write_direction_allocation(report, Path(tmp) / "a.json")
            self.assertTrue(Path(written["path"]).is_file())


if __name__ == "__main__":
    unittest.main()
