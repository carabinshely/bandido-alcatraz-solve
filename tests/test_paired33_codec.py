"""Focused synthetic evidence checks; no game or seed is evaluated."""

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch


CODEC = Path(__file__).resolve().parents[1] / "experiments/paired33/codec.py"
SPEC = importlib.util.spec_from_file_location("paired33_codec", CODEC)
codec = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(codec)


class CodecTests(TestCase):
    def test_complete_records_decode_with_exact_bytes(self):
        with TemporaryDirectory() as temporary:
            evidence = codec.Evidence(Path(temporary) / "evidence")
            evidence.write("a.json", {"text": "water", "value": 1})
            evidence.write("result.json", {"complete": True}, terminal=True)
            evidence.finish()
            encoded = (Path(temporary) / "evidence/records.gz").read_bytes()
        rows = codec.decode(encoded)
        self.assertEqual(rows["a.json"], codec.canonical({"text": "water", "value": 1}))
        self.assertEqual(rows["result.json"], codec.canonical({"complete": True}))
        with self.assertRaises(ValueError):
            codec.decode(encoded[:-1])

    def test_raw_cap_veto_precedes_new_frame(self):
        with TemporaryDirectory() as temporary, \
             patch.object(codec, "RAW_BYTES", 120), \
             patch.object(codec, "TERMINAL_RESERVE", 0):
            evidence = codec.Evidence(Path(temporary) / "evidence")
            evidence.write("first.json", {"value": "x"})
            with self.assertRaisesRegex(ValueError, "RAW_CAP_NO_TRUNCATION"):
                evidence.write("second.json", {"value": "x" * 200})
            evidence.write("failure.json", {"incomplete": True}, terminal=True)
            evidence.finish()
            rows = codec.decode((Path(temporary) / "evidence/records.gz").read_bytes())
            self.assertEqual(set(rows), {"first.json", "failure.json"})
