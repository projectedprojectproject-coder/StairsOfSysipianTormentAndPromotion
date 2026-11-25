"""Mechanics 검사기와 루프 하네스 시험: python -m unittest discover tests"""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from stairs_agents.harness.core import Budget, Evaluation, Issue, Ledger, LoopRunner, Role
from stairs_agents.mechanics import load_rules, repair, validate
from stairs_agents.sim import reach_rates
from stairs_agents.util import ROOT, Paths, extract_files

RULES = load_rules(Paths())


def replay_spec() -> dict:
    text = (ROOT / "replay" / "mechanics_spec.txt").read_text(encoding="utf-8")
    return json.loads(extract_files(text)["mechanics.json"])


def targets(spec, sev="high"):
    return [p["target"] for p in validate(spec, RULES) if p["severity"] == sev]


class ValidateTest(unittest.TestCase):
    def test_replay_spec_passes(self):
        self.assertEqual(validate(replay_spec(), RULES), [])

    def test_changed_fixed_value_fails(self):
        spec = replay_spec()
        spec["config"]["parryWindow"]["value"] = 0.3
        self.assertIn("config.parryWindow", targets(spec))

    def test_missing_floor_fails(self):
        spec = replay_spec()
        del spec["floors"][49]
        self.assertIn("floors", targets(spec))

    def test_review_floor_with_attacks_fails(self):
        spec = replay_spec()
        spec["floors"][79]["attackInterval"] = 1.0
        self.assertIn("floors.80", targets(spec))

    def test_threat_too_early(self):
        spec = replay_spec()
        spec["floors"][4]["mix"]["briefcase"] = 1.0
        self.assertIn("floors.5.mix", targets(spec, "mid"))

    def test_unknown_threat_fails(self):
        spec = replay_spec()
        spec["threats"]["fake"] = copy.deepcopy(spec["threats"]["paper"])
        self.assertIn("threats.fake", targets(spec))

    def test_motivation_required(self):
        spec = replay_spec()
        del spec["motivation"]["ghost"]
        self.assertIn("motivation.ghost", targets(spec))

    def test_preview_must_expire(self):
        spec = replay_spec()
        spec["bm"]["preview"][0]["permanent"] = True
        self.assertIn("bm.preview.pv_ceo_badge", targets(spec))

    def test_paid_tier_must_be_free_league(self):
        spec = replay_spec()
        spec["bm"]["assist"][3]["league"] = "main"
        self.assertIn("bm.assist.as_intern", targets(spec))

    def test_revive_total_limit(self):
        spec = replay_spec()
        spec["bm"]["assist"][2]["effect"]["extraRevive"] = 2
        self.assertIn("bm.assist", targets(spec))

    def test_unknown_assist_effect(self):
        spec = replay_spec()
        spec["bm"]["assist"][0]["effect"]["parryWindow"] = 0.5
        self.assertIn("bm.assist.as_elevator", targets(spec))

    def test_repair_restores_fixed_values(self):
        spec = replay_spec()
        spec["config"]["maxHearts"]["value"] = 5
        spec["floors"][19]["attackInterval"] = 1.0
        repair(spec, RULES)
        self.assertEqual(validate(spec, RULES), [])


class SimTest(unittest.TestCase):
    def test_reach_rates_shape(self):
        r = reach_rates(replay_spec(), runs=30)
        self.assertEqual(set(r), {"숙련자", "보통", "초보"})
        self.assertGreaterEqual(r["숙련자"]["reach"]["20"], r["초보"]["reach"]["20"])

    def test_assist_raises_reach(self):
        from stairs_agents.mechanics import assist_profile
        spec = replay_spec()
        unpaid = reach_rates(spec, runs=60)["보통"]["reach"]["40"]
        paid = reach_rates(spec, runs=60, assist=assist_profile(spec, 3))["보통"]["reach"]["40"]
        self.assertGreater(paid, unpaid)


class _Counter(Role):
    """차례마다 문제가 하나씩 줄어드는 가짜 역할."""
    name = "fake"

    def __init__(self, start=3, regen=True, out=None):
        self.left, self.regen, self.output_dir = start, regen, out

    def act(self, feedback, n):
        if n > 1:
            self.left -= 1

    def can_regenerate(self):
        return self.regen

    def repair(self, evals, n):
        self.left -= 1
        return True

    def evaluators(self):
        return [lambda r: Evaluation("count", [Issue("count", "mid", f"x{i}", "문제") for i in range(self.left)])]


class LoopTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ledger = Ledger(self.tmp / "ledger.jsonl")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_loop_until_pass(self):
        res = LoopRunner(self.ledger, Budget(max_rounds=6)).run(_Counter(3))
        self.assertEqual((res["verdict"], res["rounds"], res["stop"]), ("pass", 4, "통과"))
        self.assertEqual(len(self.ledger.path.read_text(encoding="utf-8").splitlines()), 5)

    def test_repair_mode_when_cannot_regenerate(self):
        res = LoopRunner(self.ledger, Budget(max_rounds=6)).run(_Counter(2, regen=False))
        self.assertEqual(res["verdict"], "pass")
        self.assertEqual([h["mode"] for h in res["history"]], ["act", "repair", "repair"])

    def test_budget_stops(self):
        res = LoopRunner(self.ledger, Budget(max_rounds=2)).run(_Counter(5))
        self.assertEqual((res["verdict"], res["rounds"]), ("revise", 2))

    def test_keeps_best_when_worse(self):
        out = self.tmp / "out"
        out.mkdir()

        class Worse(_Counter):
            def act(self, fb, n):
                (out / "v.txt").write_text(str(n))
                self.left = 1 if n == 1 else 4

        res = LoopRunner(self.ledger, Budget(max_rounds=4, patience=2)).run(Worse(out=out))
        self.assertEqual(res["best_round"], 1)
        self.assertEqual((out / "v.txt").read_text(), "1")


if __name__ == "__main__":
    unittest.main()
