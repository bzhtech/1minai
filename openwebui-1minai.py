from pydantic import BaseModel, Field
import requests


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

    def pipe(self, body: dict, __user__: dict):
        headers = {"API-KEY": f"{self.valves.API_KEY}"}

        model_id = body["model"][body["model"].find(".") + 1 :]
        models = self.pipes()
        for model in models:
            if model["id"] == model_id:
                mod = model["name"]
        # print(model)
        # Update the model id in the body
        payload = {
            "model": mod,
            "type": "CHAT_WITH_AI",
            "promptObject": {"prompt": body["messages"][-1]["content"]},
        }
        try:
            r = requests.post(
                url=f"{self.valves.AI_API_BASE_URL}",
                json=payload,
                headers=headers,
                stream=True,
            )

            r.raise_for_status()
            if body.get("stream", False):
                return r.iter_lines()
            else:
                return r.json()
        except Exception as e:
            return f"Error: {e}"
