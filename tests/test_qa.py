"""컨셉 스프라이트 뽑기(concept.py)와 QA 공통 부분 시험."""
import unittest

from PIL import Image

from stairs_agents import concept
import tempfile
from pathlib import Path

from stairs_agents.qa import MAX_ROUNDS, QAReport, qa_loop
from stairs_agents.util import Paths
from stairs_agents.qa_developer import config_block, numbers
from stairs_agents.qa_screens import accent_iou, layout_corr


def figure_on_bg() -> Image.Image:
    """회색 배경 위 빨간 막대 (16x24, 가운데 6x16)."""
    im = Image.new("RGBA", (16, 24), (60, 62, 68, 255))
    for x in range(5, 11):
        for y in range(4, 20):
            im.putpixel((x, y), (161, 61, 61, 255))
    return im


class ConceptTest(unittest.TestCase):
    def test_remove_bg_keeps_figure(self):
        cut = concept.remove_bg(figure_on_bg())
        self.assertEqual(cut.getpixel((0, 0))[3], 0)
        self.assertEqual(cut.getpixel((7, 10))[3], 255)

    def test_fit_anchors_bottom_center(self):
        out = concept.fit(concept.remove_bg(figure_on_bg()), 32, 48)
        self.assertEqual(out.size, (32, 48))
        bbox = out.getchannel("A").getbbox()
        self.assertEqual(bbox[3], 48)                       # 발이 프레임 아래
        self.assertAlmostEqual((bbox[0] + bbox[2]) / 2, 16, delta=1)

    def test_grid_roundtrip(self):
        small = concept.quantize(concept.fit(concept.remove_bg(figure_on_bg()), 16, 24), colors=2)
        rows, pal = concept.to_grid(small)
        self.assertEqual(len(rows), 24)
        self.assertTrue(all(len(r) == 16 for r in rows))
        self.assertIn(".", rows[0])
        self.assertEqual(set(pal.values()), {"#A13D3D"})

    def test_compare(self):
        a = concept.fit(concept.remove_bg(figure_on_bg()), 16, 24)
        self.assertEqual(concept.palette_distance(["#A13D3D"], ["#A13D3D"]), 0)
        self.assertGreater(concept.palette_distance(["#A13D3D"], ["#8A9A5B"]), 90)
        self.assertEqual(concept.silhouette_iou(a, a), 1.0)


class QATest(unittest.TestCase):
    def test_verdict(self):
        r = QAReport("designer")
        r.check("a", True)
        self.assertEqual(r.verdict, "pass")
        r.check("b", False, "x", "mid")
        self.assertEqual(r.verdict, "revise")
        r.check("c", False, "y", "high")
        self.assertEqual(r.verdict, "fail")

    def test_claude_high_is_revise_not_fail(self):
        r = QAReport("developer")
        r.issues.append({"source": "Claude", "asset": "x", "severity": "high", "problem": "", "fix": ""})
        self.assertEqual(r.verdict, "revise")

    def test_config_numbers(self):
        js = "const A = 1;\nconst CONFIG = {\n  hearts: 3, // 9\n  days: 30, win: 0.20, sub: { x: 1.5 },\n};\nconst B = 7;"
        block = config_block(js)
        self.assertTrue(block.startswith("{") and block.endswith("}"))
        self.assertEqual(numbers(block), {3.0, 30.0, 0.2, 1.5})


class ScreenQATest(unittest.TestCase):
    def test_same_screen(self):
        im = Image.new("RGB", (320, 180), (30, 31, 34))
        for x in range(100, 220):
            for y in range(140, 170):
                im.putpixel((x, y), (161, 61, 61))       # 빨간 버튼
        self.assertEqual(layout_corr(im, im), 1.0)
        iou, share = accent_iou(im, im)
        self.assertEqual(iou, 1.0)
        self.assertGreater(share, 0.01)

    def test_moved_button(self):
        a = Image.new("RGB", (320, 180), (30, 31, 34)); b = a.copy()
        for x in range(10, 60):
            for y in range(10, 30):
                a.putpixel((x, y), (161, 61, 61))
        for x in range(250, 310):
            for y in range(140, 170):
                b.putpixel((x, y), (161, 61, 61))
        self.assertEqual(accent_iou(a, b)[0], 0.0)


class QALoopTest(unittest.TestCase):
    def _run(self, verdicts, can_retry=True, rounds=MAX_ROUNDS):
        """verdicts[n-1] = n번째 확인의 판정. 문제 목록은 차례마다 달라지게 한다."""
        made = []
        with tempfile.TemporaryDirectory() as d:
            paths = Paths(out=Path(d))
            def produce(fb, n):
                made.append((n, fb is not None)); return n
            def check(n):
                v = verdicts[min(n, len(verdicts)) - 1]
                return {"target": "t", "verdict": v, "issues": [] if v == "pass" else [{"severity": "mid", "asset": f"a{n}", "problem": "p", "fix": "f"}]}
            res, rep = qa_loop(paths, "t", produce, check, rounds, can_retry)
        return made, rep

    def test_stops_on_pass(self):
        made, rep = self._run(["revise", "revise", "pass"])
        self.assertEqual(rep["loop"]["rounds"], 3)
        self.assertEqual(rep["loop"]["stop"], "통과")
        self.assertEqual(made, [(1, False), (2, True), (3, True)])    # 2번째부터 고칠 점을 받는다

    def test_max_eleven(self):
        made, rep = self._run(["revise"], rounds=99)
        self.assertEqual(rep["loop"]["rounds"], MAX_ROUNDS)
        self.assertEqual(MAX_ROUNDS, 11)

    def test_no_retry_in_replay(self):
        made, rep = self._run(["revise"], can_retry=False)
        self.assertEqual(rep["loop"]["rounds"], 1)


if __name__ == "__main__":
    unittest.main()
