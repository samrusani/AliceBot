"""Disclosed post-generation grounding verification (the ``--verify-grounding`` gate).

This is a NEW harness component, off by default and fully disclosed: enabling
it stamps ``verify_grounding: true`` (plus the verifier model) into the run's
config fingerprint, and every gated row records both the original hypothesis
and the full verdict. It is NOT part of the official LongMemEval protocol and
it never touches the official reading or judge templates — the answer is
generated with the untouched official template first, then checked by a
SEPARATE chat call with the minimal prompt below.

Honesty guarantees (asserted by tests in ``test_harness.py``):

- The verifier NEVER sees the gold answer, the question type, or any other
  benchmark label — only the retrieved context block, the question text, and
  the model's own answer. It is judge-neutral: it cannot know whether the
  answer is "correct", only whether its concrete claims appear in the context.
- The gate runs uniformly on every question; no code path in this module
  branches on the benchmark's question-type or abstention labels (a test
  asserts those identifiers never appear in this file).
- Fail-open: any verifier error or unparseable reply leaves the original
  answer byte-identical and records the failure in the verdict, so
  verification can only ever be a disclosed, inspectable filter — never a
  hidden crash or a silent rewrite.

Gate semantics: only UNGROUNDED **LOAD-BEARING** claims (the direct answer
value itself — a fabricated name/number/date) convert the hypothesis to the
abstention phrasing; incidental unsupported phrasing never gates.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import time
from typing import Protocol, Sequence

from longmemeval.chat import ChatCompletionResult, ChatModelConfig, chat_completion


VERIFIER_BASE_URL_ENV = "ALICE_LME_VERIFIER_BASE_URL"
VERIFIER_NAME_ENV = "ALICE_LME_VERIFIER_MODEL"
VERIFIER_API_KEY_ENV = "ALICE_LME_VERIFIER_API_KEY"
# Fallback chain mirrors the judge: each field falls back to the answer model.
_MODEL_BASE_URL_ENV = "ALICE_LME_MODEL_BASE_URL"
_MODEL_NAME_ENV = "ALICE_LME_MODEL"
_MODEL_API_KEY_ENV = "ALICE_LME_MODEL_API_KEY"

VERIFY_TEMPERATURE = 0.0
VERIFY_MAX_TOKENS = 300

# The abstention phrasing the gate substitutes. It mirrors the style of the
# dataset's own gold abstention answers, which open with sentences like
# "You did not mention this information." and "The information provided is
# not enough." (see the ``*_abs`` answers in longmemeval_s).
ABSTENTION_HYPOTHESIS = (
    "You did not mention this information. The information provided in the "
    "chat history is not enough to answer this question."
)

# The verifier prompt. This is a NEW disclosed component — it is not an
# official LongMemEval template and must never replace or alter one. It is
# deliberately terse and judge-neutral: it receives ONLY the retrieved
# context, the question, and the answer under test. The gold answer is never
# included (tests assert this on the mock client's captured payloads).
VERIFIER_PROMPT_TEMPLATE = (
    "You are verifying that an answer is grounded in its source context. "
    "Use only the context below; do not use outside knowledge.\n\n"
    "Context:\n{context}\n\n"
    "Question:\n{question}\n\n"
    "Answer to verify:\n{answer}\n\n"
    "List every specific factual claim in the answer (a name, number, date, "
    "place, or other concrete value) that the context does not state or "
    "directly support. Label a claim LOAD-BEARING if it is the direct answer "
    "to the question; label it INCIDENTAL otherwise. Use one line per claim, "
    "exactly:\n"
    "UNGROUNDED LOAD-BEARING: <claim>\n"
    "UNGROUNDED INCIDENTAL: <claim>\n"
    "If every claim is supported by the context, or the answer only says the "
    "information is unavailable, reply with exactly: GROUNDED"
)

GROUNDED_TOKEN = "GROUNDED"
_LOAD_BEARING_PREFIX = "ungrounded load-bearing:"
_INCIDENTAL_PREFIX = "ungrounded incidental:"


class ChatClient(Protocol):
    """The slice of the chat seam the verifier needs (mockable in tests)."""

    def __call__(
        self,
        messages: Sequence[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int | None,
    ) -> ChatCompletionResult: ...


def _env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def verifier_config_from_env() -> ChatModelConfig | None:
    """The verifier model; each field falls back to the answer-model env."""
    base_url = _env(VERIFIER_BASE_URL_ENV) or _env(_MODEL_BASE_URL_ENV)
    model = _env(VERIFIER_NAME_ENV) or _env(_MODEL_NAME_ENV)
    if base_url is None or model is None:
        return None
    api_key = _env(VERIFIER_API_KEY_ENV) or _env(_MODEL_API_KEY_ENV)
    return ChatModelConfig(base_url=base_url.rstrip("/"), model=model, api_key=api_key)


def make_chat_client(config: ChatModelConfig) -> ChatClient:
    """Bind the harness HTTP client to a config behind the ``ChatClient`` seam."""

    def client(
        messages: Sequence[dict[str, str]],
        *,
        temperature: float = VERIFY_TEMPERATURE,
        max_tokens: int | None = None,
    ) -> ChatCompletionResult:
        return chat_completion(config, messages, temperature=temperature, max_tokens=max_tokens)

    return client


@dataclass(frozen=True, slots=True)
class UngroundedClaim:
    text: str
    load_bearing: bool

    def to_record(self) -> dict[str, object]:
        return {"text": self.text, "load_bearing": self.load_bearing}


@dataclass(frozen=True, slots=True)
class GroundingVerdict:
    """Outcome of one verification call; always recorded in full."""

    grounded: bool
    ungrounded_claims: tuple[UngroundedClaim, ...]
    raw_response: str | None
    error: str | None
    parse_note: str | None
    latency_seconds: float | None
    prompt_tokens: int | None
    completion_tokens: int | None

    @property
    def gate_should_abstain(self) -> bool:
        """Abstain only on a clean verdict with load-bearing failures (fail-open)."""
        return self.error is None and not self.grounded

    def to_record(self) -> dict[str, object]:
        return {
            "grounded": self.grounded,
            "ungrounded_claims": [claim.to_record() for claim in self.ungrounded_claims],
            "raw_response": self.raw_response,
            "error": self.error,
            "parse_note": self.parse_note,
            "latency_seconds": round(self.latency_seconds, 3) if self.latency_seconds is not None else None,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        }


def build_verifier_prompt(*, question: str, answer_text: str, context_block: str) -> str:
    """Fill the disclosed verifier template. Context + question + answer only."""
    return VERIFIER_PROMPT_TEMPLATE.format(
        context=context_block,
        question=question,
        answer=answer_text,
    )


def parse_verifier_reply(text: str) -> tuple[bool, tuple[UngroundedClaim, ...], str | None]:
    """Deterministic parse of the strict reply format.

    Returns ``(grounded, claims, parse_note)``. ``grounded`` is False only
    when at least one LOAD-BEARING line is present. A reply with neither the
    GROUNDED token nor any UNGROUNDED line fails open as grounded, with a
    ``parse_note`` recorded for transparency.
    """
    claims: list[UngroundedClaim] = []
    for line in text.splitlines():
        stripped = line.strip().lstrip("-*").strip()
        lowered = stripped.casefold()
        if lowered.startswith(_LOAD_BEARING_PREFIX):
            claim_text = stripped[len(_LOAD_BEARING_PREFIX) :].strip()
            if claim_text:
                claims.append(UngroundedClaim(text=claim_text, load_bearing=True))
        elif lowered.startswith(_INCIDENTAL_PREFIX):
            claim_text = stripped[len(_INCIDENTAL_PREFIX) :].strip()
            if claim_text:
                claims.append(UngroundedClaim(text=claim_text, load_bearing=False))
    parse_note = None
    if not claims and GROUNDED_TOKEN.casefold() not in text.casefold():
        parse_note = "unrecognized verifier reply; failing open as grounded"
    grounded = not any(claim.load_bearing for claim in claims)
    return grounded, tuple(claims), parse_note


def verify_grounding(
    *,
    question: str,
    answer_text: str,
    context_block: str,
    chat_client: ChatClient,
) -> GroundingVerdict:
    """One verification call. Never raises: any failure records an error verdict.

    The payload sent through ``chat_client`` contains only the context block,
    the question, and the answer under test — never the gold answer or any
    benchmark label.
    """
    prompt = build_verifier_prompt(
        question=question,
        answer_text=answer_text,
        context_block=context_block,
    )
    started = time.monotonic()
    try:
        completion = chat_client(
            [{"role": "user", "content": prompt}],
            temperature=VERIFY_TEMPERATURE,
            max_tokens=VERIFY_MAX_TOKENS,
        )
    except Exception as exc:  # noqa: BLE001 - fail-open: verification must never kill a run
        return GroundingVerdict(
            grounded=True,
            ungrounded_claims=(),
            raw_response=None,
            error=f"{type(exc).__name__}: {exc}",
            parse_note=None,
            latency_seconds=time.monotonic() - started,
            prompt_tokens=None,
            completion_tokens=None,
        )
    grounded, claims, parse_note = parse_verifier_reply(completion.text)
    return GroundingVerdict(
        grounded=grounded,
        ungrounded_claims=claims,
        raw_response=completion.text.strip(),
        error=None,
        parse_note=parse_note,
        latency_seconds=completion.latency_seconds,
        prompt_tokens=completion.prompt_tokens,
        completion_tokens=completion.completion_tokens,
    )


def apply_grounding_gate(answer_text: str, verdict: GroundingVerdict) -> tuple[str, bool]:
    """``(hypothesis, gate_applied)``: abstain only on clean load-bearing failures.

    A grounded verdict (or any error/fail-open verdict) returns ``answer_text``
    byte-identical with ``gate_applied=False``.
    """
    if verdict.gate_should_abstain:
        return ABSTENTION_HYPOTHESIS, True
    return answer_text, False


__all__ = [
    "ABSTENTION_HYPOTHESIS",
    "ChatClient",
    "GROUNDED_TOKEN",
    "GroundingVerdict",
    "UngroundedClaim",
    "VERIFIER_API_KEY_ENV",
    "VERIFIER_BASE_URL_ENV",
    "VERIFIER_NAME_ENV",
    "VERIFIER_PROMPT_TEMPLATE",
    "VERIFY_MAX_TOKENS",
    "VERIFY_TEMPERATURE",
    "apply_grounding_gate",
    "build_verifier_prompt",
    "make_chat_client",
    "parse_verifier_reply",
    "verifier_config_from_env",
    "verify_grounding",
]
