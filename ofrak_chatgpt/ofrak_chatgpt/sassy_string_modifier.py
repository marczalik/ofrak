import openai

from dataclasses import dataclass

from ofrak import Resource
from ofrak.core.strings import AsciiString
from ofrak.component.modifier import Modifier
from ofrak_chatgpt.chatgpt import ChatGPTModifierConfig


@dataclass
class SassyStringModifierConfig(ChatGPTModifierConfig):
    pass


class SassyStringModifier(Modifier[SassyStringModifierConfig]):
    targets = (AsciiString,)
    outputs = (AsciiString,)

    async def modify(self, resource: Resource, config: SassyStringModifierConfig) -> None:
        # Call ChatGPT API to sassify an individual string
        string = resource.view_as(AsciiString)
        text = string.Text
        response = openai.ChatCompletion.create(
            model=config.model,
            temperature=1,
            max_tokens=len(text) * 2,
            messages=[
                {"role": "user", "content": f"Make this text sassy: {text}"},
                {
                    "role": "system",
                    "content": "You are a sassy person who loves to spice up text with your sassy attitude. Your responses contain only ASCII text.",
                },
            ],
        )
        print(f"chatgpt response: {response.choice[0].message.content}")
        return AsciiString(response.choices[0].message.content)
