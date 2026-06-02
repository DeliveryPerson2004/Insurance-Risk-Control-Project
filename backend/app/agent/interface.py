"""BaseAgent 抽象类 + CaseContext 数据类."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CaseContext:
    """传给 Agent 的案件关键信息."""
    case_id: int
    fraud_prob: float
    risk_level: str
    threshold_used: float
    claim_amount: float | None
    icd10_chapter: str | None = None
    shap_top10: list[dict] = field(default_factory=list)


@dataclass
class AgentReport:
    """Agent 返回的分析报告."""
    report_text: str
    model_used: str
    tokens_used: int
    generated_at: str  # ISO format


class BaseAgent(ABC):
    """LLM Agent 抽象基类."""

    @abstractmethod
    async def generate_report(self, case: CaseContext) -> AgentReport:
        """生成 AI 分析报告."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """检查 Agent 服务是否可用."""
        ...
