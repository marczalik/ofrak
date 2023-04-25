from dataclasses import dataclass

from ofrak import Resource
from ofrak.core.strings import AsciiString
from ofrak.component.modifier import Modifier
from ofrak.model.component_model import ComponentConfig


@dataclass
class SassyStringModifierConfig(ComponentConfig):
    pass


class SassyStringModifier(Modifier[SassyStringModifierConfig]):
    targets = (AsciiString,)

    async def modify(self, resource: Resource, config: SassyStringModifierConfig) -> None:
        # Call ChatGPT API to sassify an individual string
        pass
