from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.models import UserRequest
from app.runtime import build_navigator_from_env


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="自然言語の申請相談")
    applicant: str | None = None
    department: str | None = None


app = FastAPI(title="社内申請ナビゲーター API", version="0.34.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat/demo")
def chat_demo(request: ChatRequest) -> dict[str, object]:
    navigator = build_navigator_from_env()
    response = navigator.handle(
        UserRequest(
            message=request.message,
            applicant=request.applicant,
            department=request.department,
        )
    )
    return response.to_dict()
