"""Agent Pydantic v2 schemas."""

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    case_id: int
    force_refresh: bool = False


class AnalyzeResponse(BaseModel):
    report: str | None = None
    model_used: str | None = None
    cached: bool = False
    fallback: bool = False
    error: str | None = None


class AgentHealthResponse(BaseModel):
    available: bool
