"""Capacity regression for a prospective runner; no games or project imports."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "paired22"


def load(name):
    spec = importlib.util.spec_from_file_location("paired22_" + name, EXP / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EvidenceCapacity(unittest.TestCase):
    def test_failed_series_prefix_has_room_for_next_decision(self):
        codec, bounds = load("codec"), load("bounds")
        self.assertEqual(codec.COMPRESSED_BYTES, 64 * 1024 * 1024)
        # Actual failed run: 1,680,704 compressed bytes after 7 pairs and
        # part of the eighth. The last recorded decision reserved 157,230 raw
        # bytes. The old 2.25 MiB cap rejected a similarly sized next call.
        used = 1_680_704
        upcoming = codec.compressed_upper(157_230, 6)
        with self.assertRaisesRegex(ValueError, "EVIDENCE_CAP_BEFORE_CALL"):
            bounds.reserve(used, upcoming, 2_359_296)
        bounds.reserve(used, upcoming, codec.COMPRESSED_BYTES)

    def test_finite_limit_still_vetoes_before_a_call(self):
        codec, bounds = load("codec"), load("bounds")
        with self.assertRaisesRegex(ValueError, "EVIDENCE_CAP_BEFORE_CALL"):
            bounds.reserve(codec.COMPRESSED_BYTES - bounds.TERMINAL_RESERVE,
                           1, codec.COMPRESSED_BYTES)


if __name__ == "__main__":
    unittest.main()
