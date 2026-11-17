"""Mechanics 검사기 시험: python -m unittest discover tests"""
import copy
import json
import unittest

from stairs_agents.mechanics import validate
from stairs_agents.util import ROOT, extract_files


def replay_spec() -> dict:
    text = (ROOT / "replay" / "mechanics_spec.txt").read_text(encoding="utf-8")
    return json.loads(extract_files(text)["mechanics.json"])


class ValidateTest(unittest.TestCase):
    def test_replay_spec_passes(self):
        self.assertEqual(validate(replay_spec()), [])

    def test_changed_gdd_value_fails(self):
        spec = replay_spec()
        spec["config"]["parryWindow"]["value"] = 0.3
        self.assertTrue(any("parryWindow" in p for p in validate(spec)))

    def test_missing_floor_fails(self):
        spec = replay_spec()
        del spec["floors"][49]
        self.assertTrue(any("floors" in p for p in validate(spec)))

    def test_review_floor_with_attacks_fails(self):
        spec = replay_spec()
        spec["floors"][39]["attackInterval"] = 1.0
        self.assertTrue(any("40층" in p for p in validate(spec)))

    def test_threat_too_early_fails(self):
        spec = replay_spec()
        spec["floors"][4]["mix"] = {"phone": 1.0}
        self.assertTrue(any("phone" in p for p in validate(spec)))

    def test_unknown_threat_fails(self):
        spec = replay_spec()
        spec["threats"]["fake"] = copy.deepcopy(spec["threats"]["paper"])
        self.assertTrue(any("기획서에 없는 위협" in p for p in validate(spec)))

    def test_undecided_value_needs_reason(self):
        spec = replay_spec()
        del spec["config"]["stairsPerFloor"]["reason"]
        self.assertTrue(any("stairsPerFloor" in p for p in validate(spec)))


if __name__ == "__main__":
    unittest.main()
