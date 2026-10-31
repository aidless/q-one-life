"""Observation confidence/corrected_by tests."""
import unittest

from qone_life.models import LifeValidationError, Observation


class ObservationConfidenceTests(unittest.TestCase):
    def test_observation_with_confidence(self):
        o = Observation.from_payload({
            "domain": "energy", "metric": "sleep_quality", "value": 7,
            "minimum": 0, "maximum": 10, "observed_at": "2026-10-30T00:00:00Z",
            "source": "watch", "confidence": 0.9,
        })
        self.assertEqual(o.confidence, 0.9)
        self.assertIsNone(o.corrected_by)

    def test_observation_with_correction(self):
        o = Observation.from_payload({
            "domain": "energy", "metric": "sleep_quality", "value": 7,
            "minimum": 0, "maximum": 10, "observed_at": "2026-10-30T00:00:00Z",
            "source": "watch", "confidence": 0.6, "corrected_by": "manual-entry",
        })
        self.assertEqual(o.confidence, 0.6)
        self.assertEqual(o.corrected_by, "manual-entry")

    def test_confidence_defaults_none(self):
        o = Observation.from_payload({
            "domain": "energy", "metric": "sleep_quality", "value": 7,
            "minimum": 0, "maximum": 10, "observed_at": "2026-10-30T00:00:00Z",
            "source": "watch",
        })
        self.assertIsNone(o.confidence)
        self.assertIsNone(o.corrected_by)

    def test_confidence_out_of_range_rejected(self):
        with self.assertRaises(LifeValidationError):
            Observation.from_payload({
                "domain": "energy", "metric": "sleep_quality", "value": 7,
                "minimum": 0, "maximum": 10, "observed_at": "2026-10-30T00:00:00Z",
                "source": "watch", "confidence": 1.5,
            })

    def test_confidence_boolean_rejected(self):
        with self.assertRaises(LifeValidationError):
            Observation.from_payload({
                "domain": "energy", "metric": "sleep_quality", "value": 7,
                "minimum": 0, "maximum": 10, "observed_at": "2026-10-30T00:00:00Z",
                "source": "watch", "confidence": True,
            })

    def test_corrected_by_blank_rejected(self):
        with self.assertRaises(LifeValidationError):
            Observation.from_payload({
                "domain": "energy", "metric": "sleep_quality", "value": 7,
                "minimum": 0, "maximum": 10, "observed_at": "2026-10-30T00:00:00Z",
                "source": "watch", "corrected_by": "   ",
            })

    def test_to_dict_roundtrip(self):
        o = Observation.from_payload({
            "domain": "energy", "metric": "sleep_quality", "value": 7,
            "minimum": 0, "maximum": 10, "observed_at": "2026-10-30T00:00:00Z",
            "source": "watch", "confidence": 0.9, "corrected_by": "manual-entry",
        })
        d = o.to_dict()
        self.assertEqual(d["confidence"], 0.9)
        self.assertEqual(d["corrected_by"], "manual-entry")
        o2 = Observation.from_payload(d)
        self.assertEqual(o2, o)


if __name__ == "__main__":
    unittest.main()
