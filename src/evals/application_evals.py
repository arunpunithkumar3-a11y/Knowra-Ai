# eval_application.py
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from deepeval import evaluate
from deepeval.metrics import GEval
from deepeval.metrics.g_eval import Rubric
from deepeval.models import OpenAIModel
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from dotenv import load_dotenv

from src.config import configure
from src.evals.generator import generate_answer
from src.evals.retriever import final_retrieve

load_dotenv()

# 1. Dataset path pointing to your golden dataset
GOLDEN_PATH = Path(__file__).resolve().parent / "data" / "knowra_golden_dataset.json"

# 2. DeepEval Judge model using your codebase config
judge_model = OpenAIModel(
    model=configure.JUDGE_MODEL,
    base_url=configure.NVIDIA_BASE_URL,
    api_key=configure.NVIDIA_API_KEY,
    temperature=0,
)

THRESHOLD = 0.7


# Helper harness functions
def load_goldens(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def summarize_by_metric(result):
    return result


def print_summary(name, result):
    print(f"\n--- Evaluation Summary: {name} ---")
    print(result)


# Pipeline wrapper matching your codebase
class RagPipeline:
    def invoke(self, question: str):
        retrieved_docs = final_retrieve(query=question)
        raw_contexts = [
            (doc.metadata.get("parent_window") or doc.page_content or "").strip()
            for doc in retrieved_docs
        ]
        retrieval_context = [c for c in raw_contexts if c] or [
            "No relevant context retrieved."
        ]
        answer = generate_answer(query=question, context=retrieval_context)
        return {"answer": answer, "context": retrieval_context}


def run(rag):
    # 1. LOAD queries + ideal answers
    goldens = load_goldens(GOLDEN_PATH)

    # 2. RUN THE INJECTED PIPELINE per query, build a test case from LIVE output
    test_cases = []
    for g in goldens:
        question = g.get("query") or g.get("question")
        ideal_answer = g.get("ideal_answer") or g.get("expected_output")

        result = rag.invoke(question)  # retrieve -> rerank -> generate

        test_cases.append(
            LLMTestCase(
                input=question,
                actual_output=result["answer"],
                expected_output=ideal_answer,
            )
        )

    # 3. THREE APPLICATION-LEVEL QUALITY METRICS

    # 3a. CORRECTNESS --- reference-based, judges TRUTH (not coverage or length)
    correctness = GEval(
        name="Correctness",
        evaluation_steps=[
            "Compare only the factual claims in the actual output against the expected output.",
            "A claim is wrong only if it CONTRADICTS the expected output or is factually false. Judge truth, not completeness.",
            "A factually accurate answer must score at least 0.9 even if it is shorter or covers fewer points than the expected output.",
            "Do NOT deduct for brevity, missing elaboration, or omitted points --- omissions are not errors here.",
            "Additional correct information must NEVER lower the score.",
        ],
        rubric=[
            Rubric(
                score_range=(9, 10),
                expected_outcome="All stated claims are factually correct and consistent. No contradictions. Brevity is fine.",
            ),
            Rubric(
                score_range=(5, 8),
                expected_outcome="Mostly correct but one minor inaccuracy.",
            ),
            Rubric(
                score_range=(0, 4),
                expected_outcome="Contains a clear factual error or a claim that contradicts the expected output.",
            ),
        ],
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=THRESHOLD,
        model=judge_model,
        strict_mode=False,
    )

    # 3b. COMPLETENESS --- reference-based, judges COVERAGE (not correctness)
    completeness = GEval(
        name="Completeness",
        evaluation_steps=[
            "Identify the key points contained in the expected output.",
            "Check how many of those key points are addressed in the actual output.",
            "Penalize the actual output for each key point from the expected output that it omits or only partially covers.",
            "Judge coverage only. Do NOT lower the score because a covered point is stated incorrectly --- factual correctness is judged separately.",
            "Do NOT penalize the actual output for adding extra information beyond the expected output.",
        ],
        rubric=[
            Rubric(
                score_range=(9, 10),
                expected_outcome="Addresses essentially all key points in the expected output.",
            ),
            Rubric(
                score_range=(5, 8),
                expected_outcome="Covers the main key points but misses one or more.",
            ),
            Rubric(
                score_range=(0, 4),
                expected_outcome="Misses several key points; only partially covers the expected output.",
            ),
        ],
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=THRESHOLD,
        model=judge_model,
        strict_mode=False,
    )

    # 3c. STYLE --- reference-free, judges TONE only (note: no EXPECTED_OUTPUT)
    style = GEval(
        name="Style",
        evaluation_steps=[
            "Judge only the teaching style and tone of the actual output, not whether it is factually correct or complete.",
            "Reward an intuitive, explanatory tone: plain language, the idea explained before any formula or jargon, and technical terms briefly unpacked when used.",
            "Reward a direct, conversational register written in prose, as a CampusX lecture would explain it out loud, rather than a dry, formal, or bullet-list tone.",
            "An analogy or concrete example is a BONUS when the concept is abstract, but a clear, direct, well-explained answer is fully acceptable and must NOT be penalized for not having one.",
            "Penalize answers that are stiff, bureaucratic, structured as a bare list with no explanation, or that use unexplained jargon.",
            "Do NOT reward or penalize based on correctness, completeness, or length --- only on style and tone.",
        ],
        rubric=[
            Rubric(
                score_range=(9, 10),
                expected_outcome="Clearly in a CampusX teaching voice: intuitive, conversational prose that explains before it formalizes.",
            ),
            Rubric(
                score_range=(7, 8),
                expected_outcome="Clear, conversational, and well-explained in prose. Fully acceptable even without an analogy or example.",
            ),
            Rubric(
                score_range=(4, 6),
                expected_outcome="Understandable but somewhat flat, formal, or list-heavy in places.",
            ),
            Rubric(
                score_range=(0, 3),
                expected_outcome="Dry, stiff, bare-list, jargon-heavy, or robotic; does not read like a teaching explanation.",
            ),
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=THRESHOLD,
        model=judge_model,
        strict_mode=False,
    )

    # 4. EVALUATE --- all three together
    result = evaluate(test_cases=test_cases, metrics=[correctness, completeness, style])
    return summarize_by_metric(result)


def run_local():
    """Standalone convenience: build the pipeline, then run."""
    return run(RagPipeline())


if __name__ == "__main__":
    print_summary("application", run_local())
