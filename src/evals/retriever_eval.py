import json
from pathlib import Path

# 1. Set DeepEval overrides BEFORE importing evaluate or running metrics
from deepeval import evaluate
from deepeval.evaluate.configs import AsyncConfig, ErrorConfig
from deepeval.metrics import ContextualPrecisionMetric, ContextualRecallMetric
from deepeval.models import OpenAIModel
from deepeval.test_case import LLMTestCase
from dotenv import load_dotenv

from src.config import configure
from src.evals.retriever import final_retrieve

load_dotenv()

# DeepEval-compatible judge model pointing to NVIDIA NIM
judge_model = OpenAIModel(
    model=configure.JUDGE_MODEL,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=configure.NVIDIA_API_KEY,
    temperature=0,
)

dataset_path = (
    Path(__file__).resolve().parent / "data" / "golden_dataset.json"
    if (Path(__file__).resolve().parent / "data" / "golden_dataset.json").exists()
    else Path(__file__).resolve().parent / "golden_dataset.json"
)
def run_retriever_eval():
    with open(dataset_path, "r", encoding="utf-8") as f:
        goldens = json.load(f)

    test_cases = []
    for g in goldens:
        retrieved = final_retrieve(g["query"])
        # Ensure retrieval_context is never empty, whitespace, or None
        raw_contexts = [
            (doc.metadata.get("parent_window") or doc.page_content or "").strip()
            for doc in retrieved
        ]
        retrieval_context = [c for c in raw_contexts if c] or [
            "No relevant context retrieved."
        ]

        test_cases.append(
            LLMTestCase(
                input=g["query"],
                expected_output=g["ideal_answer"],
                retrieval_context=retrieval_context,
                actual_output=g.get("ideal_answer")
                or "(generator not evaluated in this run)",
            )
        )

    metrics = [
        ContextualRecallMetric(threshold=0.7, model=judge_model, include_reason=True),
        ContextualPrecisionMetric(threshold=0.7, model=judge_model, include_reason=True),
    ]

    # Run synchronously (run_async=False) to ensure strictly 1 request at a time without parallel bursts
    return evaluate(
        test_cases=test_cases,
        metrics=metrics,
        async_config=AsyncConfig(run_async=False),
        error_config=ErrorConfig(ignore_errors=True),
    )


if __name__ == "__main__":
    run_retriever_eval()
