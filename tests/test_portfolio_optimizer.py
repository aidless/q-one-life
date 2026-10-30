import json
import tempfile
import unittest
from pathlib import Path

from qone_life.research_factory import optimize_portfolio


def _write_overlay(root: Path, name: str, claims: list[dict], gates: list[dict]) -> Path:
    overlay = root / name
    overlay.mkdir(parents=True, exist_ok=True)
    (overlay / "project.json").write_text(json.dumps({
        "schema": "q-one-research-project-v1",
        "claims": claims,
        "gate_receipts": gates,
    }), encoding="utf-8")
    return overlay


class OptimizerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_capacity_limits_selection(self):
        overlay = _write_overlay(self.root, "ov1", [
            {"claim_id": "C01", "state": "verified"},
            {"claim_id": "C02", "state": "blocked"},
        ], [{"state": "passed"}])
        portfolio = {"projects": [{"family_id": "f1", "title": "Paper One",
                                   "priority_band": "P1"}]}
        pilots = [{"title_contains_any": ["Paper One"], "overlay_path": str(overlay)}]
        result = optimize_portfolio(portfolio, pilots, capacity=1)
        self.assertEqual(result["schema"], "q-one-allocation-v1")
        self.assertEqual(len(result["ranked"]), 1)

    def test_empty_capacity_rejected(self):
        with self.assertRaises(ValueError):
            optimize_portfolio({"projects": []}, [], capacity=0)

    def test_roi_and_gap_computed(self):
        overlay = _write_overlay(self.root, "ov2", [
            {"claim_id": "C01", "state": "verified"},
            {"claim_id": "C02", "state": "candidate"},
        ], [])
        portfolio = {"projects": [{"family_id": "f2", "title": "Paper Two",
                                   "priority_band": "P2"}]}
        pilots = [{"title_contains_any": ["Paper Two"], "overlay_path": str(overlay)}]
        result = optimize_portfolio(portfolio, pilots, capacity=5)
        row = result["ranked"][0]
        self.assertEqual(row["verified"], 1)
        self.assertEqual(row["candidate"], 1)
        self.assertEqual(row["blocked"], 0)
        self.assertAlmostEqual(row["publishability"], 0.5)
        self.assertAlmostEqual(row["evidence_gap"], 0.5)

    def test_no_quality_score_in_output(self):
        overlay = _write_overlay(self.root, "ov3", [
            {"claim_id": "C01", "state": "verified"},
        ], [])
        portfolio = {"projects": [{"family_id": "f3", "title": "Paper Three"}]}
        pilots = [{"title_contains_any": ["Paper Three"], "overlay_path": str(overlay)}]
        result = optimize_portfolio(portfolio, pilots, capacity=3)
        self.assertNotIn("quality_score", json.dumps(result))
        self.assertIn("not a paper-quality", result["note"])

    def test_sorting_is_stable(self):
        overlays = []
        for index in range(3):
            overlays.append(_write_overlay(self.root, f"ov{index}", [
                {"claim_id": "C01", "state": "verified"},
            ], []))
        portfolio = {"projects": [
            {"family_id": f"f{index}", "title": f"Paper {index}"} for index in range(3)
        ]}
        pilots = [
            {"title_contains_any": [f"Paper {index}"], "overlay_path": str(overlays[index])}
            for index in range(3)
        ]
        first = optimize_portfolio(portfolio, pilots, capacity=3)
        second = optimize_portfolio(portfolio, pilots, capacity=3)
        self.assertEqual([r["family_id"] for r in first["ranked"]],
                         [r["family_id"] for r in second["ranked"]])

    def test_project_without_overlay_has_full_gap(self):
        portfolio = {"projects": [{"family_id": "f9", "title": "No Overlay"}]}
        result = optimize_portfolio(portfolio, [], capacity=5)
        row = result["ranked"][0]
        self.assertEqual(row["evidence_gap"], 1.0)
        self.assertEqual(row["publishability"], 0.0)


if __name__ == "__main__":
    unittest.main()
