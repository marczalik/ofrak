import logging
import openai

from dataclasses import dataclass

from ofrak import Resource
from ofrak.core.strings import AsciiString, StringPatchingConfig, StringPatchingModifier
from ofrak.component.modifier import Modifier
from ofrak_chatgpt.chatgpt import ChatGPTConfig
import time

LOGGER = logging.getLogger(__name__)


@dataclass
class SassyStringModifierConfig(ChatGPTConfig):
    min_length: int = 50


class SassyStringModifier(Modifier[SassyStringModifierConfig]):
    targets = (AsciiString,)

    async def modify(self, resource: Resource, config: SassyStringModifierConfig) -> None:
        string = await resource.view_as(AsciiString)
        text = string.Text
        text_length = len(text)

        if text_length >= config.min_length:
            # Assume strings without spaces must remain space-free
            if " " not in text:
                messages = [
                    {
                        "role": "user",
                        "content": f"Make this variable name sassy: {text}. Your response must be a valid variable name that is {text_length} characters long.",
                    },
                ]
            else:
                messages = [
                    {
                        "role": "user",
                        "content": f"Make this text sassy: {text}. Your response must be {text_length} characters long.",
                    },
                ]
            try:
                response = openai.ChatCompletion.create(
                    model=config.model, temperature=1, max_tokens=text_length * 2, messages=messages
                )
                if response:
                    print(f"original text: {text}")
                    print(f"chatgpt response: {response.choices[0].message.content}")
                # Truncate response if necessary
                data = response.choices[0].message.content[: text_length - 1]
                string_patch_config = StringPatchingConfig(offset=0, string=data)
                await resource.run(StringPatchingModifier, string_patch_config)
                time.sleep(20)
            except Exception as e:
                LOGGER.warning(f"Exception {e} occurred, skipped {text}")
