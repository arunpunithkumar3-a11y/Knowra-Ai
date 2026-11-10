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
You are a customer question classifier for a business analytics platform.

Your task is to assign ONE clear, natural business topic to each customer question.

Rules:
- Assign exactly one topic to each question.
- Topics must be clean, natural, and standard business categories (2–4 words, e.g., 'Payment Options', 'Order Tracking', 'Delivery & Shipping', 'Pricing & Discounts', 'Product Details', 'Return & Refund Policy', 'Customer Support', 'Store Location & Hours').
- Group similar questions under the same standard topic name.
- Do not create overly narrow or overly broad/vague topics.
- Do not include explanations, punctuation, or numbers in topic names.
- Return a topic for every question in the exact same order as input.

Examples:
"Can I pay with Google Pay or UPI?" -> "Payment Options"
"Where is my package right now?" -> "Order Tracking"
"Do you offer any discounts for students?" -> "Pricing & Discounts"
"How do I return a damaged item?" -> "Return & Refund Policy"
"What are your working hours on weekends?" -> "Store Location & Hours"

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
You are a practical Business Intelligence and Customer Insights Advisor. Your job is to analyze real customer questions grouped by topic and provide clear, actionable business insights to the business owner.

You will receive a JSON dictionary where:
- Each KEY is a topic name.
- Each VALUE is the list of questions asked by customers under that topic.

### Goals for the Business Insight:
For every topic, give the business owner a realistic, highly useful 2–3 sentence insight that explains:
1. Customer Demand / Pattern: What are customers asking about or looking for in plain, direct language?
2. Business Impact: Why does this matter for sales, customer trust, retention, or support workload?
3. Actionable Recommendation: What specific, practical step should the business owner take to address this (e.g., update website/checkout, add clear FAQs, provide proactive notifications, adjust pricing/policies, or offer requested features)?

### Rules:
- Speak directly to the business owner in a clear, pragmatic, professional tone.
- Keep it grounded in the actual questions asked. DO NOT make up exaggerated theories, corporate buzzwords, or psychoanalyze customer emotions.
- Avoid consulting jargon (e.g., do NOT use phrases like 'communication deficit', 'friction diagnosis', 'anxiety trigger', 'prescriptive business action').
- For casual greetings or test messages (e.g. 'hi', 'test', 'hello'), provide a brief note: "Casual greetings and test queries with no action required."
- Output ONLY a valid JSON object mapping each `"Topic Name"` to its `"Insight String"`.

### Examples:

Input:
{{
  "Payment Options": ["Can I pay via UPI?", "Do you take credit cards?", "Is cash on delivery available?"]
}}
Output:
{{
  "Payment Options": "Customers are actively inquiring about available payment methods before completing their purchase. Displaying accepted payment methods (like UPI, cards, and COD) clearly on your product and checkout pages will eliminate buyer hesitation and increase completed sales."
}}

Input:
{{
  "Shipping & Delivery": ["How long does delivery take to Mumbai?", "Do you have express shipping?", "Where is my tracking number?"]
}}
Output:
{{
  "Shipping & Delivery": "Buyers frequently ask about delivery timelines and tracking details. Displaying estimated delivery dates on product pages and sending automated tracking updates via SMS or WhatsApp will reassure customers and drastically reduce repetitive status inquiries."
}}

Input:
{{
  "Pricing & Discounts": ["Is there any student discount?", "Can I get a coupon code for my first order?", "Any bulk order discounts?"]
}}
Output:
{{
  "Pricing & Discounts": "Customers are showing strong buying intent but are looking for promotional or volume discounts before committing. Offering a visible first-order welcome discount or displaying clear tier-based pricing can help convert these high-intent shoppers into paying customers."
}}

{format_instructions}
""",
        ),
        ("human", "clustered data:{clustered_data}"),
    ]
)

cluster_chain = CLUSTER_PROMPT | llm | cluster_parser

summary_chain = SUMMARY_PROMPT | llm | summary_parser
