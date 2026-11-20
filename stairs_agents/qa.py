"""품질 확인(QA) 에이전트 공통 부분: 문제 기록, Claude 검토 요청, 보고서 쓰기.

QA 에이전트는 두 단계로 확인한다.
1. 규칙 검사: 코드로 재는 항목 (LLM 없이 항상 돈다)
2. Claude 검토: 규칙 검사 결과와 결과물(이미지 또는 코드)을 Claude에 보내 기획서·컨셉과 맞는지 묻는다.
   재생 모드에서 응답 파일(replay/qa_<대상>_review.txt)이 없으면 이 단계는 건너뛰고 그 사실을 보고서에 적는다.

판정: 규칙 검사에 high 문제가 하나라도 있으면 fail, high는 없고 mid가 있거나 Claude가 revise라고 하면 revise, 아니면 pass.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .llm import LLMError
from .util import Paths, extract_json, load_prompt, log, write_json

SEVERITIES = ("high", "mid", "low")


@dataclass
class QAReport:
    target: str                          # "designer" 또는 "developer"
    checks: list = field(default_factory=list)   # {"id","ok","detail"}
    issues: list = field(default_factory=list)   # {"source","asset","severity","problem","fix"}
    metrics: dict = field(default_factory=dict)
    review: dict | None = None
    review_note: str = ""

    def check(self, cid: str, ok: bool, detail: str = "", severity: str = "mid", asset: str = "", fix: str = ""):
        self.checks.append({"id": cid, "ok": bool(ok), "detail": detail})
        if not ok:
            self.issues.append({"source": "규칙", "asset": asset or cid, "severity": severity,
                                "problem": detail or cid, "fix": fix})
        return ok

    @property
    def verdict(self) -> str:
        rule = [i for i in self.issues if i["source"] == "규칙"]
        if any(i["severity"] == "high" for i in rule):
            return "fail"
        if any(i["severity"] == "high" for i in self.issues if i["source"] == "Claude"):
            return "revise"
        if any(i["severity"] == "mid" for i in self.issues) or (self.review or {}).get("verdict") == "revise":
            return "revise"
        return "pass"

    def to_dict(self) -> dict:
        return {"target": self.target, "verdict": self.verdict, "checks": self.checks, "issues": self.issues,
                "metrics": self.metrics, "review": self.review, "review_note": self.review_note}

    def markdown(self, title: str) -> str:
        ok = sum(c["ok"] for c in self.checks)
        lines = [f"# {title}", "", f"판정: **{self.verdict}** · 규칙 검사 {ok}/{len(self.checks)} 통과", ""]
        if self.review_note:
            lines += [f"Claude 검토: {self.review_note}", ""]
        elif self.review:
            lines += ["Claude 검토 요약: " + str(self.review.get("summary", "")), ""]
        lines += ["## 문제와 고칠 점", ""]
        if not self.issues:
            lines.append("없음")
        else:
            lines += ["| 심각도 | 출처 | 대상 | 문제 | 고칠 점 |", "|---|---|---|---|---|"]
            order = {s: i for i, s in enumerate(SEVERITIES)}
            for i in sorted(self.issues, key=lambda x: order.get(x["severity"], 9)):
                cells = [i["severity"], i["source"], i["asset"], i["problem"], i.get("fix", "")]
                lines.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in cells) + " |")
        lines += ["", "## 규칙 검사", "", "| 항목 | 결과 | 내용 |", "|---|---|---|"]
        for c in self.checks:
            lines.append(f"| {c['id']} | {'통과' if c['ok'] else '문제'} | {c['detail']} |")
        if self.metrics:
            lines += ["", "## 수치", ""]
            for k, v in self.metrics.items():
                lines.append(f"- {k}: {v}")
        return "\n".join(lines) + "\n"


def ask_review(llm, paths: Paths, report: QAReport, agent: str, user: str, images=None) -> None:
    """Claude에 검토를 요청하고 응답의 issues를 report에 더한다. 응답이 없으면 건너뛴 이유를 적는다."""
    if llm is None:
        report.review_note = "건너뜀 (LLM 없이 실행)"
        return
    try:
        text = llm.complete(agent, "review", load_prompt(paths, agent), user, images=images)
    except LLMError as e:
        report.review_note = f"건너뜀 ({e})"
        log.info("[%s] Claude 검토 건너뜀: %s", agent, e)
        return
    try:
        rv = extract_json(text)
    except ValueError as e:
        report.review_note = f"응답을 읽지 못함 ({e})"
        return
    report.review = rv
    for i in rv.get("issues", []):
        sev = i.get("severity", "low")
        report.issues.append({"source": "Claude", "asset": i.get("asset", ""),
                              "severity": sev if sev in SEVERITIES else "low",
                              "problem": i.get("problem", ""), "fix": i.get("fix", "")})


def save(paths: Paths, report: QAReport, title: str, t0: float) -> dict:
    out = paths.out / "qa_out"
    out.mkdir(parents=True, exist_ok=True)
    d = report.to_dict()
    write_json(out / f"{report.target}_qa.json", d)
    (out / f"{report.target}_qa.md").write_text(report.markdown(title), encoding="utf-8")
    high = sum(i["severity"] == "high" for i in report.issues)
    log.info("[%s QA] 판정 %s: 문제 %d개 (high %d), 규칙 %d/%d 통과 (%.1f초)", report.target.capitalize(), report.verdict,
             len(report.issues), high, sum(c["ok"] for c in report.checks), len(report.checks), time.time() - t0)
    return d
