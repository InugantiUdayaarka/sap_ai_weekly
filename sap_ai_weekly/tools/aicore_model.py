"""
aicore_model.py
================
smolagents-compatible model wrapper that routes all LLM calls
to SAP AI Core GPT-4o via aicore_connector.call_llm().

Drop-in replacement for HfApiModel:
    model = AICoreGPT4oModel(max_tokens=7000, temperature=0.65)
    agent = CodeAgent(model=model, tools=[...])

No secrets here — all credential resolution is handled by
aicore_connector._enrich_from_vcap() + resolve_aicore().
"""

from typing import List, Optional

from smolagents.models import Model, ChatMessage

from tools.aicore_connector import call_llm


class AICoreGPT4oModel(Model):
    """
    smolagents Model subclass that delegates every __call__ to
    aicore_connector.call_llm(), which handles both DIRECT and
    DESTINATION modes transparently.
    """

    def __init__(self, max_tokens: int = 7000, temperature: float = 0.65):
        super().__init__()
        self.max_tokens  = max_tokens
        self.temperature = temperature
        print("[AICoreGPT4oModel] ✅ Initialized — will route via SAP AI Core GPT-4o")

    def __call__(
        self,
        messages: List[ChatMessage],
        stop_sequences: Optional[List[str]] = None,
        **kwargs,
    ) -> ChatMessage:
        """
        Called by CodeAgent on every LLM step.

        Converts smolagents ChatMessage list → OpenAI message dicts,
        calls AI Core via call_llm(), returns response as ChatMessage.
        """
        openai_messages = []
        for msg in messages:
            role    = getattr(msg, "role", "user")
            content = getattr(msg, "content", str(msg))

            # smolagents can pass content as a list of content blocks
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        parts.append(block.get("text", ""))
                    else:
                        parts.append(str(block))
                content = "\n".join(filter(None, parts))

            openai_messages.append({"role": role, "content": content})

        response_text = call_llm(
            messages=openai_messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return ChatMessage(role="assistant", content=response_text)
