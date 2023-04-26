import openai
import os

from dataclasses import dataclass

from ofrak import Resource
from ofrak.component.modifier import Modifier
from ofrak.model.component_model import ComponentConfig, ComponentExternalTool


CHATGPT = ComponentExternalTool("openai", "https://chat.openai.com/chat", "--help")
openai.api_key = os.getenv("OPENAI_API_KEY")


@dataclass
class ChatGPTModifierConfig(ComponentConfig):
    api_key: str = os.getenv("OPENAI_API_KEY")
    model: str = "gpt-3.5-turbo"


class ChatGPTModifier(Modifier[ChatGPTModifierConfig]):
    external_dependencies = (CHATGPT,)

    async def modify(self, resource: Resource, config: ChatGPTModifierConfig) -> None:
        #
        pass
