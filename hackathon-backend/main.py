import re

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database import engine, get_db
from models import Base, Question, Answer
from schemas import QuestionCreate, AnswerCreate, SimilarQuestionRequest
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from openai import OpenAI
from schemas import AIQuestionCheckRequest

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://rantao-hackathon-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


def tokenize_text(text: str):
    text = text.lower()
    text = re.sub(r"[^a-zA-Z0-9ぁ-んァ-ン一-龥]+", " ", text)
    words = text.split()
    return set(words)


def calculate_similarity(text1: str, text2: str):
    words1 = tokenize_text(text1)
    words2 = tokenize_text(text2)

    if not words1 or not words2:
        return 0

    overlap = words1.intersection(words2)
    union = words1.union(words2)

    return len(overlap) / len(union)


@app.get("/")
def root():
    return {"message": "Hackathon Q&A backend with Cloud SQL is running"}


@app.get("/questions")
def get_questions(db: Session = Depends(get_db)):
    questions = db.query(Question).order_by(Question.created_at.desc()).all()
    return questions


@app.post("/questions")
def create_question(question: QuestionCreate, db: Session = Depends(get_db)):
    new_question = Question(
        title=question.title,
        body=question.body,
        category=question.category,
    )

    db.add(new_question)
    db.commit()
    db.refresh(new_question)

    return new_question


@app.post("/questions/check-similar")
def check_similar_questions(
    request: SimilarQuestionRequest,
    db: Session = Depends(get_db),
):
    input_text = request.title + " " + request.body

    questions = db.query(Question).all()

    similar_questions = []

    for question in questions:
        existing_text = question.title + " " + question.body
        score = calculate_similarity(input_text, existing_text)

        if score > 0:
            similar_questions.append({
                "id": question.id,
                "title": question.title,
                "body": question.body,
                "similarity_score": round(score, 3),
            })

    similar_questions = sorted(
        similar_questions,
        key=lambda x: x["similarity_score"],
        reverse=True,
    )

    return {
        "input_title": request.title,
        "similar_questions": similar_questions[:5],
    }

@app.get("/questions/search")
def search_questions(q: str, db: Session = Depends(get_db)):
    questions = (
        db.query(Question)
        .filter(
            (Question.title.contains(q)) |
            (Question.body.contains(q))
        )
        .order_by(Question.created_at.desc())
        .all()
    )
    return questions
    
@app.get("/questions/{question_id}")
def get_question(question_id: int, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()

    if question is None:
        return {"error": "Question not found"}

    return {
        "question": question,
        "answers": question.answers,
    }


@app.post("/questions/{question_id}/answers")
def create_answer(
    question_id: int,
    answer: AnswerCreate,
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()

    if question is None:
        return {"error": "Question not found"}

    new_answer = Answer(
        question_id=question_id,
        body=answer.body,
    )

    db.add(new_answer)
    db.commit()
    db.refresh(new_answer)

    return new_answer

@app.get("/questions/{question_id}/answers")
def get_answers(
    question_id: int,
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()

    if question is None:
        return {"error": "Question not found"}

    answers = (
        db.query(Answer)
        .filter(Answer.question_id == question_id)
        .order_by(Answer.created_at.desc())
        .all()
    )

    return answers

@app.post("/ai/check-question")
def check_question_with_ai(request: AIQuestionCheckRequest):
    prompt = f"""
You are an assistant for a university student Q&A website.

Check the following question before it is posted.

Title:
{request.title}

Body:
{request.body}

Evaluate:
1. Is it appropriate for a student Q&A site?
2. Is it clear enough?
3. Choose exactly one category from the following:
   - class: classes, lectures, courses, exams, homework, assignments, credits, grading, course registration
   - research: research, labs, experiments, professors, papers, thesis, graduate research
   - life: student life, clubs, circles, housing, food, campus life, daily concerns
   - admin: university procedures, documents, applications, offices, deadlines, certificates
   - career: jobs, internships, graduate school choices, career paths, future plans
   - other: only if none of the above clearly applies
4. Is there any concern before posting?

Do not rewrite the user's question.

Return JSON only with this exact structure:
{{
  "is_appropriate": true,
  "appropriateness_reason": "short reason",
  "is_clear": true,
  "clarity_reason": "short reason",
  "category": "class",
  "warning": "short warning if needed, otherwise empty string"
}}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    try:
        return json.loads(response.output_text)
    except json.JSONDecodeError:
        return {
            "is_appropriate": None,
            "appropriateness_reason": "AI returned non-JSON output.",
            "is_clear": None,
            "clarity_reason": "",
            "category": "other",
            "warning": "",
            "raw_output": response.output_text,
        }