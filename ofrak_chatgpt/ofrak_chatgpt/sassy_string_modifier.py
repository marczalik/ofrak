import logging
import openai

from dataclasses import dataclass
from tiktoken import Encoding, encoding_for_model
from typing import List, Optional

from ofrak import Resource
from ofrak.core.strings import AsciiString, StringPatchingConfig, StringPatchingModifier
from ofrak.component.modifier import Modifier
from ofrak_chatgpt.chatgpt import ChatGPTConfig, retry_with_exponential_backoff

LOGGER = logging.getLogger(__name__)


@dataclass
class SassyStringModifierConfig(ChatGPTConfig):
    min_length: int = 50
    encoding: Encoding = encoding_for_model(ChatGPTConfig.model)
    max_retries: int = 3


class SassyStringModifier(Modifier[SassyStringModifierConfig]):
    targets = (AsciiString,)

    async def modify(self, resource: Resource, config: SassyStringModifierConfig) -> None:
        string = await resource.view_as(AsciiString)
        text = string.Text
        text_length = len(text)
        num_tokens = len(config.encoding.encode(text))

        if text_length >= config.min_length:
            # Assume strings without spaces must remain space-free
            if " " not in text:
                pass
                # result = await self.modify_identifier(text, text_length, num_tokens, config)
            else:
                result = await self.modify_string(text, text_length, num_tokens, config)
                if result:
                    string_patch_config = StringPatchingConfig(offset=0, string=result)
                    await resource.run(StringPatchingModifier, string_patch_config)

    async def modify_identifier(
        self, text: str, text_length: int, num_tokens: int, config: SassyStringModifierConfig
    ) -> str:
        history = [
            {
                "role": "user",
                "content": f"You are a sassy person. I will send a message and you will respond by making the text of the message more sassy.\
                                The sassy text you generate must be shorter or equal to the length to the length of the original message.\
                                It is EXTREMELY important that your sassy version is shorter than the original and contains only ASCII characters.\
                                If you understand, make the following message more sassy:{text}",
            },
        ]

        try:
            response = self.get_chatgpt_response(history, num_tokens * 2, config)

            if response:
                print(f"original text: {text}")
                print(f"chatgpt response: {response.choices[0].message.content}")
                while (
                    len(response.choices[0].message.content) > text_length
                    or " " in response.choices[0].message.content
                ):
                    history.extend(
                        [
                            {"role": "assistant", "content": response.choices[0].message.content},
                            {
                                "role": "user",
                                "content": f"Make it shorter and without spaces.",
                            },
                        ]
                    )
                    try:
                        response = self.get_chatgpt_response(history, text_length * 2, config)

                        print(f"original text: {text}")
                        print(f"chatgpt response: {response.choices[0].message.content}")
                    except Exception as e:
                        LOGGER.warning(f"Exception {e} occurred, skipped {text}")

            return response.choices[0].message.content[: text_length - 1]

        except Exception as e:
            LOGGER.warning(f"Exception {e} occurred, skipped {text}")

    async def modify_string(
        self, text: str, text_length: int, num_tokens: int, config: SassyStringModifierConfig
    ) -> str:
        history = [
            {
                "role": "user",
                "content": f"You are a sassy person. I will send a message and you will respond by making the text of the message more sassy.\
                                The sassy text you generate must be shorter or equal to the length to the length of the original message.\
                                It is EXTREMELY important that your sassy version is shorter than the original and contains only ASCII characters.\
                                If the input string contains any C format specifiers, then it is EXTREMELY important that your response contains the\
                                same specifiers in the same order.\
                                If you understand, make the following message more sassy:{text}",
            },
        ]
        try:
            response = self.get_chatgpt_response(history, num_tokens * 2, config)

            if response:
                retries = 0
                print(f"original text: {text}")
                print(f"chatgpt response: {response.choices[0].message.content}")
                while (
                    len(response.choices[0].message.content) > text_length
                    and retries < config.max_retries
                ):
                    retries += 1
                    history.extend(
                        [
                            {"role": "assistant", "content": response.choices[0].message.content},
                            {
                                "role": "user",
                                "content": f"Make it shorter.",
                            },
                        ]
                    )
                    try:
                        response = self.get_chatgpt_response(history, text_length * 2, config)

                        print(f"original text: {text}")
                        print(f"chatgpt response: {response.choices[0].message.content}")
                    except Exception as e:
                        LOGGER.warning(f"Exception {e} occurred, skipped {text}")

            return response.choices[0].message.content[: text_length - 1]

        except Exception as e:
            LOGGER.warning(f"Exception {e} occurred, skipped {text}")

    def get_chatgpt_response(
        self, history: List[str], max_tokens: int, config: SassyStringModifierConfig
    ) -> Optional[str]:
        @retry_with_exponential_backoff
        def retry_response(**kwargs) -> Optional[str]:
            return openai.ChatCompletion.create(**kwargs)

        return retry_response(
            model=config.model,
            temperature=config.temperature,
            max_tokens=max_tokens,
            messages=[message for message in history],
        )
