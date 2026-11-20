"""품질 확인(QA) 에이전트 공통 부분: 문제 기록, Claude 검토 요청, 보고서 쓰기.

QA 에이전트는 두 단계로 확인한다.
1. 규칙 검사: 코드로 재는 항목 (LLM 없이 항상 돈다)
2. Claude 검토: 규칙 검사 결과와 결과물(이미지 또는 코드)을 Claude에 보내 기획서·컨셉과 맞는지 묻는다.
   재생 모드에서 응답 파일(replay/qa_<대상>_review.txt)이 없으면 이 단계는 건너뛰고 그 사실을 보고서에 적는다.

판정: 규칙 검사에 high 문제가 하나라도 있으면 fail, high는 없고 mid가 있거나 Claude가 revise라고 하면 revise, 아니면 pass.

고침 반복 (qa_loop): 판정이 pass가 아니면 QA의 고칠 점을 만든 에이전트에게 돌려줘 다시 만들게 하고 다시 확인한다.
최대 MAX_ROUNDS(11)번까지 돌고, 통과하거나, 문제 목록이 앞 차례와 같아 나아지지 않거나,
재생 모드처럼 다시 만들어도 같은 응답이 나오는 경우에는 일찍 멈춘다. 차례마다의 판정은 qa_out/<대상>_loop.json에 남는다.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .llm import LLMError
from .util import Paths, extract_json, load_prompt, log, write_json

SEVERITIES = ("high", "mid", "low")
MAX_ROUNDS = 11


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


def ask_review(llm, paths: Paths, report: QAReport, agent: str, user: str, images=None, round_no: int = 1) -> None:
    """Claude에 검토를 요청하고 응답의 issues를 report에 더한다. 응답이 없으면 건너뛴 이유를 적는다."""
    if llm is None:
        report.review_note = "건너뜀 (LLM 없이 실행)"
        return
    try:
        text = llm.complete(agent, "review" + (f"_r{round_no}" if round_no > 1 else ""), load_prompt(paths, agent), user, images=images)
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


def feedback_text(report: dict, round_no: int) -> str:
    """QA 보고를 만든 에이전트에게 돌려줄 고칠 점 문구."""
    order = {s: i for i, s in enumerate(SEVERITIES)}
    issues = sorted(report.get("issues", []), key=lambda i: order.get(i["severity"], 9))
    lines = [f"# {report['target']} QA가 돌려준 고칠 점 ({round_no}번째 만들기, 앞 차례 판정 {report['verdict']})",
             "아래 문제를 고쳐 같은 출력 형식으로 다시 내라. 문제가 없는 부분은 그대로 둔다."]
    lines += [f"- [{i['severity']}] {i['asset']}: {i['problem']}" + (f" -> {i['fix']}" if i.get("fix") else "") for i in issues]
    return "\n".join(lines)


def _signature(report: dict) -> tuple:
    return tuple(sorted((i["severity"], i["asset"], i["problem"]) for i in report.get("issues", [])))


def qa_loop(paths: Paths, target: str, produce, check, rounds: int = MAX_ROUNDS, can_retry: bool = True):
    """produce(feedback, round_no)로 만들고 check(round_no)로 확인하기를 판정이 pass가 될 때까지 최대 rounds(<=11)번 되풀이한다.
    (첫 차례의 produce는 feedback=None으로 부른다.) 마지막 결과와 QA 보고를 돌려준다."""
    rounds = max(1, min(MAX_ROUNDS, rounds))
    result = produce(None, 1)
    rep = check(1)
    history, stop = [{"round": 1, "verdict": rep["verdict"], "issues": len(rep["issues"])}], "최대 차례"
    for n in range(2, rounds + 1):
        if rep["verdict"] == "pass":
            stop = "통과"; break
        if not can_retry:
            stop = "다시 만들 수 없음 (재생 모드는 같은 응답을 돌려준다)"; break
        prev = _signature(rep)
        log.info("[%s QA] %d번째 고침: 문제 %d개를 돌려준다", target.capitalize(), n, len(rep["issues"]))
        result = produce(feedback_text(rep, n), n)
        rep = check(n)
        history.append({"round": n, "verdict": rep["verdict"], "issues": len(rep["issues"])})
        if _signature(rep) == prev and rep["verdict"] != "pass":
            stop = "나아지지 않음 (앞 차례와 같은 문제)"; break
    else:
        if rep["verdict"] == "pass":
            stop = "통과"
    rep["loop"] = {"rounds": len(history), "max": rounds, "stop": stop, "history": history}
    write_json(paths.out / "qa_out" / f"{target}_loop.json", rep["loop"])
    log.info("[%s QA] 고침 반복 %d/%d번에서 멈춤: %s (판정 %s)", target.capitalize(), len(history), rounds, stop, rep["verdict"])
    return result, rep
