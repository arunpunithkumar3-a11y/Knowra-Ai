from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.knowra.pipeline import rag_pipeline


@tool
async def search_knowledge_base(
    query: str,
    config: RunnableConfig,
) -> str:
    """
    Search the business knowledge base.
    """

    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    business_id = configurable.get("business_id")

    if not business_id:
        return "Business context is missing."

    documents = await rag_pipeline.retrieve_ranked_context(
        query=query,
        business_id=business_id,
    )

    if not documents:
        return "No relevant information found."

    return "\n\n---\n\n".join(
        f"[Source: {doc.metadata.get('source', 'Knowledge Base')}]\n"
        f"{doc.page_content.strip()}"
        for doc in documents
    )


tools = [search_knowledge_base]
