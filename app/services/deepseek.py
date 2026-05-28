from typing import Optional

from loguru import logger
from openai import AsyncOpenAI
import httpx

from app.config import get_settings

settings = get_settings()

_STYLE_PROMPTS = {
    "casual": "你是一个普通Discord用户，用轻松随意的语气说话。",
    "formal": "你是一个专业的Discord社区成员，用语正式、礼貌。",
    "friendly": "你是一个非常友善热情的Discord用户，像一个好朋友一样说话。",
    "brief": "你是一个普通的Discord网友。用最简短的方式回复，一句话以内，别超过10个字。像真人随口说的，别加表情符号，别说自己是AI，别用括号。",
    "detailed": "回复可以稍微展开，但不要超过3句话。",
}


class DeepSeekService:
    def __init__(self) -> None:
        self._client: Optional[AsyncOpenAI] = None
        self._initialized = False

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            # 使用独立的 httpx 客户端，避免与 discord.py-self 的 SOCKS 代理冲突
            http_client = httpx.AsyncClient(proxy=None)
            self._client = AsyncOpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                http_client=http_client,
            )
        return self._client

    @property
    def is_available(self) -> bool:
        return bool(settings.deepseek_api_key and
                   settings.deepseek_api_key != "sk-your-deepseek-api-key")

    async def generate_message(
        self,
        prompt: str,
        *,
        context: Optional[str] = None,
        style: str = "casual",
        max_tokens: int = 500,
    ) -> dict:
        if not self.is_available:
            return {
                "success": False,
                "error": "DeepSeek API key not configured",
                "content": prompt,
            }

        style_instruction = _STYLE_PROMPTS.get(style, _STYLE_PROMPTS["casual"])

        system_msg = (
            f"{style_instruction}"
            "回复将在Discord中发送。不要使用markdown表格、代码块或过长的格式。"
            "保持回复自然真实，像真人聊天一样。"
            "不要说'作为一个AI'之类的话，也不要暴露自己是AI身份。"
        )

        messages = [
            {"role": "system", "content": system_msg},
        ]
        if context:
            messages.append({
                "role": "system",
                "content": f"对话上下文/参考信息:\n{context}",
            })
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=settings.deepseek_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.8,
            )
            content = response.choices[0].message.content or ""
            content = content.strip().strip('"').strip("'")

            return {
                "success": True,
                "content": content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                },
            }
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": prompt,
            }

    async def check_health(self) -> dict:
        if not self.is_available:
            return {"status": "disabled", "message": "API key not configured"}
        try:
            await self.client.models.list()
            return {"status": "healthy", "model": settings.deepseek_model}
        except Exception as e:
            return {"status": "error", "message": str(e)}


deepseek_service = DeepSeekService()
