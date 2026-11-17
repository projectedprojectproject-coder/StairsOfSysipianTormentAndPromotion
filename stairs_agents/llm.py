"""LLM 호출 계층.

ClaudeClient   Anthropic Messages API를 스트리밍으로 호출한다 (ANTHROPIC_API_KEY 필요).
ReplayClient   replay/ 폴더에 저장된 응답을 돌려준다. API 키 없이 파이프라인을 시험할 때 쓴다.
RecordingClient 실제 응답을 replay/ 형식으로 저장해 다음 실행에서 재사용할 수 있게 한다.

세 클라이언트 모두 complete(agent, step, system, user) 하나의 메서드만 가진다.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5-5"


class LLMError(RuntimeError):
    pass


class ClaudeClient:
    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 64000, retries: int = 3):
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise LLMError("anthropic 패키지가 없습니다. pip install anthropic") from e
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("ANTHROPIC_API_KEY 환경 변수가 설정되어 있지 않습니다.")
        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens
        self.retries = retries

    def complete(self, agent: str, step: str, system: str, user: str) -> str:
        last_err = None
        for attempt in range(1, self.retries + 1):
            try:
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                ) as stream:
                    msg = stream.get_final_message()
                text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
                if msg.stop_reason == "max_tokens":
                    dbg = Path("llm_truncated"); dbg.mkdir(exist_ok=True)
                    (dbg / f"{agent}_{step}.txt").write_text(text, encoding="utf-8")
                    raise LLMError(f"[{agent}/{step}] 응답이 max_tokens({self.max_tokens})에서 잘렸습니다.")
                return text
            except (self._anthropic.APIConnectionError, self._anthropic.RateLimitError,
                    self._anthropic.InternalServerError) as e:
                last_err = e
                time.sleep(2 * attempt)
        raise LLMError(f"[{agent}/{step}] API 호출 실패: {last_err}")


class ReplayClient:
    """replay/<agent>_<step>.txt 파일을 응답으로 돌려준다."""

    def __init__(self, replay_dir: Path):
        self.replay_dir = Path(replay_dir)

    def complete(self, agent: str, step: str, system: str, user: str) -> str:
        path = self.replay_dir / f"{agent}_{step}.txt"
        if not path.exists():
            raise LLMError(f"재생 응답 파일이 없습니다: {path}")
        return path.read_text(encoding="utf-8")


class RecordingClient:
    """다른 클라이언트의 응답을 replay 형식으로 저장한다."""

    def __init__(self, inner, replay_dir: Path):
        self.inner = inner
        self.replay_dir = Path(replay_dir)
        self.replay_dir.mkdir(parents=True, exist_ok=True)

    def complete(self, agent: str, step: str, system: str, user: str) -> str:
        text = self.inner.complete(agent, step, system, user)
        (self.replay_dir / f"{agent}_{step}.txt").write_text(text, encoding="utf-8")
        return text
