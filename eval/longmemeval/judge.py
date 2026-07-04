"""Official LongMemEval LLM-judge protocol.

The prompt templates below are verbatim ports of ``get_anscheck_prompt`` in
``src/evaluation/evaluate_qa.py`` of the official repo
(https://github.com/xiaowu0162/LongMemEval). Protocol details preserved:

- one user message, ``temperature=0``, ``max_tokens=10``;
- the paper's judge model is ``gpt-4o-2024-08-06``;
- a response is correct iff ``"yes" in judge_reply.lower()``;
- abstention questions (``question_id`` ending ``_abs``) use the dedicated
  abstention template regardless of ``question_type``, with the dataset's
  ``answer`` field serving as the explanation.
"""

from __future__ import annotations

from dataclasses import dataclass

from longmemeval.chat import ChatModelConfig, chat_completion


JUDGE_TEMPERATURE = 0.0
JUDGE_MAX_TOKENS = 10

_DEFAULT_TEMPLATE = (
    "I will give you a question, a correct answer, and a response from a model. "
    "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
    "If the response is equivalent to the correct answer or contains all the intermediate "
    "steps to get the correct answer, you should also answer yes. If the response only "
    "contains a subset of the information required by the answer, answer no. "
    "\n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\n"
    "Is the model response correct? Answer yes or no only."
)

_TEMPORAL_TEMPLATE = (
    "I will give you a question, a correct answer, and a response from a model. "
    "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
    "If the response is equivalent to the correct answer or contains all the intermediate "
    "steps to get the correct answer, you should also answer yes. If the response only "
    "contains a subset of the information required by the answer, answer no. In addition, "
    "do not penalize off-by-one errors for the number of days. If the question asks for "
    "the number of days/weeks/months, etc., and the model makes off-by-one errors "
    "(e.g., predicting 19 days when the answer is 18), the model's response is still correct. "
    "\n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\n"
    "Is the model response correct? Answer yes or no only."
)

_KNOWLEDGE_UPDATE_TEMPLATE = (
    "I will give you a question, a correct answer, and a response from a model. "
    "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
    "If the response contains some previous information along with an updated answer, "
    "the response should be considered as correct as long as the updated answer is the "
    "required answer.\n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\n"
    "Is the model response correct? Answer yes or no only."
)

_PREFERENCE_TEMPLATE = (
    "I will give you a question, a rubric for desired personalized response, and a response "
    "from a model. Please answer yes if the response satisfies the desired response. "
    "Otherwise, answer no. The model does not need to reflect all the points in the rubric. "
    "The response is correct as long as it recalls and utilizes the user's personal "
    "information correctly.\n\nQuestion: {}\n\nRubric: {}\n\nModel Response: {}\n\n"
    "Does the model response satisfy the rubric? Answer yes or no only."
)

_ABSTENTION_TEMPLATE = (
    "I will give you an unanswerable question, an explanation, and a response from a model. "
    "Please answer yes if the model correctly identifies the question as unanswerable. "
    "The model could say that the information is incomplete, or some other information is "
    "given but the asked information is not.\n\nQuestion: {}\n\nExplanation: {}\n\n"
    "Model Response: {}\n\nDoes the model correctly identify the question as unanswerable? "
    "Answer yes or no only."
)

_TASK_TEMPLATES = {
    "single-session-user": _DEFAULT_TEMPLATE,
    "single-session-assistant": _DEFAULT_TEMPLATE,
    "multi-session": _DEFAULT_TEMPLATE,
    "temporal-reasoning": _TEMPORAL_TEMPLATE,
    "knowledge-update": _KNOWLEDGE_UPDATE_TEMPLATE,
    "single-session-preference": _PREFERENCE_TEMPLATE,
}


class LongMemEvalJudgeError(ValueError):
    """Raised for question types the official protocol does not define."""


@dataclass(frozen=True, slots=True)
class JudgeResult:
    correct: bool
    raw_response: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_seconds: float | None = None

    def to_record(self) -> dict[str, object]:
        return {
            "correct": self.correct,
            "raw_response": self.raw_response,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_seconds": round(self.latency_seconds, 3) if self.latency_seconds is not None else None,
        }


def get_anscheck_prompt(task: str, question: str, answer: str, response: str, *, abstention: bool = False) -> str:
    """Build the official judge prompt for one hypothesis."""
    if abstention:
        return _ABSTENTION_TEMPLATE.format(question, answer, response)
    template = _TASK_TEMPLATES.get(task)
    if template is None:
        raise LongMemEvalJudgeError(f"unsupported LongMemEval question type: {task!r}")
    return template.format(question, answer, response)


def parse_judge_label(judge_reply: str) -> bool:
    """Official label extraction: correct iff 'yes' appears in the reply."""
    return "yes" in judge_reply.lower()


def judge_hypothesis(
    config: ChatModelConfig,
    *,
    question_type: str,
    question: str,
    gold_answer: str,
    hypothesis: str,
    is_abstention: bool,
) -> JudgeResult:
    prompt = get_anscheck_prompt(question_type, question, gold_answer, hypothesis, abstention=is_abstention)
    completion = chat_completion(
        config,
        [{"role": "user", "content": prompt}],
        temperature=JUDGE_TEMPERATURE,
        max_tokens=JUDGE_MAX_TOKENS,
    )
    return JudgeResult(
        correct=parse_judge_label(completion.text),
        raw_response=completion.text.strip(),
        prompt_tokens=completion.prompt_tokens,
        completion_tokens=completion.completion_tokens,
        latency_seconds=completion.latency_seconds,
    )


__all__ = [
    "JUDGE_MAX_TOKENS",
    "JUDGE_TEMPERATURE",
    "JudgeResult",
    "LongMemEvalJudgeError",
    "get_anscheck_prompt",
    "judge_hypothesis",
    "parse_judge_label",
]
