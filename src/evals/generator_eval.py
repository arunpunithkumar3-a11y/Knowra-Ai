import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from deepeval import evaluate
from deepeval.evaluate.configs import AsyncConfig, ErrorConfig
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.models import OpenAIModel
from deepeval.test_case import LLMTestCase
from dotenv import load_dotenv

from src.config import configure
from src.evals.generator import generate_answer

load_dotenv()

# DeepEval judge model
judge_model = OpenAIModel(
    model=configure.JUDGE_MODEL,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=configure.NVIDIA_API_KEY,
    temperature=0,
)

# Load dataset with golden context
data_dir = Path(__file__).resolve().parent / "data"
def run_generator_eval():
    dataset_path = data_dir / "knowra_golden_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        goldens = json.load(f)

    test_cases = []
    for g in goldens:
        query = g["query"]

        # Retrieval context comes directly from golden_context
        raw_context = g.get("golden_context", "")
        retrieval_context = (
            [raw_context.strip()] if isinstance(raw_context, str) else raw_context
        )

        # Generate answer using query and golden context in isolation
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
    ]

    return evaluate(
        test_cases=test_cases,
        metrics=metrics,
        async_config=AsyncConfig(run_async=False),
        error_config=ErrorConfig(ignore_errors=True),
    )


if __name__ == "__main__":
    run_generator_eval()
