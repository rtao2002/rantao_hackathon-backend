from datetime import datetime
from typing import List

from pydantic import BaseModel

class AIQuestionCheckRequest(BaseModel):
    title: str
    body: str

class QuestionCreate(BaseModel):
    title: str
    body: str
    category: str = "other"

class AnswerCreate(BaseModel):
    body: str


class SimilarQuestionRequest(BaseModel):
    title: str
    body: str


class AnswerResponse(BaseModel):
    id: int
    question_id: int
    body: str
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    id: int
    title: str
    body: str
    category: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionDetailResponse(BaseModel):
    question: QuestionResponse
    answers: List[AnswerResponse]