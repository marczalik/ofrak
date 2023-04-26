import logging
import openai

from dataclasses import dataclass

from ofrak import Resource
from ofrak.component.analyzer import Analyzer
from ofrak.core.complex_block import ComplexBlock
from ofrak_chatgpt.chatgpt import ChatGPTAnalysis, ChatGPTConfig

LOGGER = logging.getLogger(__name__)


@dataclass
class ChatGPTFunctionAnalyzerConfig(ChatGPTConfig):
    pass


class ChatGPTFunctionAnalyzer(Analyzer[ChatGPTFunctionAnalyzerConfig, ChatGPTAnalysis]):
    targets = (ComplexBlock,)
    outputs = (ChatGPTAnalysis,)

    async def analyze(
        self, resource: Resource, config: ChatGPTFunctionAnalyzerConfig
    ) -> ChatGPTAnalysis:
        if not config:
            config = ChatGPTFunctionAnalyzerConfig()
        cb = await resource.view_as(ComplexBlock)
        assembly = await cb.get_assembly()
        response = openai.ChatCompletion.create(
            model=config.model,
            temperature=1,
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": f"In plain English, tell me what this function does and then convert it to equivalent C without using inline assembly: {assembly}",
                }
            ],
        )
        return ChatGPTAnalysis(response.choices[0].message.content)
