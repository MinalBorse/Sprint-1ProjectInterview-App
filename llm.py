"""Talks to the AI model through OpenRouter."""
# The text in triple quotes above is a "docstring": a note saying what this file is for.

# ----- Imports: bring in the tools this file needs -----
# Built into Python: turns JSON text into Python dictionaries and lists.
import json

# Built into Python: lets us read environment variables (hidden settings, like our key).
import os

# Installed with uv: load_dotenv reads the .env file.
from dotenv import load_dotenv

# Installed with uv: OpenAI is the tool that sends messages to the model.
from openai import OpenAI

# ----- Load the key -----

# Copy each line of .env (like OPENROUTER_API_KEY=...) into the environment variables.
# After this, the key is available to the program without being written in the code.
load_dotenv()


# ----- Settings -----

# Which model to use, as an OpenRouter "slug": company/model.
# In CAPITALS because it's a constant: it never changes while the app runs.
MODEL = "openai/gpt-5-mini"


# The models this app may use, with a label for the menu.
# This is a dictionary:
#   the key (left) is the OpenRouter "slug", which the API needs;
#   the value (right) is the friendly name the user sees in the menu.
MODELS = {
    "openai/gpt-5-mini": "GPT-5 mini (default, balanced)",
    "openai/gpt-5-nano": "GPT-5 nano (fastest, cheapest)",
}

# How much the model may think before answering, from least to most.
# This is a list: the order here is the order shown in the menu.
REASONING_EFFORTS = ["minimal", "low", "medium", "high"]

# ----- Get the key, and stop early if it's missing -----

# Ask the environment for the value called OPENROUTER_API_KEY.
# If it doesn't exist, we get None (Python's word for "nothing").
api_key = os.getenv("OPENROUTER_API_KEY")

# If there's no key, stop right now with a clear message ("fail early").
# Without this, we'd still get an error later, but a confusing one.
if not api_key:
    raise RuntimeError("OPENROUTER_API_KEY is missing. Add it to your .env file.")


# ----- Create the connection -----

# The client is the object that talks to the model. It's created once and reused.
# base_url: send requests to OpenRouter instead of OpenAI (they use the same format).
# api_key: our key, which proves we're allowed to use it.
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


# ----- The function the rest of the app will use -----


def ask_model(messages, model=MODEL, max_tokens=2000, reasoning_effort=None):
    """Send the conversation to the model and return its reply as text.

    messages is a list of dictionaries, one per message, for example:
      {"role": "system", "content": "You are an interviewer..."}
      {"role": "user", "content": "My answer is..."}

    model, max_tokens and reasoning_effort are optional. If a call doesn't
    pass them, the defaults after "=" are used, so older code that only
    passes messages (like redteam.py) works exactly as before.
    reasoning_effort=None means "don't send it": the model uses its own default.
    """
    # ----- Build the request -----
    # We build it as a dictionary first, so we can add optional settings
    # only when they're set.
    request = {
        "model": model,  # which model to use
        "messages": messages,  # the conversation to send
        "max_tokens": max_tokens,  # longest output, including the hidden thinking
    }

    # Reasoning effort is an OpenRouter feature that the openai package doesn't
    # know about. "extra_body" means: add this to the request exactly as it is.
    # It's only added if an effort was chosen.
    if reasoning_effort is not None:
        request["extra_body"] = {"reasoning": {"effort": reasoning_effort}}

    # ----- Send it -----
    # "**request" unpacks the dictionary into named inputs. It's the same as
    # writing create(model=..., messages=..., max_tokens=...), plus extra_body
    # if it was added above.
    response = client.chat.completions.create(**request)

    # ----- A developer log -----
    # Printed in the TERMINAL, not on the page, so you can compare settings.
    # prompt_tokens: what we sent. completion_tokens: what came back,
    # including the model's hidden reasoning, which is billed as output.
    usage = response.usage
    print(
        f"[{model}, effort={reasoning_effort}, max_tokens={max_tokens}] "
        f"input: {usage.prompt_tokens}, output: {usage.completion_tokens} tokens"
    )

    # ----- Return the reply -----
    # The response can hold several answers, called "choices". We asked for
    # one, so we take the first, [0]. .message.content is its text.
    return response.choices[0].message.content


def ask_model_json(messages, schema):
    """Like ask_model, but asks for JSON in the shape of schema, and returns a dictionary.

    schema is a JSON schema, like REPORT_SCHEMA in prompts.py.
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        # A report is longer than a single reply, and the model also thinks first,
        # so it gets more room than ask_model's 2000.
        max_tokens=4000,
        # response_format asks for JSON that matches the schema.
        response_format={"type": "json_schema", "json_schema": schema},
    )

    # The reply is JSON written as text. "or ''" turns an empty reply (None) into "".
    text = (response.choices[0].message.content or "").strip()

    # Sometimes a model wraps JSON in ```json ... ``` marks, even when asked not to.
    # Never fully trust model output: if the marks are there, remove them.
    if text.startswith("```"):
        # .split("\n", 1)[1] drops the first line (```json).
        # .rsplit("```", 1)[0] drops everything from the last ``` onwards.
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    # json.loads turns JSON text into a Python dictionary.
    return json.loads(text)


# ----- A quick test -----

# This block only runs when we start this file directly: uv run python llm.py
# When another file (like app.py) imports llm.py, this block is skipped,
# so the test isn't sent every time the app starts.
if __name__ == "__main__":
    # A test conversation: a list with one user message.
    test_messages = [
        {"role": "user", "content": "Ask me one interview question for a junior Python developer."}
    ]
    # Send it, and print the reply.
    print(ask_model(test_messages))
