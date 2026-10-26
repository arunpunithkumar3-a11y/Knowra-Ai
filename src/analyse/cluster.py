import logging
from collections import defaultdict
from typing import List

from src.analyse.prompt import (
    cluster_chain,
    format_instructions1,
    format_instructions2,
    summary_chain,
)
from src.models.analyse_schemas import TopicInsight

logger = logging.getLogger(__name__)


def optimize_query_for_llm(text: str) -> str:
    """Cleans and normalizes query whitespace for LLM processing."""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    if text.lower() in ("none", "null", "undefined", ""):
        return ""
    return " ".join(text.split())


async def analyse(questions: List[str]) -> List[TopicInsight]:
    """
    Executes question clustering and insight summarization pipeline.
    """
    cleaned_questions = [optimize_query_for_llm(q) for q in questions]
    cleaned_questions = [q for q in cleaned_questions if q]

    if not cleaned_questions:
        return []

    try:
        step1 = await cluster_chain.ainvoke(
            {
                "questions": cleaned_questions,
                "format_instructions": format_instructions1,
            }
        )
    except Exception as e:
        logger.error(f"Cluster chain failed: {e}")
        return []

    if not step1 or not getattr(step1, "questions", None):
        return []

    cluster_data = defaultdict(list)
    for q in step1.questions:
        topic = getattr(q, "topic", None) or "General Inquiry"
        cluster_data[topic].append(getattr(q, "question", str(q)))

    if not cluster_data:
        return []

    try:
        step2 = await summary_chain.ainvoke(
            {
                "clustered_data": dict(cluster_data),
                "format_instructions": format_instructions2,
            }
        )
    except Exception as e:
        logger.error(f"Summary chain failed: {e}")
        return []

    if isinstance(step2, dict):
        return [TopicInsight(topic_name=str(k), insight=str(v)) for k, v in step2.items()]

    if isinstance(step2, list):
        return [
            item if isinstance(item, TopicInsight)
            else TopicInsight(
                topic_name=item.get("topic_name", item.get("topic", "General Inquiry")),
                insight=item.get("insight", str(item)),
            )
            for item in step2
            if item
        ]

    return []
