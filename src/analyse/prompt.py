from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from src.config import configure
from src.models.analyse_schemas import QuestionTopicResponse

cluster_parser = PydanticOutputParser(pydantic_object=QuestionTopicResponse)
summary_parser = JsonOutputParser()
format_instructions1 = cluster_parser.get_format_instructions()
format_instructions2 = summary_parser.get_format_instructions()

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=configure.GROQ_API_KEY,
    max_tokens=8192,
    temperature=0.1,
)

CLUSTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a customer-question topic classifier for a business intelligence system.

Your task is to assign ONE clear topic to each customer question.

Rules:
- Assign exactly one topic to every question.
- The topic should represent the main subject or intent of the question.
- Create meaningful, broad topics (2–5 words) that can contain similar customer questions.
- Do not create overly specific topics.
- Do not combine unrelated subjects into one topic.
- Use concise topic names, preferably 2–5 words.
- Do not include explanations.
- Return a topic for every question provided.
- Focus on the customer's underlying intent, not just individual keywords.
- Output one topic per question in the exact same order as the input questions.

Examples:

"Can I pay using UPI?"
→ "Payment Methods"

"Do you accept Visa cards?"
→ "Payment Methods"

"Where is my order?"
→ "Order Tracking"

"How long does delivery take?"
→ "Delivery Time"

"What is your refund policy?"
→ "Refunds"
{format_instructions}
""",
        ),
        ("human", "questions:\n{questions}"),
    ]
)


SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a Principal Product Strategist and Business Intelligence Director advising executive leadership.

You will receive a dictionary where:
- Each KEY is a customer question cluster.
- Each VALUE is the list of raw customer questions in that cluster.

Your mission is NOT to summarize or describe what was asked. 
Your mission is to diagnose ROOT CAUSES of customer friction, quantify BUSINESS IMPACT, and recommend HIGH-LEVERAGE ACTIONABLE FIXES.

### Analytical Framework:
For every topic in the dictionary, evaluate the questions through these 4 strategic lenses:
1. Root Cause Diagnosis: What information gap, UX friction, policy ambiguity, or missing feature is forcing customers to ask this?
2. Financial & Operational Risk: Does this cause checkout abandonment, customer churn, buyer hesitation, or support ticket inflation?
3. Behavioral Intent: What is the customer's emotional state (e.g., purchase hesitation, post-payment anxiety, feature demand)?
4. Strategic Solution: What specific self-serve fix, product change, or policy update will eliminate 80% of these queries?

### Output Formatting Rules:
- Return ONLY a single flat JSON object (dictionary) mapping:
  `"Topic Title"` -> `"Strategic Business Insight String"`
- Structure each flashcard insight in 2–3 punchy, high-impact sentences following this exact formula:
  [Root Cause & Friction Diagnosis] + [Revenue / Churn / Support Impact] + [Prescriptive Business Action].
- STRICT NEGATIVE CONSTRAINTS:
  * NEVER begin insights with "Customers are asking about...", "This topic covers...", or "Users want...".
  * DO NOT state the obvious (e.g., do not say "delivery inquiries mean customers want their package").
  * For small talk, test queries, or irrelevant banter, return a 1-sentence triage note (e.g., "Low-intent conversational noise with no product impact").
  * Process EVERY topic in the dictionary.

Example format:
{{
  "Delivery & Tracking": "Post-purchase communication deficit: Anxious inquiries regarding order status reveal an information gap between shipment and arrival. Implementing proactive automated WhatsApp/SMS status triggers at fulfillment milestones will prevent support ticket surges and restore delivery confidence.",
  "Subscription & Billing": "Pricing transparency friction: Confusion around annual billing cycles and upfront charges is causing pre-checkout hesitation. Adding a clear monthly vs. annual pricing toggle with explicit renewal terms will eliminate purchase anxiety and lift conversion.",
  "Payment Gateways": "Checkout drop-off bottleneck: Repeated requests for localized payment options (UPI, PayPal) indicate lost revenue at final checkout. Integrating regional one-click payment gateways will directly reduce cart abandonment."
}}

{format_instructions}
""",
        ),
        ("human", "clustered data:{clustered_data}"),
    ]
)

cluster_chain = CLUSTER_PROMPT | llm | cluster_parser

summary_chain = SUMMARY_PROMPT | llm | summary_parser
