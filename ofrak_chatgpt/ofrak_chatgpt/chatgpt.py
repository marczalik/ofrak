import os

from dataclasses import dataclass


from ofrak.model.component_model import ComponentConfig
from ofrak.model.resource_model import ResourceAttributes


@dataclass
class ChatGPTConfig(ComponentConfig):
    api_key: str = os.getenv("OPENAI_API_KEY")
    model: str = "gpt-3.5-turbo"


@dataclass
class ChatGPTAnalysis(ResourceAttributes):
    description: str
