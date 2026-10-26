from pydantic import BaseModel, Field


class QuestionTopic(BaseModel):
    question: str
    topic: str = Field(default="General Inquiry")


class QuestionTopicResponse(BaseModel):
    questions: list[QuestionTopic]
    topics_used: list[str] = Field(default_factory=list)


class TopicInsight(BaseModel):
    topic_name: str
    insight: str


class TopicInsightResponse(BaseModel):
    topics: list[TopicInsight]
