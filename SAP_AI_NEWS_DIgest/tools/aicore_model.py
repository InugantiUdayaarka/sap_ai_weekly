from smolagents.models import Model, ChatMessage
from tools.aicore_connector import AICoreDestinationConnector
from typing import List, Optional


class AICoreGPT4oModel(Model):
    """
    smolagents-compatible model class that routes all LLM calls
    to SAP AI Core GPT-4o via BTP Destination Service or direct credentials.

    Drop-in replacement for HfApiModel in any CodeAgent setup.

    Usage:
        model = AICoreGPT4oModel(max_tokens=7000, temperature=0.65)
        agent = CodeAgent(model=model, tools=[...])
    """

    def __init__(self, max_tokens: int = 7000, temperature: float = 0.65):
        super().__init__()
        self.max_tokens  = max_tokens
        self.temperature = temperature
        self.connector   = AICoreDestinationConnector()
        print("[AICoreGPT4oModel] ✅ Initialized — routing via SAP AI Core GPT-4o")

    def __call__(
        self,
        messages: List[ChatMessage],
        stop_sequences: Optional[List[str]] = None,
        **kwargs
    ) -> ChatMessage:
        """
        Called by CodeAgent on every LLM step.
        Converts smolagents message format → OpenAI format,
        calls AI Core, returns response as ChatMessage.
        """

        # Convert smolagents ChatMessage list → OpenAI messages format
        openai_messages = []
        for msg in messages:
            role    = getattr(msg, "role", "user")
            content = getattr(msg, "content", str(msg))

            # smolagents can pass content as a list of content blocks
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        text_parts.append(block.get("text", ""))
                    else:
                        text_parts.append(str(block))
                content = "\n".join(filter(None, text_parts))

            openai_messages.append({
                "role":    role,
                "content": content
            })

        # Call SAP AI Core GPT-4o
        response_text = self.connector.chat_completion(
            messages=openai_messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )

        return ChatMessage(role="assistant", content=response_text)
