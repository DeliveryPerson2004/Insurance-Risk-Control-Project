"""DeepSeek V4 Flash Agent 实现."""

import logging
from datetime import datetime, timezone

import httpx

from backend.app.config import settings
from backend.app.agent.interface import BaseAgent, CaseContext, AgentReport
from backend.app.agent.prompts.fraud_analysis import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class DeepSeekAgent(BaseAgent):
    """DeepSeek V4 Flash 实现."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "deepseek-chat",
        timeout: float = 30.0,
    ):
        self._api_key = api_key or getattr(settings, "DEEPSEEK_API_KEY", "")
        if not self._api_key:
            logger.warning("DEEPSEEK_API_KEY not configured, agent will be unavailable")
        self._base_url = base_url or getattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self._model = model
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def generate_report(self, case: CaseContext) -> AgentReport:
        """调用 DeepSeek API 生成分析报告."""
        user_prompt = build_user_prompt(case)

        try:
            client = await self._get_client()
            response = await client.post(
                "/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1024,
                },
            )
            response.raise_for_status()
            data = response.json()

            report_text = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            generated_at = datetime.now(timezone.utc).isoformat()

            logger.info(
                "Agent report generated for case %d: %d tokens used",
                case.case_id, tokens_used,
            )

            return AgentReport(
                report_text=report_text,
                model_used=self._model,
                tokens_used=tokens_used,
                generated_at=generated_at,
            )

        except httpx.TimeoutException:
            logger.error("Agent API timeout for case %d", case.case_id)
            raise
        except httpx.HTTPStatusError as e:
            logger.error("Agent API error for case %d: %s", case.case_id, str(e))
            raise
        except Exception as e:
            logger.exception("Agent unexpected error for case %d", case.case_id)
            raise

    async def health_check(self) -> bool:
        """通过轻量 API 调用检查服务可用性.

        Uses max_tokens=1 to minimize token consumption (~1 token per check).
        """
        try:
            client = await self._get_client()
            response = await client.post(
                "/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """关闭 HTTP 客户端."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# ---- 模块级单例 ----
_agent_instance: DeepSeekAgent | None = None


def get_agent() -> DeepSeekAgent:
    """获取 Agent 单例."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DeepSeekAgent()
    return _agent_instance
