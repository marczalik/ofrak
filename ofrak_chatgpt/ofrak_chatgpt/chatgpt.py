import os
import time

from dataclasses import dataclass
from openai.error import RateLimitError
from typing import Optional

from ofrak.model.component_model import ComponentConfig
from ofrak.model.resource_model import ResourceAttributes


@dataclass
class ChatGPTConfig(ComponentConfig):
    api_key: str = os.getenv("OPENAI_API_KEY")
    model: str = "gpt-3.5-turbo"
    system_message: Optional[str] = None
    temperature: int = 1


@dataclass
class ChatGPTAnalysis(ResourceAttributes):
    description: str


# From https://github.com/openai/openai-cookbook/blob/main/examples/How_to_handle_rate_limits.ipynb
def retry_with_exponential_backoff(
    func,
    initial_delay: float = 1,
    exponential_base: float = 2,
    max_retries: int = 10,
    errors: tuple = (RateLimitError,),
):
    """Retry a function with exponential backoff."""

    def wrapper(*args, **kwargs):
        if exponential_base < 1:
            raise Exception(
                f"Backoff must exponentially increase, {exponential_base} must be greater than or equal to 1."
            )
        num_retries = 0
        delay = initial_delay

        # Loop until a successful response or max_retries is hit or an exception is raised
        while num_retries < max_retries:
            try:
                return func(*args, **kwargs)

            # Retry on specified errors
            except errors as e:
                num_retries += 1

                if num_retries >= max_retries:
                    raise Exception(f"Maximum number of retries ({max_retries}) exceeded.")

                delay *= exponential_base
                time.sleep(delay)

            # Raise exceptions for any errors not specified
            except Exception as e:
                raise e

    return wrapper
