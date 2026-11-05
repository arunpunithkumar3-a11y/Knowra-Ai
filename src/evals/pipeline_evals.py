import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from deepeval import evaluate
from deepeval.evaluate.configs import AsyncConfig, ErrorConfig
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.models import OpenAIModel
from deepeval.test_case import LLMTestCase
from dotenv import load_dotenv

from src.config import configure
from src.evals.generator import generate_answer
from src.evals.retriever import final_retrieve

load_dotenv()

# DeepEval judge model
judge_model = OpenAIModel(
    model="openai/gpt-oss-20b",
    base_url="https://api.groq.com/openai/v1",
    api_key=configure.GROQ_API_KEY,
)
# Load dataset with golden context
data_dir = Path(__file__).resolve().parent / "data"
dataset_path = (
    data_dir / "knowra_golden_dataset.json"
    if (data_dir / "knowra_golden_dataset.json").exists()
    else data_dir / "knowra_golden_dataset_50.json"
)
def run_pipeline_eval():
    with open(dataset_path, "r", encoding="utf-8") as f:
        goldens = json.load(f)

    test_cases = []
    for g in goldens:
        query = g["query"]

        retrieved_docs = final_retrieve(query=query)
        raw_contexts = [
            (doc.metadata.get("parent_window") or doc.page_content or "").strip()
            for doc in retrieved_docs
        ]
        retrieval_context = [c for c in raw_contexts if c] or [
            "No relevant context retrieved."
        ]

        actual_output = generate_answer(query=query, context=retrieval_context)

        test_cases.append(
            LLMTestCase(
                input=query,
                actual_output=actual_output,
                retrieval_context=retrieval_context,
                expected_output=g.get("ideal_answer"),
            )
        )

    metrics = [
        FaithfulnessMetric(threshold=0.7, model=judge_model, include_reason=True),
        AnswerRelevancyMetric(threshold=0.7, model=judge_model, include_reason=True),
        ContextualRelevancyMetric(threshold=0.7, model=judge_model, include_reason=True),
    ]

    return evaluate(
        test_cases=test_cases,
        metrics=metrics,
        async_config=AsyncConfig(run_async=False),
        error_config=ErrorConfig(ignore_errors=True),
    )


if __name__ == "__main__":
    run_pipeline_eval()
