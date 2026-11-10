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
- Name topics objectively and constructively based on customer need or business domain (e.g., 'Payment Options', 'Order Tracking', 'Product Inquiries').
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
→ "Refund Policy"
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
You are a Senior Customer Intelligence & Business Growth Advisor advising business owners and executive leadership.

You will receive a dictionary where:
- Each KEY is a customer question cluster/topic.
- Each VALUE is the list of raw customer questions in that cluster.

Your mission is to provide valuable, constructive CUSTOMER INSIGHTS to the business owner.
Instead of criticizing, judging, or fault-finding the questions or customers, interpret customer inquiries as valuable market signals, user needs, and commercial growth opportunities.

### Analytical Framework:
For every topic in the dictionary, evaluate the questions through these strategic lenses:
1. Customer Intent & Demand: What are customers actively seeking, inquiring about, or trying to achieve? What matters most to them?
2. Business Opportunity & Commercial Impact: How does customer clarity in this area affect purchase confidence, brand loyalty, conversion, and repeat business?
3. Actionable Business Recommendations: What concrete, practical enhancements (e.g., proactive communication, clear self-serve information, product clarity, or service offerings) can the business owner implement to delight customers and maximize business growth?

### Output Formatting Rules:
- Return ONLY a single flat JSON object (dictionary) mapping:
  `"Topic Title"` -> `"Strategic Customer Insight String"`
- Structure each insight in 2–3 concise, high-impact sentences following this formula:
  [Customer Need & Intent Analysis] + [Business Value / Growth Opportunity] + [Actionable Recommendation for Business Owner].
- STRICT GUIDELINES:
  * Maintain an empowering, professional, and constructive advisory tone.
  * DO NOT criticize, judge, patronize, or mock customers for their questions or phrasing.
  * DO NOT treat customer questions as failures, deficits, or defects—view them as engagement and conversion opportunities.
  * NEVER begin insights with "Customers are asking about...", "This topic covers...", or "Users want...".
  * For general greetings, test queries, or casual remarks, provide a brief, professional note (e.g., "Casual engagement or test inquiries with no specific product or operational action needed.").
  * Process EVERY topic in the dictionary.

Example format:
{{
  "Delivery & Tracking": "Strong customer demand for delivery transparency: Inquiries show buyers place high importance on real-time fulfillment status post-purchase. Providing clear estimated delivery dates at checkout and proactive SMS or WhatsApp shipping updates will reinforce buyer trust and reduce repetitive inquiries.",
  "Subscription & Billing": "High purchase intent seeking billing clarity: Customers are actively evaluating plan terms before committing to recurring payments. Displaying an intuitive monthly vs. annual pricing comparison with transparent renewal terms will remove purchase hesitation and accelerate sign-ups.",
  "Payment Methods": "High-intent checkout opportunity: Repeated inquiries regarding local payment options (e.g., UPI, digital wallets) demonstrate ready-to-buy customer demand. Prominently featuring supported payment options and offering popular local gateways will streamline the purchase journey and boost completed transactions."
}}

{format_instructions}
""",
        ),
        ("human", "clustered data:{clustered_data}"),
    ]
)

cluster_chain = CLUSTER_PROMPT | llm | cluster_parser

summary_chain = SUMMARY_PROMPT | llm | summary_parser
