from pydantic import BaseModel, Field
import requests
from typing import Optional, Union, Generator, Iterator, List, Dict
import json

DEBUG = False

class Pipe:
    class Valves(BaseModel):
        AI_API_BASE_URL: str = Field(
            default="https://api.1min.ai/api/features?isStreaming=true",
            description="Base URL for accessing OpenAI API endpoints.",
        )
        API_KEY: str = Field(
            default="",
            description="API key for authenticating requests to the API.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.type = "manifold"

    def _debug(self, message: str):
        """Prints debug messages if DEBUG is enabled."""
        if DEBUG:
            print(f" DEBUG {message}")

    def _get_headers(self) -> Dict[str, str]:
        """Returns the headers for API requests."""
        if not self.valves.API_KEY:
            raise ValueError(
                "API_KEY is not set. Please configure the environment variable."
            )
        return {
            "API-KEY": f"{self.valves.API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _handle_response(self, response: requests.Response) -> dict:
        """Handles and parses API responses."""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            self._debug(f"HTTPError: {e.response.text}")
            raise
        except ValueError as e:
            self._debug(f"Invalid JSON response: {response.text}")
            raise

    def pipes(self):
        if self.valves.API_KEY:
            return [
                {"id": "GPT4o_MINI", "name": "gpt-4o-mini"},
                {"id": "CLAUDE3_5_SONNET", "name": "claude-3-5-sonnet-20240620"},
                {"id": "MISTRAL_SMALL", "name": "mistral-small-latest"},
            ]
        else:
            return [
                {
                    "id": "error",
                    "name": "API Key not provided.",
                },
            ]

    def pipe(self, body: dict) -> Union[str, Generator[str, None, None]]:
        """Handles a single request to the pipe."""
        try:
            model_id = body["model"][body["model"].find(".") + 1 :]
            models = self.pipes()
            for model in models:
                if model["id"] == model_id:
                    mod = model["name"]
            model = mod
            messages = body["messages"]

            if messages:
                return self.stream_response(model, messages)
            return self.get_completion(model, messages)

        except KeyError as e:
            error_msg = f"Missing required key in body: {e}"
            self._debug(error_msg)
            return f"Error: {error_msg}"
        except Exception as e:
            self._debug(f"Error in pipe method: {e}")
            return f"Error: {e}"

    def stream_response(
        self, model: str, messages: List[dict], retries: int = 5
    ) -> Generator[str, None, None]:
        """Streams a response from the Mistral API, handling rate limits."""
        url = f"{self.valves.AI_API_BASE_URL}"

        payload = {
            "model": model,
            "type": "CHAT_WITH_AI",
            "promptObject": {"prompt": messages[-1]["content"]},
        }

        self._debug(f"Streaming response from {url}")

        for attempt in range(retries):
            try:
                response = requests.post(
                    url, json=payload, headers=self._get_headers(), stream=True
                )
                response.raise_for_status()

                for line in response.iter_lines():
                    if line:
                        try:
                            yield f"{line.decode()}\n"
                        except requests.RequestException as e:
                            self._debug(f"Failed to decode stream line: {line}")
                            continue
                return  # Exit after successful streaming
            except requests.RequestException as e:
                if response.status_code == 429 and attempt < retries - 1:
                    wait_time = 2**attempt
                    self._debug(
                        f"Rate limited (429). Retrying after {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
                else:
                    self._debug(f"Stream request failed: {e}")
                    yield f"Error: {str(e)}"

    def get_completion(self, model: str, messages: List[dict], retries: int = 3) -> str:
        """Fetches a single completion response, handling rate limits."""
        url = f"{self.valves.AI_API_BASE_URL}"

        payload = {
            "model": model,
            "type": "CHAT_WITH_AI",
            "promptObject": {"prompt": messages[-1]["content"]},
        }

        for attempt in range(retries):
            try:
                self._debug(
                    f"Attempt {attempt + 1}: Sending completion request to {url}"
                )
                response = requests.post(url, json=payload, headers=self._get_headers())
                data = self._handle_response(response)
                return data["message"][0]["content"]
            except requests.RequestException as e:
                if response.status_code == 429 and attempt < retries - 1:
                    wait_time = 2**attempt
                    self._debug(
                        f"Rate limited (429). Retrying after {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
                else:
                    self._debug(f"Completion request failed: {e}")
                    return f"Error: {str(e)}"
